import React from "react";
import { Loader2 } from "lucide-react";

export interface LoadingStateProps {
  message?: string;
  size?: number;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = "Loading operational telemetry...",
  size = 24,
}) => {
  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "var(--space-12) var(--space-4)",
        gap: "var(--space-3)",
        color: "var(--color-text-muted)",
        minHeight: "180px",
      }}
    >
      <Loader2 size={size} className="spinner" style={{ color: "var(--color-accent)" }} />
      <span
        style={{
          fontSize: "13px",
          letterSpacing: "var(--tracking-wide)",
          color: "var(--color-text-secondary)",
        }}
      >
        {message}
      </span>
    </div>
  );
};
