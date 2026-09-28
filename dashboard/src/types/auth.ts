/**
 * Authentication and RBAC type definitions for EdgeTwin AI.
 */

export type UserRole = "ADMIN" | "MAINTENANCE_ENGINEER" | "OPERATOR";

export interface AuthUser {
  id: number;
  username: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface LoginPayload {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  role: UserRole;
  username: string;
}

export interface AuthState {
  user: AuthUser | null;
  token: string | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}
