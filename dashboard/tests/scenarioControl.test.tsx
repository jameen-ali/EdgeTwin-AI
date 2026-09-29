import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "../src/context/AuthContext";
import { MLOpsPage } from "../src/pages/MLOpsPage";
import { ScenariosPage } from "../src/pages/ScenariosPage";
import { api } from "../src/api/client";
import { MachineSummary } from "../src/types/machine";
import { ScenarioSummary, ScenarioInjectResponse } from "../src/types/scenario";
import { MLOpsOverview, ModelRegistry, PromotionGate, AuditLog } from "../src/types/mlops";

const mockMachines: MachineSummary[] = [
  {
    machine_id: "MOT-1001",
    machine_type: "Milling",
    operating_state: "RUNNING",
    health_state: "HEALTHY",
    connectivity_state: "LIVE",
    health_score: 95.0,
    failure_probability: 0.05,
    risk_band: "LOW",
    last_telemetry_at: "2026-09-29T14:00:00Z",
  },
  {
    machine_id: "PMP-2002",
    machine_type: "Pump",
    operating_state: "RUNNING",
    health_state: "WARNING",
    connectivity_state: "LIVE",
    health_score: 72.0,
    failure_probability: 0.28,
    risk_band: "MEDIUM",
    last_telemetry_at: "2026-09-29T14:00:00Z",
  },
];

const mockScenarios: ScenarioSummary[] = [
  {
    scenario_id: "SCN-01",
    name: "Healthy Nominal",
    description: "Standard operating conditions with stable temperatures, nominal RPM, and healthy baseline.",
    target_fault: "None (Nominal Baseline)",
    duration_s: 300,
    category: "healthy",
    severity: "INFO",
  },
  {
    scenario_id: "SCN-02",
    name: "Heat Dissipation Failure",
    description: "Thermal degradation causing process temperature spike above 314K and narrow delta-T.",
    target_fault: "Heat Dissipation Failure (HDF)",
    duration_s: 180,
    category: "thermal",
    severity: "CRITICAL",
  },
  {
    scenario_id: "SCN-03",
    name: "Power Failure Overload",
    description: "Excessive electrical torque load causing power spike above 9000W.",
    target_fault: "Power Failure (PWF)",
    duration_s: 120,
    category: "electrical",
    severity: "CRITICAL",
  },
  {
    scenario_id: "SCN-05",
    name: "Tool Wear Degradation",
    description: "Progressive mechanical tool wear exceeding critical limit (200-240 min).",
    target_fault: "Tool Wear Failure (TWF)",
    duration_s: 240,
    category: "mechanical",
    severity: "WARNING",
  },
];

const mockOverview: MLOpsOverview = {
  model_name: "edgetwin-risk",
  model_version: "v1.2-xgb",
  registered_alias: "champion",
  operational_threshold: 0.16,
  last_evaluated_at: "2026-09-29T14:00:00Z",
  drift: {
    model_version: "v1.2-xgb",
    reference_version: "v1.0-train-split",
    overall_status: "STABLE",
    reference_sample_count: 6897,
    current_sample_count: 100,
    window_description: "rolling 24h",
    generated_at: "2026-09-29T14:00:00Z",
    drifting_features_count: 0,
    watch_features_count: 0,
    stable_features_count: 14,
    drift_alerts: [],
    features: [],
  },
  performance: {
    window: "all",
    total_feedback: 10,
    confirmed_count: 8,
    false_alarm_count: 2,
    inconclusive_count: 0,
    precision: 0.80,
    recall: 1.0,
    false_alarm_rate: 0.20,
    status: "SUFFICIENT",
    note: "10 evaluated labels",
    generated_at: "2026-09-29T14:00:00Z",
  },
};

const mockRegistry: ModelRegistry = {
  model_name: "edgetwin-risk",
  total_versions: 1,
  champion_version: "1",
  challenger_version: null,
  versions: [
    {
      version: "1",
      status: "READY",
      aliases: ["champion"],
      run_id: "run-001",
      created_at: 1727600000000,
      val_recall_at_t_star: 0.8195,
      val_precision_at_t_star: 0.7610,
      val_pr_auc: 0.8969,
      val_roc_auc: 0.9450,
    },
  ],
  generated_at: "2026-09-29T14:00:00Z",
};

const mockGate: PromotionGate = {
  gate_passed: true,
  challenger_version: "2",
  champion_version: "1",
  challenger_val_recall: 0.8350,
  challenger_val_precision: 0.7720,
  challenger_val_pr_auc: 0.9025,
  champion_val_recall: 0.8195,
  champion_val_precision: 0.7610,
  champion_val_pr_auc: 0.8969,
  recall_delta: 0.0155,
  precision_delta: 0.0110,
  pr_auc_delta: 0.0056,
  checks_passed: ["technical_inference_gate: PASSED"],
  checks_failed: [],
  gate_reason: "All gates passed.",
  technical_gate: { status: "PASSED" },
  evaluated_at: "2026-09-29T14:00:00Z",
};

const mockAuditLog: AuditLog = {
  total_entries: 0,
  entries: [],
  generated_at: "2026-09-29T14:00:00Z",
};

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <BrowserRouter>
      <AuthProvider>{ui}</AuthProvider>
    </BrowserRouter>
  );
}

describe("MLOps Page & Scenario-Control UI (T-058)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    localStorage.setItem("edgetwin_token", "admin-token");
    vi.spyOn(api.auth, "getMe").mockResolvedValue({
      id: 1,
      username: "admin_tester",
      role: "ADMIN",
      is_active: true,
      created_at: "2026-09-29T00:00:00Z",
    });

    vi.spyOn(api.machines, "list").mockResolvedValue(mockMachines);
    vi.spyOn(api.scenarios, "list").mockResolvedValue(mockScenarios);
    vi.spyOn(api.mlops, "getOverview").mockResolvedValue(mockOverview);
    vi.spyOn(api.retrain, "getRegistry").mockResolvedValue(mockRegistry);
    vi.spyOn(api.retrain, "getGate").mockResolvedValue(mockGate);
    vi.spyOn(api.retrain, "getAuditLog").mockResolvedValue(mockAuditLog);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("renders 3 MLOps navigation tabs and switches to Scenario Control", async () => {
    renderWithProviders(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("MLOps & Model Monitoring")).toBeInTheDocument();
    });

    // Check tabs
    expect(screen.getByRole("button", { name: /Drift & Performance/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Model Lifecycle & Governance/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Scenario Control/i })).toBeInTheDocument();

    // Click Scenario Control tab
    fireEvent.click(screen.getByRole("button", { name: /Scenario Control/i }));

    await waitFor(() => {
      expect(screen.getByText("Scenario Dispatch & Demonstration Control")).toBeInTheDocument();
    });
    expect(screen.getByText(/DEMO \/ SIMULATION CONTROL/i)).toBeInTheDocument();
  });

  it("loads available machines and supported scenario presets into selectors", async () => {
    renderWithProviders(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("MLOps & Model Monitoring")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Scenario Control/i }));

    await waitFor(() => {
      expect(screen.getByText("Target Asset (Machine)")).toBeInTheDocument();
    });

    // Check machine selector options
    const machineSelect = screen.getByLabelText(/Target Machine/i) as HTMLSelectElement;
    expect(machineSelect.value).toBe("MOT-1001");
    expect(screen.getByText(/MOT-1001 — Milling/i)).toBeInTheDocument();
    expect(screen.getByText(/PMP-2002 — Pump/i)).toBeInTheDocument();

    // Check scenario selector options
    const scenarioSelect = screen.getByLabelText(/Simulation Scenario/i) as HTMLSelectElement;
    expect(scenarioSelect.value).toBe("SCN-01");
    expect(screen.getByText(/\[SCN-01\] Healthy Nominal/i)).toBeInTheDocument();
    expect(screen.getByText(/\[SCN-02\] Heat Dissipation Failure/i)).toBeInTheDocument();
  });

  it("updates preview card when selecting different machine and scenario presets", async () => {
    renderWithProviders(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("MLOps & Model Monitoring")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Scenario Control/i }));

    await waitFor(() => {
      expect(screen.getByText("Target Asset (Machine)")).toBeInTheDocument();
    });

    // Change machine to PMP-2002
    const machineSelect = screen.getByLabelText(/Target Machine/i);
    fireEvent.change(machineSelect, { target: { value: "PMP-2002" } });

    // Change scenario to SCN-02
    const scenarioSelect = screen.getByLabelText(/Simulation Scenario/i);
    fireEvent.change(scenarioSelect, { target: { value: "SCN-02" } });

    // Verify preview card shows updated info
    expect(screen.getByText(/Thermal degradation causing process temperature spike/i)).toBeInTheDocument();
    expect(screen.getByText("Heat Dissipation Failure (HDF)")).toBeInTheDocument();
    expect(screen.getByText("180s (3.0m)")).toBeInTheDocument();
    expect(screen.getByText(/PMP-2002 \(Pump\)/i)).toBeInTheDocument();
  });

  it("prevents unauthorized OPERATOR users from dispatching scenarios", async () => {
    vi.spyOn(api.auth, "getMe").mockResolvedValue({
      id: 2,
      username: "operator_bill",
      role: "OPERATOR",
      is_active: true,
      created_at: "2026-09-29T00:00:00Z",
    });

    renderWithProviders(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("MLOps & Model Monitoring")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Scenario Control/i }));

    await waitFor(() => {
      expect(screen.getByText(/Read-only: Requires Maintenance Engineer or Admin role to inject/i)).toBeInTheDocument();
    });

    // Dispatch button is disabled for Operator role
    const dispatchBtn = screen.getByRole("button", { name: /Inject Scenario \(Unauthorized\)/i });
    expect(dispatchBtn).toBeDisabled();
  });

  it("opens confirmation modal and allows cancel without making API request", async () => {
    const injectSpy = vi.spyOn(api.scenarios, "inject");

    renderWithProviders(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("MLOps & Model Monitoring")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Scenario Control/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Restore Nominal Baseline/i })).toBeInTheDocument();
    });

    // Click to open confirmation modal (SCN-01 default)
    fireEvent.click(screen.getByRole("button", { name: /Restore Nominal Baseline/i }));

    // Modal is open
    expect(screen.getByText(/Confirm Scenario Dispatch/i)).toBeInTheDocument();
    expect(screen.getByText(/You are about to dispatch a controlled simulation scenario command/i)).toBeInTheDocument();

    // Click Cancel
    fireEvent.click(screen.getByRole("button", { name: /Cancel/i }));

    // Modal should close and inject should NOT be called
    await waitFor(() => {
      expect(screen.queryByText(/Confirm Scenario Dispatch/i)).not.toBeInTheDocument();
    });
    expect(injectSpy).not.toHaveBeenCalled();
  });

  it("dispatches scenario on confirmation and adds to session command acknowledgment log", async () => {
    const mockInjectResponse: ScenarioInjectResponse = {
      status: "ACCEPTED",
      machine_id: "MOT-1001",
      scenario_id: "SCN-02",
      command_id: "cmd-scn-02-test-12345",
      message: "Scenario SCN-02 dispatched successfully to MOT-1001",
      injected_by: "admin_tester",
      injected_at: "2026-09-29T14:30:00Z",
    };

    const injectSpy = vi.spyOn(api.scenarios, "inject").mockResolvedValue(mockInjectResponse);

    renderWithProviders(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("MLOps & Model Monitoring")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Scenario Control/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/Simulation Scenario/i)).toBeInTheDocument();
    });

    // Select SCN-02
    fireEvent.change(screen.getByLabelText(/Simulation Scenario/i), {
      target: { value: "SCN-02" },
    });

    // Open modal via Inject Scenario... button
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Inject Scenario…/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /Inject Scenario…/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Confirm & Dispatch Scenario/i })).toBeInTheDocument();
    });

    // Confirm dispatch
    fireEvent.click(screen.getByRole("button", { name: /Confirm & Dispatch Scenario/i }));

    await waitFor(() => {
      expect(injectSpy).toHaveBeenCalledTimes(1);
      expect(injectSpy).toHaveBeenCalledWith({
        machine_id: "MOT-1001",
        scenario_id: "SCN-02",
      });
    });

    // Modal closes on success
    await waitFor(() => {
      expect(screen.queryByText(/Confirm Scenario Dispatch/i)).not.toBeInTheDocument();
    });

    // Session command acknowledgment log table contains the new entry
    expect(screen.getByTitle("cmd-scn-02-test-12345")).toBeInTheDocument();
    expect(screen.getAllByText(/ACCEPTED/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Scenario SCN-02 dispatched successfully to MOT-1001")).toBeInTheDocument();
  });

  it("handles backend 403 Forbidden error gracefully inside confirmation modal", async () => {
    vi.spyOn(api.scenarios, "inject").mockRejectedValue(
      new Error("Forbidden: Maintenance or Admin role required to inject simulation scenarios.")
    );

    renderWithProviders(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("MLOps & Model Monitoring")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Scenario Control/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Restore Nominal Baseline/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Restore Nominal Baseline/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Confirm & Dispatch Scenario/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Confirm & Dispatch Scenario/i }));

    await waitFor(() => {
      expect(screen.getAllByText(/Forbidden: Maintenance or Admin role required/i).length).toBeGreaterThanOrEqual(1);
    });

    // Modal stays open to inform user of error
    expect(screen.getByText(/Confirm Scenario Dispatch/i)).toBeInTheDocument();
  });

  it("handles empty fleet state gracefully", async () => {
    vi.spyOn(api.machines, "list").mockResolvedValue([]);

    renderWithProviders(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("MLOps & Model Monitoring")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Scenario Control/i }));

    await waitFor(() => {
      expect(screen.getByText("No machines available")).toBeInTheDocument();
    });

    expect(screen.getByText(/No registered machines were found in the fleet/i)).toBeInTheDocument();
  });

  it("handles API loading failure with retry button", async () => {
    vi.spyOn(api.scenarios, "list").mockRejectedValue(new Error("Network Error"));

    renderWithProviders(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("MLOps & Model Monitoring")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Scenario Control/i }));

    await waitFor(() => {
      expect(screen.getByText("Operational Error")).toBeInTheDocument();
      expect(screen.getByText("Network Error")).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: /Retry Request/i })).toBeInTheDocument();
  });

  it("quick Select Baseline (SCN-01) action button switches scenario selection", async () => {
    renderWithProviders(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("MLOps & Model Monitoring")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Scenario Control/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/Simulation Scenario/i)).toBeInTheDocument();
    });

    // First select SCN-03
    fireEvent.change(screen.getByLabelText(/Simulation Scenario/i), {
      target: { value: "SCN-03" },
    });

    const scenarioSelect = screen.getByLabelText(/Simulation Scenario/i) as HTMLSelectElement;
    expect(scenarioSelect.value).toBe("SCN-03");

    // Click "Select Baseline (SCN-01)" button
    const baselineBtn = screen.getByRole("button", { name: /Select Baseline \(SCN-01\)/i });
    expect(baselineBtn).not.toBeDisabled();
    fireEvent.click(baselineBtn);

    // Should now be SCN-01 and button disabled
    expect(scenarioSelect.value).toBe("SCN-01");
    expect(baselineBtn).toBeDisabled();
  });

  it("renders dedicated /scenarios route properly with ScenarioControlPanel", async () => {
    renderWithProviders(<ScenariosPage />);

    await waitFor(() => {
      expect(screen.getByText("Chaos & Fault Injection Scenarios")).toBeInTheDocument();
      expect(screen.getByText("Scenario Dispatch & Demonstration Control")).toBeInTheDocument();
    });
  });
});
