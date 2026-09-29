import React from "react";
import { ArrowLeft, RefreshCw, MapPin } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "../common/Button";
import { StatusBadge } from "../common/StatusBadge";
import { HealthBadge } from "../common/HealthBadge";
import { ConnectionIndicator } from "../common/ConnectionIndicator";
import { LiveIndicator } from "../common/LiveIndicator";
import { OperatingState, HealthState, ConnectivityState } from "../../types/machine";
import { formatTimeAgo } from "../../utils/formatters";

export interface MachineHeaderProps {
  machineId: string;
  machineType?: string;
  location?: string | null;
  operatingState?: OperatingState | string;
  healthState?: HealthState | string;
  connectivityState?: ConnectivityState | string;
  lastUpdatedAt?: string | null;
  isLiveWs?: boolean;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export const MachineHeader: React.FC<MachineHeaderProps> = ({
  machineId,
  machineType = "Industrial Asset",
  location,
  operatingState = "UNKNOWN",
  healthState = "UNKNOWN",
  connectivityState = "OFFLINE",
  lastUpdatedAt,
  isLiveWs = false,
  onRefresh,
  isRefreshing = false,
}) => {
  const navigate = useNavigate();

  const normConn = (connectivityState || "").toUpperCase();
  const isConnLive = normConn === "LIVE" || normConn === "ONLINE";
  const isConnStale = normConn === "STALE";

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-4)",
        marginBottom: "var(--space-6)",
      }}
    >
      {/* Top Breadcrumb / Back Navigation */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "var(--space-2)",
        }}
      >
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<ArrowLeft size={14} />}
          onClick={() => navigate("/machines")}
          aria-label="Return to Fleet directory"
          style={{ padding: "0 8px" }}
        >
          Fleet
        </Button>

        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
          {isLiveWs ? (
            <LiveIndicator isLive={true} label="LIVE STREAM" />
          ) : (
            <ConnectionIndicator
              status={isConnLive ? "ONLINE" : isConnStale ? "CONNECTING" : "OFFLINE"}
              label={normConn || "OFFLINE"}
            />
          )}

          {onRefresh && (
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<RefreshCw size={14} />}
              onClick={onRefresh}
              isLoading={isRefreshing}
              aria-label="Refresh machine telemetry and state"
            >
              Refresh
            </Button>
          )}
        </div>
      </div>

      {/* Main Identity & Badges Row */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: "var(--space-4)",
          padding: "var(--space-5)",
          backgroundColor: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-lg)",
        }}
      >
        <div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--space-3)",
              flexWrap: "wrap",
            }}
          >
            <h1
              className="text-mono"
              style={{
                fontSize: "24px",
                fontWeight: 700,
                color: "var(--color-text-primary)",
                letterSpacing: "var(--tracking-tight)",
                margin: 0,
              }}
            >
              {machineId}
            </h1>
            <span
              style={{
                fontSize: "13px",
                color: "var(--color-text-secondary)",
                backgroundColor: "var(--color-surface-raised)",
                padding: "2px 8px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border-subtle)",
              }}
            >
              {machineType}
            </span>
          </div>

          {location && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "4px",
                marginTop: "6px",
                fontSize: "12px",
                color: "var(--color-text-muted)",
              }}
            >
              <MapPin size={12} />
              <span>{location}</span>
            </div>
          )}
        </div>

        {/* Status Indicators */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "var(--space-3)",
            flexWrap: "wrap",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "4px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <StatusBadge status={operatingState} />
              <HealthBadge state={healthState} />
            </div>
            {lastUpdatedAt && (
              <span
                style={{
                  fontSize: "11px",
                  color: "var(--color-text-muted)",
                }}
              >
                Updated {formatTimeAgo(lastUpdatedAt)}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
