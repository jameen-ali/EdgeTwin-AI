import React from "react";
import {
  Thermometer,
  Activity,
  RotateCw,
  Gauge,
  Zap,
  Clock,
  Wrench,
  Compass,
} from "lucide-react";
import { MetricGrid } from "../common/MetricGrid";
import { Metric } from "../common/Metric";
import { Card } from "../common/Card";
import { formatNumber } from "../../utils/formatters";

export interface TelemetrySignals {
  process_temp_c?: number | null;
  air_temp_c?: number | null;
  vibration_mm_s?: number | null;
  rotational_speed_rpm?: number | null;
  torque_nm?: number | null;
  current_a?: number | null;
  pressure_bar?: number | null;
  voltage_v?: number | null;
  tool_wear_min?: number | null;
  operating_hours?: number | null;
  delta_t_c?: number | null;
  power_va?: number | null;
}

export interface TelemetryMetricGridProps {
  signals?: TelemetrySignals | null;
}

export const TelemetryMetricGrid: React.FC<TelemetryMetricGridProps> = ({ signals }) => {
  const formatVal = (val: number | null | undefined, decimals = 1): string => {
    if (val === null || val === undefined || isNaN(val)) {
      return "—";
    }
    return formatNumber(val, decimals);
  };

  const getStatus = (
    val: number | null | undefined,
    warnThreshold?: number,
    dangerThreshold?: number
  ): "normal" | "warning" | "danger" => {
    if (val === null || val === undefined || isNaN(val)) return "normal";
    if (dangerThreshold !== undefined && val >= dangerThreshold) return "danger";
    if (warnThreshold !== undefined && val >= warnThreshold) return "warning";
    return "normal";
  };

  return (
    <Card
      title="Current Sensor Telemetry"
      subtitle="Operational sensor readings from edge ingestion stream"
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
        {/* Priority 5 Signals */}
        <div>
          <span
            style={{
              fontSize: "11px",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "var(--tracking-wider)",
              color: "var(--color-text-muted)",
              marginBottom: "var(--space-2)",
              display: "block",
            }}
          >
            Core Operational Signals
          </span>
          <MetricGrid columns={4}>
            {/* 1. Process Temperature */}
            <Metric
              label="Process Temp"
              value={formatVal(signals?.process_temp_c, 1)}
              unit="°C"
              status={getStatus(signals?.process_temp_c, 60, 75)}
              icon={<Thermometer size={14} />}
              delta={
                signals?.air_temp_c !== null && signals?.air_temp_c !== undefined
                  ? {
                      value: `Air: ${formatVal(signals?.air_temp_c, 1)} °C`,
                      isPositive: true,
                    }
                  : undefined
              }
            />

            {/* 2. Vibration RMS */}
            <Metric
              label="Vibration RMS"
              value={formatVal(signals?.vibration_mm_s, 2)}
              unit="mm/s"
              status={getStatus(signals?.vibration_mm_s, 4.5, 7.0)}
              icon={<Activity size={14} />}
              delta={
                signals?.vibration_mm_s !== null &&
                signals?.vibration_mm_s !== undefined &&
                signals.vibration_mm_s > 4.5
                  ? {
                      value: "Above ISO Limit",
                      isPositive: false,
                    }
                  : undefined
              }
            />

            {/* 3. Rotational Speed */}
            <Metric
              label="Speed"
              value={formatVal(signals?.rotational_speed_rpm, 0)}
              unit="RPM"
              status={getStatus(signals?.rotational_speed_rpm, 2800, 3200)}
              icon={<RotateCw size={14} />}
            />

            {/* 4. Shaft Torque */}
            <Metric
              label="Shaft Torque"
              value={formatVal(signals?.torque_nm, 1)}
              unit="Nm"
              status={getStatus(signals?.torque_nm, 65, 80)}
              icon={<Gauge size={14} />}
            />

            {/* 5. Electrical Current */}
            <Metric
              label="Current"
              value={formatVal(signals?.current_a, 2)}
              unit="A"
              status={getStatus(signals?.current_a, 25, 35)}
              icon={<Zap size={14} />}
            />

            {/* Secondary Signals */}
            {/* 6. Pressure */}
            <Metric
              label="Pressure"
              value={formatVal(signals?.pressure_bar, 2)}
              unit="bar"
              icon={<Compass size={14} />}
            />

            {/* 7. Supply Voltage */}
            <Metric
              label="Supply Voltage"
              value={formatVal(signals?.voltage_v, 1)}
              unit="V"
              icon={<Zap size={14} />}
            />

            {/* 8. Cumulative Tool Wear */}
            <Metric
              label="Tool Wear"
              value={formatVal(signals?.tool_wear_min, 0)}
              unit="min"
              status={getStatus(signals?.tool_wear_min, 180, 240)}
              icon={<Wrench size={14} />}
            />

            {/* 9. Operating Hours */}
            <Metric
              label="Operating Time"
              value={formatVal(signals?.operating_hours, 1)}
              unit="hrs"
              icon={<Clock size={14} />}
            />
          </MetricGrid>
        </div>
      </div>
    </Card>
  );
};
