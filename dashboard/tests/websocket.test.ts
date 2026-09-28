import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { TwinWebSocketClient } from "../src/api/websocket";
import { WebSocketMessage } from "../src/types/websocket";

class MockWebSocket {
  public static instances: MockWebSocket[] = [];
  public url: string;
  public readyState: number = 0; // CONNECTING
  public onopen: (() => void) | null = null;
  public onmessage: ((event: { data: string }) => void) | null = null;
  public onerror: ((event: unknown) => void) | null = null;
  public onclose: ((event: { code: number; reason: string }) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    setTimeout(() => {
      this.readyState = 1; // OPEN
      if (this.onopen) this.onopen();
    }, 10);
  }

  public send = vi.fn();
  public close(code = 1000, reason = "") {
    this.readyState = 3; // CLOSED
    if (this.onclose) this.onclose({ code, reason });
  }
}

describe("TwinWebSocketClient", () => {
  const originalWebSocket = global.WebSocket;

  beforeEach(() => {
    localStorage.clear();
    MockWebSocket.instances = [];
    // @ts-expect-error Mocking browser WebSocket
    global.WebSocket = MockWebSocket;
  });

  afterEach(() => {
    global.WebSocket = originalWebSocket;
    vi.restoreAllMocks();
  });

  it("connects to /ws/live with encoded token parameter", async () => {
    localStorage.setItem("edgetwin_token", "jwt-token-alpha");

    let status = "DISCONNECTED";
    const client = new TwinWebSocketClient({
      onStatusChange: (s) => {
        status = s;
      },
    });

    client.connect();
    expect(status).toBe("CONNECTING");

    await new Promise((r) => setTimeout(r, 20));
    expect(status).toBe("CONNECTED");
    expect(MockWebSocket.instances.length).toBe(1);
    expect(MockWebSocket.instances[0].url).toContain("/ws/live?token=jwt-token-alpha");

    client.dispose();
  });

  it("parses incoming twin_update message and calls onMessage callback", async () => {
    localStorage.setItem("edgetwin_token", "jwt-token-beta");

    let receivedMsg: WebSocketMessage | null = null;
    const client = new TwinWebSocketClient({
      onMessage: (msg) => {
        receivedMsg = msg;
      },
    });

    client.connect();
    await new Promise((r) => setTimeout(r, 20));

    const mockWs = MockWebSocket.instances[0];
    const updateEvent: WebSocketMessage = {
      event: "twin_update",
      data: {
        machine_id: "MOT-1001",
        machine_type: "Induction Motor",
        operating_state: "RUNNING",
        health_state: "HEALTHY",
        connectivity_state: "LIVE",
        health_score: 98.5,
        failure_probability: 0.04,
        risk_band: "NORMAL",
        anomaly_score: -0.12,
        last_telemetry_at: "2026-09-28T12:00:00Z",
        last_prediction_at: "2026-09-28T12:00:00Z",
        reported: {},
        derived: {},
      },
    };

    mockWs.onmessage?.({ data: JSON.stringify(updateEvent) });

    expect(receivedMsg).not.toBeNull();
    const msg = receivedMsg as unknown as WebSocketMessage;
    expect(msg.event).toBe("twin_update");
    expect((msg as unknown as { data: { machine_id: string } }).data.machine_id).toBe("MOT-1001");

    client.dispose();
  });

  it("does not auto-reconnect if server closes connection with 1008 (Policy Violation)", async () => {
    localStorage.setItem("edgetwin_token", "invalid-token");

    let status = "DISCONNECTED";
    const client = new TwinWebSocketClient({
      onStatusChange: (s) => {
        status = s;
      },
    });

    client.connect();
    await new Promise((r) => setTimeout(r, 20));

    const mockWs = MockWebSocket.instances[0];
    mockWs.close(1008, "Policy Violation");

    expect(status).toBe("DISCONNECTED");

    // Wait 50ms - should not have spawned a new connection
    await new Promise((r) => setTimeout(r, 50));
    expect(MockWebSocket.instances.length).toBe(1);

    client.dispose();
  });
});
