from __future__ import annotations

from pathlib import Path
from typing import Any

from .findings import Finding, Severity
from .provenance import is_placeholder_sha256, verify_local_artifact


PASS_TOKENS = {
    "lean4": "accepted",
    "smtlib2": "unsat",
    "interval": "enclosed",
}

TOKEN_OUTCOMES = {
    "lean4": {"accepted": "pass", "rejected": "fail", "unknown": "inconclusive", "error": "error"},
    "smtlib2": {"unsat": "pass", "sat": "fail", "unknown": "inconclusive", "error": "error"},
    "interval": {"enclosed": "pass", "violated": "fail", "unknown": "inconclusive", "error": "error"},
}

CERTIFICATE_FORMATS = {
    "lean4": {"lean4-kernel-check"},
    "smtlib2": {"alethe", "lfsc", "drat"},
    "interval": {"exact-interval-replay"},
}

ARTIFACT_ROLES = (
    ("job", "$.job"),
    ("subject", "$.subject"),
    ("environment", "$.environment"),
    ("certificate", "$.certificate"),
)


def _artifact_finding(role: str, path: str, reason: str, actual: str | None) -> Finding:
    witness = {"role": role, "reason": reason}
    if actual is not None:
        witness["actual_sha256"] = actual
    return Finding(
        Severity.BLOCKED,
        "ADAPTER_ARTIFACT_UNVERIFIED",
        path,
        f"the {role} artifact did not pass local path and hash verification",
        witness=witness,
        repair="supply the exact local artifact below the receipt directory with its non-placeholder SHA-256",
    )


def audit_adapter_receipt(raw: dict[str, Any], artifact_root: Path | None) -> list[Finding]:
    """Audit an adapter receipt without granting it proof authority."""

    findings: list[Finding] = []
    for role, path in ARTIFACT_ROLES:
        reference = raw[role]
        ok, reason, actual = verify_local_artifact(artifact_root, reference["artifact"], reference["sha256"])
        if not ok:
            findings.append(_artifact_finding(role, path, reason, actual))

    transcript = raw["execution"]["transcript"]
    for stream in ("stdout", "stderr"):
        reference = transcript[stream]
        ok, reason, actual = verify_local_artifact(artifact_root, reference["artifact"], reference["sha256"])
        if not ok:
            findings.append(_artifact_finding(f"execution.{stream}", f"$.execution.transcript.{stream}", reason, actual))

    adapter = raw["adapter"]
    kind = adapter["kind"]
    for role, tool in (("adapter", adapter), ("checker", raw["verification"]["checker"])):
        if is_placeholder_sha256(tool["executable_sha256"]):
            findings.append(
                Finding(
                    Severity.BLOCKED,
                    "ADAPTER_TOOL_HASH_PLACEHOLDER",
                    f"$.{role}.executable_sha256" if role == "adapter" else "$.verification.checker.executable_sha256",
                    f"the {role} executable hash is a forbidden all-zero placeholder",
                )
            )
    certificate_format = raw["certificate"]["format"]
    if certificate_format not in CERTIFICATE_FORMATS[kind]:
        findings.append(
            Finding(
                Severity.BLOCKED,
                "ADAPTER_CERTIFICATE_FORMAT_MISMATCH",
                "$.certificate.format",
                f"certificate format {certificate_format!r} is not registered for adapter kind {kind!r}",
                witness={"allowed": sorted(CERTIFICATE_FORMATS[kind])},
            )
        )

    verification = raw["verification"]
    allowed = set(verification["assumption_policy"]["allowed"])
    observed = set(verification["assumption_policy"]["observed"])
    undeclared = sorted(observed - allowed)
    if undeclared:
        findings.append(
            Finding(
                Severity.BLOCKED,
                "ADAPTER_UNDECLARED_ASSUMPTION",
                "$.verification.assumption_policy",
                "the replay reported assumptions outside the declared allow-list",
                witness={"undeclared": undeclared},
            )
        )

    result_token = raw["result_token"]
    expected_outcome = TOKEN_OUTCOMES[kind].get(result_token)
    if expected_outcome is None:
        findings.append(
            Finding(
                Severity.BLOCKED,
                "ADAPTER_RESULT_TOKEN_KIND_MISMATCH",
                "$.result_token",
                f"result token {result_token!r} is not defined for adapter kind {kind!r}",
                witness={"allowed": sorted(TOKEN_OUTCOMES[kind])},
            )
        )
    elif raw["outcome"] != expected_outcome:
        findings.append(
            Finding(
                Severity.BLOCKED,
                "ADAPTER_OUTCOME_TOKEN_MISMATCH",
                "$.outcome",
                f"result token {result_token!r} requires adapter outcome {expected_outcome!r}",
            )
        )

    if raw["outcome"] == "pass":
        if raw["execution"]["exit_code"] != 0:
            findings.append(
                Finding(
                    Severity.BLOCKED,
                    "ADAPTER_PASS_EXIT_MISMATCH",
                    "$.execution.exit_code",
                    "a passing adapter outcome requires process exit code zero",
                )
            )
        if result_token != PASS_TOKENS[kind]:
            findings.append(
                Finding(
                    Severity.BLOCKED,
                    "ADAPTER_PASS_TOKEN_MISMATCH",
                    "$.result_token",
                    f"a passing {kind} receipt requires result token {PASS_TOKENS[kind]!r}",
                )
            )
    if raw["outcome"] in {"pass", "fail"}:
        if not verification["replay_verified"]:
            findings.append(
                Finding(
                    Severity.BLOCKED,
                    "ADAPTER_REPLAY_MISSING",
                    "$.verification.replay_verified",
                    "a decisive receipt requires a successful checker replay",
                )
            )
        if kind in {"smtlib2", "interval"} and verification["checker_relation"] != "independent_checker":
            findings.append(
                Finding(
                    Severity.BLOCKED,
                    "ADAPTER_INDEPENDENT_CHECKER_REQUIRED",
                    "$.verification.checker_relation",
                    f"a decisive {kind} receipt requires an independent certificate checker",
                )
            )

    findings.append(
        Finding(
            Severity.WARNING,
            "ADAPTER_RECEIPT_NON_ADMISSIVE",
            "$.authority",
            "this preview validates receipt structure, bindings, and internal consistency only; it does not satisfy a theorem or admission gate",
            repair="future engine versions must execute the pinned adapter and checker under a supervised, fail-closed runner before granting gate authority",
        )
    )
    if not any(finding.severity in {Severity.ERROR, Severity.BLOCKED, Severity.DEMOTION} for finding in findings):
        findings.append(
            Finding(
                Severity.INFO,
                "ADAPTER_RECEIPT_BOUND",
                "$",
                "all declared receipt artifacts are locally hash-bound and the adapter outcome is internally consistent",
            )
        )
    return findings
