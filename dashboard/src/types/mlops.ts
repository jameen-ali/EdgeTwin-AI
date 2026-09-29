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

// ---------------------------------------------------------------------------
// T-061 Governed Retraining & Promotion Types
// ---------------------------------------------------------------------------

export interface RetrainRequestPayload {
  run_name?: string;
  seed?: number;
  notes?: string;
}

export interface ChallengerResult {
  run_id: string;
  challenger_version: string;
  challenger_uri: string;
  val_recall: number;
  val_precision: number;
  val_pr_auc: number;
  val_roc_auc: number;
  val_f1: number;
  feature_cols: string[];
  artifacts_dir: string;
  authorized_train_version: string;
  train_sha256: string;
  val_sha256: string;
  retrain_timestamp: string;
}

export interface PromotionGate {
  gate_passed: boolean;
  challenger_version: string;
  champion_version: string;
  challenger_val_recall: number | null;
  challenger_val_precision: number | null;
  challenger_val_pr_auc: number | null;
  champion_val_recall: number | null;
  champion_val_precision: number | null;
  champion_val_pr_auc: number | null;
  recall_delta: number | null;
  precision_delta: number | null;
  pr_auc_delta: number | null;
  checks_passed: string[];
  checks_failed: string[];
  gate_reason: string;
  technical_gate: Record<string, any>;
  evaluated_at: string;
}

export interface PromotionResult {
  promoted: boolean;
  new_champion_version: string;
  previous_champion_version: string;
  actor: string;
  gate_result: PromotionGate;
  promoted_at: string;
  notes?: string;
}

export interface RollbackRequestPayload {
  target_version: string;
  reason: string;
}

export interface RollbackResult {
  rolled_back: boolean;
  restored_champion_version: string;
  demoted_version: string;
  actor: string;
  reason: string;
  rolled_back_at: string;
}

export interface ModelVersionSummary {
  version: string;
  status: string;
  aliases: string[];
  run_id?: string | null;
  created_at?: number | null;
  val_recall_at_t_star?: number | null;
  val_precision_at_t_star?: number | null;
  val_pr_auc?: number | null;
  val_roc_auc?: number | null;
}

export interface ModelRegistry {
  model_name: string;
  total_versions: number;
  champion_version: string | null;
  challenger_version: string | null;
  versions: ModelVersionSummary[];
  generated_at: string;
}

export interface AuditLogEntry {
  event: string;
  actor: string;
  timestamp: string;
  git_commit: string;
  authorized_train_version: string;
  train_sha256: string;
  val_sha256: string;
  mlflow_run_id: string;
  challenger_version: string;
  val_recall: number | null;
  val_precision: number | null;
  val_pr_auc: number | null;
  notes: string;
  error: string;
}

export interface AuditLog {
  total_entries: number;
  entries: AuditLogEntry[];
  generated_at: string;
}

