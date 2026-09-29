import React, { useState, useEffect } from "react";
import { AlertCircle, CheckCircle2, Info } from "lucide-react";
import { Modal } from "../common/Modal";
import { Button } from "../common/Button";
import { api } from "../../api/client";
import { FeedbackItem, FeedbackType } from "../../types/feedback";

export interface OperatorFeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  machineId: string;
  alertId?: number | null;
  predictionId?: number | null;
  predictedRiskBand?: string | null;
  failureProbability?: number | null;
  onSuccess?: (feedback: FeedbackItem) => void;
}

export const OperatorFeedbackModal: React.FC<OperatorFeedbackModalProps> = ({
  isOpen,
  onClose,
  machineId,
  alertId = null,
  predictionId = null,
  predictedRiskBand = null,
  failureProbability = null,
  onSuccess,
}) => {
  const [feedbackType, setFeedbackType] = useState<FeedbackType>("CONFIRMED");
  const [notes, setNotes] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setFeedbackType("CONFIRMED");
      setNotes("");
      setErrorMessage(null);
    }
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!machineId) {
      setErrorMessage("Machine ID is required.");
      return;
    }

    if (!alertId && !predictionId) {
      setErrorMessage("Either an Alert ID or Prediction ID must be linked.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const payload = {
        alert_id: alertId || null,
        prediction_id: predictionId || null,
        feedback_type: feedbackType,
        notes: notes.trim() || undefined,
      };

      const result = await api.feedback.submit(machineId, payload);
      if (onSuccess) {
        onSuccess(result);
      }
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to record feedback";
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Record Ground-Truth Feedback"
      maxWidth="520px"
      footer={
        <div style={{ display: "flex", gap: "var(--space-2)", justifyContent: "flex-end" }}>
          <Button variant="secondary" size="sm" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            leftIcon={<CheckCircle2 size={14} />}
            onClick={handleSubmit}
            disabled={isSubmitting}
          >
            {isSubmitting ? "Submitting..." : "Submit Feedback"}
          </Button>
        </div>
      }
    >
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
        {errorMessage && (
          <div
            style={{
              padding: "var(--space-2) var(--space-3)",
              backgroundColor: "var(--color-danger-subtle)",
              border: "1px solid var(--color-danger-border)",
              borderRadius: "var(--radius-sm)",
              color: "var(--color-danger)",
              fontSize: "12px",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <AlertCircle size={14} />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Informational Banner: Model Prediction vs Ground Truth */}
        <div
          style={{
            padding: "var(--space-3)",
            backgroundColor: "var(--color-surface-raised)",
            border: "1px solid var(--color-border-subtle)",
            borderRadius: "var(--radius-md)",
            fontSize: "12px",
            display: "flex",
            flexDirection: "column",
            gap: "6px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--color-accent)" }}>
            <Info size={14} />
            <span style={{ fontWeight: 600 }}>Ground Truth Observation</span>
          </div>
          <div style={{ color: "var(--color-text-secondary)", lineHeight: 1.4 }}>
            Record actual observed findings on the shop floor. This feedback is persisted for model performance tracking and drift evaluation. Submitting feedback does not automatically retrain the model.
          </div>
          <div style={{ display: "flex", gap: "var(--space-4)", marginTop: "4px", fontSize: "11px" }}>
            <div>
              <span style={{ color: "var(--color-text-muted)" }}>Target Machine: </span>
              <span className="text-mono" style={{ fontWeight: 700, color: "var(--color-text-primary)" }}>{machineId}</span>
            </div>
            {alertId && (
              <div>
                <span style={{ color: "var(--color-text-muted)" }}>Linked Alert: </span>
                <span className="text-mono" style={{ fontWeight: 600 }}>ALT-{alertId}</span>
              </div>
            )}
            {predictedRiskBand && (
              <div>
                <span style={{ color: "var(--color-text-muted)" }}>Predicted Risk: </span>
                <span className="text-mono" style={{ fontWeight: 600, color: "var(--color-warning)" }}>{predictedRiskBand}</span>
              </div>
            )}
            {typeof failureProbability === "number" && (
              <div>
                <span style={{ color: "var(--color-text-muted)" }}>p_fail: </span>
                <span className="text-mono" style={{ fontWeight: 600 }}>{(failureProbability * 100).toFixed(1)}%</span>
              </div>
            )}
          </div>
        </div>

        {/* Observed Outcome Radio / Choices */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-muted)" }}>
            OBSERVED OUTCOME *
          </label>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3)" }}>
            <button
              type="button"
              onClick={() => setFeedbackType("CONFIRMED")}
              style={{
                padding: "var(--space-3)",
                backgroundColor: feedbackType === "CONFIRMED" ? "var(--color-danger-subtle)" : "var(--color-surface-raised)",
                border: `1px solid ${feedbackType === "CONFIRMED" ? "var(--color-danger)" : "var(--color-border)"}`,
                borderRadius: "var(--radius-md)",
                cursor: "pointer",
                textAlign: "left",
                display: "flex",
                flexDirection: "column",
                gap: "2px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span
                  style={{
                    width: "12px",
                    height: "12px",
                    borderRadius: "50%",
                    border: `2px solid ${feedbackType === "CONFIRMED" ? "var(--color-danger)" : "var(--color-text-muted)"}`,
                    backgroundColor: feedbackType === "CONFIRMED" ? "var(--color-danger)" : "transparent",
                  }}
                />
                <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--color-text-primary)" }}>
                  CONFIRMED FAILURE
                </span>
              </div>
              <span style={{ fontSize: "10px", color: "var(--color-text-muted)", marginLeft: "18px" }}>
                True positive: physical issue or abnormal wear verified
              </span>
            </button>

            <button
              type="button"
              onClick={() => setFeedbackType("FALSE_ALARM")}
              style={{
                padding: "var(--space-3)",
                backgroundColor: feedbackType === "FALSE_ALARM" ? "var(--color-accent-subtle)" : "var(--color-surface-raised)",
                border: `1px solid ${feedbackType === "FALSE_ALARM" ? "var(--color-accent)" : "var(--color-border)"}`,
                borderRadius: "var(--radius-md)",
                cursor: "pointer",
                textAlign: "left",
                display: "flex",
                flexDirection: "column",
                gap: "2px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span
                  style={{
                    width: "12px",
                    height: "12px",
                    borderRadius: "50%",
                    border: `2px solid ${feedbackType === "FALSE_ALARM" ? "var(--color-accent)" : "var(--color-text-muted)"}`,
                    backgroundColor: feedbackType === "FALSE_ALARM" ? "var(--color-accent)" : "transparent",
                  }}
                />
                <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--color-text-primary)" }}>
                  FALSE ALARM
                </span>
              </div>
              <span style={{ fontSize: "10px", color: "var(--color-text-muted)", marginLeft: "18px" }}>
                False positive: machine inspected and verified nominal
              </span>
            </button>
          </div>
        </div>

        {/* Detailed Notes */}
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-muted)" }}>
            INSPECTION / TEARDOWN FINDINGS (OPTIONAL)
          </label>
          <textarea
            rows={4}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Record specific teardown findings, measured clearances, root cause, or sensor diagnostics..."
            style={{
              backgroundColor: "var(--color-surface-raised)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-sm)",
              padding: "8px 10px",
              color: "var(--color-text-primary)",
              fontSize: "13px",
              lineHeight: 1.4,
              resize: "vertical",
            }}
          />
        </div>
      </form>
    </Modal>
  );
};
