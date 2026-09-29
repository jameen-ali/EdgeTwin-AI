/**
 * Maintenance event and work-order type definitions.
 */

export type MaintenanceEventType =
  | "INSPECTION"
  | "PART_REPLACEMENT"
  | "OVERHAUL"
  | "LUBRICATION"
  | "CALIBRATION";

export type MaintenanceStatus =
  | "SCHEDULED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "CANCELLED";

export interface MaintenanceItem {
  id: number;
  machine_id: string;
  alert_id: number | null;
  event_type: MaintenanceEventType | string;
  description: string;
  status: MaintenanceStatus | string;
  technician: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface MaintenanceCreatePayload {
  machine_id: string;
  event_type: string;
  description: string;
  status?: string;
  technician?: string | null;
  alert_id?: number | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface MaintenanceUpdatePayload {
  status?: string;
  description?: string;
  technician?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}
