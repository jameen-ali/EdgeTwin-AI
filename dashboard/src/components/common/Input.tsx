import React from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  isMono?: boolean;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, isMono = false, style, id, disabled, ...props }, ref) => {
    const inputId = id || (label ? `input-${label.toLowerCase().replace(/\s+/g, "-")}` : undefined);

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "6px", width: "100%" }}>
        {label && (
          <label
            htmlFor={inputId}
            style={{
              fontSize: "12px",
              fontWeight: 500,
              color: "var(--color-text-secondary)",
              letterSpacing: "var(--tracking-wide)",
            }}
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          disabled={disabled}
          style={{
            height: "36px",
            padding: "0 12px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--color-surface-input)",
            border: `1px solid ${error ? "var(--color-danger)" : "var(--color-border)"}`,
            color: "var(--color-text-primary)",
            fontSize: "13px",
            fontFamily: isMono ? "var(--font-mono)" : "var(--font-sans)",
            opacity: disabled ? 0.5 : 1,
            cursor: disabled ? "not-allowed" : "text",
            transition: "border-color var(--transition-fast)",
            ...style,
          }}
          {...props}
        />
        {error && (
          <span style={{ fontSize: "11px", color: "var(--color-danger)", marginTop: "2px" }}>
            {error}
          </span>
        )}
        {!error && helperText && (
          <span style={{ fontSize: "11px", color: "var(--color-text-muted)", marginTop: "2px" }}>
            {helperText}
          </span>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
