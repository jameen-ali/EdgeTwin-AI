import { useEffect, useRef, useCallback } from 'react';
import { useAppDispatch } from '@/store';
import { addAlert, updateAlert, addNotification } from '@/store/alertSlice';
import { updateTicket } from '@/store/ticketSlice';
import { updateMechanicStatus } from '@/store/mechanicSlice';
import type { WSEvent, Alert, Ticket } from '@/types';
import { WS_BASE_URL, ACCESS_TOKEN_KEY } from '@/constants';
import { useToast } from '@/hooks/useToast';

export function useSocket() {
  const dispatch = useAppDispatch();
  const { toast } = useToast();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_DELAY_MS = 3000;

  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const wsEvent = JSON.parse(event.data as string) as WSEvent;

        switch (wsEvent.type) {
          case 'alert_new':
            dispatch(addAlert(wsEvent.payload as Alert));
            dispatch(addNotification({
              id: crypto.randomUUID(),
              type: 'alert_new',
              title: 'New Alert',
              message: `Machine alert triggered`,
              timestamp: wsEvent.timestamp,
              read: false,
              entity_id: (wsEvent.payload as Alert).alert_id,
            }));
            toast({
              title: 'New Alert Detected',
              description: `A machine has triggered a new alert.`,
              variant: 'destructive',
            });
            break;

          case 'alert_escalated':
            dispatch(updateAlert({
              ...(wsEvent.payload as Partial<Alert>),
              alert_id: (wsEvent.payload as Alert).alert_id,
              auto_escalated: true,
            }));
            dispatch(addNotification({
              id: crypto.randomUUID(),
              type: 'alert_escalated',
              title: 'Alert Escalated',
              message: `Alert auto-escalated to Maintenance Manager`,
              timestamp: wsEvent.timestamp,
              read: false,
            }));
            break;

          case 'ticket_assigned':
          case 'ticket_updated':
          case 'ticket_closed':
            dispatch(updateTicket(wsEvent.payload as Partial<Ticket> & { ticket_id: string }));
            dispatch(addNotification({
              id: crypto.randomUUID(),
              type: wsEvent.type,
              title: 'Ticket Updated',
              message: `Ticket status changed`,
              timestamp: wsEvent.timestamp,
              read: false,
              entity_id: (wsEvent.payload as Ticket).ticket_id,
            }));
            toast({
              title: 'Ticket Update',
              description: `A maintenance ticket has been updated.`,
            });
            break;

          case 'mechanic_status':
            dispatch(updateMechanicStatus(
              wsEvent.payload as { mechanic_id: string; login_status: 'available' | 'busy' | 'offline' }
            ));
            break;

          default:
            break;
        }
      } catch (e) {
        console.error('[WS] Failed to parse message', e);
      }
    },
    [dispatch]
  );

  const connect = useCallback(() => {
    const token = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (!token) return;

    const url = `${WS_BASE_URL}/ws?token=${token}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectAttemptsRef.current = 0;
      console.info('[WS] Connected');
    };

    ws.onmessage = handleMessage;

    ws.onclose = () => {
      console.warn('[WS] Disconnected');
      if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttemptsRef.current++;
        reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
      }
    };

    ws.onerror = (err) => console.error('[WS] Error', err);
  }, [handleMessage]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const sendHeartbeat = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'heartbeat' }));
    }
  }, []);

  return { sendHeartbeat };
}
