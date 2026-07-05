from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.models.ticket import TicketStatus

class TicketBase(BaseModel):
    description: str

class TicketCreate(TicketBase):
    machine_id: UUID
    alert_id: UUID

class TicketUpdate(BaseModel):
    status: Optional[TicketStatus] = None
    mechanic_id: Optional[UUID] = None
    manager_id: Optional[UUID] = None
    photo_url: Optional[str] = None
    voice_note_url: Optional[str] = None
    repair_cost: Optional[float] = None
    repair_report: Optional[str] = None
    parts_used: Optional[str] = None
    time_taken_hours: Optional[float] = None
    escalated: Optional[bool] = None

class TicketResponse(TicketBase):
    ticket_id: UUID
    machine_id: UUID
    machine_name: Optional[str] = None
    alert_id: UUID
    operator_id: UUID
    operator_name: Optional[str] = None
    mechanic_id: Optional[UUID] = None
    mechanic_name: Optional[str] = None
    manager_id: Optional[UUID] = None
    status: TicketStatus
    photo_url: Optional[str] = None
    voice_note_url: Optional[str] = None
    repair_cost: Optional[float] = None
    repair_report: Optional[str] = None
    parts_used: Optional[str] = None
    time_taken_hours: Optional[float] = None
    escalated: bool
    created_at: datetime
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PaginatedTicketResponse(BaseModel):
    items: List[TicketResponse]
    total: int
    page: int
    size: int
    pages: int
