import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { DashboardPage } from "../src/pages/DashboardPage";
import { AuthProvider } from "../src/context/AuthContext";
import { api } from "../src/api/client";
import { MachineSummary } from "../src/types/machine";
import { AlertItem } from "../src/types/alert";
import * as wsHook from "../src/hooks/useTwinWebSocket";

const mockMachines: MachineSummary[] = [
  {
    machine_id: "MOT-1001",
    machine_type: "Motor",
    location: "Cell A",
    status: "ACTIVE",
    sync_status: "LIVE",
    operating_state: "RUNNING",
    health_state: "HEALTHY",
    connectivity_state: "LIVE",
    health_score: 95.5,
    failure_probability: 0.05,
    risk_band: "LOW",
    last_telemetry_at: "2026-09-28T12:00:00Z",
  },
  {
    machine_id: "PMP-2001",
    machine_type: "Pump",
    location: "Cell B",
    status: "ACTIVE",
    sync_status: "LIVE",
    operating_state: "TRIPPED",
    health_state: "CRITICAL",
    connectivity_state: "LIVE",
    health_score: 35.0,
    failure_probability: 0.82,
    risk_band: "CRITICAL",
    last_telemetry_at: "2026-09-28T12:00:05Z",
  },
  {
    machine_id: "CNC-3001",
    machine_type: "CNC Milling",
    location: "Cell C",
    status: "ACTIVE",
    sync_status: "STALE",
    operating_state: "RUNNING",
    health_state: "WARNING",
    connectivity_state: "STALE",
    health_score: 72.0,
    failure_probability: 0.22,
    risk_band: "MEDIUM",
    last_telemetry_at: "2026-09-28T11:50:00Z",
  },
];

const mockAlerts: AlertItem[] = [
  {
    id: 101,
    machine_id: "PMP-2001",
    severity: "CRITICAL",
    status: "ACTIVE",
    rule_id: "SAFETY_TRIP",
    message: "Hardware safety trip: TRIP_OVERLOAD",
    created_at: "2026-09-28T12:00:05Z",
  },
];

describe("Fleet Dashboard (T-052)", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();

    // Default mock for WebSocket hook
    vi.spyOn(wsHook, "useTwinWebSocket").mockReturnValue({
      status: "CONNECTED",
      twins: {},
      twinList: [],
      isConnected: true,
    });
  });

  const renderDashboard = () => {
    return render(
      <MemoryRouter>
        <AuthProvider>
          <DashboardPage />
        </AuthProvider>
      </MemoryRouter>
    );
  };

  it("renders loading state while fetching machines and alerts", async () => {
    vi.spyOn(api.machines, "list").mockReturnValue(new Promise(() => {}));
    vi.spyOn(api.alerts, "list").mockReturnValue(new Promise(() => {}));

    renderDashboard();
    expect(screen.getByText(/connecting to fleet telemetry service/i)).toBeInTheDocument();
  });

  it("renders truthful empty state when fleet has no registered assets", async () => {
    vi.spyOn(api.machines, "list").mockResolvedValue([]);
    vi.spyOn(api.alerts, "list").mockResolvedValue([]);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText(/no machines registered/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/no active machine assets were found in the database/i)).toBeInTheDocument();
  });

  it("renders error state with retry button when API fails", async () => {
    vi.spyOn(api.machines, "list").mockRejectedValue(new Error("Telemetry service unavailable"));
    vi.spyOn(api.alerts, "list").mockResolvedValue([]);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText(/telemetry service unavailable/i)).toBeInTheDocument();
    });

    const retryBtn = screen.getByRole("button", { name: /retry request/i });
    expect(retryBtn).toBeInTheDocument();
  });

  it("renders fleet KPIs accurately based on fetched machines and alerts", async () => {
    vi.spyOn(api.machines, "list").mockResolvedValue(mockMachines);
    vi.spyOn(api.alerts, "list").mockResolvedValue(mockAlerts);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("MOT-1001")).toBeInTheDocument();
    });

    // Total machines KPI: 3
    expect(screen.getByText("3")).toBeInTheDocument();
    // Active running: 2 running
    expect(screen.getByText(/2 running/i)).toBeInTheDocument();
    // 1 Tripped
    expect(screen.getByText(/1 tripped/i)).toBeInTheDocument();
    // Active alarms KPI: 1 crit · 1 warn
    expect(screen.getByText(/1 crit/i)).toBeInTheDocument();
    // Average health: (95.5 + 35.0 + 72.0) / 3 = 67.5
    expect(screen.getByText("67.5")).toBeInTheDocument();
  });

  it("renders machine directory table with correct columns and status badges", async () => {
    vi.spyOn(api.machines, "list").mockResolvedValue(mockMachines);
    vi.spyOn(api.alerts, "list").mockResolvedValue([]);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("MOT-1001")).toBeInTheDocument();
      expect(screen.getByText("PMP-2001")).toBeInTheDocument();
      expect(screen.getByText("CNC-3001")).toBeInTheDocument();
    });

    // Check operating badges
    expect(screen.getAllByText("RUNNING").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("TRIPPED")).toBeInTheDocument();

    // Check health badges
    expect(screen.getByText("HEALTHY")).toBeInTheDocument();
    expect(screen.getByText("CRITICAL")).toBeInTheDocument();
    expect(screen.getByText("WARNING")).toBeInTheDocument();

    // Check calibrated failure risk highlighting
    expect(screen.getByText("5.0%")).toBeInTheDocument();
    expect(screen.getByText("82.0%")).toBeInTheDocument();
    expect(screen.getByText("22.0%")).toBeInTheDocument();
  });

  it("filters machines by search query", async () => {
    vi.spyOn(api.machines, "list").mockResolvedValue(mockMachines);
    vi.spyOn(api.alerts, "list").mockResolvedValue([]);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("MOT-1001")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search machine id, type.../i);
    fireEvent.change(searchInput, { target: { value: "PMP" } });

    expect(screen.getByText("PMP-2001")).toBeInTheDocument();
    expect(screen.queryByText("MOT-1001")).not.toBeInTheDocument();
    expect(screen.queryByText("CNC-3001")).not.toBeInTheDocument();
  });

  it("filters machines by status tabs", async () => {
    vi.spyOn(api.machines, "list").mockResolvedValue(mockMachines);
    vi.spyOn(api.alerts, "list").mockResolvedValue([]);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("MOT-1001")).toBeInTheDocument();
    });

    // Click "Tripped" tab
    const trippedTab = screen.getByRole("button", { name: /tripped \(1\)/i });
    fireEvent.click(trippedTab);

    expect(screen.getByText("PMP-2001")).toBeInTheDocument();
    expect(screen.queryByText("MOT-1001")).not.toBeInTheDocument();
    expect(screen.queryByText("CNC-3001")).not.toBeInTheDocument();

    // Click "Healthy" tab
    const healthyTab = screen.getByRole("button", { name: /healthy \(1\)/i });
    fireEvent.click(healthyTab);

    expect(screen.getByText("MOT-1001")).toBeInTheDocument();
    expect(screen.queryByText("PMP-2001")).not.toBeInTheDocument();
    expect(screen.queryByText("CNC-3001")).not.toBeInTheDocument();

    // Click "Attention Needed" tab (PMP-2001 is CRITICAL/TRIPPED, CNC-3001 is WARNING / failure_prob > 0.16)
    const attentionTab = screen.getByRole("button", { name: /attention needed \(2\)/i });
    fireEvent.click(attentionTab);

    expect(screen.getByText("PMP-2001")).toBeInTheDocument();
    expect(screen.getByText("CNC-3001")).toBeInTheDocument();
    expect(screen.queryByText("MOT-1001")).not.toBeInTheDocument();
  });

  it("toggles between Table view and Cards view", async () => {
    vi.spyOn(api.machines, "list").mockResolvedValue(mockMachines);
    vi.spyOn(api.alerts, "list").mockResolvedValue([]);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("MOT-1001")).toBeInTheDocument();
    });

    // Default view is table (has table element)
    expect(screen.getByRole("table")).toBeInTheDocument();

    // Toggle to Cards view
    const cardsBtn = screen.getByTitle("Cards view");
    fireEvent.click(cardsBtn);

    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByText("MOT-1001")).toBeInTheDocument();

    // Toggle back to Table view
    const tableBtn = screen.getByTitle("Table view");
    fireEvent.click(tableBtn);

    expect(screen.getByRole("table")).toBeInTheDocument();
  });

  it("displays active alerts and acknowledges them", async () => {
    // Set authenticated user with ADMIN role so RoleGate renders Acknowledge button
    localStorage.setItem("edgetwin_token", "admin-token");
    vi.spyOn(api.auth, "getMe").mockResolvedValue({
      id: 1,
      username: "admin",
      role: "ADMIN",
      is_active: true,
      created_at: "2026-09-28T00:00:00Z",
    });

    vi.spyOn(api.machines, "list").mockResolvedValue(mockMachines);
    vi.spyOn(api.alerts, "list").mockResolvedValue(mockAlerts);
    const ackSpy = vi.spyOn(api.alerts, "acknowledge").mockResolvedValue({ message: "Acknowledged" });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("Hardware safety trip: TRIP_OVERLOAD")).toBeInTheDocument();
    });

    const ackButton = screen.getByRole("button", { name: /acknowledge/i });
    expect(ackButton).toBeInTheDocument();
    fireEvent.click(ackButton);

    await waitFor(() => {
      expect(ackSpy).toHaveBeenCalledWith(101);
    });
  });

  it("merges live WebSocket twin updates reactively into the machine list", async () => {
    vi.spyOn(api.machines, "list").mockResolvedValue(mockMachines);
    vi.spyOn(api.alerts, "list").mockResolvedValue([]);

    // Simulate WebSocket twin update for MOT-1001 transitioning to TRIPPED & CRITICAL
    vi.spyOn(wsHook, "useTwinWebSocket").mockReturnValue({
      status: "CONNECTED",
      twins: {
        "MOT-1001": {
          machine_id: "MOT-1001",
          machine_type: "Motor",
          operating_state: "TRIPPED",
          health_state: "CRITICAL",
          connectivity_state: "LIVE",
          health_score: 22.4,
          failure_probability: 0.94,
          risk_band: "CRITICAL",
          anomaly_score: 0.88,
          last_telemetry_at: "2026-09-28T12:01:00Z",
          last_prediction_at: "2026-09-28T12:01:00Z",
          reported: {},
          derived: {},
        },
      },
      twinList: [],
      isConnected: true,
    });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("MOT-1001")).toBeInTheDocument();
    });

    // The health score for MOT-1001 should now be 22.4 (from WebSocket live twin)
    expect(screen.getByText("22.4")).toBeInTheDocument();
    // The failure probability should now be 94.0%
    expect(screen.getByText("94.0%")).toBeInTheDocument();
  });
});
