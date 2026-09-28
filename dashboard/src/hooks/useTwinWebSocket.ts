/**
 * React hook for live Digital Twin WebSocket subscriptions.
 */

import { useEffect, useState, useRef, useCallback } from "react";
import { TwinState } from "../types/machine";
import { WebSocketStatus, WebSocketMessage } from "../types/websocket";
import { TwinWebSocketClient } from "../api/websocket";

export interface UseTwinWebSocketOptions {
  machineId?: string | null;
  token?: string | null;
  enabled?: boolean;
}

export function useTwinWebSocket(options: UseTwinWebSocketOptions = {}) {
  const { machineId, token, enabled = true } = options;
  const [status, setStatus] = useState<WebSocketStatus>("DISCONNECTED");
  const [twins, setTwins] = useState<Record<string, TwinState>>({});
  const clientRef = useRef<TwinWebSocketClient | null>(null);

  const handleMessage = useCallback((msg: WebSocketMessage) => {
    if (msg.event === "snapshot") {
      if (Array.isArray(msg.data)) {
        const dict: Record<string, TwinState> = {};
        for (const item of msg.data) {
          if (item && item.machine_id) {
            dict[item.machine_id] = item;
          }
        }
        setTwins(dict);
      } else if (msg.data && typeof msg.data === "object" && "machine_id" in msg.data) {
        setTwins((prev) => ({
          ...prev,
          [(msg.data as TwinState).machine_id]: msg.data as TwinState,
        }));
      }
    } else if (msg.event === "twin_update" && msg.data?.machine_id) {
      setTwins((prev) => ({
        ...prev,
        [msg.data.machine_id]: msg.data,
      }));
    }
  }, []);

  useEffect(() => {
    if (!enabled) {
      if (clientRef.current) {
        clientRef.current.dispose();
        clientRef.current = null;
      }
      setStatus("DISCONNECTED");
      return;
    }

    const client = new TwinWebSocketClient({
      machineId,
      token,
      onMessage: handleMessage,
      onStatusChange: setStatus,
      autoReconnect: true,
    });

    clientRef.current = client;
    client.connect();

    return () => {
      client.dispose();
      clientRef.current = null;
    };
  }, [machineId, token, enabled, handleMessage]);

  return {
    status,
    twins,
    twinList: Object.values(twins),
    isConnected: status === "CONNECTED",
  };
}
