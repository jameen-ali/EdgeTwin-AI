import enum
from sqlalchemy import Column, String, Enum as SAEnum, ForeignKey
from sqlalchemy import Uuid as UUID
from app.core.database import Base


class MechanicLoginStatus(str, enum.Enum):
    available = "available"
    busy      = "busy"
    offline   = "offline"


class Mechanic(Base):
    """Extended profile for users with role=mechanic."""
    __tablename__ = "mechanics"

    mechanic_id           = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), primary_key=True)
    skill_type            = Column(String(255), nullable=False)
    login_status          = Column(SAEnum(MechanicLoginStatus), default=MechanicLoginStatus.offline, nullable=False)
    current_assignment_id = Column(UUID(as_uuid=True), ForeignKey("tickets.ticket_id"), nullable=True)
    shift                 = Column(String(100), nullable=True)
    contact               = Column(String(100), nullable=True)
