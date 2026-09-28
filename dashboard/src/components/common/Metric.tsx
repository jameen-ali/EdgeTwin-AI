import React from "react";

export interface MetricProps {
  label: string;
  value: string | number;
  unit?: string;
  delta?: {
    value: string | number;
    isPositive?: boolean;
    label?: string;
  };
  status?: "normal" | "success" | "warning" | "danger";
  icon?: React.ReactNode;
}

export const Metric: React.FC<MetricProps> = ({
  label,
  value,
  unit,
  delta,
  status = "normal",
  icon,
}) => {
  let statusColor = "var(--color-border)";
  if (status === "success") statusColor = "var(--color-success)";
  if (status === "warning") statusColor = "var(--color-warning)";
  if (status === "danger") statusColor = "var(--color-danger)";

  return (
    <div
      style={{
        backgroundColor: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--space-4) var(--space-5)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-2)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {status !== "normal" && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: "2px",
            backgroundColor: statusColor,
          }}
        />
      )}

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span
          style={{
            fontSize: "12px",
            fontWeight: 500,
            textTransform: "uppercase",
            letterSpacing: "var(--tracking-wider)",
            color: "var(--color-text-muted)",
          }}
        >
          {label}
        </span>
        {icon && <span style={{ color: "var(--color-text-muted)" }}>{icon}</span>}
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: "6px",
        }}
      >
        <span
          className="text-mono"
          style={{
            fontSize: "28px",
            fontWeight: 700,
            letterSpacing: "var(--tracking-tight)",
            color: "var(--color-text-primary)",
            lineHeight: 1.1,
          }}
        >
          {value}
        </span>
        {unit && (
          <span
            style={{
              fontSize: "13px",
              fontWeight: 500,
              color: "var(--color-text-secondary)",
            }}
          >
            {unit}
          </span>
        )}
      </div>

      {delta && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "4px",
            fontSize: "11px",
            color: delta.isPositive ? "var(--color-success)" : "var(--color-warning)",
            marginTop: "2px",
          }}
        >
          <span>{delta.value}</span>
          {delta.label && (
            <span style={{ color: "var(--color-text-muted)" }}>{delta.label}</span>
          )}
        </div>
      )}
    </div>
  );
};
