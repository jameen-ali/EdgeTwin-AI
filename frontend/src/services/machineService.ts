import api from './api';
import type { Machine, SensorReading, MLPrediction, PaginatedResponse } from '@/types';

export const machineService = {
  async getAll(): Promise<Machine[]> {
    const { data } = await api.get<Machine[]>('/machines');
    return data;
  },

  async getById(id: string): Promise<Machine> {
    const { data } = await api.get<Machine>(`/machines/${id}`);
    return data;
  },

  async getSensorReadings(
    id: string,
    limit = 100,
    _offset = 0 // Offset is ignored by simple API currently, but kept for signature compatibility
  ): Promise<PaginatedResponse<SensorReading>> {
    const { data } = await api.get<SensorReading[]>(`/machines/${id}/sensors?limit=${limit}`);
    return {
      items: data,
      total: data.length, // approximation
      page: 1,
      size: limit,
      pages: 1,
    };
  },

  async getLatestPrediction(id: string): Promise<MLPrediction | null> {
    try {
      const { data } = await api.get<MLPrediction[]>(`/machines/${id}/predictions?limit=1`);
      return data.length > 0 ? data[0] : null;
    } catch (e) {
      return null;
    }
  },

  async getAllPredictions(): Promise<MLPrediction[]> {
    // There isn't a global predictions endpoint yet, so this might fail. We return empty array for now.
    return [];
  },

  async createMachine(payload: any): Promise<Machine> {
    const { data } = await api.post<Machine>('/machines', payload);
    return data;
  },

  async updateMachine(id: string, payload: any): Promise<Machine> {
    const { data } = await api.put<Machine>(`/machines/${id}`, payload);
    return data;
  },

  async deleteMachine(id: string): Promise<void> {
    await api.delete(`/machines/${id}`);
  },
};
