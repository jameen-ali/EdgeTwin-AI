/**
 * Alert type definitions.
 */

export type AlertSeverity = "CRITICAL" | "WARNING" | "INFO";
export type AlertStatus = "ACTIVE" | "OPEN" | "ACKNOWLEDGED" | "RESOLVED";

export interface AlertItem {
  id: number;
  machine_id: string;
  severity: AlertSeverity;
  status: AlertStatus | string;
  rule_id?: string;
  alert_type?: string;
  message: string;
  trigger_conditions?: Record<string, unknown> | null;
  created_at?: string;
  triggered_at?: string;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
  resolved_at?: string | null;
  resolved_by?: string | null;
  top_contributing_factor?: string | null;
  top_factors?: Array<{ factor?: string; feature?: string; shap_value?: number; contribution?: number }> | null;
}

export interface AlertAcknowledgePayload {
  status?: "ACKNOWLEDGED" | "RESOLVED" | string;
  resolved_by?: string | null;
  notes?: string | null;
}
