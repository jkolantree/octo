#!/usr/bin/env python3
"""Emit a machine-readable fail-closed Custom GPT package verdict."""

from __future__ import annotations

import json

from build_gpt_package import public_version, verify_package


def main() -> int:
    failures = verify_package()
    print(
        json.dumps(
            {
                "decision": "pass" if not failures else "blocked",
                "bsc_version": public_version(),
                "checks_run": [
                    "deterministic_regeneration",
                    "source_and_artifact_sha256_binding",
                    "strict_json_and_jsonl",
                    "exact_reviewed_instruction_rule_registry",
                    "provenance_path_and_anchor_binding",
                    "audit_depth_and_output_order",
                    "evaluation_fixture_discovery",
                    "evaluation_source_containment",
                    "required_workflow_case_registry",
                    "per_case_scoring_criteria",
                    "poisoned_false_pass_demotion",
                    "safe_path_and_symlink_contract",
                    "unpublished_and_no_action_boundary",
                ],
                "findings": failures,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
