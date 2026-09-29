import React from "react";
import { ShieldAlert, ShieldCheck, Activity, Clock, Layers } from "lucide-react";
import { Card } from "../common/Card";
import { LoadingState } from "../common/LoadingState";
import { FeatureContributions } from "./FeatureContributions";
import { RecommendationPanel } from "./RecommendationPanel";
import { FeatureContribution, MaintenanceRecommendation } from "../../types/prediction";
import { formatPercent, formatNumber, formatDateTime } from "../../utils/formatters";

export interface PredictionPanelProps {
  failureProbability: number | null;
  riskBand: string | null;
  anomalyScore?: number | null;
  anomalyFlag?: boolean | null;
  modelVersion?: string;
  predictionTs?: string | null;
  topFactors?: FeatureContribution[] | null;
  recommendation?: MaintenanceRecommendation | null;
  isLoading?: boolean;
  onScheduleMaintenance?: () => void;
}

export const PredictionPanel: React.FC<PredictionPanelProps> = ({
  failureProbability,
  riskBand,
  anomalyScore,
  anomalyFlag,
  modelVersion = "v1.2-xgb",
  predictionTs,
  topFactors,
  recommendation,
  isLoading = false,
  onScheduleMaintenance,
}) => {
  const isElevated = failureProbability !== null && failureProbability > 0.16;
  const normRisk = (riskBand || "LOW").toUpperCase();

  let riskColor = "var(--color-success)";
  let riskBg = "var(--color-success-subtle)";
  let riskBorder = "var(--color-success-border)";

  if (normRisk === "CRITICAL" || normRisk === "HIGH") {
    riskColor = "var(--color-danger)";
    riskBg = "var(--color-danger-subtle)";
    riskBorder = "var(--color-danger-border)";
  } else if (normRisk === "MEDIUM") {
    riskColor = "var(--color-warning)";
    riskBg = "var(--color-warning-subtle)";
    riskBorder = "var(--color-warning-border)";
  }

  return (
    <Card
      title="AI Predictive Assessment"
      subtitle="Supervised failure probability, anomaly detection, and explainability"
      action={
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span
            className="text-mono"
            style={{
              fontSize: "10px",
              color: "var(--color-text-muted)",
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
          >
            <Layers size={11} /> Model: {modelVersion}
          </span>
        </div>
      }
    >
      {isLoading ? (
        <LoadingState message="Loading prediction and model explanation..." />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
        {/* Top Summary Metrics Row */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "var(--space-3)",
          }}
        >
          {/* 1. Calibrated Failure Risk */}
          <div
            style={{
              backgroundColor: "var(--color-surface-raised)",
              border: `1px solid ${isElevated ? "var(--color-danger-border)" : "var(--color-border)"}`,
              borderRadius: "var(--radius-md)",
              padding: "var(--space-3) var(--space-4)",
              display: "flex",
              flexDirection: "column",
              gap: "4px",
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
              {isElevated ? (
                <ShieldAlert size={14} color="var(--color-danger)" />
              ) : (
                <ShieldCheck size={14} color="var(--color-success)" />
              )}
            </div>

            <div style={{ display: "flex", alignItems: "baseline", gap: "6px" }}>
              <span
                className="text-mono"
                style={{
                  fontSize: "24px",
                  fontWeight: 700,
                  color: isElevated ? "var(--color-danger)" : "var(--color-text-primary)",
                  lineHeight: 1.1,
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

            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "2px" }}>
              <span
                style={{
                  fontSize: "10px",
                  fontWeight: 700,
                  padding: "1px 6px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: riskBg,
                  color: riskColor,
                  border: `1px solid ${riskBorder}`,
                  letterSpacing: "var(--tracking-wider)",
                }}
              >
                {normRisk} RISK
              </span>
              <span style={{ fontSize: "10px", color: "var(--color-text-muted)" }}>
                {isElevated ? "Above decision threshold" : "Within normal baseline"}
              </span>
            </div>
          </div>

          {/* 2. Unsupervised Anomaly Detection */}
          <div
            style={{
              backgroundColor: "var(--color-surface-raised)",
              border: `1px solid ${
                anomalyFlag ? "var(--color-warning-border)" : "var(--color-border)"
              }`,
              borderRadius: "var(--radius-md)",
              padding: "var(--space-3) var(--space-4)",
              display: "flex",
              flexDirection: "column",
              gap: "4px",
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
                Anomaly Monitor
              </span>
              <Activity
                size={14}
                color={anomalyFlag ? "var(--color-warning)" : "var(--color-text-muted)"}
              />
            </div>

            <div style={{ display: "flex", alignItems: "baseline", gap: "6px" }}>
              <span
                className="text-mono"
                style={{
                  fontSize: "24px",
                  fontWeight: 700,
                  color: anomalyFlag ? "var(--color-warning)" : "var(--color-text-primary)",
                  lineHeight: 1.1,
                }}
              >
                {typeof anomalyScore === "number" ? formatNumber(anomalyScore, 3) : "—"}
              </span>
              <span style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>score</span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "2px" }}>
              <span
                style={{
                  fontSize: "10px",
                  fontWeight: 700,
                  padding: "1px 6px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: anomalyFlag
                    ? "var(--color-warning-subtle)"
                    : "var(--color-surface-input)",
                  color: anomalyFlag ? "var(--color-warning)" : "var(--color-text-muted)",
                  border: `1px solid ${
                    anomalyFlag ? "var(--color-warning-border)" : "var(--color-border-subtle)"
                  }`,
                }}
              >
                {anomalyFlag ? "ANOMALY DETECTED" : "NOMINAL"}
              </span>
              <span style={{ fontSize: "10px", color: "var(--color-text-muted)" }}>
                Isolation Forest
              </span>
            </div>
          </div>

          {/* 3. Decision Governance Meta */}
          <div
            style={{
              backgroundColor: "var(--color-surface-raised)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              padding: "var(--space-3) var(--space-4)",
              display: "flex",
              flexDirection: "column",
              gap: "4px",
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
                Governance & Timing
              </span>
              <Clock size={14} color="var(--color-text-muted)" />
            </div>

            <div style={{ fontSize: "12px", color: "var(--color-text-secondary)", display: "flex", flexDirection: "column", gap: "2px", marginTop: "4px" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--color-text-muted)" }}>Threshold:</span>
                <span className="text-mono" style={{ fontWeight: 600 }}>t* = 0.16</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--color-text-muted)" }}>Assessed:</span>
                <span className="text-mono" style={{ fontSize: "11px" }}>
                  {predictionTs ? formatDateTime(predictionTs) : "Live Stream"}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Feature Contributions (Why this prediction?) */}
        <FeatureContributions factors={topFactors} />

        {/* System Recommendation */}
        {recommendation && (
          <RecommendationPanel
            recommendation={recommendation}
            onScheduleMaintenance={onScheduleMaintenance}
          />
        )}
      </div>
      )}
    </Card>
  );
};
