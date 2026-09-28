/**
 * Reusable WebSocket connection manager for live Digital Twin streaming.
 */

import { WebSocketStatus, WebSocketMessage } from "../types/websocket";

export interface WebSocketOptions {
  machineId?: string | null;
  token?: string | null;
  onMessage?: (message: WebSocketMessage) => void;
  onStatusChange?: (status: WebSocketStatus) => void;
  autoReconnect?: boolean;
}

export class TwinWebSocketClient {
  private ws: WebSocket | null = null;
  private status: WebSocketStatus = "DISCONNECTED";
  private reconnectTimeoutId: number | null = null;
  private pingIntervalId: number | null = null;
  private reconnectAttempts = 0;
  private maxReconnectDelay = 15000;
  private isDisposed = false;

  private options: WebSocketOptions;

  constructor(options: WebSocketOptions = {}) {
    this.options = options;
  }

  public connect(): void {
    if (this.isDisposed) return;
    this.cleanup();

    const token = this.options.token || localStorage.getItem("edgetwin_token");
    if (!token) {
      this.updateStatus("DISCONNECTED");
      return;
    }

    this.updateStatus("CONNECTING");

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const path = this.options.machineId
      ? `/ws/live/${encodeURIComponent(this.options.machineId)}`
      : `/ws/live`;

    const wsUrl = `${protocol}//${host}${path}?token=${encodeURIComponent(token)}`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.updateStatus("CONNECTED");
        this.startKeepalive();
      };

      this.ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as WebSocketMessage;
          if (this.options.onMessage) {
            this.options.onMessage(parsed);
          }
        } catch {
          // Non-JSON frame (e.g. plain pong text)
        }
      };

      this.ws.onerror = () => {
        this.updateStatus("ERROR");
      };

      this.ws.onclose = (event) => {
        this.stopKeepalive();
        this.updateStatus("DISCONNECTED");

        // Do not auto-reconnect if closed due to policy violation (invalid token)
        if (event.code === 1008) {
          return;
        }

        if (this.options.autoReconnect !== false && !this.isDisposed) {
          this.scheduleReconnect();
        }
      };
    } catch {
      this.updateStatus("ERROR");
      if (this.options.autoReconnect !== false && !this.isDisposed) {
        this.scheduleReconnect();
      }
    }
  }

  public disconnect(): void {
    this.cleanup();
    this.updateStatus("DISCONNECTED");
  }

  public dispose(): void {
    this.isDisposed = true;
    this.disconnect();
  }

  public send(text: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(text);
    }
  }

  private updateStatus(newStatus: WebSocketStatus): void {
    if (this.status !== newStatus) {
      this.status = newStatus;
      if (this.options.onStatusChange) {
        this.options.onStatusChange(newStatus);
      }
    }
  }

  private startKeepalive(): void {
    this.stopKeepalive();
    this.pingIntervalId = window.setInterval(() => {
      this.send("ping");
    }, 15000);
  }

  private stopKeepalive(): void {
    if (this.pingIntervalId !== null) {
      clearInterval(this.pingIntervalId);
      this.pingIntervalId = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimeoutId !== null) {
      clearTimeout(this.reconnectTimeoutId);
    }

    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), this.maxReconnectDelay);
    this.reconnectAttempts++;

    this.reconnectTimeoutId = window.setTimeout(() => {
      if (!this.isDisposed) {
        this.connect();
      }
    }, delay);
  }

  private cleanup(): void {
    this.stopKeepalive();
    if (this.reconnectTimeoutId !== null) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }
    if (this.ws) {
      this.ws.onopen = null;
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.onmessage = null;
      if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) {
        this.ws.close();
      }
      this.ws = null;
    }
  }
}
