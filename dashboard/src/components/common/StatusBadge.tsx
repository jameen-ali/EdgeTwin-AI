import React from "react";
import { CheckCircle2, AlertOctagon, Radio, Clock, Disc } from "lucide-react";
import { OperatingState, ConnectivityState } from "../../types/machine";

export type AnyStatus = OperatingState | ConnectivityState | "ONLINE" | "OFFLINE" | string;

export interface StatusBadgeProps {
  status: AnyStatus;
  size?: "sm" | "md";
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = "md" }) => {
  const norm = (status || "").toUpperCase();

  let bg = "var(--color-surface-raised)";
  let color = "var(--color-text-muted)";
  let border = "var(--color-border)";
  let IconComponent = Disc;

  if (norm === "RUNNING" || norm === "ONLINE") {
    bg = "var(--color-success-subtle)";
    color = "var(--color-success)";
    border = "var(--color-success-border)";
    IconComponent = CheckCircle2;
  } else if (norm === "TRIPPED") {
    bg = "var(--color-danger-subtle)";
    color = "var(--color-danger)";
    border = "var(--color-danger-border)";
    IconComponent = AlertOctagon;
  } else if (norm === "LIVE") {
    bg = "var(--color-accent-subtle)";
    color = "var(--color-accent)";
    border = "var(--color-accent-border)";
    IconComponent = Radio;
  } else if (norm === "STALE") {
    bg = "var(--color-warning-subtle)";
    color = "var(--color-warning)";
    border = "var(--color-warning-border)";
    IconComponent = Clock;
  }

  const isSmall = size === "sm";

  return (
    <span
      role="status"
      aria-label={`Status: ${norm}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: isSmall ? "4px" : "6px",
        padding: isSmall ? "2px 6px" : "3px 8px",
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
      <IconComponent size={isSmall ? 11 : 13} aria-hidden="true" />
      <span>{norm}</span>
    </span>
  );
};
