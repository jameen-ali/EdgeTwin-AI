"""scripts/seed_demo_data.py — Seed demonstration machines and maintenance work orders.

Populates PostgreSQL with:
1. Standard EdgeTwin AI fleet machines (MOT-1001, MOT-1002, CNC-1001, CNC-1002, PMP-2001, FAN-3001).
2. Initial realistic maintenance work orders across different statuses and event types.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from api.app.db.session import SessionLocal
from api.app.models.machine import MachineRecord
from api.app.models.maintenance import MaintenanceRecord

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEMO_MACHINES = [
    {
        "machine_id": "MOT-1001",
        "machine_type": "Motor",
        "location": "Production Line 1 - Drive Bay",
        "status": "ACTIVE",
    },
    {
        "machine_id": "MOT-1002",
        "machine_type": "Motor",
        "location": "Production Line 2 - Conveyor Drive",
        "status": "ACTIVE",
    },
    {
        "machine_id": "CNC-1001",
        "machine_type": "Milling",
        "location": "Precision Machining Cell A",
        "status": "ACTIVE",
    },
    {
        "machine_id": "CNC-1002",
        "machine_type": "Lathe",
        "location": "High-Speed Lathe Cell B",
        "status": "ACTIVE",
    },
    {
        "machine_id": "PMP-2001",
        "machine_type": "Pump",
        "location": "Cooling Subsystem Pump Bay Alpha",
        "status": "ACTIVE",
    },
    {
        "machine_id": "FAN-3001",
        "machine_type": "Fan",
        "location": "Facility Exhaust Ventilation Cell",
        "status": "ACTIVE",
    },
]

DEMO_MAINTENANCE = [
    {
        "machine_id": "MOT-1001",
        "event_type": "INSPECTION",
        "status": "SCHEDULED",
        "description": "Routine monthly thermal imaging and baseline vibration inspection.",
        "technician": "Sarah Connor",
        "days_ago": 2,
    },
    {
        "machine_id": "MOT-1001",
        "event_type": "LUBRICATION",
        "status": "IN_PROGRESS",
        "description": "High-temperature bearing grease replenishment following elevated torque signatures.",
        "technician": "Marcus Vance",
        "days_ago": 1,
    },
    {
        "machine_id": "PMP-2001",
        "event_type": "PART_REPLACEMENT",
        "status": "SCHEDULED",
        "description": "Impeller mechanical seal replacement after pressure fluctuation alert.",
        "technician": "Alex Rivera",
        "days_ago": 0,
    },
    {
        "machine_id": "CNC-1001",
        "event_type": "CALIBRATION",
        "status": "COMPLETED",
        "description": "Spindle axis alignment and zero-point calibration verification.",
        "technician": "Elena Rostova",
        "days_ago": 7,
    },
    {
        "machine_id": "CNC-1002",
        "event_type": "OVERHAUL",
        "status": "SCHEDULED",
        "description": "Semi-annual ballscrew and guide rail overhaul inspection.",
        "technician": "David Chen",
        "days_ago": 3,
    },
    {
        "machine_id": "FAN-3001",
        "event_type": "INSPECTION",
        "status": "COMPLETED",
        "description": "Impeller dynamic balancing and acoustic signature check.",
        "technician": "Sarah Connor",
        "days_ago": 14,
    },
    {
        "machine_id": "MOT-1002",
        "event_type": "CALIBRATION",
        "status": "COMPLETED",
        "description": "Encoder synchronization and inverter PID loop tuning.",
        "technician": "Elena Rostova",
        "days_ago": 5,
    },
]


def seed() -> None:
    now = datetime.now(UTC)
    with SessionLocal() as db:
        # 1. Seed Machines
        for m_data in DEMO_MACHINES:
            existing = db.execute(
                select(MachineRecord).where(MachineRecord.machine_id == m_data["machine_id"])
            ).scalar_one_or_none()
            if existing is None:
                logger.info(
                    "Registering demo machine: %s (%s)",
                    m_data["machine_id"],
                    m_data["machine_type"],
                )
                db.add(
                    MachineRecord(
                        machine_id=m_data["machine_id"],
                        machine_type=m_data["machine_type"],
                        location=m_data["location"],
                        status=m_data["status"],
                    )
                )
            else:
                existing.location = m_data["location"]
                existing.machine_type = m_data["machine_type"]
        db.commit()

        # 2. Seed Maintenance Work Orders
        existing_orders = db.execute(select(MaintenanceRecord)).scalars().all()
        if not existing_orders:
            logger.info("Seeding %d demo maintenance work orders...", len(DEMO_MAINTENANCE))
            for item in DEMO_MAINTENANCE:
                created_dt = now - timedelta(days=item["days_ago"])
                started_dt = (
                    created_dt + timedelta(hours=1)
                    if item["status"] in ("IN_PROGRESS", "COMPLETED")
                    else None
                )
                completed_dt = (
                    created_dt + timedelta(hours=3) if item["status"] == "COMPLETED" else None
                )

                record = MaintenanceRecord(
                    machine_id=item["machine_id"],
                    event_type=item["event_type"],
                    status=item["status"],
                    description=item["description"],
                    technician=item["technician"],
                    started_at=started_dt,
                    completed_at=completed_dt,
                    created_at=created_dt,
                )
                db.add(record)
            db.commit()
            logger.info("Successfully seeded maintenance work orders.")
        else:
            logger.info(
                "Maintenance records already exist (%d records). Skipping maintenance seed.",
                len(existing_orders),
            )


if __name__ == "__main__":
    seed()
