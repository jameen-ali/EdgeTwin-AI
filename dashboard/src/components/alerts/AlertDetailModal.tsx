import React, { useState } from "react";
import {
  CheckCircle2,
  Wrench,
  MessageSquare,
  ExternalLink,
  ShieldCheck,
} from "lucide-react";
import { Modal } from "../common/Modal";
import { Button } from "../common/Button";
import { RoleGate } from "../common/RoleGate";
import { AlertItem } from "../../types/alert";
import { formatDateTime } from "../../utils/formatters";
import { PRIVILEGED_ROLES } from "../../utils/rbac";

export interface AlertDetailModalProps {
  alert: AlertItem | null;
  isOpen: boolean;
  onClose: () => void;
  onAcknowledge?: (alertId: number, notes?: string) => Promise<void>;
  onResolve?: (alertId: number, notes?: string) => Promise<void>;
  onCreateWorkOrder?: (alert: AlertItem) => void;
  onSubmitFeedback?: (alert: AlertItem) => void;
  onViewMachine?: (machineId: string) => void;
}

export const AlertDetailModal: React.FC<AlertDetailModalProps> = ({
  alert,
  isOpen,
  onClose,
  onAcknowledge,
  onResolve,
  onCreateWorkOrder,
  onSubmitFeedback,
  onViewMachine,
}) => {
  const [actionNotes, setActionNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!alert) return null;

  const isResolved = alert.status === "RESOLVED";
  const isAcknowledged = alert.status === "ACKNOWLEDGED" || isResolved;

  const getSeverityColor = (sev: string) => {
    if (sev === "CRITICAL") return "var(--color-danger)";
    if (sev === "WARNING") return "var(--color-warning)";
    return "var(--color-info)";
  };

  const getStatusColor = (st: string) => {
    if (st === "RESOLVED") return "var(--color-success)";
    if (st === "ACKNOWLEDGED") return "var(--color-info)";
    return "var(--color-warning)";
  };

  const handleAck = async () => {
    if (!onAcknowledge) return;
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await onAcknowledge(alert.id, actionNotes.trim() || undefined);
      setActionNotes("");
      onClose();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to acknowledge alert");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRes = async () => {
    if (!onResolve) return;
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await onResolve(alert.id, actionNotes.trim() || undefined);
      setActionNotes("");
      onClose();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to resolve alert");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Incident Investigation — ALT-${alert.id}`}
      maxWidth="620px"
      footer={
        <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap", width: "100%", justifyContent: "space-between" }}>
          <div>
            {onViewMachine && (
              <Button
                variant="secondary"
                size="sm"
                leftIcon={<ExternalLink size={14} />}
                onClick={() => {
                  onClose();
                  onViewMachine(alert.machine_id);
                }}
              >
                View Machine Twin
              </Button>
            )}
          </div>
          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            <Button variant="secondary" size="sm" onClick={onClose} disabled={isSubmitting}>
              Close
            </Button>
            <RoleGate allowedRoles={PRIVILEGED_ROLES}>
              {!isAcknowledged && (
                <Button
                  variant="primary"
                  size="sm"
                  leftIcon={<CheckCircle2 size={14} />}
                  onClick={handleAck}
                  disabled={isSubmitting}
                >
                  {isSubmitting ? "Updating..." : "Acknowledge"}
                </Button>
              )}
              {!isResolved && (
                <Button
                  variant="primary"
                  size="sm"
                  style={{ backgroundColor: "var(--color-success)", borderColor: "var(--color-success)" }}
                  leftIcon={<ShieldCheck size={14} />}
                  onClick={handleRes}
                  disabled={isSubmitting}
                >
                  {isSubmitting ? "Updating..." : "Resolve"}
                </Button>
              )}
            </RoleGate>
          </div>
        </div>
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
        {/* Error notification */}
        {errorMsg && (
          <div
            style={{
              padding: "var(--space-2) var(--space-3)",
              backgroundColor: "var(--color-danger-subtle)",
              border: "1px solid var(--color-danger-border)",
              borderRadius: "var(--radius-sm)",
              color: "var(--color-danger)",
              fontSize: "12px",
            }}
          >
            {errorMsg}
          </div>
        )}

        {/* Top Badges Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "var(--space-2)",
            paddingBottom: "var(--space-3)",
            borderBottom: "1px solid var(--color-border-subtle)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            <span
              style={{
                fontSize: "11px",
                fontWeight: 700,
                padding: "2px 8px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--color-surface-raised)",
                color: getSeverityColor(alert.severity),
                border: `1px solid ${getSeverityColor(alert.severity)}`,
              }}
            >
              {alert.severity}
            </span>
            <span
              style={{
                fontSize: "11px",
                fontWeight: 700,
                padding: "2px 8px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--color-surface-raised)",
                color: getStatusColor(alert.status),
                border: `1px solid ${getStatusColor(alert.status)}`,
              }}
            >
              {alert.status}
            </span>
          </div>

          <span className="text-mono" style={{ fontSize: "14px", fontWeight: 700, color: "var(--color-accent)" }}>
            {alert.machine_id}
          </span>
        </div>

        {/* Alert Summary / Message */}
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <span style={{ fontSize: "11px", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "var(--tracking-wider)" }}>
            Alert Message
          </span>
          <p style={{ margin: 0, fontSize: "14px", fontWeight: 500, color: "var(--color-text-primary)", lineHeight: 1.4 }}>
            {alert.message}
          </p>
        </div>

        {/* Metadata Grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "var(--space-3)",
            padding: "var(--space-3)",
            backgroundColor: "var(--color-surface-raised)",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--color-border-subtle)",
          }}
        >
          <div>
            <span style={{ fontSize: "10px", color: "var(--color-text-muted)", textTransform: "uppercase" }}>Type</span>
            <div className="text-mono" style={{ fontSize: "12px", color: "var(--color-text-primary)", marginTop: "2px" }}>
              {alert.alert_type || "ANOMALY"}
            </div>
          </div>
          <div>
            <span style={{ fontSize: "10px", color: "var(--color-text-muted)", textTransform: "uppercase" }}>Triggered At</span>
            <div className="text-mono" style={{ fontSize: "12px", color: "var(--color-text-secondary)", marginTop: "2px" }}>
              {formatDateTime(alert.triggered_at || alert.created_at)}
            </div>
          </div>
          {alert.acknowledged_at && (
            <div>
              <span style={{ fontSize: "10px", color: "var(--color-text-muted)", textTransform: "uppercase" }}>Acknowledged</span>
              <div className="text-mono" style={{ fontSize: "11px", color: "var(--color-text-secondary)", marginTop: "2px" }}>
                {formatDateTime(alert.acknowledged_at)}
              </div>
            </div>
          )}
          {alert.resolved_at && (
            <div>
              <span style={{ fontSize: "10px", color: "var(--color-text-muted)", textTransform: "uppercase" }}>Resolved By</span>
              <div className="text-mono" style={{ fontSize: "11px", color: "var(--color-success)", marginTop: "2px" }}>
                {alert.resolved_by || "System"} ({formatDateTime(alert.resolved_at)})
              </div>
            </div>
          )}
        </div>

        {/* Trigger Conditions */}
        {alert.trigger_conditions && Object.keys(alert.trigger_conditions).length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <span style={{ fontSize: "11px", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "var(--tracking-wider)" }}>
              Trigger Conditions
            </span>
            <div
              style={{
                backgroundColor: "var(--color-surface-raised)",
                padding: "var(--space-2) var(--space-3)",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border-subtle)",
                fontSize: "12px",
                display: "flex",
                flexWrap: "wrap",
                gap: "var(--space-3)",
              }}
            >
              {Object.entries(alert.trigger_conditions).map(([k, v]) => (
                <div key={k} style={{ display: "flex", gap: "4px" }}>
                  <span style={{ color: "var(--color-text-muted)" }}>{k}:</span>
                  <span className="text-mono" style={{ fontWeight: 600, color: "var(--color-text-primary)" }}>
                    {typeof v === "number" ? v.toFixed(3) : String(v)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Top Contributing SHAP Factors */}
        {alert.top_factors && alert.top_factors.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <span style={{ fontSize: "11px", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "var(--tracking-wider)" }}>
              Top Contributing Factors (SHAP)
            </span>
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              {alert.top_factors.map((f, i) => {
                const name = f.feature || f.factor || `Factor ${i + 1}`;
                const val = f.shap_value ?? f.contribution ?? 0;
                return (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      backgroundColor: "var(--color-surface-raised)",
                      padding: "4px 8px",
                      borderRadius: "var(--radius-sm)",
                      fontSize: "11px",
                    }}
                  >
                    <span style={{ color: "var(--color-text-secondary)" }}>{name}</span>
                    <span className="text-mono" style={{ fontWeight: 600, color: val > 0 ? "var(--color-danger)" : "var(--color-success)" }}>
                      {val > 0 ? `+${val.toFixed(3)}` : val.toFixed(3)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Workflow Action Buttons: Schedule Maintenance & Operator Feedback */}
        <div
          style={{
            display: "flex",
            gap: "var(--space-2)",
            marginTop: "var(--space-2)",
            paddingTop: "var(--space-3)",
            borderTop: "1px solid var(--color-border-subtle)",
            flexWrap: "wrap",
          }}
        >
          {onCreateWorkOrder && (
            <RoleGate allowedRoles={PRIVILEGED_ROLES}>
              <Button
                variant="secondary"
                size="sm"
                leftIcon={<Wrench size={14} />}
                onClick={() => {
                  onClose();
                  onCreateWorkOrder(alert);
                }}
              >
                Create Work Order
              </Button>
            </RoleGate>
          )}

          {onSubmitFeedback && (
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<MessageSquare size={14} />}
              onClick={() => {
                onClose();
                onSubmitFeedback(alert);
              }}
            >
              Record Outcome / Feedback
            </Button>
          )}
        </div>

        {/* Optional Action Notes input for Ack/Resolve */}
        {!isResolved && (
          <div style={{ display: "flex", flexDirection: "column", gap: "4px", marginTop: "var(--space-2)" }}>
            <label style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
              Action Notes (Optional):
            </label>
            <input
              type="text"
              value={actionNotes}
              onChange={(e) => setActionNotes(e.target.value)}
              placeholder="e.g. Verified sensor connection, scheduled lubrication inspection"
              style={{
                backgroundColor: "var(--color-surface-raised)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                padding: "6px 10px",
                color: "var(--color-text-primary)",
                fontSize: "12px",
              }}
            />
          </div>
        )}
      </div>
    </Modal>
  );
};
