import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import type { UserRole } from '@/types';

// ─── ProtectedRoute: require authenticated user ───────────────────────────────
export function ProtectedRoute() {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Outlet />;
}

// ─── RoleRoute: restrict to specific roles ────────────────────────────────────
interface RoleRouteProps {
  allowedRoles: UserRole[];
}

export function RoleRoute({ allowedRoles }: RoleRouteProps) {
  const { isAuthenticated, hasRole, dashboardRoute } = useAuth();

  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (!hasRole(...allowedRoles)) return <Navigate to={dashboardRoute} replace />;

  return <Outlet />;
}

// ─── GuestRoute: redirect authenticated users to their dashboard ──────────────
export function GuestRoute() {
  const { isAuthenticated, dashboardRoute } = useAuth();
  if (isAuthenticated) return <Navigate to={dashboardRoute} replace />;
  return <Outlet />;
}

// ─── RootRedirect: redirect from / to appropriate place ──────────────────────
export function RootRedirect() {
  const { isAuthenticated, dashboardRoute } = useAuth();
  if (isAuthenticated) return <Navigate to={dashboardRoute} replace />;
  return <Navigate to="/login" replace />;
}
