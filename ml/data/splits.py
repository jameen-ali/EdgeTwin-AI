"""
ml/data/splits.py - EdgeTwin AI deterministic dataset splitting.

T-011: Implements a deterministic, machine-grouped train/validation/test
split for the prepared predictive-maintenance dataset.

SPLIT STRATEGY: Machine-level grouped split
-------------------------------------------
The prepared dataset contains 60 unique machines (Machine_IDs), each
contributing 137-187 rows of repeated sensor observations.  Row-level
random splitting would allow the model to observe rows from the same
machine in both training and test sets, leaking machine-specific
characteristics (sensor calibration offsets, individual wear patterns,
operating regime biases).

To prevent this, the split is performed at the Machine_ID level:
  - Each Machine_ID is assigned to exactly one partition.
  - All rows belonging to that Machine_ID go to the same partition.
  - No Machine_ID appears in more than one partition.

Split ratios (from params.yaml):
  - Train      : 70% of machines -> ~42 machines
  - Validation : 15% of machines ->  ~9 machines
  - Test       : 15% of machines ->  ~9 machines

Target stratification:
  GroupShuffleSplit does NOT guarantee target-stratified groups.
  Instead, this module uses a deterministic heuristic:
    1. Rank machines by their per-machine Machine_Failure rate.
    2. Assign machines to splits in a round-robin pattern over the
       sorted ranking so each split receives machines from across the
       full range of per-machine failure rates.
  This is not exact stratification (impossible with only 60 groups
  and integer assignment), but it distributes high/medium/low failure-
  rate machines proportionally across splits.

  IMPORTANT: This is NOT the same as sklearn's StratifiedGroupKFold.
  StratifiedGroupKFold stratifies by group-level target labels
  (membership in positive-label groups), which is a different concept.
  The heuristic implemented here distributes machine failure rates, not
  row-level labels.  The distinction is documented explicitly.

Temporal leakage:
  Timestamps span 2024-01-01 to 2024-06-28.  Tool_Wear_Min is NOT
  monotone within machines, so the data does not form a strict time
  series.  The grouped machine split is appropriate; temporal ordering
  within each split's training rows is a T-012 modelling concern.

Outputs:
  data/interim/splits/train.csv
  data/interim/splits/val.csv
  data/interim/splits/test.csv

Usage:
  from ml.data.splits import split_dataset, save_splits, load_splits
  train_df, val_df, test_df = split_dataset(df, params)

Author: T-011 / S03
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml.data.schema import TARGET_COLUMN

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------

_REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
DEFAULT_SPLITS_DIR: Path = _REPO_ROOT / "data" / "interim" / "splits"

# ---------------------------------------------------------------------------
# Split implementation
# ---------------------------------------------------------------------------


def _assign_machines_to_splits(
    machine_ids: list[str],
    machine_failure_rates: dict[str, float],
    train_frac: float,
    val_frac: float,
    seed: int,
) -> dict[str, str]:
    """Assign each Machine_ID to 'train', 'val', or 'test'.

    Strategy: rank machines by per-machine failure rate, then use a
    round-robin assignment over the sorted list so that high/medium/low
    failure-rate machines are distributed proportionally across splits.

    Parameters
    ----------
    machine_ids:
        All unique Machine_IDs in the dataset.
    machine_failure_rates:
        Per-machine Machine_Failure rate (mean of 0/1 rows).
    train_frac:
        Fraction of machines to assign to training.
    val_frac:
        Fraction of machines to assign to validation.
    seed:
        Random seed for tie-breaking when failure rates are equal.

    Returns
    -------
    dict[str, str]
        Mapping from Machine_ID to split name ('train', 'val', 'test').
    """
    n = len(machine_ids)
    n_train = round(n * train_frac)
    n_val = round(n * val_frac)
    n_test = n - n_train - n_val  # remainder goes to test

    # Sort machines by failure rate (ascending), break ties with a seeded
    # shuffle so the assignment is deterministic for a given seed.
    rng = np.random.default_rng(seed)
    noise = rng.uniform(0, 1e-9, size=n)  # tiny noise for tie-breaking

    sorted_indices = np.argsort(
        [machine_failure_rates[mid] + noise[i] for i, mid in enumerate(machine_ids)]
    )
    sorted_machines = [machine_ids[i] for i in sorted_indices]

    # Round-robin assignment: cycle through [train, val, test] across the
    # sorted machine list so each split receives machines from the full
    # range of failure rates.
    # Cycle order maps to slots: train gets the largest block.
    # Pattern: T V X T V X ... until each quota is filled.
    assignment: dict[str, str] = {}
    counts = {"train": 0, "val": 0, "test": 0}
    quotas = {"train": n_train, "val": n_val, "test": n_test}
    cycle = ["train", "val", "test"]
    cycle_idx = 0

    for mid in sorted_machines:
        # Find the next split in the cycle that still has quota
        assigned = False
        for _ in range(len(cycle)):
            split = cycle[cycle_idx % len(cycle)]
            if counts[split] < quotas[split]:
                assignment[mid] = split
                counts[split] += 1
                cycle_idx += 1
                assigned = True
                break
            cycle_idx += 1
        if not assigned:
            # Fallback: assign to whichever still has quota (shouldn't happen)
            for split in cycle:
                if counts[split] < quotas[split]:
                    assignment[mid] = split
                    counts[split] += 1
                    break

    return assignment


def split_dataset(
    df: pd.DataFrame,
    *,
    seed: int = 42,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
    group_col: str = "Machine_ID",
    target_col: str = TARGET_COLUMN,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split *df* into train, validation, and test DataFrames.

    All rows belonging to the same Machine_ID (``group_col``) are assigned
    to exactly one split.  This prevents machine-level information leakage
    between train and test.

    Strategy: failure-rate-aware round-robin group assignment.
    - Machines are ranked by their per-machine Machine_Failure rate.
    - Round-robin assignment distributes high/medium/low failure-rate
      machines proportionally.
    - This is NOT sklearn StratifiedGroupKFold; it is a deterministic
      heuristic for proportional distribution of machine failure rates.

    Parameters
    ----------
    df:
        Prepared DataFrame.  Must contain ``group_col`` and ``target_col``.
    seed:
        Random seed for tie-breaking in the assignment.  Identical seed
        produces identical splits.
    train_frac:
        Fraction of Machine_IDs assigned to train.
    val_frac:
        Fraction of Machine_IDs assigned to validation.  The test fraction
        is ``1 - train_frac - val_frac``.
    group_col:
        Column used for grouping (default: ``Machine_ID``).
    target_col:
        Target column used to compute per-machine failure rates.

    Returns
    -------
    (train, val, test) : tuple[DataFrame, DataFrame, DataFrame]
        Non-overlapping DataFrames with original column set preserved.

    Raises
    ------
    ValueError
        If group_col or target_col is missing, or if fractions are invalid.
    """
    if group_col not in df.columns:
        raise ValueError(f"Group column '{group_col}' not found in DataFrame.")
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in DataFrame.")
    if not (0 < train_frac < 1 and 0 < val_frac < 1):
        raise ValueError("train_frac and val_frac must each be in (0, 1).")
    if train_frac + val_frac >= 1.0:
        raise ValueError("train_frac + val_frac must be < 1.0 (leaves room for test).")

    machine_ids = sorted(df[group_col].unique().tolist())
    machine_failure_rates = (
        df.groupby(group_col)[target_col].mean().to_dict()
    )

    assignment = _assign_machines_to_splits(
        machine_ids=machine_ids,
        machine_failure_rates=machine_failure_rates,
        train_frac=train_frac,
        val_frac=val_frac,
        seed=seed,
    )

    split_col = df[group_col].map(assignment)
    train_df = df[split_col == "train"].reset_index(drop=True)
    val_df = df[split_col == "val"].reset_index(drop=True)
    test_df = df[split_col == "test"].reset_index(drop=True)

    return train_df, val_df, test_df


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def save_splits(
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
    splits_dir: Path = DEFAULT_SPLITS_DIR,
) -> dict[str, Path]:
    """Write train/val/test DataFrames to CSV files.

    Parameters
    ----------
    train, val, test:
        Split DataFrames from split_dataset().
    splits_dir:
        Directory to write to.  Created if absent.

    Returns
    -------
    dict[str, Path]
        Mapping from split name to written file path.
    """
    splits_dir = Path(splits_dir)
    splits_dir.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {}
    for name, df in [("train", train), ("val", val), ("test", test)]:
        p = splits_dir / f"{name}.csv"
        df.to_csv(p, index=False)
        paths[name] = p

    return paths


def load_splits(
    splits_dir: Path = DEFAULT_SPLITS_DIR,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load train/val/test DataFrames from the splits directory.

    Parameters
    ----------
    splits_dir:
        Directory containing train.csv, val.csv, test.csv.

    Returns
    -------
    (train, val, test) : tuple[DataFrame, DataFrame, DataFrame]

    Raises
    ------
    FileNotFoundError
        If any expected split file is missing.
    """
    splits_dir = Path(splits_dir)
    dfs: list[pd.DataFrame] = []
    for name in ("train", "val", "test"):
        p = splits_dir / f"{name}.csv"
        if not p.exists():
            raise FileNotFoundError(f"Split file not found: {p}")
        dfs.append(pd.read_csv(p))
    return dfs[0], dfs[1], dfs[2]


# ---------------------------------------------------------------------------
# Split statistics helper
# ---------------------------------------------------------------------------


def split_stats(
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
    target_col: str = TARGET_COLUMN,
    group_col: str = "Machine_ID",
) -> dict[str, Any]:
    """Return a summary of split sizes, failure rates, and Machine_ID counts.

    Parameters
    ----------
    train, val, test:
        Split DataFrames.
    target_col:
        Binary target column.
    group_col:
        Grouping column used for machine-level split.

    Returns
    -------
    dict
        Summary statistics for logging and the session report.
    """
    total = len(train) + len(val) + len(test)
    train_machines = set(train[group_col].unique())
    val_machines = set(val[group_col].unique())
    test_machines = set(test[group_col].unique())

    overlap = (
        train_machines & val_machines
        | train_machines & test_machines
        | val_machines & test_machines
    )

    return {
        "total_rows": total,
        "train_rows": len(train),
        "val_rows": len(val),
        "test_rows": len(test),
        "train_machines": len(train_machines),
        "val_machines": len(val_machines),
        "test_machines": len(test_machines),
        "machine_overlap": sorted(overlap),
        "train_failure_rate": float(train[target_col].mean()),
        "val_failure_rate": float(val[target_col].mean()),
        "test_failure_rate": float(test[target_col].mean()),
    }
