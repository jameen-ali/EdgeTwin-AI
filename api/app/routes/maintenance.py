"""Fleet-wide maintenance and work-order management endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from api.app.db.session import get_db
from api.app.models.user import UserRecord
from api.app.schemas.common import ProblemDetails
from api.app.schemas.maintenance import (
    MaintenanceCreateWithMachineRequest,
    MaintenanceDTO,
    MaintenanceListResponse,
    MaintenanceUpdateRequest,
)
from api.app.security.audit import log_security_event
from api.app.security.deps import get_current_user, require_roles
from api.app.security.roles import PRIVILEGED_MAINTENANCE_ROLES
from api.app.services.maintenance_service import MaintenanceService

router = APIRouter(prefix="/maintenance", tags=["Maintenance"])

DbDep = Annotated[Session, Depends(get_db)]
LimitQuery = Annotated[
    int, Query(ge=1, le=100, description="Maximum maintenance records to return (1-100)")
]
OffsetQuery = Annotated[int, Query(ge=0, description="Offset for pagination")]


@router.get(
    "",
    response_model=MaintenanceListResponse,
    summary="List fleet maintenance events",
    description="Retrieve a bounded, paginated list of maintenance events and work orders across the factory fleet.",
    responses={
        401: {"model": ProblemDetails, "description": "Unauthenticated"},
        422: {"model": ProblemDetails, "description": "Validation error"},
        500: {"model": ProblemDetails, "description": "Internal server error"},
    },
)
def list_maintenance(
    db: DbDep,
    machine_id: Annotated[
        str | None,
        Query(description="Filter by machine ID"),
    ] = None,
    status: Annotated[
        str | None,
        Query(description="Filter by status: SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED"),
    ] = None,
    event_type: Annotated[
        str | None,
        Query(
            description="Filter by event type: INSPECTION, PART_REPLACEMENT, OVERHAUL, LUBRICATION, CALIBRATION"
        ),
    ] = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
    current_user: Annotated[UserRecord, Depends(get_current_user)] = None,  # type: ignore[assignment]
) -> MaintenanceListResponse:
    return MaintenanceService.list_all_maintenance(
        db=db,
        machine_id=machine_id,
        event_status=status,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=MaintenanceDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create maintenance event / work order (Privileged)",
    description="Schedule or log a new maintenance event or work order for any registered machine. Requires Maintenance Engineer or Admin role.",
    responses={
        201: {"model": MaintenanceDTO, "description": "Maintenance event created"},
        400: {"model": ProblemDetails, "description": "Bad request or mismatched alert machine"},
        401: {"model": ProblemDetails, "description": "Unauthenticated"},
        403: {"model": ProblemDetails, "description": "Forbidden"},
        404: {"model": ProblemDetails, "description": "Machine or linked alert not found"},
        422: {"model": ProblemDetails, "description": "Validation error"},
    },
)
def create_maintenance(
    payload: MaintenanceCreateWithMachineRequest,
    db: DbDep,
    current_user: Annotated[UserRecord, Depends(require_roles(PRIVILEGED_MAINTENANCE_ROLES))],
) -> MaintenanceDTO:
    res = MaintenanceService.create_maintenance_event(
        db=db,
        machine_id=payload.machine_id,
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
            "machine_id": payload.machine_id,
            "event_type": payload.event_type,
            "alert_id": payload.alert_id,
        },
    )
    return res


@router.get(
    "/{maintenance_id}",
    response_model=MaintenanceDTO,
    summary="Get maintenance event details",
    description="Retrieve full details for a maintenance event or work order by sequence ID.",
    responses={
        401: {"model": ProblemDetails, "description": "Unauthenticated"},
        404: {"model": ProblemDetails, "description": "Maintenance event not found"},
        422: {"model": ProblemDetails, "description": "Validation error"},
    },
)
def get_maintenance(
    maintenance_id: Annotated[int, Path(ge=1, description="Maintenance sequence ID")],
    db: DbDep,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
) -> MaintenanceDTO:
    return MaintenanceService.get_maintenance_by_id(db=db, maintenance_id=maintenance_id)


@router.patch(
    "/{maintenance_id}",
    response_model=MaintenanceDTO,
    summary="Update maintenance event / work order (Privileged)",
    description="Update the lifecycle status, technician, or notes of a maintenance event. Requires Maintenance Engineer or Admin role.",
    responses={
        400: {"model": ProblemDetails, "description": "Invalid status transition or payload"},
        401: {"model": ProblemDetails, "description": "Unauthenticated"},
        403: {"model": ProblemDetails, "description": "Forbidden"},
        404: {"model": ProblemDetails, "description": "Maintenance event not found"},
        422: {"model": ProblemDetails, "description": "Validation error"},
    },
)
def update_maintenance(
    payload: MaintenanceUpdateRequest,
    maintenance_id: Annotated[int, Path(ge=1, description="Maintenance sequence ID")],
    db: DbDep,
    current_user: Annotated[UserRecord, Depends(require_roles(PRIVILEGED_MAINTENANCE_ROLES))],
) -> MaintenanceDTO:
    res = MaintenanceService.update_maintenance_event(
        db=db,
        maintenance_id=maintenance_id,
        payload=payload,
        actor=current_user.username,
    )
    log_security_event(
        action="MAINTENANCE_UPDATE",
        user=current_user.username,
        role=current_user.role,
        target=str(maintenance_id),
        success=True,
        details={"status": payload.status, "technician": payload.technician},
    )
    return res
