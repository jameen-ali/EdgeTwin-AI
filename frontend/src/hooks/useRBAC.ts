import { useAuth } from './useAuth';
import type { UserRole } from '@/types';

/**
 * Hook for Role-Based Access Control checks in JSX.
 * Example:
 *   const { can } = useRBAC();
 *   if (can('assign_mechanic')) { ... }
 */

type Permission =
  | 'report_issue'
  | 'ignore_alert'
  | 'assign_mechanic'
  | 'submit_repair_report'
  | 'enter_cost'
  | 'close_ticket'
  | 'view_risk_matrix'
  | 'view_expense_graphs'
  | 'manage_users'
  | 'view_all_machines'
  | 'view_audit_logs';

const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  operator: ['report_issue', 'ignore_alert'],
  mechanic: ['submit_repair_report'],
  maintenance_manager: [
    'assign_mechanic',
    'enter_cost',
    'close_ticket',
    'view_risk_matrix',
    'view_all_machines',
  ],
  production_manager: ['view_risk_matrix', 'view_all_machines'],
  factory_owner: ['view_risk_matrix', 'view_expense_graphs', 'view_all_machines'],
  admin: ['manage_users', 'view_audit_logs', 'view_all_machines'],
};

export function useRBAC() {
  const { role } = useAuth();

  const can = (permission: Permission): boolean => {
    if (!role) return false;
    return ROLE_PERMISSIONS[role]?.includes(permission) ?? false;
  };

  const canAny = (...permissions: Permission[]): boolean =>
    permissions.some((p) => can(p));

  const canAll = (...permissions: Permission[]): boolean =>
    permissions.every((p) => can(p));

  return { can, canAny, canAll, role };
}
