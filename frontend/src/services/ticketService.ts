// ─── Real Ticket, Alert & Mechanic Services ──────────────────────────────────
import type { Alert, Ticket, Mechanic, PaginatedResponse } from '@/types';
import api from './api';

// ─── Alert Service ────────────────────────────────────────────────────────────
export const alertService = {
  async getAll(params?: { status?: string; severity?: string }): Promise<Alert[]> {
    const query = new URLSearchParams();
    if (params?.status) query.append('status', params.status);
    if (params?.severity) query.append('severity', params.severity);
    const { data } = await api.get<Alert[]>(`/alerts?${query.toString()}`);
    return data;
  },

  async reportIssue(
    alertId: string,
    payload: { description: string; photo?: File; voice_note?: File },
    operatorId: string,
    _operatorName: string,
  ): Promise<Ticket> {
    const formData = new FormData();
    formData.append('description', payload.description);
    if (payload.photo) formData.append('photo', payload.photo);
    if (payload.voice_note) formData.append('voice_note', payload.voice_note);
    
    // Convert to JSON for now if not using multipart/form-data
    const { data } = await api.post<Ticket>(`/alerts/${alertId}/report`, {
      description: payload.description,
      operator_id: operatorId
    });
    return data;
  },

  async ignoreAlert(alertId: string, userId: string, _userName: string): Promise<void> {
    await api.post(`/alerts/${alertId}/ignore`, { user_id: userId });
  },
};

// ─── Ticket Service ───────────────────────────────────────────────────────────
export const ticketService = {
  async getAll(params?: {
    status?: string;
    page?: number;
    size?: number;
  }): Promise<PaginatedResponse<Ticket>> {
    const query = new URLSearchParams();
    if (params?.status) query.append('status', params.status);
    if (params?.page) query.append('page', params.page.toString());
    if (params?.size) query.append('size', params.size.toString());
    const { data } = await api.get<PaginatedResponse<Ticket>>(`/tickets?${query.toString()}`);
    return data;
  },

  async getById(id: string): Promise<Ticket> {
    const { data } = await api.get<Ticket>(`/tickets/${id}`);
    return data;
  },

  async assignMechanic(
    ticketId: string,
    mechanicId: string,
    managerId: string,
    _managerName: string,
  ): Promise<Ticket> {
    // 1. Update ticket
    const { data: ticket } = await api.put<Ticket>(`/tickets/${ticketId}`, {
      mechanic_id: mechanicId,
      manager_id: managerId,
      status: 'assigned',
    });
    // 2. Update mechanic
    await mechanicService.updateStatus(mechanicId, 'busy', ticketId);
    return ticket;
  },

  async acceptTask(ticketId: string, _mechanicId: string, _mechanicName: string): Promise<Ticket> {
    const { data } = await api.put<Ticket>(`/tickets/${ticketId}`, { status: 'accepted' });
    return data;
  },

  async startTask(ticketId: string): Promise<Ticket> {
    const { data } = await api.put<Ticket>(`/tickets/${ticketId}`, { status: 'in_progress' });
    return data;
  },

  async rejectTask(ticketId: string, mechanicId: string): Promise<Ticket> {
    const { data } = await api.put<Ticket>(`/tickets/${ticketId}`, { status: 'open', mechanic_id: null });
    await mechanicService.updateStatus(mechanicId, 'available', null);
    return data;
  },

  async pauseTask(ticketId: string): Promise<Ticket> {
    const { data } = await api.put<Ticket>(`/tickets/${ticketId}`, { status: 'paused' });
    return data;
  },

  async resumeTask(ticketId: string): Promise<Ticket> {
    const { data } = await api.put<Ticket>(`/tickets/${ticketId}`, { status: 'in_progress' });
    return data;
  },

  async submitRepairReport(
    ticketId: string,
    payload: { repair_report: string; parts_used: string; time_taken_hours: number },
    mechanicId: string,
    _mechanicName: string,
  ): Promise<Ticket> {
    const { data } = await api.put<Ticket>(`/tickets/${ticketId}`, {
      status: 'repaired',
      ...payload
    });
    await mechanicService.updateStatus(mechanicId, 'available', null);
    return data;
  },

  async reviewAndAddCost(
    ticketId: string,
    repairCost: number,
    _managerId: string,
    _managerName: string,
  ): Promise<Ticket> {
    const { data } = await api.put<Ticket>(`/tickets/${ticketId}`, {
      status: 'reviewed',
      repair_cost: repairCost,
    });
    return data;
  },

  async closeTicket(
    ticketId: string,
    _managerId: string,
    _managerName: string,
  ): Promise<Ticket> {
    const { data } = await api.put<Ticket>(`/tickets/${ticketId}`, {
      status: 'closed'
    });
    return data;
  },
};

// ─── Mechanic Service ─────────────────────────────────────────────────────────
export const mechanicService = {
  async getAll(): Promise<Mechanic[]> {
    const { data } = await api.get<Mechanic[]>('/mechanics');
    return data;
  },

  async getAvailable(): Promise<Mechanic[]> {
    const { data } = await api.get<Mechanic[]>('/mechanics');
    return data.filter((m) => m.login_status === 'available');
  },

  async updateStatus(
    mechanicId: string,
    status: 'available' | 'busy' | 'offline',
    current_assignment_id?: string | null
  ): Promise<Mechanic> {
    const payload: any = { login_status: status };
    if (current_assignment_id !== undefined) {
      payload.current_assignment_id = current_assignment_id;
    }
    const { data } = await api.put<Mechanic>(`/mechanics/${mechanicId}/status`, payload);
    return data;
  },

  async getMyTickets(mechanicId: string): Promise<Ticket[]> {
    const { data } = await api.get<PaginatedResponse<Ticket>>(`/tickets`);
    // Filter tickets for this mechanic in memory if no specific query param is passed
    return data.items.filter(t => t.mechanic_id === mechanicId);
  },
};
