"""Historical analytics and trend exploration endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from api.app.db.session import get_db
from api.app.schemas.common import ProblemDetails
from api.app.schemas.history import FleetHistoryResponse, MachineHistoryResponse
from api.app.security.deps import get_current_user
from api.app.services.history_service import HistoryService

router = APIRouter(
    prefix="/history",
    tags=["History"],
    dependencies=[Depends(get_current_user)],
)

MACHINE_ID_PATTERN = r"^[A-Z0-9_-]{1,32}$"

DbDep = Annotated[Session, Depends(get_db)]
MachineIdPath = Annotated[
    str,
    Path(..., pattern=MACHINE_ID_PATTERN, description="Machine identifier (e.g. MOT-1001)"),
]


@router.get(
    "/machines/{machine_id}",
    response_model=MachineHistoryResponse,
    summary="Get machine historical analytics",
    description="Retrieve bounded, downsampled historical telemetry, health trends, predictions, and operational events.",
    responses={
        401: {"model": ProblemDetails, "description": "Unauthenticated"},
        404: {"model": ProblemDetails, "description": "Machine not found"},
        422: {"model": ProblemDetails, "description": "Validation error"},
    },
)
def get_machine_history(
    machine_id: MachineIdPath,
    db: DbDep,
    window: Annotated[
        str,
        Query(description="Time window horizon: 1h, 6h, 24h, 7d, 30d"),
    ] = "24h",
    before: Annotated[
        datetime | None,
        Query(description="Filter observations before this ISO-8601 UTC timestamp"),
    ] = None,
    after: Annotated[
        datetime | None,
        Query(description="Filter observations after this ISO-8601 UTC timestamp"),
    ] = None,
    max_points: Annotated[
        int,
        Query(ge=10, le=500, description="Maximum time-series points to return for charting"),
    ] = 120,
) -> MachineHistoryResponse:
    """Retrieve comprehensive historical timeline and trend metrics for a specific machine asset."""
    return HistoryService.get_machine_history(
        db=db,
        machine_id=machine_id,
        window=window,
        before=before,
        after=after,
        max_points=max_points,
    )


@router.get(
    "/fleet",
    response_model=FleetHistoryResponse,
    summary="Get fleet historical analytics",
    description="Retrieve aggregated fleet-wide health distributions, risk bands, and incident frequencies.",
    responses={
        401: {"model": ProblemDetails, "description": "Unauthenticated"},
        422: {"model": ProblemDetails, "description": "Validation error"},
    },
)
def get_fleet_history(
    db: DbDep,
    window: Annotated[
        str,
        Query(description="Time window horizon: 1h, 6h, 24h, 7d, 30d"),
    ] = "24h",
    before: Annotated[
        datetime | None,
        Query(description="Filter observations before this ISO-8601 UTC timestamp"),
    ] = None,
    after: Annotated[
        datetime | None,
        Query(description="Filter observations after this ISO-8601 UTC timestamp"),
    ] = None,
) -> FleetHistoryResponse:
    """Retrieve aggregate operational health and incident statistics across all fleet machines."""
    return HistoryService.get_fleet_history(
        db=db,
        window=window,
        before=before,
        after=after,
    )
