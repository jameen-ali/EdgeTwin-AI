from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import math

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_roles
from app.models.user import UserRole, User
from app.models.ticket import Ticket, TicketStatus
from app.models.machine import Machine
from app.models.cost_log import CostLog
from app.models.audit_log import AuditLog
from datetime import datetime
from app.schemas.ticket import TicketResponse, TicketUpdate, PaginatedTicketResponse

router = APIRouter()

@router.get("", response_model=PaginatedTicketResponse)
def get_tickets(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    status: str = None,
    page: int = 1,
    size: int = 20
):
    query = db.query(Ticket)
    
    # RBAC logic
    if current_user.role == UserRole.operator:
        query = query.filter(Ticket.operator_id == current_user.user_id)
    elif current_user.role == UserRole.mechanic:
        query = query.filter(Ticket.mechanic_id == current_user.user_id)
        
    if status:
        query = query.filter(Ticket.status == status)
        
    total = query.count()
    tickets = query.order_by(Ticket.created_at.desc()).offset((page - 1) * size).limit(size).all()
    
    # Manually populate names to match frontend schema
    result = []
    for t in tickets:
        machine = db.query(Machine).filter(Machine.machine_id == t.machine_id).first()
        operator = db.query(User).filter(User.user_id == t.operator_id).first()
        mechanic = db.query(User).filter(User.user_id == t.mechanic_id).first() if t.mechanic_id else None
        manager = db.query(User).filter(User.user_id == t.manager_id).first() if t.manager_id else None
        
        t_dict = {c.name: getattr(t, c.name) for c in t.__table__.columns}
        t_dict["machine_name"] = machine.name if machine else None
        t_dict["operator_name"] = operator.name if operator else None
        t_dict["mechanic_name"] = mechanic.name if mechanic else None
        
        result.append(TicketResponse(**t_dict))
        
    pages = math.ceil(total / size) if size else 0
    return {"items": result, "total": total, "page": page, "size": size, "pages": pages}

@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: UUID,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    t = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    machine = db.query(Machine).filter(Machine.machine_id == t.machine_id).first()
    operator = db.query(User).filter(User.user_id == t.operator_id).first()
    mechanic = db.query(User).filter(User.user_id == t.mechanic_id).first() if t.mechanic_id else None
    
    t_dict = {c.name: getattr(t, c.name) for c in t.__table__.columns}
    t_dict["machine_name"] = machine.name if machine else None
    t_dict["operator_name"] = operator.name if operator else None
    t_dict["mechanic_name"] = mechanic.name if mechanic else None
    
    return TicketResponse(**t_dict)

@router.put("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: UUID,
    payload: TicketUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    t = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(t, key, value)
        
    # Cost Log Integration
    if payload.repair_cost is not None and payload.status == TicketStatus.reviewed:
        cost_entry = CostLog(
            ticket_id=t.ticket_id,
            machine_id=t.machine_id,
            amount=payload.repair_cost,
            month=datetime.now().month,
            year=datetime.now().year,
            approved_by=current_user.user_id
        )
        db.add(cost_entry)

    # Audit Log Integration
    audit_entry = AuditLog(
        user_id=current_user.user_id,
        action="UPDATE_TICKET",
        entity_type="ticket",
        entity_id=t.ticket_id,
        old_value=None,
        new_value=payload.model_dump(exclude_unset=True),
        ip_address="127.0.0.1"
    )
    db.add(audit_entry)

    db.commit()
    db.refresh(t)
    
    # Broadcast would go here
    return get_ticket(ticket_id, current_user, db)
