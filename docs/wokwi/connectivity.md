# EdgeTwin AI Connectivity Architecture (Wokwi & Virtual Edge)

## Overview
EdgeTwin AI uses a unified Telemetry Contract v1 (`edgetwin.telemetry.v1`) to communicate between edge devices and the central AI backend.

The edge layer comprises two implementations of this contract:
1. **Virtual Edge (`simulation.virtual_edge`)**: A Python-based edge simulator wrapping the authoritative physical process model.
2. **Wokwi Firmware (planned)**: A C++/Arduino implementation running in the Wokwi emulator interacting with virtual hardware components.

Both edges communicate via MQTT to a central Mosquitto broker using identical topics and payload schemas.

## Topic Structure
All edge implementations MUST adhere to the following topic structure:
- Canonical Telemetry: `edgetwin/v1/{machine_id}/telemetry` (QoS 1)
- State & Status: `edgetwin/v1/{machine_id}/status` (QoS 1, Retained)
- Command/Config: `edgetwin/v1/{machine_id}/cmd` (QoS 1)

**IMPORTANT**: The topic structure `machines/{machine_id}/telemetry/v1` is explicitly prohibited to ensure consistency with S07 specifications.

## Virtual Edge Architecture
The Virtual Edge serves as an orchestrator that wraps the `SimulatedMachine` process model.

### Key Capabilities
- **Pre-publish Validation**: Uses `TelemetryValidator` to ensure all emitted data adheres to `edgetwin.telemetry.v1`.
- **Resilient Connectivity**: Built-in state machine for broker connectivity utilizing `paho-mqtt` 2.0 (VERSION2).
- **Offline Buffering**: In-memory ring buffer (capacity: 1000 messages) that buffers telemetry during network partitions.
- **Automatic Flushing**: Seamlessly replays buffered telemetry to the broker upon successful reconnection.
- **LWT (Last Will and Testament)**: Gracefully notifies the backend if the edge device goes offline abruptly.

## Mosquitto Broker Config
The local Mosquitto broker is defined in `docker-compose.yml` and configured for basic unauthenticated local access.
- **Host**: `localhost`
- **Port**: `1883`

For testing and local development, the broker allows anonymous connections. Future cloud integrations (e.g., HiveMQ Serverless) will require TLS and authentication.
