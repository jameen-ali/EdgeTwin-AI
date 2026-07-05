import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { Ticket } from '@/types';

interface TicketState {
  tickets: Ticket[];
  selectedTicketId: string | null;
  isLoading: boolean;
}

const initialState: TicketState = {
  tickets: [],
  selectedTicketId: null,
  isLoading: false,
};

const ticketSlice = createSlice({
  name: 'tickets',
  initialState,
  reducers: {
    setTickets(state, action: PayloadAction<Ticket[]>) {
      state.tickets = action.payload;
    },
    addTicket(state, action: PayloadAction<Ticket>) {
      state.tickets.unshift(action.payload);
    },
    updateTicket(state, action: PayloadAction<Partial<Ticket> & { ticket_id: string }>) {
      const idx = state.tickets.findIndex((t) => t.ticket_id === action.payload.ticket_id);
      if (idx !== -1) {
        state.tickets[idx] = { ...state.tickets[idx], ...action.payload };
      }
    },
    setSelectedTicket(state, action: PayloadAction<string | null>) {
      state.selectedTicketId = action.payload;
    },
    setLoading(state, action: PayloadAction<boolean>) {
      state.isLoading = action.payload;
    },
  },
});

export const { setTickets, addTicket, updateTicket, setSelectedTicket, setLoading } =
  ticketSlice.actions;

export default ticketSlice.reducer;
