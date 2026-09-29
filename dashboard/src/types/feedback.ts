/**
 * Operator / engineer feedback type definitions.
 */

export type FeedbackType = "CONFIRMED" | "FALSE_ALARM";

export interface FeedbackItem {
  id: number;
  machine_id: string;
  alert_id: number | null;
  feedback_type: FeedbackType | string;
  notes: string | null;
  user_id: string | null;
  created_at: string;
}

export interface FeedbackCreatePayload {
  prediction_id?: number | null;
  alert_id?: number | null;
  feedback_type?: FeedbackType | string;
  ground_truth_failure?: boolean | null;
  notes?: string | null;
  technician_id?: string | null;
}
