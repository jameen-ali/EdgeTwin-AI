import React from "react";
import { WebSocketStatus } from "../../types/websocket";

export interface ConnectionIndicatorProps {
  status: WebSocketStatus | "ONLINE" | "OFFLINE";
  label?: string;
}

export const ConnectionIndicator: React.FC<ConnectionIndicatorProps> = ({ status, label }) => {
  const isLive = status === "CONNECTED" || status === "ONLINE";
  const isConnecting = status === "CONNECTING";

  let dotColor = "var(--color-text-muted)";
  let text = label || "Offline";

  if (isLive) {
    dotColor = "var(--color-success)";
    text = label || "Live";
  } else if (isConnecting) {
    dotColor = "var(--color-warning)";
    text = label || "Connecting";
  }

  return (
    <div
      role="status"
      aria-label={`Connection status: ${text}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
        padding: "3px 8px",
        borderRadius: "var(--radius-sm)",
        backgroundColor: "var(--color-surface-raised)",
        border: "1px solid var(--color-border)",
        fontSize: "11px",
        fontWeight: 600,
        textTransform: "uppercase",
        letterSpacing: "var(--tracking-wide)",
        color: "var(--color-text-secondary)",
      }}
    >
      <span
        style={{
          width: "6px",
          height: "6px",
          borderRadius: "var(--radius-full)",
          backgroundColor: dotColor,
          boxShadow: isLive ? "0 0 6px var(--color-success)" : "none",
        }}
      />
      <span>{text}</span>
    </div>
  );
};
