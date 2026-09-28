import React from "react";
import { Inbox } from "lucide-react";

export interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon,
  action,
}) => {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        padding: "var(--space-12) var(--space-6)",
        backgroundColor: "var(--color-surface)",
        border: "1px dashed var(--color-border)",
        borderRadius: "var(--radius-lg)",
        minHeight: "220px",
        gap: "var(--space-3)",
      }}
    >
      <div
        style={{
          width: "44px",
          height: "44px",
          borderRadius: "var(--radius-md)",
          backgroundColor: "var(--color-surface-raised)",
          border: "1px solid var(--color-border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--color-text-muted)",
          marginBottom: "var(--space-2)",
        }}
      >
        {icon || <Inbox size={22} />}
      </div>

      <h3
        style={{
          fontSize: "15px",
          fontWeight: 600,
          color: "var(--color-text-primary)",
          letterSpacing: "var(--tracking-tight)",
        }}
      >
        {title}
      </h3>

      <p
        style={{
          fontSize: "13px",
          color: "var(--color-text-muted)",
          maxWidth: "380px",
          lineHeight: 1.4,
        }}
      >
        {description}
      </p>

      {action && <div style={{ marginTop: "var(--space-3)" }}>{action}</div>}
    </div>
  );
};
