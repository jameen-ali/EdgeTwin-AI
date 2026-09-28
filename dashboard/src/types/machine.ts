/**
 * Machine, Telemetry, and Digital Twin type definitions.
 * Conforms to canonical backend and firmware state definitions:
 * - Health: HEALTHY, WARNING, CRITICAL, MAINTENANCE REQUIRED, OFFLINE
 * - Operating: RUNNING, TRIPPED
 * - Connectivity: LIVE, STALE, OFFLINE
 */

export type OperatingState = "RUNNING" | "TRIPPED";
export type HealthState = "HEALTHY" | "WARNING" | "CRITICAL" | "MAINTENANCE REQUIRED" | "OFFLINE";
export type ConnectivityState = "LIVE" | "STALE" | "OFFLINE";

export interface TelemetryReading {
  air_temperature_c: number;
  process_temperature_c: number;
  rotational_speed_rpm: number;
  torque_nm: number;
  tool_wear_min: number;
  vibration_rms: number;
  current_a: number;
  timestamp: string;
}

export interface TwinState {
  machine_id: string;
  machine_type: string;
  operating_state: OperatingState;
  health_state: HealthState;
  connectivity_state: ConnectivityState;
  health_score: number;
  failure_probability: number;
  risk_band: string;
  anomaly_score: number;
  last_telemetry_at: string | null;
  last_prediction_at: string | null;
  reported: Record<string, unknown>;
  derived: Record<string, unknown>;
}

export interface MachineSummary {
  machine_id: string;
  machine_type: string;
  name?: string;
  operating_state: OperatingState;
  health_state: HealthState;
  connectivity_state: ConnectivityState;
  health_score: number;
  failure_probability: number;
  risk_band: string;
  last_telemetry_at: string | null;
  location?: string;
}
