# CivicEye 360 — Modular Edge AI Pod & Autonomous Civic Auditing Rover

![Raspberry Pi](https://img.shields.io/badge/-Raspberry_Pi_5-C51A4A?style=for-the-badge&logo=Raspberry-Pi)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![YOLOv8](https://img.shields.io/badge/YOLOv8-00FFFF?style=for-the-badge&logo=YOLO)
![Arduino](https://img.shields.io/badge/-Arduino-00979D?style=for-the-badge&logo=Arduino&logoColor=white)

**CivicEye 360** is a real-time Edge AI road and streetscape auditing system built for the **Changemakers Challenge**. Powered by a **Raspberry Pi 5**, a **Hailo-8L neural accelerator (13 TOPS)**, and a **Pi Camera Module 3**, it detects urban infrastructure hazards at 30+ FPS, calculates municipal repair remedies and costs (in ₹), geotags every incident via GPS, and streams live video and telemetry to a web command dashboard.

<p align="center">
  <img width="850" alt="CivicEye 360 System Overview" src="https://github.com/user-attachments/assets/f4e5f26b-5504-445d-96a3-593cdb9c4af1" />
</p>

## The Problem & Solution

**The Problem**
Urban hubs like Bengaluru lose crores every year—and thousands of lives—to unrecorded road and streetscape hazards such as potholes, open manholes, broken footpaths, illegal garbage dumps, and dangling cables.
* **Manual surveys** are slow, inconsistent, and unsafe for workers.
* **Commercial laser-scanning vans** cost over ₹50 Lakhs and cannot enter narrow lanes or pedestrian walkways.

**The CivicEye 360 Solution**
A low-cost, automated Edge AI system that inspects roads and footpaths in real time without cloud latency.
* **Closed-Loop Action:** Brakes the rover upon spotting a defect, captures an evidence snapshot, and generates a CSV work order.
* **Automated Costing:** Estimates the required municipal repair remedy and budget (in ₹) from bounding-box geometry.
* **Live Telemetry:** Streams authenticated video and GPS coordinates to a central command dashboard.

## The Proof-of-Concept: Detachable Edge AI Pod

While the 4WD rover demonstrates autonomous closed-loop inspection on footpaths, campuses, and narrow lanes, it serves as a **proof of concept for a detachable, vehicle-agnostic Edge AI Pod**. 

*Crucially, the 4WD rover is a proof of concept for a detachable, vehicle-agnostic Edge AI Pod.

*While the ground rover demonstrates autonomous inspection on footpaths, campuses, and narrow alleys, the top compute pod (Pi 5, Hailo-8L, camera, and GPS) is engineered to unclip and mount directly onto existing municipal fleets—such as garbage trucks, city buses, or patrol vans—turning daily city vehicles into passive, citywide infrastructure auditors at a fraction of traditional costs.

*Because the pod is completely modular and hardware-accelerated, scaling beyond civil infrastructure requires only swapping the compiled .hef neural model—no hardware redesign needed. 

*Future plans include deploying the same AI Pod in healthcare and medical facilities for contactless biomedical waste and sharps triage or hospital corridor spill detection; in precision agriculture for real-time crop blight and pest mapping; and in industrial facilities for automated electrical cable, fire-hazard, and confined-space HVAC duct inspections.

**Hardware Prototype**
<p align="center">
  <img height="340" alt="Pod View 1" src="https://github.com/user-attachments/assets/e80c5cc2-20fb-47f0-a2c1-59375d207556" />
  &nbsp;&nbsp;
  <img height="340" alt="Pod View 2" src="https://github.com/user-attachments/assets/a6da8d59-b428-4e7e-86b0-b1f3152c3d68" />
</p>

**Final AI Pod Preview**
<p align="center">
  <img width="48%" alt="Final AI Pod Preview 1" src="https://github.com/user-attachments/assets/6a48f855-704c-4ab3-b433-2c7e82c1dd61" />
  &nbsp;
  <img width="48%" alt="Final AI Pod Preview 2" src="https://github.com/user-attachments/assets/79ddc155-2a95-433d-9d01-8e6b604612f7" />
</p>

## Key Features

* **30+ FPS Local Edge Inference:** Runs a custom-trained 7-class **YOLOv8n** model compiled to INT8 (`.hef`) on the Hailo-8L NPU with zero cloud latency.
* **Automated Repair Cost & Remedy Quantification:** Estimates repair actions and budgets (in ₹) from bounding-box geometry across 7 hazard classes: `pothole`, `garbage_dump`, `open_manhole`, `dangling_cable`, `illegal_hoarding`, `fallen_tree`, and `broken_footpath`.
* **Closed-Loop Auto-Brake & Onboard OLED:** Signals an **Arduino UNO R4** over USB to halt the rover over detected defects, capture an evidence snapshot and CSV work order, and display live hazard metrics on a **0.96" I2C OLED** (showing the Pi's IP address on standby until the physical start button is pressed).
* **Hybrid GNSS + Dead-Reckoning:** Reads live NMEA coordinates from a **NEO-6M GPS** over FTDI UART, with automatic dead-reckoning fallback when satellite signals drop inside concrete halls, tunnels, or underpasses.
* **Authenticated Live Dashboard API:** FastAPI + Uvicorn server exposing token-authenticated MJPEG video and 1 Hz WebSocket telemetry (compatible with local Wi-Fi or Cloudflare Tunnel for HTTPS/WSS).

## Detection & Web Interface

**Multi-Class Hazard Detection & CSV Output**
Detects manholes, potholes, illegal hoardings, dangling cables, and fallen trees, logging each defect directly to CSV.

<p align="center">
  <img width="31%" alt="Hazard Detection 1" src="https://github.com/user-attachments/assets/b3d3ade5-67b7-4912-830c-bdc8f434e1f1" />
  &nbsp;
  <img width="31%" alt="Hazard Detection 2" src="https://github.com/user-attachments/assets/f5167530-d1a6-4920-b3da-403b40822c24" />
  &nbsp;
  <img width="31%" alt="CSV Defect Output" src="https://github.com/user-attachments/assets/e9cce651-d7dc-4d46-b644-d147db6bb3e5" />
</p>

**Web Command Dashboard**

<p align="center">
  <img width="96%" alt="Web Interface Main" src="https://github.com/user-attachments/assets/c9ab5339-6c09-492d-80cb-3a34dc72d4fa" />
</p>
<p align="center">
  <img width="47%" alt="Web Interface 2" src="https://github.com/user-attachments/assets/94a053a9-0e84-4a75-9227-6c2fdda043a4" />
  &nbsp;
  <img width="47%" alt="Web Interface 3" src="https://github.com/user-attachments/assets/06227fc7-c673-40ca-8b7c-9cf1d764c6f6" />
</p>

## Hardware Architecture

| Subsystem | Components & Connections |
| :--- | :--- |
| **Edge AI Compute Pod** | Raspberry Pi 5 + Hailo-8L AI HAT + Pi Camera Module 3 (`imx708`) |
| **Motor & Telemetry Controller** | Arduino UNO R4 + L298N (`ENA=6`, `ENB=5`, `IN1=7`, `IN2=8`, `IN3=3`, `IN4=4`) |
| **UI & Controls** | 0.96" SSD1306 I2C OLED (`SDA=A4`, `SCL=A5`) + Push-Button Start (`D2` to `GND`) |
| **Localization** | NEO-6M GPS Module connected via FTDI USB-to-UART (`/dev/ttyUSB0`) |
| **Power & Networking** | 11.1V 3000mAh Li-ion + XL4016 Buck Converter (`5.15V` to Pi) + 4G Wi-Fi Hotspot |

## API Endpoints

* `POST /session` — Validates `x-api-key` header against `CIVICEYE_API_KEY` and returns `{"token": "..."}`.
* `GET /video_feed?token=<token>` — Streams annotated Hailo-8L frames as MJPEG (`multipart/x-mixed-replace; boundary=frame`).
* `WS /ws/telemetry?token=<token>` — Pushes 1 Hz JSON telemetry: `node_id`, `lat`, `lng`, `battery`, `npu_temp_c`, `fps`, and `detections`.

## Quick Start

**1. Raspberry Pi 5 Setup**
Flash `arduino/civiceye_rover.ino` to the Arduino UNO R4 and connect it to the Pi via USB (`/dev/ttyACM0`). Install dependencies on Raspberry Pi OS (Bookworm 64-bit) with `hailo-all` installed:

```bash
pip install -r requirements.txt --break-system-packages
```

**2. Management Hub / Edge Server (Windows/Linux)**
Launch the FastAPI server to stream video and telemetry:

```bash
export CIVICEYE_API_KEY="civiceye-2026"
uvicorn server:app --host 0.0.0.0 --port 8000
```

## Future Expansion Beyond Civil Infrastructure

Because the Edge AI Pod is modular and hardware-accelerated, expanding into other sectors requires only swapping the compiled `.hef` neural model—with no hardware redesign required:

* **Medical & Healthcare:** Contactless biomedical waste and sharps triage to protect frontline sanitation staff, plus automated hospital corridor spill and obstacle alerts.
* **Precision Agriculture:** Real-time crop blight, pest, and irrigation stress mapping for farms and urban terrace gardens.
* **Industrial & Facility Safety:** Confined-space HVAC duct inspection, electrical cable hazard monitoring, and solar panel micro-defect detection.
