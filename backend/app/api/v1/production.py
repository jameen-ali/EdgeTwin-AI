from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.models.machine import Machine, MachineStatus
from app.models.ticket import Ticket, TicketStatus
from app.models.production_schedule import ProductionSchedule
from app.models.notification import Notification
from app.models.audit_log import AuditLog

router = APIRouter()

class ReallocateRequest(BaseModel):
    source: str
    target: str

@router.get("/risk-overview")
def get_risk_overview(
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Risk overview for all machines - used by Production Manager."""
    # Exclude machines under maintenance from the risk pool (they are already handled)
    machines = db.query(Machine).filter(Machine.status != MachineStatus.maintenance).all()
    items = []
    for m in machines:
        open_tickets = db.query(func.count(Ticket.ticket_id)).filter(
            Ticket.machine_id == m.machine_id,
            Ticket.status.notin_([TicketStatus.closed, TicketStatus.reviewed])
        ).scalar() or 0

        items.append({
            "machine_id": str(m.machine_id),
            "machine_name": m.name,
            "location": m.location,
            "risk_level": m.risk_level.value if hasattr(m.risk_level, 'value') else str(m.risk_level),
            "health_score": m.health_score,
            "rul_hours": round(m.rul_hours, 1),
            "open_tickets": open_tickets,
        })

    # Sort by risk: critical > high > medium > low
    risk_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    items.sort(key=lambda x: risk_order.get(x["risk_level"], 4))
    return items


@router.get("/schedules")
def get_production_schedules(
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Get production schedules from the database."""
    schedules = db.query(ProductionSchedule).all()
    result = []
    for s in schedules:
        machine = db.query(Machine).filter(Machine.machine_id == s.machine_id).first()
        result.append({
            "schedule_id": s.schedule_id,
            "machine_id": str(s.machine_id),
            "machine_name": machine.name if machine else "Unknown",
            "product": s.product,
            "start_time": s.start_time.isoformat() if s.start_time else None,
            "end_time": s.end_time.isoformat() if s.end_time else None,
            "status": s.status,
            "delay_reason": s.delay_reason,
            "units_planned": s.units_planned
        })
    return result


@router.post("/reallocate")
def reallocate_load(
    req: ReallocateRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Perform production reallocation across the entire system."""
    source_machine = db.query(Machine).filter(Machine.machine_id == req.source).first()
    target_machine = db.query(Machine).filter(Machine.machine_id == req.target).first()
    
    if not source_machine or not target_machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    now = datetime.now(timezone.utc)

    # 1. Update Source Machine status
    source_machine.status = MachineStatus.maintenance
    
    # 2. Reassign Schedules
    schedules = db.query(ProductionSchedule).filter(ProductionSchedule.machine_id == req.source).all()
    for sched in schedules:
        sched.machine_id = target_machine.machine_id
        sched.status = "on_track"
        sched.delay_reason = f"Reallocated from {source_machine.name}"

    # 3. Create Ticket for Maintenance Manager (if one doesn't exist)
    existing_ticket = db.query(Ticket).filter(
        Ticket.machine_id == source_machine.machine_id,
        Ticket.status.notin_([TicketStatus.closed, TicketStatus.reviewed])
    ).first()
    
    if not existing_ticket:
        new_ticket = Ticket(
            machine_id=source_machine.machine_id,
            operator_id=current_user.user_id,
            status=TicketStatus.open,
            description=f"Auto-generated: Machine load reallocated to {target_machine.name}. Maintenance required.",
            created_at=now
        )
        db.add(new_ticket)

    # 4. Audit Log
    log = AuditLog(
        user_id=current_user.user_id,
        action="REALLOCATE_LOAD",
        entity_type="Production",
        entity_id=req.source,
        new_value=f"Production reallocated from {source_machine.name} to {target_machine.name}",
        timestamp=now,
        ip_address="127.0.0.1"
    )
    db.add(log)

    # 5. Notification
    notification = Notification(
        user_id=current_user.user_id,
        title="Load Reallocated",
        message=f"Production shifted from {source_machine.name} to {target_machine.name}.",
        created_at=now
    )
    db.add(notification)

    db.commit()
    return {"status": "success", "message": "Production load has been reallocated successfully."}
