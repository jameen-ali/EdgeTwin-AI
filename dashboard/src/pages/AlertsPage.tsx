import React, { useState, useEffect } from "react";
import { AlertTriangle, CheckCircle, RefreshCw } from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/common/Card";
import { DataTable, Column } from "../components/common/DataTable";
import { Button } from "../components/common/Button";
import { LoadingState } from "../components/common/LoadingState";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { RoleGate } from "../components/common/RoleGate";
import { AlertItem } from "../types/alert";
import { api } from "../api/client";
import { formatDateTime } from "../utils/formatters";
import { PRIVILEGED_ROLES } from "../utils/rbac";

export const AlertsPage: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<string>("ALL");

  const fetchAlerts = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.alerts.list();
      setAlerts(data || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load alerts";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, []);

  const handleAcknowledge = async (alertId: number) => {
    try {
      await api.alerts.acknowledge(alertId);
      await fetchAlerts();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to acknowledge alert");
    }
  };

  const filtered = alerts.filter(
    (a) => filterSeverity === "ALL" || a.severity === filterSeverity
  );

  const columns: Column<AlertItem>[] = [
    {
      key: "id",
      header: "Alert ID",
      render: (a) => <span className="text-mono">ALT-{a.id}</span>,
    },
    {
      key: "machine_id",
      header: "Machine",
      render: (a) => <span className="text-mono" style={{ fontWeight: 600 }}>{a.machine_id}</span>,
    },
    {
      key: "severity",
      header: "Severity",
      render: (a) => {
        let color = "var(--color-info)";
        if (a.severity === "CRITICAL") color = "var(--color-danger)";
        if (a.severity === "WARNING") color = "var(--color-warning)";

        return (
          <span
            style={{
              fontSize: "11px",
              fontWeight: 700,
              padding: "2px 6px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--color-surface-raised)",
              color,
              border: `1px solid ${color}`,
            }}
          >
            {a.severity}
          </span>
        );
      },
    },
    {
      key: "rule_id",
      header: "Rule / Cause",
      render: (a) => <span className="text-mono" style={{ fontSize: "12px" }}>{a.rule_id}</span>,
    },
    {
      key: "message",
      header: "Description",
      render: (a) => <span style={{ color: "var(--color-text-secondary)" }}>{a.message}</span>,
    },
    {
      key: "status",
      header: "Status",
      render: (a) => (
        <span style={{ fontSize: "12px", fontWeight: 600, color: a.status === "ACTIVE" ? "var(--color-warning)" : "var(--color-success)" }}>
          {a.status}
        </span>
      ),
    },
    {
      key: "created_at",
      header: "Triggered At",
      render: (a) => (
        <span className="text-mono" style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>
          {formatDateTime(a.created_at)}
        </span>
      ),
    },
    {
      key: "action",
      header: "Action",
      render: (a) => (
        <RoleGate
          allowedRoles={PRIVILEGED_ROLES}
          fallback={<span style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>View Only</span>}
        >
          {a.status === "ACTIVE" && (
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<CheckCircle size={12} />}
              onClick={() => handleAcknowledge(a.id)}
            >
              Acknowledge
            </Button>
          )}
        </RoleGate>
      ),
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      <PageHeader
        title="Operational Alerts"
        description="Active alarms and fault notifications triggered by the L1–L6 rule engine and calibrated machine learning models."
        actions={
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<RefreshCw size={14} />}
            onClick={fetchAlerts}
          >
            Refresh Alerts
          </Button>
        }
      />

      <div style={{ display: "flex", gap: "var(--space-2)" }}>
        {["ALL", "CRITICAL", "WARNING", "INFO"].map((sev) => (
          <Button
            key={sev}
            variant={filterSeverity === sev ? "primary" : "secondary"}
            size="sm"
            onClick={() => setFilterSeverity(sev)}
          >
            {sev}
          </Button>
        ))}
      </div>

      <Card title="Alert Log" subtitle={`Showing ${filtered.length} alert event(s)`}>
        {isLoading ? (
          <LoadingState message="Fetching operational alarms..." />
        ) : error ? (
          <ErrorState message={error} onRetry={fetchAlerts} />
        ) : filtered.length === 0 ? (
          <EmptyState
            title="No active alerts"
            description="All monitored machine parameters are currently within normal operating limits."
            icon={<AlertTriangle size={24} />}
          />
        ) : (
          <DataTable
            columns={columns}
            data={filtered}
            keyExtractor={(a) => a.id}
          />
        )}
      </Card>
    </div>
  );
};
