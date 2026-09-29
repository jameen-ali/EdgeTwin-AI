import React, { useState } from "react";
import { Play, ShieldAlert, CheckCircle2, AlertTriangle } from "lucide-react";
import { Modal } from "../common/Modal";
import { Button } from "../common/Button";
import { api } from "../../api/client";
import { ChallengerResult } from "../../types/mlops";

export interface RetrainJobModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (result: ChallengerResult) => void;
}

export const RetrainJobModal: React.FC<RetrainJobModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [runName, setRunName] = useState<string>("challenger-retrain");
  const [seed, setSeed] = useState<number>(42);
  const [notes, setNotes] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successResult, setSuccessResult] = useState<ChallengerResult | null>(null);

  const handleReset = () => {
    setRunName("challenger-retrain");
    setSeed(42);
    setNotes("");
    setErrorMessage(null);
    setSuccessResult(null);
    setIsSubmitting(false);
  };

  const handleClose = () => {
    handleReset();
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const result = await api.retrain.run({
        run_name: runName.trim() || "challenger-retrain",
        seed: Number(seed) || 42,
        notes: notes.trim(),
      });
      setSuccessResult(result);
      if (onSuccess) {
        onSuccess(result);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to initiate retraining pipeline.";
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Governed Retraining Pipeline"
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
                Challenger v{successResult.challenger_version} Registered Successfully
              </div>
              <div style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
                Run ID: {successResult.run_id} | Data: {successResult.authorized_train_version}
              </div>
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: "var(--space-3)",
              padding: "var(--space-3)",
              backgroundColor: "var(--color-surface)",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
            }}
          >
            <div>
              <span style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>Val Recall (t*=0.160)</span>
              <div style={{ fontSize: "18px", fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--color-text-primary)" }}>
                {(successResult.val_recall * 100).toFixed(1)}%
              </div>
            </div>
            <div>
              <span style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>Val Precision</span>
              <div style={{ fontSize: "18px", fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--color-text-primary)" }}>
                {(successResult.val_precision * 100).toFixed(1)}%
              </div>
            </div>
            <div>
              <span style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>Val PR-AUC</span>
              <div style={{ fontSize: "18px", fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--color-text-primary)" }}>
                {successResult.val_pr_auc.toFixed(4)}
              </div>
            </div>
          </div>

          <div style={{ fontSize: "12px", color: "var(--color-text-secondary)", lineHeight: 1.4 }}>
            Candidate model registered with alias <code>challenger</code>. It remains in challenger status until explicitly evaluated and promoted through the promotion gate.
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "var(--space-2)", marginTop: "var(--space-2)" }}>
            <Button variant="primary" onClick={handleClose}>
              Done
            </Button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          {/* Governance Notice */}
          <div
            style={{
              padding: "var(--space-3)",
              backgroundColor: "rgba(20, 154, 251, 0.08)",
              border: "1px solid rgba(20, 154, 251, 0.25)",
              borderRadius: "var(--radius-sm)",
              display: "flex",
              gap: "var(--space-2)",
              alignItems: "flex-start",
            }}
          >
            <ShieldAlert size={18} color="var(--color-accent)" style={{ flexShrink: 0, marginTop: "2px" }} />
            <div style={{ fontSize: "12px", color: "var(--color-text-secondary)", lineHeight: 1.4 }}>
              <strong>Data Lineage Guarantee:</strong> Uses exclusively the authorized training split (<code>v1.0-train-split</code>). Held-out test split (<code>data/test/</code>) is strictly quarantined and inaccessible. Operational cutoff is frozen at <code>t* = 0.160</code>.
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
              Run Label
            </label>
            <input
              type="text"
              value={runName}
              onChange={(e) => setRunName(e.target.value)}
              placeholder="challenger-retrain"
              style={{
                width: "100%",
                padding: "8px 12px",
                backgroundColor: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                color: "var(--color-text-primary)",
                fontSize: "13px",
              }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--color-text-primary)", marginBottom: "var(--space-1)" }}>
              Random Seed (Reproducibility)
            </label>
            <input
              type="number"
              value={seed}
              onChange={(e) => setSeed(Number(e.target.value))}
              min={0}
              style={{
                width: "100%",
                padding: "8px 12px",
                backgroundColor: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                color: "var(--color-text-primary)",
                fontSize: "13px",
              }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "var(--color-text-primary)", marginBottom: "var(--space-1)" }}>
              Audit Notes (Optional)
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Scheduled retraining following drift watch alert on vibration feature"
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
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "var(--space-2)", marginTop: "var(--space-2)" }}>
            <Button variant="ghost" onClick={handleClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={isSubmitting}>
              <Play size={14} style={{ marginRight: "6px" }} />
              {isSubmitting ? "Retraining Candidate..." : "Run Retraining"}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
};
