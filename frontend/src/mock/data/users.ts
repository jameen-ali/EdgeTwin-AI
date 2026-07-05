// ─── Demo Users ───────────────────────────────────────────────────────────────
import type { User } from '@/types';

export const DEMO_PASSWORD = 'EdgeTwin@2026';

export const mockUsers: User[] = [
  {
    user_id: '00000000-0000-0000-0000-000000000001',
    name: 'Alex Morgan',
    email: 'operator@edgetwin.ai',
    role: 'operator',
    is_active: true,
    created_at: '2025-01-15T08:00:00Z',
  },
  {
    user_id: '00000000-0000-0000-0000-000000000002',
    name: 'Sarah Chen',
    email: 'manager@edgetwin.ai',
    role: 'maintenance_manager',
    is_active: true,
    created_at: '2025-01-10T08:00:00Z',
  },
  {
    user_id: '00000000-0000-0000-0000-000000000003',
    name: 'Raj Patel',
    email: 'technician@edgetwin.ai',
    role: 'mechanic',
    is_active: true,
    created_at: '2025-02-01T08:00:00Z',
  },
  {
    user_id: '00000000-0000-0000-0000-000000000004',
    name: 'Diana Osei',
    email: 'production@edgetwin.ai',
    role: 'production_manager',
    is_active: true,
    created_at: '2025-01-20T08:00:00Z',
  },
  {
    user_id: '00000000-0000-0000-0000-000000000005',
    name: 'Marcus Liu',
    email: 'owner@edgetwin.ai',
    role: 'factory_owner',
    is_active: true,
    created_at: '2025-01-05T08:00:00Z',
  },
  {
    user_id: '00000000-0000-0000-0000-000000000006',
    name: 'System Admin',
    email: 'admin@edgetwin.ai',
    role: 'admin',
    is_active: true,
    created_at: '2025-01-01T08:00:00Z',
  },
];
