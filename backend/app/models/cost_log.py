import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Float, Integer, DateTime, ForeignKey
from sqlalchemy import Uuid as UUID
from app.core.database import Base


class CostLog(Base):
    __tablename__ = "cost_logs"

    cost_id     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id   = Column(UUID(as_uuid=True), ForeignKey("tickets.ticket_id"), nullable=False)
    machine_id  = Column(UUID(as_uuid=True), ForeignKey("machines.machine_id"), nullable=False, index=True)
    amount      = Column(Float, nullable=False)
    month       = Column(Integer, nullable=False)
    year        = Column(Integer, nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
