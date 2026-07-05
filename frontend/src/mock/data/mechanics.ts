// ─── Mechanics ────────────────────────────────────────────────────────────────
import type { Mechanic } from '@/types';

export const mockMechanics: Mechanic[] = [
  {
    mechanic_id: '00000000-0000-0000-0000-000000000003',
    name: 'Raj Patel',
    email: 'technician@edgetwin.ai',
    skill_type: 'Electrical & Mechanical',
    login_status: 'available',
    current_assignment_id: null,
    shift: 'Morning (6 AM – 2 PM)',
    contact: '+91 98765 43210',
  },
  {
    mechanic_id: 'MEC-002',
    name: 'Kenji Tanaka',
    email: 'kenji.t@edgetwin.ai',
    skill_type: 'Hydraulics & Pneumatics',
    login_status: 'busy',
    current_assignment_id: 'TKT-002',
    shift: 'Morning (6 AM – 2 PM)',
    contact: '+91 98765 43211',
  },
  {
    mechanic_id: 'MEC-003',
    name: 'Maria Garcia',
    email: 'maria.g@edgetwin.ai',
    skill_type: 'Electronics & PLC',
    login_status: 'available',
    current_assignment_id: null,
    shift: 'Afternoon (2 PM – 10 PM)',
    contact: '+91 98765 43212',
  },
  {
    mechanic_id: 'MEC-004',
    name: 'David Okonkwo',
    email: 'david.o@edgetwin.ai',
    skill_type: 'Welding & Fabrication',
    login_status: 'offline',
    current_assignment_id: null,
    shift: 'Night (10 PM – 6 AM)',
    contact: '+91 98765 43213',
  },
];
