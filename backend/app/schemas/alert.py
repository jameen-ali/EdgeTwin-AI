from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.alert import AlertSeverity, AlertStatus, OperatorResponse

class AlertBase(BaseModel):
    machine_id: UUID
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.pending
    operator_response: Optional[OperatorResponse] = None

class AlertCreate(AlertBase):
    pass

class AlertUpdate(BaseModel):
    status: Optional[AlertStatus] = None
    operator_response: Optional[OperatorResponse] = None
    auto_escalated: Optional[bool] = None

class AlertResponse(AlertBase):
    alert_id: UUID
    triggered_at: datetime
    auto_escalated: bool
    escalated_at: Optional[datetime] = None
    machine_name: Optional[str] = None

    class Config:
        from_attributes = True
