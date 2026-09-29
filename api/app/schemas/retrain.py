"""Pydantic schemas for T-061 governed retraining, promotion, and rollback API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Retraining schemas
# ---------------------------------------------------------------------------


class RetrainRequestDTO(BaseModel):
    """Request body for initiating a governed retrain."""

    run_name: str = Field(
        default="challenger-retrain",
        description="MLflow run name label for this retraining job",
    )
    seed: int = Field(
        default=42,
        ge=0,
        description="Random seed for full reproducibility",
    )
    notes: str = Field(
        default="",
        description="Optional audit notes for this retraining run",
    )

    model_config = ConfigDict(from_attributes=True)


class ChallengerResultDTO(BaseModel):
    """Result of a completed challenger retraining run."""

    run_id: str = Field(..., description="MLflow run ID for this retraining job")
    challenger_version: str = Field(..., description="MLflow model version number")
    challenger_uri: str = Field(..., description="MLflow model URI with challenger alias")
    val_recall: float = Field(..., description="Challenger val recall at t*=0.160")
    val_precision: float = Field(..., description="Challenger val precision at t*=0.160")
    val_pr_auc: float = Field(..., description="Challenger val PR-AUC")
    val_roc_auc: float = Field(..., description="Challenger val ROC-AUC")
    val_f1: float = Field(..., description="Challenger val F1 at t*=0.160")
    feature_cols: list[str] = Field(..., description="Feature columns used (14-feature contract)")
    artifacts_dir: str = Field(..., description="Local artifacts directory path")
    authorized_train_version: str = Field(
        default="v1.0-train-split", description="Authorized training data version"
    )
    train_sha256: str = Field(default="", description="SHA-256 checksum of training data")
    val_sha256: str = Field(default="", description="SHA-256 checksum of validation data")
    retrain_timestamp: str = Field(default="", description="UTC timestamp of retraining")

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# ---------------------------------------------------------------------------
# Promotion gate schemas
# ---------------------------------------------------------------------------


class PromotionGateDTO(BaseModel):
    """Champion/challenger promotion gate result."""

    gate_passed: bool = Field(..., description="True if all hard gate criteria passed")
    challenger_version: str = Field(..., description="Challenger model version")
    champion_version: str = Field(..., description="Current champion model version")
    challenger_val_recall: float | None = Field(None, description="Challenger val recall at t*")
    challenger_val_precision: float | None = Field(
        None, description="Challenger val precision at t*"
    )
    challenger_val_pr_auc: float | None = Field(None, description="Challenger val PR-AUC")
    champion_val_recall: float | None = Field(None, description="Champion val recall at t*")
    champion_val_precision: float | None = Field(None, description="Champion val precision at t*")
    champion_val_pr_auc: float | None = Field(None, description="Champion val PR-AUC")
    recall_delta: float | None = Field(
        None, description="Recall delta (challenger - champion); positive = improvement"
    )
    precision_delta: float | None = Field(
        None, description="Precision delta (challenger - champion)"
    )
    pr_auc_delta: float | None = Field(None, description="PR-AUC delta (challenger - champion)")
    checks_passed: list[str] = Field(default_factory=list, description="Passed gate checks")
    checks_failed: list[str] = Field(default_factory=list, description="Failed gate checks")
    gate_reason: str = Field(..., description="Human-readable gate verdict narrative")
    technical_gate: dict[str, Any] = Field(
        default_factory=dict, description="Technical inference gate details"
    )
    evaluated_at: str = Field(..., description="UTC timestamp of gate evaluation")

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Promotion schemas
# ---------------------------------------------------------------------------


class PromoteRequestDTO(BaseModel):
    """Request body for an explicit promotion action."""

    notes: str = Field(
        default="",
        description="Optional promotion notes written to audit log",
    )

    model_config = ConfigDict(from_attributes=True)


class PromotionResultDTO(BaseModel):
    """Result of a champion promotion operation."""

    promoted: bool = Field(..., description="True if promotion succeeded")
    new_champion_version: str = Field(..., description="Newly promoted champion version")
    previous_champion_version: str = Field(..., description="Version replaced as champion")
    actor: str = Field(..., description="Username who authorized promotion")
    gate_result: PromotionGateDTO = Field(..., description="Full gate evaluation result")
    promoted_at: str = Field(..., description="UTC timestamp of promotion")
    notes: str = Field(default="", description="Promotion notes")

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Rollback schemas
# ---------------------------------------------------------------------------


class RollbackRequestDTO(BaseModel):
    """Request body for a safe champion rollback."""

    target_version: str = Field(
        ...,
        description="Model registry version to restore as champion",
    )
    reason: str = Field(
        ...,
        min_length=10,
        description="Mandatory reason for rollback (minimum 10 characters, written to audit log)",
    )

    model_config = ConfigDict(from_attributes=True)


class RollbackResultDTO(BaseModel):
    """Result of a champion rollback operation."""

    rolled_back: bool = Field(..., description="True if rollback succeeded")
    restored_champion_version: str = Field(..., description="Model version restored as champion")
    demoted_version: str = Field(..., description="Model version demoted from champion")
    actor: str = Field(..., description="Username who authorized rollback")
    reason: str = Field(..., description="Rollback reason")
    rolled_back_at: str = Field(..., description="UTC timestamp of rollback")

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Model registry listing schemas
# ---------------------------------------------------------------------------


class ModelVersionDTO(BaseModel):
    """Summary of a single registered model version."""

    version: str = Field(..., description="Model version number")
    status: str = Field(..., description="Registry status (READY, etc.)")
    aliases: list[str] = Field(default_factory=list, description="Active aliases")
    run_id: str | None = Field(None, description="Associated MLflow run ID")
    created_at: int | None = Field(None, description="Creation timestamp (Unix ms)")
    val_recall_at_t_star: float | None = Field(None, description="Val recall at t*=0.160")
    val_precision_at_t_star: float | None = Field(None, description="Val precision at t*=0.160")
    val_pr_auc: float | None = Field(None, description="Val PR-AUC")
    val_roc_auc: float | None = Field(None, description="Val ROC-AUC")

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class ModelRegistryDTO(BaseModel):
    """Full model registry listing."""

    model_name: str = Field(..., description="Registered model name")
    total_versions: int = Field(..., description="Total number of registered versions")
    champion_version: str | None = Field(None, description="Current champion version")
    challenger_version: str | None = Field(None, description="Current challenger version")
    versions: list[ModelVersionDTO] = Field(..., description="All registered versions")
    generated_at: str = Field(..., description="UTC timestamp of registry query")

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# ---------------------------------------------------------------------------
# Audit log schemas
# ---------------------------------------------------------------------------


class AuditLogEntryDTO(BaseModel):
    """Single audit log entry."""

    event: str = Field(..., description="Audit event type")
    actor: str = Field(..., description="Username who initiated the event")
    timestamp: str = Field(..., description="UTC ISO timestamp")
    git_commit: str = Field(default="", description="Git commit SHA")
    authorized_train_version: str = Field(default="", description="Training data version")
    train_sha256: str = Field(default="", description="Training data SHA-256")
    val_sha256: str = Field(default="", description="Validation data SHA-256")
    mlflow_run_id: str = Field(default="", description="MLflow run ID")
    challenger_version: str = Field(default="", description="Challenger model version")
    val_recall: float | None = Field(None, description="Val recall at t*")
    val_precision: float | None = Field(None, description="Val precision at t*")
    val_pr_auc: float | None = Field(None, description="Val PR-AUC")
    notes: str = Field(default="", description="Event notes")
    error: str = Field(default="", description="Error message if event failed")

    model_config = ConfigDict(from_attributes=True)


class AuditLogDTO(BaseModel):
    """Full audit log response."""

    total_entries: int = Field(..., description="Total audit log entries")
    entries: list[AuditLogEntryDTO] = Field(..., description="Audit log entries")
    generated_at: str = Field(..., description="Query timestamp")

    model_config = ConfigDict(from_attributes=True)
