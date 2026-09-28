import React from "react";
import { useAuth } from "../../hooks/useAuth";
import { UserRole } from "../../types/auth";
import { hasAnyRole } from "../../utils/rbac";

export interface RoleGateProps {
  allowedRoles: UserRole[] | readonly UserRole[];
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

export const RoleGate: React.FC<RoleGateProps> = ({
  allowedRoles,
  fallback = null,
  children,
}) => {
  const { role } = useAuth();

  if (!hasAnyRole(role, allowedRoles)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};
