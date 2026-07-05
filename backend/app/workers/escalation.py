import sys
import os
from celery import Celery
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from backend.app.core.database import SessionLocal
from backend.app.models.alert import Alert, AlertStatus

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

escalation_app = Celery(
    "escalation_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

ESCALATION_MINUTES = 5

@escalation_app.task(name="check_escalations")
def check_escalations():
    """Checks for pending alerts that have timed out and escalates them."""
    db: Session = SessionLocal()
    try:
        timeout_threshold = datetime.now(timezone.utc) - timedelta(minutes=ESCALATION_MINUTES)
        
        # Find pending alerts older than 5 minutes
        expired_alerts = db.query(Alert).filter(
            Alert.status == AlertStatus.pending,
            Alert.triggered_at <= timeout_threshold
        ).all()
        
        escalated_count = 0
        for alert in expired_alerts:
            alert.status = AlertStatus.escalated
            alert.auto_escalated = True
            alert.escalated_at = datetime.now(timezone.utc)
            escalated_count += 1
            
            # Note: In a real system, you would trigger a WebSocket notification
            # or send an email/push to the Maintenance Manager here.
            
        db.commit()
        return f"Escalated {escalated_count} alerts."
        
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
