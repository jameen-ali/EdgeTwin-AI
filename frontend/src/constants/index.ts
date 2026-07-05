// ─── App Constants ────────────────────────────────────────────────────────────

export const APP_NAME = 'EdgeTwin AI';
export const APP_VERSION = '1.0.0';

// ─── API ─────────────────────────────────────────────────────────────────────

export const API_BASE_URL = import.meta.env.VITE_API_URL ?? '';
// Use relative path to leverage Vite proxy in dev, or the same host in prod
export const WS_BASE_URL  = import.meta.env.VITE_WS_URL  ?? (typeof window !== 'undefined' ? `ws://${window.location.host}` : 'ws://localhost:8000');
export const API_PREFIX   = '/api/v1';

// ─── Auth ─────────────────────────────────────────────────────────────────────

export const ACCESS_TOKEN_KEY  = 'edgetwin_access_token';
export const REFRESH_TOKEN_KEY = 'edgetwin_refresh_token';
export const USER_KEY          = 'edgetwin_user';

// ─── Auto-escalation ─────────────────────────────────────────────────────────

export const DEFAULT_ESCALATION_TIMEOUT_MINUTES = 5;

// ─── Risk Levels ─────────────────────────────────────────────────────────────

export const RISK_LABELS = {
  low:      'Low',
  medium:   'Medium',
  high:     'High',
  critical: 'Critical',
} as const;

export const RISK_COLORS = {
  low:      '#22c55e',
  medium:   '#f59e0b',
  high:     '#f97316',
  critical: '#ef4444',
} as const;

// ─── Ticket Statuses ─────────────────────────────────────────────────────────

export const TICKET_STATUS_LABELS = {
  open:        'Open',
  assigned:    'Assigned',
  in_progress: 'In Progress',
  repaired:    'Repaired',
  reviewed:    'Reviewed',
  closed:      'Closed',
} as const;

export const TICKET_STATUS_COLORS = {
  open:        'text-red-400',
  assigned:    'text-blue-400',
  in_progress: 'text-amber-400',
  repaired:    'text-purple-400',
  reviewed:    'text-cyan-400',
  closed:      'text-green-400',
} as const;

// ─── Mechanic Status ─────────────────────────────────────────────────────────

export const MECHANIC_STATUS_LABELS = {
  available: 'Available',
  busy:      'Busy',
  offline:   'Offline',
} as const;

export const MECHANIC_STATUS_COLORS = {
  available: 'text-green-400',
  busy:      'text-amber-400',
  offline:   'text-muted-foreground',
} as const;

// ─── Role Labels ─────────────────────────────────────────────────────────────

export const ROLE_LABELS = {
  operator:             'Machine Operator',
  mechanic:             'Mechanic',
  maintenance_manager:  'Maintenance Manager',
  production_manager:   'Production Manager',
  factory_owner:        'Factory Owner',
  admin:                'System Admin',
} as const;

export const ROLE_DASHBOARD_ROUTES = {
  operator:             '/operator',
  mechanic:             '/mechanic',
  maintenance_manager:  '/maintenance',
  production_manager:   '/production',
  factory_owner:        '/owner',
  admin:                '/admin',
} as const;

// ─── Recharts ─────────────────────────────────────────────────────────────────

export const CHART_COLORS = [
  '#06b6d4', // cyan-500
  '#22c55e', // green-500
  '#f59e0b', // amber-500
  '#ef4444', // red-500
  '#a855f7', // purple-500
  '#3b82f6', // blue-500
] as const;

// ─── Sensor Thresholds ───────────────────────────────────────────────────────

export const SENSOR_THRESHOLDS = {
  temperature: { warning: 70, critical: 90 },    // °C
  vibration:   { warning: 5,  critical: 10 },    // mm/s
  pressure:    { warning: 8,  critical: 12 },    // bar
  current:     { warning: 15, critical: 20 },    // A
  rpm:         { warning: 3000, critical: 3600 },
  noise_level: { warning: 80, critical: 95 },    // dB
} as const;
