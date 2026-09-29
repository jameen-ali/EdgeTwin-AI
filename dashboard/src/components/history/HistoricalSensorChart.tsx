import React, { useState, useMemo } from "react";
import { HistoricalSensorPoint } from "../../types/history";
import { formatNumber } from "../../utils/formatters";
import { EmptyState } from "../common/EmptyState";
import { Gauge } from "lucide-react";

export type SensorMetricKey =
  | "process_temp_c"
  | "vibration_mm_s"
  | "rotational_speed_rpm"
  | "torque_nm"
  | "pressure_bar"
  | "current_a"
  | "voltage_v"
  | "tool_wear_min";

interface MetricConfig {
  key: SensorMetricKey;
  label: string;
  unit: string;
  color: string;
  threshold?: {
    value: number;
    label: string;
  };
}

const METRIC_CONFIGS: MetricConfig[] = [
  {
    key: "process_temp_c",
    label: "Process Temperature",
    unit: "°C",
    color: "#EF4444",
    threshold: { value: 60.0, label: "Limit 60°C" },
  },
  {
    key: "vibration_mm_s",
    label: "Vibration RMS",
    unit: "mm/s",
    color: "#FE750E",
    threshold: { value: 4.5, label: "ISO 20816 Zone C" },
  },
  {
    key: "rotational_speed_rpm",
    label: "Rotational Speed",
    unit: "RPM",
    color: "#149AFB",
  },
  {
    key: "torque_nm",
    label: "Shaft Torque",
    unit: "Nm",
    color: "#8C9AC4",
  },
  {
    key: "pressure_bar",
    label: "Hydraulic Pressure",
    unit: "bar",
    color: "#13EF95",
  },
  {
    key: "current_a",
    label: "Phase Current",
    unit: "A",
    color: "#F59E0B",
    threshold: { value: 18.0, label: "Rated 18A" },
  },
  {
    key: "voltage_v",
    label: "Supply Voltage",
    unit: "V",
    color: "#60A5FA",
  },
  {
    key: "tool_wear_min",
    label: "Tool Wear",
    unit: "min",
    color: "#A78BFA",
  },
];

export interface HistoricalSensorChartProps {
  data: HistoricalSensorPoint[];
  height?: number;
  isDownsampled?: boolean;
  downsampleIntervalS?: number | null;
}

export const HistoricalSensorChart: React.FC<HistoricalSensorChartProps> = ({
  data,
  height = 240,
  isDownsampled = false,
  downsampleIntervalS,
}) => {
  const [selectedMetric, setSelectedMetric] = useState<SensorMetricKey>("process_temp_c");
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const activeConfig = useMemo(
    () => METRIC_CONFIGS.find((m) => m.key === selectedMetric) || METRIC_CONFIGS[0],
    [selectedMetric]
  );

  const svgWidth = 800;
  const svgHeight = height;
  const margin = { top: 20, right: 30, bottom: 35, left: 55 };
  const innerWidth = svgWidth - margin.left - margin.right;
  const innerHeight = svgHeight - margin.top - margin.bottom;

  // Extract non-null values for the active metric
  const validValues = useMemo(() => {
    return data
      .map((d) => d[selectedMetric])
      .filter((v): v is number => typeof v === "number" && !isNaN(v));
  }, [data, selectedMetric]);

  const summary = useMemo(() => {
    if (validValues.length === 0) return { min: null, avg: null, max: null };
    const min = Math.min(...validValues);
    const max = Math.max(...validValues);
    const avg = validValues.reduce((acc, v) => acc + v, 0) / validValues.length;
    return { min, avg, max };
  }, [validValues]);

  // Compute dynamic domain
  const { minY, maxY, yTicks } = useMemo(() => {
    if (validValues.length === 0) {
      return { minY: 0, maxY: 100, yTicks: [0, 25, 50, 75, 100] };
    }
    let min = Math.min(...validValues);
    let max = Math.max(...validValues);

    if (activeConfig.threshold) {
      if (activeConfig.threshold.value > max) max = activeConfig.threshold.value;
      if (activeConfig.threshold.value < min) min = activeConfig.threshold.value;
    }

    const span = max - min || 1;
    const paddedMin = Math.floor(min - span * 0.1);
    const paddedMax = Math.ceil(max + span * 0.1);

    const step = (paddedMax - paddedMin) / 4;
    const ticks = [
      paddedMin,
      paddedMin + step,
      paddedMin + step * 2,
      paddedMin + step * 3,
      paddedMax,
    ];

    return { minY: paddedMin, maxY: paddedMax, yTicks: ticks };
  }, [validValues, activeConfig]);

  const getY = (val: number) => {
    if (maxY === minY) return margin.top + innerHeight / 2;
    const ratio = (val - minY) / (maxY - minY);
    return margin.top + innerHeight - ratio * innerHeight;
  };

  const getX = (index: number) => {
    if (data.length <= 1) return margin.left + innerWidth / 2;
    return margin.left + (index / (data.length - 1)) * innerWidth;
  };

  const linePath = useMemo(() => {
    if (data.length === 0) return "";
    let path = "";
    let inSegment = false;

    for (let i = 0; i < data.length; i++) {
      const val = data[i][selectedMetric];
      if (typeof val === "number" && !isNaN(val)) {
        const x = getX(i);
        const y = getY(val);
        if (!inSegment) {
          path += `M ${x.toFixed(1)} ${y.toFixed(1)}`;
          inSegment = true;
        } else {
          path += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
        }
      } else {
        inSegment = false;
      }
    }
    return path;
  }, [data, selectedMetric, minY, maxY]);

  const areaPath = useMemo(() => {
    if (!linePath || data.length === 0) return "";
    const firstX = getX(0);
    const lastX = getX(data.length - 1);
    const baseY = margin.top + innerHeight;
    return `${linePath} L ${lastX.toFixed(1)} ${baseY} L ${firstX.toFixed(1)} ${baseY} Z`;
  }, [linePath, data]);

  const formatTimeTick = (iso: string) => {
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) return "";
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
    } catch {
      return "";
    }
  };

  const currentHoverPoint = hoverIndex !== null && data[hoverIndex] ? data[hoverIndex] : null;
  const currentHoverVal = currentHoverPoint ? currentHoverPoint[selectedMetric] : null;

  if (data.length === 0) {
    return (
      <div
        style={{
          backgroundColor: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-lg)",
          padding: "var(--space-6)",
        }}
      >
        <EmptyState
          icon={<Gauge size={32} />}
          title="No Historical Sensor Telemetry"
          description="No physical telemetry observations were reported for this machine in the selected window."
        />
      </div>
    );
  }

  return (
    <div
      style={{
        backgroundColor: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--space-4) var(--space-5)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-3)",
        position: "relative",
      }}
    >
      {/* Chart Header & Controls */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: "var(--space-3)",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            <span
              style={{
                fontSize: "14px",
                fontWeight: 600,
                color: "var(--color-text-primary)",
              }}
            >
              Sensor Telemetry History
            </span>
            {isDownsampled && (
              <span
                style={{
                  fontSize: "11px",
                  padding: "1px 6px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: "rgba(140, 154, 196, 0.15)",
                  color: "var(--color-accent)",
                  border: "1px solid var(--color-accent-border)",
                  fontFamily: "var(--font-mono)",
                }}
              >
                Downsampled {downsampleIntervalS ? `(${downsampleIntervalS}s bins)` : ""}
              </span>
            )}
          </div>
          {summary.avg !== null && (
            <div
              style={{
                display: "flex",
                gap: "var(--space-3)",
                fontSize: "11px",
                fontFamily: "var(--font-mono)",
                color: "var(--color-text-muted)",
                marginTop: "2px",
              }}
            >
              <span>Min: <strong style={{ color: "var(--color-text-primary)" }}>{formatNumber(summary.min, 2)} {activeConfig.unit}</strong></span>
              <span>Avg: <strong style={{ color: "var(--color-text-primary)" }}>{formatNumber(summary.avg, 2)} {activeConfig.unit}</strong></span>
              <span>Max: <strong style={{ color: "var(--color-text-primary)" }}>{formatNumber(summary.max, 2)} {activeConfig.unit}</strong></span>
            </div>
          )}
        </div>

        {/* Metric Selector Pills */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
          {METRIC_CONFIGS.map((m) => {
            const isSelected = m.key === selectedMetric;
            return (
              <button
                key={m.key}
                type="button"
                onClick={() => setSelectedMetric(m.key)}
                style={{
                  padding: "4px 8px",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "11px",
                  fontWeight: isSelected ? 600 : 400,
                  border: isSelected
                    ? `1px solid ${m.color}`
                    : "1px solid var(--color-border)",
                  backgroundColor: isSelected
                    ? "rgba(20, 154, 251, 0.12)"
                    : "transparent",
                  color: isSelected ? "var(--color-text-primary)" : "var(--color-text-muted)",
                  cursor: "pointer",
                  transition: "all var(--transition-fast)",
                }}
              >
                {m.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* SVG Canvas */}
      <div style={{ width: "100%", height: `${height}px`, position: "relative" }}>
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          preserveAspectRatio="none"
          style={{ width: "100%", height: "100%", overflow: "visible" }}
          onMouseLeave={() => setHoverIndex(null)}
        >
          <defs>
            <linearGradient id={`sensorGrad_${selectedMetric}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={activeConfig.color} stopOpacity="0.25" />
              <stop offset="100%" stopColor={activeConfig.color} stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Threshold Line if defined */}
          {activeConfig.threshold && (
            <g>
              <line
                x1={margin.left}
                y1={getY(activeConfig.threshold.value)}
                x2={margin.left + innerWidth}
                y2={getY(activeConfig.threshold.value)}
                stroke={activeConfig.color}
                strokeDasharray="4 4"
                strokeWidth={1}
                strokeOpacity={0.7}
              />
              <text
                x={margin.left + innerWidth - 5}
                y={getY(activeConfig.threshold.value) - 4}
                fill={activeConfig.color}
                fontSize={10}
                fontFamily="var(--font-mono)"
                textAnchor="end"
              >
                {activeConfig.threshold.label}
              </text>
            </g>
          )}

          {/* Grid lines and Y axis ticks */}
          {yTicks.map((tick) => (
            <g key={tick}>
              <line
                x1={margin.left}
                y1={getY(tick)}
                x2={margin.left + innerWidth}
                y2={getY(tick)}
                stroke="var(--color-border)"
                strokeDasharray="2 4"
                strokeWidth={1}
                strokeOpacity={0.4}
              />
              <text
                x={margin.left - 8}
                y={getY(tick) + 3}
                fill="var(--color-text-muted)"
                fontSize={10}
                fontFamily="var(--font-mono)"
                textAnchor="end"
              >
                {formatNumber(tick, 1)}
              </text>
            </g>
          ))}

          {/* Area Fill */}
          <path d={areaPath} fill={`url(#sensorGrad_${selectedMetric})`} />

          {/* Line Path */}
          <path
            d={linePath}
            fill="none"
            stroke={activeConfig.color}
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Hover Crosshair */}
          {hoverIndex !== null && currentHoverVal !== null && typeof currentHoverVal === "number" && (
            <g>
              <line
                x1={getX(hoverIndex)}
                y1={margin.top}
                x2={getX(hoverIndex)}
                y2={margin.top + innerHeight}
                stroke="var(--color-accent)"
                strokeDasharray="3 3"
                strokeWidth={1}
              />
              <circle
                cx={getX(hoverIndex)}
                cy={getY(currentHoverVal)}
                r={5}
                fill="var(--color-canvas)"
                stroke={activeConfig.color}
                strokeWidth={2}
              />
            </g>
          )}

          {/* Transparent Hover Hit Areas */}
          {data.map((_, idx) => {
            const x = getX(idx);
            const w = innerWidth / Math.max(1, data.length - 1);
            return (
              <rect
                key={idx}
                x={x - w / 2}
                y={margin.top}
                width={w}
                height={innerHeight}
                fill="transparent"
                style={{ cursor: "crosshair" }}
                onMouseEnter={() => setHoverIndex(idx)}
              />
            );
          })}

          {/* X Axis Time Ticks */}
          {data.length > 0 && (
            <g>
              <text
                x={margin.left}
                y={margin.top + innerHeight + 18}
                fill="var(--color-text-muted)"
                fontSize={10}
                fontFamily="var(--font-mono)"
                textAnchor="start"
              >
                {formatTimeTick(data[0].ts)}
              </text>
              {data.length > 2 && (
                <text
                  x={margin.left + innerWidth / 2}
                  y={margin.top + innerHeight + 18}
                  fill="var(--color-text-muted)"
                  fontSize={10}
                  fontFamily="var(--font-mono)"
                  textAnchor="middle"
                >
                  {formatTimeTick(data[Math.floor(data.length / 2)].ts)}
                </text>
              )}
              <text
                x={margin.left + innerWidth}
                y={margin.top + innerHeight + 18}
                fill="var(--color-text-muted)"
                fontSize={10}
                fontFamily="var(--font-mono)"
                textAnchor="end"
              >
                {formatTimeTick(data[data.length - 1].ts)}
              </text>
            </g>
          )}
        </svg>

        {/* Tooltip Card */}
        {currentHoverPoint && hoverIndex !== null && (
          <div
            style={{
              position: "absolute",
              left: `${Math.min(80, Math.max(15, (getX(hoverIndex) / svgWidth) * 100))}%`,
              top: "10px",
              pointerEvents: "none",
              backgroundColor: "var(--color-canvas)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              padding: "var(--space-2) var(--space-3)",
              boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
              zIndex: 10,
              fontSize: "11px",
              fontFamily: "var(--font-mono)",
            }}
          >
            <div style={{ color: "var(--color-text-muted)", marginBottom: "4px" }}>
              {new Date(currentHoverPoint.ts).toLocaleString([], {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })}
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
              <span style={{ color: "var(--color-text-secondary)" }}>{activeConfig.label}:</span>
              <span style={{ fontWeight: 700, color: activeConfig.color }}>
                {typeof currentHoverVal === "number"
                  ? `${formatNumber(currentHoverVal, 2)} ${activeConfig.unit}`
                  : "—"}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
