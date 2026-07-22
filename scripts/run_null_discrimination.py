#!/usr/bin/env python3
"""Run the registered control and fatal-mutation discrimination packet."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ("control", "audit", "examples/claim_valid.json", 0),
    ("referenced-conflict", "audit", "examples/null_conflicting_referenced.json", 1),
    ("omitted-bound-failure", "audit", "examples/null_omitted_bound_failure.json", 1),
    ("failed-proof", "audit", "examples/null_failed_proof.json", 1),
    ("missing-arithmetic-config", "audit", "examples/null_missing_arithmetic_config.json", 2),
    ("derived-contractible-control", "holonomy", "examples/holonomy_contractible_derived_pass.json", 0),
    ("derived-homology-obstruction", "holonomy", "examples/holonomy_homology_obstruction.json", 1),
    ("observed-derived-control", "holonomy", "examples/holonomy_observed_quotient_pass.json", 0),
    ("illegal-edge-short-circuit", "holonomy", "examples/holonomy_non_chain_map.json", 1),
    ("missing-observation-projection", "holonomy", "examples/schema_holonomy_missing_projection.json", 2),
    ("audit-return-control", "return-desk", "examples/audit_return_valid.json", 0),
    ("audit-return-summary-strengthening", "return-desk", "examples/audit_return_poisoned_summary.json", 1),
    ("audit-return-omitted-bound-failure", "return-desk", "examples/audit_return_omitted_bound_failure.json", 1),
    ("audit-return-unreceipted-execution", "return-desk", "examples/audit_return_unreceipted_execution.json", 1),
    ("audit-return-missing-source-promotion", "return-desk", "examples/audit_return_missing_source_promotion.json", 1),
    ("audit-return-deployment-overreach", "return-desk", "examples/audit_return_deployment_overreach.json", 1),
    ("audit-return-receipt-only-promotion", "return-desk", "examples/audit_return_receipt_only_promotion.json", 1),
    ("audit-return-missing-artifact-review", "return-desk", "examples/audit_return_missing_artifact.json", 0),
)


def main() -> int:
    records: list[dict[str, object]] = []
    failed = False
    for name, command, relative, expected in CASES:
        result = subprocess.run(
            [sys.executable, "run_audit.py", command, relative],
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
                "command": command,
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
