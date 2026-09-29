import React, { useState, useEffect } from "react";
import { Wrench, AlertCircle } from "lucide-react";
import { Modal } from "../common/Modal";
import { Button } from "../common/Button";
import { api } from "../../api/client";
import { MaintenanceItem, MaintenanceEventType } from "../../types/maintenance";

export interface CreateWorkOrderModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialMachineId?: string;
  initialAlertId?: number | null;
  initialEventType?: MaintenanceEventType | string;
  initialDescription?: string;
  initialTechnician?: string;
  onSuccess?: (created: MaintenanceItem) => void;
}

export const CreateWorkOrderModal: React.FC<CreateWorkOrderModalProps> = ({
  isOpen,
  onClose,
  initialMachineId = "",
  initialAlertId = null,
  initialEventType = "INSPECTION",
  initialDescription = "",
  initialTechnician = "",
  onSuccess,
}) => {
  const [machineId, setMachineId] = useState(initialMachineId);
  const [alertId, setAlertId] = useState<number | null>(initialAlertId);
  const [eventType, setEventType] = useState<string>(initialEventType);
  const [status, setStatus] = useState<string>("SCHEDULED");
  const [technician, setTechnician] = useState<string>(initialTechnician);
  const [description, setDescription] = useState<string>(initialDescription);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setMachineId(initialMachineId);
      setAlertId(initialAlertId);
      setEventType(initialEventType || "INSPECTION");
      setStatus("SCHEDULED");
      setTechnician(initialTechnician);
      setDescription(initialDescription);
      setErrorMessage(null);
    }
  }, [isOpen, initialMachineId, initialAlertId, initialEventType, initialDescription, initialTechnician]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!machineId.trim()) {
      setErrorMessage("Target Machine ID is required.");
      return;
    }

    if (!description.trim()) {
      setErrorMessage("Description / Work scope is required.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const payload = {
        machine_id: machineId.trim().toUpperCase(),
        event_type: eventType,
        status,
        description: description.trim(),
        technician: technician.trim() || null,
        alert_id: alertId || null,
      };

      const created = await api.maintenance.create(payload);
      if (onSuccess) {
        onSuccess(created);
      }
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create maintenance work order";
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Create Maintenance Work Order"
      maxWidth="540px"
      footer={
        <div style={{ display: "flex", gap: "var(--space-2)", justifyContent: "flex-end" }}>
          <Button variant="secondary" size="sm" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            leftIcon={<Wrench size={14} />}
            onClick={handleSubmit}
            disabled={isSubmitting}
          >
            {isSubmitting ? "Creating..." : "Create Work Order"}
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

        {/* Machine ID & Alert Link */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3)" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-muted)" }}>
              MACHINE ID *
            </label>
            <input
              type="text"
              required
              value={machineId}
              onChange={(e) => setMachineId(e.target.value.toUpperCase())}
              placeholder="e.g. MOT-1001"
              style={{
                backgroundColor: "var(--color-surface-raised)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                padding: "8px 10px",
                color: "var(--color-text-primary)",
                fontSize: "13px",
                fontFamily: "var(--font-mono)",
              }}
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-muted)" }}>
              LINKED ALERT ID (OPTIONAL)
            </label>
            <input
              type="number"
              value={alertId ?? ""}
              onChange={(e) => setAlertId(e.target.value ? Number(e.target.value) : null)}
              placeholder="None"
              style={{
                backgroundColor: "var(--color-surface-raised)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                padding: "8px 10px",
                color: "var(--color-text-primary)",
                fontSize: "13px",
                fontFamily: "var(--font-mono)",
              }}
            />
          </div>
        </div>

        {/* Event Type & Status */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3)" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-muted)" }}>
              ACTION / EVENT TYPE
            </label>
            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              style={{
                backgroundColor: "var(--color-surface-raised)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                padding: "8px 10px",
                color: "var(--color-text-primary)",
                fontSize: "13px",
              }}
            >
              <option value="INSPECTION">INSPECTION</option>
              <option value="PART_REPLACEMENT">PART_REPLACEMENT</option>
              <option value="OVERHAUL">OVERHAUL</option>
              <option value="LUBRICATION">LUBRICATION</option>
              <option value="CALIBRATION">CALIBRATION</option>
            </select>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-muted)" }}>
              INITIAL STATUS
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
            </select>
          </div>
        </div>

        {/* Assigned Technician */}
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-muted)" }}>
            ASSIGNED TECHNICIAN (OPTIONAL)
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

        {/* Description / Scope */}
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-muted)" }}>
            WORK ORDER DESCRIPTION / SCOPE *
          </label>
          <textarea
            required
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Specify maintenance action, affected components, torque checks, or diagnostic tasks..."
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
