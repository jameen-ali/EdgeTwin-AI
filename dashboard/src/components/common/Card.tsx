import React from "react";

export interface CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, "title"> {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  footer?: React.ReactNode;
  noPadding?: boolean;
}

export const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  action,
  footer,
  noPadding = false,
  children,
  style,
  className = "",
  ...props
}) => {
  return (
    <div
      style={{
        backgroundColor: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-lg)",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        ...style,
      }}
      className={`card ${className}`}
      {...props}
    >
      {(title || action) && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "var(--space-4) var(--space-5)",
            borderBottom: "1px solid var(--color-border-subtle)",
          }}
        >
          <div>
            {typeof title === "string" ? (
              <h3
                style={{
                  fontSize: "14px",
                  fontWeight: 600,
                  letterSpacing: "var(--tracking-tight)",
                  color: "var(--color-text-primary)",
                }}
              >
                {title}
              </h3>
            ) : (
              title
            )}
            {subtitle && (
              <p
                style={{
                  fontSize: "12px",
                  color: "var(--color-text-muted)",
                  marginTop: "2px",
                }}
              >
                {subtitle}
              </p>
            )}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}

      <div
        style={{
          flex: 1,
          padding: noPadding ? 0 : "var(--space-5)",
        }}
      >
        {children}
      </div>

      {footer && (
        <div
          style={{
            padding: "var(--space-3) var(--space-5)",
            borderTop: "1px solid var(--color-border-subtle)",
            backgroundColor: "var(--color-surface-raised)",
          }}
        >
          {footer}
        </div>
      )}
    </div>
  );
};
