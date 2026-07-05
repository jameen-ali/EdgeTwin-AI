import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { analyticsService } from '@/services/analyticsService';
import type { RiskOverview, ProductionImpact } from '@/types';
import type { ProductionSchedule } from '@/mock/data/production-schedules'; // or define it here if needed

interface LocalFactoryStats {
  total_machines: number;
  machines_operational: number;
  machines_critical: number;
  avg_health_score: number;
  open_tickets: number;
}

interface ProductionState {
  stats: LocalFactoryStats | null;
  riskData: RiskOverview[];
  impactData: ProductionImpact[];
  schedules: ProductionSchedule[];
  status: 'idle' | 'loading' | 'succeeded' | 'failed';
  error: string | null;
}

const initialState: ProductionState = {
  stats: null,
  riskData: [],
  impactData: [],
  schedules: [],
  status: 'idle',
  error: null,
};

export const fetchProductionData = createAsyncThunk(
  'production/fetchProductionData',
  async () => {
    const [stats, risk, impact, schedules] = await Promise.all([
      analyticsService.getFactoryStats() as unknown as Promise<LocalFactoryStats>,
      analyticsService.getRiskOverview(),
      analyticsService.getProductionImpact(),
      analyticsService.getProductionSchedules()
    ]);
    return { stats, risk, impact, schedules };
  }
);

export const reallocateProductionLoad = createAsyncThunk(
  'production/reallocate',
  async ({ source, target }: { source: string; target: string }, { dispatch }) => {
    await analyticsService.reallocateLoad(source, target);
    // After reallocation, we want to immediately fetch fresh data from the backend
    // to update the UI (Schedules, Risk Overview, etc.)
    await dispatch(fetchProductionData());
    return true;
  }
);

const productionSlice = createSlice({
  name: 'production',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchProductionData.pending, (state) => {
        state.status = 'loading';
      })
      .addCase(fetchProductionData.fulfilled, (state, action) => {
        state.status = 'succeeded';
        state.stats = action.payload.stats;
        state.riskData = action.payload.risk;
        state.impactData = action.payload.impact;
        state.schedules = action.payload.schedules;
      })
      .addCase(fetchProductionData.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.error.message || 'Failed to fetch production data';
      });
  },
});

export default productionSlice.reducer;
