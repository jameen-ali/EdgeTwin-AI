import React from "react";

export interface LiveIndicatorProps {
  isLive?: boolean;
  label?: string;
}

export const LiveIndicator: React.FC<LiveIndicatorProps> = ({ isLive = true, label = "LIVE" }) => {
  return (
    <span
      role="status"
      aria-label={`Real-time status: ${isLive ? "Live" : "Disconnected"}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
        fontSize: "11px",
        fontWeight: 700,
        letterSpacing: "var(--tracking-wider)",
        color: isLive ? "var(--color-accent)" : "var(--color-text-muted)",
        textTransform: "uppercase",
      }}
    >
      <span
        className={isLive ? "live-pulse-dot" : ""}
        style={{
          width: "7px",
          height: "7px",
          borderRadius: "var(--radius-full)",
          backgroundColor: isLive ? "var(--color-accent)" : "var(--color-text-muted)",
          display: "inline-block",
        }}
      />
      <span>{label}</span>
    </span>
  );
};
