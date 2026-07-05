import os
from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "edgetwin_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.workers.ml_inference", "app.workers.escalation"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Setup Periodic Tasks
celery_app.conf.beat_schedule = {
    "run-ml-inference-every-minute": {
        "task": "run_fleet_inference",
        "schedule": crontab(minute="*"), # Runs every minute
    },
    "check-escalations-every-minute": {
        "task": "check_escalations",
        "schedule": crontab(minute="*"), # Runs every minute
    },
}
