import React from "react";
import { Info, HelpCircle } from "lucide-react";
import { FeatureContribution } from "../../types/prediction";
import { formatNumber } from "../../utils/formatters";

export interface FeatureContributionsProps {
  factors?: FeatureContribution[] | null;
  emptyMessage?: string;
  disclaimer?: string;
}

// Friendly feature name mapping
const FEATURE_LABELS: Record<string, { label: string; unit?: string }> = {
  vibration_mm_s: { label: "Vibration RMS", unit: "mm/s" },
  process_temp_c: { label: "Process Temperature", unit: "°C" },
  air_temp_c: { label: "Ambient Air Temperature", unit: "°C" },
  rotational_speed_rpm: { label: "Rotational Speed", unit: "RPM" },
  torque_nm: { label: "Shaft Torque", unit: "Nm" },
  current_a: { label: "Phase Current", unit: "A" },
  pressure_bar: { label: "Hydraulic Pressure", unit: "bar" },
  voltage_v: { label: "Supply Voltage", unit: "V" },
  tool_wear_min: { label: "Cumulative Tool Wear", unit: "min" },
  operating_hours: { label: "Operating Time", unit: "hrs" },
  delta_t_c: { label: "Temperature Delta (ΔT)", unit: "°C" },
  power_va: { label: "Apparent Power", unit: "VA" },
};

export const FeatureContributions: React.FC<FeatureContributionsProps> = ({
  factors,
  emptyMessage = "No explanation is currently available for this prediction.",
  disclaimer = "Feature contributions indicate how each feature influenced the model output in log-odds margin space for this prediction. They are not causal explanations.",
}) => {
  if (!factors || factors.length === 0) {
    return (
      <div
        style={{
          padding: "var(--space-4)",
          backgroundColor: "var(--color-surface-raised)",
          border: "1px dashed var(--color-border)",
          borderRadius: "var(--radius-md)",
          textAlign: "center",
          color: "var(--color-text-muted)",
          fontSize: "12px",
        }}
      >
        {emptyMessage}
      </div>
    );
  }

  // Find max absolute contribution to scale horizontal bars proportionally
  const maxAbs = Math.max(...factors.map((f) => Math.abs(f.shap_value)), 0.01);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span
          style={{
            fontSize: "11px",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "var(--tracking-wider)",
            color: "var(--color-text-muted)",
          }}
        >
          Top Model Contributions (TreeSHAP)
        </span>
        <span
          style={{
            fontSize: "10px",
            color: "var(--color-text-muted)",
            display: "flex",
            alignItems: "center",
            gap: "4px",
          }}
        >
          <HelpCircle size={11} /> Margin Log-Odds Impact
        </span>
      </div>

      {/* Feature Contributions List */}
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
        {factors.map((factor, idx) => {
          const config = FEATURE_LABELS[factor.feature_name] || {
            label: factor.feature_name.replace(/_/g, " "),
          };
          const isPositive = factor.shap_value > 0;
          const absVal = Math.abs(factor.shap_value);
          const barWidthPercent = Math.min(100, Math.max(8, (absVal / maxAbs) * 100));

          // Color: positive SHAP increases risk (red/orange), negative lowers risk (green/cyan)
          const barColor = isPositive ? "var(--color-danger)" : "var(--color-success)";
          const barBg = isPositive ? "var(--color-danger-subtle)" : "var(--color-success-subtle)";

          return (
            <div
              key={`${factor.feature_name}-${idx}`}
              style={{
                backgroundColor: "var(--color-surface-raised)",
                border: "1px solid var(--color-border-subtle)",
                borderRadius: "var(--radius-sm)",
                padding: "8px 12px",
                display: "flex",
                flexDirection: "column",
                gap: "6px",
              }}
            >
              {/* Row 1: Label, Feature Value, Contribution Badge */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "var(--space-2)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span
                    style={{
                      fontSize: "12px",
                      fontWeight: 600,
                      color: "var(--color-text-primary)",
                    }}
                  >
                    {config.label}
                  </span>
                  {factor.feature_value !== undefined && factor.feature_value !== null && (
                    <span
                      className="text-mono"
                      style={{
                        fontSize: "11px",
                        color: "var(--color-text-secondary)",
                        backgroundColor: "var(--color-surface)",
                        padding: "1px 6px",
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid var(--color-border-subtle)",
                      }}
                    >
                      Value: {formatNumber(factor.feature_value, 2)} {config.unit || ""}
                    </span>
                  )}
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <span
                    className="text-mono"
                    style={{
                      fontSize: "12px",
                      fontWeight: 700,
                      color: barColor,
                    }}
                  >
                    {isPositive ? `+${formatNumber(factor.shap_value, 3)}` : formatNumber(factor.shap_value, 3)}
                  </span>
                  <span
                    style={{
                      fontSize: "10px",
                      fontWeight: 600,
                      padding: "1px 5px",
                      borderRadius: "var(--radius-sm)",
                      backgroundColor: barBg,
                      color: barColor,
                      textTransform: "uppercase",
                    }}
                  >
                    {isPositive ? "Increases Risk" : "Lowers Risk"}
                  </span>
                </div>
              </div>

              {/* Row 2: Relative Magnitude Bar */}
              <div
                style={{
                  width: "100%",
                  height: "5px",
                  backgroundColor: "var(--color-surface-input)",
                  borderRadius: "var(--radius-full)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${barWidthPercent}%`,
                    height: "100%",
                    backgroundColor: barColor,
                    borderRadius: "var(--radius-full)",
                    transition: "width var(--transition-normal)",
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Honest Scientific Disclaimer */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: "6px",
          padding: "6px 10px",
          backgroundColor: "var(--color-surface)",
          border: "1px solid var(--color-border-subtle)",
          borderRadius: "var(--radius-sm)",
          fontSize: "11px",
          color: "var(--color-text-muted)",
          lineHeight: 1.4,
          marginTop: "var(--space-1)",
        }}
      >
        <Info size={14} style={{ flexShrink: 0, marginTop: "1px" }} />
        <span>{disclaimer}</span>
      </div>
    </div>
  );
};
