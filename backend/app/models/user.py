import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy import Uuid as UUID
from app.core.database import Base


class UserRole(str, enum.Enum):
    operator             = "operator"
    mechanic             = "mechanic"
    maintenance_manager  = "maintenance_manager"
    production_manager   = "production_manager"
    factory_owner        = "factory_owner"
    admin                = "admin"


class User(Base):
    __tablename__ = "users"

    user_id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name         = Column(String(255), nullable=False)
    email        = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role         = Column(SAEnum(UserRole), nullable=False)
    is_active    = Column(Boolean, default=True, nullable=False)
    created_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
