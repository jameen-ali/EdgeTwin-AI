import React, { useState, useEffect, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Cpu,
  Activity,
  AlertTriangle,
  ShieldCheck,
  RefreshCw,
  Search,
  LayoutGrid,
  LayoutList,
  CheckCircle2,
  SlidersHorizontal,
  ExternalLink,
  X,
} from "lucide-react";
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
import { Input } from "../components/common/Input";
import { Select } from "../components/common/Select";
import { RoleGate } from "../components/common/RoleGate";
import { Toast } from "../components/common/Toast";
import { LiveIndicator } from "../components/common/LiveIndicator";
import { MachineSummary, normalizeMachine } from "../types/machine";
import { AlertItem } from "../types/alert";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useTwinWebSocket } from "../hooks/useTwinWebSocket";
import { formatNumber, formatPercent, formatDateTime, formatTimeAgo } from "../utils/formatters";
import { PRIVILEGED_ROLES } from "../utils/rbac";

type FilterStatus = "ALL" | "ATTENTION" | "HEALTHY" | "TRIPPED" | "OFFLINE";
type SortOption = "RISK_DESC" | "HEALTH_ASC" | "ID_ASC";
type ViewMode = "TABLE" | "CARDS";

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { token } = useAuth();

  const [rawMachines, setRawMachines] = useState<MachineSummary[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filter & View State
  const [search, setSearch] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<FilterStatus>("ALL");
  const [sortBy, setSortBy] = useState<SortOption>("RISK_DESC");
  const [viewMode, setViewMode] = useState<ViewMode>("TABLE");

  // Interaction State
  const [acknowledgingIds, setAcknowledgingIds] = useState<Record<number, boolean>>({});
  const [toast, setToast] = useState<{ title: string; message?: string; type: "success" | "danger" | "info" } | null>(null);

  // Real-time WebSocket Subscription
  const { twins, isConnected: isWsConnected } = useTwinWebSocket({ token });

  // Fetch machines and active alerts concurrently
  const fetchFleetData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [machinesData, alertsData] = await Promise.all([
        api.machines.list(),
        api.alerts.list({ active_only: true, limit: 20 }),
      ]);
      setRawMachines(machinesData || []);
      setAlerts(alertsData || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load fleet telemetry.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFleetData();
  }, [fetchFleetData]);

  // Merge live twin updates into the machine list
  const displayMachines = useMemo(() => {
    return rawMachines.map((m) => normalizeMachine(m, twins[m.machine_id]));
  }, [rawMachines, twins]);

  // Fleet KPIs
  const totalMachines = displayMachines.length;
  const activeRunningCount = displayMachines.filter((m) => m.operating_state === "RUNNING").length;
  const trippedCount = displayMachines.filter((m) => m.operating_state === "TRIPPED").length;
  const healthyCount = displayMachines.filter((m) => m.health_state === "HEALTHY").length;
  const warningCount = displayMachines.filter((m) => m.health_state === "WARNING").length;
  const criticalCount = displayMachines.filter((m) => m.health_state === "CRITICAL").length;
  const offlineCount = displayMachines.filter(
    (m) => m.health_state === "OFFLINE" || m.connectivity_state === "OFFLINE"
  ).length;

  const attentionNeededCount = displayMachines.filter(
    (m) => m.health_state !== "HEALTHY" || m.operating_state === "TRIPPED" || m.failure_probability > 0.16
  ).length;

  const averageHealth = totalMachines > 0
    ? displayMachines.reduce((acc, m) => acc + m.health_score, 0) / totalMachines
    : null;

  const activeAlerts = useMemo(() => {
    return alerts.filter((a) => a.status === "ACTIVE" || a.status === "OPEN");
  }, [alerts]);

  // Filter & Search Logic
  const filteredMachines = useMemo(() => {
    return displayMachines
      .filter((m) => {
        // Status filter
        if (statusFilter === "ATTENTION") {
          const needsAttention =
            m.health_state !== "HEALTHY" || m.operating_state === "TRIPPED" || m.failure_probability > 0.16;
          if (!needsAttention) return false;
        } else if (statusFilter === "HEALTHY") {
          if (m.health_state !== "HEALTHY") return false;
        } else if (statusFilter === "TRIPPED") {
          if (m.operating_state !== "TRIPPED") return false;
        } else if (statusFilter === "OFFLINE") {
          if (m.health_state !== "OFFLINE" && m.connectivity_state !== "OFFLINE") return false;
        }

        // Search query
        if (search.trim()) {
          const query = search.trim().toLowerCase();
          const matchId = m.machine_id.toLowerCase().includes(query);
          const matchType = m.machine_type.toLowerCase().includes(query);
          const matchLocation = (m.location || "").toLowerCase().includes(query);
          if (!matchId && !matchType && !matchLocation) return false;
        }

        return true;
      })
      .sort((a, b) => {
        if (sortBy === "RISK_DESC") {
          if (b.failure_probability !== a.failure_probability) {
            return b.failure_probability - a.failure_probability;
          }
          return a.health_score - b.health_score;
        }
        if (sortBy === "HEALTH_ASC") {
          return a.health_score - b.health_score;
        }
        if (sortBy === "ID_ASC") {
          return a.machine_id.localeCompare(b.machine_id);
        }
        return 0;
      });
  }, [displayMachines, statusFilter, search, sortBy]);

  // Alert Acknowledgment
  const handleAcknowledgeAlert = async (alertId: number) => {
    setAcknowledgingIds((prev) => ({ ...prev, [alertId]: true }));
    try {
      await api.alerts.acknowledge(alertId);
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? { ...a, status: "ACKNOWLEDGED" } : a))
      );
      setToast({
        title: "Alert Acknowledged",
        message: `Alert ALT-${alertId} marked as acknowledged.`,
        type: "success",
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to acknowledge alert.";
      setToast({
        title: "Acknowledgment Failed",
        message: msg,
        type: "danger",
      });
    } finally {
      setAcknowledgingIds((prev) => ({ ...prev, [alertId]: false }));
    }
  };

  // Table Columns Definition
  const columns: Column<ReturnType<typeof normalizeMachine>>[] = [
    {
      key: "machine_id",
      header: "Machine Asset",
      render: (m) => (
        <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
          <span
            className="text-mono"
            style={{
              fontWeight: 700,
              fontSize: "13px",
              color: "var(--color-accent)",
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
          >
            {m.machine_id}
          </span>
          <span style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
            {m.location}
          </span>
        </div>
      ),
    },
    {
      key: "machine_type",
      header: "Equipment Type",
      render: (m) => (
        <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
          {m.machine_type}
        </span>
      ),
    },
    {
      key: "operating_state",
      header: "Operating State",
      render: (m) => <StatusBadge status={m.operating_state} size="sm" />,
    },
    {
      key: "connectivity_state",
      header: "Twin Sync",
      render: (m) => <StatusBadge status={m.connectivity_state} size="sm" />,
    },
    {
      key: "health_state",
      header: "Health State",
      render: (m) => <HealthBadge state={m.health_state} size="sm" />,
    },
    {
      key: "health_score",
      header: "Health Index",
      align: "right",
      render: (m) => {
        let barColor = "var(--color-success)";
        if (m.health_score < 60) barColor = "var(--color-danger)";
        else if (m.health_score < 80) barColor = "var(--color-warning)";

        return (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "4px" }}>
            <span className="text-mono" style={{ fontWeight: 700, fontSize: "13px" }}>
              {formatNumber(m.health_score, 1)}
            </span>
            <div
              style={{
                width: "60px",
                height: "3px",
                backgroundColor: "var(--color-border-subtle)",
                borderRadius: "var(--radius-full)",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${Math.min(100, Math.max(0, m.health_score))}%`,
                  height: "100%",
                  backgroundColor: barColor,
                  transition: "width 0.3s ease",
                }}
              />
            </div>
          </div>
        );
      },
    },
    {
      key: "failure_probability",
      header: "Failure Risk (t*=0.16)",
      align: "right",
      render: (m) => {
        const isElevated = m.failure_probability > 0.16;
        return (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "2px" }}>
            <span
              className="text-mono"
              style={{
                fontWeight: 700,
                fontSize: "13px",
                color: isElevated ? "var(--color-warning)" : "var(--color-text-primary)",
              }}
            >
              {formatPercent(m.failure_probability)}
            </span>
            <span
              style={{
                fontSize: "10px",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "var(--tracking-wide)",
                color: isElevated ? "var(--color-warning)" : "var(--color-text-muted)",
              }}
            >
              {m.risk_band} RISK
            </span>
          </div>
        );
      },
    },
    {
      key: "last_telemetry_at",
      header: "Freshness",
      render: (m) => (
        <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
          <span className="text-mono" style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
            {formatTimeAgo(m.last_telemetry_at)}
          </span>
          <span className="text-mono" style={{ fontSize: "10px", color: "var(--color-text-muted)" }}>
            {m.last_telemetry_at ? formatDateTime(m.last_telemetry_at).slice(11) : "—"}
          </span>
        </div>
      ),
    },
    {
      key: "action",
      header: "Action",
      align: "right",
      render: (m) => (
        <Button
          variant="ghost"
          size="sm"
          rightIcon={<ExternalLink size={12} />}
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/machines?id=${encodeURIComponent(m.machine_id)}`);
          }}
        >
          Inspect
        </Button>
      ),
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      {/* Floating Feedback Toast */}
      {toast && (
        <div
          style={{
            position: "fixed",
            bottom: "var(--space-6)",
            right: "var(--space-6)",
            zIndex: 9999,
          }}
        >
          <Toast
            type={toast.type}
            title={toast.title}
            message={toast.message}
            onClose={() => setToast(null)}
          />
        </div>
      )}

      {/* Page Header */}
      <PageHeader
        title="Fleet Overview"
        description="Real-time telemetry, Digital Twin synchronization, and predictive health monitoring for industrial machine assets."
        actions={
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
            {/* Live WebSocket Connection Pill */}
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "4px 10px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                fontSize: "11px",
                fontWeight: 600,
                letterSpacing: "var(--tracking-wide)",
                color: isWsConnected ? "var(--color-accent)" : "var(--color-text-muted)",
              }}
            >
              <LiveIndicator isLive={isWsConnected} label={isWsConnected ? "LIVE TWIN STREAM (1 Hz)" : "REST POLLING"} />
            </div>

            {/* View Mode Toggle */}
            <div
              style={{
                display: "flex",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
                backgroundColor: "var(--color-surface)",
                overflow: "hidden",
              }}
            >
              <button
                type="button"
                onClick={() => setViewMode("TABLE")}
                title="Table view"
                style={{
                  padding: "6px 10px",
                  border: "none",
                  backgroundColor: viewMode === "TABLE" ? "var(--color-surface-raised)" : "transparent",
                  color: viewMode === "TABLE" ? "var(--color-accent)" : "var(--color-text-muted)",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                }}
              >
                <LayoutList size={14} />
              </button>
              <button
                type="button"
                onClick={() => setViewMode("CARDS")}
                title="Cards view"
                style={{
                  padding: "6px 10px",
                  border: "none",
                  backgroundColor: viewMode === "CARDS" ? "var(--color-surface-raised)" : "transparent",
                  color: viewMode === "CARDS" ? "var(--color-accent)" : "var(--color-text-muted)",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                }}
              >
                <LayoutGrid size={14} />
              </button>
            </div>

            {/* Refresh Fleet Trigger */}
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<RefreshCw size={14} className={isLoading ? "spin" : ""} />}
              onClick={fetchFleetData}
              disabled={isLoading}
            >
              Refresh
            </Button>
          </div>
        }
      />

      {/* Level 1: Major Operational Fleet KPIs */}
      <MetricGrid columns={4}>
        <Metric
          label="Total Machines"
          value={totalMachines}
          unit="units"
          icon={<Cpu size={18} />}
          delta={{
            value: `${activeRunningCount} running`,
            isPositive: activeRunningCount === totalMachines && totalMachines > 0,
            label: `· ${trippedCount} tripped`,
          }}
        />

        <Metric
          label="Active Running"
          value={activeRunningCount}
          unit="online"
          status={activeRunningCount > 0 ? "success" : "normal"}
          icon={<Activity size={18} />}
          delta={{
            value: totalMachines > 0 ? `${Math.round((activeRunningCount / totalMachines) * 100)}%` : "0%",
            isPositive: true,
            label: "fleet operational uptime",
          }}
        />

        <Metric
          label="Fleet Health"
          value={averageHealth !== null ? formatNumber(averageHealth, 1) : "—"}
          unit="/ 100"
          status={
            averageHealth !== null && averageHealth >= 80
              ? "success"
              : averageHealth !== null && averageHealth >= 60
              ? "warning"
              : "danger"
          }
          icon={<ShieldCheck size={18} />}
          delta={{
            value: "t* = 0.16",
            isPositive: true,
            label: "calibrated decision threshold",
          }}
        />

        <Metric
          label="Active Alarms"
          value={activeAlerts.length}
          unit="alarms"
          status={activeAlerts.length > 0 ? "danger" : "normal"}
          icon={<AlertTriangle size={18} />}
          delta={{
            value: `${criticalCount} crit · ${warningCount} warn`,
            isPositive: activeAlerts.length === 0,
            label: `· ${attentionNeededCount} need attention`,
          }}
        />
      </MetricGrid>

      {/* Level 2: Machine Fleet Directory Card */}
      <Card
        title="Machine Fleet Status"
        subtitle={
          isWsConnected
            ? `Live WebSocket twin synchronization active (1 Hz) · Showing ${filteredMachines.length} of ${totalMachines} asset(s)`
            : `Displaying cached telemetry from backend · Showing ${filteredMachines.length} of ${totalMachines} asset(s)`
        }
      >
        {/* Toolbar: Filters, Search & Sort */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "var(--space-3)",
            marginBottom: "var(--space-4)",
            paddingBottom: "var(--space-4)",
            borderBottom: "1px solid var(--color-border-subtle)",
          }}
        >
          {/* Status Filter Tabs */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
            <button
              type="button"
              onClick={() => setStatusFilter("ALL")}
              style={{
                padding: "4px 10px",
                borderRadius: "var(--radius-sm)",
                fontSize: "12px",
                fontWeight: 600,
                border: "1px solid var(--color-border)",
                backgroundColor: statusFilter === "ALL" ? "var(--color-surface-raised)" : "transparent",
                color: statusFilter === "ALL" ? "var(--color-text-primary)" : "var(--color-text-muted)",
                cursor: "pointer",
              }}
            >
              All ({totalMachines})
            </button>
            <button
              type="button"
              onClick={() => setStatusFilter("ATTENTION")}
              style={{
                padding: "4px 10px",
                borderRadius: "var(--radius-sm)",
                fontSize: "12px",
                fontWeight: 600,
                border: "1px solid",
                borderColor: attentionNeededCount > 0 ? "var(--color-warning-border)" : "var(--color-border)",
                backgroundColor: statusFilter === "ATTENTION" ? "var(--color-surface-raised)" : "transparent",
                color: attentionNeededCount > 0 ? "var(--color-warning)" : "var(--color-text-muted)",
                cursor: "pointer",
              }}
            >
              ▲ Attention Needed ({attentionNeededCount})
            </button>
            <button
              type="button"
              onClick={() => setStatusFilter("HEALTHY")}
              style={{
                padding: "4px 10px",
                borderRadius: "var(--radius-sm)",
                fontSize: "12px",
                fontWeight: 600,
                border: "1px solid var(--color-border)",
                backgroundColor: statusFilter === "HEALTHY" ? "var(--color-surface-raised)" : "transparent",
                color: statusFilter === "HEALTHY" ? "var(--color-success)" : "var(--color-text-muted)",
                cursor: "pointer",
              }}
            >
              ● Healthy ({healthyCount})
            </button>
            <button
              type="button"
              onClick={() => setStatusFilter("TRIPPED")}
              style={{
                padding: "4px 10px",
                borderRadius: "var(--radius-sm)",
                fontSize: "12px",
                fontWeight: 600,
                border: "1px solid var(--color-border)",
                backgroundColor: statusFilter === "TRIPPED" ? "var(--color-surface-raised)" : "transparent",
                color: trippedCount > 0 ? "var(--color-danger)" : "var(--color-text-muted)",
                cursor: "pointer",
              }}
            >
              ■ Tripped ({trippedCount})
            </button>
            <button
              type="button"
              onClick={() => setStatusFilter("OFFLINE")}
              style={{
                padding: "4px 10px",
                borderRadius: "var(--radius-sm)",
                fontSize: "12px",
                fontWeight: 600,
                border: "1px solid var(--color-border)",
                backgroundColor: statusFilter === "OFFLINE" ? "var(--color-surface-raised)" : "transparent",
                color: statusFilter === "OFFLINE" ? "var(--color-text-primary)" : "var(--color-text-muted)",
                cursor: "pointer",
              }}
            >
              ○ Offline ({offlineCount})
            </button>
          </div>

          {/* Search & Sort Controls */}
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", flexWrap: "wrap" }}>
            <div style={{ position: "relative", minWidth: "220px" }}>
              <Input
                placeholder="Search machine ID, type..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ paddingLeft: "32px", height: "32px", fontSize: "12px" }}
              />
              <Search
                size={14}
                style={{
                  position: "absolute",
                  left: "10px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "var(--color-text-muted)",
                  pointerEvents: "none",
                }}
              />
              {search && (
                <button
                  type="button"
                  onClick={() => setSearch("")}
                  style={{
                    position: "absolute",
                    right: "8px",
                    top: "50%",
                    transform: "translateY(-50%)",
                    background: "none",
                    border: "none",
                    color: "var(--color-text-muted)",
                    cursor: "pointer",
                    padding: 0,
                  }}
                >
                  <X size={12} />
                </button>
              )}
            </div>

            <div style={{ minWidth: "180px" }}>
              <Select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
                options={[
                  { value: "RISK_DESC", label: "Sort: Risk (Highest)" },
                  { value: "HEALTH_ASC", label: "Sort: Health (Lowest)" },
                  { value: "ID_ASC", label: "Sort: Machine ID (A-Z)" },
                ]}
                style={{ height: "32px", fontSize: "12px" }}
              />
            </div>
          </div>
        </div>

        {/* Directory Content */}
        {isLoading ? (
          <LoadingState message="Connecting to fleet telemetry service..." />
        ) : error ? (
          <ErrorState message={error} onRetry={fetchFleetData} />
        ) : totalMachines === 0 ? (
          <EmptyState
            title="No machines registered"
            description="No active machine assets were found in the database. Ensure the edge firmware simulation or backend seed script is running."
            icon={<Cpu size={24} />}
            action={
              <Button variant="secondary" size="sm" onClick={fetchFleetData}>
                Check Again
              </Button>
            }
          />
        ) : filteredMachines.length === 0 ? (
          <EmptyState
            title="No machines match criteria"
            description={`No assets match status filter "${statusFilter}" and search query "${search}".`}
            icon={<SlidersHorizontal size={24} />}
            action={
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setStatusFilter("ALL");
                  setSearch("");
                }}
              >
                Reset Filters
              </Button>
            }
          />
        ) : viewMode === "TABLE" ? (
          <DataTable
            columns={columns}
            data={filteredMachines}
            keyExtractor={(m) => m.machine_id}
            onRowClick={(m) => navigate(`/machines/${encodeURIComponent(m.machine_id)}`)}
          />
        ) : (
          /* Cards Grid View */
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: "var(--space-4)",
            }}
          >
            {filteredMachines.map((m) => {
              const isElevated = m.failure_probability > 0.16;
              let barColor = "var(--color-success)";
              if (m.health_score < 60) barColor = "var(--color-danger)";
              else if (m.health_score < 80) barColor = "var(--color-warning)";

              return (
                <div
                  key={m.machine_id}
                  onClick={() => navigate(`/machines/${encodeURIComponent(m.machine_id)}`)}
                  style={{
                    backgroundColor: "var(--color-surface)",
                    border: `1px solid ${isElevated ? "var(--color-warning-border)" : "var(--color-border)"}`,
                    borderRadius: "var(--radius-md)",
                    padding: "var(--space-4)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "var(--space-3)",
                    cursor: "pointer",
                    transition: "border-color var(--transition-fast), transform var(--transition-fast)",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = "var(--color-accent)";
                    e.currentTarget.style.transform = "translateY(-1px)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = isElevated
                      ? "var(--color-warning-border)"
                      : "var(--color-border)";
                    e.currentTarget.style.transform = "none";
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div>
                      <div
                        className="text-mono"
                        style={{ fontWeight: 700, fontSize: "14px", color: "var(--color-accent)" }}
                      >
                        {m.machine_id}
                      </div>
                      <div style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
                        {m.machine_type} · {m.location}
                      </div>
                    </div>
                    <HealthBadge state={m.health_state} size="sm" />
                  </div>

                  <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
                    <div>
                      <div style={{ fontSize: "11px", color: "var(--color-text-muted)", textTransform: "uppercase" }}>
                        Health Index
                      </div>
                      <div className="text-mono" style={{ fontSize: "22px", fontWeight: 700, color: barColor }}>
                        {formatNumber(m.health_score, 1)}
                        <span style={{ fontSize: "12px", color: "var(--color-text-muted)", fontWeight: 400 }}> / 100</span>
                      </div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: "11px", color: "var(--color-text-muted)", textTransform: "uppercase" }}>
                        Failure Risk
                      </div>
                      <div
                        className="text-mono"
                        style={{
                          fontSize: "18px",
                          fontWeight: 700,
                          color: isElevated ? "var(--color-warning)" : "var(--color-text-primary)",
                        }}
                      >
                        {formatPercent(m.failure_probability)}
                      </div>
                    </div>
                  </div>

                  {/* Health Meter Track */}
                  <div
                    style={{
                      width: "100%",
                      height: "4px",
                      backgroundColor: "var(--color-border-subtle)",
                      borderRadius: "var(--radius-full)",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: `${Math.min(100, Math.max(0, m.health_score))}%`,
                        height: "100%",
                        backgroundColor: barColor,
                      }}
                    />
                  </div>

                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      paddingTop: "var(--space-2)",
                      borderTop: "1px solid var(--color-border-subtle)",
                      fontSize: "11px",
                      color: "var(--color-text-muted)",
                    }}
                  >
                    <div style={{ display: "flex", gap: "6px" }}>
                      <StatusBadge status={m.operating_state} size="sm" />
                      <StatusBadge status={m.connectivity_state} size="sm" />
                    </div>
                    <span className="text-mono">{formatTimeAgo(m.last_telemetry_at)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* Level 3: Active Fleet Incidents & Alarms Ticker */}
      <Card
        title="Active Fleet Incidents & Alarms"
        subtitle={`Real-time L1–L6 deterministic rule excursions and ML anomaly detections (${activeAlerts.length} active)`}
        action={
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate("/alerts")}
            rightIcon={<ExternalLink size={12} />}
          >
            View All Alerts
          </Button>
        }
      >
        {activeAlerts.length === 0 ? (
          <div
            style={{
              padding: "var(--space-6) var(--space-4)",
              textAlign: "center",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "var(--space-2)",
            }}
          >
            <CheckCircle2 size={24} style={{ color: "var(--color-success)" }} />
            <div style={{ fontSize: "14px", fontWeight: 600, color: "var(--color-text-primary)" }}>
              Fleet Operations Normal
            </div>
            <div style={{ fontSize: "12px", color: "var(--color-text-muted)", maxWidth: "420px" }}>
              All monitored machine telemetry signals and failure risk predictions are currently operating within safe baseline limits.
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            {activeAlerts.map((alert) => {
              const isCrit = alert.severity === "CRITICAL";
              return (
                <div
                  key={alert.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "var(--space-3) var(--space-4)",
                    backgroundColor: "var(--color-surface-raised)",
                    border: `1px solid ${isCrit ? "var(--color-danger-border)" : "var(--color-border)"}`,
                    borderRadius: "var(--radius-md)",
                    gap: "var(--space-4)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: 700,
                        padding: "2px 6px",
                        borderRadius: "var(--radius-sm)",
                        backgroundColor: isCrit ? "var(--color-danger-subtle)" : "var(--color-warning-subtle)",
                        color: isCrit ? "var(--color-danger)" : "var(--color-warning)",
                        border: `1px solid ${isCrit ? "var(--color-danger-border)" : "var(--color-warning-border)"}`,
                        letterSpacing: "var(--tracking-wide)",
                      }}
                    >
                      {alert.severity}
                    </span>
                    <span
                      className="text-mono"
                      style={{
                        fontWeight: 700,
                        fontSize: "12px",
                        color: "var(--color-accent)",
                      }}
                    >
                      {alert.machine_id}
                    </span>
                    <span style={{ fontSize: "13px", color: "var(--color-text-secondary)" }}>
                      {alert.message}
                    </span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
                    <span className="text-mono" style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
                      {formatTimeAgo(alert.triggered_at || alert.created_at)}
                    </span>
                    <RoleGate allowedRoles={PRIVILEGED_ROLES}>
                      <Button
                        variant="secondary"
                        size="sm"
                        isLoading={acknowledgingIds[alert.id]}
                        onClick={() => handleAcknowledgeAlert(alert.id)}
                      >
                        Acknowledge
                      </Button>
                    </RoleGate>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* Level 4: Edge & MLOps Architecture Status Footer */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "var(--space-4)",
          padding: "var(--space-4) var(--space-5)",
          backgroundColor: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-lg)",
          fontSize: "12px",
        }}
      >
        <div>
          <span style={{ color: "var(--color-text-muted)", display: "block", fontSize: "10px", textTransform: "uppercase" }}>
            Inference Champion
          </span>
          <span className="text-mono" style={{ fontWeight: 600, color: "var(--color-text-primary)" }}>
            XGBoost v1.0 (t* = 0.16)
          </span>
        </div>
        <div>
          <span style={{ color: "var(--color-text-muted)", display: "block", fontSize: "10px", textTransform: "uppercase" }}>
            Health Engine
          </span>
          <span style={{ fontWeight: 600, color: "var(--color-text-primary)" }}>
            L1–L6 Rules + Hysteresis
          </span>
        </div>
        <div>
          <span style={{ color: "var(--color-text-muted)", display: "block", fontSize: "10px", textTransform: "uppercase" }}>
            Twin Stream
          </span>
          <span className="text-mono" style={{ fontWeight: 600, color: "var(--color-accent)" }}>
            /ws/live (1 Hz Push)
          </span>
        </div>
        <div>
          <span style={{ color: "var(--color-text-muted)", display: "block", fontSize: "10px", textTransform: "uppercase" }}>
            Safety Trips
          </span>
          <span style={{ fontWeight: 600, color: "var(--color-success)" }}>
            Hardware LWT & Ring Resync
          </span>
        </div>
      </div>
    </div>
  );
};
