import React, { useState, useEffect, useCallback } from "react";
import {
  RefreshCw,
  Play,
  RotateCcw,
} from "lucide-react";
import { Card } from "../common/Card";
import { Button } from "../common/Button";
import { DataTable, Column } from "../common/DataTable";
import { LoadingState } from "../common/LoadingState";
import { ErrorState } from "../common/ErrorState";
import { RoleGate } from "../common/RoleGate";
import { ADMIN_ONLY, PRIVILEGED_ROLES } from "../../utils/rbac";
import { api } from "../../api/client";
import {
  ModelRegistry,
  ModelVersionSummary,
  PromotionGate,
  AuditLog,
  AuditLogEntry,
} from "../../types/mlops";
import { formatDateTime } from "../../utils/formatters";
import { PromotionGateCard } from "./PromotionGateCard";
import { RetrainJobModal } from "./RetrainJobModal";
import { RollbackModal } from "./RollbackModal";

export const ModelLifecyclePanel: React.FC = () => {
  const [registry, setRegistry] = useState<ModelRegistry | null>(null);
  const [gate, setGate] = useState<PromotionGate | null>(null);
  const [auditLog, setAuditLog] = useState<AuditLog | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Modals state
  const [isRetrainModalOpen, setIsRetrainModalOpen] = useState<boolean>(false);
  const [isRollbackModalOpen, setIsRollbackModalOpen] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 5000);
  };

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [regData, auditData] = await Promise.all([
        api.retrain.getRegistry(),
        api.retrain.getAuditLog({ limit: 50 }),
      ]);
      setRegistry(regData);
      setAuditLog(auditData);

      // Attempt to load gate (might fail if no challenger exists)
      try {
        const gateData = await api.retrain.getGate();
        setGate(gateData);
      } catch {
        setGate(null);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load model lifecycle data.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Registry columns
  const registryColumns: Column<ModelVersionSummary>[] = [
    {
      key: "version",
      header: "Version",
      render: (v) => (
        <span style={{ fontWeight: 700, fontFamily: "var(--font-mono)" }}>
          v{v.version}
        </span>
      ),
    },
    {
      key: "aliases",
      header: "Aliases & Status",
      render: (v) => (
        <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
          {v.aliases.map((alias) => {
            const isChamp = alias === "champion";
            const isChall = alias === "challenger";
            return (
              <span
                key={alias}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  padding: "2px 8px",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "11px",
                  fontWeight: 700,
                  backgroundColor: isChamp
                    ? "rgba(20, 154, 251, 0.15)"
                    : isChall
                    ? "rgba(168, 85, 247, 0.15)"
                    : "rgba(113, 113, 122, 0.15)",
                  color: isChamp
                    ? "var(--color-accent)"
                    : isChall
                    ? "#A855F7"
                    : "var(--color-text-muted)",
                  border: `1px solid ${
                    isChamp
                      ? "rgba(20, 154, 251, 0.3)"
                      : isChall
                      ? "rgba(168, 85, 247, 0.3)"
                      : "rgba(113, 113, 122, 0.3)"
                  }`,
                }}
              >
                ● {alias.toUpperCase()}
              </span>
            );
          })}
          {v.aliases.length === 0 && (
            <span style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
              Archived
            </span>
          )}
        </div>
      ),
    },
    {
      key: "val_recall_at_t_star",
      header: "Val Recall (t*=0.160)",
      render: (v) => (
        <span style={{ fontFamily: "var(--font-mono)" }}>
          {v.val_recall_at_t_star !== null && v.val_recall_at_t_star !== undefined
            ? `${(v.val_recall_at_t_star * 100).toFixed(1)}%`
            : "—"}
        </span>
      ),
    },
    {
      key: "val_precision_at_t_star",
      header: "Val Precision",
      render: (v) => (
        <span style={{ fontFamily: "var(--font-mono)" }}>
          {v.val_precision_at_t_star !== null && v.val_precision_at_t_star !== undefined
            ? `${(v.val_precision_at_t_star * 100).toFixed(1)}%`
            : "—"}
        </span>
      ),
    },
    {
      key: "val_pr_auc",
      header: "Val PR-AUC",
      render: (v) => (
        <span style={{ fontFamily: "var(--font-mono)" }}>
          {v.val_pr_auc !== null && v.val_pr_auc !== undefined
            ? v.val_pr_auc.toFixed(4)
            : "—"}
        </span>
      ),
    },
    {
      key: "created_at",
      header: "Registered",
      render: (v) => (
        <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
          {v.created_at ? formatDateTime(new Date(v.created_at).toISOString()) : "—"}
        </span>
      ),
    },
  ];

  // Audit log columns
  const auditColumns: Column<AuditLogEntry>[] = [
    {
      key: "event",
      header: "Event",
      render: (entry) => {
        let badgeColor = "var(--color-text-muted)";
        let bgColor = "rgba(113, 113, 122, 0.15)";
        if (entry.event.includes("completed") || entry.event.includes("promoted")) {
          badgeColor = "var(--color-success)";
          bgColor = "rgba(19, 239, 149, 0.12)";
        } else if (entry.event.includes("failed")) {
          badgeColor = "var(--color-danger)";
          bgColor = "rgba(239, 68, 68, 0.12)";
        } else if (entry.event.includes("rollback")) {
          badgeColor = "var(--color-warning)";
          bgColor = "rgba(254, 117, 14, 0.12)";
        }

        return (
          <span
            style={{
              padding: "2px 8px",
              borderRadius: "var(--radius-sm)",
              fontSize: "11px",
              fontWeight: 600,
              backgroundColor: bgColor,
              color: badgeColor,
            }}
          >
            {entry.event}
          </span>
        );
      },
    },
    {
      key: "actor",
      header: "Actor",
      render: (entry) => (
        <span style={{ fontWeight: 600, fontSize: "12px" }}>{entry.actor}</span>
      ),
    },
    {
      key: "challenger_version",
      header: "Version",
      render: (entry) => (
        <span style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>
          {entry.challenger_version ? `v${entry.challenger_version}` : "—"}
        </span>
      ),
    },
    {
      key: "notes",
      header: "Details / Notes",
      render: (entry) => (
        <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
          {entry.notes || entry.error || "—"}
        </span>
      ),
    },
    {
      key: "timestamp",
      header: "Timestamp",
      render: (entry) => (
        <span style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
          {formatDateTime(entry.timestamp)}
        </span>
      ),
    },
  ];

  if (isLoading && !registry) {
    return <LoadingState message="Loading model lifecycle and registry..." />;
  }

  if (error && !registry) {
    return <ErrorState message={error} onRetry={fetchData} />;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      {/* Toast Notification */}
      {toastMessage && (
        <div
          style={{
            position: "fixed",
            bottom: "24px",
            right: "24px",
            padding: "12px 18px",
            backgroundColor: "var(--color-surface)",
            border: "1px solid var(--color-success)",
            borderRadius: "var(--radius-sm)",
            color: "var(--color-success)",
            fontSize: "13px",
            fontWeight: 600,
            boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
            zIndex: 1000,
          }}
        >
          ● {toastMessage}
        </div>
      )}

      {/* Action Header Strip */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "var(--space-3)",
          padding: "var(--space-3) var(--space-4)",
          backgroundColor: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-md)",
        }}
      >
        <div>
          <div style={{ fontSize: "14px", fontWeight: 700, color: "var(--color-text-primary)" }}>
            Model Governance & Promotion Controls
          </div>
          <div style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>
            Registered model: <code>{registry?.model_name || "edgetwin-risk"}</code> | Champion: v{registry?.champion_version || "—"} | Challenger: {registry?.challenger_version ? `v${registry.challenger_version}` : "None"}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
          <Button variant="ghost" size="sm" onClick={fetchData} disabled={isLoading}>
            <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} style={{ marginRight: "6px" }} />
            Refresh
          </Button>

          <RoleGate allowedRoles={PRIVILEGED_ROLES}>
            <Button variant="secondary" size="sm" onClick={() => setIsRetrainModalOpen(true)}>
              <Play size={14} style={{ marginRight: "6px" }} />
              Initiate Retrain Job
            </Button>
          </RoleGate>

          <RoleGate allowedRoles={ADMIN_ONLY}>
            <Button
              variant="danger"
              size="sm"
              onClick={() => setIsRollbackModalOpen(true)}
              disabled={!registry || registry.versions.length <= 1}
            >
              <RotateCcw size={14} style={{ marginRight: "6px" }} />
              Rollback Champion
            </Button>
          </RoleGate>
        </div>
      </div>

      {/* Promotion Gate Card */}
      <PromotionGateCard
        gate={gate}
        isLoading={isLoading}
        onRefresh={fetchData}
        onPromoted={(res) => showToast(`Successfully promoted v${res.new_champion_version} to champion.`)}
      />

      {/* Model Registry Version History */}
      <Card
        title="Model Registry Version History"
        subtitle={`All versions registered under '${registry?.model_name || "edgetwin-risk"}' in MLflow`}
      >
        <DataTable
          columns={registryColumns}
          data={registry?.versions || []}
          keyExtractor={(v) => v.version}
          emptyMessage="No model versions found in registry."
        />
      </Card>

      {/* Retraining & Promotion Audit Trail */}
      <Card
        title="Retraining & Promotion Audit Trail"
        subtitle="Append-only immutable audit log of all retrain, promotion, and rollback actions"
      >
        <DataTable
          columns={auditColumns}
          data={auditLog?.entries || []}
          keyExtractor={(e, idx) => `${e.timestamp}-${idx}`}
          emptyMessage="No audit log entries recorded yet."
        />
      </Card>

      {/* Retrain Job Modal */}
      <RetrainJobModal
        isOpen={isRetrainModalOpen}
        onClose={() => setIsRetrainModalOpen(false)}
        onSuccess={(result) => {
          showToast(`Retraining completed: challenger v${result.challenger_version} registered.`);
          fetchData();
        }}
      />

      {/* Rollback Modal */}
      <RollbackModal
        isOpen={isRollbackModalOpen}
        onClose={() => setIsRollbackModalOpen(false)}
        versions={registry?.versions || []}
        currentChampionVersion={registry?.champion_version}
        onSuccess={(result) => {
          showToast(`Rollback complete: champion restored to v${result.restored_champion_version}.`);
          fetchData();
        }}
      />
    </div>
  );
};
