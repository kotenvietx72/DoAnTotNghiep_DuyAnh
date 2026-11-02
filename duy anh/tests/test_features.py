"""Hồi quy F21–F23 với SQLite tạm và Telegram đã tắt bởi test_energy."""
from copy import deepcopy
from decimal import Decimal
import random
import sqlite3
import unittest
from unittest.mock import patch

import test_energy
from room_service import DEFAULT_DEVICES, ROOM_CONFIGS, RoomService, classify
from simulation_service import SimulationService

web = test_energy.web


class FeatureTests(unittest.TestCase):
    setUp = test_energy.WebTests.setUp
    tearDown = test_energy.WebTests.tearDown

    def assert_consistent(self, state):
        for room in state["rooms"].values():
            active = [item for item in room["devices"] if item["is_on"]]
            total = float(round(sum((Decimal(str(item["current_a"])) for item in active), Decimal(0)), 6))
            self.assertEqual(room["active_count"], len(active))
            self.assertEqual(room["current"], total)
            self.assertEqual(room["status"], classify(total, room)[0])
            if total > 0:
                self.assertTrue(active)
        self.assertAlmostEqual(state["total_current"], sum(room["current"] for room in state["rooms"].values()), places=6)

    def test_bulk_on_each_room_is_independent_idempotent_and_persisted(self):
        for room_id in ROOM_CONFIGS:
            before = web.room_service.snapshot()
            with patch.object(web.room_service, "_save", wraps=web.room_service._save) as save:
                response = self.client.post(f"/api/rooms/{room_id}/devices", json={"is_on": True})
                self.assertEqual(response.status_code, 200)
                save.assert_called_once()
            state = response.get_json()
            self.assert_consistent(state)
            self.assertTrue(all(item["is_on"] for item in state["rooms"][room_id]["devices"]))
            for other in ROOM_CONFIGS.keys() - {room_id}:
                self.assertEqual(state["rooms"][other], before[other])
            again = self.client.post(f"/api/rooms/{room_id}/devices", json={"is_on": True}).get_json()
            self.assertEqual(again["rooms"], state["rooms"])
            self.assertEqual(RoomService(web.room_service.database_path).snapshot(), state["rooms"])

    def test_bulk_validation_and_legacy_rejection(self):
        for data in (None, [], {}, {"is_on": 1}, {"is_on": "true"}):
            with self.subTest(data=data):
                self.assertEqual(self.client.post("/api/rooms/r1/devices", json=data).status_code, 400)
        self.assertEqual(self.client.post("/api/rooms/unknown/devices", json={"is_on": True}).status_code, 404)
        self.client.post("/api/mode", json={"mode": "legacy"})
        self.assertEqual(self.client.post("/api/rooms/r1/devices", json={"is_on": True}).status_code, 409)

    def test_storage_failure_rolls_back_bulk_and_reset_without_publish(self):
        web.room_service.set_device("r1", "light1", True)
        before = web.room_service.snapshot()
        for path, payload in (("/api/rooms/r1/devices", {"is_on": True}), ("/api/settings/reset", {})):
            with self.subTest(path=path), patch.object(web.room_service, "_save", side_effect=sqlite3.OperationalError("test failure")), patch.object(web.socketio, "emit") as emit:
                response = self.client.post(path, json=payload)
                self.assertEqual(response.status_code, 500)
                self.assertFalse(response.get_json()["success"])
                emit.assert_not_called()
            self.assertEqual(web.room_service.snapshot(), before)
            self.assertEqual(RoomService(web.room_service.database_path).snapshot(), before)
            self.assertEqual(web.history_stats["config_changes"], [])

    def test_reset_exact_defaults_preserves_switches_and_history(self):
        self.client.post("/api/rooms/r2/devices", json={"is_on": True})
        self.client.put("/api/settings", json={"rooms": {"r2": {"thresh_warn": 1, "thresh_danger": 2, "devices": {"heater": 99}}}})
        switches = {key: [item["is_on"] for item in room["devices"]] for key, room in web.room_service.snapshot().items()}
        events = list(web.history_stats["event_log"])
        response = self.client.post("/api/settings/reset", json={})
        self.assertEqual(response.status_code, 200)
        state = response.get_json()
        self.assert_consistent(state)
        for key, room in state["rooms"].items():
            self.assertEqual(room["thresh_warn"], ROOM_CONFIGS[key]["thresh_warn"])
            self.assertEqual(room["thresh_danger"], ROOM_CONFIGS[key]["thresh_danger"])
            self.assertEqual([item["current_a"] for item in room["devices"]], [item["current_a"] for item in DEFAULT_DEVICES[key]])
            self.assertEqual([item["is_on"] for item in room["devices"]], switches[key])
        self.assertEqual(web.history_stats["event_log"][:len(events)], events)
        self.assertIn("Khôi phục", web.history_stats["config_changes"][-1])
        self.assertEqual(RoomService(web.room_service.database_path).snapshot(), state["rooms"])

    def test_legacy_initial_state_many_samples_and_restore_manual(self):
        self.client.post("/api/rooms/r1/devices/light1", json={"is_on": True})
        manual = web.room_service.snapshot()
        state = self.client.post("/api/mode", json={"mode": "legacy"}).get_json()
        self.assert_consistent(state)
        with patch.object(web.room_service, "_save") as save:
            for index in range(45):
                with web.state_lock:
                    web.update_legacy_data(index)
                    state = web.publish_state()
                self.assert_consistent(state)
                self.assertEqual([state["rooms"][key]["status"] for key in ROOM_CONFIGS],
                                 [("Safe", "Warning", "Danger")[(index + offset) % 3] for offset in range(3)])
            save.assert_not_called()
        self.assertEqual(web.room_service.snapshot(), manual)
        self.assertEqual(RoomService(web.room_service.database_path).snapshot(), manual)
        state = self.client.post("/api/mode", json={"mode": "devices"}).get_json()
        self.assertEqual(state["rooms"], manual)

    def test_start_first_state_stop_freezes_and_reads_do_not_randomize(self):
        self.client.post("/api/mode", json={"mode": "legacy"})
        web.update_legacy_data(2)
        response = self.client.post("/toggle_simulation", json={"action": "start"}).get_json()
        self.assertEqual(web.legacy_scenario_idx, 0)
        self.assert_consistent(response["state"])
        self.assertEqual(self.client.post("/api/mode", json={"mode": "devices"}).status_code, 409)
        self.client.post("/toggle_simulation", json={"action": "stop"})
        before = deepcopy(web.legacy_device_states)
        with patch.object(web.simulation_service, "select", side_effect=AssertionError("read must be pure")):
            for _ in range(3):
                self.assert_consistent(self.client.get("/api/state").get_json())
                self.assert_consistent(self.client.get("/get_report").get_json()["state"])
        self.assertEqual(before, web.legacy_device_states)

    def test_settings_and_reset_rebuild_legacy_without_resetting_phase(self):
        self.client.post("/api/mode", json={"mode": "legacy"})
        web.update_legacy_data(2)
        currents = {item["id"]: 0 for item in web.room_service.devices["r1"]}
        state = self.client.put("/api/settings", json={"rooms": {"r1": {"devices": currents}}}).get_json()
        self.assert_consistent(state)
        self.assertEqual(state["rooms"]["r1"]["current"], 0)
        self.assertEqual(state["rooms"]["r1"]["active_count"], 0)
        self.assertEqual(web.legacy_scenario_idx, 2)
        state = self.client.post("/api/settings/reset", json={}).get_json()
        self.assert_consistent(state)
        self.assertEqual(web.legacy_scenario_idx, 2)
        self.assertEqual(state["rooms"]["r1"]["status"], "Danger")

    def test_runtime_split_before_bulk_and_reset(self):
        web.is_simulating = True
        web.last_sample_time = 100
        with patch.object(web.time, "monotonic", return_value=102):
            self.client.post("/api/rooms/r1/devices", json={"is_on": True})
        self.assertEqual(web.history_stats["rooms"]["r1"]["safe"], 2)
        with patch.object(web.time, "monotonic", return_value=105):
            self.client.post("/api/settings/reset", json={})
        self.assertEqual(web.history_stats["rooms"]["r1"]["danger"], 3)
        self.assertEqual(web.history_stats["total_runtime"], 5)
        self.assertTrue(web.is_simulating)

    def test_new_apis_broadcast_same_revision_to_two_clients(self):
        clients = [web.socketio.test_client(web.app) for _ in range(2)]
        try:
            for path, payload in (("/api/rooms/r1/devices", {"is_on": True}), ("/api/settings/reset", {}), ("/api/mode", {"mode": "legacy"})):
                for client in clients:
                    client.get_received()
                state = self.client.post(path, json=payload).get_json()
                for client in clients:
                    events = [event for event in client.get_received() if event["name"] == "state_update"]
                    self.assertEqual(len(events), 1)
                    self.assertEqual(events[0]["args"][0], state)
                self.assert_consistent(state)
            self.assertEqual(self.client.get("/get_report").get_json()["state"]["rooms"], state["rooms"])
        finally:
            for client in clients:
                client.disconnect()


class SelectionTests(unittest.TestCase):
    def test_selection_matches_brute_force_with_boundaries_and_unreachable_band(self):
        service = SimulationService(random.Random(7))
        devices = [{"id": str(i), "current_a": value} for i, value in enumerate((0, .1, .7, 2))]
        cfg = {"thresh_warn": .8, "thresh_danger": 2.8}
        combinations = []
        for mask in range(16):
            total = sum((Decimal(str(item["current_a"])) for i, item in enumerate(devices) if mask & (1 << i)), Decimal(0))
            combinations.append((total, classify(float(total), cfg)[0]))
        for status in ("Safe", "Warning", "Danger"):
            for target in (0, .1, .8, 1, 2.8, 3, 100):
                with self.subTest(status=status, target=target):
                    states = service.select("r1", devices, cfg, target, status)
                    total = sum((Decimal(str(item["current_a"])) for item in devices if states[item["id"]]), Decimal(0))
                    candidates = [value for value, kind in combinations if kind == status]
                    self.assertEqual(abs(total - Decimal(str(target))), min(abs(value - Decimal(str(target))) for value in candidates))
                    self.assertFalse(states["0"])
        cfg = {"thresh_warn": 10, "thresh_danger": 20}
        states = service.select("r1", devices, cfg, 50, "Danger")
        self.assertEqual(sum(Decimal(str(item["current_a"])) for item in devices if states[item["id"]]), Decimal('2.8'))

    def test_ties_preserve_devices_cache_invalidates_and_all_zero_is_off(self):
        service = SimulationService(random.Random(1))
        devices = [{"id": "a", "current_a": 1}, {"id": "b", "current_a": 1}]
        cfg = {"thresh_warn": .5, "thresh_danger": 3}
        self.assertEqual(service.select("r1", devices, cfg, 1, "Warning", ["b"]), {"a": False, "b": True})
        devices[1]["current_a"] = 5
        self.assertEqual(service.select("r1", devices, cfg, 5, "Danger"), {"a": False, "b": True})
        for item in devices:
            item["current_a"] = 0
        self.assertEqual(service.select("r1", devices, cfg, 5, "Danger", ["a", "b"]), {"a": False, "b": False})
