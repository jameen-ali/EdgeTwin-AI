import { useAppSelector, useAppDispatch } from '@/store';
import { logout } from '@/store/authSlice';
import { authService } from '@/services/authService';
import type { UserRole } from '@/types';
import { ROLE_DASHBOARD_ROUTES } from '@/constants';

export function useAuth() {
  const dispatch = useAppDispatch();
  const { user, isAuthenticated, isLoading, accessToken } = useAppSelector((s) => s.auth);

  const signOut = async () => {
    try {
      await authService.logout();
    } finally {
      dispatch(logout());
    }
  };

  const hasRole = (...roles: UserRole[]): boolean => {
    if (!user) return false;
    return roles.includes(user.role);
  };

  const dashboardRoute = user
    ? ROLE_DASHBOARD_ROUTES[user.role]
    : '/login';

  return {
    user,
    isAuthenticated,
    isLoading,
    signOut,
    hasRole,
    dashboardRoute,
    role: user?.role,
    token: accessToken,
  };
}
