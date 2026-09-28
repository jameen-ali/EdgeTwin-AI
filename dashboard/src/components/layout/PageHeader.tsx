import React from "react";

export interface PageHeaderProps {
  title: string;
  description?: string;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  description,
  badge,
  actions,
}) => {
  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: "var(--space-4)",
        marginBottom: "var(--space-6)",
      }}
    >
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
          <h1 className="page-title">{title}</h1>
          {badge}
        </div>
        {description && (
          <p
            style={{
              fontSize: "13px",
              color: "var(--color-text-secondary)",
              marginTop: "4px",
              maxWidth: "680px",
              lineHeight: 1.4,
            }}
          >
            {description}
          </p>
        )}
      </div>

      {actions && (
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
          {actions}
        </div>
      )}
    </div>
  );
};
