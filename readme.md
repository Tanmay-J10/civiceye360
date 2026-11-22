# CivicEye 360 — Modular Edge AI Pod & Autonomous Civic Auditing Rover

**CivicEye 360** is a real-time Edge AI road and streetscape auditing system built for the **Changemakers Challenge**. Powered by a **Raspberry Pi 5**, a **Hailo-8L neural accelerator (13 TOPS)**, and a **Pi Camera Module 3**, it detects urban infrastructure hazards at 30+ FPS, calculates municipal repair remedies and costs (in ₹), geotags every incident via GPS, and streams live video and telemetry to a web command dashboard.

<img width="1600" height="1000" alt="WhatsApp Image 2026-11-22 at 1 17 26 PM" src="https://github.com/user-attachments/assets/f4e5f26b-5504-445d-96a3-593cdb9c4af1" />
## Defect Output saved in csv
<img width="640" height="640" alt="WhatsApp Image 2026-11-22 at 1 17 55 PM" src="https://github.com/user-attachments/assets/e9cce651-d7dc-4d46-b644-d147db6bb3e5" />
## Manhole , Pothole, Illegal Hoardings , Dangling Cable , Fallen Tree Dectection
<img width="640" height="640" alt="WhatsApp Image 2026-11-22 at 1 18 02 PM" src="https://github.com/user-attachments/assets/b3d3ade5-67b7-4912-830c-bdc8f434e1f1" />

<img width="640" height="640" alt="WhatsApp Image 2026-11-22 at 1 18 41 PM" src="https://github.com/user-attachments/assets/f5167530-d1a6-4920-b3da-403b40822c24" />

## The Proof-of-Concept: Detachable Edge AI Pod
##
**While the 4WD rover demonstrates autonomous closed-loop inspection on footpaths, campuses, and narrow lanes**, it serves as a **proof of concept for a detachable, vehicle-agnostic Edge AI Pod**. The top compute unit (Pi 5 + Hailo-8L + Camera + GPS) is designed to unclip and mount directly onto existing municipal fleets—such as garbage trucks, city buses, and patrol vehicles—to passively audit entire cities like Bengaluru every morning at a fraction of the cost of ₹50 Lakh+ laser-scanning vans.
<img width="1200" height="1600" alt="WhatsApp Image 2026-11-22 at 1 30 18 PM" src="https://github.com/user-attachments/assets/e80c5cc2-20fb-47f0-a2c1-59375d207556" />
<img width="1600" height="1200" alt="WhatsApp Image 2026-11-22 at 1 30 17 PM" src="https://github.com/user-attachments/assets/a6da8d59-b428-4e7e-86b0-b1f3152c3d68" />

## Web Interface

<img width="2880" height="1623" alt="{1053F2C5-AC51-4251-88E1-3B052BEAC45E}" src="https://github.com/user-attachments/assets/c9ab5339-6c09-492d-80cb-3a34dc72d4fa" />
<img width="2293" height="1493" alt="{A7456D22-6CBC-47F0-9927-A786E74BAF08}" src="https://github.com/user-attachments/assets/94a053a9-0e84-4a75-9227-6c2fdda043a4" />
<img width="2880" height="1622" alt="{0E12E035-B319-4E5F-BCC8-A51166E0ED85}" src="https://github.com/user-attachments/assets/06227fc7-c673-40ca-8b7c-9cf1d764c6f6" />

## Final Ai Pod preview 
<img width="2880" height="1618" alt="image" src="https://github.com/user-attachments/assets/6a48f855-704c-4ab3-b433-2c7e82c1dd61" />
<img width="2880" height="1632" alt="{7054A6A9-7DF0-41CE-AA22-F5D235C270BB}" src="https://github.com/user-attachments/assets/79ddc155-2a95-433d-9d01-8e6b604612f7" />

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
