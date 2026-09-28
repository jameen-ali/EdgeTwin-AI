import React from "react";
import { HealthState } from "../../types/machine";

export interface HealthBadgeProps {
  state: HealthState | string;
  size?: "sm" | "md";
}

export const HealthBadge: React.FC<HealthBadgeProps> = ({ state, size = "md" }) => {
  const norm = (state || "").toUpperCase();

  let bg = "var(--color-surface-raised)";
  let color = "var(--color-text-muted)";
  let border = "var(--color-border)";
  let shapeSymbol = "○"; // Offline / fallback

  if (norm === "HEALTHY") {
    bg = "var(--color-success-subtle)";
    color = "var(--color-success)";
    border = "var(--color-success-border)";
    shapeSymbol = "●"; // Circle
  } else if (norm === "WARNING") {
    bg = "var(--color-warning-subtle)";
    color = "var(--color-warning)";
    border = "var(--color-warning-border)";
    shapeSymbol = "▲"; // Triangle
  } else if (norm === "CRITICAL") {
    bg = "var(--color-danger-subtle)";
    color = "var(--color-danger)";
    border = "var(--color-danger-border)";
    shapeSymbol = "■"; // Square
  } else if (norm === "MAINTENANCE REQUIRED" || norm === "MAINTENANCE") {
    bg = "var(--color-maintenance-subtle)";
    color = "var(--color-maintenance)";
    border = "var(--color-maintenance-border)";
    shapeSymbol = "◆"; // Diamond
  }

  const isSmall = size === "sm";

  return (
    <span
      role="status"
      aria-label={`Machine health: ${norm}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: isSmall ? "5px" : "6px",
        padding: isSmall ? "2px 7px" : "3px 9px",
        borderRadius: "var(--radius-sm)",
        fontSize: isSmall ? "11px" : "12px",
        fontWeight: 600,
        letterSpacing: "var(--tracking-wide)",
        textTransform: "uppercase",
        backgroundColor: bg,
        color: color,
        border: `1px solid ${border}`,
        lineHeight: 1,
      }}
    >
      <span style={{ fontSize: isSmall ? "10px" : "11px" }} aria-hidden="true">
        {shapeSymbol}
      </span>
      <span>{norm}</span>
    </span>
  );
};
