import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Wrench,
  Plus,
  RefreshCw,
  Search,
} from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/common/Card";
import { DataTable, Column } from "../components/common/DataTable";
import { EmptyState } from "../components/common/EmptyState";
import { LoadingState } from "../components/common/LoadingState";
import { ErrorState } from "../components/common/ErrorState";
import { Button } from "../components/common/Button";
import { RoleGate } from "../components/common/RoleGate";
import { MaintenanceItem } from "../types/maintenance";
import { api } from "../api/client";
import { formatDateTime } from "../utils/formatters";
import { PRIVILEGED_ROLES } from "../utils/rbac";
import { CreateWorkOrderModal } from "../components/maintenance/CreateWorkOrderModal";
import { UpdateWorkOrderModal } from "../components/maintenance/UpdateWorkOrderModal";

export const MaintenancePage: React.FC = () => {
  const navigate = useNavigate();

  const [items, setItems] = useState<MaintenanceItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [typeFilter, setTypeFilter] = useState<string>("ALL");
  const [searchMachine, setSearchMachine] = useState<string>("");

  // Modals
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<MaintenanceItem | null>(null);
  const [isUpdateOpen, setIsUpdateOpen] = useState(false);

  // Toast
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const fetchMaintenance = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.maintenance.list();
      setItems(data || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load maintenance events";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMaintenance();
  }, [fetchMaintenance]);

  const filtered = items.filter((item) => {
    if (statusFilter !== "ALL" && item.status !== statusFilter) return false;
    if (typeFilter !== "ALL" && item.event_type !== typeFilter) return false;
    if (searchMachine.trim() && !item.machine_id.toLowerCase().includes(searchMachine.trim().toLowerCase())) {
      return false;
    }
    return true;
  });

  const getStatusStyle = (st: string) => {
    switch (st) {
      case "COMPLETED":
        return { color: "var(--color-success)", bg: "var(--color-surface-raised)" };
      case "IN_PROGRESS":
        return { color: "var(--color-accent)", bg: "var(--color-surface-raised)" };
      case "CANCELLED":
        return { color: "var(--color-text-muted)", bg: "var(--color-surface-raised)" };
      case "SCHEDULED":
      default:
        return { color: "var(--color-warning)", bg: "var(--color-surface-raised)" };
    }
  };

  const columns: Column<MaintenanceItem>[] = [
    {
      key: "id",
      header: "Order ID",
      render: (m) => <span className="text-mono" style={{ fontWeight: 700 }}>MNT-{m.id}</span>,
    },
    {
      key: "machine_id",
      header: "Machine",
      render: (m) => (
        <button
          type="button"
          onClick={() => navigate(`/machines/${m.machine_id}`)}
          style={{
            background: "none",
            border: "none",
            padding: 0,
            cursor: "pointer",
            fontFamily: "var(--font-mono)",
            fontWeight: 600,
            color: "var(--color-accent)",
            textDecoration: "underline",
          }}
        >
          {m.machine_id}
        </button>
      ),
    },
    {
      key: "alert_id",
      header: "Linked Alert",
      render: (m) =>
        m.alert_id ? (
          <span className="text-mono" style={{ fontSize: "11px", color: "var(--color-warning)" }}>
            ALT-{m.alert_id}
          </span>
        ) : (
          <span style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>—</span>
        ),
    },
    {
      key: "event_type",
      header: "Action Type",
      render: (m) => (
        <span
          className="text-mono"
          style={{
            fontSize: "11px",
            fontWeight: 600,
            padding: "2px 6px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--color-surface-raised)",
            border: "1px solid var(--color-border-subtle)",
            color: "var(--color-text-primary)",
          }}
        >
          {m.event_type}
        </span>
      ),
    },
    {
      key: "description",
      header: "Description / Scope",
      render: (m) => (
        <span style={{ color: "var(--color-text-secondary)", fontSize: "12px", maxWidth: "260px", display: "inline-block" }}>
          {m.description}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (m) => {
        const style = getStatusStyle(m.status);
        return (
          <span
            style={{
              fontSize: "11px",
              fontWeight: 700,
              padding: "2px 7px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: style.bg,
              color: style.color,
              border: `1px solid ${style.color}`,
            }}
          >
            {m.status}
          </span>
        );
      },
    },
    {
      key: "technician",
      header: "Technician",
      render: (m) => (
        <span style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>
          {m.technician || "Unassigned"}
        </span>
      ),
    },
    {
      key: "created_at",
      header: "Created",
      render: (m) => (
        <span className="text-mono" style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
          {formatDateTime(m.created_at)}
        </span>
      ),
    },
    {
      key: "action",
      header: "Actions",
      render: (m) => (
        <RoleGate
          allowedRoles={PRIVILEGED_ROLES}
          fallback={<span style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>View Only</span>}
        >
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              setSelectedItem(m);
              setIsUpdateOpen(true);
            }}
          >
            Update
          </Button>
        </RoleGate>
      ),
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
        title="Maintenance Workflow & Work Orders"
        description="Prescriptive maintenance actions, scheduled work orders, technician dispatch, and execution audit history."
        actions={
          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<RefreshCw size={14} />}
              onClick={fetchMaintenance}
            >
              Refresh
            </Button>
            <RoleGate allowedRoles={PRIVILEGED_ROLES}>
              <Button
                variant="primary"
                size="sm"
                leftIcon={<Plus size={14} />}
                onClick={() => setIsCreateOpen(true)}
              >
                Create Work Order
              </Button>
            </RoleGate>
          </div>
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
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", flexWrap: "wrap" }}>
          <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-muted)" }}>STATUS:</span>
          {["ALL", "SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED"].map((st) => (
            <Button
              key={st}
              variant={statusFilter === st ? "primary" : "secondary"}
              size="sm"
              onClick={() => setStatusFilter(st)}
            >
              {st}
            </Button>
          ))}
        </div>

        {/* Action Type Filters */}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", flexWrap: "wrap" }}>
          <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-muted)" }}>TYPE:</span>
          {["ALL", "INSPECTION", "PART_REPLACEMENT", "OVERHAUL", "LUBRICATION", "CALIBRATION"].map((tp) => (
            <Button
              key={tp}
              variant={typeFilter === tp ? "primary" : "secondary"}
              size="sm"
              onClick={() => setTypeFilter(tp)}
            >
              {tp}
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

      {/* Main Table */}
      <Card title="Work Orders & Service Records" subtitle={`Showing ${filtered.length} of ${items.length} work order(s)`}>
        {isLoading ? (
          <LoadingState message="Fetching maintenance work orders..." />
        ) : error ? (
          <ErrorState message={error} onRetry={fetchMaintenance} />
        ) : filtered.length === 0 ? (
          <EmptyState
            title="No matching work orders"
            description="No scheduled or active maintenance work orders match the current criteria."
            icon={<Wrench size={24} />}
          />
        ) : (
          <DataTable
            columns={columns}
            data={filtered}
            keyExtractor={(m) => m.id}
          />
        )}
      </Card>

      {/* Create Work Order Modal */}
      <CreateWorkOrderModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onSuccess={(created) => {
          showToast(`Work order MNT-${created.id} scheduled for ${created.machine_id}.`);
          fetchMaintenance();
        }}
      />

      {/* Update Work Order Modal */}
      {selectedItem && (
        <UpdateWorkOrderModal
          isOpen={isUpdateOpen}
          onClose={() => setIsUpdateOpen(false)}
          item={selectedItem}
          onSuccess={(updated) => {
            showToast(`Work order MNT-${updated.id} updated (${updated.status}).`);
            fetchMaintenance();
          }}
        />
      )}
    </div>
  );
};
