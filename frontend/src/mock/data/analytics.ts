// ─── Analytics & Expense Data ─────────────────────────────────────────────────
import type { ExpenseSummary, RiskOverview, ProductionImpact } from '@/types';

// Monthly expense summaries for the past 12 months
export const mockMonthlyExpenses: ExpenseSummary[] = [
  {
    period: '2025-07', total_cost: 28500, ticket_count: 4, avg_repair_time: 2.8,
    machines: [
      { machine_id: 'MCH-001', machine_name: 'CNC Mill #1', total_cost: 3200, ticket_count: 1 },
      { machine_id: 'MCH-004', machine_name: 'Air Compressor #2', total_cost: 12500, ticket_count: 1 },
      { machine_id: 'MCH-003', machine_name: 'Hydraulic Press #5', total_cost: 8750, ticket_count: 1 },
      { machine_id: 'MCH-006', machine_name: 'Welding Robot #2', total_cost: 4050, ticket_count: 1 },
    ],
  },
  {
    period: '2025-06', total_cost: 45200, ticket_count: 6, avg_repair_time: 3.2,
    machines: [
      { machine_id: 'MCH-005', machine_name: 'Turbine Generator #1', total_cost: 22000, ticket_count: 2 },
      { machine_id: 'MCH-002', machine_name: 'Conveyor Belt #3', total_cost: 8700, ticket_count: 2 },
      { machine_id: 'MCH-008', machine_name: 'Injection Molder #1', total_cost: 14500, ticket_count: 2 },
    ],
  },
  {
    period: '2025-05', total_cost: 31800, ticket_count: 5, avg_repair_time: 2.5,
    machines: [
      { machine_id: 'MCH-001', machine_name: 'CNC Mill #1', total_cost: 5600, ticket_count: 1 },
      { machine_id: 'MCH-004', machine_name: 'Air Compressor #2', total_cost: 9800, ticket_count: 1 },
      { machine_id: 'MCH-007', machine_name: 'Lathe Machine #4', total_cost: 4200, ticket_count: 1 },
      { machine_id: 'MCH-006', machine_name: 'Welding Robot #2', total_cost: 7100, ticket_count: 1 },
      { machine_id: 'MCH-003', machine_name: 'Hydraulic Press #5', total_cost: 5100, ticket_count: 1 },
    ],
  },
  {
    period: '2025-04', total_cost: 18900, ticket_count: 3, avg_repair_time: 2.0,
    machines: [
      { machine_id: 'MCH-002', machine_name: 'Conveyor Belt #3', total_cost: 6300, ticket_count: 1 },
      { machine_id: 'MCH-005', machine_name: 'Turbine Generator #1', total_cost: 8400, ticket_count: 1 },
      { machine_id: 'MCH-008', machine_name: 'Injection Molder #1', total_cost: 4200, ticket_count: 1 },
    ],
  },
  {
    period: '2025-03', total_cost: 52400, ticket_count: 7, avg_repair_time: 3.8,
    machines: [
      { machine_id: 'MCH-005', machine_name: 'Turbine Generator #1', total_cost: 28000, ticket_count: 3 },
      { machine_id: 'MCH-004', machine_name: 'Air Compressor #2', total_cost: 15200, ticket_count: 2 },
      { machine_id: 'MCH-001', machine_name: 'CNC Mill #1', total_cost: 4600, ticket_count: 1 },
      { machine_id: 'MCH-006', machine_name: 'Welding Robot #2', total_cost: 4600, ticket_count: 1 },
    ],
  },
  {
    period: '2025-02', total_cost: 22100, ticket_count: 4, avg_repair_time: 2.3,
    machines: [
      { machine_id: 'MCH-002', machine_name: 'Conveyor Belt #3', total_cost: 7500, ticket_count: 1 },
      { machine_id: 'MCH-003', machine_name: 'Hydraulic Press #5', total_cost: 6100, ticket_count: 1 },
      { machine_id: 'MCH-007', machine_name: 'Lathe Machine #4', total_cost: 3800, ticket_count: 1 },
      { machine_id: 'MCH-008', machine_name: 'Injection Molder #1', total_cost: 4700, ticket_count: 1 },
    ],
  },
  {
    period: '2025-01', total_cost: 35600, ticket_count: 5, avg_repair_time: 3.0,
    machines: [
      { machine_id: 'MCH-005', machine_name: 'Turbine Generator #1', total_cost: 18000, ticket_count: 2 },
      { machine_id: 'MCH-004', machine_name: 'Air Compressor #2', total_cost: 11200, ticket_count: 2 },
      { machine_id: 'MCH-001', machine_name: 'CNC Mill #1', total_cost: 6400, ticket_count: 1 },
    ],
  },
  {
    period: '2024-12', total_cost: 29300, ticket_count: 4, avg_repair_time: 2.6,
    machines: [
      { machine_id: 'MCH-002', machine_name: 'Conveyor Belt #3', total_cost: 9200, ticket_count: 1 },
      { machine_id: 'MCH-006', machine_name: 'Welding Robot #2', total_cost: 5800, ticket_count: 1 },
      { machine_id: 'MCH-008', machine_name: 'Injection Molder #1', total_cost: 8100, ticket_count: 1 },
      { machine_id: 'MCH-003', machine_name: 'Hydraulic Press #5', total_cost: 6200, ticket_count: 1 },
    ],
  },
  {
    period: '2024-11', total_cost: 41700, ticket_count: 6, avg_repair_time: 3.4,
    machines: [
      { machine_id: 'MCH-005', machine_name: 'Turbine Generator #1', total_cost: 24000, ticket_count: 3 },
      { machine_id: 'MCH-004', machine_name: 'Air Compressor #2', total_cost: 10500, ticket_count: 2 },
      { machine_id: 'MCH-007', machine_name: 'Lathe Machine #4', total_cost: 7200, ticket_count: 1 },
    ],
  },
  {
    period: '2024-10', total_cost: 19800, ticket_count: 3, avg_repair_time: 2.1,
    machines: [
      { machine_id: 'MCH-001', machine_name: 'CNC Mill #1', total_cost: 5400, ticket_count: 1 },
      { machine_id: 'MCH-002', machine_name: 'Conveyor Belt #3', total_cost: 7800, ticket_count: 1 },
      { machine_id: 'MCH-006', machine_name: 'Welding Robot #2', total_cost: 6600, ticket_count: 1 },
    ],
  },
  {
    period: '2024-09', total_cost: 37500, ticket_count: 5, avg_repair_time: 3.1,
    machines: [
      { machine_id: 'MCH-005', machine_name: 'Turbine Generator #1', total_cost: 16500, ticket_count: 2 },
      { machine_id: 'MCH-008', machine_name: 'Injection Molder #1', total_cost: 11000, ticket_count: 2 },
      { machine_id: 'MCH-004', machine_name: 'Air Compressor #2', total_cost: 10000, ticket_count: 1 },
    ],
  },
  {
    period: '2024-08', total_cost: 24600, ticket_count: 4, avg_repair_time: 2.4,
    machines: [
      { machine_id: 'MCH-003', machine_name: 'Hydraulic Press #5', total_cost: 8900, ticket_count: 1 },
      { machine_id: 'MCH-002', machine_name: 'Conveyor Belt #3', total_cost: 6200, ticket_count: 1 },
      { machine_id: 'MCH-007', machine_name: 'Lathe Machine #4', total_cost: 4100, ticket_count: 1 },
      { machine_id: 'MCH-006', machine_name: 'Welding Robot #2', total_cost: 5400, ticket_count: 1 },
    ],
  },
];

// Risk overview for all machines
export const mockRiskOverview: RiskOverview[] = [
  { machine_id: 'MCH-005', machine_name: 'Turbine Generator #1', location: 'Power House — Unit 1', risk_level: 'critical', health_score: 22.8, rul_hours: 12, open_tickets: 0 },
  { machine_id: 'MCH-004', machine_name: 'Air Compressor #2', location: 'Plant B — Utility Room', risk_level: 'high', health_score: 41.0, rul_hours: 90, open_tickets: 1 },
  { machine_id: 'MCH-008', machine_name: 'Injection Molder #1', location: 'Plant C — Bay 3', risk_level: 'high', health_score: 55.4, rul_hours: 200, open_tickets: 1 },
  { machine_id: 'MCH-002', machine_name: 'Conveyor Belt #3', location: 'Plant A — Bay 3', risk_level: 'medium', health_score: 63.2, rul_hours: 480, open_tickets: 1 },
  { machine_id: 'MCH-006', machine_name: 'Welding Robot #2', location: 'Plant A — Bay 5', risk_level: 'medium', health_score: 78.3, rul_hours: 620, open_tickets: 0 },
  { machine_id: 'MCH-001', machine_name: 'CNC Mill #1', location: 'Plant A — Bay 1', risk_level: 'low', health_score: 87.5, rul_hours: 1240, open_tickets: 0 },
  { machine_id: 'MCH-007', machine_name: 'Lathe Machine #4', location: 'Plant C — Bay 1', risk_level: 'low', health_score: 91.7, rul_hours: 1800, open_tickets: 0 },
  { machine_id: 'MCH-003', machine_name: 'Hydraulic Press #5', location: 'Plant B — Bay 2', risk_level: 'low', health_score: 95.1, rul_hours: 2100, open_tickets: 0 },
];

// Production impact
export const mockProductionImpact: ProductionImpact[] = [
  { machine_id: 'MCH-005', machine_name: 'Turbine Generator #1', downtime_hours: 48, production_loss_percent: 18.5, risk_level: 'critical' },
  { machine_id: 'MCH-004', machine_name: 'Air Compressor #2', downtime_hours: 24, production_loss_percent: 8.2, risk_level: 'high' },
  { machine_id: 'MCH-008', machine_name: 'Injection Molder #1', downtime_hours: 16, production_loss_percent: 6.1, risk_level: 'high' },
  { machine_id: 'MCH-002', machine_name: 'Conveyor Belt #3', downtime_hours: 8, production_loss_percent: 3.4, risk_level: 'medium' },
  { machine_id: 'MCH-006', machine_name: 'Welding Robot #2', downtime_hours: 4, production_loss_percent: 1.8, risk_level: 'medium' },
  { machine_id: 'MCH-001', machine_name: 'CNC Mill #1', downtime_hours: 2, production_loss_percent: 0.5, risk_level: 'low' },
  { machine_id: 'MCH-003', machine_name: 'Hydraulic Press #5', downtime_hours: 3, production_loss_percent: 0.8, risk_level: 'low' },
  { machine_id: 'MCH-007', machine_name: 'Lathe Machine #4', downtime_hours: 0, production_loss_percent: 0, risk_level: 'low' },
];

// Factory-level stats for the owner dashboard
export interface FactoryStats {
  total_machines: number;
  machines_operational: number;
  machines_warning: number;
  machines_critical: number;
  overall_uptime_percent: number;
  total_maintenance_cost_ytd: number;
  avg_health_score: number;
  open_tickets: number;
  mttr_hours: number; // Mean Time To Repair
  mtbf_hours: number; // Mean Time Between Failures
}

export const mockFactoryStats: FactoryStats = {
  total_machines: 8,
  machines_operational: 4,
  machines_warning: 2,
  machines_critical: 2,
  overall_uptime_percent: 94.7,
  total_maintenance_cost_ytd: 387400,
  avg_health_score: 66.9,
  open_tickets: 3,
  mttr_hours: 2.8,
  mtbf_hours: 720,
};
