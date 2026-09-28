import React from "react";
import { Loader2 } from "lucide-react";

export type ButtonVariant = "primary" | "secondary" | "warning" | "danger" | "ghost";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = "secondary",
  size = "md",
  isLoading = false,
  leftIcon,
  rightIcon,
  disabled,
  children,
  style,
  className = "",
  ...props
}) => {
  const getVariantStyles = (): React.CSSProperties => {
    switch (variant) {
      case "primary":
        return {
          backgroundColor: "var(--color-accent)",
          color: "#ffffff",
          border: "1px solid var(--color-accent)",
          boxShadow: "0 1px 2px rgba(0, 0, 0, 0.4)",
        };
      case "warning":
        return {
          backgroundColor: "var(--color-warning)",
          color: "#ffffff",
          border: "1px solid var(--color-warning)",
        };
      case "danger":
        return {
          backgroundColor: "var(--color-danger)",
          color: "#ffffff",
          border: "1px solid var(--color-danger)",
        };
      case "ghost":
        return {
          backgroundColor: "transparent",
          color: "var(--color-text-secondary)",
          border: "1px solid transparent",
        };
      case "secondary":
      default:
        return {
          backgroundColor: "var(--color-surface-raised)",
          color: "var(--color-text-primary)",
          border: "1px solid var(--color-border)",
        };
    }
  };

  const getSizeStyles = (): React.CSSProperties => {
    switch (size) {
      case "sm":
        return {
          height: "28px",
          padding: "0 10px",
          fontSize: "12px",
        };
      case "lg":
        return {
          height: "40px",
          padding: "0 18px",
          fontSize: "15px",
        };
      case "md":
      default:
        return {
          height: "34px",
          padding: "0 14px",
          fontSize: "13px",
        };
    }
  };

  const baseStyles: React.CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "8px",
    fontWeight: 500,
    borderRadius: "var(--radius-sm)",
    cursor: disabled || isLoading ? "not-allowed" : "pointer",
    opacity: disabled || isLoading ? 0.6 : 1,
    transition: "all var(--transition-fast)",
    whiteSpace: "nowrap",
    userSelect: "none",
    ...getVariantStyles(),
    ...getSizeStyles(),
    ...style,
  };

  return (
    <button
      disabled={disabled || isLoading}
      style={baseStyles}
      className={`btn btn-${variant} ${className}`}
      {...props}
    >
      {isLoading ? <Loader2 className="spinner" size={size === "sm" ? 14 : 16} /> : leftIcon}
      <span>{children}</span>
      {!isLoading && rightIcon}
    </button>
  );
};
