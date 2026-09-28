import React from "react";
import { CheckCircle2, AlertTriangle, AlertOctagon, Info, X } from "lucide-react";
import { IconButton } from "./IconButton";

export type ToastType = "info" | "success" | "warning" | "danger";

export interface ToastProps {
  id?: string;
  type?: ToastType;
  title: string;
  message?: string;
  onClose?: () => void;
}

export const Toast: React.FC<ToastProps> = ({
  type = "info",
  title,
  message,
  onClose,
}) => {
  let Icon = Info;
  let borderColor = "var(--color-border)";
  let accentColor = "var(--color-accent)";

  if (type === "success") {
    Icon = CheckCircle2;
    borderColor = "var(--color-success-border)";
    accentColor = "var(--color-success)";
  } else if (type === "warning") {
    Icon = AlertTriangle;
    borderColor = "var(--color-warning-border)";
    accentColor = "var(--color-warning)";
  } else if (type === "danger") {
    Icon = AlertOctagon;
    borderColor = "var(--color-danger-border)";
    accentColor = "var(--color-danger)";
  }

  return (
    <div
      role="alert"
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: "var(--space-3)",
        padding: "var(--space-3) var(--space-4)",
        backgroundColor: "var(--color-surface-raised)",
        border: `1px solid ${borderColor}`,
        borderRadius: "var(--radius-md)",
        boxShadow: "0 8px 24px rgba(0, 0, 0, 0.6)",
        maxWidth: "400px",
        minWidth: "280px",
      }}
    >
      <div style={{ color: accentColor, marginTop: "2px", flexShrink: 0 }}>
        <Icon size={16} />
      </div>

      <div style={{ flex: 1 }}>
        <div
          style={{
            fontSize: "13px",
            fontWeight: 600,
            color: "var(--color-text-primary)",
          }}
        >
          {title}
        </div>
        {message && (
          <div
            style={{
              fontSize: "12px",
              color: "var(--color-text-secondary)",
              marginTop: "2px",
            }}
          >
            {message}
          </div>
        )}
      </div>

      {onClose && (
        <IconButton
          icon={<X size={14} />}
          aria-label="Dismiss notification"
          size="sm"
          onClick={onClose}
        />
      )}
    </div>
  );
};
