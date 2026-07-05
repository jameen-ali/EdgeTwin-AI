import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, Boolean, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy import Uuid as UUID
from app.core.database import Base


class TicketStatus(str, enum.Enum):
    open        = "open"
    assigned    = "assigned"
    accepted    = "accepted"
    in_progress = "in_progress"
    paused      = "paused"
    repaired    = "repaired"
    reviewed    = "reviewed"
    closed      = "closed"


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id        = Column(UUID(as_uuid=True), ForeignKey("machines.machine_id"), nullable=False, index=True)
    alert_id          = Column(UUID(as_uuid=True), ForeignKey("alerts.alert_id"), nullable=False)
    operator_id       = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    mechanic_id       = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    manager_id        = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    status            = Column(SAEnum(TicketStatus), default=TicketStatus.open, nullable=False, index=True)
    description       = Column(Text, nullable=False)
    photo_url         = Column(String(500), nullable=True)
    voice_note_url    = Column(String(500), nullable=True)
    repair_cost       = Column(Float, nullable=True)
    repair_report     = Column(Text, nullable=True)
    parts_used        = Column(Text, nullable=True)
    time_taken_hours  = Column(Float, nullable=True)
    escalated         = Column(Boolean, default=False, nullable=False)
    created_at        = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    closed_at         = Column(DateTime(timezone=True), nullable=True)
