import React from "react";

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon: React.ReactNode;
  "aria-label": string;
  size?: "sm" | "md" | "lg";
  variant?: "ghost" | "secondary";
}

export const IconButton: React.FC<IconButtonProps> = ({
  icon,
  "aria-label": ariaLabel,
  size = "md",
  variant = "ghost",
  style,
  disabled,
  className = "",
  ...props
}) => {
  const dim = size === "sm" ? 28 : size === "lg" ? 38 : 32;

  const baseStyles: React.CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    width: `${dim}px`,
    height: `${dim}px`,
    borderRadius: "var(--radius-sm)",
    backgroundColor: variant === "secondary" ? "var(--color-surface-raised)" : "transparent",
    border: variant === "secondary" ? "1px solid var(--color-border)" : "1px solid transparent",
    color: "var(--color-text-secondary)",
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.5 : 1,
    transition: "all var(--transition-fast)",
    ...style,
  };

  return (
    <button
      aria-label={ariaLabel}
      disabled={disabled}
      style={baseStyles}
      className={`icon-btn ${className}`}
      {...props}
    >
      {icon}
    </button>
  );
};
