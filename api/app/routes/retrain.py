"""
api/app/routes/retrain.py — REST API endpoints for T-061 governed retraining lifecycle.

RBAC Policy
-----------
POST /retrain/run          → ADMIN, MAINTENANCE_ENGINEER  (initiate retrain)
GET  /retrain/gate         → ADMIN, MAINTENANCE_ENGINEER  (evaluate gate)
POST /retrain/promote      → ADMIN only                   (explicit promotion)
POST /retrain/rollback     → ADMIN only                   (safe rollback)
GET  /retrain/registry     → ADMIN, MAINTENANCE_ENGINEER  (list versions)
GET  /retrain/audit-log    → ADMIN only                   (audit trail)

All endpoints require valid JWT bearer authentication.
State-changing endpoints (POST) write to the immutable audit log.
Zero test-set access: service layer enforces governance invariants.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.app.models.user import UserRecord
from api.app.schemas.retrain import (
    AuditLogDTO,
    ChallengerResultDTO,
    ModelRegistryDTO,
    PromotionGateDTO,
    PromotionResultDTO,
    RetrainRequestDTO,
    RollbackRequestDTO,
    RollbackResultDTO,
)
from api.app.security.deps import require_roles
from api.app.security.roles import ADMIN_ONLY_ROLES, PRIVILEGED_MAINTENANCE_ROLES
from api.app.services.retrain_service import RetrainService

router = APIRouter(prefix="/retrain", tags=["MLOps — Retraining"])


@router.post(
    "/run",
    response_model=ChallengerResultDTO,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Run governed challenger retraining",
    description=(
        "Initiates a governed retraining job using the authorized training split "
        "(v1.0-train-split). Trains the frozen XGBoost +physics +sigmoid architecture, "
        "evaluates on val_df at t*=0.160, and registers the result as a challenger candidate. "
        "Zero test-set access. ADMIN and MAINTENANCE_ENGINEER roles required."
    ),
)
def run_retrain(
    request: RetrainRequestDTO,
    current_user: Annotated[
        UserRecord,
        Depends(require_roles(PRIVILEGED_MAINTENANCE_ROLES)),
    ],
) -> ChallengerResultDTO:
    """Initiate a governed challenger retraining run."""
    try:
        return RetrainService.run_retrain(actor=current_user.username, request=request)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Authorized training data not found: {exc}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Retraining validation failed: {exc}",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retraining pipeline failed: {exc}",
        ) from exc


@router.get(
    "/gate",
    response_model=PromotionGateDTO,
    summary="Evaluate champion/challenger promotion gate",
    description=(
        "Runs the promotion gate comparing the current challenger against the current champion "
        "using val_df metrics only (zero test-set access). Returns per-check pass/fail results "
        "and metric deltas. Does NOT change any model aliases."
    ),
)
def get_promotion_gate(
    current_user: Annotated[
        UserRecord,
        Depends(require_roles(PRIVILEGED_MAINTENANCE_ROLES)),
    ],
) -> PromotionGateDTO:
    """Evaluate the promotion gate without executing any promotion."""
    try:
        return RetrainService.get_promotion_gate()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not evaluate promotion gate: {exc}",
        ) from exc


@router.post(
    "/promote",
    response_model=PromotionResultDTO,
    summary="Promote challenger to champion",
    description=(
        "Explicitly promotes the challenger model to champion after the promotion gate passes. "
        "Requires ADMIN role. Writes a full audit log entry. "
        "Does NOT overwrite model artifacts — only reassigns the 'champion' alias."
    ),
)
def promote_challenger(
    current_user: Annotated[
        UserRecord,
        Depends(require_roles(ADMIN_ONLY_ROLES)),
    ],
) -> PromotionResultDTO:
    """Execute an explicit, admin-authorized promotion of challenger → champion."""
    try:
        return RetrainService.promote(actor=current_user.username)
    except ValueError as exc:
        # Gate failed — return 409 Conflict (the action cannot be performed in current state)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Promotion gate failed: {exc}",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Promotion failed: {exc}",
        ) from exc


@router.post(
    "/rollback",
    response_model=RollbackResultDTO,
    summary="Roll back champion to a prior version",
    description=(
        "Safely rolls back the 'champion' alias to a specified prior model version. "
        "No artifacts are deleted or modified — only the alias is reassigned. "
        "Requires ADMIN role. A mandatory reason must be provided. Writes a full audit log entry."
    ),
)
def rollback_champion(
    request: RollbackRequestDTO,
    current_user: Annotated[
        UserRecord,
        Depends(require_roles(ADMIN_ONLY_ROLES)),
    ],
) -> RollbackResultDTO:
    """Execute a safe rollback of the champion to a specified prior version."""
    try:
        return RetrainService.rollback(actor=current_user.username, request=request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Rollback validation failed: {exc}",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rollback failed: {exc}",
        ) from exc


@router.get(
    "/registry",
    response_model=ModelRegistryDTO,
    summary="List model registry versions",
    description=(
        "Returns all registered model versions with their aliases (champion/challenger) "
        "and val_df metrics. ADMIN and MAINTENANCE_ENGINEER roles required."
    ),
)
def get_model_registry(
    current_user: Annotated[
        UserRecord,
        Depends(require_roles(PRIVILEGED_MAINTENANCE_ROLES)),
    ],
) -> ModelRegistryDTO:
    """Retrieve the full model registry listing."""
    try:
        return RetrainService.get_model_registry()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not retrieve model registry: {exc}",
        ) from exc


@router.get(
    "/audit-log",
    response_model=AuditLogDTO,
    summary="Retrieve retraining audit log",
    description=(
        "Returns the append-only audit trail of all retraining, promotion, "
        "and rollback events. ADMIN role required."
    ),
)
def get_audit_log(
    current_user: Annotated[
        UserRecord,
        Depends(require_roles(ADMIN_ONLY_ROLES)),
    ],
    limit: int | None = Query(
        None,
        ge=1,
        le=1000,
        description="Maximum number of most-recent entries to return (None = all)",
    ),
) -> AuditLogDTO:
    """Retrieve the full or partial retraining audit log."""
    try:
        return RetrainService.get_audit_log(limit=limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not read audit log: {exc}",
        ) from exc
