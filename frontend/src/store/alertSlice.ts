import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { Alert, Notification } from '@/types';

interface AlertState {
  alerts: Alert[];
  notifications: Notification[];
  unreadCount: number;
}

const initialState: AlertState = {
  alerts: [],
  notifications: [],
  unreadCount: 0,
};

const alertSlice = createSlice({
  name: 'alerts',
  initialState,
  reducers: {
    setAlerts(state, action: PayloadAction<Alert[]>) {
      state.alerts = action.payload;
    },
    addAlert(state, action: PayloadAction<Alert>) {
      const exists = state.alerts.find((a) => a.alert_id === action.payload.alert_id);
      if (!exists) {
        state.alerts.unshift(action.payload);
      }
    },
    updateAlert(state, action: PayloadAction<Partial<Alert> & { alert_id: string }>) {
      const idx = state.alerts.findIndex((a) => a.alert_id === action.payload.alert_id);
      if (idx !== -1) {
        state.alerts[idx] = { ...state.alerts[idx], ...action.payload };
      }
    },
    addNotification(state, action: PayloadAction<Notification>) {
      state.notifications.unshift(action.payload);
      state.unreadCount += 1;
    },
    markAllRead(state) {
      state.notifications = state.notifications.map((n) => ({ ...n, read: true }));
      state.unreadCount = 0;
    },
    markNotificationRead(state, action: PayloadAction<string>) {
      const n = state.notifications.find((n) => n.id === action.payload);
      if (n && !n.read) {
        n.read = true;
        state.unreadCount = Math.max(0, state.unreadCount - 1);
      }
    },
    clearNotifications(state) {
      state.notifications = [];
      state.unreadCount = 0;
    },
  },
});

export const {
  setAlerts,
  addAlert,
  updateAlert,
  addNotification,
  markAllRead,
  markNotificationRead,
  clearNotifications,
} = alertSlice.actions;

export default alertSlice.reducer;
