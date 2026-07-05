// ─── User & Auth ────────────────────────────────────────────────────────────

export type UserRole =
  | 'operator'
  | 'mechanic'
  | 'maintenance_manager'
  | 'production_manager'
  | 'factory_owner'
  | 'admin';

export interface User {
  user_id: string;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

// ─── Machine ─────────────────────────────────────────────────────────────────

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';
export type MachineStatus = 'normal' | 'warning' | 'critical' | 'offline';

export interface Machine {
  machine_id: string;
  name: string;
  location: string;
  type: string;
  assigned_operator_id: string | null;
  health_score: number;          // 0-100
  risk_level: RiskLevel;
  rul_hours: number;             // Remaining Useful Life in hours
  status: MachineStatus;
  last_updated: string;
}

// ─── Sensor Readings ──────────────────────────────────────────────────────────

export interface SensorReading {
  reading_id: string;
  machine_id: string;
  timestamp: string;
  temperature: number;
  vibration: number;
  pressure: number;
  current: number;
  rpm: number;
  noise_level: number;
}

// ─── ML Predictions ───────────────────────────────────────────────────────────

export interface MLPrediction {
  prediction_id: string;
  machine_id: string;
  timestamp: string;
  health_score: number;
  risk_level: RiskLevel;
  rul_hours: number;
  failure_type: string;
  confidence: number;
  model_version: string;
}

// ─── Alerts ───────────────────────────────────────────────────────────────────

export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';
export type AlertStatus = 'pending' | 'acknowledged' | 'escalated' | 'resolved';
export type OperatorResponse = 'reported' | 'ignored';

export interface Alert {
  alert_id: string;
  machine_id: string;
  machine_name?: string;
  triggered_at: string;
  severity: AlertSeverity;
  status: AlertStatus;
  operator_response: OperatorResponse | null;
  auto_escalated: boolean;
  escalated_at: string | null;
  prediction?: MLPrediction;
}

// ─── Tickets ──────────────────────────────────────────────────────────────────

export type TicketStatus =
  | 'open'
  | 'assigned'
  | 'accepted'
  | 'in_progress'
  | 'paused'
  | 'repaired'
  | 'reviewed'
  | 'closed';

export interface Ticket {
  ticket_id: string;
  machine_id: string;
  machine_name?: string;
  alert_id: string;
  operator_id: string;
  operator_name?: string;
  mechanic_id: string | null;
  mechanic_name?: string | null;
  manager_id: string | null;
  status: TicketStatus;
  description: string;
  photo_url: string | null;
  voice_note_url: string | null;
  repair_cost: number | null;
  repair_report: string | null;
  parts_used: string | null;
  time_taken_hours: number | null;
  escalated: boolean;
  created_at: string;
  closed_at: string | null;
}

// ─── Mechanic ─────────────────────────────────────────────────────────────────

export type MechanicLoginStatus = 'available' | 'busy' | 'offline';

export interface Mechanic {
  mechanic_id: string;
  name: string;
  email: string;
  skill_type: string;
  login_status: MechanicLoginStatus;
  current_assignment_id: string | null;
  shift: string;
  contact: string;
}

// ─── Cost Log ─────────────────────────────────────────────────────────────────

export interface CostLog {
  cost_id: string;
  ticket_id: string;
  machine_id: string;
  amount: number;
  month: number;
  year: number;
  approved_by: string;
  created_at: string;
}

// ─── Analytics ────────────────────────────────────────────────────────────────

export interface ExpenseSummary {
  period: string;         // "2024-01", "2024"
  total_cost: number;
  ticket_count: number;
  avg_repair_time: number;
  machines: ExpenseByMachine[];
}

export interface ExpenseByMachine {
  machine_id: string;
  machine_name: string;
  total_cost: number;
  ticket_count: number;
}

export interface RiskOverview {
  machine_id: string;
  machine_name: string;
  location: string;
  risk_level: RiskLevel;
  health_score: number;
  rul_hours: number;
  open_tickets: number;
}

export interface ProductionImpact {
  machine_id: string;
  machine_name: string;
  downtime_hours: number;
  production_loss_percent: number;
  risk_level: RiskLevel;
}

// ─── Audit Logs ───────────────────────────────────────────────────────────────

export interface AuditLog {
  log_id: string;
  user_id: string;
  user_name?: string;
  action: string;
  entity_type: string;
  entity_id: string;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  timestamp: string;
  ip_address: string;
}

// ─── Notifications ────────────────────────────────────────────────────────────

export type NotificationType =
  | 'alert_new'
  | 'alert_escalated'
  | 'ticket_assigned'
  | 'ticket_updated'
  | 'ticket_closed'
  | 'mechanic_status'
  | 'risk_update';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  entity_id?: string;
  link?: string;
}

// ─── WebSocket Events ─────────────────────────────────────────────────────────

export interface WSEvent<T = unknown> {
  type: NotificationType;
  payload: T;
  timestamp: string;
}

// ─── API Response wrappers ────────────────────────────────────────────────────

export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ApiError {
  detail: string;
  status_code: number;
}
