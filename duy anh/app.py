from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
from copy import deepcopy
from io import BytesIO
import threading
import time
import datetime
import random
import os
import logging
import math
import uuid
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import requests
from openpyxl.styles import Font, Alignment
from room_service import ROOM_CONFIGS, RoomService, ValidationError, classify
from simulation_service import SimulationService

TAG = "app"
logger = logging.getLogger(TAG)
BASE_DIR = Path(__file__).resolve().parent
# Biến môi trường của Render luôn được ưu tiên hơn cấu hình cục bộ.
load_dotenv(BASE_DIR / ".env", override=False)
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
# Threading tránh monkey-patch toàn bộ Python, hỗ trợ WebSocket bằng simple-websocket.
socketio = SocketIO(app, async_mode="threading")
room_service = RoomService(os.environ.get("ROOM_DATABASE", str(BASE_DIR / "data" / "rooms.sqlite3")))
state_lock = room_service.lock
is_simulating = False
simulation_thread = None
simulation_stop = None
simulation_mode = "devices"
legacy_data = {}
legacy_device_states = {}
legacy_scenario_idx = 0
simulation_service = SimulationService()
state_revision = 0
server_id = uuid.uuid4().hex
last_sample_time = None

# ================= CẤU HÌNH TELEGRAM =================
# Đọc khóa bí mật từ biến môi trường hoặc file .env chỉ lưu trên máy.
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

def send_telegram_alert(message):
    """Hàm chạy ngầm gửi tin nhắn đến Telegram"""
    if (os.environ.get("TELEGRAM_ENABLED", "1") != "1"
            or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID or "THAY_" in TELEGRAM_TOKEN):
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=3)
        response.raise_for_status()
    except Exception as e:
        # Exception của requests có thể chứa URL kèm token; chỉ ghi tên loại lỗi.
        logger.warning("Không gửi được cảnh báo Telegram (%s).", type(e).__name__)
# =====================================================



def init_history():
    return {"total_runtime": 0.0, "rooms": {key: {"safe": 0.0, "warn": 0.0,
            "danger": 0.0, "last": "Safe"} for key in ROOM_CONFIGS},
            "event_log": [], "config_changes": [], "started_at": None}


history_stats = init_history()
SAMPLE_EXCEL_PATH = str(BASE_DIR / "kich_ban_1_pha_chuan.xlsx")


def create_clean_sample_excel():
    start_time = datetime.datetime(2026, 10, 15, 8, 0, 0)
    rng = random.Random(42)
    data = []
    for i in range(180):
        t = start_time + datetime.timedelta(seconds=i)
        base_i = (10.0, 28.0, 45.0)[(i % 45) // 15]
        data.append([t.strftime("%d/%m/%Y %H:%M:%S"),
                     round(225.0 - base_i * .3 + rng.uniform(-.3, .3), 1),
                     round(base_i + rng.uniform(-.2, .2), 1)])
    df = pd.DataFrame(data, columns=["Thời gian", "Điện áp (V)", "Dòng điện (A)"])
    with pd.ExcelWriter(SAMPLE_EXCEL_PATH, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="DuLieuDo")
        ws = writer.sheets["DuLieuDo"]
        for column, width in (("A", 25), ("B", 18), ("C", 18)):
            ws.column_dimensions[column].width = width
        for row in ws:
            for cell in row:
                cell.font = Font(name="Times New Roman", size=12, bold=cell.row == 1)
                cell.alignment = Alignment(horizontal="center", vertical="center")


def notify(message):
    # Cho phép tắt gửi thật khi kiểm thử; giữ tích hợp Telegram hiện có.
    if os.environ.get("TELEGRAM_ENABLED", "1") == "1":
        socketio.start_background_task(send_telegram_alert, message)


def account_runtime():
    """Chia đúng thời lượng tại mỗi lần đổi thiết bị/cấu hình giữa hai mẫu."""
    global last_sample_time
    if not is_simulating or last_sample_time is None:
        return
    now = time.monotonic()
    duration = max(0.0, now - last_sample_time)
    last_sample_time = now
    history_stats["total_runtime"] += duration
    for key, room in build_state()["rooms"].items():
        field = {"Safe": "safe", "Warning": "warn", "Danger": "danger"}[room["status"]]
        history_stats["rooms"][key][field] += duration


def build_state():
    rooms = room_service.snapshot(legacy_data if simulation_mode == "legacy" else None,
                                  legacy_device_states if simulation_mode == "legacy" else None)
    return {"server_id": server_id, "revision": state_revision, "timestamp": time.strftime("%H:%M:%S"),
            "is_simulating": is_simulating, "mode": simulation_mode,
            "total_current": round(math.fsum(room["current"] for room in rooms.values()), 6),
            "rooms": rooms, **rooms}


def record_transitions(rooms):
    for key, room in rooms.items():
        stats = history_stats["rooms"][key]
        if stats["last"] == room["status"]:
            continue
        labels = {"Safe": "Đã an toàn trở lại", "Warning": "Cảnh báo tải cao", "Danger": "Nguy hiểm quá tải"}
        message = f"[{time.strftime('%d/%m/%Y %H:%M:%S')}] {room['name']}: {labels[room['status']]} ({room['current']:.2f} A; {room['voltage']:g} V)"
        history_stats["event_log"].append(message)
        stats["last"] = room["status"]
        if is_simulating:
            notify(message)


def publish_state(sample=False):
    global state_revision
    state_revision += 1
    state = build_state()
    record_transitions(state["rooms"])
    socketio.emit("state_update", state)
    if sample:
        socketio.emit("new_sensor_data", state)
    return state


def update_legacy_data(scenario_idx):
    global legacy_scenario_idx, legacy_data, legacy_device_states
    legacy_scenario_idx = scenario_idx
    next_states = {}
    for index, (key, cfg) in enumerate(room_service.configs.items()):
        # Kịch bản cũ vẫn luân phiên 3 trạng thái, theo ngưỡng đang cài đặt.
        bases = (cfg["thresh_warn"] * .6,
                 (cfg["thresh_warn"] + cfg["thresh_danger"]) / 2,
                 cfg["thresh_danger"] * 1.15)
        phase = (scenario_idx + index) % 3
        current = round(bases[phase] * simulation_service.rng.uniform(.99, 1.01), 4)
        previous = [key_id for key_id, value in legacy_device_states.get(key, {}).items() if value]
        next_states[key] = simulation_service.select(key, room_service.devices[key], cfg, current,
                                                    ("Safe", "Warning", "Danger")[phase], previous)
    # Hoàn thành cả ba phòng trước khi công bố; không thay trạng thái đã lưu.
    rooms = room_service.snapshot(device_states=next_states)
    legacy_device_states = next_states
    legacy_data = {key: (room["current"], round(225 - room["current"] * .3, 1)) for key, room in rooms.items()}


def run_simulation(stop_event=None):
    stop_event = stop_event or simulation_stop
    started = time.monotonic()
    while not stop_event.wait(1.0):
        with state_lock:
            if not is_simulating or simulation_stop is not stop_event:
                break
            now = time.monotonic()
            account_runtime()
            if simulation_mode == "legacy":
                update_legacy_data(int((now - started) // 5) % 3)
            publish_state(sample=True)


@app.route("/toggle_simulation", methods=["POST"])
def toggle_simulation():
    global is_simulating, simulation_thread, simulation_stop, history_stats, last_sample_time
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or data.get("action") not in ("start", "stop"):
        raise ValidationError("Hành động không hợp lệ.")
    with state_lock:
        if data["action"] == "start" and not is_simulating:
            if simulation_mode == "legacy":
                update_legacy_data(0)
            history_stats = init_history()
            history_stats["started_at"] = time.strftime("%d/%m/%Y %H:%M:%S")
            history_stats["initial_configs"] = deepcopy(room_service.configs)
            history_stats["mode"] = simulation_mode
            simulation_stop = threading.Event()
            is_simulating = True
            last_sample_time = time.monotonic()
            simulation_thread = socketio.start_background_task(run_simulation, simulation_stop)
            notify("Hệ thống giám sát đã khởi động.")
        elif data["action"] == "stop" and is_simulating:
            account_runtime()
            is_simulating = False
            simulation_stop.set()
            notify("Hệ thống đã dừng lấy mẫu.")
        state = publish_state()
        socketio.emit("system_status", {"is_simulating": is_simulating})
        return jsonify({"message": "Đã khởi động lấy mẫu." if is_simulating else "Đã dừng lấy mẫu.", "state": state})


@socketio.on("connect")
def handle_connect():
    with state_lock:
        # Chỉ gửi bản chụp cho người vừa kết nối, không làm reset trình duyệt khác.
        emit("system_status", {"is_simulating": is_simulating})
        emit("state_update", build_state())


@app.route("/api/state")
def get_state():
    with state_lock:
        return jsonify(build_state())


@app.route("/api/rooms/<room_id>/devices/<device_id>", methods=["POST"])
def set_device(room_id, device_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Dữ liệu công tắc không hợp lệ.")
    with state_lock:
        if simulation_mode != "devices":
            return jsonify(error="Hãy chuyển sang chế độ Theo thiết bị để điều khiển công tắc."), 409
        account_runtime()
        room_service.set_device(room_id, device_id, data.get("is_on"))
        return jsonify(publish_state())


@app.route("/api/rooms/<room_id>/devices", methods=["POST"])
def set_all_devices(room_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Dữ liệu công tắc không hợp lệ.")
    with state_lock:
        if simulation_mode != "devices":
            return jsonify(error="Hãy chuyển sang chế độ Theo thiết bị để điều khiển công tắc."), 409
        account_runtime()
        room_service.set_all_devices(room_id, data.get("is_on"))
        return jsonify(publish_state())


@app.route("/api/settings/reset", methods=["POST"])
def reset_settings():
    with state_lock:
        account_runtime()
        room_service.reset_settings()
        change = f"[{time.strftime('%d/%m/%Y %H:%M:%S')}] Khôi phục ngưỡng và dòng điện mặc định của ba phòng."
        history_stats["config_changes"].append(change)
        history_stats["event_log"].append(change)
        if simulation_mode == "legacy":
            update_legacy_data(legacy_scenario_idx)
        return jsonify(publish_state())


@app.route("/api/settings", methods=["GET", "PUT"])
def settings_api():
    with state_lock:
        if request.method == "PUT":
            account_runtime()
            room_service.update_settings(request.get_json(silent=True))
            change = f"[{time.strftime('%d/%m/%Y %H:%M:%S')}] Cập nhật dòng điện/ngưỡng: " + "; ".join(
                f"{cfg['name']} {cfg['thresh_warn']:g}/{cfg['thresh_danger']:g} A" for cfg in room_service.configs.values())
            history_stats["config_changes"].append(change)
            history_stats["event_log"].append(change)
            if simulation_mode == "legacy":
                update_legacy_data(legacy_scenario_idx)
            return jsonify(publish_state())
        return jsonify(build_state())


@app.route("/api/mode", methods=["POST"])
def set_mode():
    global simulation_mode
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or data.get("mode") not in ("devices", "legacy"):
        raise ValidationError("Chế độ không hợp lệ.")
    with state_lock:
        if is_simulating:
            return jsonify(error="Vui lòng dừng lấy mẫu trước khi chuyển chế độ."), 409
        simulation_mode = data["mode"]
        if simulation_mode == "legacy":
            update_legacy_data(0)
        return jsonify(publish_state())


@app.route("/get_report", methods=["GET"])
def get_report():
    with state_lock:
        account_runtime()
        return jsonify({**deepcopy(history_stats), "configs": deepcopy(room_service.configs),
                        "mode": history_stats.get("mode", simulation_mode), "state": build_state()})


@app.route("/download_sample", methods=["GET"])
def download_sample():
    if not os.path.exists(SAMPLE_EXCEL_PATH):
        create_clean_sample_excel()
    return send_file(SAMPLE_EXCEL_PATH, as_attachment=True, download_name="kich_ban_1_pha_chuan.xlsx")


@app.route("/internal")
def internal_mode():
    return render_template("internal.html", page="internal", title="Phân tích nội bộ")


@app.route("/analyze_1phase", methods=["POST"])
def analyze_1phase():
    room_id = request.form.get("room_id")
    with state_lock:
        if room_id and room_id not in room_service.configs:
            raise ValidationError("Phòng phân tích không hợp lệ.")
        cfg = deepcopy(room_service.configs[room_id]) if room_id else {
            "name": "Dữ liệu một pha", "thresh_warn": 25.0, "thresh_danger": 40.0}
    thresh_warn, thresh_danger = cfg["thresh_warn"], cfg["thresh_danger"]
    if "file" not in request.files or not request.files["file"].filename:
        raise ValidationError("Vui lòng chọn file Excel hoặc CSV.")
    file = request.files["file"]
    extension = Path(file.filename).suffix.lower()
    if extension not in (".xlsx", ".xls", ".csv"):
        raise ValidationError("Chỉ hỗ trợ file .xlsx, .xls hoặc .csv.")
    try:
        raw = file.read()
        if extension == ".csv":
            try:
                df = pd.read_csv(BytesIO(raw), encoding="utf-8-sig")
            except UnicodeDecodeError:
                df = pd.read_csv(BytesIO(raw), encoding="latin1")
        else:
            df = pd.read_excel(BytesIO(raw))
        if len(df.columns) < 3:
            raise ValidationError("File phải có 3 cột: Thời gian, Điện áp (V), Dòng điện (A).")
        df = df.iloc[:, :3].dropna(how="all")
        if df.empty:
            raise ValidationError("File không có dữ liệu để phân tích.")
        if len(df) > 100000:
            raise ValidationError("File chỉ được chứa tối đa 100.000 mẫu.")
        if df.iloc[:, 0].isna().any():
            raise ValidationError("Cột thời gian không được để trống.")
        for index in (1, 2):
            df.iloc[:, index] = pd.to_numeric(df.iloc[:, index], errors="raise")
            if not all(math.isfinite(float(value)) and float(value) >= 0 for value in df.iloc[:, index]):
                raise ValidationError("Điện áp và dòng điện phải là số hữu hạn, không âm.")
        warning_count = danger_count = safe_count = 0
        event_log, last_status = [], "Safe"
        for row in df.itertuples(index=False, name=None):
            t_str, u_val, i_val = str(row[0]), float(row[1]), float(row[2])
            status, _ = classify(i_val, cfg)
            safe_count += status == "Safe"
            if status != last_status:
                warning_count += status == "Warning"
                danger_count += status == "Danger"
                event_log.append(f"[{t_str}] {cfg['name']}: " + {
                    "Safe": "Đã an toàn trở lại", "Warning": "Cảnh báo tải cao", "Danger": "Nguy hiểm quá tải"
                }[status] + f" ({i_val:g} A)")
            last_status = status
        return jsonify(success=True, labels=df.iloc[:, 0].astype(str).tolist(),
                       U_val=df.iloc[:, 1].astype(float).tolist(), I_val=df.iloc[:, 2].astype(float).tolist(),
                       report_data={"total_runtime": len(df), "sample_count": len(df),
                                    "safe_count": safe_count, "warning_count": warning_count,
                                    "danger_count": danger_count, "event_log": event_log,
                                    "room_name": cfg["name"], "thresh_warn": thresh_warn,
                                    "thresh_danger": thresh_danger})
    except ValidationError:
        raise
    except Exception as error:
        logger.info("Không thể phân tích tệp: %s", type(error).__name__)
        raise ValidationError("Không đọc được dữ liệu. Kiểm tra định dạng và ba cột trong file.")


@app.errorhandler(ValidationError)
def invalid_input(error):
    return jsonify(success=False, error=str(error)), 400


@app.errorhandler(KeyError)
def missing_resource(error):
    return jsonify(success=False, error=str(error).strip("'")), 404


@app.errorhandler(413)
def file_too_large(error):
    return jsonify(success=False, error="File vượt quá giới hạn 10 MB."), 413


@app.errorhandler(sqlite3.Error)
def storage_error(error):
    logger.warning("Không lưu được cấu hình (%s).", type(error).__name__)
    return jsonify(success=False, error="Không lưu được thay đổi. Cấu hình trước đó được giữ; vui lòng thử lại."), 500


@app.route("/")
def index():
    return render_template("index.html", page="dashboard", title="Tổng quan hệ thống")


@app.route("/rooms/<room_id>")
def room_detail(room_id):
    if room_id not in room_service.configs:
        return render_template("not_found.html", page="", title="Không tìm thấy phòng"), 404
    return render_template("room.html", page=room_id, room_id=room_id, title=room_service.configs[room_id]["name"])


@app.route("/settings")
def settings_page():
    return render_template("settings.html", page="settings", title="Cài đặt hệ thống")


if __name__ == "__main__":
    if not os.path.exists(SAMPLE_EXCEL_PATH):
        create_clean_sample_excel()
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, debug=False, host=os.environ.get("HOST", "0.0.0.0"), port=port,
                 allow_unsafe_werkzeug=True)
