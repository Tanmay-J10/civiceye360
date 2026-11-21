# CivicEye 360 — Modular Edge AI Pod & Autonomous Civic Auditing Rover

**CivicEye 360** is a real-time Edge AI road and streetscape auditing system built for the **Changemakers Challenge**. Powered by a **Raspberry Pi 5**, a **Hailo-8L neural accelerator (13 TOPS)**, and a **Pi Camera Module 3**, it detects urban infrastructure hazards at 30+ FPS, calculates municipal repair remedies and costs (in ₹), geotags every incident via GPS, and streams live video and telemetry to a web command dashboard.

## The Proof-of-Concept: Detachable Edge AI Pod
While the 4WD rover demonstrates autonomous closed-loop inspection on footpaths, campuses, and narrow lanes, it serves as a **proof of concept for a detachable, vehicle-agnostic Edge AI Pod**. The top compute unit (Pi 5 + Hailo-8L + Camera + GPS) is designed to unclip and mount directly onto existing municipal fleets—such as garbage trucks, city buses, and patrol vehicles—to passively audit entire cities like Bengaluru every morning at a fraction of the cost of ₹50 Lakh+ laser-scanning vans.

## Key Features
* **30+ FPS Local Edge Inference**: Runs a custom-trained 7-class **YOLOv8n** model compiled to INT8 (`.hef`) on the Hailo-8L NPU with zero cloud latency.
* **Automated Repair Cost & Remedy Quantification**: Estimates repair actions and budgets (in ₹) from bounding-box geometry across 7 hazard classes: `pothole`, `garbage_dump`, `open_manhole`, `dangling_cable`, `illegal_hoarding`, `fallen_tree`, and `broken_footpath`.
* **Closed-Loop Auto-Brake & Onboard OLED**: Signals an **Arduino UNO R4** over USB to halt the rover over detected defects, capture an evidence snapshot + CSV work order, and display live hazard metrics on a **0.96" I2C OLED** (showing the Pi's IP address on standby until the physical start button is pressed).
* **Hybrid GNSS + Dead-Reckoning**: Reads live NMEA coordinates from a **NEO-6M GPS** over FTDI UART, with automatic dead-reckoning fallback when satellite signals drop inside concrete halls, tunnels, or underpasses.
* **Authenticated Live Dashboard API**: FastAPI + Uvicorn server exposing token-authenticated MJPEG video and 1 Hz WebSocket telemetry (compatible with local Wi-Fi or Cloudflare Tunnel for HTTPS/WSS).

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

## Quick Start (Raspberry Pi 5)
1. Flash `arduino/civiceye_rover.ino` to the Arduino UNO R4 and connect it to the Pi via USB (`/dev/ttyACM0`).
2. Install dependencies on Raspberry Pi OS (Bookworm 64-bit) with `hailo-all` installed:
   ```bash
   pip install -r requirements.txt --break-system-packages
## Quick Start [Management Hub/Any server (Windows/Linux)]
1.Launch the edge server:
export CIVICEYE_API_KEY="civiceye-2026"
uvicorn server:app --host 0.0.0.0 --port 8000

## Future Expansion Beyond Civil Infrastructure
Because the Edge AI Pod is modular and hardware-accelerated, expanding into other sectors requires only swapping the compiled .hef neural model—with no hardware redesign:

Medical & Healthcare: Contactless biomedical waste and sharps triage to protect frontline sanitation staff, plus automated hospital corridor spill/obstacle alerts.

Precision Agriculture: Real-time crop blight, pest, and irrigation stress mapping for farms and urban terrace gardens.

Industrial & Facility Safety: Confined-space HVAC duct inspection, electrical cable hazard monitoring, and solar panel micro-defect detection.
