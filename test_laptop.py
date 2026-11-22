import cv2
import time
import os
import csv
from datetime import datetime
from ultralytics import YOLO

# 1. Load your newly trained model
model_path = "runs/detect/civicsense_model-3/weights/best.pt"
print(f"[INFO] Loading trained weights from: {model_path}")
model = YOLO(model_path)

# 2. Municipal Class Metadata (Action & Cost Formulas)
hazard_meta = {
    0: {"name": "POTHOLE", "action": "Cold-Mix Asphalt Patch", "base_cost": 250, "color": (0, 0, 255)},        # Red
    1: {"name": "GARBAGE DUMP", "action": "SWM Compactor Clearance", "base_cost": 450, "color": (0, 140, 255)}, # Orange
    2: {"name": "OPEN MANHOLE", "action": "RCC Cover Replacement", "base_cost": 2500, "color": (0, 0, 200)},    # Deep Red
    3: {"name": "DANGLING CABLE", "action": "Cable Elevation & Clip", "base_cost": 450, "color": (0, 255, 255)}, # Yellow
    4: {"name": "ILLEGAL HOARDING", "action": "Enforcement Fine & Demolish", "base_cost": 1500, "color": (255, 0, 255)}, # Magenta
    5: {"name": "FALLEN TREE", "action": "Forest Cell Chainsaw Crew", "base_cost": 1200, "color": (50, 205, 50)}, # Lime Green
    6: {"name": "BROKEN FOOTPATH", "action": "Concrete Paver Slabs", "base_cost": 550, "color": (255, 165, 0)}  # Cyan/Blue
}

os.makedirs("test_snapshots", exist_ok=True)
cap = cv2.VideoCapture(0)
last_log_time = 0

print("\n" + "="*50)
print("[INFO] Webcam active! Hold up a photo of a hazard from your phone.")
print("Press 'q' to quit.")
print("="*50)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Run detection on your RTX 3050
    results = model(frame, conf=0.35, device=0, verbose=False)

    oled_text_lines = ["CIVICSENSE 360", "STATUS: SCANNING...", "DEFECTS: NONE", "EST. COST: Rs. 0"]

    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            area = (x2 - x1) * (y2 - y1)

            meta = hazard_meta.get(cls_id, {"name": f"CLASS_{cls_id}", "action": "Inspect Site", "base_cost": 500, "color": (255, 255, 255)})
            calculated_cost = meta["base_cost"] + int(area * 0.005)
            color = meta["color"]

            # Draw visual bounding box & HUD label
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
            label = f"{meta['name']} ({conf:.2f})"
            sub_label = f"Action: {meta['action']} | Rs.{calculated_cost}"
            
            cv2.putText(frame, label, (x1, max(25, y1 - 25)), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
            cv2.putText(frame, sub_label, (x1, max(45, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

            # Virtual 0.96" OLED Preview
            oled_text_lines = [
                "CIVICSENSE 360 [AUDIT]",
                f"HAZARD: {meta['name'][:14]}",
                f"ACT: {meta['action'][:18]}",
                f"EST. COST: Rs. {calculated_cost}"
            ]

            if conf > 0.50 and (time.time() - last_log_time > 3.0):
                last_log_time = time.time()
                cv2.imwrite(f"test_snapshots/audit_{int(time.time())}.jpg", frame)
                print(f"[LOGGED] {meta['name']} | Action: {meta['action']} | Est. Cost: Rs.{calculated_cost}")

    # Top Status Banner
    cv2.rectangle(frame, (0, 0), (640, 35), (20, 20, 20), -1)
    cv2.putText(frame, "CIVICSENSE 360 | LAPTOP TEST BENCH | RTX 3050", 
                (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

    # Virtual Onboard 0.96" OLED Box (Bottom-Right)
    cv2.rectangle(frame, (430, 360), (630, 470), (0, 0, 0), -1)
    cv2.rectangle(frame, (430, 360), (630, 470), (255, 255, 255), 1)
    cv2.putText(frame, "ONBOARD OLED PREVIEW", (435, 375), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
    for i, line in enumerate(oled_text_lines):
        cv2.putText(frame, line, (435, 395 + (i * 18)), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255) if i == 0 else (255, 255, 255), 1)

    cv2.imshow("CivicSense 360 - Live Demo Preview", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
