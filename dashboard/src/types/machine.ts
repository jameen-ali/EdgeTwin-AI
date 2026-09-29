/**
 * Machine, Telemetry, and Digital Twin type definitions.
 * Conforms to canonical backend and firmware state definitions:
 * - Health: HEALTHY, WARNING, CRITICAL, MAINTENANCE REQUIRED, OFFLINE, STALE
 * - Operating: RUNNING, STOPPED, STARTING, DEGRADING, TRIPPED
 * - Connectivity: LIVE, STALE, OFFLINE
 */

export type OperatingState =
  | "RUNNING"
  | "STOPPED"
  | "STARTING"
  | "DEGRADING"
  | "TRIPPED"
  | string;

export type HealthState =
  | "HEALTHY"
  | "WARNING"
  | "CRITICAL"
  | "MAINTENANCE REQUIRED"
  | "MAINTENANCE_REQUIRED"
  | "OFFLINE"
  | "STALE"
  | string;

export type ConnectivityState = "LIVE" | "STALE" | "OFFLINE" | string;

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

export interface TelemetryPoint {
  id?: number;
  machine_id?: string;
  seq?: number;
  ts: string;
  provenance?: string;
  fw?: string | null;
  air_temp_c?: number | null;
  process_temp_c?: number | null;
  rotational_speed_rpm?: number | null;
  torque_nm?: number | null;
  vibration_mm_s?: number | null;
  pressure_bar?: number | null;
  current_a?: number | null;
  voltage_v?: number | null;
  tool_wear_min?: number | null;
  operating_hours?: number | null;
  quality?: Record<string, any> | null;
  delta_t_c?: number | null;
  power_va?: number | null;
  trip?: string | null;
  buffered?: number;
}

export interface TwinState {
  machine_id: string;
  machine_type?: string;
  operating_state: OperatingState;
  health_state: HealthState;
  connectivity_state?: ConnectivityState;
  sync_status?: string;
  health_score: number | null;
  failure_probability: number | null;
  risk_band: string | null;
  anomaly_score?: number | null;
  anomaly_flag?: boolean | null;
  last_telemetry_at?: string | null;
  last_telemetry_ts?: string | null;
  last_prediction_at?: string | null;
  last_seq?: number | null;
  updated_at?: string | null;
  signals?: Record<string, any>;
  quality?: Record<string, string>;
  edge?: Record<string, any>;
  top_factors?: Array<Record<string, any>> | null;
  recommendation?: Record<string, any> | null;
  model_version?: string;
  provenance?: string;
  fw?: string | null;
  reported?: Record<string, unknown>;
  derived?: Record<string, unknown>;
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

export interface MachineDetail {
  machine_id: string;
  machine_type: string;
  location?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  latest_twin?: TwinState | null;
  latest_telemetry?: {
    id?: number;
    seq?: number;
    ts?: string;
    provenance?: string;
    fw?: string | null;
    signals?: Record<string, number | null>;
    delta_t_c?: number | null;
    power_va?: number | null;
    trip?: string | null;
  } | null;
  latest_prediction?: {
    id?: number;
    ts?: string;
    failure_probability?: number | null;
    risk_band?: string | null;
    health_score?: number | null;
    anomaly_flag?: boolean | null;
    anomaly_score?: number | null;
  } | null;
}

export function normalizeMachine(
  m: Partial<MachineSummary>,
  liveTwin?: TwinState
): MachineSummary {
  const operating_state = liveTwin?.operating_state ?? m.operating_state ?? "RUNNING";
  const health_state = liveTwin?.health_state ?? m.health_state ?? "HEALTHY";
  const connectivity_state =
    liveTwin?.connectivity_state ?? liveTwin?.sync_status ?? m.connectivity_state ?? m.sync_status ?? "LIVE";
  const health_score = typeof liveTwin?.health_score === "number"
    ? liveTwin.health_score
    : (typeof m.health_score === "number" ? m.health_score : 100);
  const failure_probability = typeof liveTwin?.failure_probability === "number"
    ? liveTwin.failure_probability
    : (typeof m.failure_probability === "number" ? m.failure_probability : 0.0);
  const risk_band = liveTwin?.risk_band ?? m.risk_band ?? (failure_probability > 0.16 ? "HIGH" : "LOW");
  const last_telemetry_at =
    liveTwin?.last_telemetry_at ?? liveTwin?.last_telemetry_ts ?? m.last_telemetry_at ?? m.last_telemetry_ts ?? null;

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
