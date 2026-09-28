import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { request, setUnauthorizedHandler } from "../src/api/client";
import { ApiError } from "../src/types/api";

describe("API Client & RFC 7807 Error Handling", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    localStorage.clear();
    setUnauthorizedHandler(null);
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("injects Bearer token from localStorage into Authorization header", async () => {
    localStorage.setItem("edgetwin_token", "test-mock-jwt-token");

    let capturedHeaders: Record<string, string> = {};

    global.fetch = vi.fn().mockImplementation((_url, init) => {
      capturedHeaders = init?.headers as Record<string, string>;
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ success: true }),
      });
    });

    const res = await request<{ success: boolean }>("/test-endpoint");
    expect(res.success).toBe(true);
    expect(capturedHeaders["Authorization"]).toBe("Bearer test-mock-jwt-token");
    expect(capturedHeaders["Accept"]).toBe("application/json");
  });

  it("parses RFC 7807 problem details on 400+ responses", async () => {
    const problemPayload = {
      type: "https://tools.ietf.org/html/rfc7807",
      title: "Bad Request",
      status: 400,
      detail: "Invalid telemetry payload format.",
    };

    global.fetch = vi.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: false,
        status: 400,
        statusText: "Bad Request",
        text: () => Promise.resolve(JSON.stringify(problemPayload)),
      });
    });

    try {
      await request("/test-fail");
      expect.fail("Should have thrown ApiError");
    } catch (err: unknown) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(400);
      expect(apiErr.message).toBe("Invalid telemetry payload format.");
      expect(apiErr.problem?.detail).toBe("Invalid telemetry payload format.");
    }
  });

  it("triggers unauthorized callback on 401 response", async () => {
    const unauthorizedCallback = vi.fn();
    setUnauthorizedHandler(unauthorizedCallback);

    global.fetch = vi.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        text: () => Promise.resolve(JSON.stringify({ detail: "Token expired" })),
      });
    });

    try {
      await request("/protected-route");
    } catch {
      // expected error
    }

    expect(unauthorizedCallback).toHaveBeenCalledTimes(1);
  });

  it("handles 204 No Content cleanly without JSON parsing errors", async () => {
    global.fetch = vi.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 204,
      });
    });

    const res = await request<{}>("/no-content-route");
    expect(res).toEqual({});
  });
});
