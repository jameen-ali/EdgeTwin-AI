import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  ShieldCheck,
  Search,
} from "lucide-react";
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
import { AlertDetailModal } from "../components/alerts/AlertDetailModal";
import { CreateWorkOrderModal } from "../components/maintenance/CreateWorkOrderModal";
import { OperatorFeedbackModal } from "../components/feedback/OperatorFeedbackModal";

export const AlertsPage: React.FC = () => {
  const navigate = useNavigate();

  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<string>("ALL");
  const [filterStatus, setFilterStatus] = useState<string>("ALL");
  const [searchMachine, setSearchMachine] = useState<string>("");

  // Modals state
  const [selectedAlert, setSelectedAlert] = useState<AlertItem | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [workOrderAlert, setWorkOrderAlert] = useState<AlertItem | null>(null);
  const [feedbackAlert, setFeedbackAlert] = useState<AlertItem | null>(null);

  // Toast / notification
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const fetchAlerts = useCallback(async () => {
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
  }, []);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  const handleAcknowledge = async (alertId: number, notes?: string) => {
    // Optimistic UI update
    const previousAlerts = [...alerts];
    setAlerts((prev) =>
      prev.map((a) => (a.id === alertId ? { ...a, status: "ACKNOWLEDGED", acknowledged_at: new Date().toISOString() } : a))
    );

    try {
      const updated = await api.alerts.acknowledge(alertId, { notes });
      setAlerts((prev) => prev.map((a) => (a.id === alertId ? updated : a)));
      showToast(`Alert ALT-${alertId} acknowledged successfully.`);
    } catch (err: unknown) {
      // Rollback on failure
      setAlerts(previousAlerts);
      const msg = err instanceof Error ? err.message : "Failed to acknowledge alert";
      showToast(`Error: ${msg}`);
    }
  };

  const handleResolve = async (alertId: number, notes?: string) => {
    const previousAlerts = [...alerts];
    setAlerts((prev) =>
      prev.map((a) => (a.id === alertId ? { ...a, status: "RESOLVED", resolved_at: new Date().toISOString() } : a))
    );

    try {
      const updated = await api.alerts.resolve(alertId, { notes });
      setAlerts((prev) => prev.map((a) => (a.id === alertId ? updated : a)));
      showToast(`Alert ALT-${alertId} resolved.`);
    } catch (err: unknown) {
      setAlerts(previousAlerts);
      const msg = err instanceof Error ? err.message : "Failed to resolve alert";
      showToast(`Error: ${msg}`);
    }
  };

  const filtered = alerts.filter((a) => {
    if (filterSeverity !== "ALL" && a.severity !== filterSeverity) return false;
    if (filterStatus !== "ALL") {
      const normStatus = a.status.toUpperCase();
      if (filterStatus === "ACTIVE" && normStatus !== "OPEN" && normStatus !== "ACTIVE") return false;
      if (filterStatus === "ACKNOWLEDGED" && normStatus !== "ACKNOWLEDGED") return false;
      if (filterStatus === "RESOLVED" && normStatus !== "RESOLVED") return false;
    }
    if (searchMachine.trim() && !a.machine_id.toLowerCase().includes(searchMachine.trim().toLowerCase())) {
      return false;
    }
    return true;
  });

  const columns: Column<AlertItem>[] = [
    {
      key: "id",
      header: "Alert ID",
      render: (a) => (
        <button
          type="button"
          onClick={() => {
            setSelectedAlert(a);
            setIsDetailOpen(true);
          }}
          style={{
            background: "none",
            border: "none",
            padding: 0,
            cursor: "pointer",
            fontFamily: "var(--font-mono)",
            fontWeight: 700,
            color: "var(--color-accent)",
            textDecoration: "underline",
          }}
        >
          ALT-{a.id}
        </button>
      ),
    },
    {
      key: "machine_id",
      header: "Machine",
      render: (a) => (
        <button
          type="button"
          onClick={() => navigate(`/machines/${a.machine_id}`)}
          style={{
            background: "none",
            border: "none",
            padding: 0,
            cursor: "pointer",
            fontFamily: "var(--font-mono)",
            fontWeight: 600,
            color: "var(--color-text-primary)",
          }}
        >
          {a.machine_id}
        </button>
      ),
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
      key: "alert_type",
      header: "Alert Type",
      render: (a) => (
        <span className="text-mono" style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
          {a.alert_type || a.rule_id || "ANOMALY"}
        </span>
      ),
    },
    {
      key: "message",
      header: "Description",
      render: (a) => <span style={{ color: "var(--color-text-secondary)" }}>{a.message}</span>,
    },
    {
      key: "status",
      header: "Status",
      render: (a) => {
        let color = "var(--color-warning)";
        if (a.status === "RESOLVED") color = "var(--color-success)";
        if (a.status === "ACKNOWLEDGED") color = "var(--color-info)";

        return (
          <span style={{ fontSize: "12px", fontWeight: 700, color }}>
            {a.status}
          </span>
        );
      },
    },
    {
      key: "created_at",
      header: "Triggered At",
      render: (a) => (
        <span className="text-mono" style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>
          {formatDateTime(a.triggered_at || a.created_at)}
        </span>
      ),
    },
    {
      key: "action",
      header: "Actions",
      render: (a) => {
        const isOpenAlert = a.status === "OPEN" || a.status === "ACTIVE";
        const isAck = a.status === "ACKNOWLEDGED";

        return (
          <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setSelectedAlert(a);
                setIsDetailOpen(true);
              }}
            >
              Details
            </Button>

            <RoleGate allowedRoles={PRIVILEGED_ROLES}>
              {isOpenAlert && (
                <Button
                  variant="primary"
                  size="sm"
                  leftIcon={<CheckCircle size={12} />}
                  onClick={() => handleAcknowledge(a.id)}
                >
                  Ack
                </Button>
              )}
              {isAck && (
                <Button
                  variant="secondary"
                  size="sm"
                  style={{ color: "var(--color-success)" }}
                  leftIcon={<ShieldCheck size={12} />}
                  onClick={() => handleResolve(a.id)}
                >
                  Resolve
                </Button>
              )}
            </RoleGate>
          </div>
        );
      },
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      {/* Toast Notification */}
      {toastMessage && (
        <div
          role="status"
          style={{
            position: "fixed",
            bottom: "var(--space-6)",
            right: "var(--space-6)",
            backgroundColor: "var(--color-surface)",
            border: "1px solid var(--color-accent)",
            color: "var(--color-text-primary)",
            padding: "var(--space-3) var(--space-4)",
            borderRadius: "var(--radius-md)",
            boxShadow: "0 8px 24px rgba(0, 0, 0, 0.5)",
            zIndex: 100,
            fontSize: "13px",
            fontWeight: 500,
          }}
        >
          {toastMessage}
        </div>
      )}

      <PageHeader
        title="Operational Alerts & Incidents"
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

      {/* Filter and Search Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "var(--space-3)",
          backgroundColor: "var(--color-surface)",
          padding: "var(--space-3) var(--space-4)",
          borderRadius: "var(--radius-md)",
          border: "1px solid var(--color-border)",
        }}
      >
        {/* Status Filters */}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
          <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-muted)" }}>STATUS:</span>
          {["ALL", "ACTIVE", "ACKNOWLEDGED", "RESOLVED"].map((st) => (
            <Button
              key={st}
              variant={filterStatus === st ? "primary" : "secondary"}
              size="sm"
              onClick={() => setFilterStatus(st)}
            >
              {st}
            </Button>
          ))}
        </div>

        {/* Severity Filters */}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
          <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-muted)" }}>SEVERITY:</span>
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

        {/* Machine Search */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <Search size={14} color="var(--color-text-muted)" />
          <input
            type="text"
            placeholder="Filter machine (e.g. MOT)..."
            value={searchMachine}
            onChange={(e) => setSearchMachine(e.target.value)}
            style={{
              backgroundColor: "var(--color-surface-raised)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-sm)",
              padding: "5px 8px",
              color: "var(--color-text-primary)",
              fontSize: "12px",
              fontFamily: "var(--font-mono)",
            }}
          />
        </div>
      </div>

      <Card title="Alert Log" subtitle={`Showing ${filtered.length} of ${alerts.length} incident(s)`}>
        {isLoading ? (
          <LoadingState message="Fetching operational alarms..." />
        ) : error ? (
          <ErrorState message={error} onRetry={fetchAlerts} />
        ) : filtered.length === 0 ? (
          <EmptyState
            title="No matching alerts"
            description="All monitored machine parameters are currently within normal operating limits or match criteria."
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

      {/* Incident Detail Modal */}
      {selectedAlert && (
        <AlertDetailModal
          isOpen={isDetailOpen}
          onClose={() => setIsDetailOpen(false)}
          alert={selectedAlert}
          onAcknowledge={handleAcknowledge}
          onResolve={handleResolve}
          onCreateWorkOrder={(alert) => {
            setWorkOrderAlert(alert);
          }}
          onSubmitFeedback={(alert) => {
            setFeedbackAlert(alert);
          }}
          onViewMachine={(machineId) => navigate(`/machines/${machineId}`)}
        />
      )}

      {/* Create Work Order Modal linked from Alert */}
      {workOrderAlert && (
        <CreateWorkOrderModal
          isOpen={Boolean(workOrderAlert)}
          onClose={() => setWorkOrderAlert(null)}
          initialMachineId={workOrderAlert.machine_id}
          initialAlertId={workOrderAlert.id}
          initialEventType={workOrderAlert.severity === "CRITICAL" ? "PART_REPLACEMENT" : "INSPECTION"}
          initialDescription={`Maintenance triggered by alert ALT-${workOrderAlert.id}: ${workOrderAlert.message}`}
          onSuccess={(created) => {
            showToast(`Work order MNT-${created.id} scheduled for ${created.machine_id}.`);
            fetchAlerts();
          }}
        />
      )}

      {/* Operator Feedback Modal linked from Alert */}
      {feedbackAlert && (
        <OperatorFeedbackModal
          isOpen={Boolean(feedbackAlert)}
          onClose={() => setFeedbackAlert(null)}
          machineId={feedbackAlert.machine_id}
          alertId={feedbackAlert.id}
          predictedRiskBand={feedbackAlert.severity}
          failureProbability={
            feedbackAlert.trigger_conditions && typeof feedbackAlert.trigger_conditions.failure_probability === "number"
              ? feedbackAlert.trigger_conditions.failure_probability
              : null
          }
          onSuccess={(fb) => {
            showToast(`Ground-truth feedback logged for ${fb.machine_id} (ALT-${fb.alert_id}).`);
          }}
        />
      )}
    </div>
  );
};
