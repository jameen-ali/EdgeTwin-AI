# S09 Session Report — T-040 Wokwi Hardware Feasibility Spike

## 1. Executive Summary & Session Information

- **Session:** S09
- **Model:** Gemini 3.7 Flash (High)
- **Task:** T-040 (Wokwi Hardware Feasibility Spike)
- **Branch:** `feat/T-040-wokwi-feasibility`
- **Base Commit:** `ab2f7d8` (S08 finalization: `feat(edge): add virtual edge and mqtt broker`)
- **Author:** Mohamed Jameen Ali M R (Register No: 24AD0173)

### Executive Conclusion
The technical feasibility of integrating an ESP32 hardware simulation in Wokwi with the EdgeTwin AI MQTT ingestion pipeline has been audited and established. 

**Path A (Wokwi Browser ESP32 $\rightarrow$ Public Cloud Broker over TLS/8883 $\rightarrow$ EdgeTwin Backend)** is selected as the primary architecture because it achieves **zero recurring cost**, requires no proprietary licensing or local helper binaries, and enables seamless evaluation from any web browser. 

The software-only **Virtual Edge (S08)** remains the permanent offline and automated CI fallback.

---

## 2. Answers to Required Feasibility Questions

| # | Feasibility Question | Status | Evidence & Technical Findings |
|---|---|---|---|
| 1 | Can Wokwi Public IoT Gateway reach a public MQTT broker? | **CONFIRMED** | Wokwi Public Gateway (`10.10.0.2`) routes outbound TCP traffic over standard ports (1883, 8883) to public IPv4 and FQDN endpoints. |
| 2 | Can ESP32 simulation establish MQTT over TLS/8883? | **CONFIRMED** | `WiFiClientSecure` in ESP32 Arduino core establishes TLS connections on port 8883 using root CA certificates or `espClient.setInsecure()`. |
| 3 | Can the selected MQTT library publish QoS 1? | **CONFIRMED** | Standard `PubSubClient` supports QoS 0 ONLY for publish; however, `256dpi/arduino-mqtt` and native `esp-mqtt` (`mqtt_client.h`) natively support QoS 1 publishing. |
| 4 | Can it support LWT / status? | **CONFIRMED** | MQTT 3.1.1 LWT is fully supported by ESP32 MQTT libraries on `edgetwin/v1/{machine_id}/status` with `retain=true`. |
| 5 | Is the expected telemetry payload size supported? | **CONFIRMED** | `edgetwin.telemetry.v1` payload is ~450–550 bytes. Supported dynamically by `256dpi/arduino-mqtt` and `esp-mqtt` (or by `setBufferSize(1024)` in PubSubClient). |
| 6 | Can the required sensors be represented in Wokwi? | **CONFIRMED** | DHT22 (`wokwi-dht22`), slide potentiometer (`wokwi-slide-potentiometer`), and MPU6050 (`wokwi-mpu6050`) exist in Wokwi catalog. Remaining channels are generated via coupled firmware process equations. |
| 7 | Can Path A work without requiring incoming connections? | **CONFIRMED** | MQTT is an outbound client-initiated TCP connection; broker responses and subscriptions travel over the existing outbound socket. |
| 8 | What limitations exist for credentials/secrets in Wokwi? | **CONFIRMED** | Wokwi Community sketches are public. Production secrets must never be embedded. Mitigated by using throw-away demo credentials with broker ACL topic restrictions. |
| 9 | What does Path B require? | **CONFIRMED** | Path B requires the local Wokwi Private IoT Gateway executable (`wokwigw` on port 9011) and connects to `host.wokwi.internal:1883`, requiring a paid Hobby+ plan ($7/mo) or VS Code license. |
| 10 | What is the documented fallback if Path A is unavailable? | **CONFIRMED** | The Python `VirtualEdge` publisher (`simulation.virtual_edge`) running against local Mosquitto in Docker provides 100% deterministic offline fallback. |

---

## 3. Evidence Classification Summary

- **CONFIRMED:**
  - Wokwi ESP32 outbound TCP to public internet
  - Wokwi browser cannot reach `localhost:1883` via Public Gateway
  - Wokwi Private Gateway bridges to host as `host.wokwi.internal:1883`
  - Wokwi Private Gateway requires paid tier / extension license
  - Official `PubSubClient` does not support QoS 1 publish
  - `256dpi/arduino-mqtt` and native `esp-mqtt` support QoS 1 publish and dynamic buffers $>512$ bytes
  - HiveMQ Cloud Serverless provides free-tier MQTT over TLS on port 8883 (100 connections, 10 GB/mo)
  - Wokwi Community sketches are publicly viewable
  - DHT22, slide potentiometer, MPU6050, and LEDs exist in Wokwi hardware catalog
- **LIKELY:**
  - Public internet jitter between Wokwi cloud gateway and local backend will remain within the p95 $\le 2.0$ s latency SLA (to be formally measured in T-043).
- **UNCONFIRMED / BLOCKED:**
  - Zero items blocked. No unconfirmed assumptions remain for Phase 0.

---

## 4. Path A vs. Path B Comparison

| Metric / Dimension | Path A: Cloud MQTT Broker | Path B: Local Mosquitto Broker |
|---|---|---|
| **Wokwi Simulator Compatibility** | Runs in web browser via default Public Gateway. | Requires Wokwi Private IoT Gateway binary (`wokwigw`) or VS Code extension. |
| **Network Destination** | Public FQDN over internet (e.g. `*.hivemq.cloud:8883`). | `host.wokwi.internal:1883` on developer loopback. |
| **Internet Dependency** | Mandatory continuous internet connection. | Zero internet dependency during simulation run. |
| **Broker Implementation** | Managed multi-tenant cloud broker (HiveMQ Serverless). | Local Docker container (`eclipse-mosquitto:2.0`). |
| **Authentication & TLS** | Mandatory TLS (port 8883) with username/password auth. | Plain TCP (port 1883) or local self-signed TLS. |
| **Monetary Cost** | $0 on free tier (satisfies PRD §6 constraint). | Requires paid Wokwi license ($7/mo Hobby+) for Private Gateway. |
| **Sketch Security** | Publicly visible sketch; requires throw-away demo credentials. | Entirely private on local filesystem. |
| **Evaluator Usability** | Anyone can open public Wokwi URL in a browser. | Evaluator must install local helper binary and have a paid license. |

---

## 5. Implementation Specification for T-041 (Firmware v1)

- **Target MCU:** ESP32 DevKit v1 (`wokwi-esp32-devkit-v1`).
- **Hardware Simulation:**
  - Ambient Temperature: `wokwi-dht22` on GPIO 15.
  - Mechanical Load: `wokwi-slide-potentiometer` on GPIO 34 (ADC1).
  - Vibration Velocity Proxy: `wokwi-mpu6050` on I2C (SDA 21, SCL 22).
  - Safety Trip Indicator: Red LED on GPIO 2 with 220 $\Omega$ resistor.
- **Process Model Coupling:**
  - Process temperature derived from electrical load: $T_{\text{proc}} = T_{\text{air}} + \Delta T_{\text{load}}$.
  - Current coupled to torque: $I = 12.0 \cdot (\tau / 40.1)$.
  - Rotational speed follows state machine: 0 RPM stopped $\to$ 1548 RPM nominal running.
- **Wire Contract:** Strict `edgetwin.telemetry.v1` JSON payload matching S07 contract.
- **Canonical Topics:**
  - Telemetry: `edgetwin/v1/MOT-1001/telemetry` (QoS 1)
  - Status: `edgetwin/v1/MOT-1001/status` (QoS 1, Retained, LWT)
  - Command: `edgetwin/v1/MOT-1001/cmd` (QoS 1)
- **MQTT Library:** `256dpi/arduino-mqtt` or native `esp_mqtt_client` (QoS 1 publish capable).

---

## 6. Verification and Governance

- **Test Suite Status:** 339 tests passing, 1 test skipped (live local broker check), 0 failures.
- **Test-Set Protection:** Held-out test partition (`data/test/`) was strictly untouched.
- **Secrets Governance:** No API keys, credentials, or private certificates were introduced or committed.
- **Working Tree:** Clean.
