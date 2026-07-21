#!/usr/bin/env python3
"""Run the registered control and fatal-mutation discrimination packet."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ("control", "examples/claim_valid.json", 0),
    ("referenced-conflict", "examples/null_conflicting_referenced.json", 1),
    ("omitted-bound-failure", "examples/null_omitted_bound_failure.json", 1),
    ("failed-proof", "examples/null_failed_proof.json", 1),
    ("missing-arithmetic-config", "examples/null_missing_arithmetic_config.json", 2),
)


def main() -> int:
    records: list[dict[str, object]] = []
    failed = False
    for name, relative, expected in CASES:
        result = subprocess.run(
            [sys.executable, "run_audit.py", "audit", relative],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            payload = {"decision": "invalid_output", "findings": []}
        correct = result.returncode == expected
        failed = failed or not correct
        records.append(
            {
                "name": name,
                "input": relative,
                "expected_exit": expected,
                "actual_exit": result.returncode,
                "decision": payload.get("decision"),
                "finding_codes": [item.get("code") for item in payload.get("findings", []) if isinstance(item, dict)],
                "discriminated": correct,
            }
        )
    print(json.dumps({"suite": "null-discrimination-v1", "cases": records}, indent=2, sort_keys=True))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
