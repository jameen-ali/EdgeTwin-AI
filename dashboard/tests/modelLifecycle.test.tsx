import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MLOpsPage } from "../src/pages/MLOpsPage";
import { api } from "../src/api/client";
import {
  MLOpsOverview,
  ModelRegistry,
  PromotionGate,
  AuditLog,
} from "../src/types/mlops";

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
  total_versions: 2,
  champion_version: "1",
  challenger_version: "2",
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
    {
      version: "2",
      status: "READY",
      aliases: ["challenger"],
      run_id: "run-002",
      created_at: 1727610000000,
      val_recall_at_t_star: 0.8350,
      val_precision_at_t_star: 0.7720,
      val_pr_auc: 0.9025,
      val_roc_auc: 0.9480,
    },
  ],
  generated_at: "2026-09-29T14:00:00Z",
};

const mockPassingGate: PromotionGate = {
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
  checks_passed: [
    "recall_protection: chall=0.8350 >= champ=0.8195 - 0.05",
    "precision_floor: chall=0.7720 >= 0.1",
    "feature_contract: n_features=14 == 14",
    "calibration_contract: method=sigmoid",
    "threshold_contract: threshold=0.16 == 0.16",
    "technical_inference_gate: PASSED",
  ],
  checks_failed: [],
  gate_reason: "All 6 hard gate checks passed. Challenger v2 is eligible for promotion to champion.",
  technical_gate: { status: "PASSED" },
  evaluated_at: "2026-09-29T14:00:00Z",
};

const mockBlockedGate: PromotionGate = {
  gate_passed: false,
  challenger_version: "2",
  champion_version: "1",
  challenger_val_recall: 0.7000,
  challenger_val_precision: 0.7500,
  challenger_val_pr_auc: 0.8500,
  champion_val_recall: 0.8195,
  champion_val_precision: 0.7610,
  champion_val_pr_auc: 0.8969,
  recall_delta: -0.1195,
  precision_delta: -0.0110,
  pr_auc_delta: -0.0469,
  checks_passed: [
    "precision_floor: chall=0.7500 >= 0.1",
    "feature_contract: n_features=14 == 14",
    "calibration_contract: method=sigmoid",
    "threshold_contract: threshold=0.16 == 0.16",
    "technical_inference_gate: PASSED",
  ],
  checks_failed: [
    "recall_protection: chall=0.7000 < champ=0.8195 - 0.05 = 0.7695",
  ],
  gate_reason: "1 hard gate check(s) failed. Challenger v2 is NOT eligible for promotion.",
  technical_gate: { status: "PASSED" },
  evaluated_at: "2026-09-29T14:00:00Z",
};

const mockAuditLog: AuditLog = {
  total_entries: 3,
  entries: [
    {
      event: "promotion_completed",
      actor: "admin_user",
      timestamp: "2026-09-29T13:00:00Z",
      git_commit: "987abc",
      authorized_train_version: "v1.0-train-split",
      train_sha256: "a".repeat(64),
      val_sha256: "b".repeat(64),
      mlflow_run_id: "run-001",
      challenger_version: "1",
      val_recall: 0.8195,
      val_precision: 0.7610,
      val_pr_auc: 0.8969,
      notes: "Promoted v1 to champion",
      error: "",
    },
    {
      event: "retrain_completed",
      actor: "lead_engineer",
      timestamp: "2026-09-29T12:00:00Z",
      git_commit: "123def",
      authorized_train_version: "v1.0-train-split",
      train_sha256: "a".repeat(64),
      val_sha256: "b".repeat(64),
      mlflow_run_id: "run-002",
      challenger_version: "2",
      val_recall: 0.8350,
      val_precision: 0.7720,
      val_pr_auc: 0.9025,
      notes: "",
      error: "",
    },
  ],
  generated_at: "2026-09-29T14:00:00Z",
};

import React from "react";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "../src/context/AuthContext";

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <BrowserRouter>
      <AuthProvider>{ui}</AuthProvider>
    </BrowserRouter>
  );
}

describe("Model Lifecycle & Governance UI (T-061)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    localStorage.setItem("edgetwin_token", "admin-token");
    vi.spyOn(api.auth, "getMe").mockResolvedValue({
      id: 1,
      username: "admin_test",
      role: "ADMIN",
      is_active: true,
      created_at: "2026-09-29T00:00:00Z",
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("switches to Model Lifecycle & Governance tab and renders registry table", async () => {
    vi.spyOn(api.mlops, "getOverview").mockResolvedValue(mockOverview);
    vi.spyOn(api.retrain, "getRegistry").mockResolvedValue(mockRegistry);
    vi.spyOn(api.retrain, "getGate").mockResolvedValue(mockPassingGate);
    vi.spyOn(api.retrain, "getAuditLog").mockResolvedValue(mockAuditLog);

    renderWithProviders(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("MLOps & Model Monitoring")).toBeInTheDocument();
    });

    // Switch to Lifecycle tab
    const lifecycleTab = screen.getByRole("button", { name: /Model Lifecycle & Governance/i });
    fireEvent.click(lifecycleTab);

    // Verify registry header & versions
    await waitFor(() => {
      expect(screen.getByText("Model Registry Version History")).toBeInTheDocument();
    });

    expect(screen.getAllByText("v1").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("v2").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("● CHAMPION")).toBeInTheDocument();
    expect(screen.getByText("● CHALLENGER")).toBeInTheDocument();
  });

  it("renders passing promotion gate card with metric deltas and criteria checklist", async () => {
    vi.spyOn(api.mlops, "getOverview").mockResolvedValue(mockOverview);
    vi.spyOn(api.retrain, "getRegistry").mockResolvedValue(mockRegistry);
    vi.spyOn(api.retrain, "getGate").mockResolvedValue(mockPassingGate);
    vi.spyOn(api.retrain, "getAuditLog").mockResolvedValue(mockAuditLog);

    renderWithProviders(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("MLOps & Model Monitoring")).toBeInTheDocument();
    });

    // Switch to Lifecycle tab
    fireEvent.click(screen.getByRole("button", { name: /Model Lifecycle & Governance/i }));

    await waitFor(() => {
      expect(screen.getByText("GATE PASSED")).toBeInTheDocument();
    });

    // Check comparison metrics & deltas
    expect(screen.getAllByText("83.5%").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("+1.55 pp")).toBeInTheDocument();
    expect(screen.getByText("+1.10 pp")).toBeInTheDocument();

    // Check criteria checklist
    expect(screen.getByText(/Recall Protection/i)).toBeInTheDocument();
    expect(screen.getByText(/Precision Floor/i)).toBeInTheDocument();
    expect(screen.getByText(/Feature Contract/i)).toBeInTheDocument();

    // Promote button is enabled
    const promoteBtn = screen.getByRole("button", {
      name: /Promote Challenger v2 to Champion/i,
    });
    expect(promoteBtn).toBeEnabled();
  });

  it("renders blocked promotion gate when criteria fail and disables promotion", async () => {
    vi.spyOn(api.mlops, "getOverview").mockResolvedValue(mockOverview);
    vi.spyOn(api.retrain, "getRegistry").mockResolvedValue(mockRegistry);
    vi.spyOn(api.retrain, "getGate").mockResolvedValue(mockBlockedGate);
    vi.spyOn(api.retrain, "getAuditLog").mockResolvedValue(mockAuditLog);

    renderWithProviders(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("MLOps & Model Monitoring")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Model Lifecycle & Governance/i }));

    await waitFor(() => {
      expect(screen.getByText("GATE BLOCKED")).toBeInTheDocument();
    });

    const promoteBtn = screen.getByRole("button", {
      name: /Promote Challenger v2 to Champion/i,
    });
    expect(promoteBtn).toBeDisabled();
  });

  it("handles explicit promotion with confirmation step", async () => {
    vi.spyOn(api.mlops, "getOverview").mockResolvedValue(mockOverview);
    vi.spyOn(api.retrain, "getRegistry").mockResolvedValue(mockRegistry);
    vi.spyOn(api.retrain, "getGate").mockResolvedValue(mockPassingGate);
    vi.spyOn(api.retrain, "getAuditLog").mockResolvedValue(mockAuditLog);

    const promoteSpy = vi.spyOn(api.retrain, "promote").mockResolvedValue({
      promoted: true,
      new_champion_version: "2",
      previous_champion_version: "1",
      actor: "admin_test",
      gate_result: mockPassingGate,
      promoted_at: "2026-09-29T14:30:00Z",
    });

    renderWithProviders(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("MLOps & Model Monitoring")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Model Lifecycle & Governance/i }));

    await waitFor(() => {
      expect(screen.getByText("GATE PASSED")).toBeInTheDocument();
    });

    // Click promote -> shows confirmation prompt
    const promoteBtn = screen.getByRole("button", {
      name: /Promote Challenger v2 to Champion/i,
    });
    fireEvent.click(promoteBtn);

    expect(
      screen.getByText(/Are you sure you want to promote v2 to production champion\?/i)
    ).toBeInTheDocument();

    // Click confirm
    const confirmBtn = screen.getByRole("button", { name: /Confirm Promotion/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(promoteSpy).toHaveBeenCalledTimes(1);
    });
  });

  it("renders retraining and promotion audit trail table", async () => {
    vi.spyOn(api.mlops, "getOverview").mockResolvedValue(mockOverview);
    vi.spyOn(api.retrain, "getRegistry").mockResolvedValue(mockRegistry);
    vi.spyOn(api.retrain, "getGate").mockResolvedValue(mockPassingGate);
    vi.spyOn(api.retrain, "getAuditLog").mockResolvedValue(mockAuditLog);

    renderWithProviders(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("MLOps & Model Monitoring")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Model Lifecycle & Governance/i }));

    await waitFor(() => {
      expect(screen.getByText("Retraining & Promotion Audit Trail")).toBeInTheDocument();
    });

    expect(screen.getByText("promotion_completed")).toBeInTheDocument();
    expect(screen.getByText("retrain_completed")).toBeInTheDocument();
    expect(screen.getByText("lead_engineer")).toBeInTheDocument();
  });
});
