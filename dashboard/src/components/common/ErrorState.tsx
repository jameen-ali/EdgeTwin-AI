import React from "react";
import { AlertCircle, RotateCcw } from "lucide-react";
import { Button } from "./Button";
import { ProblemDetails } from "../../types/api";

export interface ErrorStateProps {
  title?: string;
  message?: string;
  problem?: ProblemDetails;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = "Operational Error",
  message = "Failed to communicate with EdgeTwin API.",
  problem,
  onRetry,
}) => {
  const detail = problem?.detail || message;
  const status = problem?.status;

  return (
    <div
      role="alert"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        padding: "var(--space-8) var(--space-6)",
        backgroundColor: "var(--color-surface)",
        border: "1px solid var(--color-danger-border)",
        borderRadius: "var(--radius-lg)",
        gap: "var(--space-3)",
      }}
    >
      <div
        style={{
          width: "40px",
          height: "40px",
          borderRadius: "var(--radius-md)",
          backgroundColor: "var(--color-danger-subtle)",
          border: "1px solid var(--color-danger-border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--color-danger)",
        }}
      >
        <AlertCircle size={22} />
      </div>

      <div>
        <h3
          style={{
            fontSize: "15px",
            fontWeight: 600,
            color: "var(--color-danger)",
            letterSpacing: "var(--tracking-tight)",
          }}
        >
          {status ? `[HTTP ${status}] ${title}` : title}
        </h3>
        <p
          style={{
            fontSize: "13px",
            color: "var(--color-text-secondary)",
            maxWidth: "460px",
            marginTop: "4px",
            lineHeight: 1.4,
          }}
        >
          {detail}
        </p>
      </div>

      {onRetry && (
        <Button
          variant="secondary"
          size="sm"
          leftIcon={<RotateCcw size={14} />}
          onClick={onRetry}
          style={{ marginTop: "var(--space-2)" }}
        >
          Retry Request
        </Button>
      )}
    </div>
  );
};
