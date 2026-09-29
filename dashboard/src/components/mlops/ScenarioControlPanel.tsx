import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  Play,
  RotateCcw,
  AlertTriangle,
  ShieldCheck,
  CheckCircle2,
  Sliders,
  Info,
  Clock,
  Terminal,
  Cpu,
  AlertOctagon,
  XCircle,
} from "lucide-react";
import { Card } from "../common/Card";
import { Button } from "../common/Button";
import { StatusBadge } from "../common/StatusBadge";
import { Modal } from "../common/Modal";
import { RoleGate } from "../common/RoleGate";
import { LoadingState } from "../common/LoadingState";
import { ErrorState } from "../common/ErrorState";
import { EmptyState } from "../common/EmptyState";
import { DataTable, Column } from "../common/DataTable";
import { api } from "../../api/client";
import { ScenarioSummary, ScenarioInjectResponse } from "../../types/scenario";
import { MachineSummary } from "../../types/machine";
import { PRIVILEGED_ROLES, canInjectScenario } from "../../utils/rbac";
import { useAuth } from "../../hooks/useAuth";
import { formatDateTime } from "../../utils/formatters";

export const ScenarioControlPanel: React.FC = () => {
  const { role } = useAuth();
  const isPrivileged = canInjectScenario(role);

  // Data states
  const [machines, setMachines] = useState<MachineSummary[]>([]);
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [selectedMachineId, setSelectedMachineId] = useState<string>("");
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>("");

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Action states
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [dispatchHistory, setDispatchHistory] = useState<ScenarioInjectResponse[]>([]);

  // Toast notification
  const [toast, setToast] = useState<{ message: string; type: "success" | "danger" | "info" } | null>(null);

  const showToast = (message: string, type: "success" | "danger" | "info" = "success") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  };

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [machinesData, scenariosData] = await Promise.all([
        api.machines.list({ limit: 100 }),
        api.scenarios.list(),
      ]);

      setMachines(machinesData || []);
      setScenarios(scenariosData || []);

      if (machinesData && machinesData.length > 0) {
        setSelectedMachineId((prev) => prev || machinesData[0].machine_id);
      }
      if (scenariosData && scenariosData.length > 0) {
        setSelectedScenarioId((prev) => prev || scenariosData[0].scenario_id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load simulation control data";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Derived selected machine and scenario
  const selectedMachine = useMemo(
    () => machines.find((m) => m.machine_id === selectedMachineId) || null,
    [machines, selectedMachineId]
  );

  const selectedScenario = useMemo(
    () => scenarios.find((s) => s.scenario_id === selectedScenarioId) || null,
    [scenarios, selectedScenarioId]
  );

  // Quick action: Restore Nominal Baseline (SCN-01)
  const handleSelectBaseline = () => {
    const baseline = scenarios.find((s) => s.scenario_id === "SCN-01");
    if (baseline) {
      setSelectedScenarioId("SCN-01");
    }
  };

  // Open confirmation modal
  const handleOpenConfirm = () => {
    if (!isPrivileged) return;
    setActionError(null);
    setIsConfirmModalOpen(true);
  };

  // Execute scenario injection
  const handleConfirmInject = async () => {
    if (!selectedMachineId || !selectedScenarioId || isSubmitting) return;

    setIsSubmitting(true);
    setActionError(null);

    try {
      const res = await api.scenarios.inject({
        machine_id: selectedMachineId,
        scenario_id: selectedScenarioId,
      });

      // Prepend to session history
      setDispatchHistory((prev) => [res, ...prev]);

      showToast(
        `Scenario ${res.scenario_id} accepted for ${res.machine_id} (Command ID: ${res.command_id.slice(0, 8)}).`,
        "success"
      );

      setIsConfirmModalOpen(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to dispatch scenario command";
      setActionError(msg);
      showToast(`Error: ${msg}`, "danger");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Columns for recent dispatches table
  const historyColumns: Column<ScenarioInjectResponse>[] = [
    {
      key: "command_id",
      header: "Command ID",
      render: (item) => (
        <span
          className="text-mono"
          style={{ fontSize: "11px", color: "var(--color-accent)", fontWeight: 600 }}
          title={item.command_id}
        >
          {item.command_id.slice(0, 8)}…
        </span>
      ),
    },
    {
      key: "machine_id",
      header: "Machine",
      render: (item) => (
        <span className="text-mono" style={{ fontWeight: 600 }}>
          {item.machine_id}
        </span>
      ),
    },
    {
      key: "scenario_id",
      header: "Scenario Code",
      render: (item) => (
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "4px",
            fontSize: "11px",
            padding: "2px 8px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--color-surface-raised)",
            border: "1px solid var(--color-border)",
            fontWeight: 600,
          }}
        >
          {item.scenario_id}
        </span>
      ),
    },
    {
      key: "status",
      header: "Dispatch Status",
      render: (item) => (
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "4px",
            fontSize: "11px",
            padding: "2px 8px",
            borderRadius: "var(--radius-sm)",
            fontWeight: 600,
            backgroundColor: "rgba(20, 154, 251, 0.12)",
            color: "var(--color-accent)",
            border: "1px solid rgba(20, 154, 251, 0.25)",
          }}
        >
          <CheckCircle2 size={12} />
          {item.status}
        </span>
      ),
    },
    {
      key: "injected_by",
      header: "Authorized By",
      render: (item) => (
        <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
          {item.injected_by}
        </span>
      ),
    },
    {
      key: "injected_at",
      header: "Timestamp",
      render: (item) => (
        <span style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
          {formatDateTime(item.injected_at)}
        </span>
      ),
    },
    {
      key: "message",
      header: "Server Acknowledgment",
      render: (item) => (
        <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
          {item.message}
        </span>
      ),
    },
  ];

  if (isLoading && machines.length === 0 && scenarios.length === 0) {
    return <LoadingState message="Loading simulation scenarios and registered machines..." />;
  }

  if (error && machines.length === 0) {
    return <ErrorState message={error} onRetry={loadData} />;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      {/* Toast Notification */}
      {toast && (
        <div
          role="status"
          aria-live="polite"
          style={{
            position: "fixed",
            bottom: "var(--space-6)",
            right: "var(--space-6)",
            zIndex: 100,
            padding: "12px 20px",
            borderRadius: "var(--radius-md)",
            backgroundColor:
              toast.type === "danger"
                ? "rgba(239, 68, 68, 0.95)"
                : toast.type === "info"
                ? "rgba(20, 154, 251, 0.95)"
                : "rgba(19, 239, 149, 0.95)",
            color: toast.type === "success" ? "#000" : "#FFF",
            fontSize: "13px",
            fontWeight: 600,
            boxShadow: "0 8px 24px rgba(0, 0, 0, 0.6)",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          {toast.type === "danger" ? (
            <AlertOctagon size={16} />
          ) : (
            <CheckCircle2 size={16} />
          )}
          {toast.message}
        </div>
      )}

      {/* Governance & Simulation Boundary Banner */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "var(--space-3)",
          padding: "var(--space-3) var(--space-4)",
          backgroundColor: "rgba(20, 154, 251, 0.08)",
          border: "1px solid rgba(20, 154, 251, 0.25)",
          borderRadius: "var(--radius-md)",
        }}
      >
        <Terminal size={18} style={{ color: "var(--color-accent)", flexShrink: 0 }} />
        <div style={{ fontSize: "12px", color: "var(--color-text-secondary)", lineHeight: 1.5 }}>
          <strong style={{ color: "var(--color-accent)", marginRight: "6px" }}>
            DEMO / SIMULATION CONTROL:
          </strong>
          Dispatches canonical simulation scenarios to virtual or edge simulators. Injected scenarios
          alter real-time sensor dynamics and exercise digital twin anomaly detection, health scoring,
          and trip safety logic. Simulated fault scenarios do NOT alter physical machinery or retrain production ML models.
        </div>
      </div>

      {/* Main Control Card */}
      <Card
        title="Scenario Dispatch & Demonstration Control"
        subtitle="Select a target machine and canonical fault preset to test predictive alerts and edge trips."
        action={
          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<RotateCcw size={14} />}
              onClick={handleSelectBaseline}
              disabled={selectedScenarioId === "SCN-01"}
              title="Quickly select Healthy Nominal baseline (SCN-01)"
            >
              Select Baseline (SCN-01)
            </Button>
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<Sliders size={14} />}
              onClick={loadData}
              disabled={isLoading}
            >
              Refresh Fleet
            </Button>
          </div>
        }
      >
        {machines.length === 0 ? (
          <EmptyState
            title="No machines available"
            description="No registered machines were found in the fleet to inject scenarios."
            icon={<Cpu size={24} />}
          />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
            {/* Form Controls: Machine & Scenario Selection */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
                gap: "var(--space-4)",
              }}
            >
              {/* Machine Selection Dropdown */}
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <label
                  htmlFor="machine-select"
                  style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    color: "var(--color-text-secondary)",
                    textTransform: "uppercase",
                    letterSpacing: "var(--tracking-wide)",
                  }}
                >
                  Target Asset (Machine)
                </label>
                <select
                  id="machine-select"
                  aria-label="Target Machine"
                  value={selectedMachineId}
                  onChange={(e) => setSelectedMachineId(e.target.value)}
                  style={{
                    padding: "10px 12px",
                    borderRadius: "var(--radius-sm)",
                    backgroundColor: "var(--color-surface-raised)",
                    border: "1px solid var(--color-border)",
                    color: "var(--color-text-primary)",
                    fontSize: "13px",
                    fontFamily: "var(--font-sans)",
                    outline: "none",
                  }}
                >
                  {machines.map((m) => (
                    <option key={m.machine_id} value={m.machine_id}>
                      {m.machine_id} — {m.machine_type} ({m.operating_state})
                    </option>
                  ))}
                </select>
              </div>

              {/* Scenario Selection Dropdown */}
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <label
                  htmlFor="scenario-select"
                  style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    color: "var(--color-text-secondary)",
                    textTransform: "uppercase",
                    letterSpacing: "var(--tracking-wide)",
                  }}
                >
                  Simulation Scenario Preset
                </label>
                <select
                  id="scenario-select"
                  aria-label="Simulation Scenario"
                  value={selectedScenarioId}
                  onChange={(e) => setSelectedScenarioId(e.target.value)}
                  style={{
                    padding: "10px 12px",
                    borderRadius: "var(--radius-sm)",
                    backgroundColor: "var(--color-surface-raised)",
                    border: "1px solid var(--color-border)",
                    color: "var(--color-text-primary)",
                    fontSize: "13px",
                    fontFamily: "var(--font-sans)",
                    outline: "none",
                  }}
                >
                  {scenarios.map((s) => (
                    <option key={s.scenario_id} value={s.scenario_id}>
                      [{s.scenario_id}] {s.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Scenario Preview Box */}
            {selectedScenario && (
              <div
                style={{
                  padding: "var(--space-4)",
                  backgroundColor: "var(--color-surface-raised)",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--color-border)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "var(--space-3)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    flexWrap: "wrap",
                    gap: "var(--space-2)",
                  }}
                >
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span
                        className="text-mono"
                        style={{
                          fontSize: "12px",
                          fontWeight: 700,
                          color: "var(--color-accent)",
                          padding: "2px 6px",
                          backgroundColor: "rgba(20, 154, 251, 0.12)",
                          borderRadius: "var(--radius-sm)",
                        }}
                      >
                        {selectedScenario.scenario_id}
                      </span>
                      <h3 style={{ fontSize: "15px", fontWeight: 600, margin: 0 }}>
                        {selectedScenario.name}
                      </h3>
                    </div>
                    <p
                      style={{
                        fontSize: "13px",
                        color: "var(--color-text-secondary)",
                        marginTop: "4px",
                        marginBottom: 0,
                      }}
                    >
                      {selectedScenario.description}
                    </p>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                    {selectedMachine && (
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
                          Current State:
                        </span>
                        <StatusBadge status={selectedMachine.operating_state} size="sm" />
                      </div>
                    )}
                  </div>
                </div>

                {/* Scenario Metadata Grid */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                    gap: "var(--space-3)",
                    padding: "var(--space-3)",
                    backgroundColor: "var(--color-surface)",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--color-border-subtle)",
                    fontSize: "12px",
                  }}
                >
                  <div>
                    <span style={{ color: "var(--color-text-muted)", display: "block" }}>
                      Target Failure Mode
                    </span>
                    <span style={{ fontWeight: 600, color: "var(--color-text-primary)" }}>
                      {selectedScenario.target_fault || "NONE"}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: "var(--color-text-muted)", display: "block" }}>
                      Command Safety Guard
                    </span>
                    <span
                      style={{
                        fontWeight: 600,
                        color: "var(--color-success)",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "4px",
                      }}
                    >
                      <ShieldCheck size={13} />
                      Preset Enforced (No Injection)
                    </span>
                  </div>
                  <div>
                    <span style={{ color: "var(--color-text-muted)", display: "block" }}>
                      Selected Asset
                    </span>
                    <span className="text-mono" style={{ fontWeight: 600, color: "var(--color-text-primary)" }}>
                      {selectedMachine?.machine_id} ({selectedMachine?.machine_type})
                    </span>
                  </div>
                  {selectedScenario.duration_s !== undefined && (
                    <div>
                      <span style={{ color: "var(--color-text-muted)", display: "block" }}>
                        Estimated Duration
                      </span>
                      <span style={{ fontWeight: 600, color: "var(--color-text-primary)" }}>
                        {selectedScenario.duration_s}s ({(selectedScenario.duration_s / 60).toFixed(1)}m)
                      </span>
                    </div>
                  )}
                </div>

                {/* Action Row */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: "var(--space-3)",
                    marginTop: "var(--space-2)",
                    paddingTop: "var(--space-3)",
                    borderTop: "1px solid var(--color-border-subtle)",
                  }}
                >
                  <div style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>
                    {isPrivileged ? (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                        <CheckCircle2 size={14} style={{ color: "var(--color-success)" }} />
                        Authorized: Requires Maintenance Engineer or Admin role.
                      </span>
                    ) : (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "6px", color: "var(--color-warning)" }}>
                        <AlertTriangle size={14} />
                        Read-only: Requires Maintenance Engineer or Admin role to inject.
                      </span>
                    )}
                  </div>

                  <RoleGate
                    allowedRoles={PRIVILEGED_ROLES}
                    fallback={
                      <Button variant="secondary" size="md" disabled title="Operator role is read-only">
                        Inject Scenario (Unauthorized)
                      </Button>
                    }
                  >
                    <Button
                      variant={selectedScenario.scenario_id === "SCN-01" ? "primary" : "warning"}
                      size="md"
                      leftIcon={<Play size={14} />}
                      onClick={handleOpenConfirm}
                    >
                      {selectedScenario.scenario_id === "SCN-01"
                        ? "Restore Nominal Baseline"
                        : "Inject Scenario…"}
                    </Button>
                  </RoleGate>
                </div>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Simulation Lifecycle & Stop Clarification Card */}
      <Card
        title="Simulation Lifecycle & Reset Procedure"
        subtitle="How to stop a running scenario and restore standard operational telemetry."
      >
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "var(--space-4)",
            fontSize: "13px",
            color: "var(--color-text-secondary)",
            lineHeight: 1.6,
          }}
        >
          <Info size={20} style={{ color: "var(--color-accent)", flexShrink: 0, marginTop: "2px" }} />
          <div>
            <p style={{ margin: "0 0 var(--space-2) 0" }}>
              EdgeTwin physical simulation scenarios execute asynchronously on edge simulators or Wokwi virtual hardware.
              When a scenario is dispatched, the simulator shifts its coupled process equations into the target failure profile
              (e.g., elevated vibration, thermal breakdown, or sensor dropout).
            </p>
            <p style={{ margin: 0 }}>
              <strong>To stop a simulated fault:</strong> Dispatches do not use an artificial kill signal; instead,
              dispatch <strong>SCN-01 (Healthy Nominal Operation)</strong> to command the simulator to recover nominal temperature,
              speed, torque, and vibration envelopes.
            </p>
          </div>
        </div>
      </Card>

      {/* Session Dispatch History Table */}
      <Card
        title="Session Dispatch Log"
        subtitle="Audit record of scenario injection commands dispatched during the active session."
      >
        {dispatchHistory.length === 0 ? (
          <EmptyState
            title="No scenario dispatches yet"
            description="Simulation commands executed during this browser session will appear here with command IDs and server acknowledgment."
            icon={<Clock size={22} />}
          />
        ) : (
          <DataTable
            columns={historyColumns}
            data={dispatchHistory}
            keyExtractor={(item) => item.command_id}
          />
        )}
      </Card>

      {/* Confirmation Modal */}
      <Modal
        isOpen={isConfirmModalOpen}
        onClose={() => {
          if (!isSubmitting) setIsConfirmModalOpen(false);
        }}
        title={`Confirm Scenario Dispatch: ${selectedScenario?.scenario_id}`}
        maxWidth="540px"
        footer={
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "var(--space-2)" }}>
            <Button
              variant="secondary"
              onClick={() => setIsConfirmModalOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              variant={selectedScenario?.scenario_id === "SCN-01" ? "primary" : "warning"}
              onClick={handleConfirmInject}
              isLoading={isSubmitting}
              leftIcon={<Play size={14} />}
            >
              {isSubmitting ? "Dispatching..." : "Confirm & Dispatch Scenario"}
            </Button>
          </div>
        }
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          {actionError && (
            <div
              style={{
                padding: "10px 14px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "rgba(239, 68, 68, 0.12)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                color: "var(--color-danger)",
                fontSize: "12px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <XCircle size={15} />
              {actionError}
            </div>
          )}

          <p style={{ margin: 0, fontSize: "13px", color: "var(--color-text-secondary)" }}>
            You are about to dispatch a controlled simulation scenario command to the targeted asset.
            Please review the parameters:
          </p>

          <div
            style={{
              padding: "var(--space-3)",
              backgroundColor: "var(--color-surface-raised)",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
              display: "flex",
              flexDirection: "column",
              gap: "8px",
              fontSize: "12px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--color-text-muted)" }}>Target Asset:</span>
              <span className="text-mono" style={{ fontWeight: 600, color: "var(--color-text-primary)" }}>
                {selectedMachineId} ({selectedMachine?.machine_type})
              </span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--color-text-muted)" }}>Scenario:</span>
              <span style={{ fontWeight: 600, color: "var(--color-text-primary)" }}>
                [{selectedScenario?.scenario_id}] {selectedScenario?.name}
              </span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--color-text-muted)" }}>Expected Effect:</span>
              <span style={{ fontWeight: 600, color: "var(--color-text-primary)" }}>
                {selectedScenario?.target_fault || "Nominal Baseline"}
              </span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--color-text-muted)" }}>Authorized User:</span>
              <span style={{ color: "var(--color-accent)", fontWeight: 600 }}>
                {role || "Authenticated User"}
              </span>
            </div>
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: "8px",
              padding: "10px 12px",
              backgroundColor: "rgba(254, 117, 14, 0.08)",
              border: "1px solid rgba(254, 117, 14, 0.25)",
              borderRadius: "var(--radius-sm)",
              fontSize: "12px",
              color: "var(--color-warning)",
            }}
          >
            <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: "2px" }} />
            <span>
              This command alters simulated operational telemetry. If a fault scenario is selected,
              digital twin anomaly scores and risk bands will respond accordingly.
            </span>
          </div>
        </div>
      </Modal>
    </div>
  );
};
