from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.machine import RiskLevel, MachineStatus

class MachineBase(BaseModel):
    name: str
    location: str
    type: str
    assigned_operator_id: Optional[UUID] = None

class MachineCreate(MachineBase):
    pass

class MachineUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    type: Optional[str] = None
    assigned_operator_id: Optional[UUID] = None
    health_score: Optional[float] = None
    risk_level: Optional[RiskLevel] = None
    rul_hours: Optional[float] = None
    status: Optional[MachineStatus] = None

class MachineResponse(MachineBase):
    machine_id: UUID
    health_score: float
    risk_level: RiskLevel
    rul_hours: float
    status: MachineStatus
    last_updated: datetime

    class Config:
        from_attributes = True
