/**
 * Role-Based Access Control (RBAC) helpers for frontend authorization gating.
 *
 * NOTE: Frontend RBAC is strictly for UX customization (hiding buttons/tabs).
 * Backend RBAC remains the authoritative security boundary.
 */

import { UserRole } from "../types/auth";

export const ALL_ROLES: UserRole[] = ["ADMIN", "MAINTENANCE_ENGINEER", "OPERATOR"];
export const PRIVILEGED_ROLES: UserRole[] = ["ADMIN", "MAINTENANCE_ENGINEER"];
export const ADMIN_ONLY: UserRole[] = ["ADMIN"];

/**
 * Check if the user role matches a required role.
 */
export function hasRole(userRole: UserRole | null | undefined, requiredRole: UserRole): boolean {
  if (!userRole) return false;
  return userRole === requiredRole;
}

/**
 * Check if the user role is present in a set of allowed roles.
 */
export function hasAnyRole(
  userRole: UserRole | null | undefined,
  allowedRoles: UserRole[] | readonly UserRole[]
): boolean {
  if (!userRole) return false;
  return allowedRoles.includes(userRole);
}

/**
 * Check if role can view machines and telemetry.
 */
export function canViewMachines(userRole: UserRole | null | undefined): boolean {
  return hasAnyRole(userRole, ALL_ROLES);
}

/**
 * Check if role can acknowledge or resolve alerts.
 */
export function canAcknowledgeAlerts(userRole: UserRole | null | undefined): boolean {
  return hasAnyRole(userRole, PRIVILEGED_ROLES);
}

/**
 * Check if role can trigger chaos / scenario injections.
 */
export function canInjectScenario(userRole: UserRole | null | undefined): boolean {
  return hasAnyRole(userRole, PRIVILEGED_ROLES);
}

/**
 * Check if role can submit feedback (e.g., false alarm, maintenance confirmed).
 */
export function canSubmitFeedback(userRole: UserRole | null | undefined): boolean {
  return hasAnyRole(userRole, ALL_ROLES);
}

/**
 * Check if role can perform platform administration (user management, settings).
 */
export function canManageSettings(userRole: UserRole | null | undefined): boolean {
  return hasAnyRole(userRole, ADMIN_ONLY);
}
