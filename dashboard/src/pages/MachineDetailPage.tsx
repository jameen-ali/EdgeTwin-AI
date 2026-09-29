import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Cpu,
  ArrowLeft,
  RefreshCw,
  BarChart3,
  Table as TableIcon,
  Wrench,
  MessageSquare,
  Plus,
  AlertTriangle,
} from "lucide-react";
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
import { Card } from "../components/common/Card";
import { Select } from "../components/common/Select";
import { RoleGate } from "../components/common/RoleGate";
import { MachineDetail, TelemetryPoint, TwinState } from "../types/machine";
import { PredictionRecord } from "../types/prediction";
import { AlertItem } from "../types/alert";
import { MaintenanceItem } from "../types/maintenance";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useTwinWebSocket } from "../hooks/useTwinWebSocket";
import { PRIVILEGED_ROLES } from "../utils/rbac";
import { CreateWorkOrderModal } from "../components/maintenance/CreateWorkOrderModal";
import { UpdateWorkOrderModal } from "../components/maintenance/UpdateWorkOrderModal";
import { AlertDetailModal } from "../components/alerts/AlertDetailModal";
import { OperatorFeedbackModal } from "../components/feedback/OperatorFeedbackModal";

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

  // Operational State (S22: Alerts, Maintenance, Feedback)
  const [machineAlerts, setMachineAlerts] = useState<AlertItem[]>([]);
  const [machineMaintenance, setMachineMaintenance] = useState<MaintenanceItem[]>([]);
  const [isCreateWorkOrderOpen, setIsCreateWorkOrderOpen] = useState(false);
  const [workOrderInitial, setWorkOrderInitial] = useState<{
    eventType?: string;
    description?: string;
    alertId?: number | null;
  }>({});
  const [selectedAlert, setSelectedAlert] = useState<AlertItem | null>(null);
  const [selectedMaint, setSelectedMaint] = useState<MaintenanceItem | null>(null);
  const [isFeedbackOpen, setIsFeedbackOpen] = useState(false);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 4000);
  };

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
        const [detailRes, telemRes, alertsRes, maintRes] = await Promise.all([
          api.machines.getDetail(id),
          api.machines.getTelemetry(id, { limit: pointLimit }),
          api.alerts.list({ machine_id: id, limit: 10 }).catch(() => [] as AlertItem[]),
          api.maintenance.getByMachine(id, { limit: 10 }).catch(() => [] as MaintenanceItem[]),
        ]);

        setMachine(detailRes);
        setMachineAlerts(alertsRes || []);
        setMachineMaintenance(maintRes || []);

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
              onScheduleMaintenance={
                recommendation
                  ? () => {
                      const isCritical = (recommendation.urgency || "").toUpperCase() === "CRITICAL";
                      setWorkOrderInitial({
                        eventType: isCritical ? "PART_REPLACEMENT" : "INSPECTION",
                        description: `Action [${recommendation.action_code}]: ${recommendation.recommendation_text} (Target: ${recommendation.target_component}. Reason: ${recommendation.reason})`,
                        alertId: machineAlerts.find((a) => a.status === "OPEN" || a.status === "ACTIVE")?.id || null,
                      });
                      setIsCreateWorkOrderOpen(true);
                    }
                  : undefined
              }
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

          {/* S22: Operational Workflow Section: Alerts, Maintenance & Feedback */}
          <div style={{ marginTop: "var(--space-4)", display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "var(--space-3)",
              }}
            >
              <div>
                <h3 style={{ fontSize: "16px", fontWeight: 700, margin: 0, color: "var(--color-text-primary)" }}>
                  Operational Workflow & Incident Triage
                </h3>
                <span style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>
                  Traceable actions from AI risk alerts to scheduled work orders and ground-truth verification.
                </span>
              </div>

              <div style={{ display: "flex", gap: "var(--space-2)" }}>
                <Button
                  variant="secondary"
                  size="sm"
                  leftIcon={<MessageSquare size={14} />}
                  onClick={() => setIsFeedbackOpen(true)}
                >
                  Record Ground Truth
                </Button>
                <RoleGate allowedRoles={PRIVILEGED_ROLES}>
                  <Button
                    variant="primary"
                    size="sm"
                    leftIcon={<Plus size={14} />}
                    onClick={() => {
                      setWorkOrderInitial({
                        eventType: "INSPECTION",
                        description: `Routine maintenance check for ${id}`,
                      });
                      setIsCreateWorkOrderOpen(true);
                    }}
                  >
                    Schedule Work Order
                  </Button>
                </RoleGate>
              </div>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(440px, 1fr))",
                gap: "var(--space-4)",
              }}
            >
              {/* Machine Alerts Card */}
              <Card
                title="Active & Recent Alerts"
                subtitle={`${machineAlerts.length} alert(s) registered for ${id}`}
              >
                {machineAlerts.length === 0 ? (
                  <EmptyState
                    title="No alerts logged"
                    description="This asset currently has no active or historical alarm conditions."
                    icon={<AlertTriangle size={20} />}
                  />
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
                    {machineAlerts.slice(0, 5).map((a) => {
                      const isAck = a.status === "ACKNOWLEDGED";
                      const isCrit = a.severity === "CRITICAL";

                      return (
                        <div
                          key={a.id}
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            padding: "var(--space-3)",
                            backgroundColor: "var(--color-surface-raised)",
                            border: `1px solid ${isCrit ? "var(--color-danger-border)" : "var(--color-border-subtle)"}`,
                            borderRadius: "var(--radius-md)",
                            gap: "var(--space-3)",
                          }}
                        >
                          <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                              <span
                                style={{
                                  fontSize: "10px",
                                  fontWeight: 700,
                                  padding: "1px 5px",
                                  borderRadius: "var(--radius-sm)",
                                  backgroundColor: isCrit ? "var(--color-danger-subtle)" : "var(--color-warning-subtle)",
                                  color: isCrit ? "var(--color-danger)" : "var(--color-warning)",
                                }}
                              >
                                {a.severity}
                              </span>
                              <span className="text-mono" style={{ fontSize: "11px", fontWeight: 700 }}>
                                ALT-{a.id}
                              </span>
                              <span style={{ fontSize: "11px", color: a.status === "RESOLVED" ? "var(--color-success)" : isAck ? "var(--color-info)" : "var(--color-warning)", fontWeight: 600 }}>
                                [{a.status}]
                              </span>
                            </div>
                            <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
                              {a.message}
                            </span>
                          </div>

                          <div style={{ display: "flex", gap: "6px" }}>
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => setSelectedAlert(a)}
                            >
                              Triage
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </Card>

              {/* Machine Maintenance Card */}
              <Card
                title="Maintenance History"
                subtitle={`${machineMaintenance.length} work order(s) logged for ${id}`}
              >
                {machineMaintenance.length === 0 ? (
                  <EmptyState
                    title="No maintenance scheduled"
                    description="No preventive or corrective work orders have been logged for this machine."
                    icon={<Wrench size={20} />}
                  />
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
                    {machineMaintenance.slice(0, 5).map((m) => (
                      <div
                        key={m.id}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          padding: "var(--space-3)",
                          backgroundColor: "var(--color-surface-raised)",
                          border: "1px solid var(--color-border-subtle)",
                          borderRadius: "var(--radius-md)",
                          gap: "var(--space-3)",
                        }}
                      >
                        <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            <span className="text-mono" style={{ fontSize: "11px", fontWeight: 700 }}>
                              MNT-{m.id}
                            </span>
                            <span
                              style={{
                                fontSize: "10px",
                                fontWeight: 700,
                                padding: "1px 5px",
                                borderRadius: "var(--radius-sm)",
                                backgroundColor: "var(--color-surface)",
                                color: m.status === "COMPLETED" ? "var(--color-success)" : "var(--color-warning)",
                              }}
                            >
                              {m.status}
                            </span>
                            <span className="text-mono" style={{ fontSize: "10px", color: "var(--color-text-muted)" }}>
                              {m.event_type}
                            </span>
                          </div>
                          <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
                            {m.description}
                          </span>
                        </div>

                        <RoleGate allowedRoles={PRIVILEGED_ROLES}>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => setSelectedMaint(m)}
                          >
                            Update
                          </Button>
                        </RoleGate>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          </div>

          {/* Toast Notification */}
          {toastMsg && (
            <div
              role="status"
              style={{
                position: "fixed",
                bottom: "var(--space-6)",
                right: "var(--space-6)",
                backgroundColor: "var(--color-surface)",
                border: "1px solid var(--color-accent)",
                color: "var(--color-text-primary)",
                padding: "var(--space-3) var(--space-4)",
                borderRadius: "var(--radius-md)",
                boxShadow: "0 8px 24px rgba(0, 0, 0, 0.5)",
                zIndex: 100,
                fontSize: "13px",
                fontWeight: 500,
              }}
            >
              {toastMsg}
            </div>
          )}

          {/* Modals */}
          {selectedAlert && (
            <AlertDetailModal
              isOpen={Boolean(selectedAlert)}
              onClose={() => setSelectedAlert(null)}
              alert={selectedAlert}
              onAcknowledge={async (alertId, notes) => {
                const updated = await api.alerts.acknowledge(alertId, { notes });
                setMachineAlerts((prev) => prev.map((a) => (a.id === alertId ? updated : a)));
                showToast(`Alert ALT-${alertId} acknowledged.`);
              }}
              onResolve={async (alertId, notes) => {
                const updated = await api.alerts.resolve(alertId, { notes });
                setMachineAlerts((prev) => prev.map((a) => (a.id === alertId ? updated : a)));
                showToast(`Alert ALT-${alertId} resolved.`);
              }}
              onCreateWorkOrder={(alert) => {
                setWorkOrderInitial({
                  eventType: alert.severity === "CRITICAL" ? "PART_REPLACEMENT" : "INSPECTION",
                  description: `Maintenance triggered by alert ALT-${alert.id}: ${alert.message}`,
                  alertId: alert.id,
                });
                setIsCreateWorkOrderOpen(true);
              }}
              onSubmitFeedback={() => {
                setIsFeedbackOpen(true);
              }}
            />
          )}

          <CreateWorkOrderModal
            isOpen={isCreateWorkOrderOpen}
            onClose={() => setIsCreateWorkOrderOpen(false)}
            initialMachineId={id}
            initialAlertId={workOrderInitial.alertId}
            initialEventType={workOrderInitial.eventType}
            initialDescription={workOrderInitial.description}
            onSuccess={(created) => {
              showToast(`Work order MNT-${created.id} scheduled for ${created.machine_id}.`);
              loadMachineData(true);
            }}
          />

          {selectedMaint && (
            <UpdateWorkOrderModal
              isOpen={Boolean(selectedMaint)}
              onClose={() => setSelectedMaint(null)}
              item={selectedMaint}
              onSuccess={(updated) => {
                showToast(`Work order MNT-${updated.id} updated (${updated.status}).`);
                loadMachineData(true);
              }}
            />
          )}

          {id && (
            <OperatorFeedbackModal
              isOpen={isFeedbackOpen}
              onClose={() => setIsFeedbackOpen(false)}
              machineId={id}
              alertId={machineAlerts.find((a) => a.status === "OPEN" || a.status === "ACTIVE")?.id || null}
              predictionId={machine?.latest_prediction?.id || predictionRecord?.id || null}
              predictedRiskBand={riskBand}
              failureProbability={failureProbability}
              onSuccess={(fb) => {
                showToast(`Ground-truth feedback recorded for ${fb.machine_id}.`);
              }}
            />
          )}
        </>
      )}
    </div>
  );
};
