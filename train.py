from ultralytics import YOLO
import os

# 1. Path to your merged dataset configuration
data_yaml_path = os.path.abspath("civicsense_dataset/data.yaml")

print(f"[INFO] Using dataset: {data_yaml_path}")
print("[INFO] Initializing YOLOv8 Nano on RTX 3050...")

# 2. Load base YOLOv8 Nano architecture (optimized for Hailo-8L)
model = YOLO("yolov8n.pt")

# 3. Train with GPU acceleration
results = model.train(
    data=data_yaml_path,
    epochs=35,             # 35 epochs gives great accuracy while training quickly
    imgsz=640,
    batch=16,              # Fits comfortably in your 4GB VRAM
    device=0,              # Forces your RTX 3050 GPU
    workers=4,
    name="civicsense_model",
    save=True
)

print("\n" + "="*50)
print("[SUCCESS] Training complete!")
print("Trained weights saved to: runs/detect/civicsense_model/weights/best.pt")
print("="*50)
