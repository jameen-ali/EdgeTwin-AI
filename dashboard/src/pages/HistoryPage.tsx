import React, { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { HistoryWindow, MachineHistoryResponse, FleetHistoryResponse } from "../types/history";
import { MachineSummary } from "../types/machine";
import { HistoricalHealthChart } from "../components/history/HistoricalHealthChart";
import { HistoricalSensorChart } from "../components/history/HistoricalSensorChart";
import { HistoricalPredictionTimeline } from "../components/history/HistoricalPredictionTimeline";
import { HistoricalEventTimeline } from "../components/history/HistoricalEventTimeline";
import { FleetAnalyticsSection } from "../components/history/FleetAnalyticsSection";
import { Card } from "../components/common/Card";
import { Button } from "../components/common/Button";
import { LoadingState } from "../components/common/LoadingState";
import { ErrorState } from "../components/common/ErrorState";
import { formatNumber } from "../utils/formatters";
import {
  RotateCw,
  Clock,
  Activity,
  AlertTriangle,
  Wrench,
  ShieldAlert,
} from "lucide-react";

const FLEET_KEY = "__FLEET__";

const WINDOW_LABELS: Record<HistoryWindow, string> = {
  "1h": "Last 1 Hour",
  "6h": "Last 6 Hours",
  "24h": "Last 24 Hours",
  "7d": "Last 7 Days",
  "30d": "Last 30 Days",
};

export const HistoryPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialMachine = searchParams.get("machine_id") || "";
  const initialWindow = (searchParams.get("window") as HistoryWindow) || "24h";

  const [selectedTarget, setSelectedTarget] = useState<string>(initialMachine || FLEET_KEY);
  const [selectedWindow, setSelectedWindow] = useState<HistoryWindow>(initialWindow);

  const [machines, setMachines] = useState<MachineSummary[]>([]);
  const [isMachinesLoading, setIsMachinesLoading] = useState<boolean>(true);

  const [machineData, setMachineData] = useState<MachineHistoryResponse | null>(null);
  const [fleetData, setFleetData] = useState<FleetHistoryResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load registered machines on mount
  useEffect(() => {
    let isMounted = true;
    const fetchMachines = async () => {
      try {
        setIsMachinesLoading(true);
        const res = await api.machines.list({ limit: 100 });
        if (isMounted) {
          setMachines(res);
          // If no machine selected and initial was provided, keep it; else if none, default to fleet or first machine
          if (!initialMachine && res.length > 0 && selectedTarget === "") {
            setSelectedTarget(FLEET_KEY);
          }
        }
      } catch (err) {
        console.error("Failed to load machine fleet inventory:", err);
      } finally {
        if (isMounted) setIsMachinesLoading(false);
      }
    };
    fetchMachines();
    return () => {
      isMounted = false;
    };
  }, [initialMachine]);

  // Load historical analytics data based on selection
  const loadData = useCallback(async () => {
    setError(null);
    setIsLoading(true);
    try {
      if (selectedTarget === FLEET_KEY || !selectedTarget) {
        const res = await api.history.getFleetHistory({ window: selectedWindow });
        setFleetData(res);
        setMachineData(null);
      } else {
        const res = await api.history.getMachineHistory(selectedTarget, { window: selectedWindow });
        setMachineData(res);
        setFleetData(null);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.problem?.detail || err.message || "Failed to load historical analytics.");
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Network error connecting to historical analytics service.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [selectedTarget, selectedWindow]);

  useEffect(() => {
    loadData();
    // Update search params
    const nextParams = new URLSearchParams();
    if (selectedTarget && selectedTarget !== FLEET_KEY) {
      nextParams.set("machine_id", selectedTarget);
    }
    nextParams.set("window", selectedWindow);
    setSearchParams(nextParams, { replace: true });
  }, [loadData, selectedTarget, selectedWindow, setSearchParams]);

  const formatSeconds = (sec: number) => {
    if (sec <= 0) return "0s";
    if (sec < 60) return `${sec}s`;
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    if (m < 60) return s > 0 ? `${m}m ${s}s` : `${m}m`;
    const h = Math.floor(m / 60);
    const remM = m % 60;
    return remM > 0 ? `${h}h ${remM}m` : `${h}h`;
  };

  return (
    <div style={{ padding: "var(--space-6)", display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      {/* Top Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: "var(--space-4)",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
            <h1
              style={{
                fontSize: "22px",
                fontWeight: 700,
                color: "var(--color-text-primary)",
                margin: 0,
                letterSpacing: "var(--tracking-tight)",
              }}
            >
              Historical Analytics
            </h1>
            <span
              style={{
                fontSize: "11px",
                fontWeight: 600,
                fontFamily: "var(--font-mono)",
                padding: "2px 8px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "rgba(20, 154, 251, 0.12)",
                color: "var(--color-accent)",
                border: "1px solid var(--color-accent-border)",
              }}
            >
              T-057 RETROSPECTIVE
            </span>
          </div>
          <p
            style={{
              fontSize: "13px",
              color: "var(--color-text-muted)",
              margin: "4px 0 0 0",
              maxWidth: "600px",
            }}
          >
            Deep-dive operational timeline, downsampled telemetry, composite health trends, and incident retrospective
          </p>
        </div>

        {/* Global Controls: Machine & Window Selector */}
        <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: "var(--space-3)" }}>
          {/* Target Selector */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <label htmlFor="history-target-select" style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>
              Scope:
            </label>
            <select
              id="history-target-select"
              value={selectedTarget}
              onChange={(e) => setSelectedTarget(e.target.value)}
              disabled={isMachinesLoading}
              style={{
                backgroundColor: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                color: "var(--color-text-primary)",
                fontSize: "12px",
                padding: "6px 12px",
                cursor: "pointer",
                outline: "none",
              }}
            >
              <option value={FLEET_KEY}>⚡ Fleet-wide Overview</option>
              {machines.map((m) => (
                <option key={m.machine_id} value={m.machine_id}>
                  {m.machine_id} — {m.machine_type} ({m.status || "ACTIVE"})
                </option>
              ))}
            </select>
          </div>

          {/* Time Window Selector */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <label htmlFor="history-window-select" style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>
              Horizon:
            </label>
            <select
              id="history-window-select"
              value={selectedWindow}
              onChange={(e) => setSelectedWindow(e.target.value as HistoryWindow)}
              style={{
                backgroundColor: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                color: "var(--color-text-primary)",
                fontSize: "12px",
                padding: "6px 12px",
                cursor: "pointer",
                outline: "none",
              }}
            >
              {(["1h", "6h", "24h", "7d", "30d"] as const).map((w) => (
                <option key={w} value={w}>
                  {WINDOW_LABELS[w]}
                </option>
              ))}
            </select>
          </div>

          {/* Refresh Action */}
          <Button
            variant="secondary"
            size="sm"
            onClick={loadData}
            isLoading={isLoading}
            leftIcon={<RotateCw size={14} />}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <ErrorState
          title="Failed to Load Historical Data"
          message={error}
          onRetry={loadData}
        />
      )}

      {/* Loading State */}
      {isLoading && !error && (
        <div style={{ padding: "var(--space-12) 0" }}>
          <LoadingState message={`Retrieving historical telemetry and events for ${selectedWindow}...`} />
        </div>
      )}

      {/* Machine Historical View */}
      {!isLoading && !error && machineData && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
          {/* Machine Summary KPI Row */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: "var(--space-4)",
            }}
          >
            <Card>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "rgba(19, 239, 149, 0.12)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--color-success)",
                  }}
                >
                  <Activity size={18} />
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--color-text-muted)", textTransform: "uppercase" }}>
                    Avg Health Score
                  </div>
                  <div style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-text-primary)", fontFamily: "var(--font-mono)" }}>
                    {machineData.summary.avg_health_score !== null
                      ? `${formatNumber(machineData.summary.avg_health_score, 1)}%`
                      : "—"}
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
                    Min: {machineData.summary.min_health_score !== null ? `${formatNumber(machineData.summary.min_health_score, 1)}%` : "—"}
                  </div>
                </div>
              </div>
            </Card>

            <Card>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "rgba(254, 117, 14, 0.12)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--color-warning)",
                  }}
                >
                  <Clock size={18} />
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--color-text-muted)", textTransform: "uppercase" }}>
                    Time in Warning / Crit
                  </div>
                  <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--color-text-primary)", fontFamily: "var(--font-mono)" }}>
                    {formatSeconds(machineData.summary.time_in_warning_s)} / {formatSeconds(machineData.summary.time_in_critical_s)}
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
                    Sampled duration
                  </div>
                </div>
              </div>
            </Card>

            <Card>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "rgba(239, 68, 68, 0.12)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--color-danger)",
                  }}
                >
                  <AlertTriangle size={18} />
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--color-text-muted)", textTransform: "uppercase" }}>
                    Total Alarms Raised
                  </div>
                  <div style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-text-primary)", fontFamily: "var(--font-mono)" }}>
                    {machineData.summary.alert_count} Alerts
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--color-success)" }}>
                    {machineData.summary.resolved_alert_count} resolved
                  </div>
                </div>
              </div>
            </Card>

            <Card>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "rgba(140, 154, 196, 0.12)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--color-accent)",
                  }}
                >
                  <Wrench size={18} />
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--color-text-muted)", textTransform: "uppercase" }}>
                    Maintenance Logged
                  </div>
                  <div style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-text-primary)", fontFamily: "var(--font-mono)" }}>
                    {machineData.summary.maintenance_count} Work Orders
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
                    In selected window
                  </div>
                </div>
              </div>
            </Card>

            <Card>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "rgba(20, 154, 251, 0.12)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--color-accent)",
                  }}
                >
                  <ShieldAlert size={18} />
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--color-text-muted)", textTransform: "uppercase" }}>
                    Avg Failure Risk p(fail)
                  </div>
                  <div style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-text-primary)", fontFamily: "var(--font-mono)" }}>
                    {machineData.summary.avg_failure_probability !== null
                      ? `${(machineData.summary.avg_failure_probability * 100).toFixed(1)}%`
                      : "—"}
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
                    Threshold: 16.0%
                  </div>
                </div>
              </div>
            </Card>
          </div>

          {/* Main Charts: Health and Sensor Trends */}
          <HistoricalHealthChart
            data={machineData.health_trend}
            isDownsampled={machineData.is_downsampled}
            downsampleIntervalS={machineData.downsample_interval_s}
          />

          <HistoricalSensorChart
            data={machineData.sensor_trend}
            isDownsampled={machineData.is_downsampled}
            downsampleIntervalS={machineData.downsample_interval_s}
          />

          {/* Predictions Retrospective */}
          <HistoricalPredictionTimeline predictions={machineData.prediction_history} />

          {/* Incident and Maintenance Event Timelines */}
          <HistoricalEventTimeline alerts={machineData.alerts} maintenance={machineData.maintenance} />
        </div>
      )}

      {/* Fleet Historical View */}
      {!isLoading && !error && fleetData && (
        <FleetAnalyticsSection
          data={fleetData}
          onSelectMachine={(mId) => setSelectedTarget(mId)}
        />
      )}
    </div>
  );
};
