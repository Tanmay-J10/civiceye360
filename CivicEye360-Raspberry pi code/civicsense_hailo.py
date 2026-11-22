import cv2
import time
import os
import csv
import threading
import serial
import numpy as np
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from picamera2 import Picamera2
from hailo_platform import (
    VDevice, HEF, ConfigureParams, HailoStreamInterface,
    InferVStreams, InputVStreamParams, OutputVStreamParams, FormatType
)

# 1. Arduino Uno R3 Serial Link (Optional Bench Fallback)
try:
    arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    time.sleep(2)
    print("[INFO] Arduino R3 linked on /dev/ttyACM0")
except Exception as e:
    print(f"[WARN] Arduino not connected ({e}). Running in camera-only mode.")
    arduino = None

def send_arduino(cmd):
    if arduino and arduino.is_open:
        arduino.write((cmd + "\n").encode())

# 2. Municipal Hazard Metadata
hazard_meta = {
    0: {"name": "POTHOLE", "action": "Cold-Mix Asphalt", "base_cost": 250, "color": (0, 0, 255)},
    1: {"name": "GARBAGE DUMP", "action": "SWM Compactor", "base_cost": 450, "color": (0, 140, 255)},
    2: {"name": "OPEN MANHOLE", "action": "RCC Cover Replace", "base_cost": 2500, "color": (0, 0, 200)},
    3: {"name": "DANGLING CABLE", "action": "Cable Elevation", "base_cost": 450, "color": (0, 255, 255)},
    4: {"name": "ILLEGAL HOARDING", "action": "Fine & Demolish", "base_cost": 1500, "color": (255, 0, 255)},
    5: {"name": "FALLEN TREE", "action": "Chainsaw Crew", "base_cost": 1200, "color": (50, 205, 50)},
    6: {"name": "BROKEN FOOTPATH", "action": "Paver Slabs", "base_cost": 550, "color": (255, 165, 0)}
}

# 3. CSV Work-Order Logger
os.makedirs("audit_records", exist_ok=True)
csv_path = "audit_records/civicsense_work_orders.csv"
file_exists = os.path.isfile(csv_path)
csv_file = open(csv_path, "a", newline="")
csv_writer = csv.writer(csv_file)
if not file_exists:
    csv_writer.writerow(["Defect_ID", "Timestamp", "Hazard", "Action", "Cost_INR", "Confidence"])
    csv_file.flush()

# 4. MJPEG Web Stream Server (Port 8080)
latest_jpg = None
frame_lock = threading.Lock()

class StreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
        self.end_headers()
        while True:
            with frame_lock:
                jpg = latest_jpg
            if jpg is not None:
                try:
                    self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpg + b'\r\n')
                except BrokenPipeError:
                    break
            time.sleep(0.03)
    def log_message(self, format, *args):
        pass  # Keep terminal clean

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', 8080), StreamHandler).serve_forever(), daemon=True).start()
print("[INFO] Live HUD stream active at http://<YOUR_PI_IP>:8080")

# 5. Initialize Pi Cam 3 (640x640 + Continuous Autofocus)
picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"size": (640, 640), "format": "RGB888"},
    controls={"AfMode": 2}
)
picam2.configure(config)
picam2.start()
print("[INFO] Pi Cam 3 started with Continuous Autofocus.")

# 6. Load Hailo-8L Model
hef = HEF("yolov8n.hef")
defect_counter = 0
last_detection_time = 0
is_paused_for_audit = False
pause_start_time = 0

send_arduino("F")

with VDevice() as target:
    configure_params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
    network_group = target.configure(hef, configure_params)[0]
    network_group_params = network_group.create_params()

    input_vstream_info = hef.get_input_vstream_infos()[0]
    output_vstream_info = hef.get_output_vstream_infos()[0]

    input_params = InputVStreamParams.make_from_network_group(network_group, quantized=True, format_type=FormatType.UINT8)
    output_params = OutputVStreamParams.make_from_network_group(network_group, quantized=False, format_type=FormatType.FLOAT32)

    print("[INFO] Hailo-8L NPU active! Running real-time inference...")

    with InferVStreams(network_group, input_params, output_params) as infer_pipeline:
        with network_group.activate(network_group_params):
            try:
                while True:
                    # Picamera2 'RGB888' returns BGR in memory for OpenCV
                    frame = picam2.capture_array()
                    rgb_input = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    input_data = {input_vstream_info.name: np.expand_dims(rgb_input, axis=0)}

                    # Run Hardware Inference on Hailo-8L
                    raw_results = infer_pipeline.infer(input_data)
                    detections_by_class = raw_results[output_vstream_info.name][0]

                    current_time = time.time()
                    if is_paused_for_audit and (current_time - pause_start_time > 3.5):
                        is_paused_for_audit = False
                        send_arduino("F")

                    for cls_id, dets in enumerate(detections_by_class):
                        if cls_id == 4:  # Ignore Class 4 (illegal_hoarding)
                            continue
                        for det in dets:
                            ymin, xmin, ymax, xmax, conf = det
                            if conf < 0.40:
                                continue

                            x1, y1 = int(xmin * 640), int(ymin * 640)
                            x2, y2 = int(xmax * 640), int(ymax * 640)
                            area = max(0, (x2 - x1) * (y2 - y1))

                            meta = hazard_meta.get(cls_id, {"name": f"CLASS_{cls_id}", "action": "Inspect", "base_cost": 500, "color": (255, 255, 255)})
                            cost = meta["base_cost"] + int(area * 0.005)
                            color = meta["color"]

                            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                            cv2.putText(frame, f"{meta['name']} ({conf:.2f})", (x1, max(25, y1 - 25)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                            cv2.putText(frame, f"{meta['action']} | Rs.{cost}", (x1, max(45, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

                            if not is_paused_for_audit and (current_time - last_detection_time > 4.0):
                                defect_counter += 1
                                last_detection_time = current_time
                                is_paused_for_audit = True
                                pause_start_time = current_time

                                send_arduino(f"ALERT:{meta['name']}|{meta['action']}|{cost}")
                                cv2.imwrite(f"audit_records/defect_{defect_counter}_{int(current_time)}.jpg", frame)
                                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                csv_writer.writerow([f"DEF-{defect_counter:03d}", now_str, meta["name"], meta["action"], cost, f"{conf:.2f}"])
                                csv_file.flush()
                                print(f"[LOGGED] DEF-{defect_counter:03d}: {meta['name']} | Rs.{cost}")

                    # Top Status Banner
                    status_text = "STATUS: BRAKED & AUDITING" if is_paused_for_audit else "STATUS: HAILO-8L PATROL"
                    status_color = (0, 0, 255) if is_paused_for_audit else (0, 255, 0)
                    cv2.rectangle(frame, (0, 0), (640, 35), (20, 20, 20), -1)
                    cv2.putText(frame, f"CIVICEYE 360 | {status_text} | LOGGED: {defect_counter}", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.52, status_color, 2)

                    _, jpg_buf = cv2.imencode('.jpg', frame)
                    with frame_lock:
                        latest_jpg = jpg_buf.tobytes()

            except KeyboardInterrupt:
                print("\n[INFO] Shutting down CivicEye 360...")

send_arduino("S")
picam2.stop()
csv_file.close()
if arduino:
    arduino.close()
