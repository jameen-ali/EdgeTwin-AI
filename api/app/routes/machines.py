"""Machine asset and per-machine subresource endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from api.app.db.session import get_db
from api.app.models.user import UserRecord
from api.app.schemas.alert import AlertListResponse
from api.app.schemas.common import ProblemDetails
from api.app.schemas.feedback import FeedbackCreateRequest, FeedbackDTO, FeedbackListResponse
from api.app.schemas.machine import MachineDetailResponse, MachineListResponse
from api.app.schemas.maintenance import (
    MaintenanceCreateRequest,
    MaintenanceDTO,
    MaintenanceListResponse,
)
from api.app.schemas.prediction import PredictionListResponse
from api.app.schemas.telemetry import TelemetryListResponse
from api.app.schemas.twin import TwinHistoryResponse, TwinStateDTO
from api.app.security.audit import log_security_event
from api.app.security.deps import get_current_user, require_roles
from api.app.security.roles import PRIVILEGED_MAINTENANCE_ROLES
from api.app.services.alert_service import AlertService
from api.app.services.feedback_service import FeedbackService
from api.app.services.machine_service import MachineService
from api.app.services.maintenance_service import MaintenanceService
from api.app.services.prediction_service import PredictionService
from api.app.services.telemetry_service import TelemetryService
from api.app.services.twin_query_service import TwinQueryService

router = APIRouter(
    prefix="/machines",
    tags=["Machines"],
    dependencies=[Depends(get_current_user)],
)

MACHINE_ID_PATTERN = r"^[A-Z0-9_-]{1,32}$"

DbDep = Annotated[Session, Depends(get_db)]
MachineIdPath = Annotated[
    str,
    Path(..., pattern=MACHINE_ID_PATTERN, description="Machine identifier (e.g. MOT-1001)"),
]
LimitQuery = Annotated[
    int,
    Query(ge=1, le=100, description="Maximum items to return (1-100)"),
]
OffsetQuery = Annotated[
    int,
    Query(ge=0, description="Offset for pagination"),
]


@router.get(
    "",
    response_model=MachineListResponse,
    summary="List fleet machines",
    description="Retrieve a bounded, paginated list of registered industrial assets with their latest twin state.",
    responses={
        422: {"model": ProblemDetails, "description": "Validation error"},
        500: {"model": ProblemDetails, "description": "Internal server error"},
    },
)
def list_machines(
    db: DbDep,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
    status: Annotated[
        str | None, Query(description="Filter by status (e.g. OFFLINE, ACTIVE)")
    ] = None,
) -> MachineListResponse:
    return MachineService.get_machines(db=db, limit=limit, offset=offset, machine_status=status)


@router.get(
    "/{machine_id}",
    response_model=MachineDetailResponse,
    summary="Get machine details",
    description="Retrieve detailed metadata, latest telemetry, latest prediction, and twin state for a specific machine.",
    responses={
        404: {"model": ProblemDetails, "description": "Machine not found"},
        422: {"model": ProblemDetails, "description": "Validation error"},
    },
)
def get_machine(
    machine_id: MachineIdPath,
    db: DbDep,
) -> MachineDetailResponse:
    return MachineService.get_machine(db=db, machine_id=machine_id)


@router.get(
    "/{machine_id}/telemetry",
    response_model=TelemetryListResponse,
    summary="Get machine telemetry history",
    description="Retrieve bounded historical telemetry observations for a machine.",
    responses={
        404: {"model": ProblemDetails, "description": "Machine not found"},
        422: {"model": ProblemDetails, "description": "Validation error"},
    },
)
def get_machine_telemetry(
    machine_id: MachineIdPath,
    db: DbDep,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
    before: Annotated[
        datetime | None,
        Query(description="Filter observations before this ISO-8601 UTC timestamp"),
    ] = None,
    after: Annotated[
        datetime | None,
        Query(description="Filter observations after this ISO-8601 UTC timestamp"),
    ] = None,
    seq_min: Annotated[
        int | None,
        Query(ge=0, description="Filter by minimum sequence number"),
    ] = None,
    seq_max: Annotated[
        int | None,
        Query(ge=0, description="Filter by maximum sequence number"),
    ] = None,
) -> TelemetryListResponse:
    return TelemetryService.get_telemetry(
        db=db,
        machine_id=machine_id,
        limit=limit,
        offset=offset,
        before=before,
        after=after,
        seq_min=seq_min,
        seq_max=seq_max,
    )


@router.get(
    "/{machine_id}/predictions",
    response_model=PredictionListResponse,
    summary="Get machine prediction history",
    description="Retrieve persisted ML risk predictions and health assessments without recomputing inference.",
    responses={
        404: {"model": ProblemDetails, "description": "Machine not found"},
        422: {"model": ProblemDetails, "description": "Validation error"},
    },
)
def get_machine_predictions(
    machine_id: MachineIdPath,
    db: DbDep,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
    before: Annotated[
        datetime | None,
        Query(description="Filter predictions before this ISO-8601 UTC timestamp"),
    ] = None,
    after: Annotated[
        datetime | None,
        Query(description="Filter predictions after this ISO-8601 UTC timestamp"),
    ] = None,
) -> PredictionListResponse:
    return PredictionService.get_predictions(
        db=db,
        machine_id=machine_id,
        limit=limit,
        offset=offset,
        before=before,
        after=after,
    )


@router.get(
    "/{machine_id}/twin",
    response_model=TwinStateDTO,
    summary="Get latest Digital Twin state",
    description="Retrieve the canonical real-time Digital Twin state matching the WebSocket broadcast.",
    responses={
        404: {"model": ProblemDetails, "description": "Machine not found"},
        422: {"model": ProblemDetails, "description": "Validation error"},
    },
)
def get_machine_twin(
    machine_id: MachineIdPath,
    db: DbDep,
) -> TwinStateDTO:
    return TwinQueryService.get_latest_twin(db=db, machine_id=machine_id)


@router.get(
    "/{machine_id}/twin/history",
    response_model=TwinHistoryResponse,
    summary="Get Digital Twin snapshot history",
    description="Retrieve historical state snapshots for a machine's Digital Twin.",
    responses={
        404: {"model": ProblemDetails, "description": "Machine not found"},
        422: {"model": ProblemDetails, "description": "Validation error"},
    },
)
def get_machine_twin_history(
    machine_id: MachineIdPath,
    db: DbDep,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
    before: Annotated[
        datetime | None,
        Query(description="Filter snapshots before this timestamp"),
    ] = None,
    after: Annotated[
        datetime | None,
        Query(description="Filter snapshots after this timestamp"),
    ] = None,
) -> TwinHistoryResponse:
    return TwinQueryService.get_twin_history(
        db=db,
        machine_id=machine_id,
        limit=limit,
        offset=offset,
        before=before,
        after=after,
    )


@router.get(
    "/{machine_id}/alerts",
    response_model=AlertListResponse,
    summary="Get machine alerts",
    description="Retrieve alerts raised for a specific machine.",
    responses={
        404: {"model": ProblemDetails, "description": "Machine not found"},
        422: {"model": ProblemDetails, "description": "Validation error"},
    },
)
def get_machine_alerts(
    machine_id: MachineIdPath,
    db: DbDep,
    severity: Annotated[
        str | None,
        Query(description="Filter by severity: INFO, WARNING, CRITICAL"),
    ] = None,
    status: Annotated[
        str | None,
        Query(description="Filter by status: OPEN, ACKNOWLEDGED, RESOLVED"),
    ] = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> AlertListResponse:
    return AlertService.get_machine_alerts(
        db=db,
        machine_id=machine_id,
        severity=severity,
        alert_status=status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{machine_id}/maintenance",
    response_model=MaintenanceListResponse,
    summary="Get machine maintenance history",
    description="Retrieve maintenance events, inspections, and component replacements for a machine.",
    responses={
        404: {"model": ProblemDetails, "description": "Machine not found"},
        422: {"model": ProblemDetails, "description": "Validation error"},
    },
)
def get_machine_maintenance(
    machine_id: MachineIdPath,
    db: DbDep,
    status: Annotated[
        str | None,
        Query(description="Filter by status: SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED"),
    ] = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> MaintenanceListResponse:
    return MaintenanceService.get_maintenance_events(
        db=db,
        machine_id=machine_id,
        event_status=status,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/{machine_id}/maintenance",
    response_model=MaintenanceDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule machine maintenance / work order (Privileged)",
    description="Create or schedule a maintenance event or work order for a machine. Requires Maintenance Engineer or Admin role.",
    responses={
        201: {"model": MaintenanceDTO, "description": "Maintenance event created"},
        400: {"model": ProblemDetails, "description": "Bad request or mismatched alert machine"},
        401: {"model": ProblemDetails, "description": "Unauthenticated"},
        403: {"model": ProblemDetails, "description": "Forbidden"},
        404: {"model": ProblemDetails, "description": "Machine or linked alert not found"},
        422: {"model": ProblemDetails, "description": "Validation error"},
    },
)
def create_machine_maintenance(
    payload: MaintenanceCreateRequest,
    machine_id: MachineIdPath,
    db: DbDep,
    current_user: Annotated[UserRecord, Depends(require_roles(PRIVILEGED_MAINTENANCE_ROLES))],
) -> MaintenanceDTO:
    res = MaintenanceService.create_maintenance_event(
        db=db,
        machine_id=machine_id,
        payload=payload,
        actor=current_user.username,
    )
    log_security_event(
        action="MAINTENANCE_CREATE",
        user=current_user.username,
        role=current_user.role,
        target=str(res.id),
        success=True,
        details={
            "machine_id": machine_id,
            "event_type": payload.event_type,
            "alert_id": payload.alert_id,
        },
    )
    return res


@router.post(
    "/{machine_id}/feedback",
    response_model=FeedbackDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Submit operator feedback",
    description="Submit human verification / ground-truth evaluation of a prediction or alert.",
    responses={
        201: {"model": FeedbackDTO, "description": "Feedback successfully recorded"},
        404: {
            "model": ProblemDetails,
            "description": "Machine, prediction, or alert reference not found",
        },
        422: {"model": ProblemDetails, "description": "Validation error"},
    },
)
def submit_feedback(
    payload: FeedbackCreateRequest,
    machine_id: MachineIdPath,
    db: DbDep,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
) -> FeedbackDTO:
    if not payload.technician_id:
        payload.technician_id = current_user.username

    res = FeedbackService.create_feedback(
        db=db,
        machine_id=machine_id,
        payload=payload,
    )
    log_security_event(
        action="FEEDBACK_SUBMIT",
        user=current_user.username,
        role=current_user.role,
        target=machine_id,
        success=True,
    )
    return res


@router.get(
    "/{machine_id}/feedback",
    response_model=FeedbackListResponse,
    summary="Get machine feedback history",
    description="Retrieve bounded operator/technician evaluation feedback history for a machine.",
    responses={
        401: {"model": ProblemDetails, "description": "Unauthenticated"},
        404: {"model": ProblemDetails, "description": "Machine not found"},
        422: {"model": ProblemDetails, "description": "Validation error"},
    },
)
def get_machine_feedback(
    machine_id: MachineIdPath,
    db: DbDep,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> FeedbackListResponse:
    return FeedbackService.get_feedback_by_machine(
        db=db,
        machine_id=machine_id,
        limit=limit,
        offset=offset,
    )
