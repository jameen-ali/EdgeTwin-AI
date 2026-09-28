import { describe, it, expect } from "vitest";
import {
  hasRole,
  hasAnyRole,
  canViewMachines,
  canAcknowledgeAlerts,
  canInjectScenario,
  canSubmitFeedback,
  canManageSettings,
} from "../src/utils/rbac";
import { UserRole } from "../src/types/auth";

describe("RBAC Utilities", () => {
  it("hasRole correctly checks exact match", () => {
    expect(hasRole("ADMIN", "ADMIN")).toBe(true);
    expect(hasRole("OPERATOR", "ADMIN")).toBe(false);
    expect(hasRole(null, "ADMIN")).toBe(false);
    expect(hasRole(undefined, "OPERATOR")).toBe(false);
  });

  it("hasAnyRole checks role membership in list", () => {
    const privileged: UserRole[] = ["ADMIN", "MAINTENANCE_ENGINEER"];
    expect(hasAnyRole("ADMIN", privileged)).toBe(true);
    expect(hasAnyRole("MAINTENANCE_ENGINEER", privileged)).toBe(true);
    expect(hasAnyRole("OPERATOR", privileged)).toBe(false);
    expect(hasAnyRole(null, privileged)).toBe(false);
  });

  it("canViewMachines allows all authenticated roles", () => {
    expect(canViewMachines("ADMIN")).toBe(true);
    expect(canViewMachines("MAINTENANCE_ENGINEER")).toBe(true);
    expect(canViewMachines("OPERATOR")).toBe(true);
    expect(canViewMachines(null)).toBe(false);
  });

  it("canAcknowledgeAlerts restricts to ADMIN and MAINTENANCE_ENGINEER", () => {
    expect(canAcknowledgeAlerts("ADMIN")).toBe(true);
    expect(canAcknowledgeAlerts("MAINTENANCE_ENGINEER")).toBe(true);
    expect(canAcknowledgeAlerts("OPERATOR")).toBe(false);
    expect(canAcknowledgeAlerts(null)).toBe(false);
  });

  it("canInjectScenario restricts to ADMIN and MAINTENANCE_ENGINEER", () => {
    expect(canInjectScenario("ADMIN")).toBe(true);
    expect(canInjectScenario("MAINTENANCE_ENGINEER")).toBe(true);
    expect(canInjectScenario("OPERATOR")).toBe(false);
  });

  it("canSubmitFeedback permits all roles", () => {
    expect(canSubmitFeedback("ADMIN")).toBe(true);
    expect(canSubmitFeedback("MAINTENANCE_ENGINEER")).toBe(true);
    expect(canSubmitFeedback("OPERATOR")).toBe(true);
  });

  it("canManageSettings is restricted to ADMIN only", () => {
    expect(canManageSettings("ADMIN")).toBe(true);
    expect(canManageSettings("MAINTENANCE_ENGINEER")).toBe(false);
    expect(canManageSettings("OPERATOR")).toBe(false);
    expect(canManageSettings(null)).toBe(false);
  });
});
