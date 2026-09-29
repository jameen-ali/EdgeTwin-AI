import React from "react";
import { DataTable, Column } from "../common/DataTable";
import { Card } from "../common/Card";
import { TelemetryPoint } from "../../types/machine";
import { formatNumber, formatDateTime } from "../../utils/formatters";

export interface RawTelemetryTableProps {
  telemetry: TelemetryPoint[];
  emptyMessage?: string;
}

export const RawTelemetryTable: React.FC<RawTelemetryTableProps> = ({
  telemetry,
  emptyMessage = "No telemetry records available for this machine.",
}) => {
  const formatCell = (val: number | null | undefined, decimals = 1): string => {
    if (val === null || val === undefined || isNaN(val)) return "—";
    return formatNumber(val, decimals);
  };

  const columns: Column<TelemetryPoint>[] = [
    {
      key: "seq",
      header: "Seq",
      width: "70px",
      render: (item) => (
        <span className="text-mono" style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
          {item.seq !== undefined ? `#${item.seq}` : "—"}
        </span>
      ),
    },
    {
      key: "ts",
      header: "Timestamp (UTC)",
      render: (item) => (
        <span className="text-mono" style={{ fontSize: "12px" }}>
          {formatDateTime(item.ts)}
        </span>
      ),
    },
    {
      key: "process_temp_c",
      header: "Process Temp (°C)",
      align: "right",
      render: (item) => (
        <span className="text-mono">{formatCell(item.process_temp_c, 1)}</span>
      ),
    },
    {
      key: "vibration_mm_s",
      header: "Vibration (mm/s)",
      align: "right",
      render: (item) => (
        <span
          className="text-mono"
          style={{
            color:
              item.vibration_mm_s && item.vibration_mm_s > 4.5
                ? "var(--color-warning)"
                : "inherit",
          }}
        >
          {formatCell(item.vibration_mm_s, 2)}
        </span>
      ),
    },
    {
      key: "rotational_speed_rpm",
      header: "Speed (RPM)",
      align: "right",
      render: (item) => (
        <span className="text-mono">{formatCell(item.rotational_speed_rpm, 0)}</span>
      ),
    },
    {
      key: "torque_nm",
      header: "Torque (Nm)",
      align: "right",
      render: (item) => (
        <span className="text-mono">{formatCell(item.torque_nm, 1)}</span>
      ),
    },
    {
      key: "current_a",
      header: "Current (A)",
      align: "right",
      render: (item) => (
        <span className="text-mono">{formatCell(item.current_a, 2)}</span>
      ),
    },
    {
      key: "trip",
      header: "Trip / Event",
      render: (item) => (
        item.trip ? (
          <span
            style={{
              fontSize: "11px",
              fontWeight: 600,
              padding: "2px 6px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--color-danger-subtle)",
              color: "var(--color-danger)",
              border: "1px solid var(--color-danger-border)",
            }}
          >
            {item.trip}
          </span>
        ) : (
          <span style={{ color: "var(--color-text-muted)" }}>—</span>
        )
      ),
    },
  ];

  return (
    <Card
      title="Recent Telemetry Records"
      subtitle={`Raw observations buffer (${telemetry.length} records)`}
      noPadding
    >
      <DataTable
        columns={columns}
        data={telemetry}
        keyExtractor={(item, index) => item.id ?? item.seq ?? `${item.ts}-${index}`}
        emptyMessage={emptyMessage}
      />
    </Card>
  );
};
