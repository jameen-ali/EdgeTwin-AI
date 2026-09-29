import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Cpu, RefreshCw } from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/common/Card";
import { DataTable, Column } from "../components/common/DataTable";
import { StatusBadge } from "../components/common/StatusBadge";
import { HealthBadge } from "../components/common/HealthBadge";
import { Button } from "../components/common/Button";
import { Input } from "../components/common/Input";
import { LoadingState } from "../components/common/LoadingState";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { MachineSummary } from "../types/machine";
import { api } from "../api/client";
import { formatNumber, formatPercent, formatDateTime } from "../utils/formatters";

export const MachinesPage: React.FC = () => {
  const navigate = useNavigate();
  const [machines, setMachines] = useState<MachineSummary[]>([]);
  const [search, setSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMachines = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.machines.list();
      setMachines(data || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load machines";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMachines();
  }, []);

  const filtered = machines.filter(
    (m) =>
      m.machine_id.toLowerCase().includes(search.toLowerCase()) ||
      (m.machine_type && m.machine_type.toLowerCase().includes(search.toLowerCase()))
  );

  const columns: Column<MachineSummary>[] = [
    {
      key: "machine_id",
      header: "Machine ID",
      render: (m) => <span className="text-mono" style={{ fontWeight: 600 }}>{m.machine_id}</span>,
    },
    {
      key: "machine_type",
      header: "Asset Type",
      render: (m) => <span>{m.machine_type}</span>,
    },
    {
      key: "operating_state",
      header: "Operating State",
      render: (m) => <StatusBadge status={m.operating_state} size="sm" />,
    },
    {
      key: "health_state",
      header: "Health State",
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
      header: "Calibrated Risk (t*=0.16)",
      align: "right",
      render: (m) => (
        <span className="text-mono" style={{ color: m.failure_probability > 0.16 ? "var(--color-warning)" : "inherit" }}>
          {formatPercent(m.failure_probability)}
        </span>
      ),
    },
    {
      key: "last_telemetry_at",
      header: "Last Telemetry",
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
        title="Connected Machines"
        description="Directory of industrial machine assets monitored via high-frequency edge telemetry and digital twin models."
        actions={
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<RefreshCw size={14} />}
            onClick={fetchMachines}
          >
            Refresh
          </Button>
        }
      />

      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)", maxWidth: "340px" }}>
        <Input
          placeholder="Search by machine ID or type..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <Card title="Asset Registry" subtitle={`Total monitored assets: ${filtered.length}`}>
        {isLoading ? (
          <LoadingState message="Loading machine registry..." />
        ) : error ? (
          <ErrorState message={error} onRetry={fetchMachines} />
        ) : filtered.length === 0 ? (
          <EmptyState
            title="No machines found"
            description={
              search ? `No machine assets matching "${search}".` : "No machine assets registered in the platform yet."
            }
            icon={<Cpu size={24} />}
          />
        ) : (
          <DataTable
            columns={columns}
            data={filtered}
            keyExtractor={(m) => m.machine_id}
            onRowClick={(m) => navigate(`/machines/${encodeURIComponent(m.machine_id)}`)}
          />
        )}
      </Card>
    </div>
  );
};
