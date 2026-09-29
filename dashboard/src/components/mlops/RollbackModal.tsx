import React, { useState, useEffect } from "react";
import { RotateCcw, AlertTriangle, CheckCircle2, ShieldAlert } from "lucide-react";
import { Modal } from "../common/Modal";
import { Button } from "../common/Button";
import { api } from "../../api/client";
import { ModelVersionSummary, RollbackResult } from "../../types/mlops";

export interface RollbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  versions: ModelVersionSummary[];
  currentChampionVersion?: string | null;
  onSuccess?: (result: RollbackResult) => void;
}

export const RollbackModal: React.FC<RollbackModalProps> = ({
  isOpen,
  onClose,
  versions,
  currentChampionVersion,
  onSuccess,
}) => {
  const eligibleVersions = versions.filter((v) => v.version !== currentChampionVersion);
  const [targetVersion, setTargetVersion] = useState<string>(
    eligibleVersions.length > 0 ? eligibleVersions[eligibleVersions.length - 1].version : ""
  );
  const [reason, setReason] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successResult, setSuccessResult] = useState<RollbackResult | null>(null);

  useEffect(() => {
    if (isOpen) {
      const filtered = versions.filter((v) => v.version !== currentChampionVersion);
      if (filtered.length > 0 && !targetVersion) {
        setTargetVersion(filtered[filtered.length - 1].version);
      }
      setReason("");
      setErrorMessage(null);
      setSuccessResult(null);
      setIsSubmitting(false);
    }
  }, [isOpen, versions, currentChampionVersion]);

  const handleClose = () => {
    setReason("");
    setErrorMessage(null);
    setSuccessResult(null);
    setIsSubmitting(false);
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!targetVersion) {
      setErrorMessage("Please select a target model version to restore.");
      return;
    }

    if (!reason.trim() || reason.trim().length < 10) {
      setErrorMessage("Rollback reason must be at least 10 characters long.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const result = await api.retrain.rollback({
        target_version: targetVersion,
        reason: reason.trim(),
      });
      setSuccessResult(result);
      if (onSuccess) {
        onSuccess(result);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to execute model rollback.";
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Safe Model Rollback"
    >
      {successResult ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)", padding: "var(--space-2)" }}>
          <div
            style={{
              padding: "var(--space-3)",
              backgroundColor: "rgba(19, 239, 149, 0.1)",
              border: "1px solid rgba(19, 239, 149, 0.3)",
              borderRadius: "var(--radius-sm)",
              display: "flex",
              alignItems: "center",
              gap: "var(--space-3)",
            }}
          >
            <CheckCircle2 size={24} color="var(--color-success)" style={{ flexShrink: 0 }} />
            <div>
              <div style={{ fontWeight: 600, color: "var(--color-success)" }}>
                Champion Restored: v{successResult.restored_champion_version}
              </div>
              <div style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
                Demoted version: v{successResult.demoted_version} | Actor: {successResult.actor}
              </div>
            </div>
          </div>

          <div style={{ fontSize: "12px", color: "var(--color-text-secondary)", lineHeight: 1.4 }}>
            The <code>champion</code> alias was successfully reassigned to version {successResult.restored_champion_version}. All operational inference will now route to this restored version.
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "var(--space-2)", marginTop: "var(--space-2)" }}>
            <Button variant="primary" onClick={handleClose}>
              Done
            </Button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          <div
            style={{
              padding: "var(--space-3)",
              backgroundColor: "rgba(254, 117, 14, 0.08)",
              border: "1px solid rgba(254, 117, 14, 0.25)",
              borderRadius: "var(--radius-sm)",
              display: "flex",
              gap: "var(--space-2)",
              alignItems: "flex-start",
            }}
          >
            <ShieldAlert size={18} color="var(--color-warning)" style={{ flexShrink: 0, marginTop: "2px" }} />
            <div style={{ fontSize: "12px", color: "var(--color-text-secondary)", lineHeight: 1.4 }}>
              <strong>Safe Non-Destructive Operation:</strong> Rollback reassigns the <code>champion</code> alias in MLflow. No model artifacts or weights are deleted. Full audit logging is recorded.
            </div>
          </div>

          {errorMessage && (
            <div
              style={{
                padding: "var(--space-3)",
                backgroundColor: "rgba(239, 68, 68, 0.1)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                borderRadius: "var(--radius-sm)",
                color: "var(--color-danger)",
                fontSize: "13px",
                display: "flex",
                gap: "var(--space-2)",
                alignItems: "center",
              }}
            >
              <AlertTriangle size={16} />
              <span>{errorMessage}</span>
            </div>
          )}

          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--color-text-primary)", marginBottom: "var(--space-1)" }}>
              Target Model Version to Restore
            </label>
            <select
              value={targetVersion}
              onChange={(e) => setTargetVersion(e.target.value)}
              style={{
                width: "100%",
                padding: "8px 12px",
                backgroundColor: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                color: "var(--color-text-primary)",
                fontSize: "13px",
              }}
            >
              {eligibleVersions.map((v) => (
                <option key={v.version} value={v.version}>
                  Version {v.version} {v.aliases.length > 0 ? `(${v.aliases.join(", ")})` : ""} {v.val_recall_at_t_star ? `— Recall ${(v.val_recall_at_t_star * 100).toFixed(1)}%` : ""}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--color-text-primary)", marginBottom: "var(--space-1)" }}>
              Mandatory Reason for Rollback (min 10 characters)
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Incident INC-0012: false alarm increase following operational shift on Motor-1002"
              rows={3}
              style={{
                width: "100%",
                padding: "8px 12px",
                backgroundColor: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                color: "var(--color-text-primary)",
                fontSize: "13px",
                resize: "vertical",
              }}
            />
            <div style={{ fontSize: "11px", color: "var(--color-text-muted)", marginTop: "4px" }}>
              {reason.trim().length}/10 characters minimum
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "var(--space-2)", marginTop: "var(--space-2)" }}>
            <Button variant="ghost" onClick={handleClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button
              variant="danger"
              type="submit"
              disabled={isSubmitting || reason.trim().length < 10}
            >
              <RotateCcw size={14} style={{ marginRight: "6px" }} />
              {isSubmitting ? "Rolling Back..." : "Execute Rollback"}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
};
