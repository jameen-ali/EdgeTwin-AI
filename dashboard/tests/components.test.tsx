import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Button } from "../src/components/common/Button";
import { StatusBadge } from "../src/components/common/StatusBadge";
import { HealthBadge } from "../src/components/common/HealthBadge";
import { Metric } from "../src/components/common/Metric";
import { RoleGate } from "../src/components/common/RoleGate";
import { EmptyState } from "../src/components/common/EmptyState";
import { ErrorState } from "../src/components/common/ErrorState";
import * as authHook from "../src/hooks/useAuth";

describe("UI Foundation Component Kit", () => {
  it("renders Button with proper text and handles onClick", () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Acknowledge</Button>);

    const btn = screen.getByRole("button", { name: /acknowledge/i });
    expect(btn).toBeInTheDocument();
    fireEvent.click(btn);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("disables Button when isLoading is true", () => {
    render(<Button isLoading>Submit</Button>);
    const btn = screen.getByRole("button");
    expect(btn).toBeDisabled();
  });

  it("renders StatusBadge with non-color-only text and icon", () => {
    const { rerender } = render(<StatusBadge status="RUNNING" />);
    expect(screen.getByText("RUNNING")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveAttribute("aria-label", "Status: RUNNING");

    rerender(<StatusBadge status="TRIPPED" />);
    expect(screen.getByText("TRIPPED")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveAttribute("aria-label", "Status: TRIPPED");
  });

  it("renders HealthBadge with geometric symbol and accessible label", () => {
    const { rerender } = render(<HealthBadge state="HEALTHY" />);
    expect(screen.getByText("HEALTHY")).toBeInTheDocument();
    expect(screen.getByText("●")).toBeInTheDocument();

    rerender(<HealthBadge state="WARNING" />);
    expect(screen.getByText("WARNING")).toBeInTheDocument();
    expect(screen.getByText("▲")).toBeInTheDocument();

    rerender(<HealthBadge state="CRITICAL" />);
    expect(screen.getByText("CRITICAL")).toBeInTheDocument();
    expect(screen.getByText("■")).toBeInTheDocument();
  });

  it("renders Metric card with label, value, and unit", () => {
    render(
      <Metric
        label="Rotational Speed"
        value="1,532"
        unit="RPM"
        status="success"
      />
    );

    expect(screen.getByText("Rotational Speed")).toBeInTheDocument();
    expect(screen.getByText("1,532")).toBeInTheDocument();
    expect(screen.getByText("RPM")).toBeInTheDocument();
  });

  it("RoleGate renders children when user role matches allowedRoles", () => {
    vi.spyOn(authHook, "useAuth").mockReturnValue({
      user: { id: 1, username: "admin", role: "ADMIN", is_active: true, created_at: "" },
      token: "mock-token",
      role: "ADMIN",
      isAuthenticated: true,
      isLoading: false,
      error: null,
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    render(
      <RoleGate allowedRoles={["ADMIN"]}>
        <div data-testid="admin-panel">Admin Secret Controls</div>
      </RoleGate>
    );

    expect(screen.getByTestId("admin-panel")).toBeInTheDocument();
  });

  it("RoleGate renders fallback or null when role does not match", () => {
    vi.spyOn(authHook, "useAuth").mockReturnValue({
      user: { id: 2, username: "operator", role: "OPERATOR", is_active: true, created_at: "" },
      token: "mock-token",
      role: "OPERATOR",
      isAuthenticated: true,
      isLoading: false,
      error: null,
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    render(
      <RoleGate allowedRoles={["ADMIN"]} fallback={<div>Access Denied</div>}>
        <div data-testid="admin-panel">Admin Secret Controls</div>
      </RoleGate>
    );

    expect(screen.queryByTestId("admin-panel")).not.toBeInTheDocument();
    expect(screen.getByText("Access Denied")).toBeInTheDocument();
  });

  it("renders EmptyState with truthful title and description", () => {
    render(
      <EmptyState
        title="No active machines"
        description="Waiting for edge telemetry stream..."
      />
    );

    expect(screen.getByText("No active machines")).toBeInTheDocument();
    expect(screen.getByText("Waiting for edge telemetry stream...")).toBeInTheDocument();
  });

  it("renders ErrorState with RFC 7807 problem detail and retry action", () => {
    const handleRetry = vi.fn();
    render(
      <ErrorState
        title="Ingestion Error"
        problem={{ status: 422, detail: "Schema validation failed on sequence_id" }}
        onRetry={handleRetry}
      />
    );

    expect(screen.getByText("[HTTP 422] Ingestion Error")).toBeInTheDocument();
    expect(screen.getByText("Schema validation failed on sequence_id")).toBeInTheDocument();

    const retryBtn = screen.getByRole("button", { name: /retry request/i });
    fireEvent.click(retryBtn);
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });
});
