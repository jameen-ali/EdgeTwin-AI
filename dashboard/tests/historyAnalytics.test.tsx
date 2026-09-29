import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../src/context/AuthContext";
import { HistoryPage } from "../src/pages/HistoryPage";
import { api } from "../src/api/client";
import { MachineSummary } from "../src/types/machine";
import { MachineHistoryResponse, FleetHistoryResponse } from "../src/types/history";

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

const mockMachineHistory: MachineHistoryResponse = {
  machine_id: "MOT-1001",
  machine_type: "Milling",
  current_operating_state: "RUNNING",
  window: "24h",
  from_ts: "2026-09-28T14:00:00Z",
  to_ts: "2026-09-29T14:00:00Z",
  summary: {
    avg_health_score: 88.5,
    min_health_score: 74.0,
    max_health_score: 96.0,
    time_in_warning_s: 180,
    time_in_critical_s: 0,
    alert_count: 2,
    resolved_alert_count: 1,
    maintenance_count: 1,
    avg_failure_probability: 0.08,
    sample_count: 50,
  },
  health_trend: [
    {
      ts: "2026-09-28T14:00:00Z",
      health_score: 96.0,
      health_state: "HEALTHY",
      operating_state: "RUNNING",
      failure_probability: 0.03,
    },
    {
      ts: "2026-09-28T20:00:00Z",
      health_score: 74.0,
      health_state: "WARNING",
      operating_state: "RUNNING",
      failure_probability: 0.17,
    },
    {
      ts: "2026-09-29T14:00:00Z",
      health_score: 92.0,
      health_state: "HEALTHY",
      operating_state: "RUNNING",
      failure_probability: 0.05,
    },
  ],
  sensor_trend: [
    {
      ts: "2026-09-28T14:00:00Z",
      process_temp_c: 42.0,
      air_temp_c: 24.0,
      rotational_speed_rpm: 1520.0,
      torque_nm: 38.0,
      vibration_mm_s: 1.8,
      pressure_bar: 5.0,
      current_a: 11.5,
      voltage_v: 400.0,
      power_va: 4600.0,
      tool_wear_min: 80.0,
    },
    {
      ts: "2026-09-28T20:00:00Z",
      process_temp_c: 62.5,
      air_temp_c: 25.0,
      rotational_speed_rpm: 1480.0,
      torque_nm: 45.0,
      vibration_mm_s: 4.8,
      pressure_bar: 5.2,
      current_a: 14.5,
      voltage_v: 402.0,
      power_va: 5800.0,
      tool_wear_min: 110.0,
    },
    {
      ts: "2026-09-29T14:00:00Z",
      process_temp_c: 44.0,
      air_temp_c: 24.5,
      rotational_speed_rpm: 1510.0,
      torque_nm: 39.0,
      vibration_mm_s: 2.1,
      pressure_bar: 5.0,
      current_a: 12.0,
      voltage_v: 401.0,
      power_va: 4800.0,
      tool_wear_min: 140.0,
    },
  ],
  prediction_history: [
    {
      id: 101,
      ts: "2026-09-28T20:00:00Z",
      failure_probability: 0.17,
      failure_prediction: 1,
      risk_band: "HIGH",
      anomaly_score: 0.42,
      anomaly_flag: true,
      model_version: "v1.2-xgb",
      top_factors: [{ feature: "Process_Temperature_C", shap_value: 0.35 }],
    },
    {
      id: 102,
      ts: "2026-09-29T14:00:00Z",
      failure_probability: 0.05,
      failure_prediction: 0,
      risk_band: "LOW",
      anomaly_score: 0.12,
      anomaly_flag: false,
      model_version: "v1.2-xgb",
      top_factors: [{ feature: "Rotational_Speed_RPM", shap_value: -0.05 }],
    },
  ],
  alerts: [
    {
      id: 1,
      alert_type: "PREDICTIVE_FAILURE_WARNING",
      severity: "WARNING",
      status: "OPEN",
      message: "Process temperature elevated above normal zone",
      triggered_at: "2026-09-28T20:00:00Z",
      acknowledged_at: null,
      resolved_at: null,
      resolved_by: null,
    },
    {
      id: 2,
      alert_type: "VIBRATION_EXCURSION",
      severity: "INFO",
      status: "RESOLVED",
      message: "Transient vibration spike resolved",
      triggered_at: "2026-09-28T16:00:00Z",
      acknowledged_at: "2026-09-28T16:05:00Z",
      resolved_at: "2026-09-28T17:00:00Z",
      resolved_by: "operator_alex",
    },
  ],
  maintenance: [
    {
      id: 501,
      alert_id: 1,
      event_type: "INSPECTION",
      description: "Inspect coolant flow and clean fan cowl",
      status: "SCHEDULED",
      technician: "TECH-007",
      started_at: null,
      completed_at: null,
      created_at: "2026-09-28T20:15:00Z",
    },
  ],
  is_downsampled: false,
  downsample_interval_s: null,
};

const mockFleetHistory: FleetHistoryResponse = {
  window: "24h",
  from_ts: "2026-09-28T14:00:00Z",
  to_ts: "2026-09-29T14:00:00Z",
  total_machines: 2,
  avg_fleet_health: 83.5,
  health_distribution: {
    healthy: 1,
    warning: 1,
    critical: 0,
    offline: 0,
  },
  risk_distribution: {
    low: 1,
    medium: 1,
    high: 0,
    critical: 0,
  },
  alerts_by_machine: [
    { machine_id: "MOT-1001", alert_count: 2, critical_count: 0 },
    { machine_id: "PMP-2002", alert_count: 0, critical_count: 0 },
  ],
  machine_summaries: [
    {
      machine_id: "MOT-1001",
      machine_type: "Milling",
      location: "Cell-A",
      operating_state: "RUNNING",
      health_state: "HEALTHY",
      health_score: 95.0,
      failure_probability: 0.05,
      alert_count: 2,
      maintenance_count: 1,
    },
    {
      machine_id: "PMP-2002",
      machine_type: "Pump",
      location: "Cell-B",
      operating_state: "RUNNING",
      health_state: "WARNING",
      health_score: 72.0,
      failure_probability: 0.28,
      alert_count: 0,
      maintenance_count: 0,
    },
  ],
};

const renderHistoryPage = (initialEntries: string[] = ["/history"]) => {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <AuthProvider>
        <HistoryPage />
      </AuthProvider>
    </MemoryRouter>
  );
};

describe("HistoryPage & Analytics (T-057)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem("edgetwin_token", "fake_jwt");
    localStorage.setItem("edgetwin_user", JSON.stringify({ username: "engineer_jane", role: "MAINTENANCE_ENGINEER" }));

    vi.spyOn(api.machines, "list").mockResolvedValue(mockMachines);
    vi.spyOn(api.history, "getFleetHistory").mockResolvedValue(mockFleetHistory);
    vi.spyOn(api.history, "getMachineHistory").mockResolvedValue(mockMachineHistory);
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("renders page header and scope/horizon selector controls", async () => {
    renderHistoryPage();

    expect(screen.getByText("Historical Analytics")).toBeInTheDocument();
    expect(screen.getByText("T-057 RETROSPECTIVE")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByLabelText(/Scope:/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Horizon:/i)).toBeInTheDocument();
    });
  });

  it("renders fleet overview by default with KPI distribution cards", async () => {
    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByText("Total Fleet Assets")).toBeInTheDocument();
      expect(screen.getByText("2 Machines")).toBeInTheDocument();
      expect(screen.getByText("Fleet Avg Health")).toBeInTheDocument();
      expect(screen.getByText("Fleet Health Distribution")).toBeInTheDocument();
      expect(screen.getByText("Model Failure Risk Bands ($t^*=0.160$)")).toBeInTheDocument();
    });
  });

  it("switches to machine scope and renders machine history panels", async () => {
    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByLabelText(/Scope:/i)).toBeInTheDocument();
    });

    const select = screen.getByLabelText(/Scope:/i);
    fireEvent.change(select, { target: { value: "MOT-1001" } });

    await waitFor(() => {
      expect(api.history.getMachineHistory).toHaveBeenCalledWith("MOT-1001", { window: "24h" });
      expect(screen.getByText("Machine Health Trend")).toBeInTheDocument();
      expect(screen.getByText("Sensor Telemetry History")).toBeInTheDocument();
      expect(screen.getByText(/Persisted Model Assessments/i)).toBeInTheDocument();
      expect(screen.getByText(/Alerts Timeline/i)).toBeInTheDocument();
    });
  });

  it("switches time window horizon and triggers reload", async () => {
    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByLabelText(/Horizon:/i)).toBeInTheDocument();
    });

    const windowSelect = screen.getByLabelText(/Horizon:/i);
    fireEvent.change(windowSelect, { target: { value: "7d" } });

    await waitFor(() => {
      expect(api.history.getFleetHistory).toHaveBeenCalledWith({ window: "7d" });
    });
  });

  it("allows switching sensor metrics in sensor chart", async () => {
    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByLabelText(/Scope:/i)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/Scope:/i), { target: { value: "MOT-1001" } });

    await waitFor(() => {
      expect(screen.getByText("Sensor Telemetry History")).toBeInTheDocument();
    });

    // Switch to Vibration RMS
    const vibrationBtn = screen.getByRole("button", { name: "Vibration RMS" });
    fireEvent.click(vibrationBtn);

    expect(screen.getByText("Vibration RMS")).toBeInTheDocument();
  });

  it("filters incident alerts by status in event timeline", async () => {
    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByLabelText(/Scope:/i)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/Scope:/i), { target: { value: "MOT-1001" } });

    await waitFor(() => {
      expect(screen.getByText("Process temperature elevated above normal zone")).toBeInTheDocument();
    });

    // Filter by Open
    const openBtn = screen.getByRole("button", { name: "Open" });
    fireEvent.click(openBtn);

    expect(screen.getByText("Process temperature elevated above normal zone")).toBeInTheDocument();
    expect(screen.queryByText("Transient vibration spike resolved")).not.toBeInTheDocument();

    // Filter by Resolved
    const resolvedBtn = screen.getByRole("button", { name: "Resolved" });
    fireEvent.click(resolvedBtn);

    expect(screen.getByText("Transient vibration spike resolved")).toBeInTheDocument();
    expect(screen.queryByText("Process temperature elevated above normal zone")).not.toBeInTheDocument();
  });

  it("switches to maintenance tab in event timeline", async () => {
    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByLabelText(/Scope:/i)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/Scope:/i), { target: { value: "MOT-1001" } });

    await waitFor(() => {
      expect(screen.getByText(/Maintenance Activity/i)).toBeInTheDocument();
    });

    const maintTab = screen.getByRole("button", { name: /Maintenance Activity/i });
    fireEvent.click(maintTab);

    expect(screen.getByText("Inspect coolant flow and clean fan cowl")).toBeInTheDocument();
    expect(screen.getByText("WO-501")).toBeInTheDocument();
    expect(screen.getByText("TECH-007")).toBeInTheDocument();
  });

  it("drills down from fleet machine table into specific machine history", async () => {
    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByText("Machine Operational Performance Retrospective")).toBeInTheDocument();
    });

    const viewButtons = screen.getAllByRole("button", { name: "View History →" });
    expect(viewButtons.length).toBeGreaterThan(0);

    fireEvent.click(viewButtons[0]);

    await waitFor(() => {
      expect(api.history.getMachineHistory).toHaveBeenCalledWith("MOT-1001", { window: "24h" });
    });
  });

  it("renders error state when API fails with retry option", async () => {
    vi.spyOn(api.history, "getFleetHistory").mockRejectedValue(new Error("Database connection refused"));

    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByText("Failed to Load Historical Data")).toBeInTheDocument();
      expect(screen.getByText(/Database connection refused/i)).toBeInTheDocument();
    });

    // Test retry
    vi.spyOn(api.history, "getFleetHistory").mockResolvedValue(mockFleetHistory);
    const retryBtn = screen.getByRole("button", { name: /Retry/i });
    fireEvent.click(retryBtn);

    await waitFor(() => {
      expect(screen.queryByText("Failed to Load Historical Data")).not.toBeInTheDocument();
    });
  });

  it("renders truthful empty states when a machine has no history recorded", async () => {
    const emptyMachineHistory: MachineHistoryResponse = {
      ...mockMachineHistory,
      health_trend: [],
      sensor_trend: [],
      prediction_history: [],
      alerts: [],
      maintenance: [],
      summary: {
        ...mockMachineHistory.summary,
        avg_health_score: null,
        min_health_score: null,
        max_health_score: null,
        alert_count: 0,
        maintenance_count: 0,
        sample_count: 0,
      },
    };

    vi.spyOn(api.history, "getMachineHistory").mockResolvedValue(emptyMachineHistory);

    renderHistoryPage();

    await waitFor(() => {
      expect(screen.getByLabelText(/Scope:/i)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/Scope:/i), { target: { value: "PMP-2002" } });

    await waitFor(() => {
      expect(screen.getByText("No Historical Health Data")).toBeInTheDocument();
      expect(screen.getByText("No Historical Sensor Telemetry")).toBeInTheDocument();
      expect(screen.getByText("No Historical Predictions")).toBeInTheDocument();
      expect(screen.getByText("No Incident Alerts")).toBeInTheDocument();
    });
  });
});
