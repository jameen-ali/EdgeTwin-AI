/**
 * Centralized Authentication Context & Provider for EdgeTwin AI.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { AuthUser, AuthState, LoginPayload, UserRole } from "../types/auth";
import { api, setUnauthorizedHandler } from "../api/client";

interface AuthContextValue extends AuthState {
  login: (payload: LoginPayload) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => {
    try {
      return localStorage.getItem("edgetwin_token");
    } catch {
      return null;
    }
  });

  const [user, setUser] = useState<AuthUser | null>(null);
  const [role, setRole] = useState<UserRole | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const logout = useCallback(() => {
    try {
      localStorage.removeItem("edgetwin_token");
    } catch {
      // ignore
    }
    setToken(null);
    setUser(null);
    setRole(null);
    setError(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const currentToken = localStorage.getItem("edgetwin_token");
    if (!currentToken) {
      setUser(null);
      setRole(null);
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      const profile = await api.auth.getMe();
      setUser(profile);
      setRole(profile.role);
      setError(null);
    } catch (err: unknown) {
      // Token invalid or expired
      logout();
    } finally {
      setIsLoading(false);
    }
  }, [logout]);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      logout();
    });

    refreshUser();

    return () => {
      setUnauthorizedHandler(null);
    };
  }, [logout, refreshUser]);

  const login = async (payload: LoginPayload) => {
    setIsLoading(true);
    setError(null);

    try {
      const res = await api.auth.login(payload);
      try {
        localStorage.setItem("edgetwin_token", res.access_token);
      } catch {
        // ignore
      }
      setToken(res.access_token);
      setRole(res.role);

      // Fetch full authenticated user record
      const profile = await api.auth.getMe();
      setUser(profile);
      setRole(profile.role);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Authentication failed";
      setError(msg);
      logout();
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const value: AuthContextValue = {
    user,
    token,
    role,
    isAuthenticated: !!token && !!user,
    isLoading,
    error,
    login,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
