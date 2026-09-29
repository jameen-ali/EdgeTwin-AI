import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { DigitalTwinView } from "../src/components/machine/DigitalTwinView";
import { PredictionPanel } from "../src/components/machine/PredictionPanel";
import { FeatureContributions } from "../src/components/machine/FeatureContributions";
import { RecommendationPanel } from "../src/components/machine/RecommendationPanel";
import { MachineDetailPage } from "../src/pages/MachineDetailPage";
import { AuthProvider } from "../src/context/AuthContext";
import { api } from "../src/api/client";
import { MachineDetail, TelemetryPoint, TwinState } from "../src/types/machine";
import { FeatureContribution, MaintenanceRecommendation } from "../src/types/prediction";
import * as wsHook from "../src/hooks/useTwinWebSocket";

// Sample mock data
const mockTopFactors: FeatureContribution[] = [
  {
    feature_name: "vibration_mm_s",
    feature_value: 8.2,
    shap_value: 0.31,
    abs_magnitude: 0.31,
    direction: "INCREASES_RISK",
  },
  {
    feature_name: "process_temp_c",
    feature_value: 74.2,
    shap_value: 0.22,
    abs_magnitude: 0.22,
    direction: "INCREASES_RISK",
  },
  {
    feature_name: "torque_nm",
    feature_value: 88.0,
    shap_value: 0.14,
    abs_magnitude: 0.14,
    direction: "INCREASES_RISK",
  },
  {
    feature_name: "rotational_speed_rpm",
    feature_value: 1800,
    shap_value: -0.05,
    abs_magnitude: 0.05,
    direction: "LOWERS_RISK",
  },
];

const mockRecommendation: MaintenanceRecommendation = {
  action_code: "INSPECT_BEARING",
  recommendation_text: "Schedule mechanical inspection for front drive-end bearing due to anomalous harmonic vibration.",
  urgency: "HIGH",
  target_component: "Drive End Bearing",
  reason: "Vibration RMS exceeds ISO standard with high model risk attribution",
};

const mockMachineWithPrediction: MachineDetail = {
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
    health_score: 82.4,
    failure_probability: 0.18,
    risk_band: "HIGH",
    anomaly_flag: true,
    anomaly_score: 0.65,
    model_version: "v1.2-xgb",
    last_seq: 1500,
    last_telemetry_ts: "2026-09-29T12:00:00Z",
    updated_at: "2026-09-29T12:00:00Z",
    signals: {
      process_temp_c: 74.2,
      air_temp_c: 25.0,
      vibration_mm_s: 8.2,
      rotational_speed_rpm: 1800,
      torque_nm: 88.0,
      current_a: 24.5,
      pressure_bar: 5.8,
      voltage_v: 400.0,
    },
    top_factors: mockTopFactors,
    recommendation: mockRecommendation,
  },
  latest_telemetry: {
    id: 9500,
    seq: 1500,
    ts: "2026-09-29T12:00:00Z",
    signals: {
      process_temp_c: 74.2,
      vibration_mm_s: 8.2,
      rotational_speed_rpm: 1800,
      torque_nm: 88.0,
      current_a: 24.5,
    },
  },
  latest_prediction: {
    id: 501,
    ts: "2026-09-29T12:00:00Z",
    failure_probability: 0.18,
    risk_band: "HIGH",
    health_score: 82.4,
    anomaly_score: 0.65,
    anomaly_flag: true,
    model_version: "v1.2-xgb",
    top_factors: mockTopFactors,
  },
};

const mockTelemetryHistory: TelemetryPoint[] = [
  {
    id: 9499,
    machine_id: "MOT-1001",
    seq: 1499,
    ts: "2026-09-29T11:59:55Z",
    process_temp_c: 73.8,
    vibration_mm_s: 8.1,
    rotational_speed_rpm: 1800,
    torque_nm: 87.5,
    current_a: 24.2,
  },
  {
    id: 9500,
    machine_id: "MOT-1001",
    seq: 1500,
    ts: "2026-09-29T12:00:00Z",
    process_temp_c: 74.2,
    vibration_mm_s: 8.2,
    rotational_speed_rpm: 1800,
    torque_nm: 88.0,
    current_a: 24.5,
  },
];

const renderMachineDetailPage = (machineId = "MOT-1001") => {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[`/machines/${machineId}`]}>
        <Routes>
          <Route path="/machines/:id" element={<MachineDetailPage />} />
          <Route path="/machines" element={<div>Fleet Registry Screen</div>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
};

describe("T-054 — Digital Twin Visualization", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // 1. Digital Twin renders machine identity
  it("renders machine identity and type accurately", () => {
    render(
      <DigitalTwinView
        machineId="MOT-1001"
        machineType="Industrial Induction Motor"
        operatingState="RUNNING"
        healthState="HEALTHY"
        healthScore={88.5}
      />
    );

    expect(screen.getByText("MOT-1001")).toBeInTheDocument();
    expect(screen.getByText(/Industrial Induction Motor • Real-time operational schematic/i)).toBeInTheDocument();
  });

  // 2. Digital Twin renders operating state
  it("renders operating state badge accurately", () => {
    render(
      <DigitalTwinView
        machineId="MOT-1001"
        operatingState="RUNNING"
        healthState="HEALTHY"
      />
    );

    expect(screen.getByText("RUNNING")).toBeInTheDocument();
  });

  // 3. Digital Twin renders health
  it("renders health score and health badge accurately", () => {
    render(
      <DigitalTwinView
        machineId="MOT-1001"
        operatingState="RUNNING"
        healthState="HEALTHY"
        healthScore={92.4}
      />
    );

    expect(screen.getByText("92.4%")).toBeInTheDocument();
    expect(screen.getByText("HEALTHY")).toBeInTheDocument();
  });

  // 4. Digital Twin renders current sensor values
  it("renders current sensor values with correct units and quality flags", () => {
    render(
      <DigitalTwinView
        machineId="MOT-1001"
        operatingState="RUNNING"
        healthState="HEALTHY"
        healthScore={82.0}
        signals={{
          process_temp_c: 74.2,
          air_temp_c: 25.1,
          vibration_mm_s: 8.2,
          rotational_speed_rpm: 1800,
          torque_nm: 88.0,
          current_a: 24.5,
          voltage_v: 400.0,
        }}
        quality={{
          vibration_mm_s: "LIMIT_WARN",
        }}
      />
    );

    expect(screen.getByText("74.2")).toBeInTheDocument();
    expect(screen.getByText("8.20")).toBeInTheDocument();
    expect(screen.getByText("1,800")).toBeInTheDocument();
    expect(screen.getByText("88.0")).toBeInTheDocument();
    expect(screen.getByText("24.50")).toBeInTheDocument();
    // Quality flag rendered
    expect(screen.getByText("LIMIT_WARN")).toBeInTheDocument();
  });

  // 5. Digital Twin reacts to live WebSocket updates
  it("reacts dynamically to live WebSocket twin updates without reload", async () => {
    vi.spyOn(api.machines, "getDetail").mockResolvedValue(mockMachineWithPrediction);
    vi.spyOn(api.machines, "getTelemetry").mockResolvedValue(mockTelemetryHistory);

    const useTwinWsSpy = vi.spyOn(wsHook, "useTwinWebSocket");
    useTwinWsSpy.mockReturnValue({
      status: "CONNECTED",
      twins: {},
      twinList: [],
      isConnected: true,
    });

    const { rerender } = renderMachineDetailPage();

    await waitFor(() => {
      expect(screen.getAllByText("MOT-1001").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("74.2").length).toBeGreaterThanOrEqual(1);
    });

    // Simulate incoming WebSocket live twin update with new temperature 86.4 and degrading state
    const liveUpdateTwin: TwinState = {
      ...mockMachineWithPrediction.latest_twin!,
      operating_state: "DEGRADING",
      health_score: 68.0,
      signals: {
        ...mockMachineWithPrediction.latest_twin!.signals,
        process_temp_c: 86.4,
        vibration_mm_s: 9.85,
      },
    };

    useTwinWsSpy.mockReturnValue({
      status: "CONNECTED",
      twins: { "MOT-1001": liveUpdateTwin },
      twinList: [liveUpdateTwin],
      isConnected: true,
    });

    rerender(
      <AuthProvider>
        <MemoryRouter initialEntries={["/machines/MOT-1001"]}>
          <Routes>
            <Route path="/machines/:id" element={<MachineDetailPage />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getAllByText("86.4").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("9.85").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("68.0%").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("DEGRADING").length).toBeGreaterThanOrEqual(1);
    });
  });

  // 6. Digital Twin correctly represents LIVE/STALE/OFFLINE
  it("correctly represents LIVE, STALE, and OFFLINE states", () => {
    const { rerender } = render(
      <DigitalTwinView
        machineId="MOT-1001"
        connectivityState="LIVE"
        isLiveWs={true}
      />
    );
    expect(screen.getByText(/TWIN SYNCED/i)).toBeInTheDocument();

    rerender(
      <DigitalTwinView
        machineId="MOT-1001"
        connectivityState="STALE"
        isLiveWs={false}
      />
    );
    expect(screen.getByText("STALE")).toBeInTheDocument();

    rerender(
      <DigitalTwinView
        machineId="MOT-1001"
        connectivityState="OFFLINE"
        isLiveWs={false}
      />
    );
    expect(screen.getByText("OFFLINE")).toBeInTheDocument();
  });

  // 7. Digital Twin correctly represents RUNNING/STOPPED/TRIPPED/STARTING
  it("correctly renders distinct visual treatments for RUNNING, STOPPED, and TRIPPED states", () => {
    const { rerender } = render(
      <DigitalTwinView
        machineId="MOT-1001"
        operatingState="RUNNING"
      />
    );
    expect(screen.getByText("ACTIVE")).toBeInTheDocument();

    rerender(
      <DigitalTwinView
        machineId="MOT-1001"
        operatingState="TRIPPED"
        edge={{ trip: "OVER_CURRENT_INTERLOCK" }}
      />
    );
    expect(screen.getByText("INTERLOCK TRIPPED")).toBeInTheDocument();
    expect(screen.getByText("OVER_CURRENT_INTERLOCK")).toBeInTheDocument();
    expect(screen.getByText("TRIP")).toBeInTheDocument();

    rerender(
      <DigitalTwinView
        machineId="MOT-1001"
        operatingState="STOPPED"
      />
    );
    expect(screen.getByText("STOP")).toBeInTheDocument();
  });

  // 8. SVG has accessible labeling
  it("provides meaningful accessible label and role on the SVG schematic container", () => {
    render(
      <DigitalTwinView
        machineId="MOT-1001"
        machineType="Industrial Induction Motor"
        operatingState="RUNNING"
        healthState="HEALTHY"
        healthScore={88.2}
      />
    );

    const imgContainer = screen.getByRole("img", {
      name: /Digital Twin visualization for machine MOT-1001, equipment type Industrial Induction Motor, currently RUNNING and HEALTHY with health score 88.2/i,
    });
    expect(imgContainer).toBeInTheDocument();
  });
});

describe("T-055 — Predictions & Explanations Panel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // 1. Prediction probability renders from backend
  it("renders failure probability formatted as percentage from backend", () => {
    render(
      <PredictionPanel
        failureProbability={0.184}
        riskBand="HIGH"
        modelVersion="v1.2-xgb"
      />
    );

    expect(screen.getByText("18.4%")).toBeInTheDocument();
  });

  // 2. Risk band renders correctly
  it("renders risk band badge with correct text", () => {
    render(
      <PredictionPanel
        failureProbability={0.184}
        riskBand="HIGH"
      />
    );

    expect(screen.getByText("HIGH RISK")).toBeInTheDocument();
  });

  // 3. Threshold 0.16 is displayed from expected source
  it("displays decision threshold t* = 0.16 clearly", () => {
    render(
      <PredictionPanel
        failureProbability={0.184}
        riskBand="HIGH"
      />
    );

    expect(screen.getByText("(t* = 0.16)")).toBeInTheDocument();
    expect(screen.getByText("t* = 0.16")).toBeInTheDocument();
  });

  // 4. Anomaly state renders when provided
  it("renders unsupervised anomaly detection score and detection status", () => {
    render(
      <PredictionPanel
        failureProbability={0.184}
        riskBand="HIGH"
        anomalyScore={0.652}
        anomalyFlag={true}
      />
    );

    expect(screen.getByText("0.652")).toBeInTheDocument();
    expect(screen.getByText("ANOMALY DETECTED")).toBeInTheDocument();
    expect(screen.getByText("Isolation Forest")).toBeInTheDocument();
  });

  // 5. Model version renders when provided
  it("renders model version tag from backend", () => {
    render(
      <PredictionPanel
        failureProbability={0.04}
        riskBand="LOW"
        modelVersion="v1.2-xgb"
      />
    );

    expect(screen.getByText(/Model: v1.2-xgb/i)).toBeInTheDocument();
  });

  // 6. Feature contributions render
  it("renders top feature contributions list", () => {
    render(<FeatureContributions factors={mockTopFactors} />);

    expect(screen.getByText("Vibration RMS")).toBeInTheDocument();
    expect(screen.getByText("Process Temperature")).toBeInTheDocument();
    expect(screen.getByText("Shaft Torque")).toBeInTheDocument();
    expect(screen.getByText("Rotational Speed")).toBeInTheDocument();
  });

  // 7. Positive and negative contributions are distinguishable
  it("distinguishes positive risk-increasing and negative risk-reducing contributions", () => {
    render(<FeatureContributions factors={mockTopFactors} />);

    expect(screen.getByText("+0.310")).toBeInTheDocument();
    expect(screen.getAllByText(/increases risk/i).length).toBe(3);

    expect(screen.getByText("-0.050")).toBeInTheDocument();
    expect(screen.getByText(/lowers risk/i)).toBeInTheDocument();
  });

  // 8. Feature values and contribution values are not confused
  it("clearly distinguishes feature raw value from model attribution magnitude", () => {
    render(<FeatureContributions factors={mockTopFactors} />);

    // Vibration feature value is 8.20 mm/s, while contribution is +0.310
    expect(screen.getByText("Value: 8.20 mm/s")).toBeInTheDocument();
    expect(screen.getByText("+0.310")).toBeInTheDocument();

    // Process temp feature value is 74.20 °C, while contribution is +0.220
    expect(screen.getByText("Value: 74.20 °C")).toBeInTheDocument();
    expect(screen.getByText("+0.220")).toBeInTheDocument();
  });

  // 9. SHAP disclaimer is visible
  it("displays the honest non-causal SHAP disclaimer", () => {
    render(<FeatureContributions factors={mockTopFactors} />);

    expect(
      screen.getByText(/Feature contributions indicate how each feature influenced the model output in log-odds margin space for this prediction. They are not causal explanations./i)
    ).toBeInTheDocument();
  });

  // 10. Recommendation renders from backend
  it("renders backend maintenance recommendation with action code, urgency, and reasoning", () => {
    render(<RecommendationPanel recommendation={mockRecommendation} />);

    expect(screen.getByText("INSPECT_BEARING")).toBeInTheDocument();
    expect(screen.getByText("HIGH PRIORITY")).toBeInTheDocument();
    expect(
      screen.getByText(/Schedule mechanical inspection for front drive-end bearing due to anomalous harmonic vibration./i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Drive End Bearing/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Vibration RMS exceeds ISO standard with high model risk attribution/i)
    ).toBeInTheDocument();
  });

  // 11. Missing explanation produces truthful empty state
  it("produces a truthful empty state when no feature contributions exist", () => {
    render(<FeatureContributions factors={[]} />);

    expect(
      screen.getByText("No explanation is currently available for this prediction.")
    ).toBeInTheDocument();
  });

  // 12. Explanation API failure does not break machine page
  it("does not break the machine page if prediction history API fails", async () => {
    vi.spyOn(api.machines, "getDetail").mockResolvedValue(mockMachineWithPrediction);
    vi.spyOn(api.machines, "getTelemetry").mockResolvedValue(mockTelemetryHistory);
    vi.spyOn(api.machines, "getPredictions").mockRejectedValue(new Error("503 Service Unavailable"));

    vi.spyOn(wsHook, "useTwinWebSocket").mockReturnValue({
      status: "CONNECTED",
      twins: {},
      twinList: [],
      isConnected: true,
    });

    renderMachineDetailPage();

    await waitFor(() => {
      // Machine page loaded successfully despite prediction history endpoint error
      expect(screen.getAllByText("MOT-1001").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("Industrial Induction Motor").length).toBeGreaterThanOrEqual(1);
    });
  });

  // 13. Live prediction update changes prediction UI when backend sends one
  it("updates failure probability and risk band when a live twin update is received", async () => {
    vi.spyOn(api.machines, "getDetail").mockResolvedValue(mockMachineWithPrediction);
    vi.spyOn(api.machines, "getTelemetry").mockResolvedValue(mockTelemetryHistory);

    const useTwinWsSpy = vi.spyOn(wsHook, "useTwinWebSocket");
    useTwinWsSpy.mockReturnValue({
      status: "CONNECTED",
      twins: {},
      twinList: [],
      isConnected: true,
    });

    const { rerender } = renderMachineDetailPage();

    await waitFor(() => {
      expect(screen.getAllByText("18.0%").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("HIGH RISK").length).toBeGreaterThanOrEqual(1);
    });

    // Simulate backend sending an elevated critical risk twin update via WebSocket
    const criticalTwin: TwinState = {
      ...mockMachineWithPrediction.latest_twin!,
      failure_probability: 0.842,
      risk_band: "CRITICAL",
      anomaly_score: 0.91,
      anomaly_flag: true,
    };

    useTwinWsSpy.mockReturnValue({
      status: "CONNECTED",
      twins: { "MOT-1001": criticalTwin },
      twinList: [criticalTwin],
      isConnected: true,
    });

    rerender(
      <AuthProvider>
        <MemoryRouter initialEntries={["/machines/MOT-1001"]}>
          <Routes>
            <Route path="/machines/:id" element={<MachineDetailPage />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getAllByText("84.2%").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("CRITICAL RISK").length).toBeGreaterThanOrEqual(1);
    });
  });

  // 14. No duplicate explanation requests occur for ordinary telemetry updates
  it("does not trigger additional prediction/explanation requests on ordinary telemetry updates", async () => {
    const getPredictionsSpy = vi.spyOn(api.machines, "getPredictions").mockResolvedValue([]);
    vi.spyOn(api.machines, "getDetail").mockResolvedValue(mockMachineWithPrediction);
    vi.spyOn(api.machines, "getTelemetry").mockResolvedValue(mockTelemetryHistory);

    const useTwinWsSpy = vi.spyOn(wsHook, "useTwinWebSocket");
    useTwinWsSpy.mockReturnValue({
      status: "CONNECTED",
      twins: {},
      twinList: [],
      isConnected: true,
    });

    const { rerender } = renderMachineDetailPage();

    await waitFor(() => {
      expect(screen.getAllByText("MOT-1001").length).toBeGreaterThanOrEqual(1);
    });

    const initialCallCount = getPredictionsSpy.mock.calls.length;

    // Simulate ordinary 1 Hz telemetry streaming without prediction change
    const nextTelemetryTwin: TwinState = {
      ...mockMachineWithPrediction.latest_twin!,
      last_seq: 1501,
      last_telemetry_ts: "2026-09-29T12:00:01Z",
      signals: {
        ...mockMachineWithPrediction.latest_twin!.signals,
        process_temp_c: 74.3,
        vibration_mm_s: 8.21,
      },
    };

    useTwinWsSpy.mockReturnValue({
      status: "CONNECTED",
      twins: { "MOT-1001": nextTelemetryTwin },
      twinList: [nextTelemetryTwin],
      isConnected: true,
    });

    rerender(
      <AuthProvider>
        <MemoryRouter initialEntries={["/machines/MOT-1001"]}>
          <Routes>
            <Route path="/machines/:id" element={<MachineDetailPage />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getAllByText("74.3").length).toBeGreaterThanOrEqual(1);
    });

    // Verify call count did not increase on ordinary telemetry packet
    expect(getPredictionsSpy.mock.calls.length).toBe(initialCallCount);
  });
});
