"""Alert fleet-wide endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from api.app.db.session import get_db
from api.app.schemas.alert import AlertAcknowledgeRequest, AlertDTO, AlertListResponse
from api.app.schemas.common import ProblemDetails
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


@router.patch(
    "/{alert_id}",
    response_model=AlertDTO,
    summary="Acknowledge or resolve an alert",
    description="Update the lifecycle status of an alert to ACKNOWLEDGED or RESOLVED.",
    responses={
        404: {"model": ProblemDetails, "description": "Alert not found"},
        422: {"model": ProblemDetails, "description": "Validation error"},
    },
)
def acknowledge_alert(
    payload: AlertAcknowledgeRequest,
    alert_id: Annotated[int, Path(ge=1, description="Alert sequence ID")],
    db: DbDep,
) -> AlertDTO:
    return AlertService.acknowledge_alert(
        db=db,
        alert_id=alert_id,
        resolved_by=payload.resolved_by,
        notes=payload.notes,
        new_status=payload.status,
    )
