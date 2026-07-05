import sys
import os
import uuid
import random
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import engine, Base, SessionLocal
from app.models.user import User
from app.models.machine import Machine, RiskLevel, MachineStatus
from app.models.sensor_reading import SensorReading
from app.models.ml_prediction import MLPrediction
from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.ticket import Ticket, TicketStatus
from app.models.cost_log import CostLog
from app.models.mechanic import Mechanic
from app.models.audit_log import AuditLog
from app.models.production_schedule import ProductionSchedule
from app.models.notification import Notification

import bcrypt

def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

DEMO_USERS = [
    {"user_id": "00000000-0000-0000-0000-000000000001", "name": "Alex Morgan", "email": "operator@edgetwin.ai", "role": "operator"},
    {"user_id": "00000000-0000-0000-0000-000000000002", "name": "Sarah Chen", "email": "manager@edgetwin.ai", "role": "maintenance_manager"},
    {"user_id": "00000000-0000-0000-0000-000000000003", "name": "Raj Patel", "email": "technician@edgetwin.ai", "role": "mechanic"},
    {"user_id": "00000000-0000-0000-0000-000000000004", "name": "Diana Osei", "email": "production@edgetwin.ai", "role": "production_manager"},
    {"user_id": "00000000-0000-0000-0000-000000000005", "name": "Marcus Liu", "email": "owner@edgetwin.ai", "role": "factory_owner"},
    {"user_id": "00000000-0000-0000-0000-000000000006", "name": "System Admin", "email": "admin@edgetwin.ai", "role": "admin"},
    {"user_id": "00000000-0000-0000-0000-000000000007", "name": "John Smith", "email": "mechanic2@edgetwin.ai", "role": "mechanic"},
]

DEMO_MACHINES = [
    {"machine_id": "00000000-0000-0000-0001-000000000001", "name": "CNC Mill #1", "type": "CNC Milling Machine", "location": "Plant A — Bay 1", "status": MachineStatus.normal, "health": 87.5, "risk": RiskLevel.low, "rul": 1240},
    {"machine_id": "00000000-0000-0000-0001-000000000002", "name": "Conveyor Belt #3", "type": "Conveyor System", "location": "Plant A — Bay 3", "status": MachineStatus.warning, "health": 63.2, "risk": RiskLevel.medium, "rul": 480},
    {"machine_id": "00000000-0000-0000-0001-000000000003", "name": "Air Compressor #2", "type": "Air Compressor", "location": "Plant B — Utility Room", "status": MachineStatus.critical, "health": 41.0, "risk": RiskLevel.high, "rul": 90},
    {"machine_id": "00000000-0000-0000-0001-000000000004", "name": "Hydraulic Press #5", "type": "Hydraulic Press", "location": "Plant B — Bay 2", "status": MachineStatus.normal, "health": 95.1, "risk": RiskLevel.low, "rul": 2100},
    {"machine_id": "00000000-0000-0000-0001-000000000005", "name": "Turbine Generator #1", "type": "Turbine Generator", "location": "Power House — Unit 1", "status": MachineStatus.critical, "health": 22.8, "risk": RiskLevel.critical, "rul": 12},
]

FAILURE_TYPES = ["Bearing Wear", "Motor Overheat", "Seal Leak", "Shaft Misalignment", "Electrical Fault"]

def seed_db():
    print("=" * 60)
    print("EdgeTwin AI — Full Database Seed")
    print("=" * 60)

    print("\n[1/9] Dropping and recreating all tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # ─── Users ────────────────────────────────────────────────────
        print("[2/9] Seeding Users...")
        pwd_hash = _hash("EdgeTwin@2026")
        users = []
        for du in DEMO_USERS:
            u = User(
                user_id=uuid.UUID(du["user_id"]),
                name=du["name"],
                email=du["email"],
                password_hash=pwd_hash,
                role=du["role"],
                is_active=True
            )
            users.append(u)
            db.add(u)
        db.commit()
        print(f"    ✅ {len(users)} users created")

        # ─── Mechanics ─────────────────────────────────────────────────
        print("[3/9] Seeding Mechanics...")
        mechanics_data = [
            {"id": "00000000-0000-0000-0000-000000000003", "skill": "Electrical & Mechanical", "shift": "Morning", "contact": "+1-555-0103", "status": "available"},
            {"id": "00000000-0000-0000-0000-000000000007", "skill": "Hydraulics & Pneumatics", "shift": "Evening", "contact": "+1-555-0107", "status": "available"},
        ]
        for md in mechanics_data:
            m = Mechanic(
                mechanic_id=uuid.UUID(md["id"]),
                skill_type=md["skill"],
                login_status=md["status"],
                shift=md["shift"],
                contact=md["contact"]
            )
            db.add(m)
        db.commit()
        print(f"    ✅ {len(mechanics_data)} mechanics created")

        # ─── Machines ──────────────────────────────────────────────────
        print("[4/9] Seeding Machines...")
        machines = []
        for dm in DEMO_MACHINES:
            m = Machine(
                machine_id=uuid.UUID(dm["machine_id"]),
                name=dm["name"],
                location=dm["location"],
                type=dm["type"],
                health_score=dm["health"],
                status=dm["status"],
                risk_level=dm["risk"],
                rul_hours=dm["rul"],
                assigned_operator_id=uuid.UUID("00000000-0000-0000-0000-000000000001")
            )
            machines.append(m)
            db.add(m)
        db.commit()
        print(f"    ✅ {len(machines)} machines created")

        # ─── Sensor Readings & ML Predictions ──────────────────────────
        print("[5/9] Seeding Sensor Readings & ML Predictions (30 days + 24 hours)...")
        now = datetime.now(timezone.utc)
        reading_count = 0
        pred_count = 0
        for m in machines:
            # 30 days, 1 reading per day
            for i in range(30, 0, -1):
                timestamp = now - timedelta(days=i)
                base_temp = 45 + (100 - m.health_score) * 0.4
                reading = SensorReading(
                    machine_id=m.machine_id,
                    timestamp=timestamp,
                    temperature=round(base_temp + random.uniform(-5, 10), 1),
                    vibration=round(random.uniform(0.5, 4.0), 2),
                    pressure=round(random.uniform(2.0, 8.0), 1),
                    current=round(random.uniform(15, 45), 1),
                    rpm=round(random.uniform(1500, 2500), 0),
                    noise_level=round(random.uniform(60, 90), 1)
                )
                db.add(reading)
                reading_count += 1
                
                prediction = MLPrediction(
                    machine_id=m.machine_id,
                    timestamp=timestamp,
                    health_score=round(random.uniform(max(10, m.health_score - 15), min(100, m.health_score + 10)), 1),
                    risk_level=m.risk_level.value,
                    rul_hours=round(m.rul_hours + (i * 24), 1),
                    failure_type=random.choice(FAILURE_TYPES) if m.health_score < 70 else random.choice(FAILURE_TYPES + [None, None, None]),
                    confidence=round(random.uniform(0.65, 0.98), 3),
                    model_version="v2.1"
                )
                db.add(prediction)
                pred_count += 1
            
            # 24 hours of hourly data
            for i in range(24, 0, -1):
                timestamp = now - timedelta(hours=i)
                base_temp = 45 + (100 - m.health_score) * 0.4
                reading = SensorReading(
                    machine_id=m.machine_id,
                    timestamp=timestamp,
                    temperature=round(base_temp + random.uniform(-3, 8), 1),
                    vibration=round(random.uniform(0.3, 3.5), 2),
                    pressure=round(random.uniform(2.5, 7.5), 1),
                    current=round(random.uniform(18, 42), 1),
                    rpm=round(random.uniform(1600, 2400), 0),
                    noise_level=round(random.uniform(62, 88), 1)
                )
                db.add(reading)
                reading_count += 1
        
        db.commit()
        print(f"    ✅ {reading_count} sensor readings, {pred_count} ML predictions")

        # ─── Alerts ─────────────────────────────────────────────────────
        print("[6/9] Seeding Alerts...")
        alerts = []
        
        # Pending alert for a normal machine (simulating AI detecting early anomaly)
        a1 = Alert(
            machine_id=uuid.UUID("00000000-0000-0000-0001-000000000001"),
            severity=AlertSeverity.medium,
            status=AlertStatus.pending,
            triggered_at=now - timedelta(hours=1),
            auto_escalated=False
        )
        db.add(a1)
        alerts.append(a1)

        # Escalated alerts for warning/critical machines
        a2 = Alert(
            machine_id=uuid.UUID("00000000-0000-0000-0001-000000000002"),
            severity=AlertSeverity.high,
            status=AlertStatus.escalated,
            triggered_at=now - timedelta(hours=3),
            auto_escalated=True,
            escalated_at=now - timedelta(hours=2, minutes=55)
        )
        db.add(a2)
        alerts.append(a2)

        a3 = Alert(
            machine_id=uuid.UUID("00000000-0000-0000-0001-000000000003"),
            severity=AlertSeverity.critical,
            status=AlertStatus.escalated,
            triggered_at=now - timedelta(hours=4),
            auto_escalated=True,
            escalated_at=now - timedelta(hours=3, minutes=55)
        )
        db.add(a3)
        alerts.append(a3)

        a4 = Alert(
            machine_id=uuid.UUID("00000000-0000-0000-0001-000000000005"),
            severity=AlertSeverity.critical,
            status=AlertStatus.escalated,
            triggered_at=now - timedelta(hours=6),
            auto_escalated=True,
            escalated_at=now - timedelta(hours=5, minutes=55)
        )
        db.add(a4)
        alerts.append(a4)

        # Resolved alert (historical)
        a5 = Alert(
            machine_id=uuid.UUID("00000000-0000-0000-0001-000000000004"),
            severity=AlertSeverity.low,
            status=AlertStatus.resolved,
            triggered_at=now - timedelta(days=5),
            auto_escalated=False
        )
        db.add(a5)
        alerts.append(a5)

        db.commit()
        print(f"    ✅ {len(alerts)} alerts created (1 pending, 3 escalated, 1 resolved)")

        # ─── Tickets ────────────────────────────────────────────────────
        print("[7/9] Seeding Tickets...")
        op_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        mech_id = uuid.UUID("00000000-0000-0000-0000-000000000003")
        mgr_id = uuid.UUID("00000000-0000-0000-0000-000000000002")

        tickets = []

        # Ticket 1: OPEN (Conveyor Belt) — Manager can assign
        t1 = Ticket(
            machine_id=uuid.UUID("00000000-0000-0000-0001-000000000002"),
            alert_id=a2.alert_id,
            operator_id=op_id,
            mechanic_id=None,
            manager_id=None,
            status=TicketStatus.open,
            description="AI detected high vibration patterns indicating belt misalignment. Conveyor is running but with reduced efficiency.",
            created_at=now - timedelta(hours=2)
        )
        db.add(t1)
        tickets.append(t1)

        # Ticket 2: ASSIGNED (Air Compressor) — Mechanic should Accept
        t2 = Ticket(
            machine_id=uuid.UUID("00000000-0000-0000-0001-000000000003"),
            alert_id=a3.alert_id,
            operator_id=op_id,
            mechanic_id=mech_id,
            manager_id=mgr_id,
            status=TicketStatus.assigned,
            description="Critical pressure loss detected in air compressor. Seal leak suspected based on AI analysis.",
            created_at=now - timedelta(hours=3)
        )
        db.add(t2)
        tickets.append(t2)

        # Ticket 3: IN_PROGRESS (Turbine Generator) — Mechanic is working on it
        t3 = Ticket(
            machine_id=uuid.UUID("00000000-0000-0000-0001-000000000005"),
            alert_id=a4.alert_id,
            operator_id=op_id,
            mechanic_id=mech_id,
            manager_id=mgr_id,
            status=TicketStatus.in_progress,
            description="Emergency: Turbine bearing failure detected. Machine shutdown required for immediate maintenance.",
            created_at=now - timedelta(hours=5)
        )
        db.add(t3)
        tickets.append(t3)

        # Ticket 4: CLOSED (historical — Hydraulic Press — from 5 days ago)
        t4 = Ticket(
            machine_id=uuid.UUID("00000000-0000-0000-0001-000000000004"),
            alert_id=a5.alert_id,
            operator_id=op_id,
            mechanic_id=mech_id,
            manager_id=mgr_id,
            status=TicketStatus.closed,
            description="Routine maintenance: Hydraulic fluid change and filter replacement.",
            repair_report="Replaced hydraulic fluid (20L), cleaned filters, inspected seals. Machine operating within parameters.",
            parts_used="1x Hydraulic Filter HF-200, 20L Hydraulic Fluid ISO VG 46",
            time_taken_hours=2.5,
            repair_cost=1850.00,
            created_at=now - timedelta(days=5),
            closed_at=now - timedelta(days=4)
        )
        db.add(t4)
        tickets.append(t4)

        db.commit()
        print(f"    ✅ {len(tickets)} tickets created (open, assigned, in_progress, closed)")

        # ─── Cost Logs ──────────────────────────────────────────────────
        print("[8/9] Seeding Cost Logs (12 months)...")
        cost_count = 0
        for m in machines:
            for month_offset in range(12):
                cost_date = now - timedelta(days=30 * month_offset)
                cost = CostLog(
                    ticket_id=t4.ticket_id,  # Reference existing closed ticket
                    machine_id=m.machine_id,
                    amount=round(random.uniform(800, 8000), 2),
                    month=cost_date.month,
                    year=cost_date.year,
                    approved_by=uuid.UUID("00000000-0000-0000-0000-000000000005")
                )
                db.add(cost)
                cost_count += 1
        db.commit()
        print(f"    ✅ {cost_count} cost log entries")

        # ─── Production Schedules ───────────────────────────────────────
        print("[8.5/9] Seeding Production Schedules...")
        sched_data = [
            {"id": "SCH-001", "machine": "00000000-0000-0000-0001-000000000001", "product": "Precision Gears — Batch A42", "status": "on_track", "reason": None},
            {"id": "SCH-002", "machine": "00000000-0000-0000-0001-000000000002", "product": "Assembly Line — Module K9", "status": "delayed", "reason": "Maintenance in progress"},
            {"id": "SCH-003", "machine": "00000000-0000-0000-0001-000000000004", "product": "Steel Panels — Order 7821", "status": "on_track", "reason": None},
            {"id": "SCH-004", "machine": "00000000-0000-0000-0001-000000000003", "product": "Pneumatic Assembly — Line 3", "status": "at_risk", "reason": "High vibration detected"},
            {"id": "SCH-005", "machine": "00000000-0000-0000-0001-000000000005", "product": "Power Generation — Zone A", "status": "halted", "reason": "Critical failure"},
        ]
        schedules = []
        for sd in sched_data:
            s = ProductionSchedule(
                schedule_id=sd["id"],
                machine_id=sd["machine"].replace("-", ""),
                product=sd["product"],
                start_time=now - timedelta(hours=2),
                end_time=now + timedelta(hours=6),
                status=sd["status"],
                delay_reason=sd["reason"]
            )
            db.add(s)
            schedules.append(s)
        db.commit()
        print(f"    ✅ {len(schedules)} production schedules created")

        # ─── Audit Logs ─────────────────────────────────────────────────
        print("[9/9] Seeding Audit Logs...")
        actions = [
            ("LOGIN", "Auth", "User logged in"),
            ("CREATE_USER", "User", "New user created"),
            ("UPDATE_MACHINE", "Machine", "Machine status updated"),
            ("ASSIGN_TICKET", "Ticket", "Mechanic assigned to ticket"),
            ("CLOSE_TICKET", "Ticket", "Ticket closed after repair"),
            ("UPDATE_SETTINGS", "Settings", "System settings modified"),
            ("REALLOCATE_LOAD", "Production", "Production load reallocated"),
        ]
        all_user_ids = [uuid.UUID(u["user_id"]) for u in DEMO_USERS]
        audit_count = 0
        for i in range(60):
            u_id = random.choice(all_user_ids)
            act = random.choice(actions)
            log = AuditLog(
                user_id=u_id,
                action=act[0],
                entity_type=act[1],
                entity_id=str(uuid.uuid4()),
                new_value=act[2],
                timestamp=now - timedelta(hours=random.randint(1, 720)),
                ip_address=f"192.168.1.{random.randint(10, 250)}"
            )
            db.add(log)
            audit_count += 1
        
        db.commit()
        print(f"    ✅ {audit_count} audit log entries")

        print("\n" + "=" * 60)
        print("✅ DATABASE SEEDING COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"\nLogin Credentials (all users):")
        print(f"  Password: EdgeTwin@2026")
        print(f"\nUsers:")
        for u in DEMO_USERS:
            print(f"  {u['role']:25s} → {u['email']}")
        print()
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
