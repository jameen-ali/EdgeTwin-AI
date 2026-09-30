#!/usr/bin/env python
"""
scripts/download_ai4i.py - Download AI4I 2020 Predictive Maintenance Dataset.

The raw CSV is gitignored (data/raw/*.csv). Run this script once to fetch it
before running the T-071 generalization benchmark.

Dataset: UCI ML Repository
License: CC BY 4.0 (Stephan Matzka, HTW Berlin)
URL: https://archive.ics.uci.edu/ml/datasets/AI4I+2020+Predictive+Maintenance+Dataset

Usage:
    python scripts/download_ai4i.py
"""

import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "raw" / "ai4i2020.csv"
URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/00601/ai4i2020.csv"


def main() -> None:
    if OUT.exists():
        size = OUT.stat().st_size
        print(f"Already present: {OUT} ({size:,} bytes)")
        return
    print(f"Downloading AI4I 2020 -> {OUT}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(URL, str(OUT))
    size = OUT.stat().st_size
    print(f"Done: {size:,} bytes")


if __name__ == "__main__":
    main()
