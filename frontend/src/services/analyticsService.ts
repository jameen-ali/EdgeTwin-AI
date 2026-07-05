// ─── Analytics & Admin Services ──────────────────────────────────────────
import type { RiskOverview, ExpenseSummary, AuditLog, User, PaginatedResponse, ProductionImpact } from '@/types';
import type { ProductionSchedule } from '@/mock/data/production-schedules';
import type { FactoryStats } from '@/mock/data/analytics';
import { mockStore } from '@/mock/store';
import { mockMonthlyExpenses, mockRiskOverview, mockProductionImpact } from '@/mock/data/analytics';
import api from './api';

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

// ─── Analytics Service ────────────────────────────────────────────────────────
export const analyticsService = {
  async getRiskOverview(): Promise<RiskOverview[]> {
    try {
      const { data } = await api.get<RiskOverview[]>('/production/risk-overview');
      return data;
    } catch {
      // Fallback to mock data if API fails
      await delay(300);
      return structuredClone(mockRiskOverview);
    }
  },

  async getExpenseSummary(range: 'month' | 'year'): Promise<ExpenseSummary[]> {
    try {
      const { data } = await api.get<ExpenseSummary[]>(`/owner/expenses?range=${range}`);
      if (data && data.length > 0) return data;
    } catch {
      // fallback
    }
    // Fallback to mock if API returns empty or fails
    await delay(400);
    if (range === 'year') {
      const yearMap = new Map<string, ExpenseSummary>();
      for (const m of mockMonthlyExpenses) {
        const year = m.period.slice(0, 4);
        const existing = yearMap.get(year);
        if (existing) {
          existing.total_cost += m.total_cost;
          existing.ticket_count += m.ticket_count;
          existing.avg_repair_time = (existing.avg_repair_time + m.avg_repair_time) / 2;
        } else {
          yearMap.set(year, { ...structuredClone(m), period: year });
        }
      }
      return Array.from(yearMap.values());
    }
    return structuredClone(mockMonthlyExpenses);
  },

  async getProductionImpact(): Promise<ProductionImpact[]> {
    try {
      const { data } = await api.get<ProductionImpact[]>('/owner/impact');
      if (data && data.length > 0) return data;
    } catch {
      // fallback
    }
    await delay(300);
    return structuredClone(mockProductionImpact);
  },

  async getFactoryStats(): Promise<FactoryStats> {
    try {
      const { data } = await api.get<FactoryStats>('/owner/stats');
      return data;
    } catch {
      // fallback
      await delay(200);
      return structuredClone(mockStore.factoryStats);
    }
  },

  async getProductionSchedules(): Promise<ProductionSchedule[]> {
    try {
      const { data } = await api.get<ProductionSchedule[]>('/production/schedules');
      return data;
    } catch {
      await delay(300);
      return structuredClone(mockStore.productionSchedules);
    }
  },

  async updateScheduleStatus(
    scheduleId: string,
    status: ProductionSchedule['status'],
    reason?: string,
  ): Promise<ProductionSchedule> {
    await delay(300);
    const idx = mockStore.productionSchedules.findIndex((s) => s.schedule_id === scheduleId);
    if (idx === -1) throw new Error(`Schedule ${scheduleId} not found`);

    mockStore.productionSchedules[idx] = {
      ...mockStore.productionSchedules[idx],
      status,
      delay_reason: reason ?? mockStore.productionSchedules[idx].delay_reason,
    };

    return structuredClone(mockStore.productionSchedules[idx]);
  },

  async reallocateLoad(sourceMachineId: string, targetMachineId: string): Promise<void> {
    try {
      await api.post('/production/reallocate', { source: sourceMachineId, target: targetMachineId });
    } catch {
      await delay(500);
    }
    // Also update mock data for immediate UI feedback
    const sourceIdx = mockRiskOverview.findIndex(r => r.machine_id === sourceMachineId);
    if (sourceIdx !== -1) {
      mockRiskOverview[sourceIdx].risk_level = 'low';
      mockRiskOverview[sourceIdx].health_score = 95;
      mockRiskOverview[sourceIdx].rul_hours = 5000;
    }
  },
};

// ─── Admin Service ────────────────────────────────────────────────────────────
export const adminService = {
  async getUsers(role?: string): Promise<User[]> {
    const response = await api.get('/admin/users');
    let users = response.data;
    if (role) {
      users = users.filter((u: User) => u.role === role);
    }
    return users;
  },

  async createUser(payload: {
    name: string;
    email: string;
    password: string;
    role: User['role'];
  }): Promise<User> {
    const response = await api.post('/admin/users', Object.assign({}, payload, { is_active: true }));
    return response.data;
  },

  async updateUser(
    id: string,
    payload: Partial<{ name: string; email: string; is_active: boolean }>
  ): Promise<User> {
    const response = await api.put(`/admin/users/${id}`, payload);
    return response.data;
  },

  async deactivateUser(id: string): Promise<void> {
    await api.delete(`/admin/users/${id}`);
  },

  async getAuditLogs(
    page = 1,
    size = 50
  ): Promise<PaginatedResponse<AuditLog>> {
    const skip = (page - 1) * size;
    const response = await api.get(`/admin/audit-logs?skip=${skip}&limit=${size}`);
    return response.data;
  },
};

// ─── Notification Service ─────────────────────────────────────────────────────
export const notificationService = {
  async getAll(): Promise<import('@/types').Notification[]> {
    await delay(200);
    return structuredClone(mockStore.notifications);
  },

  async markAsRead(id: string): Promise<void> {
    await delay(100);
    const n = mockStore.notifications.find((n) => n.id === id);
    if (n) n.read = true;
  },

  async markAllAsRead(): Promise<void> {
    await delay(100);
    mockStore.notifications.forEach((n) => { n.read = true; });
  },
};
