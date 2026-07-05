import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { Mechanic } from '@/types';

interface MechanicState {
  mechanics: Mechanic[];
  availableMechanics: Mechanic[];
}

const initialState: MechanicState = {
  mechanics: [],
  availableMechanics: [],
};

const mechanicSlice = createSlice({
  name: 'mechanics',
  initialState,
  reducers: {
    setMechanics(state, action: PayloadAction<Mechanic[]>) {
      state.mechanics = action.payload;
      state.availableMechanics = action.payload.filter(
        (m) => m.login_status === 'available'
      );
    },
    updateMechanicStatus(
      state,
      action: PayloadAction<{ mechanic_id: string; login_status: Mechanic['login_status'] }>
    ) {
      const m = state.mechanics.find((m) => m.mechanic_id === action.payload.mechanic_id);
      if (m) {
        m.login_status = action.payload.login_status;
      }
      state.availableMechanics = state.mechanics.filter(
        (m) => m.login_status === 'available'
      );
    },
  },
});

export const { setMechanics, updateMechanicStatus } = mechanicSlice.actions;
export default mechanicSlice.reducer;
