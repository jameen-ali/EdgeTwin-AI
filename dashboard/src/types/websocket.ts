/**
 * WebSocket streaming protocol types for live twin state.
 */

import { TwinState } from "./machine";

export type WebSocketStatus = "CONNECTING" | "CONNECTED" | "DISCONNECTED" | "ERROR";

export interface WebSocketSnapshotMessage {
  event: "snapshot";
  data: TwinState[] | TwinState | null;
  message?: string;
}

export interface WebSocketUpdateMessage {
  event: "twin_update";
  data: TwinState;
}

export interface WebSocketPongMessage {
  event: "pong";
  data: string;
}

export interface WebSocketErrorMessage {
  event: "error";
  data: string;
}

export type WebSocketMessage =
  | WebSocketSnapshotMessage
  | WebSocketUpdateMessage
  | WebSocketPongMessage
  | WebSocketErrorMessage;
