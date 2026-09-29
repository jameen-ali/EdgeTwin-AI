"""
api/app/services/retrain_service.py — Service layer for T-061 governed retraining lifecycle.

Orchestrates:
1. Challenger retraining (assemble → train → calibrate → register)
2. Promotion gate evaluation (champion/challenger comparison, val metrics only)
3. Explicit promotion (actor-authorized, audit-logged)
4. Safe rollback (alias reassignment only, no artifact deletion)
5. Model registry listing
6. Audit log retrieval

Governance rules enforced here:
- All state-changing operations receive actor identity from the authenticated user.
- Zero test-set access: service layer never loads or references test.csv.
- No automatic promotion is possible through this service.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from api.app.config import get_settings
from api.app.schemas.retrain import (
    AuditLogDTO,
    AuditLogEntryDTO,
    ChallengerResultDTO,
    ModelRegistryDTO,
    ModelVersionDTO,
    PromotionGateDTO,
    PromotionResultDTO,
    RetrainRequestDTO,
    RollbackRequestDTO,
    RollbackResultDTO,
)
from mlops.promote import (
    PromotionGateResult,
    list_model_versions,
    promote_challenger,
    rollback_champion,
    run_promotion_gate,
)
from mlops.retrain import (
    AUDIT_LOG_PATH,
    ChallengerResult,
    read_audit_log,
    train_challenger,
)

logger = logging.getLogger(__name__)

# Default MLflow tracking URI — matches the rest of the project
_DEFAULT_TRACKING_URI: str = "sqlite:///mlflow.db"
_DEFAULT_ARTIFACTS_DIR: Path = Path("artifacts")


def _get_tracking_uri() -> str:
    """Return the MLflow tracking URI from settings or default."""
    try:
        settings = get_settings()
        return getattr(settings, "MLFLOW_TRACKING_URI", _DEFAULT_TRACKING_URI)
    except Exception:  # noqa: BLE001
        return _DEFAULT_TRACKING_URI


def _challenger_result_to_dto(result: ChallengerResult) -> ChallengerResultDTO:
    """Map ChallengerResult to ChallengerResultDTO."""
    metadata = result.metadata or {}
    return ChallengerResultDTO(
        run_id=result.run_id,
        challenger_version=result.challenger_version,
        challenger_uri=result.challenger_uri,
        val_recall=result.val_recall,
        val_precision=result.val_precision,
        val_pr_auc=result.val_pr_auc,
        val_roc_auc=result.val_roc_auc,
        val_f1=result.val_f1,
        feature_cols=result.feature_cols,
        artifacts_dir=result.artifacts_dir,
        authorized_train_version=str(metadata.get("authorized_train_version", "v1.0-train-split")),
        train_sha256=str(metadata.get("train_sha256", "")),
        val_sha256=str(metadata.get("val_sha256", "")),
        retrain_timestamp=str(metadata.get("retrain_timestamp", "")),
    )


def _gate_result_to_dto(gate: PromotionGateResult) -> PromotionGateDTO:
    """Map PromotionGateResult to PromotionGateDTO."""
    return PromotionGateDTO(
        gate_passed=gate.gate_passed,
        challenger_version=gate.challenger_version,
        champion_version=gate.champion_version,
        challenger_val_recall=gate.challenger_val_recall,
        challenger_val_precision=gate.challenger_val_precision,
        challenger_val_pr_auc=gate.challenger_val_pr_auc,
        champion_val_recall=gate.champion_val_recall,
        champion_val_precision=gate.champion_val_precision,
        champion_val_pr_auc=gate.champion_val_pr_auc,
        recall_delta=gate.recall_delta,
        precision_delta=gate.precision_delta,
        pr_auc_delta=gate.pr_auc_delta,
        checks_passed=gate.checks_passed,
        checks_failed=gate.checks_failed,
        gate_reason=gate.gate_reason,
        technical_gate=gate.technical_gate,
        evaluated_at=gate.evaluated_at,
    )


class RetrainService:
    """Service for governed MLOps retraining, promotion, and rollback operations."""

    @staticmethod
    def run_retrain(actor: str, request: RetrainRequestDTO) -> ChallengerResultDTO:
        """Assemble authorized dataset, train challenger, register with MLflow.

        Parameters
        ----------
        actor:
            Authenticated username from the request context.
        request:
            Retrain parameters (run_name, seed, notes).

        Returns
        -------
        ChallengerResultDTO
            Full retraining outcome with val metrics and artifact references.
        """
        tracking_uri = _get_tracking_uri()
        logger.info(f"[RetrainService] Initiating retrain for actor={actor}")

        result = train_challenger(
            actor=actor,
            tracking_uri=tracking_uri,
            artifacts_dir=_DEFAULT_ARTIFACTS_DIR,
            run_name=request.run_name,
            seed=request.seed,
            audit_log_path=AUDIT_LOG_PATH,
        )

        return _challenger_result_to_dto(result)

    @staticmethod
    def get_promotion_gate() -> PromotionGateDTO:
        """Evaluate the champion/challenger promotion gate (val metrics, NO test set).

        Returns
        -------
        PromotionGateDTO
            Gate result with per-check pass/fail and metric deltas.
        """
        tracking_uri = _get_tracking_uri()
        gate = run_promotion_gate(tracking_uri=tracking_uri)
        return _gate_result_to_dto(gate)

    @staticmethod
    def promote(actor: str) -> PromotionResultDTO:
        """Execute an explicit, actor-authorized promotion of challenger to champion.

        Parameters
        ----------
        actor:
            Authenticated username who is authorizing the promotion.

        Returns
        -------
        PromotionResultDTO

        Raises
        ------
        ValueError
            If the promotion gate fails.
        """
        tracking_uri = _get_tracking_uri()
        logger.info(f"[RetrainService] Promotion requested by actor={actor}")

        result = promote_challenger(
            actor=actor,
            tracking_uri=tracking_uri,
            audit_log_path=AUDIT_LOG_PATH,
        )

        return PromotionResultDTO(
            promoted=result.promoted,
            new_champion_version=result.new_champion_version,
            previous_champion_version=result.previous_champion_version,
            actor=result.actor,
            gate_result=_gate_result_to_dto(result.gate_result),
            promoted_at=result.promoted_at,
            notes="",
        )

    @staticmethod
    def rollback(actor: str, request: RollbackRequestDTO) -> RollbackResultDTO:
        """Execute a safe rollback: restore a prior model version as champion.

        Parameters
        ----------
        actor:
            Authenticated username authorizing the rollback.
        request:
            Target version and mandatory reason.

        Returns
        -------
        RollbackResultDTO
        """
        tracking_uri = _get_tracking_uri()
        logger.warning(
            f"[RetrainService] Rollback requested by actor={actor} "
            f"to version={request.target_version}: {request.reason}"
        )

        result = rollback_champion(
            target_version=request.target_version,
            actor=actor,
            reason=request.reason,
            tracking_uri=tracking_uri,
            audit_log_path=AUDIT_LOG_PATH,
        )

        return RollbackResultDTO(
            rolled_back=result.rolled_back,
            restored_champion_version=result.restored_champion_version,
            demoted_version=result.demoted_version,
            actor=result.actor,
            reason=result.reason,
            rolled_back_at=result.rolled_back_at,
        )

    @staticmethod
    def get_model_registry() -> ModelRegistryDTO:
        """Return the full model registry listing with all versions and aliases.

        Returns
        -------
        ModelRegistryDTO
        """
        from mlops.register import MODEL_NAME

        tracking_uri = _get_tracking_uri()
        versions_raw = list_model_versions(tracking_uri=tracking_uri)

        versions: list[ModelVersionDTO] = []
        champion_version: str | None = None
        challenger_version: str | None = None

        for v in versions_raw:
            dto = ModelVersionDTO(
                version=v["version"],
                status=v.get("status", "UNKNOWN"),
                aliases=v.get("aliases", []),
                run_id=v.get("run_id"),
                created_at=v.get("created_at"),
                val_recall_at_t_star=v.get("val_recall_at_t_star"),
                val_precision_at_t_star=v.get("val_precision_at_t_star"),
                val_pr_auc=v.get("val_pr_auc"),
                val_roc_auc=v.get("val_roc_auc"),
            )
            versions.append(dto)
            if "champion" in dto.aliases:
                champion_version = dto.version
            if "challenger" in dto.aliases:
                challenger_version = dto.version

        return ModelRegistryDTO(
            model_name=MODEL_NAME,
            total_versions=len(versions),
            champion_version=champion_version,
            challenger_version=challenger_version,
            versions=versions,
            generated_at=datetime.now(UTC).isoformat(),
        )

    @staticmethod
    def get_audit_log(limit: int | None = None) -> AuditLogDTO:
        """Return the retraining audit log.

        Parameters
        ----------
        limit:
            Maximum number of most-recent entries to return (None = all).

        Returns
        -------
        AuditLogDTO
        """
        entries_raw = read_audit_log(AUDIT_LOG_PATH)

        # Return in reverse-chronological order (most recent first)
        entries_raw_sorted = list(reversed(entries_raw))
        if limit is not None:
            entries_raw_sorted = entries_raw_sorted[:limit]

        entries: list[AuditLogEntryDTO] = []
        for raw in entries_raw_sorted:
            entries.append(
                AuditLogEntryDTO(
                    event=raw.get("event", ""),
                    actor=raw.get("actor", ""),
                    timestamp=raw.get("timestamp", ""),
                    git_commit=raw.get("git_commit", ""),
                    authorized_train_version=raw.get("authorized_train_version", ""),
                    train_sha256=raw.get("train_sha256", ""),
                    val_sha256=raw.get("val_sha256", ""),
                    mlflow_run_id=raw.get("mlflow_run_id", ""),
                    challenger_version=raw.get("challenger_version", ""),
                    val_recall=raw.get("val_recall"),
                    val_precision=raw.get("val_precision"),
                    val_pr_auc=raw.get("val_pr_auc"),
                    notes=raw.get("notes", ""),
                    error=raw.get("error", ""),
                )
            )

        return AuditLogDTO(
            total_entries=len(read_audit_log(AUDIT_LOG_PATH)),
            entries=entries,
            generated_at=datetime.now(UTC).isoformat(),
        )
