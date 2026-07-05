// ─── Real Auth Service ────────────────────────────────────────────────────────
// Calls the FastAPI backend at http://localhost:8000/api/v1/auth/*
// The login endpoint uses OAuth2PasswordRequestForm (form-encoded, not JSON).

import api from './api';
import type { AuthTokens, LoginCredentials, User } from '@/types';

export const authService = {
  /**
   * Login — POSTs to /api/v1/auth/login as OAuth2 form data.
   * Returns real JWT tokens and fetches the user profile via /auth/me.
   */
  async login(credentials: LoginCredentials): Promise<{ tokens: AuthTokens; user: User }> {
    // FastAPI OAuth2PasswordRequestForm requires application/x-www-form-urlencoded
    const formData = new URLSearchParams();
    formData.append('username', credentials.email);
    formData.append('password', credentials.password);

    const { data: tokens } = await api.post<AuthTokens>(
      `/auth/login`,
      formData,
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    );

    // Fetch user profile using the new access token
    const { data: user } = await api.get<User>(`/auth/me`, {
      headers: { Authorization: `Bearer ${tokens.access_token}` },
    });

    return { tokens, user };
  },

  async logout(): Promise<void> {
    localStorage.clear();
  },

  async refreshToken(refreshToken: string): Promise<AuthTokens> {
    const { data } = await api.post<AuthTokens>(`/auth/refresh`, {
      refresh_token: refreshToken,
    });
    return data;
  },

  async me(): Promise<User> {
    const stored = localStorage.getItem('edgetwin_user');
    if (stored) {
      return JSON.parse(stored) as User;
    }
    throw new Error('Not authenticated');
  },
};
