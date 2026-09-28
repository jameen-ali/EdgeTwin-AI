/**
 * Alert type definitions.
 */

export type AlertSeverity = "CRITICAL" | "WARNING" | "INFO";
export type AlertStatus = "ACTIVE" | "ACKNOWLEDGED" | "RESOLVED";

export interface AlertItem {
  id: number;
  machine_id: string;
  severity: AlertSeverity;
  status: AlertStatus;
  rule_id: string;
  message: string;
  created_at: string;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
  resolved_at?: string | null;
  resolved_by?: string | null;
  top_contributing_factor?: string | null;
}
