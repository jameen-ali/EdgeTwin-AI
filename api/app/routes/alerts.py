"""Alert fleet-wide endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from api.app.db.session import get_db
from api.app.models.user import UserRecord
from api.app.schemas.alert import AlertAcknowledgeRequest, AlertDTO, AlertListResponse
from api.app.schemas.common import ProblemDetails
from api.app.security.audit import log_security_event
from api.app.security.deps import get_current_user, require_roles
from api.app.security.roles import PRIVILEGED_MAINTENANCE_ROLES
from api.app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["Alerts"])

DbDep = Annotated[Session, Depends(get_db)]
LimitQuery = Annotated[int, Query(ge=1, le=100, description="Maximum alerts to return (1-100)")]
OffsetQuery = Annotated[int, Query(ge=0, description="Offset for pagination")]


@router.get(
    "",
    response_model=AlertListResponse,
    summary="List fleet alerts",
    description="Retrieve a bounded, paginated list of system and machine alerts across the entire factory fleet.",
    responses={
        422: {"model": ProblemDetails, "description": "Validation error"},
        500: {"model": ProblemDetails, "description": "Internal server error"},
    },
)
def list_alerts(
    db: DbDep,
    severity: Annotated[
        str | None,
        Query(description="Filter by severity: INFO, WARNING, CRITICAL"),
    ] = None,
    status: Annotated[
        str | None,
        Query(description="Filter by status: OPEN, ACKNOWLEDGED, RESOLVED"),
    ] = None,
    acknowledged: Annotated[
        bool | None,
        Query(description="Filter by acknowledgement state"),
    ] = None,
    machine_id: Annotated[
        str | None,
        Query(description="Filter by machine ID"),
    ] = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
    before: Annotated[
        datetime | None,
        Query(description="Filter alerts triggered before this timestamp"),
    ] = None,
    after: Annotated[
        datetime | None,
        Query(description="Filter alerts triggered after this timestamp"),
    ] = None,
    current_user: Annotated[UserRecord, Depends(get_current_user)] = None,  # type: ignore[assignment]
) -> AlertListResponse:
    return AlertService.get_alerts(
        db=db,
        severity=severity,
        alert_status=status,
        acknowledged=acknowledged,
        machine_id=machine_id,
        limit=limit,
        offset=offset,
        before=before,
        after=after,
    )


@router.get(
    "/{alert_id}",
    response_model=AlertDTO,
    summary="Get alert details",
    description="Retrieve full details for an alert by sequence ID.",
    responses={
        401: {"model": ProblemDetails, "description": "Unauthenticated"},
        404: {"model": ProblemDetails, "description": "Alert not found"},
        422: {"model": ProblemDetails, "description": "Validation error"},
    },
)
def get_alert(
    alert_id: Annotated[int, Path(ge=1, description="Alert sequence ID")],
    db: DbDep,
    current_user: Annotated[UserRecord, Depends(get_current_user)] = None,  # type: ignore[assignment]
) -> AlertDTO:
    return AlertService.get_alert_by_id(db=db, alert_id=alert_id)


@router.patch(
    "/{alert_id}",
    response_model=AlertDTO,
    summary="Acknowledge or resolve an alert (Privileged)",
    description="Update the lifecycle status of an alert to ACKNOWLEDGED or RESOLVED. Requires Maintenance Engineer or Admin role.",
    responses={
        401: {"model": ProblemDetails, "description": "Unauthenticated"},
        403: {
            "model": ProblemDetails,
            "description": "Forbidden: Requires Maintenance Engineer or Admin role",
        },
        404: {"model": ProblemDetails, "description": "Alert not found"},
        422: {"model": ProblemDetails, "description": "Validation error"},
    },
)
def acknowledge_alert(
    payload: AlertAcknowledgeRequest,
    alert_id: Annotated[int, Path(ge=1, description="Alert sequence ID")],
    db: DbDep,
    current_user: Annotated[UserRecord, Depends(require_roles(PRIVILEGED_MAINTENANCE_ROLES))],
) -> AlertDTO:
    resolved_by = payload.resolved_by or current_user.username
    res = AlertService.acknowledge_alert(
        db=db,
        alert_id=alert_id,
        resolved_by=resolved_by,
        notes=payload.notes,
        new_status=payload.status,
    )
    log_security_event(
        action="ALERT_ACKNOWLEDGE",
        user=current_user.username,
        role=current_user.role,
        target=str(alert_id),
        success=True,
        details={"status": payload.status, "notes": payload.notes},
    )
    return res
