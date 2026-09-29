import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Cpu, ArrowLeft, RefreshCw, BarChart3, Table as TableIcon } from "lucide-react";
import { MachineHeader } from "../components/machine/MachineHeader";
import { DigitalTwinView } from "../components/machine/DigitalTwinView";
import { PredictionPanel } from "../components/machine/PredictionPanel";
import { MachineStatusSummary } from "../components/machine/MachineStatusSummary";
import { TelemetryMetricGrid, TelemetrySignals } from "../components/machine/TelemetryMetricGrid";
import { TelemetryChart, ChartSeries } from "../components/machine/TelemetryChart";
import { RawTelemetryTable } from "../components/machine/RawTelemetryTable";
import { LoadingState } from "../components/common/LoadingState";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { Button } from "../components/common/Button";
import { Select } from "../components/common/Select";
import { MachineDetail, TelemetryPoint, TwinState } from "../types/machine";
import { PredictionRecord } from "../types/prediction";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useTwinWebSocket } from "../hooks/useTwinWebSocket";

const MAX_CHART_POINTS = 100;

export const MachineDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { token } = useAuth();

  const [machine, setMachine] = useState<MachineDetail | null>(null);
  const [telemetryHistory, setTelemetryHistory] = useState<TelemetryPoint[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isNotFound, setIsNotFound] = useState<boolean>(false);
  const [pointLimit, setPointLimit] = useState<number>(50);
  const [activeTab, setActiveTab] = useState<"charts" | "table">("charts");
  const [predictionRecord, setPredictionRecord] = useState<PredictionRecord | null>(null);

  // Subscribe to machine-specific WebSocket stream
  const { twins, isConnected: isWsConnected } = useTwinWebSocket({
    machineId: id,
    token,
    enabled: Boolean(id),
  });

  const liveTwin: TwinState | undefined = id ? twins[id] : undefined;

  // Load Machine Metadata and Historical Telemetry
  const loadMachineData = useCallback(
    async (isManualRefresh = false) => {
      if (!id) return;

      if (isManualRefresh) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setError(null);
      setIsNotFound(false);

      try {
        const [detailRes, telemRes] = await Promise.all([
          api.machines.getDetail(id),
          api.machines.getTelemetry(id, { limit: pointLimit }),
        ]);

        setMachine(detailRes);

        // Backend orders telemetry `ts desc`, reverse for chronological time-series
        const chronPoints = [...(telemRes || [])].reverse();
        setTelemetryHistory(chronPoints);

        // Optional non-destructive prediction fetch if latest_prediction or top_factors missing
        if (!detailRes.latest_prediction?.top_factors) {
          try {
            const preds = await api.machines.getPredictions(id, { limit: 1 });
            if (preds && preds.length > 0) {
              setPredictionRecord(preds[0]);
            }
          } catch {
            // Non-destructive fallback: explanation/prediction API failure does not break the machine page
          }
        }
      } catch (err: unknown) {
        if (err instanceof ApiError && err.status === 404) {
          setIsNotFound(true);
          setError(`Machine '${id}' not found in the EdgeTwin fleet registry.`);
        } else if (
          err &&
          typeof err === "object" &&
          "status" in err &&
          (err as { status?: number }).status === 404
        ) {
          setIsNotFound(true);
          setError(`Machine '${id}' not found in the EdgeTwin fleet registry.`);
        } else {
          const msg = err instanceof Error ? err.message : "Failed to load machine data";
          setError(msg);
        }
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [id, pointLimit]
  );

  useEffect(() => {
    loadMachineData();
  }, [loadMachineData]);

  // Handle incoming live twin telemetry from WebSocket
  useEffect(() => {
    if (!liveTwin) return;

    // If live twin has signals, create a new TelemetryPoint and append to history buffer
    if (liveTwin.signals && Object.keys(liveTwin.signals).length > 0) {
      const sigs = liveTwin.signals;
      const ts = liveTwin.last_telemetry_ts || liveTwin.updated_at || new Date().toISOString();
      const seq = liveTwin.last_seq;

      const newPoint: TelemetryPoint = {
        machine_id: liveTwin.machine_id,
        seq: seq ?? undefined,
        ts,
        air_temp_c: sigs.air_temp_c ?? null,
        process_temp_c: sigs.process_temp_c ?? null,
        rotational_speed_rpm: sigs.rotational_speed_rpm ?? null,
        torque_nm: sigs.torque_nm ?? null,
        vibration_mm_s: sigs.vibration_mm_s ?? null,
        pressure_bar: sigs.pressure_bar ?? null,
        current_a: sigs.current_a ?? null,
        voltage_v: sigs.voltage_v ?? null,
        tool_wear_min: sigs.tool_wear_min ?? null,
        operating_hours: sigs.operating_hours ?? null,
        trip: sigs.trip ?? liveTwin.edge?.trip ?? null,
      };

      setTelemetryHistory((prev) => {
        // Prevent duplicate appending if same timestamp or sequence
        if (prev.length > 0) {
          const last = prev[prev.length - 1];
          if ((seq !== undefined && last.seq === seq) || last.ts === ts) {
            // Update the last point in place
            const updated = [...prev];
            updated[updated.length - 1] = newPoint;
            return updated;
          }
        }
        // Append and enforce bounded buffer size
        const next = [...prev, newPoint];
        if (next.length > MAX_CHART_POINTS) {
          return next.slice(next.length - MAX_CHART_POINTS);
        }
        return next;
      });
    }
  }, [liveTwin]);

  // Merge authoritative twin state: prioritize live WebSocket twin over initial REST twin
  const currentTwin = liveTwin || machine?.latest_twin;

  // Extract current sensor signals: prioritize live twin, fallback to latest_telemetry
  const currentSignals: TelemetrySignals | null = useMemo(() => {
    if (liveTwin?.signals && Object.keys(liveTwin.signals).length > 0) {
      return liveTwin.signals;
    }
    if (machine?.latest_twin?.signals && Object.keys(machine.latest_twin.signals).length > 0) {
      return machine.latest_twin.signals;
    }
    if (machine?.latest_telemetry?.signals) {
      return machine.latest_telemetry.signals;
    }
    if (telemetryHistory.length > 0) {
      const last = telemetryHistory[telemetryHistory.length - 1];
      return {
        air_temp_c: last.air_temp_c,
        process_temp_c: last.process_temp_c,
        vibration_mm_s: last.vibration_mm_s,
        rotational_speed_rpm: last.rotational_speed_rpm,
        torque_nm: last.torque_nm,
        current_a: last.current_a,
        pressure_bar: last.pressure_bar,
        voltage_v: last.voltage_v,
        tool_wear_min: last.tool_wear_min,
        operating_hours: last.operating_hours,
        delta_t_c: last.delta_t_c,
        power_va: last.power_va,
      };
    }
    return null;
  }, [liveTwin, machine, telemetryHistory]);

  // Current values
  const healthScore =
    currentTwin?.health_score !== undefined
      ? currentTwin.health_score
      : machine?.latest_prediction?.health_score ?? predictionRecord?.health_score ?? null;

  const failureProbability =
    currentTwin?.failure_probability !== undefined
      ? currentTwin.failure_probability
      : machine?.latest_prediction?.failure_probability ?? predictionRecord?.failure_probability ?? null;

  const riskBand =
    currentTwin?.risk_band || machine?.latest_prediction?.risk_band || predictionRecord?.risk_band || null;

  const operatingState =
    currentTwin?.operating_state || "UNKNOWN";

  const healthState =
    currentTwin?.health_state || "UNKNOWN";

  const connectivityState =
    currentTwin?.sync_status || (isWsConnected ? "LIVE" : "OFFLINE");

  const lastTelemetryTs =
    currentTwin?.last_telemetry_ts ||
    machine?.latest_telemetry?.ts ||
    (telemetryHistory.length > 0 ? telemetryHistory[telemetryHistory.length - 1].ts : null);

  const lastSeq =
    currentTwin?.last_seq ?? machine?.latest_telemetry?.seq ?? null;

  const topFactors =
    liveTwin?.top_factors ||
    machine?.latest_twin?.top_factors ||
    machine?.latest_prediction?.top_factors ||
    predictionRecord?.top_factors ||
    null;

  const recommendation =
    liveTwin?.recommendation ||
    machine?.latest_twin?.recommendation ||
    null;

  const anomalyScore =
    currentTwin?.anomaly_score !== undefined
      ? currentTwin.anomaly_score
      : machine?.latest_prediction?.anomaly_score ?? predictionRecord?.anomaly_score ?? null;

  const anomalyFlag =
    currentTwin?.anomaly_flag !== undefined
      ? currentTwin.anomaly_flag
      : machine?.latest_prediction?.anomaly_flag ?? predictionRecord?.anomaly_flag ?? null;

  const modelVersion =
    currentTwin?.model_version ||
    machine?.latest_prediction?.model_version ||
    predictionRecord?.model_version ||
    "v1.2-xgb";

  const predictionTs =
    machine?.latest_prediction?.ts ||
    predictionRecord?.ts ||
    currentTwin?.updated_at ||
    lastTelemetryTs;

  // Chart Series Configurations
  const tempSeries: ChartSeries[] = [
    {
      key: "process_temp_c",
      name: "Process Temp",
      color: "var(--color-accent)", // #149AFB Electric Cyan
      unit: "°C",
      threshold: { value: 75, label: "Alarm", color: "var(--color-danger)" },
    },
    {
      key: "air_temp_c",
      name: "Ambient Air",
      color: "var(--color-text-muted)", // Grey
      unit: "°C",
    },
  ];

  const vibrationSeries: ChartSeries[] = [
    {
      key: "vibration_mm_s",
      name: "Vibration RMS",
      color: "var(--color-warning)", // #FE750E Orange
      unit: "mm/s",
      threshold: { value: 4.5, label: "ISO 10816 Limit", color: "var(--color-danger)" },
    },
  ];

  const speedTorqueSeries: ChartSeries[] = [
    {
      key: "rotational_speed_rpm",
      name: "Rotational Speed",
      color: "var(--color-success)", // #13EF95 Green
      unit: "RPM",
    },
    {
      key: "torque_nm",
      name: "Shaft Torque",
      color: "var(--color-maintenance)", // #8C9AC4 Indigo
      unit: "Nm",
      threshold: { value: 75, label: "Peak Torque", color: "var(--color-warning)" },
    },
  ];

  const currentSeries: ChartSeries[] = [
    {
      key: "current_a",
      name: "Phase Current",
      color: "var(--color-accent)",
      unit: "A",
      threshold: { value: 30, label: "FLC Overcurrent", color: "var(--color-danger)" },
    },
  ];

  // 404 Not Found State
  if (!isLoading && isNotFound) {
    return (
      <div
        style={{
          maxWidth: "640px",
          margin: "var(--space-12) auto",
          padding: "0 var(--space-4)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "var(--space-4)",
        }}
      >
        <ErrorState
          title="Machine not found"
          message={`The requested machine "${id}" is not registered in the EdgeTwin fleet.`}
        />
        <Button
          variant="secondary"
          leftIcon={<ArrowLeft size={14} />}
          onClick={() => navigate("/machines")}
        >
          Return to Fleet
        </Button>
      </div>
    );
  }

  // Generic Error State
  if (!isLoading && error && !machine) {
    return (
      <div style={{ maxWidth: "640px", margin: "var(--space-12) auto", padding: "0 var(--space-4)" }}>
        <ErrorState
          title="Failed to load machine detail"
          message={error}
          onRetry={() => loadMachineData(false)}
        />
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      {/* Header */}
      {isLoading && !machine ? (
        <LoadingState message="Connecting to machine telemetry stream..." />
      ) : (
        <>
          <MachineHeader
            machineId={machine?.machine_id || id || "UNKNOWN"}
            machineType={machine?.machine_type}
            location={machine?.location}
            operatingState={operatingState}
            healthState={healthState}
            connectivityState={connectivityState}
            lastUpdatedAt={machine?.updated_at || lastTelemetryTs}
            isLiveWs={isWsConnected}
            onRefresh={() => loadMachineData(true)}
            isRefreshing={isRefreshing}
          />

          {/* S21: Digital Twin Visualization & AI Predictions / Explanations */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(440px, 1fr))",
              gap: "var(--space-6)",
            }}
          >
            {/* T-054: Digital Twin Schematic */}
            <DigitalTwinView
              machineId={machine?.machine_id || id || "UNKNOWN"}
              machineType={machine?.machine_type}
              operatingState={operatingState}
              healthState={healthState}
              connectivityState={connectivityState}
              healthScore={healthScore}
              signals={currentSignals}
              quality={currentTwin?.quality}
              edge={currentTwin?.edge}
              isLiveWs={isWsConnected}
            />

            {/* T-055: AI Predictive Assessment & Explanations Panel */}
            <PredictionPanel
              failureProbability={failureProbability}
              riskBand={riskBand}
              anomalyScore={anomalyScore}
              anomalyFlag={anomalyFlag}
              modelVersion={modelVersion}
              predictionTs={predictionTs}
              topFactors={topFactors}
              recommendation={recommendation}
              isLoading={isLoading}
            />
          </div>

          {/* Current Twin State Summary */}
          <MachineStatusSummary
            healthScore={healthScore}
            failureProbability={failureProbability}
            riskBand={riskBand}
            operatingState={operatingState}
            healthState={healthState}
            connectivityState={connectivityState}
            lastTelemetryTs={lastTelemetryTs}
            lastSeq={lastSeq}
            modelVersion={currentTwin?.model_version}
            anomalyScore={currentTwin?.anomaly_score}
            anomalyFlag={currentTwin?.anomaly_flag}
          />

          {/* Current Sensor Telemetry Grid */}
          <TelemetryMetricGrid signals={currentSignals} />

          {/* Historical & Live Telemetry Section */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: "var(--space-4)",
              marginTop: "var(--space-2)",
            }}
          >
            {/* View Switcher: Charts vs Raw Table */}
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <Button
                variant={activeTab === "charts" ? "primary" : "secondary"}
                size="sm"
                leftIcon={<BarChart3 size={14} />}
                onClick={() => setActiveTab("charts")}
                aria-pressed={activeTab === "charts"}
              >
                Telemetry Charts
              </Button>
              <Button
                variant={activeTab === "table" ? "primary" : "secondary"}
                size="sm"
                leftIcon={<TableIcon size={14} />}
                onClick={() => setActiveTab("table")}
                aria-pressed={activeTab === "table"}
              >
                Observations Log
              </Button>
            </div>

            {/* Range / Sample Count Controls */}
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
              <span style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>
                Window Samples:
              </span>
              <div style={{ width: "130px" }}>
                <Select
                  value={String(pointLimit)}
                  onChange={(e) => setPointLimit(Number(e.target.value))}
                  options={[
                    { value: "25", label: "25 points" },
                    { value: "50", label: "50 points" },
                    { value: "100", label: "100 points" },
                  ]}
                  style={{ height: "30px", fontSize: "12px" }}
                />
              </div>
            </div>
          </div>

          {/* Telemetry Display */}
          {telemetryHistory.length === 0 ? (
            <EmptyState
              title="No historical telemetry available"
              description="Telemetry history will appear when this machine begins reporting sensor observations from the edge."
              icon={<Cpu size={24} />}
              action={
                <Button
                  variant="secondary"
                  size="sm"
                  leftIcon={<RefreshCw size={14} />}
                  onClick={() => loadMachineData(true)}
                >
                  Check Again
                </Button>
              }
            />
          ) : activeTab === "charts" ? (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(440px, 1fr))",
                gap: "var(--space-4)",
              }}
            >
              {/* Chart 1: Temperature */}
              <TelemetryChart
                title="Temperature Tracking"
                subtitle="Dual-channel contact process and ambient air temperature"
                unit="°C"
                series={tempSeries}
                data={telemetryHistory}
                timeWindowLabel={`Last ${telemetryHistory.length} samples`}
              />

              {/* Chart 2: Vibration */}
              <TelemetryChart
                title="Vibration Velocity"
                subtitle="High-frequency windowed RMS velocity monitoring"
                unit="mm/s"
                series={vibrationSeries}
                data={telemetryHistory}
                timeWindowLabel={`Last ${telemetryHistory.length} samples`}
              />

              {/* Chart 3: Speed & Torque */}
              <TelemetryChart
                title="Kinematic Drive Dynamics"
                subtitle="Shaft rotational speed (RPM) and dynamic mechanical torque"
                unit="RPM / Nm"
                series={speedTorqueSeries}
                data={telemetryHistory}
                timeWindowLabel={`Last ${telemetryHistory.length} samples`}
              />

              {/* Chart 4: Electrical Current */}
              <TelemetryChart
                title="Phase Current Draw"
                subtitle="Motor winding current consumption vs full load current limit"
                unit="A"
                series={currentSeries}
                data={telemetryHistory}
                timeWindowLabel={`Last ${telemetryHistory.length} samples`}
              />
            </div>
          ) : (
            /* Raw Telemetry Observations Table */
            <RawTelemetryTable telemetry={telemetryHistory} />
          )}
        </>
      )}
    </div>
  );
};
