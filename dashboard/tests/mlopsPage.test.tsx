import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MLOpsPage } from "../src/pages/MLOpsPage";
import { api } from "../src/api/client";
import { MLOpsOverview } from "../src/types/mlops";

const mockOverview: MLOpsOverview = {
  model_name: "edgetwin-risk",
  model_version: "v1.2-xgb",
  registered_alias: "champion",
  operational_threshold: 0.16,
  last_evaluated_at: "2026-09-29T14:00:00Z",
  drift: {
    model_version: "v1.2-xgb",
    reference_version: "v1.0-train-split",
    overall_status: "WATCH",
    reference_sample_count: 6897,
    current_sample_count: 100,
    window_description: "Latest 100 observations (rolling 24h)",
    generated_at: "2026-09-29T14:00:00Z",
    drifting_features_count: 0,
    watch_features_count: 1,
    stable_features_count: 13,
    drift_alerts: [
      {
        feature_name: "Vibration_mm_s",
        severity: "WARNING",
        metric: "PSI",
        value: 0.1425,
        threshold: 0.10,
        message: "Feature 'Vibration_mm_s' exhibits moderate distribution shift.",
        recommendation: "Monitor feature over next 24-48 hours.",
      },
    ],
    features: [
      {
        feature_name: "Vibration_mm_s",
        feature_type: "numeric",
        reference_count: 6604,
        current_count: 100,
        psi: 0.1425,
        ks_statistic: 0.0921,
        ks_p_value: 0.0345,
        missing_reference_pct: 4.25,
        missing_current_pct: 2.0,
        status: "WATCH",
        message: "Moderate distribution shift detected.",
      },
      {
        feature_name: "Process_Temperature_C",
        feature_type: "numeric",
        reference_count: 6793,
        current_count: 100,
        psi: 0.0215,
        ks_statistic: 0.0410,
        ks_p_value: 0.4500,
        missing_reference_pct: 1.51,
        missing_current_pct: 0.0,
        status: "STABLE",
        message: "Feature distribution consistent with training reference.",
      },
      {
        feature_name: "Machine_Type",
        feature_type: "categorical",
        reference_count: 6897,
        current_count: 100,
        psi: 0.0180,
        ks_statistic: null,
        ks_p_value: null,
        missing_reference_pct: 0.0,
        missing_current_pct: 0.0,
        status: "STABLE",
        message: "Category distribution consistent with training baseline.",
      },
    ],
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
    note: "Evaluated across 10 operational feedback submissions (8 confirmed true positives, 2 false alarms).",
    generated_at: "2026-09-29T14:00:00Z",
  },
};

const mockInsufficientOverview: MLOpsOverview = {
  model_name: "edgetwin-risk",
  model_version: "v1.2-xgb",
  registered_alias: "champion",
  operational_threshold: 0.16,
  last_evaluated_at: "2026-09-29T14:00:00Z",
  drift: {
    model_version: "v1.2-xgb",
    reference_version: "v1.0-train-split",
    overall_status: "INSUFFICIENT_DATA",
    reference_sample_count: 6897,
    current_sample_count: 5,
    window_description: "Latest 5 observations (rolling 24h)",
    generated_at: "2026-09-29T14:00:00Z",
    drifting_features_count: 0,
    watch_features_count: 0,
    stable_features_count: 0,
    drift_alerts: [],
    features: [
      {
        feature_name: "Vibration_mm_s",
        feature_type: "numeric",
        reference_count: 6604,
        current_count: 5,
        psi: null,
        ks_statistic: null,
        ks_p_value: null,
        missing_reference_pct: 4.25,
        missing_current_pct: 0.0,
        status: "INSUFFICIENT_DATA",
        message: "Insufficient observations (n=5; minimum required n=30).",
      },
    ],
  },
  performance: {
    window: "all",
    total_feedback: 2,
    confirmed_count: 2,
    false_alarm_count: 0,
    inconclusive_count: 0,
    precision: null,
    recall: null,
    false_alarm_rate: null,
    status: "INSUFFICIENT_DATA",
    note: "Insufficient labeled feedback (2 evaluated labels; minimum 5 required for statistical validity).",
    generated_at: "2026-09-29T14:00:00Z",
  },
};

describe("MLOps Page (T-060)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading state while fetching MLOps overview", () => {
    vi.spyOn(api.mlops, "getOverview").mockImplementation(() => new Promise(() => {}));
    render(<MLOpsPage />);
    expect(screen.getByText(/Computing feature drift statistics/i)).toBeInTheDocument();
  });

  it("renders error state when API request fails", async () => {
    vi.spyOn(api.mlops, "getOverview").mockRejectedValue(new Error("Database connection timeout"));
    render(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("Database connection timeout")).toBeInTheDocument();
    });
  });

  it("displays model version, training baseline, cutoff, and KPIs on success", async () => {
    vi.spyOn(api.mlops, "getOverview").mockResolvedValue(mockOverview);
    render(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("MLOps & Model Monitoring")).toBeInTheDocument();
    });

    // Governance bar
    expect(screen.getAllByText("v1.2-xgb").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/v1.0-train-split/)).toBeInTheDocument();
    expect(screen.getAllByText("t* = 0.160").length).toBeGreaterThanOrEqual(1);

    // KPI Cards
    expect(screen.getByText("Overall Drift Status")).toBeInTheDocument();
    expect(screen.getByText("WATCH")).toBeInTheDocument();
    expect(screen.getAllByText("80.0%").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("20.0%").length).toBeGreaterThanOrEqual(1);
  });

  it("displays drift alerts banner when features exceed watch/drift thresholds", async () => {
    vi.spyOn(api.mlops, "getOverview").mockResolvedValue(mockOverview);
    render(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("Active Model & Feature Drift Alerts")).toBeInTheDocument();
    });

    expect(screen.getByText("WARNING")).toBeInTheDocument();
    expect(screen.getByText(/Feature 'Vibration_mm_s' exhibits moderate distribution shift/)).toBeInTheDocument();
  });

  it("renders feature drift table with numeric PSI, KS, and categorical N/A", async () => {
    vi.spyOn(api.mlops, "getOverview").mockResolvedValue(mockOverview);
    render(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("MLOps & Model Monitoring")).toBeInTheDocument();
    });

    // Vibration row values (alert banner also displays Vibration_mm_s, so check multiple)
    expect(screen.getAllByText("Vibration_mm_s").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("0.1425")).toBeInTheDocument();
    expect(screen.getByText("0.0921")).toBeInTheDocument();

    // Machine_Type row (categorical)
    expect(screen.getByText("Machine_Type")).toBeInTheDocument();
    expect(screen.getByText("N/A (Categorical)")).toBeInTheDocument();
  });

  it("filters features table by search query", async () => {
    vi.spyOn(api.mlops, "getOverview").mockResolvedValue(mockOverview);
    render(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("MLOps & Model Monitoring")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("Search features...");
    fireEvent.change(searchInput, { target: { value: "Process" } });

    expect(screen.getByText("Process_Temperature_C")).toBeInTheDocument();
    // Vibration_mm_s remains only in the alert banner (1 element), filtered out from table
    expect(screen.getAllByText("Vibration_mm_s").length).toBe(1);
  });

  it("filters features table by status tabs", async () => {
    vi.spyOn(api.mlops, "getOverview").mockResolvedValue(mockOverview);
    render(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("MLOps & Model Monitoring")).toBeInTheDocument();
    });

    // Click 'Watch' tab (1 feature: Vibration_mm_s)
    const watchTab = screen.getByRole("button", { name: /Watch \(1\)/i });
    fireEvent.click(watchTab);

    // Vibration_mm_s is present in both alert banner and table row
    expect(screen.getAllByText("Vibration_mm_s").length).toBe(2);
    expect(screen.queryByText("Process_Temperature_C")).not.toBeInTheDocument();
  });

  it("handles insufficient data state gracefully with dashes and sample notes", async () => {
    vi.spyOn(api.mlops, "getOverview").mockResolvedValue(mockInsufficientOverview);
    render(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("INSUFFICIENT_DATA")).toBeInTheDocument();
    });

    // Precision & False alarm rate show '—'
    const dashElements = screen.getAllByText("—");
    expect(dashElements.length).toBeGreaterThan(0);

    // Explanatory note displayed
    expect(screen.getByText(/Insufficient labeled feedback \(2 evaluated labels; minimum 5 required/i)).toBeInTheDocument();
    expect(screen.getByText(/Insufficient observations \(n=5; minimum required n=30\)/i)).toBeInTheDocument();
  });

  it("triggers refresh when clicking Refresh button", async () => {
    const getOverviewSpy = vi.spyOn(api.mlops, "getOverview").mockResolvedValue(mockOverview);
    render(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("MLOps & Model Monitoring")).toBeInTheDocument();
    });

    const refreshBtn = screen.getByRole("button", { name: /Refresh/i });
    fireEvent.click(refreshBtn);

    await waitFor(() => {
      expect(getOverviewSpy).toHaveBeenCalledTimes(2);
    });
  });

  it("updates window hours when selecting telemetry window option", async () => {
    const getOverviewSpy = vi.spyOn(api.mlops, "getOverview").mockResolvedValue(mockOverview);
    render(<MLOpsPage />);

    await waitFor(() => {
      expect(screen.getByText("MLOps & Model Monitoring")).toBeInTheDocument();
    });

    const select = screen.getByLabelText("Telemetry Window");
    fireEvent.change(select, { target: { value: "72" } });

    await waitFor(() => {
      expect(getOverviewSpy).toHaveBeenCalledWith({
        window_hours: 72,
        window_days: undefined,
      });
    });
  });
});
