from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class MLPredictionBase(BaseModel):
    health_score: float
    risk_level: str
    rul_hours: float
    failure_type: Optional[str] = None
    confidence: float
    model_version: str
    model_config = {'protected_namespaces': ()}

class MLPredictionCreate(MLPredictionBase):
    machine_id: UUID
    timestamp: Optional[datetime] = None

class MLPredictionResponse(MLPredictionBase):
    prediction_id: UUID
    machine_id: UUID
    timestamp: datetime

    class Config:
        from_attributes = True
