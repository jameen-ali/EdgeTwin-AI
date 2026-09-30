"""
simulation/virtual_edge.py — Virtual Edge Telemetry Publisher

Tasks: T-022 Virtual Edge / Python Telemetry Publisher

Provides:
- VirtualEdge: Orchestrator wrapping SimulatedMachine, maintaining a ring buffer,
  and publishing telemetry to MQTT using paho-mqtt VERSION2.
"""

import argparse
import json
import logging
import time
from collections import deque
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt
import yaml

from simulation.contract import TelemetryValidator
from simulation.process_model import SimulatedMachine

logger = logging.getLogger(__name__)


class VirtualEdge:
    """Virtual Edge simulating an IoT device that reads from the process model
    and publishes MQTT messages. Implements a ring buffer for disconnects.
    """

    def __init__(
        self,
        machine_id: str = "MOT-1001",
        scenario: dict[str, Any] | None = None,
        seed: int = 42,
        tick_interval_s: float = 1.0,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        auto_start_machine: bool = True,
    ):
        self.machine_id = machine_id
        self.broker_host = broker_host
        self.broker_port = broker_port

        # Authoritative physical process simulation
        self.machine = SimulatedMachine(
            machine_id=machine_id,
            scenario=scenario,
            seed=seed,
            tick_interval_s=tick_interval_s,
            auto_start=auto_start_machine,
        )
        self.validator = TelemetryValidator()

        # Max capacity 1000 as per requirements
        self.buffer: deque[dict[str, Any]] = deque(maxlen=1000)
        self.connected = False

        # Use Paho MQTT 2.x API
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id=f"ve_{self.machine_id}"
        )
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

        # Canonical topics
        self.telemetry_topic = f"edgetwin/v1/{self.machine_id}/telemetry"
        self.status_topic = f"edgetwin/v1/{self.machine_id}/status"
        self.cmd_topic = f"edgetwin/v1/{self.machine_id}/cmd"

        # LWT (Last Will and Testament)
        self.client.will_set(
            self.status_topic,
            payload=json.dumps({"status": "OFFLINE"}),
            qos=1,
            retain=True,
        )

    def _on_connect(
        self, client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any
    ) -> None:
        if getattr(reason_code, "value", reason_code) == 0:
            self.connected = True
            logger.info(f"[{self.machine_id}] Connected to broker.")
            self.client.publish(
                self.status_topic,
                payload=json.dumps({"status": "ONLINE"}),
                qos=1,
                retain=True,
            )
            self._flush_buffer()
        else:
            self.connected = False
            logger.error(f"[{self.machine_id}] Connection failed, reason_code={reason_code}")

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        disconnect_flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        self.connected = False
        logger.warning(f"[{self.machine_id}] Disconnected from broker, reason_code={reason_code}")

    def _flush_buffer(self) -> None:
        """Attempt to publish all buffered messages."""
        while self.buffer and self.connected:
            payload = self.buffer[0]
            try:
                # Update the buffered count to reflect it's being flushed
                payload["edge"]["buffered"] = len(self.buffer) - 1
                msg_str = json.dumps(payload)
                msg_info = self.client.publish(self.telemetry_topic, msg_str, qos=1)
                msg_info.wait_for_publish(timeout=1.0)
                if msg_info.is_published():
                    self.buffer.popleft()
                else:
                    # Publish timeout or not yet published, back off
                    break
            except Exception as e:  # noqa: BLE001
                logger.error(f"[{self.machine_id}] Error flushing buffer: {e}")
                break

    def connect(self) -> None:
        """Connect to the Mosquitto broker and start the network loop."""
        self.client.connect(self.broker_host, self.broker_port, keepalive=60)
        self.client.loop_start()

    def disconnect(self) -> None:
        """Cleanly disconnect from the broker."""
        if self.connected:
            msg_info = self.client.publish(
                self.status_topic,
                payload=json.dumps({"status": "OFFLINE"}),
                qos=1,
                retain=True,
            )
            msg_info.wait_for_publish(timeout=2.0)
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False

    def step(self) -> dict[str, Any] | None:
        """Advance simulation by 1 tick, validate, buffer, and publish if connected."""
        payload = self.machine.step()
        if payload is None:
            return None

        # Pre-publish validation
        val_res = self.validator.validate(payload, topic=self.telemetry_topic)
        if not val_res.valid:
            logger.error(f"[{self.machine_id}] Telemetry validation failed: {val_res.errors}")
            # If payload is invalid according to contract, we still might simulate the hardware
            # but in a real-world scenario we log and might not send it.
            # To adhere to contract, we won't throw exception but log it.

        if self.connected:
            self._flush_buffer()
            payload["edge"]["buffered"] = len(self.buffer)
            try:
                # Paho MQTT publish is asynchronous, but we use wait_for_publish if we want
                # strict queue tracking. For high freq, we'd just publish.
                # Since this is EdgeTwin, we'll just publish and rely on Paho's internal queue
                # for brief transient errors, and our explicit ring buffer for full disconnects.
                self.client.publish(self.telemetry_topic, json.dumps(payload), qos=1)
                # If network drops suddenly before on_disconnect fires, this might fail or queue internally.
            except Exception as e:  # noqa: BLE001
                logger.error(f"[{self.machine_id}] Publish error: {e}")
                self.buffer.append(payload)
        else:
            payload["edge"]["buffered"] = len(self.buffer) + 1
            self.buffer.append(payload)

        return payload


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint for virtual edge publisher."""
    parser = argparse.ArgumentParser(
        description="EdgeTwin AI Virtual Edge Telemetry Publisher",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--machine-id",
        type=str,
        default="MOT-1001",
        help="Target machine identifier",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=1.0,
        help="Publishing rate in Hz (ticks per second)",
    )
    parser.add_argument(
        "--broker",
        type=str,
        default="localhost",
        help="MQTT broker host address",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=1883,
        help="MQTT broker port number",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Path or name of scenario YAML file (e.g., healthy_nominal)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic simulation",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="Total ticks to simulate before exiting (default: run indefinitely)",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    scenario_dict = None
    if args.scenario:
        scenario_path = Path(args.scenario)
        if not scenario_path.is_file():
            candidates = [
                Path(__file__).parent / "scenarios" / f"{args.scenario}.yaml",
                Path(__file__).parent / "scenarios" / args.scenario,
            ]
            for cand in candidates:
                if cand.is_file():
                    scenario_path = cand
                    break
        if scenario_path.is_file():
            logger.info("Loading scenario from %s", scenario_path)
            with open(scenario_path, "r", encoding="utf-8") as f:
                scenario_dict = yaml.safe_load(f)
        else:
            logger.warning("Scenario '%s' not found, using nominal baseline.", args.scenario)

    tick_interval = 1.0 / args.rate if args.rate > 0 else 1.0

    edge = VirtualEdge(
        machine_id=args.machine_id,
        scenario=scenario_dict,
        seed=args.seed,
        tick_interval_s=tick_interval,
        broker_host=args.broker,
        broker_port=args.port,
    )

    logger.info(
        "Starting Virtual Edge for machine=%s -> %s:%d @ %.1f Hz",
        args.machine_id,
        args.broker,
        args.port,
        args.rate,
    )

    edge.connect()
    # Wait briefly for MQTT network loop handshake
    time.sleep(0.5)

    ticks = 0
    try:
        while True:
            t0 = time.monotonic()
            payload = edge.step()
            if payload is None:
                logger.info("Simulation reached completion of scenario.")
                break

            ticks += 1
            ts = payload.get("ts", "")
            seq = payload.get("seq", 0)
            m_id = payload.get("machine_id", edge.machine_id)
            state = edge.machine.state.value
            signals = payload.get("signals", {})
            temp = signals.get("process_temp_c", 0.0)
            rpm = signals.get("rotational_speed_rpm", 0.0)
            torque = signals.get("torque_nm", 0.0)
            vib = signals.get("vibration_mm_s")
            vib_str = f"{vib:4.2f} mm/s" if vib is not None else "N/A"

            print(
                f"[{ts}] seq={seq:04d} | "
                f"Machine={m_id} ({state}) | "
                f"Temp={temp:5.1f} C | Speed={rpm:6.1f} RPM | "
                f"Torque={torque:4.1f} Nm | Vib={vib_str}"
            )

            if args.count is not None and ticks >= args.count:
                logger.info("Completed %d requested ticks.", ticks)
                break

            elapsed = time.monotonic() - t0
            sleep_time = max(0.0, tick_interval - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\nStopping Virtual Edge...")
    finally:
        edge.disconnect()
        logger.info("Virtual Edge shutdown cleanly.")


if __name__ == "__main__":
    main()
