import React, { useState, useEffect } from "react";
import { Play, RefreshCw, AlertCircle } from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/common/Card";
import { DataTable, Column } from "../components/common/DataTable";
import { Button } from "../components/common/Button";
import { LoadingState } from "../components/common/LoadingState";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { RoleGate } from "../components/common/RoleGate";
import { ScenarioSummary } from "../types/scenario";
import { api } from "../api/client";
import { PRIVILEGED_ROLES } from "../utils/rbac";

export const ScenariosPage: React.FC = () => {
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchScenarios = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.scenarios.list();
      setScenarios(data || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load scenarios";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchScenarios();
  }, []);

  const columns: Column<ScenarioSummary>[] = [
    {
      key: "scenario_id",
      header: "Scenario Code",
      render: (s) => <span className="text-mono" style={{ fontWeight: 600 }}>{s.scenario_id}</span>,
    },
    {
      key: "name",
      header: "Fault Profile",
      render: (s) => <span style={{ fontWeight: 500 }}>{s.name}</span>,
    },
    {
      key: "category",
      header: "Category",
      render: (s) => (
        <span
          style={{
            fontSize: "11px",
            padding: "2px 6px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--color-surface-raised)",
            border: "1px solid var(--color-border)",
            color: "var(--color-text-secondary)",
          }}
        >
          {s.category}
        </span>
      ),
    },
    {
      key: "description",
      header: "Failure Mechanism",
      render: (s) => <span style={{ color: "var(--color-text-secondary)" }}>{s.description}</span>,
    },
    {
      key: "action",
      header: "Injection Action",
      align: "right",
      render: (s) => (
        <RoleGate
          allowedRoles={PRIVILEGED_ROLES}
          fallback={<span style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>Unauthorized</span>}
        >
          <Button
            variant="warning"
            size="sm"
            leftIcon={<Play size={12} />}
            onClick={() => alert(`Simulating scenario: ${s.name} (${s.scenario_id})`)}
          >
            Inject Fault
          </Button>
        </RoleGate>
      ),
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      <PageHeader
        title="Chaos & Fault Injection Scenarios"
        description="Controlled synthetic failure injection library used to validate edge safety trips, model sensitivity, and digital twin anomaly detection."
        actions={
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<RefreshCw size={14} />}
            onClick={fetchScenarios}
          >
            Refresh
          </Button>
        }
      />

      <Card
        title="Available Fault Profiles"
        subtitle="Privileged action: Requires Maintenance Engineer or Admin role"
      >
        {isLoading ? (
          <LoadingState message="Loading fault scenario catalog..." />
        ) : error ? (
          <ErrorState message={error} onRetry={fetchScenarios} />
        ) : scenarios.length === 0 ? (
          <EmptyState
            title="No scenarios configured"
            description="The scenario catalogue has not yet been loaded from backend."
            icon={<AlertCircle size={22} />}
          />
        ) : (
          <DataTable
            columns={columns}
            data={scenarios}
            keyExtractor={(s) => s.scenario_id}
          />
        )}
      </Card>
    </div>
  );
};
