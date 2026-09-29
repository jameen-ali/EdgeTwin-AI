import React from "react";
import { HistoricalPredictionPoint } from "../../types/history";
import { StatusBadge } from "../common/StatusBadge";
import { EmptyState } from "../common/EmptyState";
import { Brain, AlertCircle } from "lucide-react";

export interface HistoricalPredictionTimelineProps {
  predictions: HistoricalPredictionPoint[];
}

export const HistoricalPredictionTimeline: React.FC<HistoricalPredictionTimelineProps> = ({
  predictions,
}) => {
  if (predictions.length === 0) {
    return (
      <div
        style={{
          backgroundColor: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-lg)",
          padding: "var(--space-6)",
        }}
      >
        <EmptyState
          icon={<Brain size={32} />}
          title="No Historical Predictions"
          description="Historical prediction records are not available for this machine in the selected window."
        />
      </div>
    );
  }

  return (
    <div
      style={{
        backgroundColor: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--space-4) var(--space-5)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-4)",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "var(--space-2)",
        }}
      >
        <div>
          <h3
            style={{
              fontSize: "14px",
              fontWeight: 600,
              color: "var(--color-text-primary)",
              margin: 0,
            }}
          >
            Persisted Model Assessments ({predictions.length})
          </h3>
          <p
            style={{
              fontSize: "12px",
              color: "var(--color-text-muted)",
              margin: "2px 0 0 0",
            }}
          >
            Historical supervised failure risk ($t^*=0.160$) and unsupervised anomaly inference
          </p>
        </div>

        <span
          style={{
            fontSize: "11px",
            fontFamily: "var(--font-mono)",
            color: "var(--color-accent)",
            backgroundColor: "rgba(20, 154, 251, 0.1)",
            padding: "2px 8px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-accent-border)",
          }}
        >
          Model: {predictions[0]?.model_version || "v1.2-xgb"}
        </span>
      </div>

      {/* Table of predictions */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
          <thead>
            <tr
              style={{
                borderBottom: "1px solid var(--color-border)",
                textAlign: "left",
                color: "var(--color-text-muted)",
              }}
            >
              <th style={{ padding: "8px 12px", fontWeight: 500 }}>Timestamp (UTC)</th>
              <th style={{ padding: "8px 12px", fontWeight: 500 }}>Failure Risk p(fail)</th>
              <th style={{ padding: "8px 12px", fontWeight: 500 }}>Risk Band</th>
              <th style={{ padding: "8px 12px", fontWeight: 500 }}>Anomaly Status</th>
              <th style={{ padding: "8px 12px", fontWeight: 500 }}>Top Contributing Factors (TreeSHAP)</th>
            </tr>
          </thead>
          <tbody>
            {predictions.map((p) => {
              const pPercent = (p.failure_probability * 100).toFixed(1);
              const isHighRisk = p.failure_probability >= 0.16;
              const formattedDate = new Date(p.ts).toLocaleString([], {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              });

              return (
                <tr
                  key={p.id}
                  style={{
                    borderBottom: "1px solid rgba(255, 255, 255, 0.04)",
                    backgroundColor: isHighRisk ? "rgba(239, 68, 68, 0.04)" : "transparent",
                  }}
                >
                  <td style={{ padding: "10px 12px", fontFamily: "var(--font-mono)", color: "var(--color-text-primary)" }}>
                    {formattedDate}
                  </td>
                  <td style={{ padding: "10px 12px" }}>
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontWeight: 700,
                        color: isHighRisk ? "var(--color-danger)" : "var(--color-success)",
                      }}
                    >
                      {pPercent}%
                    </span>
                  </td>
                  <td style={{ padding: "10px 12px" }}>
                    <StatusBadge
                      status={p.risk_band}
                      size="sm"
                    />
                  </td>
                  <td style={{ padding: "10px 12px" }}>
                    {p.anomaly_flag ? (
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "4px",
                          color: "var(--color-warning)",
                          fontSize: "11px",
                          fontWeight: 600,
                        }}
                      >
                        <AlertCircle size={13} />
                        ANOMALY DETECTED {p.anomaly_score !== null ? `(${p.anomaly_score.toFixed(2)})` : ""}
                      </span>
                    ) : (
                      <span style={{ color: "var(--color-text-muted)", fontSize: "11px" }}>
                        Nominal {p.anomaly_score !== null ? `(${p.anomaly_score.toFixed(2)})` : ""}
                      </span>
                    )}
                  </td>
                  <td style={{ padding: "10px 12px", color: "var(--color-text-secondary)" }}>
                    {p.top_factors && p.top_factors.length > 0 ? (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                        {p.top_factors.slice(0, 3).map((f, fIdx) => (
                          <span
                            key={fIdx}
                            style={{
                              fontSize: "11px",
                              fontFamily: "var(--font-mono)",
                              backgroundColor: "var(--color-surface-hover)",
                              padding: "2px 6px",
                              borderRadius: "var(--radius-sm)",
                              border: "1px solid var(--color-border)",
                            }}
                          >
                            {f.feature}: {f.shap_value >= 0 ? `+${f.shap_value.toFixed(2)}` : f.shap_value.toFixed(2)}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span style={{ color: "var(--color-text-muted)" }}>—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
