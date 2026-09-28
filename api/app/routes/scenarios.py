"""Scenario control and command guard endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.db.session import get_db
from api.app.models.machine import MachineRecord
from api.app.models.user import UserRecord
from api.app.schemas.common import ProblemDetails
from api.app.schemas.scenario import (
    CANONICAL_SCENARIOS,
    ScenarioInjectRequest,
    ScenarioInjectResponse,
    ScenarioListResponse,
    ScenarioSummary,
)
from api.app.security.audit import log_security_event
from api.app.security.deps import get_current_user, require_roles
from api.app.security.roles import PRIVILEGED_MAINTENANCE_ROLES

router = APIRouter(prefix="/scenarios", tags=["Scenarios & Command Guard"])

DbDep = Annotated[Session, Depends(get_db)]


@router.get(
    "",
    response_model=ScenarioListResponse,
    summary="List canonical fault and simulation scenarios",
    description="Retrieve inventory of validated physical simulation scenarios (SCN-01 to SCN-08).",
    responses={
        401: {"model": ProblemDetails, "description": "Unauthenticated"},
    },
)
def list_scenarios(
    current_user: Annotated[UserRecord, Depends(get_current_user)],
) -> ScenarioListResponse:
    """Return list of authorized simulation scenarios."""
    summaries = [
        ScenarioSummary(
            scenario_id=sc_id,
            name=meta["name"],
            description=meta["description"],
            target_fault=meta["target_fault"],
        )
        for sc_id, meta in CANONICAL_SCENARIOS.items()
    ]
    return ScenarioListResponse(scenarios=summaries, total=len(summaries))


@router.post(
    "/inject",
    response_model=ScenarioInjectResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Inject a simulation fault scenario (Privileged)",
    description="Dispatch an approved scenario (SCN-01 through SCN-08) to a targeted simulated machine under command guard authorization.",
    responses={
        202: {"model": ScenarioInjectResponse, "description": "Command accepted for execution"},
        401: {"model": ProblemDetails, "description": "Unauthenticated"},
        403: {
            "model": ProblemDetails,
            "description": "Forbidden: Requires Maintenance Engineer or Admin role",
        },
        404: {"model": ProblemDetails, "description": "Target machine not found"},
        422: {"model": ProblemDetails, "description": "Invalid scenario ID or payload"},
    },
)
def inject_scenario(
    payload: ScenarioInjectRequest,
    db: DbDep,
    current_user: Annotated[UserRecord, Depends(require_roles(PRIVILEGED_MAINTENANCE_ROLES))],
) -> ScenarioInjectResponse:
    """Validate and dispatch an authorized fault simulation scenario."""
    # 1. Target Machine Validation
    machine = db.execute(
        select(MachineRecord).where(MachineRecord.machine_id == payload.machine_id)
    ).scalar_one_or_none()

    if machine is None:
        log_security_event(
            action="SCENARIO_INJECT",
            user=current_user.username,
            role=current_user.role,
            target=payload.machine_id,
            success=False,
            details={"error": "machine_not_found", "scenario": payload.scenario_id.value},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine '{payload.machine_id}' was not found in registered fleet.",
        )

    # 2. Command Safety Check: disallow arbitrary shell or python execution parameters
    forbidden_keys = {"__", "eval", "exec", "system", "os", "subprocess", "sh"}
    param_keys = set(payload.parameters.keys())
    if any(k.lower() in forbidden_keys for k in param_keys):
        log_security_event(
            action="COMMAND_GUARD_BLOCKED",
            user=current_user.username,
            role=current_user.role,
            target=payload.machine_id,
            success=False,
            details={"reason": "unsafe_parameter_detected", "keys": list(param_keys)},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsafe execution parameter detected. Arbitrary command execution is forbidden.",
        )

    # 3. Generate dispatch command ID and audit log
    command_id = str(uuid.uuid4())
    log_security_event(
        action="SCENARIO_INJECT",
        user=current_user.username,
        role=current_user.role,
        target=f"{payload.machine_id}:{payload.scenario_id.value}",
        success=True,
        details={"command_id": command_id, "parameters": payload.parameters},
    )

    scenario_name = CANONICAL_SCENARIOS.get(payload.scenario_id.value, {}).get(
        "name", payload.scenario_id.value
    )

    return ScenarioInjectResponse(
        command_id=command_id,
        machine_id=payload.machine_id,
        scenario_id=payload.scenario_id.value,
        status="ACCEPTED",
        message=f"Scenario '{scenario_name}' accepted for simulated machine '{payload.machine_id}'.",
        injected_by=current_user.username,
        injected_at=datetime.now(UTC),
    )
