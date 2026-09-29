import React from "react";
import {
  Activity,
  Thermometer,
  RotateCw,
  Zap,
  Wrench,
  Compass,
  Lock,
} from "lucide-react";
import { Card } from "../common/Card";
import { StatusBadge } from "../common/StatusBadge";
import { HealthBadge } from "../common/HealthBadge";
import { LiveIndicator } from "../common/LiveIndicator";
import { ConnectionIndicator } from "../common/ConnectionIndicator";
import { OperatingState, HealthState, ConnectivityState } from "../../types/machine";
import { formatNumber } from "../../utils/formatters";

export interface DigitalTwinViewProps {
  machineId: string;
  machineType?: string;
  operatingState?: OperatingState | string;
  healthState?: HealthState | string;
  connectivityState?: ConnectivityState | string;
  healthScore?: number | null;
  signals?: Record<string, any> | null;
  quality?: Record<string, string> | null;
  edge?: Record<string, any> | null;
  isLiveWs?: boolean;
}

export const DigitalTwinView: React.FC<DigitalTwinViewProps> = ({
  machineId,
  machineType = "Industrial Induction Motor",
  operatingState = "UNKNOWN",
  healthState = "UNKNOWN",
  connectivityState = "OFFLINE",
  healthScore = null,
  signals,
  quality,
  edge,
  isLiveWs = false,
}) => {
  const normState = (operatingState || "").toUpperCase();
  const normConn = (connectivityState || "").toUpperCase();
  const isRunning = normState === "RUNNING";
  const isTripped = normState === "TRIPPED";
  const isDegrading = normState === "DEGRADING";
  const isStarting = normState === "STARTING";
  const isLive = normConn === "LIVE" || normConn === "ONLINE" || isLiveWs;
  const isStale = normConn === "STALE";

  // Health color
  let healthColor = "var(--color-success)";
  if (healthScore !== null) {
    if (healthScore < 60) healthColor = "var(--color-danger)";
    else if (healthScore < 80) healthColor = "var(--color-warning)";
  }

  // State schematic theme
  let casingStroke = "var(--color-border)";
  let casingFill = "var(--color-surface)";
  let accentGlow = "transparent";

  if (isTripped) {
    casingStroke = "var(--color-danger)";
    casingFill = "var(--color-danger-subtle)";
    accentGlow = "rgba(239, 68, 68, 0.25)";
  } else if (isDegrading) {
    casingStroke = "var(--color-warning)";
    casingFill = "var(--color-warning-subtle)";
    accentGlow = "rgba(254, 117, 14, 0.2)";
  } else if (isRunning) {
    casingStroke = "var(--color-accent)";
    accentGlow = "rgba(20, 154, 251, 0.2)";
  } else if (isStarting) {
    casingStroke = "var(--color-warning)";
    accentGlow = "rgba(254, 117, 14, 0.15)";
  }

  // Format sensor values
  const fmt = (val: number | null | undefined, decimals = 1): string => {
    if (val === null || val === undefined || isNaN(val)) return "—";
    return formatNumber(val, decimals);
  };

  // Quality badge helper
  const renderQualityTag = (sensorKey: string) => {
    const q = quality?.[sensorKey];
    if (!q || q === "OK") return null;

    let tagColor = "var(--color-warning)";
    let tagBg = "var(--color-warning-subtle)";
    let tagBorder = "var(--color-warning-border)";

    if (q === "LIMIT_ALARM" || q === "OUT_OF_RANGE") {
      tagColor = "var(--color-danger)";
      tagBg = "var(--color-danger-subtle)";
      tagBorder = "var(--color-danger-border)";
    }

    return (
      <span
        style={{
          fontSize: "9px",
          fontWeight: 700,
          padding: "1px 4px",
          borderRadius: "var(--radius-sm)",
          backgroundColor: tagBg,
          color: tagColor,
          border: `1px solid ${tagBorder}`,
          textTransform: "uppercase",
        }}
      >
        {q}
      </span>
    );
  };

  const accessibleLabel = `Digital Twin visualization for machine ${machineId}, equipment type ${machineType}, currently ${operatingState} and ${healthState} with health score ${
    healthScore !== null ? healthScore : "unavailable"
  }.`;

  return (
    <Card
      title="Digital Twin Model"
      subtitle={`${machineType} • Real-time operational schematic and telemetry mapping`}
      action={
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
          {isLiveWs ? (
            <LiveIndicator isLive={true} label="TWIN SYNCED" />
          ) : (
            <ConnectionIndicator
              status={isLive ? "ONLINE" : isStale ? "CONNECTING" : "OFFLINE"}
              label={normConn || "OFFLINE"}
            />
          )}
        </div>
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
        {/* Status Strip */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "var(--space-3)",
            padding: "var(--space-3) var(--space-4)",
            backgroundColor: "var(--color-surface-raised)",
            border: "1px solid var(--color-border-subtle)",
            borderRadius: "var(--radius-md)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            <span
              className="text-mono"
              style={{
                fontSize: "14px",
                fontWeight: 700,
                color: "var(--color-text-primary)",
              }}
            >
              {machineId}
            </span>
            <StatusBadge status={operatingState} size="sm" />
            <HealthBadge state={healthState} size="sm" />
          </div>

          {/* Health Index Ring */}
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
            <div style={{ textAlign: "right" }}>
              <div
                style={{
                  fontSize: "10px",
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "var(--tracking-wider)",
                  color: "var(--color-text-muted)",
                }}
              >
                Twin Health
              </div>
              <div className="text-mono" style={{ fontSize: "16px", fontWeight: 700, color: healthColor }}>
                {healthScore !== null ? `${formatNumber(healthScore, 1)}%` : "—"}
              </div>
            </div>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "50%",
                background: `conic-gradient(${healthColor} ${
                  healthScore !== null ? healthScore * 3.6 : 0
                }deg, var(--color-surface-input) 0deg)`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: "3px",
              }}
            >
              <div
                style={{
                  width: "100%",
                  height: "100%",
                  borderRadius: "50%",
                  backgroundColor: "var(--color-surface-raised)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Activity size={14} color={healthColor} />
              </div>
            </div>
          </div>
        </div>

        {/* SVG Schematic Canvas */}
        <div
          role="img"
          aria-label={accessibleLabel}
          style={{
            position: "relative",
            width: "100%",
            backgroundColor: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-md)",
            overflow: "hidden",
            padding: "var(--space-2)",
          }}
        >
          <svg
            viewBox="0 0 760 320"
            style={{ width: "100%", height: "auto", display: "block" }}
          >
            <defs>
              {/* Subtle radial glow for running/active state */}
              <radialGradient id="schematicGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor={accentGlow} />
                <stop offset="100%" stopColor="transparent" />
              </radialGradient>

              {/* Cooling fin pattern */}
              <pattern id="coolingFins" width="12" height="60" patternUnits="userSpaceOnUse">
                <line x1="0" y1="0" x2="0" y2="60" stroke="var(--color-border-subtle)" strokeWidth="2" />
                <line x1="6" y1="0" x2="6" y2="60" stroke="var(--color-surface-input)" strokeWidth="1" />
              </pattern>
            </defs>

            {/* Background Aura */}
            <circle cx="360" cy="160" r="140" fill="url(#schematicGlow)" />

            {/* Grid Backdrop Lines */}
            <g opacity="0.15">
              <line x1="40" y1="80" x2="720" y2="80" stroke="var(--color-border)" strokeDasharray="3 3" />
              <line x1="40" y1="160" x2="720" y2="160" stroke="var(--color-border)" strokeDasharray="3 3" />
              <line x1="40" y1="240" x2="720" y2="240" stroke="var(--color-border)" strokeDasharray="3 3" />
              <line x1="240" y1="30" x2="240" y2="290" stroke="var(--color-border)" strokeDasharray="3 3" />
              <line x1="480" y1="30" x2="480" y2="290" stroke="var(--color-border)" strokeDasharray="3 3" />
            </g>

            {/* 1. Base Mounting Plate */}
            <rect
              x="220"
              y="226"
              width="280"
              height="18"
              rx="3"
              fill="var(--color-surface-input)"
              stroke="var(--color-border)"
              strokeWidth="1.5"
            />
            {/* Mounting Bolts */}
            <circle cx="236" cy="235" r="3" fill="var(--color-text-muted)" />
            <circle cx="484" cy="235" r="3" fill="var(--color-text-muted)" />

            {/* 2. Rear Fan Cowl Housing (Left) */}
            <path
              d="M 230 110 L 260 100 L 260 220 L 230 210 Z"
              fill="var(--color-surface-raised)"
              stroke="var(--color-border)"
              strokeWidth="1.5"
            />
            {/* Fan Louvers */}
            <line x1="238" y1="125" x2="252" y2="125" stroke="var(--color-text-muted)" strokeWidth="1.5" />
            <line x1="238" y1="145" x2="252" y2="145" stroke="var(--color-text-muted)" strokeWidth="1.5" />
            <line x1="238" y1="165" x2="252" y2="165" stroke="var(--color-text-muted)" strokeWidth="1.5" />
            <line x1="238" y1="185" x2="252" y2="185" stroke="var(--color-text-muted)" strokeWidth="1.5" />

            {/* 3. Main Stator Casing with Cooling Fins */}
            <rect
              x="260"
              y="94"
              width="190"
              height="132"
              rx="6"
              fill={casingFill}
              stroke={casingStroke}
              strokeWidth="2"
            />
            <rect
              x="264"
              y="98"
              width="182"
              height="124"
              fill="url(#coolingFins)"
              opacity="0.8"
            />

            {/* 4. Top Terminal Junction Box */}
            <rect
              x="320"
              y="58"
              width="70"
              height="36"
              rx="4"
              fill="var(--color-surface-raised)"
              stroke={casingStroke}
              strokeWidth="1.5"
            />
            <rect x="330" y="66" width="50" height="4" fill="var(--color-border)" rx="1" />
            {/* Electrical Power Gland */}
            <rect x="345" y="48" width="20" height="10" fill="var(--color-border)" rx="2" />
            <path d="M 355 48 L 355 38" stroke="var(--color-accent)" strokeWidth="2" strokeDasharray="2 2" />

            {/* 5. Front Bearing Bracket / End-Shield (Right) */}
            <path
              d="M 450 100 L 485 110 L 485 210 L 450 220 Z"
              fill="var(--color-surface-raised)"
              stroke="var(--color-border)"
              strokeWidth="1.5"
            />
            {/* Bearing Flange Bolts */}
            <circle cx="470" cy="120" r="2.5" fill="var(--color-text-muted)" />
            <circle cx="470" cy="200" r="2.5" fill="var(--color-text-muted)" />

            {/* 6. Drive Shaft Assembly */}
            <rect
              x="485"
              y="146"
              width="80"
              height="28"
              rx="3"
              fill="var(--color-surface-input)"
              stroke={isRunning ? "var(--color-accent)" : "var(--color-border)"}
              strokeWidth="1.5"
            />
            {/* Shaft Keyway */}
            <rect x="520" y="148" width="30" height="5" fill="var(--color-text-muted)" rx="1" />

            {/* 7. Center Stator Core Centerline / Rotor Window */}
            <circle
              cx="355"
              cy="160"
              r="40"
              fill="var(--color-canvas)"
              stroke={casingStroke}
              strokeWidth="2"
            />
            <circle
              cx="355"
              cy="160"
              r="28"
              fill="var(--color-surface-raised)"
              stroke="var(--color-border-subtle)"
              strokeWidth="1"
            />

            {/* Running Rotation / Status Aura */}
            {isRunning ? (
              <g className="twin-schematic-running">
                {/* Rotating dash ring */}
                <circle
                  cx="355"
                  cy="160"
                  r="28"
                  fill="none"
                  stroke="var(--color-accent)"
                  strokeWidth="2.5"
                  strokeDasharray="14 10"
                />
                <circle cx="355" cy="160" r="10" fill="var(--color-success)" opacity="0.8" />
                {/* Arrow arc indicating rotation */}
                <path
                  d="M 335 145 A 25 25 0 0 1 375 145"
                  fill="none"
                  stroke="var(--color-success)"
                  strokeWidth="2"
                  markerEnd="url(#rotArrow)"
                />
              </g>
            ) : isTripped ? (
              <g>
                <circle cx="355" cy="160" r="24" fill="var(--color-danger-subtle)" />
                <path d="M 345 150 L 365 170 M 365 150 L 345 170" stroke="var(--color-danger)" strokeWidth="3" strokeLinecap="round" />
              </g>
            ) : isStarting ? (
              <g>
                <circle cx="355" cy="160" r="24" fill="var(--color-warning-subtle)" />
                <circle cx="355" cy="160" r="12" fill="var(--color-warning)" opacity="0.6" className="live-pulse-dot" />
              </g>
            ) : (
              /* Stopped */
              <circle cx="355" cy="160" r="8" fill="var(--color-text-muted)" />
            )}

            {/* Status Text on Center Core */}
            <text
              x="355"
              y="164"
              textAnchor="middle"
              fill={isTripped ? "var(--color-danger)" : isRunning ? "var(--color-text-primary)" : "var(--color-text-muted)"}
              fontSize="10"
              fontWeight="700"
              fontFamily="var(--font-mono)"
            >
              {isTripped ? "TRIP" : isRunning ? "ACTIVE" : normState.slice(0, 4)}
            </text>

            {/* Tripped safety interlock banner */}
            {isTripped && (
              <g>
                <rect x="290" y="106" width="130" height="24" rx="4" fill="var(--color-danger)" opacity="0.9" />
                <text x="355" y="122" textAnchor="middle" fill="#ffffff" fontSize="11" fontWeight="700" letterSpacing="1">
                  INTERLOCK TRIPPED
                </text>
              </g>
            )}

            {/* Leader Lines to Spatial Sensor Node Overlays */}
            {/* Top: Terminal Box to Power Node */}
            <polyline points="355,58 355,20 180,20" fill="none" stroke="var(--color-border-hover)" strokeWidth="1" strokeDasharray="3 3" />
            <circle cx="355" cy="58" r="3" fill="var(--color-accent)" />

            {/* Left-Top: Stator Temp */}
            <polyline points="280,94 280,48 180,48" fill="none" stroke="var(--color-border-hover)" strokeWidth="1" strokeDasharray="3 3" />
            <circle cx="280" cy="94" r="3" fill="var(--color-accent)" />

            {/* Left-Bottom: Ambient Air & Wear */}
            <polyline points="230,160 180,160" fill="none" stroke="var(--color-border-hover)" strokeWidth="1" strokeDasharray="3 3" />
            <circle cx="230" cy="160" r="3" fill="var(--color-text-muted)" />

            {/* Right-Top: Shaft Speed & Torque */}
            <polyline points="535,146 535,48 580,48" fill="none" stroke="var(--color-border-hover)" strokeWidth="1" strokeDasharray="3 3" />
            <circle cx="535" cy="146" r="3" fill="var(--color-success)" />

            {/* Right-Bottom: Bearing Vibration */}
            <polyline points="470,160 520,160 580,160" fill="none" stroke="var(--color-border-hover)" strokeWidth="1" strokeDasharray="3 3" />
            <circle cx="470" cy="160" r="3" fill="var(--color-warning)" />
          </svg>

          {/* Spatial Callout Sensor Overlays (HTML over SVG for accessibility & crisp text) */}
          <div
            style={{
              position: "absolute",
              top: "10px",
              left: "12px",
              display: "flex",
              flexDirection: "column",
              gap: "6px",
              maxWidth: "200px",
            }}
          >
            {/* 1. Stator Core Temperature */}
            <div
              style={{
                backgroundColor: "var(--color-surface-raised)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                padding: "4px 8px",
                display: "flex",
                flexDirection: "column",
                gap: "2px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "10px", fontWeight: 600, color: "var(--color-text-muted)", display: "flex", alignItems: "center", gap: "4px" }}>
                  <Thermometer size={10} color="var(--color-accent)" /> PROCESS TEMP
                </span>
                {renderQualityTag("process_temp_c")}
              </div>
              <div style={{ display: "flex", alignItems: "baseline", gap: "4px" }}>
                <span className="text-mono" style={{ fontSize: "14px", fontWeight: 700, color: "var(--color-text-primary)" }}>
                  {fmt(signals?.process_temp_c, 1)}
                </span>
                <span style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>°C</span>
                {signals?.air_temp_c !== undefined && signals?.air_temp_c !== null && (
                  <span style={{ fontSize: "10px", color: "var(--color-text-muted)", marginLeft: "4px" }}>
                    (Air: {fmt(signals?.air_temp_c, 1)}°)
                  </span>
                )}
              </div>
            </div>

            {/* 2. Electrical Current & Voltage */}
            <div
              style={{
                backgroundColor: "var(--color-surface-raised)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                padding: "4px 8px",
                display: "flex",
                flexDirection: "column",
                gap: "2px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "10px", fontWeight: 600, color: "var(--color-text-muted)", display: "flex", alignItems: "center", gap: "4px" }}>
                  <Zap size={10} color="var(--color-accent)" /> CURRENT & VOLTAGE
                </span>
                {renderQualityTag("current_a")}
              </div>
              <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
                <div>
                  <span className="text-mono" style={{ fontSize: "14px", fontWeight: 700, color: "var(--color-text-primary)" }}>
                    {fmt(signals?.current_a, 2)}
                  </span>
                  <span style={{ fontSize: "11px", color: "var(--color-text-secondary)", marginLeft: "2px" }}>A</span>
                </div>
                {signals?.voltage_v !== undefined && signals?.voltage_v !== null && (
                  <div>
                    <span className="text-mono" style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
                      {fmt(signals?.voltage_v, 1)}
                    </span>
                    <span style={{ fontSize: "10px", color: "var(--color-text-muted)", marginLeft: "2px" }}>V</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Sensor Overlays */}
          <div
            style={{
              position: "absolute",
              top: "10px",
              right: "12px",
              display: "flex",
              flexDirection: "column",
              gap: "6px",
              maxWidth: "200px",
            }}
          >
            {/* 3. Rotational Speed & Torque */}
            <div
              style={{
                backgroundColor: "var(--color-surface-raised)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                padding: "4px 8px",
                display: "flex",
                flexDirection: "column",
                gap: "2px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "10px", fontWeight: 600, color: "var(--color-text-muted)", display: "flex", alignItems: "center", gap: "4px" }}>
                  <RotateCw size={10} color="var(--color-success)" /> DRIVE SHAFT
                </span>
                {renderQualityTag("rotational_speed_rpm")}
              </div>
              <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
                <div>
                  <span className="text-mono" style={{ fontSize: "14px", fontWeight: 700, color: "var(--color-text-primary)" }}>
                    {fmt(signals?.rotational_speed_rpm, 0)}
                  </span>
                  <span style={{ fontSize: "11px", color: "var(--color-text-secondary)", marginLeft: "2px" }}>RPM</span>
                </div>
                {signals?.torque_nm !== undefined && signals?.torque_nm !== null && (
                  <div>
                    <span className="text-mono" style={{ fontSize: "13px", color: "var(--color-text-primary)" }}>
                      {fmt(signals?.torque_nm, 1)}
                    </span>
                    <span style={{ fontSize: "10px", color: "var(--color-text-secondary)", marginLeft: "2px" }}>Nm</span>
                  </div>
                )}
              </div>
            </div>

            {/* 4. Bearing Vibration RMS */}
            <div
              style={{
                backgroundColor: "var(--color-surface-raised)",
                border: `1px solid ${
                  signals?.vibration_mm_s && signals.vibration_mm_s > 4.5
                    ? "var(--color-warning-border)"
                    : "var(--color-border)"
                }`,
                borderRadius: "var(--radius-sm)",
                padding: "4px 8px",
                display: "flex",
                flexDirection: "column",
                gap: "2px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "10px", fontWeight: 600, color: "var(--color-text-muted)", display: "flex", alignItems: "center", gap: "4px" }}>
                  <Activity size={10} color="var(--color-warning)" /> VIBRATION RMS
                </span>
                {renderQualityTag("vibration_mm_s")}
              </div>
              <div style={{ display: "flex", alignItems: "baseline", gap: "4px" }}>
                <span
                  className="text-mono"
                  style={{
                    fontSize: "14px",
                    fontWeight: 700,
                    color:
                      signals?.vibration_mm_s && signals.vibration_mm_s > 4.5
                        ? "var(--color-warning)"
                        : "var(--color-text-primary)",
                  }}
                >
                  {fmt(signals?.vibration_mm_s, 2)}
                </span>
                <span style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>mm/s</span>
                {signals?.vibration_mm_s && signals.vibration_mm_s > 4.5 && (
                  <span style={{ fontSize: "10px", color: "var(--color-warning)", marginLeft: "4px" }}>
                    (ISO Exceeded)
                  </span>
                )}
              </div>
            </div>

            {/* 5. Tool Wear or Pressure (if available) */}
            {(signals?.tool_wear_min !== undefined || signals?.pressure_bar !== undefined) && (
              <div
                style={{
                  backgroundColor: "var(--color-surface-raised)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-sm)",
                  padding: "4px 8px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  fontSize: "11px",
                }}
              >
                {signals?.tool_wear_min !== undefined && signals?.tool_wear_min !== null ? (
                  <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                    <Wrench size={10} color="var(--color-text-muted)" />
                    <span style={{ color: "var(--color-text-muted)" }}>Wear:</span>
                    <span className="text-mono" style={{ fontWeight: 600 }}>{fmt(signals.tool_wear_min, 0)} min</span>
                  </div>
                ) : null}
                {signals?.pressure_bar !== undefined && signals?.pressure_bar !== null ? (
                  <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                    <Compass size={10} color="var(--color-text-muted)" />
                    <span style={{ color: "var(--color-text-muted)" }}>Pres:</span>
                    <span className="text-mono" style={{ fontWeight: 600 }}>{fmt(signals.pressure_bar, 1)} bar</span>
                  </div>
                ) : null}
              </div>
            )}
          </div>

          {/* Safety Interlock Trip Banner Footer in SVG Container */}
          {edge?.trip && (
            <div
              style={{
                position: "absolute",
                bottom: "8px",
                left: "12px",
                right: "12px",
                backgroundColor: "var(--color-danger-subtle)",
                border: "1px solid var(--color-danger-border)",
                borderRadius: "var(--radius-sm)",
                padding: "4px 10px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                fontSize: "11px",
                color: "var(--color-danger)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <Lock size={12} />
                <span style={{ fontWeight: 700 }}>HARDWARE SAFETY TRIP:</span>
                <span className="text-mono">{edge.trip}</span>
              </div>
              <span style={{ fontSize: "10px" }}>Safety interlock active on edge controller</span>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};
