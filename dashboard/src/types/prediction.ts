/**
 * Prediction and Explainability (SHAP) type definitions.
 * Matches backend schemas: PredictionDTO, TwinStateDTO.top_factors, Recommendation.
 */

export interface FeatureContribution {
  feature_name: string;
  feature_value?: number | null;
  shap_value: number;
  abs_magnitude?: number;
  direction?: "increases risk" | "lowers risk" | "neutral" | string;
}

export interface MaintenanceRecommendation {
  action_code: string;
  recommendation_text: string;
  urgency: "ROUTINE" | "LOW" | "MEDIUM" | "HIGH" | "IMMEDIATE" | string;
  target_component: string;
  reason: string;
}

export interface PredictionRecord {
  id?: number;
  machine_id?: string;
  telemetry_id?: number | null;
  ts: string;
  failure_probability: number;
  failure_prediction?: number;
  risk_band: string;
  anomaly_score?: number | null;
  anomaly_flag?: boolean | null;
  health_score?: number | null;
  health_state?: string | null;
  top_factors?: FeatureContribution[] | null;
  model_version?: string;
  inference_latency_ms?: number | null;
  created_at?: string;
}
