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
  location?: string | null;
  status?: string;
  sync_status?: string | null;
  operating_state: OperatingState | string;
  health_state: HealthState | string;
  connectivity_state: ConnectivityState | string;
  health_score: number;
  failure_probability: number;
  risk_band: string;
  last_telemetry_at: string | null;
  last_telemetry_ts?: string | null;
  updated_at?: string | null;
}

export function normalizeMachine(
  m: Partial<MachineSummary>,
  liveTwin?: TwinState
): MachineSummary {
  const operating_state = liveTwin?.operating_state ?? m.operating_state ?? "RUNNING";
  const health_state = liveTwin?.health_state ?? m.health_state ?? "HEALTHY";
  const connectivity_state = liveTwin?.connectivity_state ?? m.connectivity_state ?? m.sync_status ?? "LIVE";
  const health_score = typeof liveTwin?.health_score === "number"
    ? liveTwin.health_score
    : (typeof m.health_score === "number" ? m.health_score : 100);
  const failure_probability = typeof liveTwin?.failure_probability === "number"
    ? liveTwin.failure_probability
    : (typeof m.failure_probability === "number" ? m.failure_probability : 0.0);
  const risk_band = liveTwin?.risk_band ?? m.risk_band ?? (failure_probability > 0.16 ? "HIGH" : "LOW");
  const last_telemetry_at = liveTwin?.last_telemetry_at ?? m.last_telemetry_at ?? m.last_telemetry_ts ?? null;

  return {
    machine_id: m.machine_id || "UNKNOWN",
    machine_type: m.machine_type || "Induction Motor",
    name: m.name,
    location: m.location || "Cell A",
    status: m.status || "ACTIVE",
    sync_status: m.sync_status || "LIVE",
    operating_state,
    health_state,
    connectivity_state,
    health_score,
    failure_probability,
    risk_band,
    last_telemetry_at,
    last_telemetry_ts: m.last_telemetry_ts ?? null,
    updated_at: m.updated_at ?? null,
  };
}
