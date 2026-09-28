/**
 * Scenario injection and chaos simulation types.
 */

export interface ScenarioSummary {
  scenario_id: string;
  name: string;
  description: string;
  category: string;
  severity: "CRITICAL" | "WARNING" | "INFO";
  parameters: Record<string, unknown>;
}

export interface ScenarioInjectPayload {
  scenario_id: string;
  machine_id: string;
  duration_seconds?: number;
  override_params?: Record<string, unknown>;
}
