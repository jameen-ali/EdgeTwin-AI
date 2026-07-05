from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_roles
from app.models.user import UserRole
from app.models.alert import Alert, AlertStatus, OperatorResponse
from app.models.machine import Machine
from app.schemas.alert import AlertResponse, AlertUpdate

router = APIRouter()

@router.get("", response_model=List[AlertResponse])
def get_alerts(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    status: str = None
):
    """Get active alerts."""
    query = db.query(Alert)
    
    if current_user.role == UserRole.operator:
        # Operator only sees alerts for machines they are assigned to
        query = query.join(Machine).filter(Machine.assigned_operator_id == current_user.user_id)
        
    if status:
        query = query.filter(Alert.status == status)
        
    alerts = query.order_by(Alert.triggered_at.desc()).offset(skip).limit(limit).all()
    return alerts

@router.post("/{alert_id}/report", response_model=AlertResponse, dependencies=[Depends(require_roles(UserRole.operator))])
def report_issue(
    alert_id: UUID,
    db: Session = Depends(get_db)
):
    """Operator reports the issue and acknowledges the alert."""
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    if alert.status not in [AlertStatus.pending, AlertStatus.escalated]:
        raise HTTPException(status_code=400, detail="Alert is not actionable")
        
    alert.operator_response = OperatorResponse.reported
    alert.status = AlertStatus.acknowledged
    db.commit()
    db.refresh(alert)
    return alert

@router.post("/{alert_id}/ignore", response_model=AlertResponse, dependencies=[Depends(require_roles(UserRole.operator))])
def ignore_issue(
    alert_id: UUID,
    db: Session = Depends(get_db)
):
    """Operator ignores the issue."""
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    if alert.status not in [AlertStatus.pending, AlertStatus.escalated]:
        raise HTTPException(status_code=400, detail="Alert is not actionable")
        
    alert.operator_response = OperatorResponse.ignored
    alert.status = AlertStatus.acknowledged
    # Note: In a real system, 'ignored' might trigger auto-escalation immediately
    db.commit()
    db.refresh(alert)
    return alert
