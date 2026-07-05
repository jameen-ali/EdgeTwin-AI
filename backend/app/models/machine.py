import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy import Uuid as UUID
from app.core.database import Base


class RiskLevel(str, enum.Enum):
    low      = "low"
    medium   = "medium"
    high     = "high"
    critical = "critical"


class MachineStatus(str, enum.Enum):
    normal   = "normal"
    warning  = "warning"
    critical = "critical"
    offline  = "offline"


class Machine(Base):
    __tablename__ = "machines"

    machine_id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name                 = Column(String(255), nullable=False)
    location             = Column(String(255), nullable=False)
    type                 = Column(String(100), nullable=False)
    assigned_operator_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    health_score         = Column(Float, default=100.0, nullable=False)
    risk_level           = Column(SAEnum(RiskLevel), default=RiskLevel.low, nullable=False)
    rul_hours            = Column(Float, default=1000.0, nullable=False)
    status               = Column(SAEnum(MachineStatus), default=MachineStatus.normal, nullable=False)
    last_updated         = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
