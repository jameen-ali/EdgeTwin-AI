import React from "react";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: SelectOption[];
  error?: string;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, options, error, style, id, disabled, ...props }, ref) => {
    const selectId = id || (label ? `select-${label.toLowerCase().replace(/\s+/g, "-")}` : undefined);

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "6px", width: "100%" }}>
        {label && (
          <label
            htmlFor={selectId}
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
        <select
          ref={ref}
          id={selectId}
          disabled={disabled}
          style={{
            height: "36px",
            padding: "0 12px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--color-surface-input)",
            border: `1px solid ${error ? "var(--color-danger)" : "var(--color-border)"}`,
            color: "var(--color-text-primary)",
            fontSize: "13px",
            fontFamily: "var(--font-sans)",
            opacity: disabled ? 0.5 : 1,
            cursor: disabled ? "not-allowed" : "pointer",
            ...style,
          }}
          {...props}
        >
          {options.map((opt) => (
            <option
              key={opt.value}
              value={opt.value}
              style={{ backgroundColor: "var(--color-surface-raised)", color: "var(--color-text-primary)" }}
            >
              {opt.label}
            </option>
          ))}
        </select>
        {error && (
          <span style={{ fontSize: "11px", color: "var(--color-danger)", marginTop: "2px" }}>
            {error}
          </span>
        )}
      </div>
    );
  }
);

Select.displayName = "Select";
