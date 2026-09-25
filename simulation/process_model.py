"""
simulation/process_model.py — Physical process simulation and FSM for EdgeTwin AI.

Tasks: T-021 Scenario Specification & Process Model

Implements:
- MachineOperatingState: 5-state FSM (STOPPED, STARTING, RUNNING, DEGRADING, TRIPPED)
- SimulatedMachine: Seeded, deterministic physical simulator with coupled dynamics
  between temperature, current, voltage, power, torque, speed, vibration, pressure,
  tool wear, and operating hours. Generates valid Telemetry Contract v1 messages.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from simulation.contract import SCHEMA_ID


class MachineOperatingState(str, Enum):
    """Authoritative 5-state FSM for machine operation."""

    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    DEGRADING = "DEGRADING"
    TRIPPED = "TRIPPED"


class SimulatedMachine:
    """Coupled physical process simulator driving deterministic telemetry generation."""

    def __init__(
        self,
        machine_id: str = "MOT-1001",
        scenario: dict[str, Any] | None = None,
        seed: int = 42,
        tick_interval_s: float = 1.0,
        start_time_iso: str = "2026-01-01T00:00:00Z",
        auto_start: bool = True,
    ) -> None:
        self.machine_id = machine_id
        self.scenario = scenario or {}
        self.seed = int(self.scenario.get("seed", seed))
        self.rng = np.random.RandomState(self.seed)
        self.tick_interval_s = float(self.scenario.get("tick_interval_s", tick_interval_s))

        # Base timestamp handling
        dt = datetime.fromisoformat(start_time_iso)
        self.start_epoch = dt.timestamp()
        self.current_epoch = self.start_epoch

        self.seq = 0
        self.step_idx = 0
        self.state = MachineOperatingState.STOPPED
        self.active_trip: str | None = None
        self.buffered_count = 0

        # Load baseline parameters from scenario or defaults
        base = self.scenario.get("baseline", {})
        self.air_temp_nominal = float(base.get("air_temp_c", {}).get("mean", 25.4))
        self.air_temp_std = float(base.get("air_temp_c", {}).get("std", 0.5))

        self.proc_temp_nominal = float(base.get("process_temp_c", {}).get("mean", 35.3))
        self.proc_temp_std = float(base.get("process_temp_c", {}).get("std", 0.6))

        self.rpm_nominal = float(base.get("rotational_speed_rpm", {}).get("mean", 1548.0))
        self.rpm_std = float(base.get("rotational_speed_rpm", {}).get("std", 20.0))

        self.torque_nominal = float(base.get("torque_nm", {}).get("mean", 40.1))
        self.torque_std = float(base.get("torque_nm", {}).get("std", 2.0))

        self.vib_nominal = float(base.get("vibration_mm_s", {}).get("mean", 2.5))
        self.vib_std = float(base.get("vibration_mm_s", {}).get("std", 0.3))

        self.pressure_nominal = float(base.get("pressure_bar", {}).get("mean", 5.5))
        self.pressure_std = float(base.get("pressure_bar", {}).get("std", 0.4))

        self.current_nominal = float(base.get("current_a", {}).get("mean", 12.0))
        self.current_std = float(base.get("current_a", {}).get("std", 0.5))

        self.voltage_nominal = float(base.get("voltage_v", {}).get("mean", 415.0))
        self.voltage_std = float(base.get("voltage_v", {}).get("std", 2.0))

        self.tool_wear_min = float(base.get("tool_wear_min", 50.0))
        self.tool_wear_rate = float(base.get("tool_wear_rate", 0.1))
        self.operating_hours = float(base.get("operating_hours", 10000.0))

        # Dynamic physical state
        self.air_temp = self.air_temp_nominal
        self.process_temp = self.air_temp_nominal
        self.rpm = 0.0
        self.torque = 0.0
        self.current = 0.0
        self.voltage = self.voltage_nominal
        self.vibration = 0.1
        self.pressure = 1.0

        # Fault tracking
        self.fault_spec = self.scenario.get("fault", {})
        self.fault_active = False

        if auto_start:
            self.start()

    @classmethod
    def from_scenario_file(
        cls,
        scenario_path: Path | str,
        seed: int = 42,
        machine_id: str | None = None,
    ) -> SimulatedMachine:
        """Instantiate a SimulatedMachine from a YAML scenario file."""
        path = Path(scenario_path)
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        m_id = machine_id or data.get("machine_id", "MOT-1001")
        return cls(machine_id=m_id, scenario=data, seed=seed)

    # -----------------------------------------------------------------------
    # FSM State Transitions
    # -----------------------------------------------------------------------

    def start(self) -> None:
        """Transition STOPPED -> STARTING."""
        if self.state == MachineOperatingState.STOPPED:
            self.state = MachineOperatingState.STARTING
            self.active_trip = None

    def stop(self) -> None:
        """Transition RUNNING/STARTING -> STOPPED."""
        self.state = MachineOperatingState.STOPPED
        self.rpm = 0.0
        self.torque = 0.0
        self.current = 0.0

    def trigger_trip(self, trip_code: str) -> None:
        """Trigger an edge hardware safety trip (RUNNING/DEGRADING -> TRIPPED)."""
        self.state = MachineOperatingState.TRIPPED
        self.active_trip = trip_code
        self.rpm = 0.0
        self.torque = 0.0
        self.current = 0.0

    def reset(self) -> None:
        """Reset machine from TRIPPED -> STOPPED."""
        if self.state == MachineOperatingState.TRIPPED:
            self.state = MachineOperatingState.STOPPED
            self.active_trip = None

    def clear_fault(self) -> None:
        """Clear active degradation and return to RUNNING."""
        if self.state == MachineOperatingState.DEGRADING:
            self.state = MachineOperatingState.RUNNING
            self.fault_active = False

    # -----------------------------------------------------------------------
    # Coupled Physics Simulation Tick
    # -----------------------------------------------------------------------

    def step(self) -> dict[str, Any] | None:
        """Advance simulation clock by 1 tick and return canonical telemetry payload.

        Returns None if machine is in offline/disconnected scenario mode.
        """
        # 1. Offline scenario check
        fault_type = self.fault_spec.get("type", "none")
        if fault_type == "offline":
            disconnect_step = int(self.fault_spec.get("disconnect_step", 10))
            if self.step_idx >= disconnect_step:
                # Silent connection loss — no telemetry emitted
                self.step_idx += 1
                self.current_epoch += self.tick_interval_s
                return None

        # 2. Evaluate Fault Trigger
        trigger_step = int(self.fault_spec.get("trigger_step", 999999))
        duration_steps = int(self.fault_spec.get("duration_steps", 60))

        if self.step_idx >= trigger_step and not self.fault_active and fault_type != "none":
            self.fault_active = True
            if self.state == MachineOperatingState.RUNNING:
                self.state = MachineOperatingState.DEGRADING

        # Fault progress in [0, 1]
        progress: float = 0.0
        if self.fault_active and duration_steps > 0:
            elapsed_fault = self.step_idx - trigger_step
            progress = min(1.0, max(0.0, elapsed_fault / float(duration_steps)))

        # 3. Ambient conditions (slow thermal drift)
        self.air_temp = self.air_temp_nominal + self.rng.normal(0.0, self.air_temp_std)

        # 4. State-dependent Physics Evolution
        if self.state == MachineOperatingState.STARTING:
            # Ramping up speed over ~5 ticks
            self.rpm = min(self.rpm_nominal, self.rpm + (self.rpm_nominal / 5.0))
            # Inrush current spike
            self.current = self.current_nominal * 2.2
            self.torque = self.torque_nominal * 0.8
            self.voltage = self.voltage_nominal + self.rng.normal(0.0, self.voltage_std)
            self.vibration = 1.2 + self.rng.normal(0.0, 0.1)
            self.pressure = 3.0 + self.rng.normal(0.0, 0.2)
            # Process temperature starts tracking
            self.process_temp += 0.5 * (self.air_temp + 5.0 - self.process_temp)

            if self.rpm >= 1400.0:
                self.state = MachineOperatingState.RUNNING

        elif self.state in (MachineOperatingState.RUNNING, MachineOperatingState.DEGRADING):
            # Target operating parameters
            target_torque = self.torque_nominal
            target_rpm = self.rpm_nominal
            target_voltage = self.voltage_nominal
            target_current = self.current_nominal
            target_proc_temp = self.air_temp + 9.9  # Nominal Delta_T approx 9.9 °C
            target_vib = self.vib_nominal
            target_pressure = self.pressure_nominal

            # Apply Fault Trajectories
            if self.fault_active:
                targets = self.fault_spec.get("target_values", {})
                if fault_type == "ramp":
                    if "process_temp_c" in targets:
                        target_proc_temp = (1.0 - progress) * (
                            self.air_temp + 9.9
                        ) + progress * float(targets["process_temp_c"])
                    if "air_temp_c" in targets:
                        self.air_temp = (1.0 - progress) * self.air_temp_nominal + progress * float(
                            targets["air_temp_c"]
                        )
                    if "rotational_speed_rpm" in targets:
                        target_rpm = (1.0 - progress) * self.rpm_nominal + progress * float(
                            targets["rotational_speed_rpm"]
                        )
                    if "torque_nm" in targets:
                        target_torque = (1.0 - progress) * self.torque_nominal + progress * float(
                            targets["torque_nm"]
                        )
                    if "current_a" in targets:
                        target_current = (1.0 - progress) * self.current_nominal + progress * float(
                            targets["current_a"]
                        )
                    if "vibration_mm_s" in targets:
                        target_vib = (1.0 - progress) * self.vib_nominal + progress * float(
                            targets["vibration_mm_s"]
                        )

                elif fault_type == "step":
                    if "current_a" in targets:
                        target_current = float(targets["current_a"])
                    if "voltage_v" in targets:
                        target_voltage = float(targets["voltage_v"])
                    if "vibration_mm_s" in targets:
                        target_vib = float(targets["vibration_mm_s"])
                    if "pressure_bar" in targets:
                        target_pressure = float(targets["pressure_bar"])
                    if "process_temp_c" in targets:
                        target_proc_temp = float(targets["process_temp_c"])

            # Physically Coupled Sensor Updates:
            # 1. Torque & Current Coupling
            load_factor = target_torque / max(1.0, self.torque_nominal)
            if fault_type != "step" or "current_a" not in self.fault_spec.get("target_values", {}):
                target_current = self.current_nominal * load_factor

            self.torque = target_torque + self.rng.normal(0.0, self.torque_std)
            self.current = target_current + self.rng.normal(0.0, self.current_std)
            self.voltage = target_voltage + self.rng.normal(0.0, self.voltage_std)
            self.rpm = target_rpm + self.rng.normal(0.0, self.rpm_std)

            # 2. Thermal Dissipation Differential Coupling
            # Thermal accumulation from electrical current and mechanical load
            load_heat = 0.5 * (self.current / 12.0) ** 2 + 0.5 * (self.torque / 40.0)
            equilibrium_temp = target_proc_temp + (load_heat - 1.0) * 2.0
            self.process_temp += 0.25 * (equilibrium_temp - self.process_temp)
            self.process_temp += self.rng.normal(0.0, self.proc_temp_std * 0.3)

            # 3. Vibration & Pressure Dynamics
            wear_vib_factor = max(0.0, (self.tool_wear_min - 150.0) / 100.0) * 0.8
            self.vibration = target_vib + wear_vib_factor + self.rng.normal(0.0, self.vib_std)
            self.pressure = target_pressure + self.rng.normal(0.0, self.pressure_std)

            # 4. Tool Wear and Operating Hours Accumulation
            wear_rate_mult = 1.0 + max(0.0, (self.torque - 40.0) / 30.0)
            self.tool_wear_min += self.tool_wear_rate * wear_rate_mult * self.tick_interval_s
            self.operating_hours += self.tick_interval_s / 3600.0

            # 5. Check Edge Hardware Safety Trips
            trip_candidate = self.fault_spec.get("trip_code")
            trip_delay = int(self.fault_spec.get("trip_delay_steps", 10))
            if trip_candidate and self.fault_active:
                elapsed_fault = self.step_idx - trigger_step
                if elapsed_fault >= trip_delay:
                    self.trigger_trip(trip_candidate)
            elif (self.process_temp - self.air_temp) > 45.0:
                self.trigger_trip("TRIP_THERMAL")
            elif self.current > 45.0:
                self.trigger_trip("TRIP_OVERCURRENT")
            elif self.vibration > 15.0:
                self.trigger_trip("TRIP_VIBRATION")

        elif self.state in (MachineOperatingState.STOPPED, MachineOperatingState.TRIPPED):
            # Machine not operating; process temp cools down toward air temp
            self.rpm = 0.0
            self.torque = 0.0
            self.current = 0.0
            self.voltage = self.voltage_nominal + self.rng.normal(0.0, 0.5)
            self.vibration = max(0.0, 0.1 + self.rng.normal(0.0, 0.02))
            self.pressure = max(0.0, 0.5 + self.rng.normal(0.0, 0.05))
            self.process_temp += 0.05 * (self.air_temp - self.process_temp)

        # 5. Format ISO-8601 UTC timestamp
        current_dt = datetime.fromtimestamp(self.current_epoch, tz=UTC)
        ts_str = current_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        # 6. Apply Dropout if configured
        drop_vib = False
        drop_press = False
        if fault_type == "dropout" and "dropouts" in self.fault_spec:
            for drop_cfg in self.fault_spec["dropouts"]:
                sensor_name = drop_cfg.get("sensor")
                s_start = int(drop_cfg.get("start_step", 0))
                s_end = int(drop_cfg.get("end_step", 999999))
                if s_start <= self.step_idx <= s_end:
                    if sensor_name == "vibration_mm_s":
                        drop_vib = True
                    elif sensor_name == "pressure_bar":
                        drop_press = True

        signals: dict[str, Any] = {
            "air_temp_c": round(float(self.air_temp), 2),
            "process_temp_c": round(float(self.process_temp), 2),
            "rotational_speed_rpm": round(float(self.rpm), 1),
            "torque_nm": round(float(self.torque), 2),
            "vibration_mm_s": None if drop_vib else round(float(self.vibration), 2),
            "pressure_bar": None if drop_press else round(float(self.pressure), 2),
            "current_a": round(float(self.current), 2),
            "voltage_v": round(float(self.voltage), 2),
            "tool_wear_min": round(float(self.tool_wear_min), 2),
            "operating_hours": round(float(self.operating_hours), 4),
        }

        # Quality determination
        quality: dict[str, str] = {}
        if drop_vib:
            quality["vibration_mm_s"] = "MISSING"
        elif self.vibration > 7.0:
            quality["vibration_mm_s"] = "LIMIT_ALARM"
        elif self.vibration > 4.5:
            quality["vibration_mm_s"] = "LIMIT_WARN"
        else:
            quality["vibration_mm_s"] = "OK"

        if drop_press:
            quality["pressure_bar"] = "MISSING"
        elif self.pressure > 8.0:
            quality["pressure_bar"] = "LIMIT_ALARM"
        else:
            quality["pressure_bar"] = "OK"

        # Edge computed diagnostics
        edge_delta_t = round(float(self.process_temp - self.air_temp), 2)
        edge_power = round(float(self.voltage * self.current), 2)

        payload: dict[str, Any] = {
            "schema": SCHEMA_ID,
            "machine_id": self.machine_id,
            "seq": self.seq,
            "ts": ts_str,
            "provenance": "SIMULATED",
            "fw": "0.2.0",
            "signals": signals,
            "quality": quality,
            "edge": {
                "delta_t_c": edge_delta_t,
                "power_va": edge_power,
                "trip": self.active_trip,
                "buffered": self.buffered_count,
            },
        }

        # Advance counters
        self.seq += 1
        self.step_idx += 1
        self.current_epoch += self.tick_interval_s

        return payload

    def run_scenario(self, steps: int | None = None) -> list[dict[str, Any]]:
        """Execute the configured scenario for *steps* ticks and collect emitted messages."""
        total_steps = steps or int(self.scenario.get("duration_steps", 100))
        messages: list[dict[str, Any]] = []

        for _ in range(total_steps):
            msg = self.step()
            if msg is not None:
                messages.append(msg)

        return messages
