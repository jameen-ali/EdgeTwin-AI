"""Root conftest.py to ensure sys.path includes the project root."""

import os
import sys
from pathlib import Path

os.environ["MLFLOW_SKIP_PIP_REQUIREMENTS_CHECK"] = "true"

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
