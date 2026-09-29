"""
mlops/promote.py — EdgeTwin AI T-061 Champion/Challenger Promotion Gate & Rollback.

Implements the governed promotion lifecycle:
1. Champion/challenger technical comparison gate (val metrics only, NO test set).
2. Explicit promotion: assign 'champion' alias to passing challenger version.
3. Safe rollback: re-assign 'champion' alias to a known-good previous version.
4. Full audit trail for every promotion and rollback decision.

Promotion Gate Invariants
--------------------------
- Comparison uses val_df metrics ONLY (fetched from MLflow run metrics).
- The held-out test set is NEVER accessed for champion/challenger comparison.
- A challenger must pass ALL hard gates before promotion is possible.
- Promotion requires explicit actor authorization (no automatic promotion).
- Champion is never overwritten; rollback always targets a verified prior version.
- Every promotion and rollback is written to the immutable audit log.

Promotion Gate Criteria (val_df metrics at t* = 0.160)
-------------------------------------------------------
Hard gates (ALL must pass to proceed):
  1. val_recall    >= champion val_recall - RECALL_MARGIN (recall protection)
  2. val_precision >= MIN_PRECISION_FLOOR
  3. n_features    == 14  (feature contract)
  4. calibration_method == "sigmoid"  (calibration contract)
  5. operational_threshold == 0.160  (threshold contract)
  6. Technical inference gate (schema, bounds, threshold, risk bands)

Soft signal (informational, does not block promotion):
  - val_pr_auc vs champion val_pr_auc

Author: T-061 / S24
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import mlflow
from mlflow.tracking import MlflowClient

from mlops.register import (
    MODEL_NAME,
    verify_promotion_gate,
)
from mlops.retrain import (
    AUDIT_LOG_PATH,
    FROZEN_CALIBRATION_METHOD,
    FROZEN_N_FEATURES,
    FROZEN_THRESHOLD,
    RetrainAuditEntry,
    append_audit_log,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Promotion gate thresholds
# ---------------------------------------------------------------------------

#: A challenger's val_recall must be >= champion val_recall - RECALL_MARGIN.
#: Prevents recall regression when promoting a challenger.
RECALL_MARGIN: float = 0.05

#: Hard floor on challenger precision (any challenger below this is rejected).
MIN_PRECISION_FLOOR: float = 0.10

# ---------------------------------------------------------------------------
# Helpers: MLflow metadata extraction
# ---------------------------------------------------------------------------


def _get_model_version_info(client: MlflowClient, model_name: str, alias: str) -> dict[str, Any]:
    """Return version number, run_id, and run metrics for model *alias*.

    Raises
    ------
    RuntimeError
        If the alias does not resolve to any registered version.
    """
    try:
        mv = client.get_model_version_by_alias(model_name, alias)
    except Exception as exc:
        raise RuntimeError(f"Alias '{alias}' not found on model '{model_name}': {exc}") from exc

    run_id = mv.run_id
    version = mv.version

    run_metrics: dict[str, float] = {}
    if run_id:
        try:
            run = client.get_run(run_id)
            run_metrics = dict(run.data.metrics)
        except Exception:  # noqa: BLE001
            logger.warning(f"Could not fetch run metrics for run_id={run_id}")

    run_params: dict[str, str] = {}
    if run_id:
        try:
            run = client.get_run(run_id)
            run_params = dict(run.data.params)
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"Could not fetch run params for run_id={run_id}: {exc}")

    return {
        "version": version,
        "run_id": run_id,
        "metrics": run_metrics,
        "params": run_params,
    }


def get_champion_metrics(
    tracking_uri: str = "sqlite:///mlflow.db",
    model_name: str = MODEL_NAME,
) -> dict[str, Any]:
    """Return champion model metadata and val metrics from MLflow registry.

    Returns
    -------
    dict
        Keys: version, run_id, metrics (with val_recall, val_precision, etc.),
        params (with calibration_method, n_features, operational_threshold).
    """
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)
    return _get_model_version_info(client, model_name, "champion")


def get_challenger_metrics(
    tracking_uri: str = "sqlite:///mlflow.db",
    model_name: str = MODEL_NAME,
) -> dict[str, Any]:
    """Return challenger model metadata and val metrics from MLflow registry."""
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)
    return _get_model_version_info(client, model_name, "challenger")


# ---------------------------------------------------------------------------
# Comparison gate
# ---------------------------------------------------------------------------


@dataclass
class PromotionGateResult:
    """Result of a champion/challenger comparison gate evaluation."""

    gate_passed: bool
    challenger_version: str
    champion_version: str
    challenger_val_recall: float | None
    challenger_val_precision: float | None
    challenger_val_pr_auc: float | None
    champion_val_recall: float | None
    champion_val_precision: float | None
    champion_val_pr_auc: float | None
    recall_delta: float | None  # challenger - champion (positive = improvement)
    precision_delta: float | None
    pr_auc_delta: float | None
    checks_passed: list[str]
    checks_failed: list[str]
    gate_reason: str
    technical_gate: dict[str, Any]
    evaluated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_promotion_gate(
    tracking_uri: str = "sqlite:///mlflow.db",
    model_name: str = MODEL_NAME,
) -> PromotionGateResult:
    """Execute the champion/challenger promotion gate.

    Compares challenger (alias='challenger') against champion (alias='champion')
    using val_df metrics logged to MLflow. NO test set access.

    All five hard gate criteria must pass for gate_passed=True.

    Parameters
    ----------
    tracking_uri:
        MLflow tracking URI.
    model_name:
        Registered model name in MLflow registry.

    Returns
    -------
    PromotionGateResult
        Full gate result with per-check pass/fail and delta metrics.
    """
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)

    champion_info = _get_model_version_info(client, model_name, "champion")
    challenger_info = _get_model_version_info(client, model_name, "challenger")

    champ_v = champion_info["version"]
    chall_v = challenger_info["version"]
    champ_metrics = champion_info["metrics"]
    chall_metrics = challenger_info["metrics"]

    # Extract key metrics (val_df only — zero test set access)
    champ_recall = champ_metrics.get("val_recall_at_t_star")
    champ_precision = champ_metrics.get("val_precision_at_t_star")
    champ_pr_auc = champ_metrics.get("val_pr_auc")

    chall_recall = chall_metrics.get("val_recall_at_t_star")
    chall_precision = chall_metrics.get("val_precision_at_t_star")
    chall_pr_auc = chall_metrics.get("val_pr_auc")

    checks_passed: list[str] = []
    checks_failed: list[str] = []

    # -------------------------------------------------------------------------
    # Hard gate 1: Recall protection (challenger recall >= champion - RECALL_MARGIN)
    # -------------------------------------------------------------------------
    recall_delta: float | None = None
    if chall_recall is not None and champ_recall is not None:
        recall_delta = chall_recall - champ_recall
        if chall_recall >= champ_recall - RECALL_MARGIN:
            checks_passed.append(
                f"recall_protection: chall={chall_recall:.4f} >= "
                f"champ={champ_recall:.4f} - {RECALL_MARGIN}"
            )
        else:
            checks_failed.append(
                f"recall_protection: chall={chall_recall:.4f} < "
                f"champ={champ_recall:.4f} - {RECALL_MARGIN} = "
                f"{champ_recall - RECALL_MARGIN:.4f}"
            )
    else:
        checks_failed.append("recall_protection: missing val_recall_at_t_star in MLflow metrics")

    # -------------------------------------------------------------------------
    # Hard gate 2: Precision floor
    # -------------------------------------------------------------------------
    precision_delta: float | None = None
    if chall_precision is not None:
        if champ_precision is not None:
            precision_delta = chall_precision - champ_precision
        if chall_precision >= MIN_PRECISION_FLOOR:
            checks_passed.append(
                f"precision_floor: chall={chall_precision:.4f} >= {MIN_PRECISION_FLOOR}"
            )
        else:
            checks_failed.append(
                f"precision_floor: chall={chall_precision:.4f} < {MIN_PRECISION_FLOOR}"
            )
    else:
        checks_failed.append("precision_floor: missing val_precision_at_t_star in MLflow metrics")

    # -------------------------------------------------------------------------
    # Hard gate 3: Feature contract
    # -------------------------------------------------------------------------
    chall_params = challenger_info["params"]
    n_features_str = chall_params.get("n_features", "")
    try:
        n_features = int(n_features_str)
    except (ValueError, TypeError):
        n_features = -1
    if n_features == FROZEN_N_FEATURES:
        checks_passed.append(f"feature_contract: n_features={n_features} == {FROZEN_N_FEATURES}")
    else:
        checks_failed.append(f"feature_contract: n_features={n_features} != {FROZEN_N_FEATURES}")

    # -------------------------------------------------------------------------
    # Hard gate 4: Calibration contract
    # -------------------------------------------------------------------------
    cal_method = chall_params.get("calibration_method", "")
    if cal_method == FROZEN_CALIBRATION_METHOD:
        checks_passed.append(f"calibration_contract: method={cal_method}")
    else:
        checks_failed.append(
            f"calibration_contract: method={cal_method} != {FROZEN_CALIBRATION_METHOD}"
        )

    # -------------------------------------------------------------------------
    # Hard gate 5: Threshold contract
    # -------------------------------------------------------------------------
    try:
        registered_threshold = float(chall_params.get("operational_threshold", -1.0))
    except (ValueError, TypeError):
        registered_threshold = -1.0
    if abs(registered_threshold - FROZEN_THRESHOLD) < 1e-9:
        checks_passed.append(
            f"threshold_contract: threshold={registered_threshold} == {FROZEN_THRESHOLD}"
        )
    else:
        checks_failed.append(
            f"threshold_contract: threshold={registered_threshold} != {FROZEN_THRESHOLD}"
        )

    # -------------------------------------------------------------------------
    # Hard gate 6: Technical inference gate (schema, bounds, risk bands)
    # -------------------------------------------------------------------------
    tech_gate: dict[str, Any] = {}
    try:
        challenger_uri = f"models:/{model_name}@challenger"
        chall_metadata = {
            "calibration_method": FROZEN_CALIBRATION_METHOD,
            "operational_threshold": FROZEN_THRESHOLD,
            "n_features": FROZEN_N_FEATURES,
        }
        tech_gate = verify_promotion_gate(challenger_uri, metadata=chall_metadata)
        checks_passed.append("technical_inference_gate: PASSED")
    except Exception as exc:  # noqa: BLE001
        tech_gate = {"status": "FAILED", "error": str(exc)}
        checks_failed.append(f"technical_inference_gate: FAILED — {exc}")

    # -------------------------------------------------------------------------
    # Aggregate result
    # -------------------------------------------------------------------------
    pr_auc_delta: float | None = None
    if chall_pr_auc is not None and champ_pr_auc is not None:
        pr_auc_delta = chall_pr_auc - champ_pr_auc

    gate_passed = len(checks_failed) == 0

    if gate_passed:
        gate_reason = (
            f"All {len(checks_passed)} hard gate checks passed. "
            f"Challenger v{chall_v} is eligible for promotion to champion."
        )
    else:
        gate_reason = (
            f"{len(checks_failed)} hard gate check(s) failed. "
            f"Challenger v{chall_v} is NOT eligible for promotion. "
            f"Failures: {'; '.join(checks_failed)}"
        )

    logger.info(f"[T-061] Promotion gate: passed={gate_passed}, reason={gate_reason}")

    return PromotionGateResult(
        gate_passed=gate_passed,
        challenger_version=chall_v,
        champion_version=champ_v,
        challenger_val_recall=chall_recall,
        challenger_val_precision=chall_precision,
        challenger_val_pr_auc=chall_pr_auc,
        champion_val_recall=champ_recall,
        champion_val_precision=champ_precision,
        champion_val_pr_auc=champ_pr_auc,
        recall_delta=recall_delta,
        precision_delta=precision_delta,
        pr_auc_delta=pr_auc_delta,
        checks_passed=checks_passed,
        checks_failed=checks_failed,
        gate_reason=gate_reason,
        technical_gate=tech_gate,
    )


# ---------------------------------------------------------------------------
# Promotion
# ---------------------------------------------------------------------------


@dataclass
class PromotionResult:
    """Outcome of a promotion operation."""

    promoted: bool
    new_champion_version: str
    previous_champion_version: str
    actor: str
    gate_result: PromotionGateResult
    promoted_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def promote_challenger(
    actor: str,
    tracking_uri: str = "sqlite:///mlflow.db",
    model_name: str = MODEL_NAME,
    force: bool = False,
    audit_log_path: Path = AUDIT_LOG_PATH,
) -> PromotionResult:
    """Promote the challenger to champion if the promotion gate passes.

    This is an EXPLICIT human-initiated action. No automatic promotion occurs.

    Parameters
    ----------
    actor:
        Username of the engineer authorizing the promotion.
    tracking_uri:
        MLflow tracking URI.
    model_name:
        Registered model name.
    force:
        If True, bypass soft checks but still enforce hard gates. Reserved for
        future use; currently ALWAYS enforces all hard gate criteria.
    audit_log_path:
        Path to the append-only audit log.

    Returns
    -------
    PromotionResult
        Full promotion outcome including gate results.

    Raises
    ------
    ValueError
        If the promotion gate fails (hard gate criteria not met).
    RuntimeError
        If MLflow alias assignment fails.
    """
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)

    # 1. Retrieve current champion version (for rollback reference)
    try:
        prev_champ_info = _get_model_version_info(client, model_name, "champion")
        previous_champion_version = prev_champ_info["version"]
    except RuntimeError:
        previous_champion_version = "none"

    # 2. Run promotion gate
    gate_result = run_promotion_gate(tracking_uri=tracking_uri, model_name=model_name)

    if not gate_result.gate_passed:
        # Write audit entry for failed promotion attempt
        fail_entry = RetrainAuditEntry(
            event="promotion_gate_failed",
            actor=actor,
            challenger_version=gate_result.challenger_version,
            val_recall=gate_result.challenger_val_recall,
            val_precision=gate_result.challenger_val_precision,
            val_pr_auc=gate_result.challenger_val_pr_auc,
            notes=gate_result.gate_reason,
        )
        append_audit_log(fail_entry, audit_log_path)

        raise ValueError(
            f"Promotion gate FAILED for challenger v{gate_result.challenger_version}. "
            f"{gate_result.gate_reason}"
        )

    # 3. Promote: assign 'champion' alias to challenger version
    new_champion_version = gate_result.challenger_version
    client.set_registered_model_alias(model_name, "champion", new_champion_version)

    logger.info(
        f"[T-061] PROMOTED challenger v{new_champion_version} → champion "
        f"(previous champion: v{previous_champion_version}), actor={actor}"
    )

    # 4. Audit: promoted
    promote_entry = RetrainAuditEntry(
        event="promotion_completed",
        actor=actor,
        challenger_version=new_champion_version,
        val_recall=gate_result.challenger_val_recall,
        val_precision=gate_result.challenger_val_precision,
        val_pr_auc=gate_result.challenger_val_pr_auc,
        notes=(
            f"Promoted v{new_champion_version} to champion. "
            f"Previous champion: v{previous_champion_version}. "
            f"Gate: {gate_result.gate_reason}"
        ),
    )
    append_audit_log(promote_entry, audit_log_path)

    return PromotionResult(
        promoted=True,
        new_champion_version=new_champion_version,
        previous_champion_version=previous_champion_version,
        actor=actor,
        gate_result=gate_result,
    )


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------


@dataclass
class RollbackResult:
    """Outcome of a rollback operation."""

    rolled_back: bool
    restored_champion_version: str
    demoted_version: str
    actor: str
    reason: str
    rolled_back_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def rollback_champion(
    target_version: str,
    actor: str,
    reason: str,
    tracking_uri: str = "sqlite:///mlflow.db",
    model_name: str = MODEL_NAME,
    audit_log_path: Path = AUDIT_LOG_PATH,
) -> RollbackResult:
    """Roll back the champion alias to a specified previous model version.

    This is a SAFE rollback: it simply re-assigns the 'champion' alias to a
    prior verified version. No model artifacts are deleted or altered.

    Parameters
    ----------
    target_version:
        The model version string to restore as champion.
    actor:
        Username authorizing the rollback.
    reason:
        Mandatory narrative reason for the rollback (written to audit log).
    tracking_uri:
        MLflow tracking URI.
    model_name:
        Registered model name.
    audit_log_path:
        Path to the append-only audit log.

    Returns
    -------
    RollbackResult
        Full rollback outcome.

    Raises
    ------
    ValueError
        If target_version does not exist in the registry.
    RuntimeError
        If MLflow alias assignment fails.
    """
    if not reason or not reason.strip():
        raise ValueError("Rollback reason must be provided (non-empty string).")

    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)

    # Verify target_version exists
    model_versions = client.search_model_versions(f"name='{model_name}'")
    existing_versions = {v.version for v in model_versions}
    if str(target_version) not in existing_versions:
        raise ValueError(
            f"Target version '{target_version}' does not exist in registry for '{model_name}'. "
            f"Available versions: {sorted(existing_versions)}"
        )

    # Capture current champion before rollback
    try:
        current_info = _get_model_version_info(client, model_name, "champion")
        demoted_version = current_info["version"]
    except RuntimeError:
        demoted_version = "unknown"

    # Execute rollback: reassign 'champion' alias
    client.set_registered_model_alias(model_name, "champion", str(target_version))

    logger.warning(
        f"[T-061] ROLLBACK executed by actor={actor}: "
        f"champion demoted from v{demoted_version} → restored v{target_version}. "
        f"Reason: {reason}"
    )

    # Audit: rollback
    rollback_entry = RetrainAuditEntry(
        event="rollback_executed",
        actor=actor,
        challenger_version=demoted_version,  # reusing field: records demoted version
        notes=(f"Rolled back to v{target_version} from v{demoted_version}. " f"Reason: {reason}"),
    )
    append_audit_log(rollback_entry, audit_log_path)

    return RollbackResult(
        rolled_back=True,
        restored_champion_version=str(target_version),
        demoted_version=demoted_version,
        actor=actor,
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Registry listing helpers
# ---------------------------------------------------------------------------


def list_model_versions(
    tracking_uri: str = "sqlite:///mlflow.db",
    model_name: str = MODEL_NAME,
) -> list[dict[str, Any]]:
    """Return all registered model versions with their aliases and key metrics."""
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)

    model_versions = client.search_model_versions(f"name='{model_name}'")

    # Build alias lookup: version -> [alias, ...]
    alias_lookup: dict[str, list[str]] = {}
    try:
        rm = client.get_registered_model(model_name)
        for alias, version in (rm.aliases or {}).items():
            alias_lookup.setdefault(version, []).append(alias)
    except Exception as exc:  # noqa: BLE001
        logger.debug(f"Could not fetch aliases for model {model_name}: {exc}")

    results: list[dict[str, Any]] = []
    for mv in sorted(model_versions, key=lambda v: int(v.version)):
        metrics: dict[str, float] = {}
        if mv.run_id:
            try:
                run = client.get_run(mv.run_id)
                metrics = dict(run.data.metrics)
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"Could not fetch run metrics for {mv.run_id}: {exc}")

        results.append(
            {
                "version": mv.version,
                "status": mv.status,
                "aliases": alias_lookup.get(mv.version, []),
                "run_id": mv.run_id,
                "created_at": mv.creation_timestamp,
                "val_recall_at_t_star": metrics.get("val_recall_at_t_star"),
                "val_precision_at_t_star": metrics.get("val_precision_at_t_star"),
                "val_pr_auc": metrics.get("val_pr_auc"),
                "val_roc_auc": metrics.get("val_roc_auc"),
            }
        )

    return results
