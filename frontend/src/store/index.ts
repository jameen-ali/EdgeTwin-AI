import { configureStore } from '@reduxjs/toolkit';
import { useDispatch, useSelector, type TypedUseSelectorHook } from 'react-redux';
import authReducer from './authSlice';
import alertReducer from './alertSlice';
import ticketReducer from './ticketSlice';
import mechanicReducer from './mechanicSlice';
import productionReducer from './productionSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    alerts: alertReducer,
    tickets: ticketReducer,
    mechanics: mechanicReducer,
    production: productionReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: false,
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// Typed hooks
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
