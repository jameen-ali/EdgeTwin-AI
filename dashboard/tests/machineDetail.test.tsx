import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { MachineDetailPage } from "../src/pages/MachineDetailPage";
import { AuthProvider } from "../src/context/AuthContext";
import { api, ApiError } from "../src/api/client";
import { MachineDetail, TelemetryPoint } from "../src/types/machine";
import * as wsHook from "../src/hooks/useTwinWebSocket";

const mockMachineDetail: MachineDetail = {
  machine_id: "MOT-1001",
  machine_type: "Industrial Induction Motor",
  location: "Sector 4 - Workcell Alpha",
  status: "ACTIVE",
  created_at: "2026-09-20T10:00:00Z",
  updated_at: "2026-09-29T12:00:00Z",
  latest_twin: {
    machine_id: "MOT-1001",
    sync_status: "LIVE",
    operating_state: "RUNNING",
    health_state: "HEALTHY",
    health_score: 94.2,
    failure_probability: 0.04,
    risk_band: "LOW",
    anomaly_flag: false,
    anomaly_score: 0.02,
    model_version: "v1.2-xgb",
    last_seq: 1420,
    last_telemetry_ts: "2026-09-29T12:00:00Z",
    updated_at: "2026-09-29T12:00:00Z",
    signals: {
      process_temp_c: 54.8,
      air_temp_c: 24.1,
      vibration_mm_s: 2.15,
      rotational_speed_rpm: 2950,
      torque_nm: 42.6,
      current_a: 14.8,
      pressure_bar: 5.2,
      voltage_v: 400.1,
      tool_wear_min: 85,
      operating_hours: 1240.5,
    },
  },
  latest_telemetry: {
    id: 9001,
    seq: 1420,
    ts: "2026-09-29T12:00:00Z",
    signals: {
      process_temp_c: 54.8,
      air_temp_c: 24.1,
      vibration_mm_s: 2.15,
      rotational_speed_rpm: 2950,
      torque_nm: 42.6,
      current_a: 14.8,
    },
  },
  latest_prediction: {
    id: 401,
    ts: "2026-09-29T12:00:00Z",
    failure_probability: 0.04,
    risk_band: "LOW",
    health_score: 94.2,
  },
};

const mockTelemetryHistory: TelemetryPoint[] = [
  {
    id: 8998,
    machine_id: "MOT-1001",
    seq: 1417,
    ts: "2026-09-29T11:59:45Z",
    process_temp_c: 53.9,
    air_temp_c: 24.0,
    vibration_mm_s: 2.1,
    rotational_speed_rpm: 2948,
    torque_nm: 42.1,
    current_a: 14.5,
    pressure_bar: 5.2,
    voltage_v: 400.0,
  },
  {
    id: 8999,
    machine_id: "MOT-1001",
    seq: 1418,
    ts: "2026-09-29T11:59:50Z",
    process_temp_c: 54.2,
    air_temp_c: 24.0,
    vibration_mm_s: 2.12,
    rotational_speed_rpm: 2952,
    torque_nm: 42.3,
    current_a: 14.6,
    pressure_bar: 5.2,
    voltage_v: 400.2,
  },
  {
    id: 9000,
    machine_id: "MOT-1001",
    seq: 1419,
    ts: "2026-09-29T11:59:55Z",
    process_temp_c: 54.5,
    air_temp_c: 24.1,
    vibration_mm_s: 2.14,
    rotational_speed_rpm: 2950,
    torque_nm: 42.5,
    current_a: 14.7,
    pressure_bar: 5.2,
    voltage_v: 400.1,
  },
  {
    id: 9001,
    machine_id: "MOT-1001",
    seq: 1420,
    ts: "2026-09-29T12:00:00Z",
    process_temp_c: 54.8,
    air_temp_c: 24.1,
    vibration_mm_s: 2.15,
    rotational_speed_rpm: 2950,
    torque_nm: 42.6,
    current_a: 14.8,
    pressure_bar: 5.2,
    voltage_v: 400.1,
  },
];

describe("Machine Detail & Live Telemetry Monitoring (T-053)", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();

    // Default WebSocket mock: connected, no live updates initially
    vi.spyOn(wsHook, "useTwinWebSocket").mockReturnValue({
      status: "CONNECTED",
      twins: {},
      twinList: [],
      isConnected: true,
    });
  });

  const renderMachineDetail = (initialRoute = "/machines/MOT-1001") => {
    return render(
      <MemoryRouter initialEntries={[initialRoute]}>
        <AuthProvider>
          <Routes>
            <Route path="/machines/:id" element={<MachineDetailPage />} />
            <Route path="/machines" element={<div>Fleet Registry Screen</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );
  };

  // 1. Route test
  it("renders the machine detail route at /machines/:id", async () => {
    vi.spyOn(api.machines, "getDetail").mockResolvedValue(mockMachineDetail);
    vi.spyOn(api.machines, "getTelemetry").mockResolvedValue(mockTelemetryHistory);

    renderMachineDetail("/machines/MOT-1001");

    await waitFor(() => {
      expect(screen.getByText("MOT-1001")).toBeInTheDocument();
    });
    expect(screen.getByText("Industrial Induction Motor")).toBeInTheDocument();
  });

  // 2. Machine loading test
  it("displays machine identity, equipment type, and location on API success", async () => {
    vi.spyOn(api.machines, "getDetail").mockResolvedValue(mockMachineDetail);
    vi.spyOn(api.machines, "getTelemetry").mockResolvedValue(mockTelemetryHistory);

    renderMachineDetail();

    await waitFor(() => {
      expect(screen.getByText("MOT-1001")).toBeInTheDocument();
      expect(screen.getByText("Sector 4 - Workcell Alpha")).toBeInTheDocument();
      expect(screen.getByText("Industrial Induction Motor")).toBeInTheDocument();
    });
  });

  // 3. Machine not found test (404)
  it("displays truthful error state with Return to Fleet action when API returns 404", async () => {
    const error404 = new ApiError("Machine 'UNKNOWN-99' not found.", 404);
    vi.spyOn(api.machines, "getDetail").mockRejectedValue(error404);
    vi.spyOn(api.machines, "getTelemetry").mockResolvedValue([]);

    renderMachineDetail("/machines/UNKNOWN-99");

    await waitFor(() => {
      expect(screen.getByText(/machine not found/i)).toBeInTheDocument();
    });
    expect(
      screen.getByText(/the requested machine "UNKNOWN-99" is not registered in the edgetwin fleet/i)
    ).toBeInTheDocument();

    const returnBtn = screen.getByRole("button", { name: /return to fleet/i });
    expect(returnBtn).toBeInTheDocument();

    fireEvent.click(returnBtn);
    await waitFor(() => {
      expect(screen.getByText("Fleet Registry Screen")).toBeInTheDocument();
    });
  });

  // 4. Twin state test
  it("renders health score, failure probability (t*=0.16), risk band, and operating state", async () => {
    vi.spyOn(api.machines, "getDetail").mockResolvedValue(mockMachineDetail);
    vi.spyOn(api.machines, "getTelemetry").mockResolvedValue(mockTelemetryHistory);

    renderMachineDetail();

    await waitFor(() => {
      expect(screen.getByText("94.2")).toBeInTheDocument();
      expect(screen.getByText("4.0%")).toBeInTheDocument();
      expect(screen.getByText("LOW RISK")).toBeInTheDocument();
      expect(screen.getAllByText("RUNNING").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("HEALTHY").length).toBeGreaterThanOrEqual(1);
    });
  });

  // 5. Current telemetry test
  it("displays current sensor values for temperature, vibration, RPM, torque, and current", async () => {
    vi.spyOn(api.machines, "getDetail").mockResolvedValue(mockMachineDetail);
    vi.spyOn(api.machines, "getTelemetry").mockResolvedValue(mockTelemetryHistory);

    renderMachineDetail();

    await waitFor(() => {
      // Temperature 54.8 °C
      expect(screen.getByText("54.8")).toBeInTheDocument();
      // Vibration 2.15 mm/s
      expect(screen.getByText("2.15")).toBeInTheDocument();
      // RPM 2,950
      expect(screen.getByText("2,950")).toBeInTheDocument();
      // Torque 42.6 Nm
      expect(screen.getByText("42.6")).toBeInTheDocument();
      // Current 14.80 A
      expect(screen.getByText("14.80")).toBeInTheDocument();
    });
  });

  // 6. Historical telemetry test
  it("renders historical telemetry series in charts and allows viewing raw table", async () => {
    vi.spyOn(api.machines, "getDetail").mockResolvedValue(mockMachineDetail);
    vi.spyOn(api.machines, "getTelemetry").mockResolvedValue(mockTelemetryHistory);

    renderMachineDetail();

    await waitFor(() => {
      expect(screen.getByText(/temperature tracking/i)).toBeInTheDocument();
      expect(screen.getByText(/vibration velocity/i)).toBeInTheDocument();
      expect(screen.getByText(/kinematic drive dynamics/i)).toBeInTheDocument();
      expect(screen.getByText(/phase current draw/i)).toBeInTheDocument();
    });

    // Switch to Observations Log (raw table view)
    const logTab = screen.getByRole("button", { name: /observations log/i });
    fireEvent.click(logTab);

    await waitFor(() => {
      expect(screen.getByText("#1420")).toBeInTheDocument();
      expect(screen.getByText("#1417")).toBeInTheDocument();
    });
  });

  // 7. Null telemetry test
  it("truthfully displays '—' for null sensor values and does NOT convert them to zero", async () => {
    const detailWithNulls: MachineDetail = {
      ...mockMachineDetail,
      latest_twin: {
        ...mockMachineDetail.latest_twin!,
        signals: {
          process_temp_c: null,
          air_temp_c: null,
          vibration_mm_s: null,
          rotational_speed_rpm: null,
          torque_nm: null,
          current_a: null,
          pressure_bar: null,
        },
      },
      latest_telemetry: null,
    };

    vi.spyOn(api.machines, "getDetail").mockResolvedValue(detailWithNulls);
    vi.spyOn(api.machines, "getTelemetry").mockResolvedValue([]);

    renderMachineDetail();

    await waitFor(() => {
      expect(screen.getByText("MOT-1001")).toBeInTheDocument();
    });

    // Verify presence of dashes rather than 0
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(5);
  });

  // 8. WebSocket test: Live Twin update changes machine state
  it("updates machine state and failure probability reactively on WebSocket twin update", async () => {
    vi.spyOn(api.machines, "getDetail").mockResolvedValue(mockMachineDetail);
    vi.spyOn(api.machines, "getTelemetry").mockResolvedValue(mockTelemetryHistory);

    // Provide twin update via WebSocket hook
    vi.spyOn(wsHook, "useTwinWebSocket").mockReturnValue({
      status: "CONNECTED",
      twins: {
        "MOT-1001": {
          machine_id: "MOT-1001",
          sync_status: "LIVE",
          operating_state: "TRIPPED",
          health_state: "CRITICAL",
          health_score: 31.5,
          failure_probability: 0.88,
          risk_band: "CRITICAL",
          anomaly_flag: true,
          anomaly_score: 0.95,
          model_version: "v1.2-xgb",
          signals: mockMachineDetail.latest_twin!.signals,
        },
      },
      twinList: [],
      isConnected: true,
    });

    renderMachineDetail();

    await waitFor(() => {
      expect(screen.getByText("31.5")).toBeInTheDocument();
      expect(screen.getByText("88.0%")).toBeInTheDocument();
      expect(screen.getByText("CRITICAL RISK")).toBeInTheDocument();
      expect(screen.getAllByText("TRIPPED").length).toBeGreaterThanOrEqual(1);
    });
  });

  // 9. Live telemetry test: incoming telemetry changes current values
  it("updates sensor metrics dynamically when live telemetry arrives via WebSocket", async () => {
    vi.spyOn(api.machines, "getDetail").mockResolvedValue(mockMachineDetail);
    vi.spyOn(api.machines, "getTelemetry").mockResolvedValue(mockTelemetryHistory);

    vi.spyOn(wsHook, "useTwinWebSocket").mockReturnValue({
      status: "CONNECTED",
      twins: {
        "MOT-1001": {
          ...mockMachineDetail.latest_twin!,
          signals: {
            ...mockMachineDetail.latest_twin!.signals,
            process_temp_c: 82.5,
            vibration_mm_s: 6.88,
            current_a: 32.1,
          },
        },
      },
      twinList: [],
      isConnected: true,
    });

    renderMachineDetail();

    await waitFor(() => {
      // Temperature updated to 82.5
      expect(screen.getByText("82.5")).toBeInTheDocument();
      // Vibration updated to 6.88
      expect(screen.getByText("6.88")).toBeInTheDocument();
      // Current updated to 32.10
      expect(screen.getByText("32.10")).toBeInTheDocument();
    });
  });

  // 10. Connection test: LIVE / STALE / OFFLINE
  it("renders connection status indicators accurately", async () => {
    const staleMachine: MachineDetail = {
      ...mockMachineDetail,
      latest_twin: {
        ...mockMachineDetail.latest_twin!,
        sync_status: "STALE",
      },
    };

    vi.spyOn(api.machines, "getDetail").mockResolvedValue(staleMachine);
    vi.spyOn(api.machines, "getTelemetry").mockResolvedValue(mockTelemetryHistory);

    vi.spyOn(wsHook, "useTwinWebSocket").mockReturnValue({
      status: "DISCONNECTED",
      twins: {},
      twinList: [],
      isConnected: false,
    });

    renderMachineDetail();

    await waitFor(() => {
      expect(screen.getAllByText("STALE").length).toBeGreaterThanOrEqual(1);
    });
  });

  // 11. Empty history test
  it("renders truthful EmptyState when no historical telemetry observations exist", async () => {
    vi.spyOn(api.machines, "getDetail").mockResolvedValue(mockMachineDetail);
    vi.spyOn(api.machines, "getTelemetry").mockResolvedValue([]);

    renderMachineDetail();

    await waitFor(() => {
      expect(screen.getByText(/no historical telemetry available/i)).toBeInTheDocument();
    });
    expect(
      screen.getByText(/telemetry history will appear when this machine begins reporting sensor observations/i)
    ).toBeInTheDocument();
  });

  // 12. Navigation test: Back-to-fleet works
  it("navigates back to fleet directory when 'Fleet' back button is clicked", async () => {
    vi.spyOn(api.machines, "getDetail").mockResolvedValue(mockMachineDetail);
    vi.spyOn(api.machines, "getTelemetry").mockResolvedValue(mockTelemetryHistory);

    renderMachineDetail();

    await waitFor(() => {
      expect(screen.getByText("MOT-1001")).toBeInTheDocument();
    });

    const backBtn = screen.getByRole("button", { name: /return to fleet directory/i });
    expect(backBtn).toBeInTheDocument();

    fireEvent.click(backBtn);

    await waitFor(() => {
      expect(screen.getByText("Fleet Registry Screen")).toBeInTheDocument();
    });
  });
});
