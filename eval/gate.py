"""
Pre-merge quality gate for Meridian.

Reads scores.json written by eval/run.py and exits non-zero if
context_precision is below the 0.85 threshold.

Usage:
    python -m eval.run && python -m eval.gate

Exit codes:
    0  context_precision >= 0.85
    1  context_precision < 0.85
    2  scores.json not found
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCORES_PATH = Path(__file__).parent / "scores.json"
METRIC = "context_precision"
THRESHOLD = 0.85


def main() -> None:
    if not SCORES_PATH.exists():
        print(
            f"error: {SCORES_PATH} not found - run 'python -m eval.run' first",
            file=sys.stderr,
        )
        sys.exit(2)

    scores: dict[str, float] = json.loads(SCORES_PATH.read_text())

    if METRIC not in scores:
        print(
            f"error: metric '{METRIC}' not in {SCORES_PATH} - available: {list(scores.keys())}",
            file=sys.stderr,
        )
        sys.exit(2)

    score = scores[METRIC]

    print("=" * 50)
    print("MERIDIAN QUALITY GATE")
    print("=" * 50)
    print(f"  metric     : {METRIC}")
    print(f"  score      : {score:.4f}")
    print(f"  threshold  : {THRESHOLD}")

    if score >= THRESHOLD:
        print(f"  result     : PASS")
        print("=" * 50)
        sys.exit(0)
    else:
        gap = THRESHOLD - score
        print(f"  result     : FAIL  (gap: {gap:.4f})")
        print("=" * 50)
        print(
            f"gate failed - {METRIC} {score:.4f} is below threshold {THRESHOLD}\n"
            "refer to ADR 003 for chunking strategy guidance"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
