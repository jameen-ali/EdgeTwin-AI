# EdgeTwin AI Connectivity Architecture (Wokwi & Virtual Edge)

## 1. Overview
EdgeTwin AI uses a unified Telemetry Contract v1 (`edgetwin.telemetry.v1`) to communicate between edge devices and the central AI backend.

The edge layer comprises two implementations of this contract:
1. **Virtual Edge (`simulation.virtual_edge`)**: A Python-based edge simulator wrapping the authoritative physical process model (`simulation.process_model.SimulatedMachine`).
2. **Wokwi Firmware (ESP32 DevKit v1)**: A C++/Arduino implementation running in the Wokwi emulator interacting with virtual sensors and firmware-driven process variables.

Both edge implementations communicate via MQTT using identical topics, QoS levels, and payload schemas.

---

## 2. Topic Structure
All edge implementations MUST adhere to the following topic structure:
- **Canonical Telemetry:** `edgetwin/v1/{machine_id}/telemetry` (QoS 1)
- **State & Status:** `edgetwin/v1/{machine_id}/status` (QoS 1, Retained)
- **Command/Config:** `edgetwin/v1/{machine_id}/cmd` (QoS 1)

**IMPORTANT:** The topic structure `machines/{machine_id}/telemetry/v1` is explicitly prohibited to prevent contract divergence with S07/S08 specifications.

---

## 3. Connectivity Paths

### Path A: Public Cloud Broker (Primary Zero-Cost Architecture)
- **Topology:** Wokwi Browser ESP32 $\rightarrow$ Wokwi Public IoT Gateway $\rightarrow$ Public Cloud Broker (TLS 8883) $\leftarrow$ EdgeTwin Backend.
- **Broker Option:** HiveMQ Cloud Serverless (Free tier: 100 concurrent clients, 10 GB/month data transfer, TLS-SNI on port 8883).
- **Network Mode:** Outbound TCP via Wokwi Public Gateway (`10.10.0.2`). No local gateway binary or browser extensions required.
- **Security:** Requires TLS encryption (`WiFiClientSecure`) and throw-away demo credentials with broker ACLs restricted to `edgetwin/v1/{machine_id}/#`.
- **Cost:** $0 recurring cost (satisfies PRD §6 constraint).

### Path B: Local Mosquitto Broker (Local Development / Fallback)
- **Topology:** Wokwi ESP32 $\rightarrow$ Wokwi Private IoT Gateway (`host.wokwi.internal:1883`) $\rightarrow$ Local Mosquitto in Docker $\leftarrow$ EdgeTwin Backend.
- **Localhost Constraint:** Standard Wokwi in a web browser **CANNOT** reach `localhost:1883` directly due to browser sandboxing. Path B requires running the local `wokwigw` utility (listening on port 9011) or using the Wokwi for VS Code extension.
- **Licensing Limitation:** The Private IoT Gateway requires a paid Wokwi Hobby+ subscription ($7/mo) or active VS Code extension license.

---

## 4. Hardware & Sensor Mapping

| Telemetry Channel | Wokwi Part / Source | Implementation Mechanism | Nominal Value | Bounds Range |
|---|---|---|---|---|
| `air_temp_c` | `wokwi-dht22` | Virtual Sensor on GPIO 15 | 25.4 °C | [0.0, 60.0] °C |
| `process_temp_c` | Coupled Thermal Model | Firmware Process Variable ($T_{\text{proc}} = T_{\text{air}} + \Delta T_{\text{load}}$) | 35.3 °C | [0.0, 80.0] °C |
| `rotational_speed_rpm` | FSM Speed Curve | Firmware Process Variable (0 RPM stopped $\to$ 1548 RPM running) | 1548.0 RPM | [0.0, 5000.0] RPM |
| `torque_nm` | `wokwi-slide-potentiometer` | Analog ADC on GPIO 34 (0–4095 scaled to 0–150 N·m) | 40.1 N·m | [0.0, 150.0] N·m |
| `vibration_mm_s` | `wokwi-mpu6050` | I2C (SDA 21, SCL 22) + Wear Noise Model | 2.5 mm/s | [0.0, 20.0] mm/s |
| `pressure_bar` | Fluid Dynamics Model | Firmware Process Variable ($P = 5.5 \pm \epsilon$) | 5.5 bar | [0.0, 20.0] bar |
| `current_a` | Load Coupling | Firmware Process Variable ($I = 12.0 \cdot (\tau / 40.1)$) | 12.0 A | [0.0, 50.0] A |
| `voltage_v` | Supply Grid Model | Firmware Process Variable ($V = 415.0 \pm \epsilon$) | 415.0 V | [300.0, 500.0] V |
| `tool_wear_min` | Wear Integrator | Firmware Accumulated Variable ($\text{wear} += \text{rate} \cdot \Delta t$) | ~50.0 min | [0.0, 300.0] min |
| `operating_hours` | Runtime Counter | Firmware Monotonic Counter ($\text{hours} += \Delta t / 3600$) | ~10000.0 h | [0.0, 25000.0] h |

---

## 5. MQTT Client Library Constraints
- **Standard `PubSubClient` Limitation:** Official `PubSubClient` supports **QoS 0 ONLY** for publishing. It also defaults to a 256-byte buffer, which truncates the ~500-byte telemetry JSON payload.
- **Recommended Libraries for T-041:**
  1. `256dpi/arduino-mqtt` (`MQTTClient`): Natively supports QoS 1 publishing (`client.publish(topic, payload, false, 1)`) and dynamic buffers.
  2. Native Espressif `esp-mqtt` (`mqtt_client.h`): Bundled in ESP32 Arduino Core with full QoS 1/2, TLS, and background reconnection.

---

## 6. Resilience & Offline Fallback
- **Edge Buffering:** The edge device maintains an in-memory ring buffer for telemetry emissions when disconnected from the broker.
- **LWT:** Configured on `edgetwin/v1/{machine_id}/status` with retained payload `{"status": "OFFLINE"}`.
- **Offline Simulation Fallback:** If internet connectivity or public cloud brokers are unavailable, the software-only `VirtualEdge` publisher (`simulation.virtual_edge`) provides 100% deterministic local execution against local Mosquitto.
