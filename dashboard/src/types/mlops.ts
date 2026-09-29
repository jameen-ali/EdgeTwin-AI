/**
 * MLOps drift monitoring and feedback performance type definitions (T-060).
 */

export type DriftStatusType = "STABLE" | "WATCH" | "DRIFT" | "INSUFFICIENT_DATA";

export interface FeatureDrift {
  feature_name: string;
  feature_type: "numeric" | "categorical" | string;
  reference_count: number;
  current_count: number;
  psi: number | null;
  ks_statistic: number | null;
  ks_p_value: number | null;
  missing_reference_pct: number;
  missing_current_pct: number;
  status: DriftStatusType;
  message: string;
  details?: Record<string, any>;
}

export interface DriftAlert {
  feature_name: string;
  severity: "WARNING" | "CRITICAL";
  metric: string;
  value: number;
  threshold: number;
  message: string;
  recommendation: string;
}

export interface DriftReport {
  model_version: string;
  reference_version: string;
  overall_status: DriftStatusType;
  reference_sample_count: number;
  current_sample_count: number;
  window_description: string;
  generated_at: string;
  features: FeatureDrift[];
  drift_alerts: DriftAlert[];
  drifting_features_count: number;
  watch_features_count: number;
  stable_features_count: number;
}

export interface PerformanceMetrics {
  window: string;
  total_feedback: number;
  confirmed_count: number;
  false_alarm_count: number;
  inconclusive_count: number;
  precision: number | null;
  recall: number | null;
  false_alarm_rate: number | null;
  status: "SUFFICIENT" | "INSUFFICIENT_DATA";
  note: string;
  generated_at: string;
}

export interface MLOpsOverview {
  model_name: string;
  model_version: string;
  registered_alias: string;
  operational_threshold: number;
  drift: DriftReport;
  performance: PerformanceMetrics;
  last_evaluated_at: string;
}
