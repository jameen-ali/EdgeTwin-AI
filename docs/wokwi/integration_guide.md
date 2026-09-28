# EdgeTwin AI — Wokwi ↔ Backend Integration Guide & Verification Checklist

## 1. Overview & Architecture

EdgeTwin AI integrates a physical/emulated edge tier running on an ESP32 microcontroller with a central AI predictive maintenance backend. The edge firmware adheres strictly to the canonical `edgetwin.telemetry.v1` contract.

```
+---------------------------------------------------------------------------------+
|                                 EDGE LAYER                                      |
|                                                                                 |
|   +-------------------------------------------------------------------------+   |
|   |                       ESP32 DevKit v1 (Wokwi)                           |   |
|   |                                                                         |   |
|   |   +-------------------+  +-------------------+  +-------------------+   |   |
|   |   |   DHT22 (Air T)   |  | Potentiometer (T) |  |   MPU6050 (Vib)   |   |   |
|   |   |      GPIO 15      |  |   GPIO 34 (ADC)   |  |   I2C (SDA21/22)  |   |   |
|   |   +---------+---------+  +---------+---------+  +---------+---------+   |   |
|   |             |                      |                      |             |   |
|   |             +----------------------+----------------------+             |   |
|   |                                    |                                    |   |
|   |                                    v                                    |   |
|   |                         +---------------------+                         |   |
|   |                         | 5-State Process FSM |                         |   |
|   |                         +----------+----------+                         |   |
|   |                                    |                                    |   |
|   |             +----------------------+----------------------+             |   |
|   |             | (Trip)                                      | (Normal)    |   |
|   |             v                                             v             |   |
|   |   +-------------------+                         +-------------------+   |   |
|   |   |  Red Trip LED ON  |                         | 50-Msg FIFO Ring  |   |   |
|   |   |      GPIO 2       |                         |    Store/Fwd      |   |   |
|   |   +-------------------+                         +---------+---------+   |   |
|   |                                                           |             |   |
|   |                                                           v             |   |
|   |                                                 +-------------------+   |   |
|   |                                                 | 256dpi MQTT (QoS1)|   |   |
|   |                                                 +---------+---------+   |   |
|   +-----------------------------------------------------------+-------------+   |
+---------------------------------------------------------------|-----------------+
                                                                |
                                                                v
                                              +-----------------------------------+
                                              |       MQTT Transport Layer        |
                                              |                                   |
                                              | Path A: HiveMQ Cloud (TLS 8883)   |
                                              | Path B: Mosquitto Docker (1883)   |
                                              +-----------------+-----------------+
                                                                |
                                                                v
+---------------------------------------------------------------|-----------------+
|                                BACKEND LAYER                  |                 |
|                                                               v                 |
|   +-------------------+     +--------------------+   +----------------------+   |
|   | PostgreSQL / DB   | <---+ Paho Ingestion     |   | Real-time ML & Health|   |
|   | Persistence       |     | Schema Validation  +-->| Inference Engine     |   |
|   +-------------------+     +--------------------+   +----------+-----------+   |
|                                                                 |               |
|                                                                 v               |
|   +-------------------+     +--------------------+   +----------------------+   |
|   | Operator Alerting | <---+ WebSocket Broadcast| <-+ Digital Twin Service |   |
|   | & Maintenance     |     | (/ws/live)         |   | State Model (LIVE)   |   |
|   +-------------------+     +--------------------+   +----------------------+   |
+---------------------------------------------------------------------------------+
```

### Supported Connectivity Paths

| Parameter | Path A (Primary — Zero Cost) | Path B (Local Dev / Fallback) |
|---|---|---|
| **Wokwi Runtime** | Browser Community Simulator | VS Code Extension or Wokwi CLI |
| **Gateway** | Public IoT Gateway (`10.10.0.2`) | Private IoT Gateway (`host.wokwi.internal`) |
| **MQTT Broker** | HiveMQ Cloud Serverless (TLS 8883) | Local Mosquitto in Docker (Port 1883) |
| **Authentication** | Username/Password over TLS | Anonymous / Token (Local dev) |
| **Cost** | $0 recurring cost | Requires Wokwi license for private GW |
| **Backend Sub** | Connects to HiveMQ Cloud TLS | Connects to `localhost:1883` |

---

## 2. Hardware Schematic & Pin Assignments

Reference: [`edge/diagram.json`](file:///d:/Project/EdgeTwin-AI/edge/diagram.json).

| Component | Part ID | ESP32 Pin | Purpose | Physical / Simulated Signal |
|---|---|---|---|---|
| **ESP32 DevKit v1** | `esp` | — | Microcontroller core | 240 MHz dual-core, 520 KB SRAM |
| **DHT22** | `dht` | `GPIO 15` | Ambient Temperature & Humidity | `air_temp_c` [0.0, 60.0] °C |
| **Slide Potentiometer**| `pot` | `GPIO 34` (ADC1) | Interactive Motor Load Control | `torque_nm` [0.0, 150.0] N·m |
| **MPU6050** | `mpu` | `GPIO 21` (SDA)<br>`GPIO 22` (SCL) | Vibration RMS proxy | `vibration_mm_s` [0.0, 20.0] mm/s |
| **Red Indicator LED** | `led_trip` | `GPIO 2` (via 220 Ω) | Hardware Safety Trip Indicator | Driven `HIGH` on latch trip |

---

## 3. Step-by-Step Setup Procedure

### Step 1: Prepare Edge Configuration
1. In `edge/`, create `config.h` from `config.h.example`:
   ```bash
   cp edge/config.h.example edge/config.h
   ```
2. Configure credentials in `config.h`:
   - For **Path A (HiveMQ Cloud Serverless)**:
     ```cpp
     #define WIFI_SSID "Wokwi-GUEST"
     #define WIFI_PASSWORD ""
     #define MQTT_BROKER "YOUR_CLUSTER.s1.eu.hivemq.cloud"
     #define MQTT_PORT 8883
     #define MQTT_USE_TLS 1
     #define MQTT_USER "edgetwin_demo"
     #define MQTT_PASS "your_secure_password"
     ```
   - For **Path B (Local Mosquitto)**:
     ```cpp
     #define WIFI_SSID "Wokwi-GUEST"
     #define WIFI_PASSWORD ""
     #define MQTT_BROKER "host.wokwi.internal"
     #define MQTT_PORT 1883
     #define MQTT_USE_TLS 0
     #define MQTT_USER ""
     #define MQTT_PASS ""
     ```
   *(Note: `edge/config.h` is git-ignored and MUST never be committed with live secrets).*

### Step 2: Launch Backend Ingestion
1. Start the backend services (or local Mosquitto if using Path B):
   ```bash
   # Path B: start local broker
   docker compose up -d mosquitto
   # Start backend API and MQTT consumer
   python -m uvicorn api.app.main:app --host 0.0.0.0 --port 8000
   ```

### Step 3: Run Wokwi Simulator
1. **In Browser (Wokwi Web)**:
   - Navigate to [wokwi.com](https://wokwi.com).
   - Create a new ESP32 project.
   - Replace project files with repository files:
     - `diagram.json` $\leftarrow$ `edge/diagram.json`
     - `sketch.ino` $\leftarrow$ `edge/firmware.ino`
     - `libraries.txt` $\leftarrow$ `edge/libraries.txt`
     - Add header & source tabs: `process_model.h`, `process_model.cpp`, `ring_buffer.h`, `ring_buffer.cpp`, `command.h`, `command.cpp`, `telemetry.h`, `telemetry.cpp`, `sensors.h`, `sensors.cpp`, `config.h`.
   - Click **Play (Start Simulation)**.
2. **Via Wokwi CLI (Automated)**:
   ```bash
   wokwi-cli --timeout 30000 edge/
   ```

---

## 4. End-to-End Verification Checklist

Use this repeatable 10-stage checklist to verify edge-to-backend integrity:

| # | Stage | Verification Action | Expected Result | Pass Criteria |
|---|---|---|---|---|
| **1** | **WiFi Association** | Observe serial output during boot | Serial logs: `Connecting to WiFi: Wokwi-GUEST... WiFi connected, IP: 10.10.0.2` | IP assigned |
| **2** | **MQTT TLS Connection** | Observe broker handshake | Serial logs: `Connecting to MQTT broker... Connected to MQTT broker` | Clean connect |
| **3** | **LWT Registration** | Check broker LWT subscription | LWT set on `edgetwin/v1/MOT-1001/status` with payload `{"status":"OFFLINE"}` | Retained LWT active |
| **4** | **ONLINE Status** | Monitor topic `edgetwin/v1/MOT-1001/status` | Receives retained payload `{"status":"ONLINE"}` | Message received |
| **5** | **1 Hz Telemetry** | Monitor `edgetwin/v1/MOT-1001/telemetry` | Valid JSON conforming to `edgetwin.telemetry.v1` with seq incrementing | Schema valid, seq +1 |
| **6** | **Backend Ingestion** | Query backend database / logs | Ingest logs: `Persisted telemetry seq=X for MOT-1001`; record in DB | DB row created |
| **7** | **Digital Twin Sync** | Connect to WebSocket `/ws/live` | Receives twin snapshot with `sync_status: "LIVE"`, `health_state: "HEALTHY"` | Twin sync LIVE |
| **8** | **Safety Trip Enforcement** | Slide potentiometer $> 100$ N·m ($I > 45$ A) | Red LED turns ON; serial logs `SAFETY TRIP: TRIP_OVERCURRENT`; $\text{RPM}=0$ | Interlock latched |
| **9** | **Offline Buffer** | Disconnect broker or WiFi | Telemetry queued; `buffered` counter increases up to 50; no loop starvation | Drop-oldest FIFO |
| **10**| **Reconnect & Command** | Reconnect network & send `RESET` | Buffer flushes (max 10/tick); valid `RESET` clears trip only if safe | Interlock safe |

---

## 5. Automated Verification Harness

EdgeTwin AI includes an automated verification runner: [`simulation/wokwi_runner.py`](file:///d:/Project/EdgeTwin-AI/simulation/wokwi_runner.py).

### Running Locally:
```bash
# Run all available verification layers
python simulation/wokwi_runner.py

# Run with JSON machine-readable output
python simulation/wokwi_runner.py --json

# Run native firmware unit tests only
python simulation/wokwi_runner.py --mode=native

# Run E2E pipeline verification only
python simulation/wokwi_runner.py --mode=e2e
```

### Verification Claim Policy:
- **`PASS`**: Toolchain executed, firmware ran, and assertions verified.
- **`NOT_EXECUTED`**: Toolchain prerequisite missing (e.g. `wokwi-cli` not installed or `WOKWI_CLI_TOKEN` not configured). Reason is explicitly logged; no unit test is converted to a simulated pass.
- **`FAIL`**: Executed test failed or threw an error.

---

## 6. Troubleshooting Matrix

| Symptom | Root Cause | Remediation |
|---|---|---|
| WiFi connection timeout | Wokwi virtual WiFi gateway unreachable | Ensure diagram.json includes ESP32 DevKit v1 with internet access |
| MQTT connect error -2 | Broker address or port unreachable | Path A: verify TLS port 8883; Path B: verify port 1883 and gateway |
| Payload truncated at edge | Client buffer size insufficient | `firmware.ino` uses `256dpi/arduino-mqtt` configured with dynamic payload buffer |
| Schema validation rejection | Malformed field or missing key | Ensure firmware serializes canonical `edgetwin.telemetry.v1` format |
| Safety trip cannot be reset | Hazardous condition persists | Physical sensors must return to safe zone before `RESET` command is honored |
| LWT not triggering on exit | Clean disconnect sent before close | LWT triggers on unannounced/unclean disconnect or broker keepalive timeout |
