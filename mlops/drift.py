"""
mlops/drift.py - EdgeTwin AI feature & data drift monitoring module.

T-060: Implements Population Stability Index (PSI) and Kolmogorov-Smirnov (KS)
distribution comparison against the authoritative training reference distribution.

Key Design & Governance Principles:
-----------------------------------
1. Reference Immutability & Traceability:
   - Compares CURRENT operational observations against the frozen training reference
     from data/interim/splits/train.csv (v1.0-train-split, 42 machines, 6,897 samples).
   - Reference bin edges are established once on the training data and are immutable.
   - Current production data CANNOT redefine reference bins.
   - NEVER touches or uses data/test/ (zero held-out leakage).

2. Statistical Methodology:
   - PSI (Continuous): Fixed decile binning from reference data with [-inf, +inf] bounds,
     epsilon smoothing for zero bins, deterministic calculation.
   - PSI (Categorical): Category proportions with unseen category / other binning.
   - KS Test: scipy.stats.ks_2samp applied strictly to continuous/numeric features.
     Categorical feature (Machine_Type) is explicitly excluded from KS (displays N/A).
   - Missing Data Monitoring: Missingness rate in reference vs current reported.

3. Honest Operational Interpretation:
   - Drift indicates distribution shift; it does NOT automatically mean model failure
     or machine degradation.
   - Minimum sample size guard (N_min = 30): Returns INSUFFICIENT_DATA rather than
     premature statistical conclusions on tiny samples.
   - Drift monitoring NEVER automatically retrains, promotes, or alters models.

Author: T-060 / S23
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from ml.data.engineering import apply_feature_set

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants & Monitored Feature Registry
# ---------------------------------------------------------------------------

CONTINUOUS_FEATURES: list[str] = [
    "Air_Temperature_C",
    "Process_Temperature_C",
    "Rotational_Speed_RPM",
    "Torque_Nm",
    "Vibration_mm_s",
    "Pressure_bar",
    "Current_A",
    "Voltage_V",
    "Tool_Wear_Min",
    "Operating_Hours",
    "Delta_T_C",
    "Apparent_Power_VA",
    "Mech_Power_W",
]

CATEGORICAL_FEATURES: list[str] = [
    "Machine_Type",
]

MONITORED_FEATURES: list[str] = CONTINUOUS_FEATURES + CATEGORICAL_FEATURES

# Minimum sample size to evaluate statistical drift
MIN_SAMPLE_SIZE: int = 30

# Epsilon to prevent log(0) and division by zero in PSI
DEFAULT_EPSILON: float = 1e-4

# Operational Thresholds (Project Monitoring Heuristics)
PSI_STABLE_THRESHOLD: float = 0.10
PSI_DRIFT_THRESHOLD: float = 0.25

KS_P_VALUE_THRESHOLD: float = 0.05
KS_STATISTIC_WATCH_THRESHOLD: float = 0.08
KS_STATISTIC_DRIFT_THRESHOLD: float = 0.15

MISSING_RATE_DELTA_THRESHOLD: float = 0.15

# Default Artifact Paths
_REPO_ROOT: Path = Path(__file__).resolve().parent.parent
DEFAULT_TRAIN_CSV: Path = _REPO_ROOT / "data" / "interim" / "splits" / "train.csv"
DEFAULT_REF_STATS_PATH: Path = _REPO_ROOT / "artifacts" / "training_reference_stats.json"


# ---------------------------------------------------------------------------
# Enums and Data Models
# ---------------------------------------------------------------------------


class DriftStatus(str, Enum):
    """Operational drift status classification."""

    STABLE = "STABLE"
    WATCH = "WATCH"
    DRIFT = "DRIFT"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass
class FeatureDriftResult:
    """Drift evaluation result for a single monitored feature."""

    feature_name: str
    feature_type: str  # "numeric" or "categorical"
    reference_count: int
    current_count: int
    psi: float | None
    ks_statistic: float | None
    ks_p_value: float | None
    missing_reference_pct: float
    missing_current_pct: float
    status: DriftStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary representation."""
        res = asdict(self)
        res["status"] = self.status.value
        return res


@dataclass
class DriftAlert:
    """Operational alert raised when feature drift exceeds watch/drift thresholds."""

    feature_name: str
    severity: str  # "WARNING" or "CRITICAL"
    metric: str  # "PSI" or "KS" or "DATA_QUALITY"
    value: float
    threshold: float
    message: str
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        """Convert alert to dictionary."""
        return asdict(self)


@dataclass
class DriftReport:
    """Complete multi-feature drift monitoring report."""

    model_version: str
    reference_version: str
    overall_status: DriftStatus
    reference_sample_count: int
    current_sample_count: int
    window_description: str
    generated_at: str
    feature_results: list[FeatureDriftResult]
    drift_alerts: list[DriftAlert]
    drifting_features_count: int
    watch_features_count: int
    stable_features_count: int

    def to_dict(self) -> dict[str, Any]:
        """Convert full report to dictionary."""
        return {
            "model_version": self.model_version,
            "reference_version": self.reference_version,
            "overall_status": self.overall_status.value,
            "reference_sample_count": self.reference_sample_count,
            "current_sample_count": self.current_sample_count,
            "window_description": self.window_description,
            "generated_at": self.generated_at,
            "features": [f.to_dict() for f in self.feature_results],
            "drift_alerts": [a.to_dict() for a in self.drift_alerts],
            "drifting_features_count": self.drifting_features_count,
            "watch_features_count": self.watch_features_count,
            "stable_features_count": self.stable_features_count,
        }


# ---------------------------------------------------------------------------
# PSI & KS Calculation Core
# ---------------------------------------------------------------------------


def calculate_psi(
    expected_proportions: np.ndarray,
    actual_proportions: np.ndarray,
    epsilon: float = DEFAULT_EPSILON,
) -> float:
    """Calculate Population Stability Index (PSI) between two discrete distributions.

    Formula:
        PSI = sum((q_i - p_i) * ln(q_i / p_i))
    where p_i = expected (reference), q_i = actual (current).

    Zero bins are smoothed using *epsilon* before normalization.
    """
    if len(expected_proportions) == 0 or len(actual_proportions) == 0:
        return 0.0

    p = np.maximum(expected_proportions, epsilon)
    p = p / np.sum(p)

    q = np.maximum(actual_proportions, epsilon)
    q = q / np.sum(q)

    psi_val = np.sum((q - p) * np.log(q / p))
    return float(max(0.0, psi_val))


def compute_continuous_psi(
    reference_proportions: list[float],
    interior_cuts: list[float],
    current_values: np.ndarray,
    epsilon: float = DEFAULT_EPSILON,
) -> float:
    """Compute PSI for a continuous feature using fixed reference interior cuts.

    Bins: [-inf, cut_1, cut_2, ..., cut_k, +inf]
    """
    if len(current_values) == 0:
        return 0.0

    bins = np.concatenate([[-np.inf], interior_cuts, [np.inf]])
    current_counts, _ = np.histogram(current_values, bins=bins)
    actual_proportions = current_counts / len(current_values)

    return calculate_psi(np.array(reference_proportions), actual_proportions, epsilon)


def compute_categorical_psi(
    reference_category_proportions: dict[str, float],
    current_categories: list[str] | pd.Series,
    epsilon: float = DEFAULT_EPSILON,
) -> float:
    """Compute PSI for a categorical feature based on category proportions.

    Unseen categories are grouped into an '__OTHER__' bucket.
    """
    if len(current_categories) == 0:
        return 0.0

    series = pd.Series(current_categories).dropna().astype(str)
    if len(series) == 0:
        return 0.0

    categories = list(reference_category_proportions.keys())
    ref_props = [reference_category_proportions[c] for c in categories]

    # Append __OTHER__ category with epsilon reference proportion
    categories.append("__OTHER__")
    ref_props.append(epsilon)
    ref_props_arr = np.array(ref_props)
    ref_props_arr = ref_props_arr / np.sum(ref_props_arr)

    counts = series.value_counts().to_dict()
    curr_counts = []
    other_count = 0
    for cat, count in counts.items():
        if cat in reference_category_proportions:
            pass
        else:
            other_count += count

    for cat in categories[:-1]:
        curr_counts.append(counts.get(cat, 0))
    curr_counts.append(other_count)

    curr_props = np.array(curr_counts, dtype=float) / len(series)
    return calculate_psi(ref_props_arr, curr_props, epsilon)


# ---------------------------------------------------------------------------
# Drift Reference Management
# ---------------------------------------------------------------------------


class DriftReference:
    """Encapsulates the immutable training reference baseline for drift detection."""

    def __init__(
        self,
        metadata: dict[str, Any],
        raw_numeric_samples: dict[str, np.ndarray] | None = None,
    ) -> None:
        self.metadata = metadata
        self.reference_version: str = metadata.get("reference_version", "v1.0-train-split")
        self.source_dataset: str = metadata.get("source_dataset", "train.csv")
        self.total_records: int = metadata.get("total_records", 0)
        self.features_meta: dict[str, Any] = metadata.get("features", {})
        self.raw_numeric_samples: dict[str, np.ndarray] = raw_numeric_samples or {}

    @classmethod
    def build_from_train_data(
        cls,
        train_csv_path: Path = DEFAULT_TRAIN_CSV,
        output_json_path: Path | None = DEFAULT_REF_STATS_PATH,
    ) -> DriftReference:
        """Deterministically compute reference stats from the training split."""
        if not train_csv_path.exists():
            raise FileNotFoundError(f"Training dataset not found at '{train_csv_path}'.")

        logger.info(f"Building drift reference profile from '{train_csv_path}'")
        train_df = pd.read_csv(train_csv_path)

        # Apply authoritative physics feature derivations
        feat_df = apply_feature_set(train_df, "+physics")

        features_meta: dict[str, Any] = {}
        raw_samples: dict[str, np.ndarray] = {}

        # 1. Process continuous features
        for col in CONTINUOUS_FEATURES:
            if col not in feat_df.columns:
                raise ValueError(
                    f"Required monitored feature '{col}' missing from engineered dataset."
                )

            series = feat_df[col]
            clean_vals = series.dropna().to_numpy(dtype=float)
            raw_samples[col] = clean_vals

            # 9 interior decile cuts creating 10 quantile bins
            interior_cuts = np.unique(np.quantile(clean_vals, np.linspace(0.1, 0.9, 9))).tolist()
            bins = np.concatenate([[-np.inf], interior_cuts, [np.inf]])
            counts, _ = np.histogram(clean_vals, bins=bins)
            ref_props = (counts / len(clean_vals)).tolist()

            features_meta[col] = {
                "type": "numeric",
                "count": len(clean_vals),
                "missing_count": int(series.isna().sum()),
                "missing_rate": float(series.isna().mean()),
                "min": float(clean_vals.min()),
                "max": float(clean_vals.max()),
                "mean": float(clean_vals.mean()),
                "std": float(clean_vals.std()),
                "interior_cuts": interior_cuts,
                "reference_proportions": ref_props,
            }

        # 2. Process categorical features
        for col in CATEGORICAL_FEATURES:
            series = feat_df[col]
            cat_counts = series.value_counts(dropna=True)
            cat_props = series.value_counts(dropna=True, normalize=True).to_dict()

            features_meta[col] = {
                "type": "categorical",
                "count": int(cat_counts.sum()),
                "missing_count": int(series.isna().sum()),
                "missing_rate": float(series.isna().mean()),
                "categories": {str(k): float(v) for k, v in cat_props.items()},
            }

        metadata = {
            "reference_version": "v1.0-train-split",
            "source_dataset": str(train_csv_path).replace("\\", "/"),
            "total_records": len(feat_df),
            "machine_count": (
                int(feat_df["Machine_ID"].nunique()) if "Machine_ID" in feat_df else 42
            ),
            "feature_count": len(features_meta),
            "created_at": datetime.now(UTC).isoformat(),
            "features": features_meta,
        }

        if output_json_path:
            output_json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Saved drift reference metadata to '{output_json_path}'")

        return cls(metadata, raw_numeric_samples=raw_samples)

    @classmethod
    def load(
        cls,
        json_path: Path = DEFAULT_REF_STATS_PATH,
        train_csv_path: Path = DEFAULT_TRAIN_CSV,
    ) -> DriftReference:
        """Load reference profile from JSON artifact, rebuilding if missing."""
        if not json_path.exists():
            return cls.build_from_train_data(train_csv_path, json_path)

        with open(json_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # For KS test, load raw numeric arrays from train.csv (or raw dataset fallback)
        raw_samples: dict[str, np.ndarray] = {}
        source_csv = train_csv_path
        if not source_csv.exists():
            fallback_raw = _REPO_ROOT / "data" / "raw" / "predictive_maintenance_dataset.csv"
            if fallback_raw.exists():
                source_csv = fallback_raw

        if source_csv.exists():
            try:
                train_df = pd.read_csv(source_csv)
                feat_df = apply_feature_set(train_df, "+physics")
                for col in CONTINUOUS_FEATURES:
                    if col in feat_df.columns:
                        raw_samples[col] = feat_df[col].dropna().to_numpy(dtype=float)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Could not load raw training values for KS test: {exc}")

        return cls(metadata, raw_numeric_samples=raw_samples)


_GLOBAL_REFERENCE: DriftReference | None = None


def get_drift_reference() -> DriftReference:
    """Retrieve or lazily initialize the singleton DriftReference."""
    global _GLOBAL_REFERENCE
    if _GLOBAL_REFERENCE is None:
        _GLOBAL_REFERENCE = DriftReference.load()
    return _GLOBAL_REFERENCE


# ---------------------------------------------------------------------------
# Feature Drift Evaluation
# ---------------------------------------------------------------------------


def evaluate_feature_drift(
    feature_name: str,
    current_series: pd.Series,
    reference: DriftReference,
    min_sample_size: int = MIN_SAMPLE_SIZE,
) -> FeatureDriftResult:
    """Evaluate drift metrics (PSI, KS, missingness) for a single feature."""
    ref_meta = reference.features_meta.get(feature_name)
    if not ref_meta:
        return FeatureDriftResult(
            feature_name=feature_name,
            feature_type="unknown",
            reference_count=0,
            current_count=len(current_series),
            psi=None,
            ks_statistic=None,
            ks_p_value=None,
            missing_reference_pct=0.0,
            missing_current_pct=float(current_series.isna().mean() * 100.0),
            status=DriftStatus.INSUFFICIENT_DATA,
            message=f"Feature '{feature_name}' not found in reference baseline.",
        )

    feat_type = ref_meta.get("type", "numeric")
    ref_count = ref_meta.get("count", 0)
    ref_missing_pct = float(ref_meta.get("missing_rate", 0.0) * 100.0)

    curr_total = len(current_series)
    curr_missing_count = int(current_series.isna().sum())
    curr_missing_pct = float((curr_missing_count / curr_total) * 100.0) if curr_total > 0 else 0.0

    non_null_current = current_series.dropna()
    curr_count = len(non_null_current)

    # 1. Sample Sufficiency Guard
    if curr_count < min_sample_size:
        return FeatureDriftResult(
            feature_name=feature_name,
            feature_type=feat_type,
            reference_count=ref_count,
            current_count=curr_count,
            psi=None,
            ks_statistic=None,
            ks_p_value=None,
            missing_reference_pct=round(ref_missing_pct, 2),
            missing_current_pct=round(curr_missing_pct, 2),
            status=DriftStatus.INSUFFICIENT_DATA,
            message=f"Insufficient observations (n={curr_count}; minimum required n={min_sample_size}).",
        )

    # 2. Evaluate Continuous Feature
    if feat_type == "numeric":
        cuts = ref_meta.get("interior_cuts", [])
        ref_props = ref_meta.get("reference_proportions", [])
        curr_vals = non_null_current.to_numpy(dtype=float)

        # PSI
        psi_val = compute_continuous_psi(ref_props, cuts, curr_vals)

        # KS Test
        ref_sample = reference.raw_numeric_samples.get(feature_name)
        if ref_sample is not None and len(ref_sample) > 0:
            ks_res = ks_2samp(ref_sample, curr_vals)
            ks_stat = float(ks_res.statistic)
            ks_pval = float(ks_res.pvalue)
        else:
            ks_stat = None
            ks_pval = None

        # Determine Feature Status
        # PSI condition
        psi_drift = psi_val >= PSI_DRIFT_THRESHOLD
        psi_watch = PSI_STABLE_THRESHOLD <= psi_val < PSI_DRIFT_THRESHOLD

        # KS condition
        ks_drift = False
        ks_watch = False
        if ks_stat is not None and ks_pval is not None:
            if ks_pval < KS_P_VALUE_THRESHOLD and ks_stat >= KS_STATISTIC_DRIFT_THRESHOLD:
                ks_drift = True
            elif (ks_pval < KS_P_VALUE_THRESHOLD and ks_stat >= KS_STATISTIC_WATCH_THRESHOLD) or (
                ks_stat >= KS_STATISTIC_DRIFT_THRESHOLD
            ):
                ks_watch = True

        # Missing data delta
        missing_delta = abs(curr_missing_pct - ref_missing_pct) / 100.0
        missing_watch = missing_delta > MISSING_RATE_DELTA_THRESHOLD

        if psi_drift or ks_drift:
            status = DriftStatus.DRIFT
            message = "Significant distribution drift detected vs training baseline."
        elif psi_watch or ks_watch or missing_watch:
            status = DriftStatus.WATCH
            message = "Moderate distribution shift or missingness change detected."
        else:
            status = DriftStatus.STABLE
            message = "Feature distribution consistent with training reference."

        return FeatureDriftResult(
            feature_name=feature_name,
            feature_type="numeric",
            reference_count=ref_count,
            current_count=curr_count,
            psi=round(psi_val, 4),
            ks_statistic=round(ks_stat, 4) if ks_stat is not None else None,
            ks_p_value=round(ks_pval, 6) if ks_pval is not None else None,
            missing_reference_pct=round(ref_missing_pct, 2),
            missing_current_pct=round(curr_missing_pct, 2),
            status=status,
            message=message,
            details={
                "mean_reference": ref_meta.get("mean"),
                "mean_current": round(float(curr_vals.mean()), 4) if len(curr_vals) > 0 else None,
                "std_current": round(float(curr_vals.std()), 4) if len(curr_vals) > 0 else None,
            },
        )

    # 3. Evaluate Categorical Feature (Machine_Type)
    ref_cats = ref_meta.get("categories", {})
    psi_val = compute_categorical_psi(ref_cats, non_null_current)

    if psi_val >= PSI_DRIFT_THRESHOLD:
        status = DriftStatus.DRIFT
        message = "Significant categorical proportion drift detected."
    elif psi_val >= PSI_STABLE_THRESHOLD:
        status = DriftStatus.WATCH
        message = "Moderate categorical proportion shift detected."
    else:
        status = DriftStatus.STABLE
        message = "Category distribution consistent with training baseline."

    return FeatureDriftResult(
        feature_name=feature_name,
        feature_type="categorical",
        reference_count=ref_count,
        current_count=curr_count,
        psi=round(psi_val, 4),
        ks_statistic=None,  # KS not applicable to categorical
        ks_p_value=None,  # KS not applicable to categorical
        missing_reference_pct=round(ref_missing_pct, 2),
        missing_current_pct=round(curr_missing_pct, 2),
        status=status,
        message=message,
        details={"reference_categories": ref_cats},
    )


# ---------------------------------------------------------------------------
# Multi-Feature Report Generation
# ---------------------------------------------------------------------------


def generate_drift_report(
    current_df: pd.DataFrame,
    reference: DriftReference | None = None,
    model_version: str = "v1.2-xgb",
    window_description: str = "Recent Operational Telemetry",
    min_sample_size: int = MIN_SAMPLE_SIZE,
) -> DriftReport:
    """Generate comprehensive drift assessment across all 14 monitored features."""
    if reference is None:
        reference = get_drift_reference()

    current_sample_count = len(current_df)

    # Check for empty or insufficient overall dataframe
    if current_sample_count < min_sample_size:
        feature_results = []
        for feat in MONITORED_FEATURES:
            feat_type = "categorical" if feat in CATEGORICAL_FEATURES else "numeric"
            ref_meta = reference.features_meta.get(feat, {})
            feature_results.append(
                FeatureDriftResult(
                    feature_name=feat,
                    feature_type=feat_type,
                    reference_count=ref_meta.get("count", 0),
                    current_count=current_sample_count,
                    psi=None,
                    ks_statistic=None,
                    ks_p_value=None,
                    missing_reference_pct=round(
                        float(ref_meta.get("missing_rate", 0.0) * 100.0), 2
                    ),
                    missing_current_pct=0.0,
                    status=DriftStatus.INSUFFICIENT_DATA,
                    message=f"Insufficient observations (n={current_sample_count}; minimum required n={min_sample_size}).",
                )
            )

        return DriftReport(
            model_version=model_version,
            reference_version=reference.reference_version,
            overall_status=DriftStatus.INSUFFICIENT_DATA,
            reference_sample_count=reference.total_records,
            current_sample_count=current_sample_count,
            window_description=window_description,
            generated_at=datetime.now(UTC).isoformat(),
            feature_results=feature_results,
            drift_alerts=[],
            drifting_features_count=0,
            watch_features_count=0,
            stable_features_count=0,
        )

    # Ensure engineered features are present if raw columns exist
    df_eval = current_df.copy()
    if "Process_Temperature_C" in df_eval.columns and "Delta_T_C" not in df_eval.columns:
        df_eval = apply_feature_set(df_eval, "+physics")

    feature_results = []
    drift_alerts = []
    drifting_count = 0
    watch_count = 0
    stable_count = 0

    for feat in MONITORED_FEATURES:
        if feat in df_eval.columns:
            series = df_eval[feat]
        else:
            series = pd.Series([np.nan] * len(df_eval), name=feat)

        result = evaluate_feature_drift(feat, series, reference, min_sample_size)
        feature_results.append(result)

        if result.status == DriftStatus.DRIFT:
            drifting_count += 1
            metric_name = "PSI" if (result.psi and result.psi >= PSI_DRIFT_THRESHOLD) else "KS"
            val = result.psi if metric_name == "PSI" else (result.ks_statistic or 0.0)
            thresh = PSI_DRIFT_THRESHOLD if metric_name == "PSI" else KS_STATISTIC_DRIFT_THRESHOLD
            drift_alerts.append(
                DriftAlert(
                    feature_name=feat,
                    severity="CRITICAL",
                    metric=metric_name,
                    value=round(val, 4),
                    threshold=thresh,
                    message=f"Feature '{feat}' exhibits severe distribution drift ({metric_name}={val:.3f} >= {thresh}).",
                    recommendation="Investigate sensor calibration or physical operating condition changes; review operator feedback.",
                )
            )
        elif result.status == DriftStatus.WATCH:
            watch_count += 1
            drift_alerts.append(
                DriftAlert(
                    feature_name=feat,
                    severity="WARNING",
                    metric="PSI" if (result.psi and result.psi >= PSI_STABLE_THRESHOLD) else "KS",
                    value=(
                        result.psi
                        if (result.psi and result.psi >= PSI_STABLE_THRESHOLD)
                        else (result.ks_statistic or 0.0)
                    ),
                    threshold=PSI_STABLE_THRESHOLD,
                    message=f"Feature '{feat}' exhibits moderate distribution shift.",
                    recommendation="Monitor feature over next 24-48 hours; check for operating regime shifts.",
                )
            )
        elif result.status == DriftStatus.STABLE:
            stable_count += 1

    # Aggregate Overall Status
    if drifting_count > 0:
        overall_status = DriftStatus.DRIFT
    elif watch_count > 0:
        overall_status = DriftStatus.WATCH
    else:
        overall_status = DriftStatus.STABLE

    return DriftReport(
        model_version=model_version,
        reference_version=reference.reference_version,
        overall_status=overall_status,
        reference_sample_count=reference.total_records,
        current_sample_count=current_sample_count,
        window_description=window_description,
        generated_at=datetime.now(UTC).isoformat(),
        feature_results=feature_results,
        drift_alerts=drift_alerts,
        drifting_features_count=drifting_count,
        watch_features_count=watch_count,
        stable_features_count=stable_count,
    )
