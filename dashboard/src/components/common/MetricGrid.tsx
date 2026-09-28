import React from "react";

export interface MetricGridProps {
  columns?: 2 | 3 | 4;
  children: React.ReactNode;
}

export const MetricGrid: React.FC<MetricGridProps> = ({ columns = 4, children }) => {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(auto-fit, minmax(220px, 1fr))`,
        gap: "var(--space-4)",
        width: "100%",
      }}
      className={`metric-grid metric-grid-${columns}`}
    >
      {children}
    </div>
  );
};
