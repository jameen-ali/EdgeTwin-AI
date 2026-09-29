/**
 * Typed API Client for EdgeTwin backend with RFC 7807 problem details parsing.
 */

import { ApiError, ProblemDetails, HealthResponse } from "../types/api";
export { ApiError };
import { AuthUser, LoginPayload, TokenResponse } from "../types/auth";
import {
  MachineSummary,
  MachineDetail,
  TwinState,
  TelemetryPoint,
  PredictionRecord,
  normalizeMachine,
} from "../types/machine";
import { AlertItem, AlertAcknowledgePayload } from "../types/alert";
import {
  MaintenanceItem,
  MaintenanceCreatePayload,
  MaintenanceUpdatePayload,
} from "../types/maintenance";
import { FeedbackItem, FeedbackCreatePayload } from "../types/feedback";
import {
  ScenarioSummary,
  ScenarioInjectPayload,
  ScenarioInjectResponse,
} from "../types/scenario";
import {
  MLOpsOverview,
  DriftReport,
  PerformanceMetrics,
  RetrainRequestPayload,
  ChallengerResult,
  PromotionGate,
  PromotionResult,
  RollbackRequestPayload,
  RollbackResult,
  ModelRegistry,
  AuditLog,
} from "../types/mlops";

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
    list: async (params?: { limit?: number; offset?: number; status?: string }): Promise<MachineSummary[]> => {
      const searchParams = new URLSearchParams();
      if (params?.limit) searchParams.append("limit", String(params.limit));
      if (params?.offset) searchParams.append("offset", String(params.offset));
      if (params?.status) searchParams.append("status", params.status);

      const queryStr = searchParams.toString();
      const res = await request<MachineSummary[] | { items: MachineSummary[]; total: number }>(
        `/machines${queryStr ? `?${queryStr}` : ""}`,
        { method: "GET" }
      );
      if (Array.isArray(res)) return res.map((m) => normalizeMachine(m));
      if (res && typeof res === "object" && Array.isArray((res as { items?: MachineSummary[] }).items)) {
        return (res as { items: MachineSummary[] }).items.map((m) => normalizeMachine(m));
      }
      return [];
    },

    get: async (machineId: string): Promise<MachineSummary> => {
      const res = await request<MachineSummary>(`/machines/${encodeURIComponent(machineId)}`, {
        method: "GET",
      });
      return normalizeMachine(res);
    },

    getDetail: (machineId: string): Promise<MachineDetail> => {
      return request<MachineDetail>(`/machines/${encodeURIComponent(machineId)}`, {
        method: "GET",
      });
    },

    getTwin: (machineId: string): Promise<TwinState> => {
      return request<TwinState>(`/machines/${encodeURIComponent(machineId)}/twin`, {
        method: "GET",
      });
    },

    getTelemetry: async (
      machineId: string,
      params?: {
        limit?: number;
        offset?: number;
        before?: string;
        after?: string;
        seq_min?: number;
        seq_max?: number;
      }
    ): Promise<TelemetryPoint[]> => {
      const searchParams = new URLSearchParams();
      if (params?.limit) searchParams.append("limit", String(params.limit));
      if (params?.offset) searchParams.append("offset", String(params.offset));
      if (params?.before) searchParams.append("before", params.before);
      if (params?.after) searchParams.append("after", params.after);
      if (params?.seq_min !== undefined) searchParams.append("seq_min", String(params.seq_min));
      if (params?.seq_max !== undefined) searchParams.append("seq_max", String(params.seq_max));

      const queryStr = searchParams.toString();
      const res = await request<TelemetryPoint[] | { items: TelemetryPoint[]; total: number }>(
        `/machines/${encodeURIComponent(machineId)}/telemetry${queryStr ? `?${queryStr}` : ""}`,
        { method: "GET" }
      );
      if (Array.isArray(res)) return res;
      if (res && typeof res === "object" && Array.isArray((res as { items?: TelemetryPoint[] }).items)) {
        return (res as { items: TelemetryPoint[] }).items;
      }
      return [];
    },

    getPredictions: async (
      machineId: string,
      params?: {
        limit?: number;
        offset?: number;
        before?: string;
        after?: string;
      }
    ): Promise<PredictionRecord[]> => {
      const searchParams = new URLSearchParams();
      if (params?.limit) searchParams.append("limit", String(params.limit));
      if (params?.offset) searchParams.append("offset", String(params.offset));
      if (params?.before) searchParams.append("before", params.before);
      if (params?.after) searchParams.append("after", params.after);

      const queryStr = searchParams.toString();
      const res = await request<PredictionRecord[] | { items: PredictionRecord[]; total: number }>(
        `/machines/${encodeURIComponent(machineId)}/predictions${queryStr ? `?${queryStr}` : ""}`,
        { method: "GET" }
      );
      if (Array.isArray(res)) return res;
      if (res && typeof res === "object" && Array.isArray((res as { items?: PredictionRecord[] }).items)) {
        return (res as { items: PredictionRecord[] }).items;
      }
      return [];
    },
  },

  alerts: {
    list: async (params?: {
      machine_id?: string;
      severity?: string;
      status?: string;
      acknowledged?: boolean;
      active_only?: boolean;
      limit?: number;
      offset?: number;
    }): Promise<AlertItem[]> => {
      const searchParams = new URLSearchParams();
      if (params?.machine_id) searchParams.append("machine_id", params.machine_id);
      if (params?.severity) searchParams.append("severity", params.severity);
      if (params?.status) searchParams.append("status", params.status);
      if (params?.acknowledged !== undefined) searchParams.append("acknowledged", String(params.acknowledged));
      if (params?.active_only !== undefined && params?.status === undefined) {
        searchParams.append("status", "OPEN");
      }
      if (params?.limit) searchParams.append("limit", String(params.limit));
      if (params?.offset) searchParams.append("offset", String(params.offset));

      const queryStr = searchParams.toString();
      const res = await request<AlertItem[] | { items: AlertItem[]; total: number }>(
        `/alerts${queryStr ? `?${queryStr}` : ""}`,
        { method: "GET" }
      );
      if (Array.isArray(res)) return res;
      if (res && typeof res === "object" && Array.isArray((res as { items?: AlertItem[] }).items)) {
        return (res as { items: AlertItem[] }).items;
      }
      return [];
    },

    get: (alertId: number): Promise<AlertItem> => {
      return request<AlertItem>(`/alerts/${alertId}`, {
        method: "GET",
      });
    },

    acknowledge: (alertId: number, payload?: AlertAcknowledgePayload): Promise<AlertItem> => {
      return request<AlertItem>(`/alerts/${alertId}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: "ACKNOWLEDGED",
          notes: payload?.notes,
          resolved_by: payload?.resolved_by,
        }),
      });
    },

    resolve: (alertId: number, payload?: AlertAcknowledgePayload): Promise<AlertItem> => {
      return request<AlertItem>(`/alerts/${alertId}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: "RESOLVED",
          notes: payload?.notes,
          resolved_by: payload?.resolved_by,
        }),
      });
    },
  },

  maintenance: {
    list: async (params?: {
      machine_id?: string;
      status?: string;
      event_type?: string;
      limit?: number;
      offset?: number;
    }): Promise<MaintenanceItem[]> => {
      const searchParams = new URLSearchParams();
      if (params?.machine_id) searchParams.append("machine_id", params.machine_id);
      if (params?.status) searchParams.append("status", params.status);
      if (params?.event_type) searchParams.append("event_type", params.event_type);
      if (params?.limit) searchParams.append("limit", String(params.limit));
      if (params?.offset) searchParams.append("offset", String(params.offset));

      const queryStr = searchParams.toString();
      const res = await request<MaintenanceItem[] | { items: MaintenanceItem[]; total: number }>(
        `/maintenance${queryStr ? `?${queryStr}` : ""}`,
        { method: "GET" }
      );
      if (Array.isArray(res)) return res;
      if (res && typeof res === "object" && Array.isArray((res as { items?: MaintenanceItem[] }).items)) {
        return (res as { items: MaintenanceItem[] }).items;
      }
      return [];
    },

    get: (id: number): Promise<MaintenanceItem> => {
      return request<MaintenanceItem>(`/maintenance/${id}`, {
        method: "GET",
      });
    },

    create: (payload: MaintenanceCreatePayload): Promise<MaintenanceItem> => {
      return request<MaintenanceItem>("/maintenance", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },

    update: (id: number, payload: MaintenanceUpdatePayload): Promise<MaintenanceItem> => {
      return request<MaintenanceItem>(`/maintenance/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    },

    getByMachine: async (
      machineId: string,
      params?: { status?: string; limit?: number; offset?: number }
    ): Promise<MaintenanceItem[]> => {
      const searchParams = new URLSearchParams();
      if (params?.status) searchParams.append("status", params.status);
      if (params?.limit) searchParams.append("limit", String(params.limit));
      if (params?.offset) searchParams.append("offset", String(params.offset));

      const queryStr = searchParams.toString();
      const res = await request<MaintenanceItem[] | { items: MaintenanceItem[]; total: number }>(
        `/machines/${encodeURIComponent(machineId)}/maintenance${queryStr ? `?${queryStr}` : ""}`,
        { method: "GET" }
      );
      if (Array.isArray(res)) return res;
      if (res && typeof res === "object" && Array.isArray((res as { items?: MaintenanceItem[] }).items)) {
        return (res as { items: MaintenanceItem[] }).items;
      }
      return [];
    },

    createForMachine: (
      machineId: string,
      payload: Omit<MaintenanceCreatePayload, "machine_id">
    ): Promise<MaintenanceItem> => {
      return request<MaintenanceItem>(`/machines/${encodeURIComponent(machineId)}/maintenance`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
  },

  feedback: {
    submit: (machineId: string, payload: FeedbackCreatePayload): Promise<FeedbackItem> => {
      return request<FeedbackItem>(`/machines/${encodeURIComponent(machineId)}/feedback`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },

    getByMachine: async (
      machineId: string,
      params?: { limit?: number; offset?: number }
    ): Promise<FeedbackItem[]> => {
      const searchParams = new URLSearchParams();
      if (params?.limit) searchParams.append("limit", String(params.limit));
      if (params?.offset) searchParams.append("offset", String(params.offset));

      const queryStr = searchParams.toString();
      const res = await request<FeedbackItem[] | { items: FeedbackItem[]; total: number }>(
        `/machines/${encodeURIComponent(machineId)}/feedback${queryStr ? `?${queryStr}` : ""}`,
        { method: "GET" }
      );
      if (Array.isArray(res)) return res;
      if (res && typeof res === "object" && Array.isArray((res as { items?: FeedbackItem[] }).items)) {
        return (res as { items: FeedbackItem[] }).items;
      }
      return [];
    },
  },

  scenarios: {
    list: async (): Promise<ScenarioSummary[]> => {
      const res = await request<
        ScenarioSummary[] | { items?: ScenarioSummary[]; scenarios?: ScenarioSummary[]; total?: number }
      >("/scenarios", {
        method: "GET",
      });
      if (Array.isArray(res)) return res;
      if (res && typeof res === "object") {
        if (Array.isArray((res as { scenarios?: ScenarioSummary[] }).scenarios)) {
          return (res as { scenarios: ScenarioSummary[] }).scenarios!;
        }
        if (Array.isArray((res as { items?: ScenarioSummary[] }).items)) {
          return (res as { items: ScenarioSummary[] }).items!;
        }
      }
      return [];
    },

    inject: (payload: ScenarioInjectPayload): Promise<ScenarioInjectResponse> => {
      return request<ScenarioInjectResponse>("/scenarios/inject", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
  },

  mlops: {
    getOverview: (params?: { window_hours?: number; window_days?: number }): Promise<MLOpsOverview> => {
      const searchParams = new URLSearchParams();
      if (params?.window_hours) searchParams.append("window_hours", String(params.window_hours));
      if (params?.window_days) searchParams.append("window_days", String(params.window_days));
      const queryStr = searchParams.toString();
      return request<MLOpsOverview>(`/mlops/overview${queryStr ? `?${queryStr}` : ""}`, {
        method: "GET",
      });
    },

    getDrift: (params?: { window_hours?: number; limit?: number }): Promise<DriftReport> => {
      const searchParams = new URLSearchParams();
      if (params?.window_hours) searchParams.append("window_hours", String(params.window_hours));
      if (params?.limit) searchParams.append("limit", String(params.limit));
      const queryStr = searchParams.toString();
      return request<DriftReport>(`/mlops/drift${queryStr ? `?${queryStr}` : ""}`, {
        method: "GET",
      });
    },

    getPerformance: (params?: { window?: string; window_days?: number }): Promise<PerformanceMetrics> => {
      const searchParams = new URLSearchParams();
      if (params?.window) searchParams.append("window", params.window);
      if (params?.window_days) searchParams.append("window_days", String(params.window_days));
      const queryStr = searchParams.toString();
      return request<PerformanceMetrics>(`/mlops/performance${queryStr ? `?${queryStr}` : ""}`, {
        method: "GET",
      });
    },
  },

  retrain: {
    run: (payload?: RetrainRequestPayload): Promise<ChallengerResult> => {
      return request<ChallengerResult>("/retrain/run", {
        method: "POST",
        body: JSON.stringify(payload || {}),
      });
    },

    getGate: (): Promise<PromotionGate> => {
      return request<PromotionGate>("/retrain/gate", {
        method: "GET",
      });
    },

    promote: (): Promise<PromotionResult> => {
      return request<PromotionResult>("/retrain/promote", {
        method: "POST",
      });
    },

    rollback: (payload: RollbackRequestPayload): Promise<RollbackResult> => {
      return request<RollbackResult>("/retrain/rollback", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },

    getRegistry: (): Promise<ModelRegistry> => {
      return request<ModelRegistry>("/retrain/registry", {
        method: "GET",
      });
    },

    getAuditLog: (params?: { limit?: number }): Promise<AuditLog> => {
      const searchParams = new URLSearchParams();
      if (params?.limit) searchParams.append("limit", String(params.limit));
      const queryStr = searchParams.toString();
      return request<AuditLog>(`/retrain/audit-log${queryStr ? `?${queryStr}` : ""}`, {
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
