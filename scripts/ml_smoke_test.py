"""EdgeTwin AI - Production ML Operational Invariants Smoke Test (T-062).

Fast, deterministic verification script for CI pipelines and local deployment sanity checks.
Validates:
1. Serialized model artifacts presence and non-zero size.
2. 14-feature production contract (sensors + machine type + physics) without leakage.
3. Operational decision threshold is strictly 0.160.
4. ModelEngine loads champion and infers calibrated probability in [0, 1].
5. Risk-band categorization boundaries.
6. Isolation Forest anomaly scoring.

Returns exit code 0 on success, non-zero on invariant violation.
Zero access to held-out test data (data/test/).
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def main() -> int:
    """Run pytest suite on tests/ml/test_ml_smoke.py."""
    print("=" * 70)
    print("EdgeTwin AI — Running ML Production Smoke Test Suite")
    print("=" * 70)

    try:
        import pytest
    except ImportError:
        print(
            "ERROR: 'pytest' is required to execute the ML production smoke test suite.\n"
            "Please install test dependencies: pip install -e .[dev]",
            file=sys.stderr,
        )
        return 1

    test_path = _PROJECT_ROOT / "tests" / "ml" / "test_ml_smoke.py"
    if not test_path.is_file():
        print(f"ERROR: Smoke test file not found: {test_path}", file=sys.stderr)
        return 1

    exit_code = pytest.main(["-v", "-s", str(test_path)])
    if exit_code == 0:
        print("\n[SUCCESS] All ML production smoke invariants verified.")
    else:
        print(f"\n[FAILURE] ML smoke test failed with exit code: {exit_code}", file=sys.stderr)
    return int(exit_code)


if __name__ == "__main__":
    sys.exit(main())
