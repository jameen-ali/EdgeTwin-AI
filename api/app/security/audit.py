"""Structured security audit logging for authentication and privileged operations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from api.app.logging import get_logger

logger = get_logger("security.audit")


def log_security_event(
    action: str,
    user: str | None,
    role: str | None,
    target: str | None = None,
    success: bool = True,
    details: dict[str, Any] | None = None,
) -> None:
    """Log an auditable security event using structured JSON-compatible formatting.

    Parameters
    ----------
    action : str
        Action identifier (e.g. 'LOGIN', 'ALERT_ACKNOWLEDGE', 'SCENARIO_INJECT', 'FEEDBACK_SUBMIT').
    user : str | None
        Username or user identifier initiating the action.
    role : str | None
        Role of the actor.
    target : str | None, optional
        Target resource (e.g. machine ID, alert ID, scenario ID).
    success : bool, default True
        Whether the attempted action succeeded or was rejected.
    details : dict[str, Any] | None, optional
        Additional contextual metadata (MUST NOT contain secrets, passwords, or tokens).
    """
    event = {
        "event_type": "SECURITY_AUDIT",
        "timestamp": datetime.now(UTC).isoformat(),
        "action": action,
        "user": user or "ANONYMOUS",
        "role": role or "NONE",
        "target": target or "NONE",
        "success": success,
        "details": details or {},
    }

    if success:
        logger.info(
            f"AUDIT {action} user={event['user']} role={event['role']} target={event['target']} status=SUCCESS"
        )
    else:
        logger.warning(
            f"AUDIT {action} user={event['user']} role={event['role']} target={event['target']} status=FAILURE"
        )
