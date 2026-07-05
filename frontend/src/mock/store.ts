// ─── Centralized Mock Store ───────────────────────────────────────────────────
// In-memory store that all mock services read/write. Supports event listeners
// so Redux slices can react to changes (simulating WebSocket push).

import type { User, Machine, Alert, Ticket, Mechanic, Notification, AuditLog, MLPrediction } from '@/types';
import type { ProductionSchedule } from './data/production-schedules';
import type { FactoryStats } from './data/analytics';

import { mockUsers } from './data/users';
import { mockMachines } from './data/machines';
import { mockAlerts } from './data/alerts';
import { mockTickets } from './data/tickets';
import { mockMechanics } from './data/mechanics';
import { mockNotifications } from './data/notifications';
import { mockAuditLogs } from './data/audit-logs';
import { mockPredictions } from './data/predictions';
import { mockProductionSchedules } from './data/production-schedules';
import { mockFactoryStats } from './data/analytics';

export type MockEventType =
  | 'alert_added'
  | 'alert_updated'
  | 'ticket_added'
  | 'ticket_updated'
  | 'mechanic_updated'
  | 'notification_added'
  | 'machine_updated';

type Listener = (event: MockEventType, payload: unknown) => void;

class MockStore {
  // ─── Data ─────────────────────────────────────────────────────────────────
  users: User[];
  machines: Machine[];
  alerts: Alert[];
  tickets: Ticket[];
  mechanics: Mechanic[];
  notifications: Notification[];
  auditLogs: AuditLog[];
  predictions: MLPrediction[];
  productionSchedules: ProductionSchedule[];
  factoryStats: FactoryStats;

  private listeners: Set<Listener> = new Set();
  private nextTicketNum = 7; // TKT-007 next
  private nextAlertNum = 9;
  private nextLogNum = 11;
  private nextNotifNum = 9;

  constructor() {
    // Deep clone so re-imports don't share references
    this.users = structuredClone(mockUsers);
    this.machines = structuredClone(mockMachines);
    this.alerts = structuredClone(mockAlerts);
    this.tickets = structuredClone(mockTickets);
    this.mechanics = structuredClone(mockMechanics);
    this.notifications = structuredClone(mockNotifications);
    this.auditLogs = structuredClone(mockAuditLogs);
    this.predictions = structuredClone(mockPredictions);
    this.productionSchedules = structuredClone(mockProductionSchedules);
    this.factoryStats = structuredClone(mockFactoryStats);
  }

  // ─── Event system ────────────────────────────────────────────────────────
  subscribe(listener: Listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private emit(event: MockEventType, payload: unknown) {
    this.listeners.forEach((fn) => fn(event, payload));
  }

  // ─── ID generators ──────────────────────────────────────────────────────
  nextTicketId(): string {
    return `TKT-${String(this.nextTicketNum++).padStart(3, '0')}`;
  }

  nextAlertId(): string {
    return `ALT-${String(this.nextAlertNum++).padStart(3, '0')}`;
  }

  nextNotificationId(): string {
    return `NTF-${String(this.nextNotifNum++).padStart(3, '0')}`;
  }

  nextAuditLogId(): string {
    return `LOG-${String(this.nextLogNum++).padStart(3, '0')}`;
  }

  // ─── Alert operations ────────────────────────────────────────────────────
  updateAlert(alertId: string, changes: Partial<Alert>) {
    const idx = this.alerts.findIndex((a) => a.alert_id === alertId);
    if (idx !== -1) {
      this.alerts[idx] = { ...this.alerts[idx], ...changes };
      this.emit('alert_updated', this.alerts[idx]);
    }
  }

  // ─── Ticket operations ───────────────────────────────────────────────────
  createTicket(ticket: Ticket) {
    this.tickets.unshift(ticket);
    this.emit('ticket_added', ticket);
  }

  updateTicket(ticketId: string, changes: Partial<Ticket>) {
    const idx = this.tickets.findIndex((t) => t.ticket_id === ticketId);
    if (idx !== -1) {
      this.tickets[idx] = { ...this.tickets[idx], ...changes };
      this.emit('ticket_updated', this.tickets[idx]);
    }
  }

  // ─── Mechanic operations ─────────────────────────────────────────────────
  updateMechanic(mechanicId: string, changes: Partial<Mechanic>) {
    const idx = this.mechanics.findIndex((m) => m.mechanic_id === mechanicId);
    if (idx !== -1) {
      this.mechanics[idx] = { ...this.mechanics[idx], ...changes };
      this.emit('mechanic_updated', this.mechanics[idx]);
    }
  }

  // ─── Notification operations ─────────────────────────────────────────────
  addNotification(notification: Notification) {
    this.notifications.unshift(notification);
    this.emit('notification_added', notification);
  }

  // ─── Machine operations ──────────────────────────────────────────────────
  updateMachine(machineId: string, changes: Partial<Machine>) {
    const idx = this.machines.findIndex((m) => m.machine_id === machineId);
    if (idx !== -1) {
      this.machines[idx] = { ...this.machines[idx], ...changes };
      this.emit('machine_updated', this.machines[idx]);
    }
  }

  // ─── Audit operations ───────────────────────────────────────────────────
  addAuditLog(log: AuditLog) {
    this.auditLogs.unshift(log);
  }

  // ─── User operations ────────────────────────────────────────────────────
  addUser(user: User) {
    this.users.push(user);
  }

  updateUser(userId: string, changes: Partial<User>) {
    const idx = this.users.findIndex((u) => u.user_id === userId);
    if (idx !== -1) {
      this.users[idx] = { ...this.users[idx], ...changes };
    }
  }

  // ─── Reset (for testing) ─────────────────────────────────────────────────
  reset() {
    this.users = structuredClone(mockUsers);
    this.machines = structuredClone(mockMachines);
    this.alerts = structuredClone(mockAlerts);
    this.tickets = structuredClone(mockTickets);
    this.mechanics = structuredClone(mockMechanics);
    this.notifications = structuredClone(mockNotifications);
    this.auditLogs = structuredClone(mockAuditLogs);
    this.predictions = structuredClone(mockPredictions);
    this.productionSchedules = structuredClone(mockProductionSchedules);
    this.factoryStats = structuredClone(mockFactoryStats);
  }
}

// Singleton instance — all services share this
export const mockStore = new MockStore();
