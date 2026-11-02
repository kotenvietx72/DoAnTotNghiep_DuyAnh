"""Mô hình dòng điện thiết bị và điện áp nguồn một pha 220 V."""
from copy import deepcopy
from contextlib import contextmanager
from decimal import Decimal
import json
import math
from pathlib import Path
import sqlite3
import threading
from device_references import DEVICE_REFERENCE_KEYS, REFERENCE_PROFILES, LEGACY_DEVICE_DEFAULTS


ROOM_CONFIGS = {
    "r1": {"name": "Phòng học", "subtitle": "Không gian học tập", "kind": "classroom",
           "base_safe": 15.0, "base_warn": 40.0, "base_danger": 55.0,
           "thresh_warn": 12.0, "thresh_danger": 18.0},
    "r2": {"name": "Kí túc xá", "subtitle": "Không gian sinh hoạt", "kind": "dormitory",
           "base_safe": 10.0, "base_warn": 28.0, "base_danger": 45.0,
           "thresh_warn": 12.0, "thresh_danger": 20.0},
    "r3": {"name": "Phòng bảo vệ", "subtitle": "Không gian trực an ninh", "kind": "security",
           "base_safe": 5.0, "base_warn": 18.0, "base_danger": 28.0,
           "thresh_warn": 6.0, "thresh_danger": 10.0},
}


def device(device_id, name, kind, reference_key, x, y):
    profile = deepcopy(REFERENCE_PROFILES[reference_key])
    return {"id": device_id, "name": name, "kind": kind, "current_a": profile["current_a"], "reference": profile,
            "is_on": False, "x": x, "y": y}


DEFAULT_DEVICES = {
    "r1": [
        device("light1", "Đèn lớp 01", "light", "room_led", 240, 190),
        device("light2", "Đèn lớp 02", "light", "room_led", 420, 190),
        device("light3", "Đèn lớp 03", "light", "room_led", 600, 190),
        device("light4", "Đèn lớp 04", "light", "room_led", 240, 340),
        device("light5", "Đèn lớp 05", "light", "room_led", 420, 340),
        device("light6", "Đèn lớp 06", "light", "room_led", 600, 340),
        device("fan1", "Quạt trần 01", "fan", "ceiling_fan", 310, 260),
        device("fan2", "Quạt trần 02", "fan", "ceiling_fan", 520, 260),
        device("fan3", "Quạt trần 03", "fan", "ceiling_fan", 310, 420),
        device("fan4", "Quạt trần 04", "fan", "ceiling_fan", 520, 420),
        device("ac1", "Điều hòa 01", "ac", "ac_classroom", 170, 105),
        device("ac2", "Điều hòa 02", "ac", "ac_classroom", 650, 105),
        device("projector", "Máy chiếu", "projector", "projector", 420, 115),
        device("computer", "Máy tính giáo viên", "computer", "computer", 175, 460),
    ],
    "r2": [
        device("light1", "Đèn phòng 01", "light", "small_led", 310, 190),
        device("light2", "Đèn phòng 02", "light", "small_led", 530, 190),
        device("desk_light1", "Đèn bàn 01", "light", "desk_led", 200, 405),
        device("desk_light2", "Đèn bàn 02", "light", "desk_led", 610, 405),
        device("fan1", "Quạt 01", "fan", "standing_fan", 310, 305),
        device("fan2", "Quạt 02", "fan", "standing_fan", 525, 305),
        device("ac", "Điều hòa", "ac", "ac_dormitory", 420, 105),
        device("heater", "Bình nóng lạnh", "heater", "heater", 655, 115),
        device("laptop1", "Máy tính 01", "computer", "laptop", 195, 465),
        device("laptop2", "Máy tính 02", "computer", "laptop", 620, 465),
        device("kettle", "Ấm siêu tốc", "kettle", "kettle", 420, 455),
    ],
    "r3": [
        device("light1", "Đèn trực 01", "light", "small_led", 315, 195),
        device("light2", "Đèn trực 02", "light", "small_led", 530, 195),
        device("fan", "Quạt trực", "fan", "standing_fan", 420, 300),
        device("ac", "Điều hòa", "ac", "ac_security", 420, 105),
        device("computer", "Máy tính trực", "computer", "computer", 290, 425),
        device("monitor", "Màn hình camera", "monitor", "monitor", 530, 425),
        device("camera", "Camera an ninh", "camera", "camera", 650, 115),
        device("kettle", "Ấm siêu tốc", "kettle", "kettle", 650, 425),
    ],
}


class ValidationError(ValueError):
    pass


def number(value, label, minimum=0, maximum=100000):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{label} phải là một số hợp lệ.")
    if not math.isfinite(value) or value < minimum or value > maximum:
        raise ValidationError(f"{label} phải nằm trong khoảng {minimum}–{maximum}.")
    return float(value)


def classify(current, cfg):
    if current >= cfg["thresh_danger"]:
        return "Danger", f"Nguy hiểm: quá tải. Hãy tắt bớt thiết bị (ngưỡng {cfg['thresh_danger']:g} A)."
    if current >= cfg["thresh_warn"]:
        return "Warning", f"Cảnh báo: tải đang cao. Nên giảm thiết bị (ngưỡng {cfg['thresh_warn']:g} A)."
    return "Safe", "Phụ tải trong giới hạn an toàn."


class RoomService:
    def __init__(self, database_path):
        self.lock = threading.RLock()
        self.database_path = str(database_path)
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self.configs = deepcopy(ROOM_CONFIGS)
        self.devices = deepcopy(DEFAULT_DEVICES)
        with self._connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS configuration (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
            row = connection.execute("SELECT payload FROM configuration WHERE id=1").fetchone()
        if row:
            saved = json.loads(row[0])
            migrated = saved.get("device_unit", "W") == "W"
            if migrated:
                # Chỉ chuyển cấu hình cũ một lần; giữ nguyên ngưỡng A và công tắc.
                for room_id, cfg in saved.get("rooms", {}).items():
                    for key, value in cfg.get("devices", {}).items():
                        value = number(value, "Giá trị cấu hình cũ")
                        # Mặc định cũ áp thông số hãng; mức người dùng tự đặt được giữ tương đương.
                        if value == LEGACY_DEVICE_DEFAULTS.get(room_id, {}).get(key):
                            cfg["devices"][key] = REFERENCE_PROFILES[DEVICE_REFERENCE_KEYS[room_id][key]]["current_a"]
                        else:
                            cfg["devices"][key] = round(value / 220, 6)
            elif saved.get("device_unit") != "A":
                raise ValidationError("Đơn vị cấu hình thiết bị không được hỗ trợ.")
            self.update_settings(saved, persist=False)
            for room_id, items in saved.get("states", {}).items():
                if room_id in self.devices:
                    for item in self.devices[room_id]:
                        item["is_on"] = items.get(item["id"]) is True
            if migrated:
                self._save()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _save(self):
        payload = {"schema_version": 2, "device_unit": "A", "rooms": {key: {
            "thresh_warn": cfg["thresh_warn"], "thresh_danger": cfg["thresh_danger"],
            "devices": {item["id"]: item["current_a"] for item in self.devices[key]},
        } for key, cfg in self.configs.items()},
            "states": {key: {item["id"]: item["is_on"] for item in items}
                       for key, items in self.devices.items()}}
        with self._connect() as connection:
            connection.execute("INSERT OR REPLACE INTO configuration (id,payload) VALUES (1,?)",
                               (json.dumps(payload, ensure_ascii=False),))

    def update_settings(self, payload, persist=True):
        with self.lock:
            if not isinstance(payload, dict) or not isinstance(payload.get("rooms"), dict) or not payload["rooms"]:
                raise ValidationError("Cần cung cấp cấu hình phòng.")
            configs, devices = deepcopy(self.configs), deepcopy(self.devices)
            for room_id, changes in payload["rooms"].items():
                if room_id not in configs or not isinstance(changes, dict):
                    raise ValidationError("Phòng không hợp lệ.")
                cfg = configs[room_id]
                for field in ("thresh_warn", "thresh_danger"):
                    if field in changes:
                        cfg[field] = number(changes[field], "Ngưỡng dòng điện (A)", 0.01, 1000)
                if cfg["thresh_warn"] >= cfg["thresh_danger"]:
                    raise ValidationError("Ngưỡng nguy hiểm phải lớn hơn ngưỡng cảnh báo.")
                currents = changes.get("devices", {})
                if not isinstance(currents, dict):
                    raise ValidationError("Danh sách dòng điện không hợp lệ.")
                known = {item["id"]: item for item in devices[room_id]}
                for device_id, current in currents.items():
                    if device_id not in known:
                        raise ValidationError("Thiết bị không tồn tại trong phòng.")
                    known[device_id]["current_a"] = number(current, "Dòng điện thiết bị (A)", 0, 1000)
            old_configs, old_devices = self.configs, self.devices
            self.configs, self.devices = configs, devices
            try:
                if persist:
                    self._save()
            except Exception:
                self.configs, self.devices = old_configs, old_devices
                raise

    def set_device(self, room_id, device_id, is_on):
        with self.lock:
            if room_id not in self.devices:
                raise KeyError("Phòng không tồn tại.")
            if type(is_on) is not bool:
                raise ValidationError("Trạng thái bật/tắt phải là true hoặc false.")
            item = next((item for item in self.devices[room_id] if item["id"] == device_id), None)
            if item is None:
                raise KeyError("Thiết bị không tồn tại.")
            previous = item["is_on"]
            item["is_on"] = is_on
            try:
                self._save()
            except Exception:
                item["is_on"] = previous
                raise

    def set_all_devices(self, room_id, is_on):
        with self.lock:
            if room_id not in self.devices:
                raise KeyError("Phòng không tồn tại.")
            if type(is_on) is not bool:
                raise ValidationError("Trạng thái bật/tắt phải là true hoặc false.")
            previous = [item["is_on"] for item in self.devices[room_id]]
            for item in self.devices[room_id]:
                item["is_on"] = is_on
            try:
                self._save()
            except Exception:
                for item, value in zip(self.devices[room_id], previous):
                    item["is_on"] = value
                raise

    def reset_settings(self):
        self.update_settings({"rooms": {key: {
            "thresh_warn": cfg["thresh_warn"], "thresh_danger": cfg["thresh_danger"],
            "devices": {item["id"]: item["current_a"] for item in DEFAULT_DEVICES[key]},
        } for key, cfg in ROOM_CONFIGS.items()}})

    def snapshot(self, overrides=None, device_states=None):
        with self.lock:
            rooms = {}
            for key, cfg in self.configs.items():
                items = deepcopy(self.devices[key])
                if device_states is not None:
                    for item in items:
                        item["is_on"] = device_states.get(key, {}).get(item["id"], False)
                # Cộng số thập phân để 0.1 A + 0.7 A chạm đúng ngưỡng 0.8 A.
                current = float(round(sum((Decimal(str(item["current_a"])) for item in items if item["is_on"]), Decimal(0)), 6))
                voltage = 220.0
                if overrides and key in overrides:
                    # Giữ hợp đồng override cũ; mô phỏng đồng bộ luôn lấy dòng từ thiết bị.
                    if device_states is None:
                        current, voltage = overrides[key]
                    else:
                        voltage = overrides[key][1]
                status, advice = classify(current, cfg)
                rooms[key] = {**deepcopy(cfg), "id": key, "current": round(current, 6),
                              "voltage": voltage,
                              "status": status, "advice": advice,
                              "active_count": sum(item["is_on"] for item in items),
                              "devices": deepcopy(items)}
            return rooms
