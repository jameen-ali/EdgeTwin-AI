/**
 * Scenario injection and chaos simulation types.
 */

export interface ScenarioSummary {
  scenario_id: string;
  name: string;
  description: string;
  target_fault?: string;
  category?: string;
  severity?: "CRITICAL" | "WARNING" | "INFO";
  duration_s?: number;
  parameters?: Record<string, unknown>;
}

export interface ScenarioListResponse {
  scenarios: ScenarioSummary[];
  total: number;
}

export interface ScenarioInjectPayload {
  machine_id: string;
  scenario_id: string;
  parameters?: Record<string, unknown>;
}

export interface ScenarioInjectResponse {
  command_id: string;
  machine_id: string;
  scenario_id: string;
  status: string;
  message: string;
  injected_by: string;
  injected_at: string;
}
