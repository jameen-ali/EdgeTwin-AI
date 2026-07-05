// ─── Production Schedules ─────────────────────────────────────────────────────

export interface ProductionSchedule {
  schedule_id: string;
  machine_id: string;
  machine_name: string;
  product: string;
  batch_id: string;
  planned_start: string;
  planned_end: string;
  actual_start: string | null;
  actual_end: string | null;
  status: 'scheduled' | 'in_progress' | 'completed' | 'delayed' | 'cancelled';
  units_planned: number;
  units_completed: number;
  delay_reason: string | null;
}

const now = Date.now();
const hour = 3600_000;

export const mockProductionSchedules: ProductionSchedule[] = [
  {
    schedule_id: 'SCH-001',
    machine_id: 'MCH-001',
    machine_name: 'CNC Mill #1',
    product: 'Gear Housing — Part #GH-2045',
    batch_id: 'BATCH-2025-0701',
    planned_start: new Date(now - 8 * hour).toISOString(),
    planned_end: new Date(now + 4 * hour).toISOString(),
    actual_start: new Date(now - 8 * hour).toISOString(),
    actual_end: null,
    status: 'in_progress',
    units_planned: 200,
    units_completed: 142,
    delay_reason: null,
  },
  {
    schedule_id: 'SCH-002',
    machine_id: 'MCH-002',
    machine_name: 'Conveyor Belt #3',
    product: 'Assembly Line Transfer',
    batch_id: 'BATCH-2025-0702',
    planned_start: new Date(now - 6 * hour).toISOString(),
    planned_end: new Date(now + 6 * hour).toISOString(),
    actual_start: new Date(now - 6 * hour).toISOString(),
    actual_end: null,
    status: 'delayed',
    units_planned: 500,
    units_completed: 180,
    delay_reason: 'Belt misalignment causing intermittent stops',
  },
  {
    schedule_id: 'SCH-003',
    machine_id: 'MCH-003',
    machine_name: 'Hydraulic Press #5',
    product: 'Chassis Frame Stamping — Part #CF-1120',
    batch_id: 'BATCH-2025-0703',
    planned_start: new Date(now - 4 * hour).toISOString(),
    planned_end: new Date(now + 8 * hour).toISOString(),
    actual_start: new Date(now - 4 * hour).toISOString(),
    actual_end: null,
    status: 'in_progress',
    units_planned: 80,
    units_completed: 28,
    delay_reason: null,
  },
  {
    schedule_id: 'SCH-004',
    machine_id: 'MCH-005',
    machine_name: 'Turbine Generator #1',
    product: 'Power Generation',
    batch_id: 'BATCH-2025-0704',
    planned_start: new Date(now - 24 * hour).toISOString(),
    planned_end: new Date(now + 24 * hour).toISOString(),
    actual_start: new Date(now - 24 * hour).toISOString(),
    actual_end: null,
    status: 'delayed',
    units_planned: 1000,
    units_completed: 420,
    delay_reason: 'Bearing seizure risk — operating at reduced capacity',
  },
  {
    schedule_id: 'SCH-005',
    machine_id: 'MCH-008',
    machine_name: 'Injection Molder #1',
    product: 'Dashboard Panel — Part #DP-3301',
    batch_id: 'BATCH-2025-0705',
    planned_start: new Date(now - 10 * hour).toISOString(),
    planned_end: new Date(now + 2 * hour).toISOString(),
    actual_start: new Date(now - 10 * hour).toISOString(),
    actual_end: null,
    status: 'delayed',
    units_planned: 300,
    units_completed: 165,
    delay_reason: 'Heater zone 3 failure — repair in progress',
  },
  {
    schedule_id: 'SCH-006',
    machine_id: 'MCH-007',
    machine_name: 'Lathe Machine #4',
    product: 'Drive Shaft — Part #DS-4420',
    batch_id: 'BATCH-2025-0706',
    planned_start: new Date(now + 2 * hour).toISOString(),
    planned_end: new Date(now + 10 * hour).toISOString(),
    actual_start: null,
    actual_end: null,
    status: 'scheduled',
    units_planned: 150,
    units_completed: 0,
    delay_reason: null,
  },
  {
    schedule_id: 'SCH-007',
    machine_id: 'MCH-006',
    machine_name: 'Welding Robot #2',
    product: 'Body Panel Welding — Part #BP-5510',
    batch_id: 'BATCH-2025-0707',
    planned_start: new Date(now - 12 * hour).toISOString(),
    planned_end: new Date(now - 2 * hour).toISOString(),
    actual_start: new Date(now - 12 * hour).toISOString(),
    actual_end: new Date(now - 1.5 * hour).toISOString(),
    status: 'completed',
    units_planned: 120,
    units_completed: 120,
    delay_reason: null,
  },
  {
    schedule_id: 'SCH-008',
    machine_id: 'MCH-001',
    machine_name: 'CNC Mill #1',
    product: 'Transmission Casing — Part #TC-8810',
    batch_id: 'BATCH-2025-0708',
    planned_start: new Date(now + 6 * hour).toISOString(),
    planned_end: new Date(now + 18 * hour).toISOString(),
    actual_start: null,
    actual_end: null,
    status: 'scheduled',
    units_planned: 100,
    units_completed: 0,
    delay_reason: null,
  },
];
