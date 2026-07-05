from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import uuid

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_roles
from app.models.user import UserRole
from app.models.machine import Machine
from app.models.sensor_reading import SensorReading
from app.models.ml_prediction import MLPrediction
from app.schemas.machine import MachineResponse, MachineCreate, MachineUpdate
from app.schemas.sensor import SensorReadingResponse, SensorReadingCreate
from app.schemas.ml_prediction import MLPredictionResponse

router = APIRouter()

@router.get("", response_model=List[MachineResponse])
def get_machines(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Get all machines. Operators only see their assigned machines."""
    query = db.query(Machine)
    if current_user.role == UserRole.operator:
        query = query.filter(Machine.assigned_operator_id == current_user.user_id)
    
    machines = query.offset(skip).limit(limit).all()
    return machines

@router.get("/{machine_id}", response_model=MachineResponse)
def get_machine(
    machine_id: UUID,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Get a specific machine by ID."""
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
        
    if current_user.role == UserRole.operator and machine.assigned_operator_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not assigned to this machine")
        
    return machine

@router.post("", response_model=MachineResponse, dependencies=[Depends(require_roles(UserRole.admin, UserRole.factory_owner))])
def create_machine(
    machine_in: MachineCreate,
    db: Session = Depends(get_db)
):
    """Create a new machine (Admin/Owner only)."""
    machine = Machine(**machine_in.model_dump())
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return machine

@router.put("/{machine_id}", response_model=MachineResponse, dependencies=[Depends(require_roles(UserRole.admin, UserRole.factory_owner, UserRole.maintenance_manager))])
def update_machine(
    machine_id: UUID,
    machine_in: MachineUpdate,
    db: Session = Depends(get_db)
):
    """Update a machine."""
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
        
    update_data = machine_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(machine, field, value)
        
    db.commit()
    db.refresh(machine)
    return machine

@router.delete("/{machine_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(UserRole.admin, UserRole.factory_owner))])
def delete_machine(
    machine_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a machine."""
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
        
    from app.models.cost_log import CostLog
    from app.models.ticket import Ticket
    from app.models.alert import Alert
    from app.models.sensor_reading import SensorReading
    from app.models.ml_prediction import MLPrediction
    
    db.query(CostLog).filter(CostLog.machine_id == machine_id).delete(synchronize_session=False)
    db.query(Ticket).filter(Ticket.machine_id == machine_id).delete(synchronize_session=False)
    db.query(Alert).filter(Alert.machine_id == machine_id).delete(synchronize_session=False)
    db.query(SensorReading).filter(SensorReading.machine_id == machine_id).delete(synchronize_session=False)
    db.query(MLPrediction).filter(MLPrediction.machine_id == machine_id).delete(synchronize_session=False)
    
    db.delete(machine)
    db.commit()
    return None

@router.get("/{machine_id}/sensors", response_model=List[SensorReadingResponse])
def get_machine_sensors(
    machine_id: UUID,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    limit: int = 100
):
    """Get recent sensor readings for a machine."""
    # Verify access
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
        
    if current_user.role == UserRole.operator and machine.assigned_operator_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not assigned to this machine")
        
    readings = db.query(SensorReading)\
        .filter(SensorReading.machine_id == machine_id)\
        .order_by(SensorReading.timestamp.desc())\
        .limit(limit)\
        .all()
        
    return readings

@router.get("/{machine_id}/predictions", response_model=List[MLPredictionResponse])
def get_machine_predictions(
    machine_id: UUID,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    limit: int = 10
):
    """Get recent ML predictions for a machine."""
    # Verify access
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
        
    if current_user.role == UserRole.operator and machine.assigned_operator_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not assigned to this machine")
        
    predictions = db.query(MLPrediction)\
        .filter(MLPrediction.machine_id == machine_id)\
        .order_by(MLPrediction.timestamp.desc())\
        .limit(limit)\
        .all()
        
    return predictions

@router.post("/{machine_id}/sensors", response_model=SensorReadingResponse)
def ingest_sensor_reading(
    machine_id: UUID,
    reading_in: SensorReadingCreate,
    db: Session = Depends(get_db)
):
    """Ingest a new sensor reading. (Typically called by Edge Agent/MQTT bridge)"""
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
        
    reading = SensorReading(**reading_in.model_dump())
    if not reading.machine_id:
        reading.machine_id = machine_id
        
    db.add(reading)
    db.commit()
    db.refresh(reading)
    
    # Check thresholds and emit websocket alert if necessary
    if reading.temperature > 85.0 or reading.vibration > 0.65:
        from app.models.alert import Alert, AlertSeverity, AlertStatus
        from app.websocket.manager import manager
        import asyncio
        from datetime import datetime, timezone

        new_alert = Alert(
            alert_id=str(uuid.uuid4()).replace("-", ""),
            machine_id=machine_id,
            severity=AlertSeverity.critical,
            status=AlertStatus.pending,
            auto_escalated=False
        )
        db.add(new_alert)
        
        # We should also update machine risk level
        machine.risk_level = "critical"
        machine.status = "warning"
        
        db.commit()
        db.refresh(new_alert)

        ws_event = {
            "type": "alert_new",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "alert_id": new_alert.alert_id,
                "machine_id": str(machine_id),
                "type": "CRITICAL_TEMP" if reading.temperature > 85.0 else "CRITICAL_VIBE",
                "severity": "critical",
                "status": "pending",
                "message": f"Critical threshold breached on {machine.name}. Temp: {reading.temperature}, Vibe: {reading.vibration}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        # Run broadcast in background
        loop = asyncio.get_event_loop()
        loop.create_task(manager.broadcast(ws_event))

    return reading

