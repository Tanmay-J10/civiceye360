import asyncio
import csv
import os
import secrets
import socket
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime

import cv2
import numpy as np
import serial
from fastapi import FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from picamera2 import Picamera2
from hailo_platform import (
    VDevice, HEF, ConfigureParams, HailoStreamInterface,
    InferVStreams, InputVStreamParams, OutputVStreamParams, FormatType
)

API_KEY = os.environ.get("CIVICEYE_API_KEY", "civiceye-2026")
ARDUINO_PORT = os.environ.get("ARDUINO_PORT", "/dev/ttyACM0")
GPS_PORT = os.environ.get("GPS_PORT", "/dev/ttyUSB0")
HEF_PATH = "yolov8n.hef"

INDOOR_BASE_LAT = 12.89435
INDOOR_BASE_LNG = 77.54150

HAZARD_META = {
    0: {"name": "POTHOLE", "action": "Cold-Mix Asphalt", "base_cost": 250, "color": (0, 0, 255)},
    1: {"name": "GARBAGE DUMP", "action": "SWM Compactor", "base_cost": 450, "color": (0, 140, 255)},
    2: {"name": "OPEN MANHOLE", "action": "RCC Cover Replace", "base_cost": 2500, "color": (0, 0, 200)},
    3: {"name": "DANGLING CABLE", "action": "Cable Elevation", "base_cost": 450, "color": (0, 255, 255)},
    4: {"name": "ILLEGAL HOARDING", "action": "Fine & Demolish", "base_cost": 1500, "color": (255, 0, 255)},
    5: {"name": "FALLEN TREE", "action": "Chainsaw Crew", "base_cost": 1200, "color": (50, 205, 50)},
    6: {"name": "BROKEN FOOTPATH", "action": "Paver Slabs", "base_cost": 550, "color": (255, 165, 0)},
}

valid_tokens = set()
state_lock = threading.Lock()
latest_jpg = None
arduino_ser = None
stop_event = threading.Event()

telemetry_state = {
    "node_id": "NODE-01",
    "lat": INDOOR_BASE_LAT,
    "lng": INDOOR_BASE_LNG,
    "battery": 96,
    "npu_temp_c": 45.0,
    "fps": 0.0,
    "detections": [],
}

rover_active = False
is_paused_for_audit = False
gps_has_fix = False
start_time = time.time()


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_temp_c():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return round(int(f.read().strip()) / 1000.0, 1)
    except Exception:
        return 45.0


def send_arduino(cmd: str):
    global arduino_ser
    if arduino_ser and arduino_ser.is_open:
        try:
            arduino_ser.write((cmd + "\n").encode())
        except Exception:
            pass


def nmea_to_decimal(raw_val: str, direction: str):
    if not raw_val or "." not in raw_val:
        return None
    dot = raw_val.index(".")
    deg_len = dot - 2
    deg = float(raw_val[:deg_len])
    mins = float(raw_val[deg_len:])
    val = deg + (mins / 60.0)
    if direction in ("S", "W"):
        val = -val
    return round(val, 6)


def arduino_thread():
    global arduino_ser, rover_active
    try:
        arduino_ser = serial.Serial(ARDUINO_PORT, 9600, timeout=0.5)
        time.sleep(2.2)
        ip = get_local_ip()
        send_arduino(f"IP:{ip}")
        print(f"[INFO] Arduino connected on {ARDUINO_PORT} | Sent IP:{ip}")
    except Exception as e:
        print(f"[WARN] Arduino not connected on {ARDUINO_PORT} ({e}).")
        return

    last_ip_push = time.time()
    while not stop_event.is_set():
        try:
            if arduino_ser.in_waiting > 0:
                line = arduino_ser.readline().decode(errors="ignore").strip()
                if line == "START":
                    rover_active = True
                    print("[INFO] Button pressed -> ROVER PATROL STARTED")
                elif line == "STOP":
                    rover_active = False
                    print("[INFO] Button pressed -> ROVER STOPPED")
            if not rover_active and (time.time() - last_ip_push > 5.0):
                send_arduino(f"IP:{get_local_ip()}")
                last_ip_push = time.time()
        except Exception:
            pass
        time.sleep(0.05)


def gps_thread():
    global gps_has_fix
    gps_ser = None
    try:
        gps_ser = serial.Serial(GPS_PORT, 9600, timeout=1)
        print(f"[INFO] GPS connected on {GPS_PORT}")
    except Exception as e:
        print(f"[WARN] GPS not found on {GPS_PORT} ({e}). Using indoor dead-reckoning.")

    sim_lat, sim_lng = INDOOR_BASE_LAT, INDOOR_BASE_LNG
    last_step = time.time()

    while not stop_event.is_set():
        got_fix = False
        if gps_ser and gps_ser.is_open:
            try:
                line = gps_ser.readline().decode(errors="ignore").strip()
                if line.startswith("$GPGGA") or line.startswith("$GNGGA"):
                    parts = line.split(",")
                    if len(parts) > 6 and parts[6] in ("1", "2"):
                        lat = nmea_to_decimal(parts[2], parts[3])
                        lng = nmea_to_decimal(parts[4], parts[5])
                        if lat and lng:
                            with state_lock:
                                telemetry_state["lat"] = lat
                                telemetry_state["lng"] = lng
                            gps_has_fix = True
                            got_fix = True
            except Exception:
                pass

        if not got_fix and (time.time() - last_step >= 1.0):
            last_step = time.time()
            if rover_active and not is_paused_for_audit:
                sim_lat = round(sim_lat + 0.000018, 6)
                sim_lng = round(sim_lng + 0.000006, 6)
            if not gps_has_fix:
                with state_lock:
                    telemetry_state["lat"] = sim_lat
                    telemetry_state["lng"] = sim_lng
        if not gps_ser:
            time.sleep(0.2)


def hailo_camera_thread():
    global latest_jpg, is_paused_for_audit

    os.makedirs("audit_records", exist_ok=True)
    csv_path = "audit_records/civicsense_work_orders.csv"
    file_exists = os.path.isfile(csv_path)
    csv_file = open(csv_path, "a", newline="")
    csv_writer = csv.writer(csv_file)
    if not file_exists:
        csv_writer.writerow(["Defect_ID", "Timestamp", "Lat", "Lng", "Hazard", "Action", "Cost_INR", "Confidence"])
        csv_file.flush()

    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={"size": (640, 640), "format": "RGB888"},
        controls={"AfMode": 2}
    )
    picam2.configure(config)
    picam2.start()
    print("[INFO] Pi Cam 3 active.")

    hef = HEF(HEF_PATH)
    defect_counter = 0
    last_detection_time = 0.0
    pause_start_time = 0.0
    fps_counter = 0
    fps_timer = time.time()

    with VDevice() as target:
        configure_params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
        network_group = target.configure(hef, configure_params)[0]
        network_group_params = network_group.create_params()

        input_vstream_info = hef.get_input_vstream_infos()[0]
        output_vstream_info = hef.get_output_vstream_infos()[0]
        input_params = InputVStreamParams.make_from_network_group(network_group, quantized=True, format_type=FormatType.UINT8)
        output_params = OutputVStreamParams.make_from_network_group(network_group, quantized=False, format_type=FormatType.FLOAT32)

        print("[INFO] Hailo-8L NPU active!")
        with InferVStreams(network_group, input_params, output_params) as infer_pipeline:
            with network_group.activate(network_group_params):
                while not stop_event.is_set():
                    frame = picam2.capture_array()
                    rgb_input = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    raw_results = infer_pipeline.infer({input_vstream_info.name: np.expand_dims(rgb_input, axis=0)})
                    detections_by_class = raw_results[output_vstream_info.name][0]

                    now = time.time()
                    if is_paused_for_audit and (now - pause_start_time > 3.5):
                        is_paused_for_audit = False
                        if rover_active:
                            send_arduino("F")

                    frame_detections = []
                    for cls_id, dets in enumerate(detections_by_class):
                        if cls_id == 4:
                            continue
                        for det in dets:
                            ymin, xmin, ymax, xmax, conf = det
                            if conf < 0.40:
                                continue
                            x1, y1 = int(xmin * 640), int(ymin * 640)
                            x2, y2 = int(xmax * 640), int(ymax * 640)
                            area = max(0, (x2 - x1) * (y2 - y1))

                            meta = HAZARD_META.get(cls_id, {"name": f"CLASS_{cls_id}", "action": "Inspect", "base_cost": 500, "color": (255, 255, 255)})
                            cost = meta["base_cost"] + int(area * 0.005)
                            color = meta["color"]

                            frame_detections.append({
                                "class": meta["name"],
                                "confidence": round(float(conf), 2),
                                "action": meta["action"],
                                "cost_inr": cost,
                                "bbox": [x1, y1, x2, y2],
                            })

                            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                            cv2.putText(frame, f"{meta['name']} ({conf:.2f})", (x1, max(25, y1 - 25)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                            cv2.putText(frame, f"{meta['action']} | Rs.{cost}", (x1, max(45, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

                            if rover_active and not is_paused_for_audit and (now - last_detection_time > 4.0):
                                defect_counter += 1
                                last_detection_time = now
                                is_paused_for_audit = True
                                pause_start_time = now

                                send_arduino(f"ALERT:{meta['name']}|{meta['action']}|{cost}")
                                cv2.imwrite(f"audit_records/defect_{defect_counter}_{int(now)}.jpg", frame)
                                with state_lock:
                                    lat, lng = telemetry_state["lat"], telemetry_state["lng"]
                                csv_writer.writerow([f"DEF-{defect_counter:03d}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), lat, lng, meta["name"], meta["action"], cost, f"{conf:.2f}"])
                                csv_file.flush()
                                print(f"[LOGGED] DEF-{defect_counter:03d}: {meta['name']} | Rs.{cost} @ {lat},{lng}")

                    fps_counter += 1
                    if now - fps_timer >= 1.0:
                        elapsed_mins = (now - start_time) / 60.0
                        with state_lock:
                            telemetry_state["fps"] = round(fps_counter / (now - fps_timer), 1)
                            telemetry_state["npu_temp_c"] = get_temp_c()
                            telemetry_state["battery"] = max(15, int(98 - elapsed_mins * 0.4))
                        fps_counter = 0
                        fps_timer = now

                    with state_lock:
                        telemetry_state["detections"] = frame_detections
                        cur_fps = telemetry_state["fps"]

                    status_txt = "BRAKED & AUDITING" if is_paused_for_audit else ("AUTO-PATROL" if rover_active else "STANDBY (PRESS BTN)")
                    status_col = (0, 0, 255) if is_paused_for_audit else ((0, 255, 0) if rover_active else (0, 255, 255))
                    cv2.rectangle(frame, (0, 0), (640, 35), (20, 20, 20), -1)
                    cv2.putText(frame, f"CIVICEYE 360 | {status_txt} | {cur_fps} FPS", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.52, status_col, 2)

                    _, jpg_buf = cv2.imencode(".jpg", frame)
                    with state_lock:
                        latest_jpg = jpg_buf.tobytes()

    picam2.stop()
    csv_file.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=arduino_thread, daemon=True).start()
    threading.Thread(target=gps_thread, daemon=True).start()
    threading.Thread(target=hailo_camera_thread, daemon=True).start()
    yield
    stop_event.set()
    send_arduino("S")


app = FastAPI(title="CivicEye 360 Edge Node", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/session")
async def create_session(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid x-api-key")
    token = secrets.token_urlsafe(24)
    valid_tokens.add(token)
    return {"token": token}


@app.get("/video_feed")
async def video_feed(token: str = Query(...)):
    if token not in valid_tokens:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    async def mjpeg_generator():
        while True:
            with state_lock:
                jpg = latest_jpg
            if jpg is not None:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
            await asyncio.sleep(0.033)

    return StreamingResponse(mjpeg_generator(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.websocket("/ws/telemetry")
async def ws_telemetry(websocket: WebSocket, token: str = Query(...)):
    if token not in valid_tokens:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try:
        while True:
            with state_lock:
                payload = dict(telemetry_state)
            await websocket.send_json(payload)
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        pass
