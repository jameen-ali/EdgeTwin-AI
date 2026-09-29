import React, { useState, useEffect } from "react";
import { CheckCircle2, AlertCircle } from "lucide-react";
import { Modal } from "../common/Modal";
import { Button } from "../common/Button";
import { api } from "../../api/client";
import { MaintenanceItem } from "../../types/maintenance";
import { formatDateTime } from "../../utils/formatters";

export interface UpdateWorkOrderModalProps {
  isOpen: boolean;
  onClose: () => void;
  item: MaintenanceItem | null;
  onSuccess?: (updated: MaintenanceItem) => void;
}

export const UpdateWorkOrderModal: React.FC<UpdateWorkOrderModalProps> = ({
  isOpen,
  onClose,
  item,
  onSuccess,
}) => {
  const [status, setStatus] = useState<string>("SCHEDULED");
  const [technician, setTechnician] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (item && isOpen) {
      setStatus(item.status);
      setTechnician(item.technician || "");
      setDescription(item.description || "");
      setErrorMessage(null);
    }
  }, [item, isOpen]);

  if (!item) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const payload = {
        status,
        technician: technician.trim() || null,
        description: description.trim() || undefined,
      };

      const updated = await api.maintenance.update(item.id, payload);
      if (onSuccess) {
        onSuccess(updated);
      }
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update maintenance event";
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Update Work Order — MNT-${item.id}`}
      maxWidth="500px"
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
            {isSubmitting ? "Updating..." : "Save Changes"}
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

        {/* Static Header Info */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "var(--space-3)",
            padding: "var(--space-3)",
            backgroundColor: "var(--color-surface-raised)",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--color-border-subtle)",
            fontSize: "12px",
          }}
        >
          <div>
            <span style={{ color: "var(--color-text-muted)" }}>Target Machine: </span>
            <span className="text-mono" style={{ fontWeight: 700, color: "var(--color-accent)" }}>
              {item.machine_id}
            </span>
          </div>
          <div>
            <span style={{ color: "var(--color-text-muted)" }}>Action Type: </span>
            <span className="text-mono" style={{ fontWeight: 600 }}>{item.event_type}</span>
          </div>
          {item.alert_id && (
            <div>
              <span style={{ color: "var(--color-text-muted)" }}>Linked Alert: </span>
              <span className="text-mono" style={{ fontWeight: 600 }}>ALT-{item.alert_id}</span>
            </div>
          )}
          <div>
            <span style={{ color: "var(--color-text-muted)" }}>Logged: </span>
            <span className="text-mono" style={{ fontSize: "11px" }}>{formatDateTime(item.created_at)}</span>
          </div>
        </div>

        {/* Lifecycle Status */}
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-muted)" }}>
            WORK ORDER STATUS
          </label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            style={{
              backgroundColor: "var(--color-surface-raised)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-sm)",
              padding: "8px 10px",
              color: "var(--color-text-primary)",
              fontSize: "13px",
            }}
          >
            <option value="SCHEDULED">SCHEDULED</option>
            <option value="IN_PROGRESS">IN_PROGRESS</option>
            <option value="COMPLETED">COMPLETED</option>
            <option value="CANCELLED">CANCELLED</option>
          </select>
        </div>

        {/* Assigned Technician */}
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-muted)" }}>
            ASSIGNED TECHNICIAN
          </label>
          <input
            type="text"
            value={technician}
            onChange={(e) => setTechnician(e.target.value)}
            placeholder="e.g. Lead Tech Sarah"
            style={{
              backgroundColor: "var(--color-surface-raised)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-sm)",
              padding: "8px 10px",
              color: "var(--color-text-primary)",
              fontSize: "13px",
            }}
          />
        </div>

        {/* Work Order Description / Completion Notes */}
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-muted)" }}>
            NOTES / ACTIONS PERFORMED
          </label>
          <textarea
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Work completed, parts replaced, inspection findings..."
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
