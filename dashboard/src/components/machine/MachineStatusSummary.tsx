import React from "react";
import { Activity, ShieldAlert, Cpu, Radio, Hash } from "lucide-react";
import { Card } from "../common/Card";
import { HealthBadge } from "../common/HealthBadge";
import { StatusBadge } from "../common/StatusBadge";
import { formatNumber, formatPercent, formatDateTime } from "../../utils/formatters";
import { OperatingState, HealthState, ConnectivityState } from "../../types/machine";

export interface MachineStatusSummaryProps {
  healthScore: number | null;
  failureProbability: number | null;
  riskBand: string | null;
  operatingState: OperatingState | string;
  healthState: HealthState | string;
  connectivityState: ConnectivityState | string;
  lastTelemetryTs?: string | null;
  lastSeq?: number | null;
  modelVersion?: string;
  anomalyScore?: number | null;
  anomalyFlag?: boolean | null;
}

export const MachineStatusSummary: React.FC<MachineStatusSummaryProps> = ({
  healthScore,
  failureProbability,
  riskBand,
  operatingState,
  healthState,
  connectivityState,
  lastTelemetryTs,
  lastSeq,
  modelVersion,
  anomalyScore,
  anomalyFlag,
}) => {
  const isHighRisk = failureProbability !== null && failureProbability > 0.16;

  // Health Score bar color
  let healthBarColor = "var(--color-success)";
  if (healthScore !== null) {
    if (healthScore < 60) healthBarColor = "var(--color-danger)";
    else if (healthScore < 80) healthBarColor = "var(--color-warning)";
  }

  // Risk band styling
  const normRisk = (riskBand || "LOW").toUpperCase();
  let riskColor = "var(--color-success)";
  if (normRisk === "CRITICAL" || normRisk === "HIGH") riskColor = "var(--color-danger)";
  else if (normRisk === "MEDIUM") riskColor = "var(--color-warning)";

  return (
    <Card title="Current Digital Twin State" subtitle="Real-time operational status and ML failure risk assessment">
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "var(--space-4)",
        }}
      >
        {/* Health Score */}
        <div
          style={{
            backgroundColor: "var(--color-surface-raised)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-md)",
            padding: "var(--space-4)",
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-2)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span
              style={{
                fontSize: "11px",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "var(--tracking-wider)",
                color: "var(--color-text-muted)",
              }}
            >
              Health Index
            </span>
            <Activity size={14} color="var(--color-text-muted)" />
          </div>

          <div style={{ display: "flex", alignItems: "baseline", gap: "6px" }}>
            <span
              className="text-mono"
              style={{
                fontSize: "26px",
                fontWeight: 700,
                color: healthScore !== null ? "var(--color-text-primary)" : "var(--color-text-muted)",
              }}
            >
              {healthScore !== null ? formatNumber(healthScore, 1) : "—"}
            </span>
            <span style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>/ 100</span>
          </div>

          {/* Health Progress Bar */}
          <div
            style={{
              width: "100%",
              height: "4px",
              backgroundColor: "var(--color-surface-input)",
              borderRadius: "var(--radius-full)",
              overflow: "hidden",
              marginTop: "4px",
            }}
          >
            <div
              style={{
                width: healthScore !== null ? `${Math.min(100, Math.max(0, healthScore))}%` : "0%",
                height: "100%",
                backgroundColor: healthBarColor,
                transition: "width var(--transition-normal)",
              }}
            />
          </div>

          <div style={{ marginTop: "4px" }}>
            <HealthBadge state={healthState} size="sm" />
          </div>
        </div>

        {/* Calibrated Failure Risk */}
        <div
          style={{
            backgroundColor: "var(--color-surface-raised)",
            border: `1px solid ${isHighRisk ? "var(--color-danger-border)" : "var(--color-border)"}`,
            borderRadius: "var(--radius-md)",
            padding: "var(--space-4)",
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-2)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span
              style={{
                fontSize: "11px",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "var(--tracking-wider)",
                color: "var(--color-text-muted)",
              }}
            >
              Failure Probability
            </span>
            <ShieldAlert size={14} color={isHighRisk ? "var(--color-danger)" : "var(--color-text-muted)"} />
          </div>

          <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
            <span
              className="text-mono"
              style={{
                fontSize: "26px",
                fontWeight: 700,
                color: isHighRisk ? "var(--color-danger)" : "var(--color-text-primary)",
              }}
            >
              {failureProbability !== null ? formatPercent(failureProbability) : "—"}
            </span>
            <span
              className="text-mono"
              style={{
                fontSize: "10px",
                color: "var(--color-text-muted)",
              }}
            >
              (t* = 0.16)
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "4px" }}>
            <span
              style={{
                fontSize: "11px",
                fontWeight: 700,
                padding: "2px 6px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--color-surface)",
                border: `1px solid ${riskColor}`,
                color: riskColor,
                letterSpacing: "var(--tracking-wider)",
              }}
            >
              {normRisk} RISK
            </span>
            {anomalyFlag && (
              <span
                style={{
                  fontSize: "10px",
                  fontWeight: 600,
                  padding: "2px 5px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: "var(--color-warning-subtle)",
                  color: "var(--color-warning)",
                  border: "1px solid var(--color-warning-border)",
                }}
              >
                ANOMALY DETECTED
              </span>
            )}
          </div>
        </div>

        {/* Operating State & Telemetry Sync */}
        <div
          style={{
            backgroundColor: "var(--color-surface-raised)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-md)",
            padding: "var(--space-4)",
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-2)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span
              style={{
                fontSize: "11px",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "var(--tracking-wider)",
                color: "var(--color-text-muted)",
              }}
            >
              Operational Sync
            </span>
            <Radio size={14} color="var(--color-text-muted)" />
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <StatusBadge status={operatingState} size="md" />
            <span
              style={{
                fontSize: "12px",
                fontWeight: 600,
                color: "var(--color-text-secondary)",
              }}
            >
              {connectivityState}
            </span>
          </div>

          <div
            style={{
              fontSize: "11px",
              color: "var(--color-text-muted)",
              display: "flex",
              flexDirection: "column",
              gap: "2px",
              marginTop: "4px",
            }}
          >
            {lastTelemetryTs && (
              <span>Last packet: {formatDateTime(lastTelemetryTs)}</span>
            )}
            {typeof lastSeq === "number" && (
              <span className="text-mono" style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <Hash size={11} /> Seq: {lastSeq}
              </span>
            )}
          </div>
        </div>

        {/* Edge / ML Metadata */}
        <div
          style={{
            backgroundColor: "var(--color-surface-raised)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-md)",
            padding: "var(--space-4)",
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-2)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span
              style={{
                fontSize: "11px",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "var(--tracking-wider)",
                color: "var(--color-text-muted)",
              }}
            >
              Edge Intelligence
            </span>
            <Cpu size={14} color="var(--color-text-muted)" />
          </div>

          <div style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
              <span style={{ color: "var(--color-text-muted)" }}>Model Version:</span>
              <span className="text-mono">{modelVersion || "v1.0-xgb"}</span>
            </div>
            {typeof anomalyScore === "number" && (
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                <span style={{ color: "var(--color-text-muted)" }}>Anomaly Score:</span>
                <span className="text-mono">{formatNumber(anomalyScore, 3)}</span>
              </div>
            )}
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--color-text-muted)" }}>Decision Threshold:</span>
              <span className="text-mono">t* = 0.16</span>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};
