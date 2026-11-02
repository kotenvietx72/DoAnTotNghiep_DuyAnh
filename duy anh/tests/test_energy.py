"""Kiểm thử nghiệp vụ và hồi quy API, không gửi Telegram hoặc MQTT thật."""
import atexit
import json
import sqlite3
from io import BytesIO
import os
from pathlib import Path
import tempfile
import time
import unittest
import random

os.environ["TELEGRAM_ENABLED"] = "0"
_import_database = tempfile.TemporaryDirectory()
atexit.register(_import_database.cleanup)
os.environ["ROOM_DATABASE"] = str(Path(_import_database.name) / "import.sqlite3")

import app as web
from room_service import RoomService, ValidationError
from simulation_service import SimulationService


class LoadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "rooms.sqlite3"
        self.service = RoomService(self.path)
        self.service.update_settings({"rooms":{"r1":{"devices":{"light1":0.2,"fan1":0.3}}}})

    def tearDown(self):
        self.temp.cleanup()

    def test_all_off_is_exactly_zero_and_safe(self):
        for room in self.service.snapshot().values():
            self.assertEqual((room["current"],room["active_count"]),(0,0))
            self.assertNotIn("power_w",room)
            self.assertEqual(room["status"],"Safe")
            self.assertEqual(room["voltage"],220)

    def test_switches_add_only_active_devices_and_rooms_are_independent(self):
        self.service.set_device("r1","light1",True)
        self.service.set_device("r1","fan1",True)
        room = self.service.snapshot()["r1"]
        self.assertEqual(room["current"],0.5)
        self.assertEqual(self.service.snapshot()["r2"]["current"],0)
        self.service.set_device("r1","light1",False)
        self.assertEqual(self.service.snapshot()["r1"]["current"],0.3)
        self.service.set_device("r1","fan1",False)
        self.assertEqual(self.service.snapshot()["r1"]["current"],0)

    def test_repeated_explicit_on_is_idempotent(self):
        for _ in range(3): self.service.set_device("r1","light1",True)
        self.assertEqual(self.service.snapshot()["r1"]["current"],0.2)

    def test_inclusive_warning_and_danger_boundaries(self):
        self.service.update_settings({"rooms":{"r1":{"thresh_warn":5,"thresh_danger":10,"devices":{"light1":5}}}})
        self.service.set_device("r1","light1",True)
        self.assertEqual(self.service.snapshot()["r1"]["status"],"Warning")
        self.service.update_settings({"rooms":{"r1":{"devices":{"light1":10}}}})
        self.assertEqual(self.service.snapshot()["r1"]["status"],"Danger")
        self.service.update_settings({"rooms":{"r1":{"devices":{"light1":4.99}}}})
        self.assertEqual(self.service.snapshot()["r1"]["status"],"Safe")

    def test_zero_current_device_does_not_add_load(self):
        self.service.update_settings({"rooms":{"r2":{"devices":{"ac":0}}}})
        self.service.set_device("r2","ac",True)
        self.assertEqual(self.service.snapshot()["r2"]["current"],0)

    def test_invalid_settings_are_atomic_and_do_not_persist(self):
        before = self.service.snapshot()
        with self.assertRaises(ValidationError):
            self.service.update_settings({"rooms":{"r1":{"devices":{"light1":88}},"r2":{"thresh_warn":50,"thresh_danger":20}}})
        self.assertEqual(self.service.snapshot(),before)
        self.assertEqual(RoomService(self.path).snapshot(),before)

    def test_rejects_invalid_numeric_values_and_boolean_currents(self):
        for value in [-1,float("nan"),float("inf"),True,"100"]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.service.update_settings({"rooms":{"r1":{"devices":{"light1":value}}}})

    def test_configuration_and_switches_survive_restart(self):
        self.service.update_settings({"rooms":{"r3":{"thresh_warn":2,"thresh_danger":4,"devices":{"fan":123}}}})
        self.service.set_device("r3","fan",True)
        self.assertEqual(RoomService(self.path).snapshot(),self.service.snapshot())

    def test_rejects_invalid_device_and_non_boolean_switch(self):
        with self.assertRaises(KeyError): self.service.set_device("r1","missing",True)
        with self.assertRaises(KeyError): self.service.set_device("missing","fan",True)
        with self.assertRaises(ValidationError): self.service.set_device("r1","fan1",1)

    def test_decimal_sum_reaches_warning_threshold_exactly(self):
        self.service.update_settings({"rooms":{"r1":{"thresh_warn":0.8,"thresh_danger":1.5,"devices":{"light1":0.1,"fan1":0.7}}}})
        self.service.set_device("r1","light1",True)
        self.service.set_device("r1","fan1",True)
        room = self.service.snapshot()["r1"]
        self.assertEqual(room["current"],0.8)
        self.assertEqual(room["status"],"Warning")

    def test_legacy_conversion_preserves_custom_values_switches_and_runs_once(self):
        legacy = {"rooms":{"r1":{"thresh_warn":1,"thresh_danger":2,
                  "devices":{"light1":40,"fan1":110}}},
                  "states":{"r1":{"light1":True,"fan1":True}}}
        with sqlite3.connect(self.path) as connection:
            connection.execute("INSERT OR REPLACE INTO configuration (id,payload) VALUES (1,?)",(json.dumps(legacy),))
        connection.close()
        migrated = RoomService(self.path)
        room = migrated.snapshot()["r1"]
        devices = {item["id"]:item for item in room["devices"]}
        self.assertEqual(devices["light1"]["current_a"],0.095)
        self.assertEqual(devices["fan1"]["current_a"],0.5)
        self.assertTrue(devices["fan1"]["is_on"])
        self.assertEqual((room["thresh_warn"],room["thresh_danger"]),(1,2))
        self.assertEqual(room["current"],0.595)
        self.assertEqual(RoomService(self.path).snapshot(),migrated.snapshot())
        with sqlite3.connect(self.path) as connection:
            payload = json.loads(connection.execute("SELECT payload FROM configuration WHERE id=1").fetchone()[0])
        connection.close()
        self.assertEqual(payload["device_unit"],"A")


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        web.room_service = RoomService(Path(self.temp.name)/"rooms.sqlite3")
        web.room_service.update_settings({"rooms":{"r1":{"devices":{"light1":0.2,"fan1":0.3}},"r3":{"devices":{"fan":0.25}}}})
        web.state_lock = web.room_service.lock
        web.history_stats = web.init_history()
        web.is_simulating = False
        web.simulation_mode = "devices"
        web.legacy_data = {}
        web.legacy_device_states = {}
        web.legacy_scenario_idx = 0
        web.simulation_service = SimulationService(random.Random(42))
        web.state_revision = 0
        web.last_sample_time = None
        web.simulation_stop = None
        web.simulation_thread = None
        web.app.config["TESTING"] = True
        self.client = web.app.test_client()

    def tearDown(self):
        with web.state_lock:
            web.is_simulating = False
            if web.simulation_stop: web.simulation_stop.set()
        if web.simulation_thread: web.simulation_thread.join(timeout=2)
        self.temp.cleanup()

    def test_all_pages_render_and_room_404(self):
        for path in ["/","/rooms/r1","/rooms/r2","/rooms/r3","/settings","/internal"]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code,200)
                self.assertIn("EPU Energy",response.get_data(as_text=True))
        self.assertEqual(self.client.get("/rooms/missing").status_code,404)

    def test_api_validation_and_unknown_device(self):
        self.assertEqual(self.client.post("/toggle_simulation",json={"action":"wrong"}).status_code,400)
        self.assertEqual(self.client.put("/api/settings",json={"rooms":[]}).status_code,400)
        self.assertEqual(self.client.post("/api/rooms/r1/devices/light1",json={"is_on":"false"}).status_code,400)
        self.assertEqual(self.client.post("/api/rooms/r1/devices/missing",json={"is_on":True}).status_code,404)

    def test_device_changes_immediately_even_when_sampling_stopped(self):
        result = self.client.post("/api/rooms/r1/devices/light1",json={"is_on":True}).get_json()
        self.assertEqual(result["rooms"]["r1"]["current"],0.2)
        self.assertNotIn("total_power_w",result)
        self.assertFalse(result["is_simulating"])
        self.assertEqual(self.client.get("/api/state").get_json()["total_current"],0.2)

    def test_dashboard_total_sums_room_currents_and_keeps_voltage_separate(self):
        self.client.post("/api/rooms/r1/devices/light1",json={"is_on":True})
        result = self.client.post("/api/rooms/r3/devices/fan",json={"is_on":True}).get_json()
        self.assertEqual(result["total_current"],0.45)
        self.assertEqual(result["rooms"]["r1"]["voltage"],220)
        self.assertEqual(result["rooms"]["r3"]["voltage"],220)
        self.assertNotIn("power_w",result["rooms"]["r1"])

    def test_settings_recalculate_active_devices_and_report_uses_new_config(self):
        self.client.post("/api/rooms/r1/devices/light1",json={"is_on":True})
        response = self.client.put("/api/settings",json={"rooms":{"r1":{"thresh_warn":1,"thresh_danger":2,"devices":{"light1":2}}}})
        self.assertEqual(response.get_json()["rooms"]["r1"]["status"],"Danger")
        report = self.client.get("/get_report").get_json()
        self.assertEqual(report["configs"]["r1"]["thresh_danger"],2)
        self.assertEqual(report["configs"]["r2"]["name"],"Kí túc xá")
        self.assertTrue(report["config_changes"])

    def test_socket_updates_both_clients_and_late_connect_is_targeted(self):
        first = web.socketio.test_client(web.app)
        first.get_received()
        second = web.socketio.test_client(web.app)
        self.assertEqual(first.get_received(),[])
        self.assertTrue(any(event["name"]=="state_update" for event in second.get_received()))
        self.client.post("/api/rooms/r3/devices/fan",json={"is_on":True})
        for client in [first,second]:
            events = [event for event in client.get_received() if event["name"]=="state_update"]
            self.assertEqual(events[-1]["args"][0]["rooms"]["r3"]["current"],0.25)
            client.disconnect()

    def test_start_stop_fast_restart_has_one_worker_and_time_is_accounted(self):
        self.client.post("/toggle_simulation",json={"action":"start"})
        old_worker = web.simulation_thread
        self.client.post("/toggle_simulation",json={"action":"stop"})
        self.client.post("/toggle_simulation",json={"action":"start"})
        self.assertIsNot(web.simulation_thread,old_worker)
        old_worker.join(timeout=2)
        self.assertFalse(old_worker.is_alive())
        time.sleep(1.05)
        self.client.post("/toggle_simulation",json={"action":"stop"})
        report = self.client.get("/get_report").get_json()
        self.assertGreaterEqual(report["total_runtime"],1)
        self.assertLess(report["total_runtime"],2)
        for room in report["rooms"].values():
            self.assertAlmostEqual(room["safe"]+room["warn"]+room["danger"],report["total_runtime"],places=4)

    def test_modes_are_explicit_and_device_state_is_preserved(self):
        self.client.post("/api/rooms/r1/devices/light1",json={"is_on":True})
        self.client.post("/api/mode",json={"mode":"legacy"})
        self.assertEqual(self.client.post("/api/rooms/r1/devices/light1",json={"is_on":False}).status_code,409)
        self.client.post("/toggle_simulation",json={"action":"start"})
        self.assertEqual(self.client.post("/api/mode",json={"mode":"devices"}).status_code,409)
        self.client.post("/toggle_simulation",json={"action":"stop"})
        response = self.client.post("/api/mode",json={"mode":"devices"}).get_json()
        self.assertEqual(response["rooms"]["r1"]["current"],0.2)

    def test_csv_uses_selected_thresholds_and_counts_transitions(self):
        payload = b'time,voltage,current\n08:00:00,220,0\n08:00:01,220,12\n08:00:02,220,18\n08:00:03,220,18\n08:00:04,220,0\n'
        response = self.client.post("/analyze_1phase",data={"room_id":"r1","file":(BytesIO(payload),"READINGS.CSV")})
        self.assertEqual(response.status_code,200)
        report = response.get_json()["report_data"]
        self.assertEqual((report["sample_count"],report["safe_count"],report["warning_count"],report["danger_count"]),(5,2,1,1))
        self.assertEqual(report["thresh_warn"],12)
        self.assertEqual(len(report["event_log"]),3)

    def test_xlsx_and_sample_download_still_work(self):
        sample = self.client.get("/download_sample")
        self.assertEqual(sample.status_code,200)
        response = self.client.post("/analyze_1phase",data={"room_id":"r2","file":(BytesIO(sample.data),"sample.xlsx")})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.get_json()["report_data"]["sample_count"],180)
        sample.close()

    def test_original_single_phase_thresholds_remain_available(self):
        payload = b'time,voltage,current\n0,220,10\n1,220,28\n2,220,45\n'
        response = self.client.post("/analyze_1phase",data={"room_id":"","file":(BytesIO(payload),"sample.csv")})
        report = response.get_json()["report_data"]
        self.assertEqual((report["thresh_warn"],report["thresh_danger"]),(25,40))
        self.assertEqual((report["safe_count"],report["warning_count"],report["danger_count"]),(1,1,1))

    def test_invalid_uploads_are_user_errors_not_server_crashes(self):
        cases = [(b"a,b\n1,2\n","missing.csv"),(b"a,b,c\n","empty.csv"),(b"a,b,c\nt,220,-1\n","negative.csv"),(b"a,b,c\nt,220,inf\n","infinite.csv"),(b"invalid","wrong.txt"),(b"a,b,c\nt,220,no\n","text.csv")]
        for payload,name in cases:
            with self.subTest(name=name):
                response = self.client.post("/analyze_1phase",data={"file":(BytesIO(payload),name)})
                self.assertEqual(response.status_code,400)
                self.assertFalse(response.get_json()["success"])

    def test_all_frontend_assets_are_local_and_served(self):
        for path in ["css/app.css","js/app.js","js/room-model.js","vendor/chart.umd.js","vendor/socket.io.min.js","vendor/html2pdf.bundle.min.js"]:
            response = self.client.get(f"/static/{path}")
            self.assertEqual(response.status_code,200,path)
            self.assertGreater(len(response.data),100)
            response.close()


if __name__ == "__main__":
    unittest.main()
