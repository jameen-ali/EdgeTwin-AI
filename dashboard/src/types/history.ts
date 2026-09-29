export type HistoryWindow = "1h" | "6h" | "24h" | "7d" | "30d";

export interface HistoricalHealthPoint {
  ts: string;
  health_score: number;
  health_state: string;
  operating_state: string;
  failure_probability: number | null;
}

export interface HistoricalSensorPoint {
  ts: string;
  process_temp_c: number | null;
  air_temp_c: number | null;
  rotational_speed_rpm: number | null;
  torque_nm: number | null;
  vibration_mm_s: number | null;
  pressure_bar: number | null;
  current_a: number | null;
  voltage_v: number | null;
  power_va: number | null;
  tool_wear_min: number | null;
}

export interface HistoricalPredictionPoint {
  id: number;
  ts: string;
  failure_probability: number;
  failure_prediction: number;
  risk_band: string;
  anomaly_score: number | null;
  anomaly_flag: boolean | null;
  model_version: string;
  top_factors: Array<{ feature: string; shap_value: number }> | null;
}

export interface HistoricalAlertItem {
  id: number;
  alert_type: string;
  severity: "INFO" | "WARNING" | "CRITICAL";
  status: "OPEN" | "ACKNOWLEDGED" | "RESOLVED";
  message: string;
  triggered_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  resolved_by: string | null;
}

export interface HistoricalMaintenanceItem {
  id: number;
  alert_id: number | null;
  event_type: string;
  description: string;
  status: "SCHEDULED" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";
  technician: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface MachineHistorySummary {
  avg_health_score: number | null;
  min_health_score: number | null;
  max_health_score: number | null;
  time_in_warning_s: number;
  time_in_critical_s: number;
  alert_count: number;
  resolved_alert_count: number;
  maintenance_count: number;
  avg_failure_probability: number | null;
  sample_count: number;
}

export interface MachineHistoryResponse {
  machine_id: string;
  machine_type: string;
  current_operating_state: string;
  window: string;
  from_ts: string;
  to_ts: string;
  summary: MachineHistorySummary;
  health_trend: HistoricalHealthPoint[];
  sensor_trend: HistoricalSensorPoint[];
  prediction_history: HistoricalPredictionPoint[];
  alerts: HistoricalAlertItem[];
  maintenance: HistoricalMaintenanceItem[];
  is_downsampled: boolean;
  downsample_interval_s: number | null;
}

export interface FleetHealthDistribution {
  healthy: number;
  warning: number;
  critical: number;
  offline: number;
}

export interface FleetRiskDistribution {
  low: number;
  medium: number;
  high: number;
  critical: number;
}

export interface FleetMachineSummary {
  machine_id: string;
  machine_type: string;
  location: string | null;
  operating_state: string;
  health_state: string;
  health_score: number | null;
  failure_probability: number | null;
  alert_count: number;
  maintenance_count: number;
}

export interface FleetAlertCount {
  machine_id: string;
  alert_count: number;
  critical_count: number;
}

export interface FleetHistoryResponse {
  window: string;
  from_ts: string;
  to_ts: string;
  total_machines: number;
  avg_fleet_health: number | null;
  health_distribution: FleetHealthDistribution;
  risk_distribution: FleetRiskDistribution;
  alerts_by_machine: FleetAlertCount[];
  machine_summaries: FleetMachineSummary[];
}
