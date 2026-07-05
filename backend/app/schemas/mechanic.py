from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from app.models.mechanic import MechanicLoginStatus

class MechanicBase(BaseModel):
    skill_type: str
    login_status: MechanicLoginStatus
    shift: Optional[str] = None
    contact: Optional[str] = None

class MechanicResponse(MechanicBase):
    mechanic_id: UUID
    name: str
    email: str
    current_assignment_id: Optional[UUID] = None

    class Config:
        from_attributes = True

class MechanicUpdate(BaseModel):
    login_status: Optional[MechanicLoginStatus] = None
    current_assignment_id: Optional[UUID] = None
