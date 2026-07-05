import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Boolean, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import Uuid as UUID
from app.core.database import Base


class AlertSeverity(str, enum.Enum):
    low      = "low"
    medium   = "medium"
    high     = "high"
    critical = "critical"


class AlertStatus(str, enum.Enum):
    pending       = "pending"
    acknowledged  = "acknowledged"
    escalated     = "escalated"
    resolved      = "resolved"


class OperatorResponse(str, enum.Enum):
    reported = "reported"
    ignored  = "ignored"


class Alert(Base):
    __tablename__ = "alerts"

    alert_id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id        = Column(UUID(as_uuid=True), ForeignKey("machines.machine_id"), nullable=False, index=True)
    triggered_at      = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    severity          = Column(SAEnum(AlertSeverity), nullable=False)
    status            = Column(SAEnum(AlertStatus), default=AlertStatus.pending, nullable=False)
    operator_response = Column(SAEnum(OperatorResponse), nullable=True)
    auto_escalated    = Column(Boolean, default=False, nullable=False)
    escalated_at      = Column(DateTime(timezone=True), nullable=True)

    machine = relationship("Machine", backref="alerts")

    @property
    def machine_name(self) -> str:
        return self.machine.name if self.machine else "Unknown"
