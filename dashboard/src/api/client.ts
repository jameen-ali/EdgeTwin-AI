/**
 * Typed API Client for EdgeTwin backend with RFC 7807 problem details parsing.
 */

import { ApiError, ProblemDetails, HealthResponse } from "../types/api";
import { AuthUser, LoginPayload, TokenResponse } from "../types/auth";
import { MachineSummary } from "../types/machine";
import { AlertItem } from "../types/alert";
import { ScenarioSummary } from "../types/scenario";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

type UnauthorizedHandler = () => void;
let unauthorizedHandler: UnauthorizedHandler | null = null;

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null) {
  unauthorizedHandler = handler;
}

function getStoredToken(): string | null {
  try {
    return localStorage.getItem("edgetwin_token");
  } catch {
    return null;
  }
}

interface RequestOptions extends RequestInit {
  timeoutMs?: number;
}

export async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { timeoutMs = 15000, headers = {}, ...rest } = options;

  const url = `${API_BASE_URL}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  const token = getStoredToken();

  const reqHeaders: Record<string, string> = {
    Accept: "application/json",
    ...((headers as Record<string, string>) || {}),
  };

  if (token) {
    reqHeaders["Authorization"] = `Bearer ${token}`;
  }

  if (options.body && typeof options.body === "string" && !reqHeaders["Content-Type"]) {
    reqHeaders["Content-Type"] = "application/json";
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...rest,
      headers: reqHeaders,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      if (response.status === 401 && unauthorizedHandler) {
        unauthorizedHandler();
      }

      let problem: ProblemDetails | undefined;
      let errorMsg = `HTTP Error ${response.status}: ${response.statusText}`;

      try {
        const text = await response.text();
        if (text) {
          problem = JSON.parse(text);
          if (problem?.detail) {
            errorMsg = typeof problem.detail === "string" ? problem.detail : JSON.stringify(problem.detail);
          } else if (problem?.title) {
            errorMsg = problem.title;
          }
        }
      } catch {
        // Body was not JSON
      }

      throw new ApiError(errorMsg, response.status, problem);
    }

    // 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return (await response.json()) as T;
  } catch (error: unknown) {
    clearTimeout(timeoutId);

    if (error instanceof ApiError) {
      throw error;
    }

    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("Request timed out", 408);
    }

    const message = error instanceof Error ? error.message : "Network error";
    throw new ApiError(message, 0);
  }
}

/* ==========================================================================
   API Service Namespaces
   ========================================================================== */

export const api = {
  auth: {
    login: (credentials: LoginPayload): Promise<TokenResponse> => {
      return request<TokenResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify(credentials),
      });
    },

    getMe: (): Promise<AuthUser> => {
      return request<AuthUser>("/auth/me", {
        method: "GET",
      });
    },
  },

  machines: {
    list: (): Promise<MachineSummary[]> => {
      return request<MachineSummary[]>("/machines", {
        method: "GET",
      });
    },

    get: (machineId: string): Promise<MachineSummary> => {
      return request<MachineSummary>(`/machines/${encodeURIComponent(machineId)}`, {
        method: "GET",
      });
    },
  },

  alerts: {
    list: (params?: { machine_id?: string; severity?: string; active_only?: boolean }): Promise<AlertItem[]> => {
      const searchParams = new URLSearchParams();
      if (params?.machine_id) searchParams.append("machine_id", params.machine_id);
      if (params?.severity) searchParams.append("severity", params.severity);
      if (params?.active_only !== undefined) searchParams.append("active_only", String(params.active_only));

      const queryStr = searchParams.toString();
      return request<AlertItem[]>(`/alerts${queryStr ? `?${queryStr}` : ""}`, {
        method: "GET",
      });
    },

    acknowledge: (alertId: number): Promise<{ message: string }> => {
      return request<{ message: string }>(`/alerts/${alertId}/acknowledge`, {
        method: "POST",
      });
    },
  },

  scenarios: {
    list: (): Promise<ScenarioSummary[]> => {
      return request<ScenarioSummary[]>("/scenarios", {
        method: "GET",
      });
    },
  },

  health: {
    check: (): Promise<HealthResponse> => {
      // Backend /health root endpoint is at /health or /api/v1/health
      return request<HealthResponse>("/health", {
        method: "GET",
      });
    },
  },
};
