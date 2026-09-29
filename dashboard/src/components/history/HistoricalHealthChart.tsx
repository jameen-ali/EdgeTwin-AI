import React, { useState, useMemo } from "react";
import { HistoricalHealthPoint } from "../../types/history";
import { formatNumber } from "../../utils/formatters";
import { EmptyState } from "../common/EmptyState";
import { Activity } from "lucide-react";

export interface HistoricalHealthChartProps {
  data: HistoricalHealthPoint[];
  height?: number;
  isDownsampled?: boolean;
  downsampleIntervalS?: number | null;
}

export const HistoricalHealthChart: React.FC<HistoricalHealthChartProps> = ({
  data,
  height = 240,
  isDownsampled = false,
  downsampleIntervalS,
}) => {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const svgWidth = 800;
  const svgHeight = height;
  const margin = { top: 20, right: 30, bottom: 35, left: 55 };
  const innerWidth = svgWidth - margin.left - margin.right;
  const innerHeight = svgHeight - margin.top - margin.bottom;

  // Domain for Health Score is fixed 0 to 100 with standard industrial thresholds
  const yTicks = [0, 25, 50, 60, 75, 80, 100];

  const getY = (val: number) => {
    const ratio = Math.max(0, Math.min(100, val)) / 100;
    return margin.top + innerHeight - ratio * innerHeight;
  };

  const getX = (index: number) => {
    if (data.length <= 1) return margin.left + innerWidth / 2;
    return margin.left + (index / (data.length - 1)) * innerWidth;
  };

  const linePath = useMemo(() => {
    if (data.length === 0) return "";
    let path = "";
    for (let i = 0; i < data.length; i++) {
      const x = getX(i);
      const y = getY(data[i].health_score);
      if (i === 0) {
        path += `M ${x.toFixed(1)} ${y.toFixed(1)}`;
      } else {
        path += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
      }
    }
    return path;
  }, [data]);

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
          icon={<Activity size={32} />}
          title="No Historical Health Data"
          description="No health score observations or digital twin snapshots are recorded for this machine in the selected window."
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
            <span
              style={{
                fontSize: "14px",
                fontWeight: 600,
                color: "var(--color-text-primary)",
              }}
            >
              Machine Health Trend
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
          <p style={{ margin: "2px 0 0 0", fontSize: "12px", color: "var(--color-text-muted)" }}>
            Composite multi-layer health score progression (0–100)
          </p>
        </div>

        {/* Legend */}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)", fontSize: "11px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "var(--color-success)" }} />
            <span style={{ color: "var(--color-text-muted)" }}>Healthy (≥80)</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "var(--color-warning)" }} />
            <span style={{ color: "var(--color-text-muted)" }}>Warning (60–79)</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "var(--color-danger)" }} />
            <span style={{ color: "var(--color-text-muted)" }}>Critical (&lt;60)</span>
          </div>
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
            <linearGradient id="healthAreaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#13EF95" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#13EF95" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Threshold Zone Guides */}
          {/* 80 Line - Warning Boundary */}
          <line
            x1={margin.left}
            y1={getY(80)}
            x2={margin.left + innerWidth}
            y2={getY(80)}
            stroke="var(--color-warning)"
            strokeDasharray="4 4"
            strokeWidth={1}
            strokeOpacity={0.6}
          />
          {/* 60 Line - Critical Boundary */}
          <line
            x1={margin.left}
            y1={getY(60)}
            x2={margin.left + innerWidth}
            y2={getY(60)}
            stroke="var(--color-danger)"
            strokeDasharray="4 4"
            strokeWidth={1}
            strokeOpacity={0.6}
          />

          {/* Horizontal Grid lines */}
          {yTicks.map((tick) => (
            <g key={tick}>
              <line
                x1={margin.left}
                y1={getY(tick)}
                x2={margin.left + innerWidth}
                y2={getY(tick)}
                stroke="var(--color-border)"
                strokeDasharray={tick === 0 || tick === 100 ? "none" : "2 4"}
                strokeWidth={1}
                strokeOpacity={0.4}
              />
              <text
                x={margin.left - 8}
                y={getY(tick) + 3}
                fill={tick === 80 ? "var(--color-warning)" : tick === 60 ? "var(--color-danger)" : "var(--color-text-muted)"}
                fontSize={10}
                fontFamily="var(--font-mono)"
                textAnchor="end"
              >
                {tick}
              </text>
            </g>
          ))}

          {/* Area Fill */}
          <path d={areaPath} fill="url(#healthAreaGrad)" />

          {/* Health Trend Line */}
          <path
            d={linePath}
            fill="none"
            stroke="var(--color-success)"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Hover Crosshair & Point Indicator */}
          {hoverIndex !== null && data[hoverIndex] && (
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
                cy={getY(data[hoverIndex].health_score)}
                r={5}
                fill="var(--color-canvas)"
                stroke="var(--color-success)"
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

        {/* Floating Tooltip Card */}
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
            <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", marginBottom: "2px" }}>
              <span style={{ color: "var(--color-text-secondary)" }}>Health:</span>
              <span
                style={{
                  fontWeight: 700,
                  color:
                    currentHoverPoint.health_score >= 80
                      ? "var(--color-success)"
                      : currentHoverPoint.health_score >= 60
                      ? "var(--color-warning)"
                      : "var(--color-danger)",
                }}
              >
                {formatNumber(currentHoverPoint.health_score, 1)} / 100
              </span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", marginBottom: "2px" }}>
              <span style={{ color: "var(--color-text-secondary)" }}>State:</span>
              <span style={{ color: "var(--color-text-primary)", fontWeight: 600 }}>
                {currentHoverPoint.health_state} ({currentHoverPoint.operating_state})
              </span>
            </div>
            {currentHoverPoint.failure_probability !== null && (
              <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
                <span style={{ color: "var(--color-text-secondary)" }}>Risk p(fail):</span>
                <span style={{ color: "var(--color-accent)", fontWeight: 600 }}>
                  {(currentHoverPoint.failure_probability * 100).toFixed(1)}%
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
