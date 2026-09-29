import React, { useState, useMemo } from "react";
import { TelemetryPoint } from "../../types/machine";
import { formatNumber } from "../../utils/formatters";

export interface ChartSeries {
  key: keyof TelemetryPoint;
  name: string;
  color: string;
  unit?: string;
  threshold?: {
    value: number;
    label: string;
    color?: string;
  };
}

export interface TelemetryChartProps {
  title: string;
  subtitle?: string;
  unit: string;
  series: ChartSeries[];
  data: TelemetryPoint[];
  height?: number;
  timeWindowLabel?: string;
  emptyMessage?: string;
}

export const TelemetryChart: React.FC<TelemetryChartProps> = ({
  title,
  subtitle,
  unit,
  series,
  data,
  height = 220,
  timeWindowLabel,
  emptyMessage = "No telemetry observations recorded.",
}) => {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  // SVG coordinate bounds
  const svgWidth = 800;
  const svgHeight = height;
  const margin = { top: 20, right: 30, bottom: 35, left: 60 };
  const innerWidth = svgWidth - margin.left - margin.right;
  const innerHeight = svgHeight - margin.top - margin.bottom;

  // Calculate Y-axis domain across all series
  const { minY, maxY, yTicks } = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;

    for (const point of data) {
      for (const s of series) {
        const val = point[s.key];
        if (typeof val === "number" && !isNaN(val)) {
          if (val < min) min = val;
          if (val > max) max = val;
        }
        if (s.threshold) {
          if (s.threshold.value < min) min = s.threshold.value;
          if (s.threshold.value > max) max = s.threshold.value;
        }
      }
    }

    if (min === Infinity || max === -Infinity) {
      return { minY: 0, maxY: 100, yTicks: [0, 25, 50, 75, 100] };
    }

    // Add padding (at least 5% top and bottom)
    const range = max - min || 1;
    const paddedMin = Math.floor(min - range * 0.1);
    const paddedMax = Math.ceil(max + range * 0.1);

    const step = (paddedMax - paddedMin) / 4;
    const ticks = [
      paddedMin,
      paddedMin + step,
      paddedMin + step * 2,
      paddedMin + step * 3,
      paddedMax,
    ];

    return { minY: paddedMin, maxY: paddedMax, yTicks: ticks };
  }, [data, series]);

  // Coordinate mapping functions
  const getY = (val: number) => {
    if (maxY === minY) return innerHeight / 2 + margin.top;
    const ratio = (val - minY) / (maxY - minY);
    return margin.top + innerHeight - ratio * innerHeight;
  };

  const getX = (index: number) => {
    if (data.length <= 1) return margin.left + innerWidth / 2;
    return margin.left + (index / (data.length - 1)) * innerWidth;
  };

  // Generate SVG path for a series handling gaps for nulls
  const getSeriesPath = (s: ChartSeries) => {
    let path = "";
    let inSegment = false;

    for (let i = 0; i < data.length; i++) {
      const val = data[i][s.key];
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
  };

  // Area path for primary series
  const getAreaPath = (s: ChartSeries) => {
    const linePath = getSeriesPath(s);
    if (!linePath || data.length === 0) return "";
    const firstX = getX(0);
    const lastX = getX(data.length - 1);
    const baseY = margin.top + innerHeight;
    return `${linePath} L ${lastX.toFixed(1)} ${baseY} L ${firstX.toFixed(1)} ${baseY} Z`;
  };

  // Format time label for X-axis
  const formatTimeTick = (iso: string) => {
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) return "";
      return d.toLocaleTimeString("en-US", {
        hour12: false,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return "";
    }
  };

  // Determine latest non-null values for series header
  const latestValues = useMemo(() => {
    const map: Record<string, number | null> = {};
    for (const s of series) {
      let val: number | null = null;
      for (let i = data.length - 1; i >= 0; i--) {
        const v = data[i][s.key];
        if (typeof v === "number" && !isNaN(v)) {
          val = v;
          break;
        }
      }
      map[String(s.key)] = val;
    }
    return map;
  }, [data, series]);

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
      {/* Chart Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: "var(--space-2)",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            <h4
              style={{
                fontSize: "13px",
                fontWeight: 600,
                color: "var(--color-text-primary)",
                letterSpacing: "var(--tracking-tight)",
                margin: 0,
              }}
            >
              {title}
            </h4>
            <span
              style={{
                fontSize: "11px",
                fontWeight: 500,
                color: "var(--color-text-muted)",
              }}
            >
              ({unit})
            </span>
          </div>
          {subtitle && (
            <p
              style={{
                fontSize: "11px",
                color: "var(--color-text-muted)",
                margin: "2px 0 0 0",
              }}
            >
              {subtitle}
            </p>
          )}
        </div>

        {/* Legend & Latest Values */}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)", flexWrap: "wrap" }}>
          {series.map((s) => {
            const current = latestValues[String(s.key)];
            return (
              <div
                key={String(s.key)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  fontSize: "11px",
                }}
              >
                <span
                  style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "2px",
                    backgroundColor: s.color,
                    display: "inline-block",
                  }}
                />
                <span style={{ color: "var(--color-text-secondary)" }}>{s.name}:</span>
                <span
                  className="text-mono"
                  style={{
                    fontWeight: 700,
                    color: current !== null ? "var(--color-text-primary)" : "var(--color-text-muted)",
                  }}
                >
                  {current !== null ? `${formatNumber(current, 1)} ${s.unit || unit}` : "—"}
                </span>
              </div>
            );
          })}
          {timeWindowLabel && (
            <span
              className="text-mono"
              style={{
                fontSize: "10px",
                color: "var(--color-text-muted)",
                paddingLeft: "var(--space-2)",
                borderLeft: "1px solid var(--color-border-subtle)",
              }}
            >
              {timeWindowLabel}
            </span>
          )}
        </div>
      </div>

      {/* SVG Canvas */}
      {data.length === 0 ? (
        <div
          style={{
            height: `${height}px`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "var(--color-surface-input)",
            borderRadius: "var(--radius-md)",
            border: "1px dashed var(--color-border)",
            color: "var(--color-text-muted)",
            fontSize: "12px",
          }}
        >
          {emptyMessage}
        </div>
      ) : (
        <div style={{ position: "relative", width: "100%", overflow: "hidden" }}>
          <svg
            viewBox={`0 0 ${svgWidth} ${svgHeight}`}
            style={{ width: "100%", height: "auto", display: "block" }}
            onMouseLeave={() => setHoverIndex(null)}
            onMouseMove={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const mouseX = ((e.clientX - rect.left) / rect.width) * svgWidth;
              if (mouseX >= margin.left && mouseX <= margin.left + innerWidth) {
                const fraction = (mouseX - margin.left) / innerWidth;
                const idx = Math.min(data.length - 1, Math.max(0, Math.round(fraction * (data.length - 1))));
                setHoverIndex(idx);
              } else {
                setHoverIndex(null);
              }
            }}
          >
            <defs>
              {series.map((s, idx) => (
                <linearGradient
                  key={String(s.key)}
                  id={`area-grad-${idx}`}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop offset="0%" stopColor={s.color} stopOpacity="0.25" />
                  <stop offset="100%" stopColor={s.color} stopOpacity="0.0" />
                </linearGradient>
              ))}
            </defs>

            {/* Horizontal Gridlines & Y-Axis Ticks */}
            {yTicks.map((tick, i) => {
              const y = getY(tick);
              return (
                <g key={i}>
                  <line
                    x1={margin.left}
                    y1={y}
                    x2={margin.left + innerWidth}
                    y2={y}
                    stroke="var(--color-border-subtle)"
                    strokeWidth="1"
                    strokeDasharray="2 4"
                  />
                  <text
                    x={margin.left - 8}
                    y={y + 3}
                    textAnchor="end"
                    fill="var(--color-text-muted)"
                    fontSize="10"
                    fontFamily="var(--font-mono)"
                  >
                    {formatNumber(tick, 0)}
                  </text>
                </g>
              );
            })}

            {/* Threshold Line if provided */}
            {series.map(
              (s) =>
                s.threshold && (
                  <g key={`thresh-${String(s.key)}`}>
                    <line
                      x1={margin.left}
                      y1={getY(s.threshold.value)}
                      x2={margin.left + innerWidth}
                      y2={getY(s.threshold.value)}
                      stroke={s.threshold.color || "var(--color-warning)"}
                      strokeWidth="1.5"
                      strokeDasharray="4 4"
                    />
                    <text
                      x={margin.left + innerWidth - 6}
                      y={getY(s.threshold.value) - 4}
                      textAnchor="end"
                      fill={s.threshold.color || "var(--color-warning)"}
                      fontSize="9"
                      fontWeight="600"
                      fontFamily="var(--font-mono)"
                    >
                      {s.threshold.label} ({s.threshold.value} {unit})
                    </text>
                  </g>
                )
            )}

            {/* Series Area Gradients (rendered for first series) */}
            {series.slice(0, 1).map((s, idx) => (
              <path
                key={`area-${String(s.key)}`}
                d={getAreaPath(s)}
                fill={`url(#area-grad-${idx})`}
              />
            ))}

            {/* Series Lines */}
            {series.map((s) => (
              <path
                key={`line-${String(s.key)}`}
                d={getSeriesPath(s)}
                fill="none"
                stroke={s.color}
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            ))}

            {/* Latest Live Point Pulse on each series */}
            {data.length > 0 &&
              series.map((s) => {
                const lastIdx = data.length - 1;
                const lastVal = data[lastIdx][s.key];
                if (typeof lastVal !== "number" || isNaN(lastVal)) return null;
                const cx = getX(lastIdx);
                const cy = getY(lastVal);
                return (
                  <g key={`live-pt-${String(s.key)}`}>
                    <circle
                      cx={cx}
                      cy={cy}
                      r="6"
                      fill={s.color}
                      opacity="0.3"
                      className="live-pulse-dot"
                    />
                    <circle cx={cx} cy={cy} r="3.5" fill={s.color} />
                  </g>
                );
              })}

            {/* X-Axis Time Ticks */}
            {data.length > 1 &&
              [0, Math.floor(data.length / 2), data.length - 1].map((idx) => {
                const x = getX(idx);
                const timeStr = formatTimeTick(data[idx].ts);
                const anchor = idx === 0 ? "start" : idx === data.length - 1 ? "end" : "middle";
                return (
                  <text
                    key={`time-${idx}`}
                    x={x}
                    y={margin.top + innerHeight + 18}
                    textAnchor={anchor}
                    fill="var(--color-text-muted)"
                    fontSize="10"
                    fontFamily="var(--font-mono)"
                  >
                    {timeStr}
                  </text>
                );
              })}

            {/* Hover Crosshair & Tooltip Overlay */}
            {hoverIndex !== null && data[hoverIndex] && (
              <g>
                <line
                  x1={getX(hoverIndex)}
                  y1={margin.top}
                  x2={getX(hoverIndex)}
                  y2={margin.top + innerHeight}
                  stroke="var(--color-border-hover)"
                  strokeWidth="1"
                  strokeDasharray="2 2"
                />
                {series.map((s) => {
                  const val = data[hoverIndex][s.key];
                  if (typeof val !== "number" || isNaN(val)) return null;
                  return (
                    <circle
                      key={`hover-pt-${String(s.key)}`}
                      cx={getX(hoverIndex)}
                      cy={getY(val)}
                      r="4"
                      fill="var(--color-canvas)"
                      stroke={s.color}
                      strokeWidth="2"
                    />
                  );
                })}
              </g>
            )}
          </svg>

          {/* Interactive Floating Tooltip */}
          {hoverIndex !== null && data[hoverIndex] && (
            <div
              style={{
                position: "absolute",
                top: "10px",
                left: `${Math.min(75, Math.max(15, (getX(hoverIndex) / svgWidth) * 100))}%`,
                transform: "translateX(-50%)",
                backgroundColor: "var(--color-surface-raised)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                padding: "6px 10px",
                pointerEvents: "none",
                boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
                zIndex: 10,
                fontSize: "11px",
              }}
            >
              <div
                className="text-mono"
                style={{
                  color: "var(--color-text-muted)",
                  fontSize: "10px",
                  marginBottom: "4px",
                  borderBottom: "1px solid var(--color-border-subtle)",
                  paddingBottom: "2px",
                }}
              >
                {data[hoverIndex].ts.slice(0, 19).replace("T", " ")} UTC
              </div>
              {series.map((s) => {
                const val = data[hoverIndex][s.key];
                return (
                  <div
                    key={`tip-${String(s.key)}`}
                    style={{ display: "flex", alignItems: "center", gap: "6px" }}
                  >
                    <span
                      style={{
                        width: "6px",
                        height: "6px",
                        borderRadius: "1px",
                        backgroundColor: s.color,
                      }}
                    />
                    <span style={{ color: "var(--color-text-secondary)" }}>{s.name}:</span>
                    <span className="text-mono" style={{ fontWeight: 700, color: "var(--color-text-primary)" }}>
                      {typeof val === "number" && !isNaN(val) ? `${formatNumber(val, 1)} ${s.unit || unit}` : "—"}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
