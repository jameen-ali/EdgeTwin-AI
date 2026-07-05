import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy import Uuid as UUID, JSON as JSONB
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    action      = Column(String(255), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id   = Column(UUID(as_uuid=True), nullable=True)
    old_value   = Column(JSONB, nullable=True)
    new_value   = Column(JSONB, nullable=True)
    timestamp   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    ip_address  = Column(String(50), nullable=True)
