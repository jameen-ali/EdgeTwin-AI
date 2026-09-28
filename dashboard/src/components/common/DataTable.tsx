import React from "react";

export interface Column<T> {
  key: string;
  header: React.ReactNode;
  align?: "left" | "center" | "right";
  width?: string;
  render?: (item: T, index: number) => React.ReactNode;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (item: T, index: number) => string | number;
  onRowClick?: (item: T) => void;
  emptyMessage?: string;
}

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  onRowClick,
  emptyMessage = "No records found.",
}: DataTableProps<T>) {
  return (
    <div
      style={{
        width: "100%",
        overflowX: "auto",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-lg)",
        backgroundColor: "var(--color-surface)",
      }}
    >
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          textAlign: "left",
          fontSize: "13px",
        }}
      >
        <thead>
          <tr
            style={{
              backgroundColor: "var(--color-surface-raised)",
              borderBottom: "1px solid var(--color-border)",
            }}
          >
            {columns.map((col) => (
              <th
                key={col.key}
                style={{
                  padding: "10px 14px",
                  fontSize: "11px",
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "var(--tracking-wider)",
                  color: "var(--color-text-muted)",
                  textAlign: col.align || "left",
                  width: col.width,
                  whiteSpace: "nowrap",
                }}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                style={{
                  padding: "var(--space-8) var(--space-4)",
                  textAlign: "center",
                  color: "var(--color-text-muted)",
                  fontSize: "13px",
                }}
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((item, index) => (
              <tr
                key={keyExtractor(item, index)}
                onClick={() => onRowClick?.(item)}
                style={{
                  borderBottom: "1px solid var(--color-border-subtle)",
                  cursor: onRowClick ? "pointer" : "default",
                  transition: "background-color var(--transition-fast)",
                }}
                onMouseEnter={(e) => {
                  if (onRowClick) {
                    e.currentTarget.style.backgroundColor = "var(--color-surface-hover)";
                  }
                }}
                onMouseLeave={(e) => {
                  if (onRowClick) {
                    e.currentTarget.style.backgroundColor = "transparent";
                  }
                }}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    style={{
                      padding: "10px 14px",
                      textAlign: col.align || "left",
                      color: "var(--color-text-primary)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {col.render ? col.render(item, index) : (item as Record<string, unknown>)[col.key] as React.ReactNode}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
