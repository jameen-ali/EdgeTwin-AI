import React, { createContext, useContext, useEffect, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/useToast';
import type { Notification, NotificationType } from '@/types';

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const { user, token } = useAuth();
  const { toast } = useToast();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  // WebSocket connection managed inside useEffect

  useEffect(() => {
    if (!user || !token) return;

    // Determine WS URL based on current origin
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.hostname}:8000/ws?token=${token}`;
    
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('[WebSocket] Connected');
      // Ping interval to keep connection alive
      const interval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        }
      }, 30000);
      
      ws.onclose = () => {
        clearInterval(interval);
        console.log('[WebSocket] Disconnected');
      };
    };

    ws.onmessage = (event) => {
      if (event.data === 'pong') return;
      
      try {
        const data = JSON.parse(event.data);
        
        // Handle incoming events
        if (data.type === 'alert_new' || data.type === 'ticket_updated') {
          const newNotif: Notification = {
            id: data.payload.alert_id || data.payload.ticket_id || Date.now().toString(),
            title: data.type === 'alert_new' ? 'New Critical Alert' : 'Ticket Updated',
            message: data.payload.message || 'System status changed',
            type: data.type as NotificationType,
            read: false,
            timestamp: data.timestamp || new Date().toISOString(),
            link: data.type === 'alert_new' ? '/operator/alerts' : '/maintenance/tickets',
          };

          setNotifications(prev => [newNotif, ...prev]);

          toast({
            title: newNotif.title,
            description: newNotif.message,
            variant: data.payload.severity === 'critical' ? 'destructive' : 'default',
          });
        }
      } catch (e) {
        console.error('[WebSocket] Parse error:', e);
      }
    };

    // Optional: store ws ref if needed elsewhere
    return () => {
      ws.close();
    };
  }, [user, token, toast]);

  const markAsRead = (id: string) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  };

  const markAllAsRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <NotificationContext.Provider value={{ notifications, unreadCount, markAsRead, markAllAsRead }}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
}
