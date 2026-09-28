import React from "react";
import { Shield, User, Server } from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/common/Card";
import { RoleGate } from "../components/common/RoleGate";
import { Button } from "../components/common/Button";
import { useAuth } from "../hooks/useAuth";
import { ADMIN_ONLY } from "../utils/rbac";

export const SettingsPage: React.FC = () => {
  const { user, role } = useAuth();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      <PageHeader
        title="Platform Settings & RBAC"
        description="System configuration, security policies, active user session details, and role permissions."
      />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: "var(--space-4)" }}>
        {/* Active Session */}
        <Card title="Active Session & Identity" subtitle="Authenticated operator">
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)", fontSize: "13px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--color-border-subtle)", paddingBottom: "8px" }}>
              <span style={{ color: "var(--color-text-muted)" }}>Username:</span>
              <span className="text-mono" style={{ fontWeight: 600 }}>{user?.username}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--color-border-subtle)", paddingBottom: "8px" }}>
              <span style={{ color: "var(--color-text-muted)" }}>Assigned Role:</span>
              <span style={{ fontWeight: 600, color: "var(--color-accent)" }}>{role}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--color-border-subtle)", paddingBottom: "8px" }}>
              <span style={{ color: "var(--color-text-muted)" }}>User ID:</span>
              <span className="text-mono">{user?.id}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--color-text-muted)" }}>Account Active:</span>
              <span style={{ color: user?.is_active ? "var(--color-success)" : "var(--color-danger)", fontWeight: 600 }}>
                {user?.is_active ? "ACTIVE" : "INACTIVE"}
              </span>
            </div>
          </div>
        </Card>

        {/* System & Architecture Info */}
        <Card title="System Architecture" subtitle="Backend services & endpoints">
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)", fontSize: "13px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--color-border-subtle)", paddingBottom: "8px" }}>
              <span style={{ color: "var(--color-text-muted)" }}>REST API:</span>
              <span className="text-mono">/api/v1 (FastAPI 0.115)</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--color-border-subtle)", paddingBottom: "8px" }}>
              <span style={{ color: "var(--color-text-muted)" }}>WebSocket:</span>
              <span className="text-mono">/ws/live (Starlette WS)</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--color-border-subtle)", paddingBottom: "8px" }}>
              <span style={{ color: "var(--color-text-muted)" }}>MQTT Broker:</span>
              <span className="text-mono">HiveMQ TLS / Mosquitto</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--color-text-muted)" }}>Digital Twin:</span>
              <span className="text-mono">In-Memory FSM (S13)</span>
            </div>
          </div>
        </Card>
      </div>

      {/* Admin-only Panel */}
      <RoleGate
        allowedRoles={ADMIN_ONLY}
        fallback={
          <div
            style={{
              padding: "var(--space-4)",
              backgroundColor: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-lg)",
              color: "var(--color-text-muted)",
              fontSize: "13px",
            }}
          >
            System administration options require the <strong>ADMIN</strong> role.
          </div>
        }
      >
        <Card title="Administrative Controls" subtitle="Restricted to ADMIN role">
          <div style={{ display: "flex", gap: "var(--space-3)", flexWrap: "wrap" }}>
            <Button variant="secondary" size="sm" leftIcon={<User size={14} />}>
              Manage Operators & Engineers
            </Button>
            <Button variant="secondary" size="sm" leftIcon={<Server size={14} />}>
              Audit Security Logs
            </Button>
            <Button variant="danger" size="sm" leftIcon={<Shield size={14} />}>
              Flush Offline Twin Cache
            </Button>
          </div>
        </Card>
      </RoleGate>
    </div>
  );
};
