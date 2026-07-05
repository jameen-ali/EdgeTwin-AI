-- EdgeTwin AI — Demo User Seed SQL
-- Generated: 2026-07-04T00:56:58.342866+00:00
-- Run this against your PostgreSQL edgetwin_db database.

BEGIN;

-- ── Users ─────────────────────────────────────────────────────────
INSERT INTO users (user_id, name, email, password_hash, role, is_active, created_at)
VALUES ('00000000-0000-0000-0000-000000000001', 'Alex Morgan', 'operator@edgetwin.ai',
        '$2b$12$.NbF7wQerjd8/wDivMLMTOiifHuW.X6ZI9QuJA.blH19Y5QBAh8f.',
        'operator', true, NOW())
ON CONFLICT (email) DO NOTHING;

INSERT INTO users (user_id, name, email, password_hash, role, is_active, created_at)
VALUES ('00000000-0000-0000-0000-000000000002', 'Sarah Chen', 'manager@edgetwin.ai',
        '$2b$12$YvFOuuEnLd.hyJDes9bqJOzrbStG2GfjawHs3AvLlGKJeDHy/lII6',
        'maintenance_manager', true, NOW())
ON CONFLICT (email) DO NOTHING;

INSERT INTO users (user_id, name, email, password_hash, role, is_active, created_at)
VALUES ('00000000-0000-0000-0000-000000000003', 'Raj Patel', 'technician@edgetwin.ai',
        '$2b$12$8Km5h9HBIzfbfBf6ElnZVuJP86qKk3L6H0ZJEgRC0o3blXIw8N7Im',
        'mechanic', true, NOW())
ON CONFLICT (email) DO NOTHING;

INSERT INTO users (user_id, name, email, password_hash, role, is_active, created_at)
VALUES ('00000000-0000-0000-0000-000000000004', 'Diana Osei', 'production@edgetwin.ai',
        '$2b$12$wxlzYMCFF47UUngwu1wkcOKKmoNnfWiP7cwrN90eUPosclkOYzXy.',
        'production_manager', true, NOW())
ON CONFLICT (email) DO NOTHING;

INSERT INTO users (user_id, name, email, password_hash, role, is_active, created_at)
VALUES ('00000000-0000-0000-0000-000000000005', 'Marcus Liu', 'owner@edgetwin.ai',
        '$2b$12$3kn1807dktytS.VtKC3beeZva3fW..i3H0ivsn3Wx5L0uZiwUoBPu',
        'factory_owner', true, NOW())
ON CONFLICT (email) DO NOTHING;

INSERT INTO users (user_id, name, email, password_hash, role, is_active, created_at)
VALUES ('00000000-0000-0000-0000-000000000006', 'System Admin', 'admin@edgetwin.ai',
        '$2b$12$TbRYx4WeYQ18O/canbSVBuTdLr9QdRIUzjpbImv8TieaRMXMQ/bou',
        'admin', true, NOW())
ON CONFLICT (email) DO NOTHING;


-- ── Mechanic Profile ──────────────────────────────────────────────
INSERT INTO mechanics (mechanic_id, skill_type, login_status, shift, contact)
VALUES ('00000000-0000-0000-0000-000000000003',
        'Electrical & Mechanical', 'available', 'Morning', '+1-555-0103')
ON CONFLICT (mechanic_id) DO NOTHING;

-- ── Demo Machines ──────────────────────────────────────────────────
INSERT INTO machines
  (machine_id, name, location, type, assigned_operator_id,
   health_score, risk_level, rul_hours, status, last_updated)
VALUES
  ('00000000-0000-0000-0001-000000000001', 'CNC Mill #1', 'Plant A — Bay 1', 'CNC Milling Machine', '00000000-0000-0000-0000-000000000001',
   87.5, 'low', 1240.0, 'normal', NOW())
ON CONFLICT (machine_id) DO NOTHING;

INSERT INTO machines
  (machine_id, name, location, type, assigned_operator_id,
   health_score, risk_level, rul_hours, status, last_updated)
VALUES
  ('00000000-0000-0000-0001-000000000002', 'Conveyor Belt #3', 'Plant A — Bay 3', 'Conveyor System', '00000000-0000-0000-0000-000000000001',
   63.2, 'medium', 480.0, 'warning', NOW())
ON CONFLICT (machine_id) DO NOTHING;

INSERT INTO machines
  (machine_id, name, location, type, assigned_operator_id,
   health_score, risk_level, rul_hours, status, last_updated)
VALUES
  ('00000000-0000-0000-0001-000000000003', 'Air Compressor #2', 'Plant B — Utility Room', 'Air Compressor', NULL,
   41.0, 'high', 90.0, 'critical', NOW())
ON CONFLICT (machine_id) DO NOTHING;

INSERT INTO machines
  (machine_id, name, location, type, assigned_operator_id,
   health_score, risk_level, rul_hours, status, last_updated)
VALUES
  ('00000000-0000-0000-0001-000000000004', 'Hydraulic Press #5', 'Plant B — Bay 2', 'Hydraulic Press', NULL,
   95.1, 'low', 2100.0, 'normal', NOW())
ON CONFLICT (machine_id) DO NOTHING;

INSERT INTO machines
  (machine_id, name, location, type, assigned_operator_id,
   health_score, risk_level, rul_hours, status, last_updated)
VALUES
  ('00000000-0000-0000-0001-000000000005', 'Turbine Generator #1', 'Power House — Unit 1', 'Turbine Generator', NULL,
   22.8, 'critical', 12.0, 'critical', NOW())
ON CONFLICT (machine_id) DO NOTHING;


COMMIT;
