import React, { useState, useEffect } from "react";
import { Cpu, Activity, AlertTriangle, ShieldCheck, RefreshCw } from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { MetricGrid } from "../components/common/MetricGrid";
import { Metric } from "../components/common/Metric";
import { Card } from "../components/common/Card";
import { DataTable, Column } from "../components/common/DataTable";
import { StatusBadge } from "../components/common/StatusBadge";
import { HealthBadge } from "../components/common/HealthBadge";
import { LoadingState } from "../components/common/LoadingState";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { Button } from "../components/common/Button";
import { MachineSummary } from "../types/machine";
import { api } from "../api/client";
import { useTwinWebSocket } from "../hooks/useTwinWebSocket";
import { formatNumber, formatPercent, formatDateTime } from "../utils/formatters";

export const DashboardPage: React.FC = () => {
  const [machines, setMachines] = useState<MachineSummary[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const { twins, isConnected: isWsConnected } = useTwinWebSocket();

  const fetchMachines = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.machines.list();
      setMachines(data || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load machines.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMachines();
  }, []);

  // Merge live twin updates into the machine list if available
  const displayMachines = machines.map((m) => {
    const liveTwin = twins[m.machine_id];
    if (!liveTwin) return m;
    return {
      ...m,
      operating_state: liveTwin.operating_state,
      health_state: liveTwin.health_state,
      connectivity_state: liveTwin.connectivity_state,
      health_score: liveTwin.health_score,
      failure_probability: liveTwin.failure_probability,
      risk_band: liveTwin.risk_band,
      last_telemetry_at: liveTwin.last_telemetry_at,
    };
  });

  const activeCount = displayMachines.filter((m) => m.operating_state === "RUNNING").length;
  const criticalCount = displayMachines.filter((m) => m.health_state === "CRITICAL").length;
  const averageHealth = displayMachines.length > 0
    ? displayMachines.reduce((acc, m) => acc + m.health_score, 0) / displayMachines.length
    : null;

  const columns: Column<MachineSummary>[] = [
    {
      key: "machine_id",
      header: "Machine ID",
      render: (m) => <span className="text-mono" style={{ fontWeight: 600 }}>{m.machine_id}</span>,
    },
    {
      key: "machine_type",
      header: "Type",
      render: (m) => <span>{m.machine_type || "Induction Motor"}</span>,
    },
    {
      key: "operating_state",
      header: "Operating State",
      render: (m) => <StatusBadge status={m.operating_state} size="sm" />,
    },
    {
      key: "health_state",
      header: "Health",
      render: (m) => <HealthBadge state={m.health_state} size="sm" />,
    },
    {
      key: "health_score",
      header: "Health Score",
      align: "right",
      render: (m) => (
        <span className="text-mono" style={{ fontWeight: 600 }}>
          {formatNumber(m.health_score, 1)}
        </span>
      ),
    },
    {
      key: "failure_probability",
      header: "Failure Risk",
      align: "right",
      render: (m) => (
        <span className="text-mono" style={{ color: m.failure_probability > 0.16 ? "var(--color-warning)" : "inherit" }}>
          {formatPercent(m.failure_probability)}
        </span>
      ),
    },
    {
      key: "last_telemetry_at",
      header: "Last Update",
      render: (m) => (
        <span className="text-mono" style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>
          {formatDateTime(m.last_telemetry_at)}
        </span>
      ),
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      <PageHeader
        title="Fleet Overview"
        description="Real-time telemetry, Digital Twin synchronization, and predictive health monitoring for industrial machine assets."
        actions={
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<RefreshCw size={14} />}
            onClick={fetchMachines}
          >
            Refresh Fleet
          </Button>
        }
      />

      {/* Level 1: Major Operational Metrics */}
      <MetricGrid columns={4}>
        <Metric
          label="Total Machines"
          value={displayMachines.length}
          unit="units"
          icon={<Cpu size={18} />}
        />
        <Metric
          label="Active Running"
          value={activeCount}
          unit="online"
          status={activeCount > 0 ? "success" : "normal"}
          icon={<Activity size={18} />}
        />
        <Metric
          label="Fleet Health"
          value={averageHealth !== null ? formatNumber(averageHealth, 1) : "—"}
          unit="/ 100"
          status={averageHealth !== null && averageHealth > 80 ? "success" : "warning"}
          icon={<ShieldCheck size={18} />}
        />
        <Metric
          label="Critical Failures"
          value={criticalCount}
          unit="alerts"
          status={criticalCount > 0 ? "danger" : "normal"}
          icon={<AlertTriangle size={18} />}
        />
      </MetricGrid>

      {/* Level 2: Machine Fleet Directory Table */}
      <Card
        title="Machine Fleet Status"
        subtitle={
          isWsConnected
            ? "Live WebSocket twin synchronization active (1 Hz)"
            : "Displaying cached telemetry from backend"
        }
      >
        {isLoading ? (
          <LoadingState message="Connecting to fleet telemetry service..." />
        ) : error ? (
          <ErrorState message={error} onRetry={fetchMachines} />
        ) : displayMachines.length === 0 ? (
          <EmptyState
            title="No machines registered"
            description="No active machine assets were found in the database. Ensure the edge firmware simulation or backend seed script is running."
            icon={<Cpu size={24} />}
            action={
              <Button variant="secondary" size="sm" onClick={fetchMachines}>
                Check Again
              </Button>
            }
          />
        ) : (
          <DataTable
            columns={columns}
            data={displayMachines}
            keyExtractor={(m) => m.machine_id}
          />
        )}
      </Card>
    </div>
  );
};
