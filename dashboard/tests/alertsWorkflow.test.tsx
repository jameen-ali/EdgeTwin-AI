import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { AlertsPage } from "../src/pages/AlertsPage";
import { MaintenancePage } from "../src/pages/MaintenancePage";
import { CreateWorkOrderModal } from "../src/components/maintenance/CreateWorkOrderModal";
import { UpdateWorkOrderModal } from "../src/components/maintenance/UpdateWorkOrderModal";
import { OperatorFeedbackModal } from "../src/components/feedback/OperatorFeedbackModal";
import { AuthProvider } from "../src/context/AuthContext";
import { api } from "../src/api/client";
import { AlertItem } from "../src/types/alert";
import { MaintenanceItem } from "../src/types/maintenance";

const mockAlerts: AlertItem[] = [
  {
    id: 101,
    machine_id: "MOT-1001",
    severity: "CRITICAL",
    status: "OPEN",
    alert_type: "PREDICTIVE_FAILURE_WARNING",
    message: "Calibrated failure probability 82.4% exceeds threshold t*=0.16",
    trigger_conditions: { failure_probability: 0.824, temperature_c: 88.5 },
    top_factors: [
      { feature: "Process_Temperature_C", shap_value: 0.42 },
      { feature: "Tool_Wear_Min", shap_value: 0.28 },
    ],
    triggered_at: "2026-09-29T10:00:00Z",
  },
  {
    id: 102,
    machine_id: "PMP-2001",
    severity: "WARNING",
    status: "ACKNOWLEDGED",
    alert_type: "VIBRATION_SPIKE",
    message: "Vibration anomaly detected on impeller bearing",
    trigger_conditions: { vibration_mm_s: 4.8 },
    triggered_at: "2026-09-29T09:30:00Z",
    acknowledged_at: "2026-09-29T09:35:00Z",
    resolved_by: "tech_alex",
  },
  {
    id: 103,
    machine_id: "MOT-1001",
    severity: "INFO",
    status: "RESOLVED",
    alert_type: "HIGH_TEMP",
    message: "Process temperature returned to nominal range",
    triggered_at: "2026-09-29T08:00:00Z",
    acknowledged_at: "2026-09-29T08:05:00Z",
    resolved_at: "2026-09-29T08:30:00Z",
    resolved_by: "admin_user",
  },
];

const mockMaintenance: MaintenanceItem[] = [
  {
    id: 201,
    machine_id: "MOT-1001",
    alert_id: 101,
    event_type: "PART_REPLACEMENT",
    description: "Replace drive bearing and inspect alignment",
    status: "SCHEDULED",
    technician: "lead_tech_sarah",
    started_at: null,
    completed_at: null,
    created_at: "2026-09-29T10:15:00Z",
  },
  {
    id: 202,
    machine_id: "PMP-2001",
    alert_id: null,
    event_type: "INSPECTION",
    description: "Monthly routine seal inspection",
    status: "COMPLETED",
    technician: "tech_alex",
    started_at: "2026-09-29T08:00:00Z",
    completed_at: "2026-09-29T09:00:00Z",
    created_at: "2026-09-29T07:30:00Z",
  },
];

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <BrowserRouter>
      <AuthProvider>{ui}</AuthProvider>
    </BrowserRouter>
  );
}

describe("S22 — Alerts Operational Workflow (T-056)", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("edgetwin_token", "admin-jwt-token");
    vi.spyOn(api.auth, "getMe").mockResolvedValue({
      id: 1,
      username: "admin_engineer",
      role: "ADMIN",
      is_active: true,
      created_at: "2026-09-29T00:00:00Z",
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders alerts list, severity badges, and machine IDs", async () => {
    vi.spyOn(api.alerts, "list").mockResolvedValue(mockAlerts);

    renderWithProviders(<AlertsPage />);

    expect(screen.getByText(/fetching operational alarms/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("ALT-101")).toBeInTheDocument();
      expect(screen.getByText("ALT-102")).toBeInTheDocument();
      expect(screen.getByText("ALT-103")).toBeInTheDocument();
    });

    expect(screen.getAllByText("CRITICAL")[0]).toBeInTheDocument();
    expect(screen.getAllByText("WARNING")[0]).toBeInTheDocument();
    expect(screen.getAllByText("INFO")[0]).toBeInTheDocument();
  });

  it("filters alerts by status tab (ACTIVE, ACKNOWLEDGED, RESOLVED)", async () => {
    vi.spyOn(api.alerts, "list").mockResolvedValue(mockAlerts);

    renderWithProviders(<AlertsPage />);

    await waitFor(() => {
      expect(screen.getByText("ALT-101")).toBeInTheDocument();
    });

    // Click RESOLVED filter
    const resolvedBtn = screen.getByRole("button", { name: "RESOLVED" });
    fireEvent.click(resolvedBtn);

    expect(screen.getByText("ALT-103")).toBeInTheDocument();
    expect(screen.queryByText("ALT-101")).not.toBeInTheDocument();

    // Click ACTIVE filter
    const activeBtn = screen.getByRole("button", { name: "ACTIVE" });
    fireEvent.click(activeBtn);

    expect(screen.getByText("ALT-101")).toBeInTheDocument();
    expect(screen.queryByText("ALT-103")).not.toBeInTheDocument();
  });

  it("filters alerts by severity (CRITICAL, WARNING)", async () => {
    vi.spyOn(api.alerts, "list").mockResolvedValue(mockAlerts);

    renderWithProviders(<AlertsPage />);

    await waitFor(() => {
      expect(screen.getByText("ALT-101")).toBeInTheDocument();
    });

    const critBtn = screen.getByRole("button", { name: "CRITICAL" });
    fireEvent.click(critBtn);

    expect(screen.getByText("ALT-101")).toBeInTheDocument();
    expect(screen.queryByText("ALT-102")).not.toBeInTheDocument();
  });

  it("handles alert acknowledgment with API persistence and optimistic update", async () => {
    vi.spyOn(api.alerts, "list").mockResolvedValue(mockAlerts);
    const ackSpy = vi.spyOn(api.alerts, "acknowledge").mockResolvedValue({
      ...mockAlerts[0],
      status: "ACKNOWLEDGED",
      acknowledged_at: "2026-09-29T10:05:00Z",
    });

    renderWithProviders(<AlertsPage />);

    await waitFor(() => {
      expect(screen.getByText("ALT-101")).toBeInTheDocument();
    });

    const ackBtn = screen.getByRole("button", { name: "Ack" });
    fireEvent.click(ackBtn);

    await waitFor(() => {
      expect(ackSpy).toHaveBeenCalledWith(101, { notes: undefined });
    });
  });

  it("rolls back optimistic acknowledgment and shows error toast on failure", async () => {
    vi.spyOn(api.alerts, "list").mockResolvedValue(mockAlerts);
    vi.spyOn(api.alerts, "acknowledge").mockRejectedValue(new Error("Network timeout during acknowledgment"));

    renderWithProviders(<AlertsPage />);

    await waitFor(() => {
      expect(screen.getByText("ALT-101")).toBeInTheDocument();
    });

    const ackBtn = screen.getByRole("button", { name: "Ack" });
    fireEvent.click(ackBtn);

    await waitFor(() => {
      expect(screen.getByText(/error: network timeout during acknowledgment/i)).toBeInTheDocument();
    });
  });

  it("opens alert detail modal showing SHAP factors and trigger conditions", async () => {
    vi.spyOn(api.alerts, "list").mockResolvedValue(mockAlerts);

    renderWithProviders(<AlertsPage />);

    await waitFor(() => {
      expect(screen.getByText("ALT-101")).toBeInTheDocument();
    });

    const detailsBtn = screen.getAllByRole("button", { name: "Details" })[0];
    fireEvent.click(detailsBtn);

    await waitFor(() => {
      expect(screen.getByText(/Incident Investigation — ALT-101/i)).toBeInTheDocument();
      expect(screen.getByText(/Process_Temperature_C/i)).toBeInTheDocument();
      expect(screen.getByText(/Tool_Wear_Min/i)).toBeInTheDocument();
      expect(screen.getByText(/0.824/i)).toBeInTheDocument();
    });
  });
});

describe("S22 — Maintenance Workflow & Work Orders (T-056)", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("edgetwin_token", "admin-jwt-token");
    vi.spyOn(api.auth, "getMe").mockResolvedValue({
      id: 1,
      username: "lead_engineer",
      role: "MAINTENANCE_ENGINEER",
      is_active: true,
      created_at: "2026-09-29T00:00:00Z",
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders maintenance history and work orders", async () => {
    vi.spyOn(api.maintenance, "list").mockResolvedValue(mockMaintenance);

    renderWithProviders(<MaintenancePage />);

    await waitFor(() => {
      expect(screen.getByText("MNT-201")).toBeInTheDocument();
      expect(screen.getByText("MNT-202")).toBeInTheDocument();
      expect(screen.getAllByText("PART_REPLACEMENT")[0]).toBeInTheDocument();
      expect(screen.getAllByText("INSPECTION")[0]).toBeInTheDocument();
      expect(screen.getAllByText("SCHEDULED")[0]).toBeInTheDocument();
      expect(screen.getAllByText("COMPLETED")[0]).toBeInTheDocument();
    });
  });

  it("creates a new maintenance work order with validation", async () => {
    const createSpy = vi.spyOn(api.maintenance, "create").mockResolvedValue({
      id: 203,
      machine_id: "MOT-1001",
      alert_id: 101,
      event_type: "OVERHAUL",
      description: "Full mechanical bearing overhaul",
      status: "SCHEDULED",
      technician: "lead_tech_sarah",
      started_at: null,
      completed_at: null,
      created_at: "2026-09-29T11:00:00Z",
    });

    const onSuccess = vi.fn();
    renderWithProviders(
      <CreateWorkOrderModal
        isOpen={true}
        onClose={vi.fn()}
        initialMachineId="MOT-1001"
        initialAlertId={101}
        initialEventType="OVERHAUL"
        initialDescription="Full mechanical bearing overhaul"
        initialTechnician="lead_tech_sarah"
        onSuccess={onSuccess}
      />
    );

    expect(screen.getByDisplayValue("MOT-1001")).toBeInTheDocument();
    expect(screen.getByDisplayValue("101")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Full mechanical bearing overhaul")).toBeInTheDocument();

    const submitBtn = screen.getByRole("button", { name: /create work order/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith({
        machine_id: "MOT-1001",
        alert_id: 101,
        event_type: "OVERHAUL",
        status: "SCHEDULED",
        description: "Full mechanical bearing overhaul",
        technician: "lead_tech_sarah",
      });
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it("updates existing work order status from SCHEDULED to IN_PROGRESS", async () => {
    const updateSpy = vi.spyOn(api.maintenance, "update").mockResolvedValue({
      ...mockMaintenance[0],
      status: "IN_PROGRESS",
      technician: "field_tech_dave",
    });

    const onSuccess = vi.fn();
    renderWithProviders(
      <UpdateWorkOrderModal
        isOpen={true}
        onClose={vi.fn()}
        item={mockMaintenance[0]}
        onSuccess={onSuccess}
      />
    );

    expect(screen.getByText(/Update Work Order — MNT-201/i)).toBeInTheDocument();

    const statusSelect = screen.getByRole("combobox");
    fireEvent.change(statusSelect, { target: { value: "IN_PROGRESS" } });

    const techInput = screen.getByDisplayValue("lead_tech_sarah");
    fireEvent.change(techInput, { target: { value: "field_tech_dave" } });

    const saveBtn = screen.getByRole("button", { name: /save changes/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(201, {
        status: "IN_PROGRESS",
        technician: "field_tech_dave",
        description: mockMaintenance[0].description,
      });
      expect(onSuccess).toHaveBeenCalled();
    });
  });
});

describe("S22 — Operator Feedback Loop (T-056)", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("edgetwin_token", "operator-jwt-token");
    vi.spyOn(api.auth, "getMe").mockResolvedValue({
      id: 2,
      username: "floor_operator_dan",
      role: "OPERATOR",
      is_active: true,
      created_at: "2026-09-29T00:00:00Z",
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("submits operator ground-truth feedback with CONFIRMED failure outcome", async () => {
    const submitSpy = vi.spyOn(api.feedback, "submit").mockResolvedValue({
      id: 501,
      machine_id: "MOT-1001",
      alert_id: 101,
      feedback_type: "CONFIRMED",
      notes: "Bearing spalling confirmed during teardown",
      user_id: "floor_operator_dan",
      created_at: "2026-09-29T11:30:00Z",
    });

    const onSuccess = vi.fn();
    renderWithProviders(
      <OperatorFeedbackModal
        isOpen={true}
        onClose={vi.fn()}
        machineId="MOT-1001"
        alertId={101}
        predictedRiskBand="CRITICAL"
        failureProbability={0.824}
        onSuccess={onSuccess}
      />
    );

    expect(screen.getByText(/Record Ground-Truth Feedback/i)).toBeInTheDocument();
    expect(screen.getByText(/82.4%/i)).toBeInTheDocument();

    const notesArea = screen.getByPlaceholderText(/record specific teardown findings/i);
    fireEvent.change(notesArea, { target: { value: "Bearing spalling confirmed during teardown" } });

    const submitBtn = screen.getByRole("button", { name: /submit feedback/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(submitSpy).toHaveBeenCalledWith("MOT-1001", {
        alert_id: 101,
        prediction_id: null,
        feedback_type: "CONFIRMED",
        notes: "Bearing spalling confirmed during teardown",
      });
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it("handles duplicate feedback 409 rejection gracefully", async () => {
    vi.spyOn(api.feedback, "submit").mockRejectedValue(
      new Error("Feedback has already been submitted for alert '101'.")
    );

    renderWithProviders(
      <OperatorFeedbackModal
        isOpen={true}
        onClose={vi.fn()}
        machineId="MOT-1001"
        alertId={101}
      />
    );

    const submitBtn = screen.getByRole("button", { name: /submit feedback/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/feedback has already been submitted for alert '101'/i)).toBeInTheDocument();
    });
  });
});
