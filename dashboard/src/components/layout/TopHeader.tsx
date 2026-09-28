import React, { useState, useEffect } from "react";
import { Menu, Activity } from "lucide-react";
import { IconButton } from "../common/IconButton";
import { ConnectionIndicator } from "../common/ConnectionIndicator";
import { LiveIndicator } from "../common/LiveIndicator";
import { useAuth } from "../../hooks/useAuth";
import { useTwinWebSocket } from "../../hooks/useTwinWebSocket";
import { api } from "../../api/client";

export interface TopHeaderProps {
  onToggleSidebar?: () => void;
  pageTitle?: string;
}

export const TopHeader: React.FC<TopHeaderProps> = ({ onToggleSidebar, pageTitle = "Console" }) => {
  const { user, role } = useAuth();
  const { isConnected: isWsConnected } = useTwinWebSocket({ enabled: !!user });
  const [apiOnline, setApiOnline] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    const checkApi = async () => {
      try {
        await api.health.check();
        if (isMounted) setApiOnline(true);
      } catch {
        if (isMounted) setApiOnline(false);
      }
    };

    checkApi();
    const interval = setInterval(checkApi, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header className="app-topheader">
      {/* Left: Mobile Toggle & Page Context */}
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
        {onToggleSidebar && (
          <div className="mobile-toggle-btn" style={{ display: "none" }}>
            <IconButton
              icon={<Menu size={18} />}
              aria-label="Toggle navigation menu"
              onClick={onToggleSidebar}
            />
          </div>
        )}
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span
            style={{
              fontSize: "13px",
              fontWeight: 500,
              color: "var(--color-text-muted)",
            }}
          >
            EdgeTwin /
          </span>
          <span
            style={{
              fontSize: "14px",
              fontWeight: 600,
              color: "var(--color-text-primary)",
              letterSpacing: "var(--tracking-tight)",
            }}
          >
            {pageTitle}
          </span>
        </div>
      </div>

      {/* Right: Operational Telemetry Status & Role */}
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
        {/* Backend Connectivity */}
        <ConnectionIndicator
          status={apiOnline ? "ONLINE" : "OFFLINE"}
          label={apiOnline ? "API Online" : "API Offline"}
        />

        {/* WebSocket / Twin Connectivity */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "3px 10px",
            backgroundColor: "var(--color-surface-raised)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          <Activity size={14} style={{ color: isWsConnected ? "var(--color-accent)" : "var(--color-text-muted)" }} />
          <LiveIndicator isLive={isWsConnected} label={isWsConnected ? "Twin Live" : "Twin Stale"} />
        </div>

        {/* User Role Badge */}
        <span
          style={{
            fontSize: "11px",
            fontWeight: 700,
            letterSpacing: "var(--tracking-wide)",
            padding: "2px 8px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--color-surface-strong)",
            color: "var(--color-text-secondary)",
            border: "1px solid var(--color-border)",
            textTransform: "uppercase",
          }}
        >
          {role || "OPERATOR"}
        </span>
      </div>
    </header>
  );
};
