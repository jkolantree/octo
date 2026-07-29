from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .findings import Finding, Severity
from .judgment import CheckedJudgment
from .plugins import DOMAIN_CHECK_FIELDS, TRACE_REQUIRED_OBLIGATIONS
from .provenance import (
    MAX_ARTIFACT_BYTES,
    is_placeholder_sha256,
    is_sha256,
    sha256_json,
    verify_local_artifact,
)
from .theorem import (
    FORMAL_ONLY_SCOPE,
    LANGUAGE,
    MAX_CERTIFICATE_BYTES,
    SCIENTIFIC_TRUTH_STATE,
    THEOREM_AUTHORITY,
    THEOREM_AUTHORITY_SCOPE,
    THEOREM_GATE_ID,
    TheoremReplay,
    canonical_formal_title,
    canonical_formal_statement,
    load_and_replay_theorem_certificate,
)


SUPPORTED_MANIFEST_VERSIONS = {"0.3.0", "0.4.0"}
REQUIRED_TOP = (
    "manifest_version",
    "draft",
    "claim",
    "system",
    "observation",
    "representation",
    "target",
    "experiment",
    "admission",
    "demotion",
    "preservation",
)
OBJECT_TOP = set(REQUIRED_TOP) - {"manifest_version", "draft"}
CLAIM_TYPES = {
    "definition",
    "theorem",
    "theorem_schema",
    "conjecture",
    "diagnostic",
    "empirical_claim",
    "analogy",
    "open_problem",
}
DEPLOYMENT_STATES = {"research_only", "sandboxed", "candidate", "admitted", "retired"}
EVIDENCE_MATURITY = {"declared", "structurally_checked", "empirically_passed", "externally_replicated"}
EVIDENCE_STATUS = {"declared", "verified"}
EVIDENCE_RESULTS = {"pass", "fail", "inconclusive"}
EVIDENCE_KINDS = {
    "proof",
    "formal_proof",
    "exact_certificate",
    "dataset",
    "statistical_certificate",
    "experimental_record",
    "independent_replication",
    "counterexample",
    "audit_report",
}
PROOF_KINDS = {"proof", "formal_proof", "exact_certificate"}
SUPPORTED_DOMAIN_CHECKS = {"arithmetic_trace", "global_recovery"}
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{2,191}$")
PLACEHOLDERS = {
    "draft",
    "placeholder",
    "replace me",
    "replace-me",
    "tbd",
    "todo",
    "unassigned",
    "not set",
}

ArtifactVerification = tuple[bool, str, str | None]
ArtifactVerificationKey = tuple[str | None, str, str, int]
TheoremArtifactKey = tuple[str | None, str, str]
TheoremReplayKey = tuple[str, str, str]

MAX_THEOREM_ARTIFACTS_PER_AUDIT = 32
MAX_THEOREM_REPLAYS_PER_AUDIT = 16
THEOREM_PROFILE_DEPLOYMENT_STATES = {"research_only", "sandboxed"}


@dataclass
class _ManifestAuditContext:
    """Per-audit cache for immutable artifact verification and theorem replay."""

    artifact_verifications: dict[ArtifactVerificationKey, ArtifactVerification] = field(
        default_factory=dict
    )
    theorem_artifacts: set[TheoremArtifactKey] = field(default_factory=set)
    theorem_replays: dict[TheoremReplayKey, TheoremReplay] = field(
        default_factory=dict
    )
    theorem_replays_started: int = 0


def _root_cache_key(root: Path | None) -> str | None:
    if root is None:
        return None
    try:
        return str(root.resolve())
    except (OSError, RuntimeError):
        return None


def _verify_local_artifact_cached(
    cache: _ManifestAuditContext,
    root: Path | None,
    relative_path: object,
    expected_hash: object,
    *,
    max_bytes: int = MAX_ARTIFACT_BYTES,
    theorem_artifact: bool = False,
) -> ArtifactVerification:
    if not isinstance(relative_path, str) or not isinstance(expected_hash, str):
        return verify_local_artifact(
            root,
            relative_path,
            expected_hash,
            max_bytes=max_bytes,
        )
    key = (_root_cache_key(root), relative_path, expected_hash, max_bytes)
    if key not in cache.artifact_verifications:
        theorem_key = key[:3]
        if (
            theorem_artifact
            and is_sha256(expected_hash)
            and not is_placeholder_sha256(expected_hash)
            and theorem_key not in cache.theorem_artifacts
        ):
            if len(cache.theorem_artifacts) >= MAX_THEOREM_ARTIFACTS_PER_AUDIT:
                cache.artifact_verifications[key] = (
                    False,
                    "theorem_artifact_limit",
                    None,
                )
                return cache.artifact_verifications[key]
            cache.theorem_artifacts.add(theorem_key)
        cache.artifact_verifications[key] = verify_local_artifact(
            root,
            relative_path,
            expected_hash,
            max_bytes=max_bytes,
        )
    return cache.artifact_verifications[key]


def get_path(raw: dict[str, Any], path: str, default: Any = None) -> Any:
    value: Any = raw
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    return value


def _is_placeholder(value: object) -> bool:
    if not isinstance(value, str):
        return False
    normalized = " ".join(value.strip().lower().split())
    return normalized in PLACEHOLDERS or "replace-me" in normalized or "replace me" in normalized


def _required_string(
    findings: list[Finding],
    container: dict[str, Any],
    field: str,
    path: str,
    *,
    minimum: int = 1,
) -> None:
    value = container.get(field)
    field_path = f"{path}.{field}"
    if not isinstance(value, str) or len(value.strip()) < minimum:
        findings.append(Finding(Severity.ERROR, "FIELD_REQUIRED", field_path, "required substantive string is missing"))
    elif _is_placeholder(value):
        findings.append(Finding(Severity.BLOCKED, "DRAFT_PLACEHOLDER", field_path, "placeholder text cannot support promotion"))


def _evidence_records(raw: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = raw.get("evidence", [])
    return [item for item in evidence if isinstance(item, dict)] if isinstance(evidence, list) else []


def _closed_theorem_contract(raw: dict[str, Any]) -> bool:
    claim = raw.get("claim")
    return (
        raw.get("manifest_version") == "0.4.0"
        and isinstance(claim, dict)
        and claim.get("type") == "theorem_schema"
        and claim.get("family") == LANGUAGE
    )


def _semantic_hash_or_none(value: object) -> str | None:
    try:
        return sha256_json(value)
    except (TypeError, ValueError):
        return None


def _closed_theorem_profile_findings(claim: dict[str, Any]) -> list[Finding]:
    """Bind a closed theorem manifest to its formal, non-scientific meaning."""

    findings: list[Finding] = []
    formal_statement = claim.get("formal_statement")
    try:
        canonical_title = canonical_formal_title(formal_statement)
        canonical_statement = canonical_formal_statement(formal_statement)
    except (TypeError, ValueError):
        canonical_title = None
        canonical_statement = None

    if canonical_title is not None and claim.get("title") != canonical_title:
        findings.append(
            Finding(
                Severity.BLOCKED,
                "THEOREM_TITLE_NOT_CANONICAL",
                "claim.title",
                "closed theorem titles must use the deterministic formal profile; free-form scientific titles are non-admissible",
                witness={
                    "canonical_formal_title": canonical_title,
                    "provided_title_sha256": _semantic_hash_or_none(
                        claim.get("title")
                    ),
                    "authority": THEOREM_AUTHORITY,
                    "authority_scope": THEOREM_AUTHORITY_SCOPE,
                    "scientific_truth": SCIENTIFIC_TRUTH_STATE,
                },
                repair="replace claim.title with canonical_formal_title exactly",
            )
        )
    if (
        canonical_statement is not None
        and claim.get("statement") != canonical_statement
    ):
        findings.append(
            Finding(
                Severity.BLOCKED,
                "THEOREM_STATEMENT_NOT_CANONICAL",
                "claim.statement",
                "closed theorem claims must use the deterministic AST projection; free-form theorem gloss is non-admissible",
                witness={
                    "canonical_formal_statement": canonical_statement,
                    "provided_statement_sha256": _semantic_hash_or_none(
                        claim.get("statement")
                    ),
                    "authority": THEOREM_AUTHORITY,
                    "authority_scope": THEOREM_AUTHORITY_SCOPE,
                    "scientific_truth": SCIENTIFIC_TRUTH_STATE,
                },
                repair="replace claim.statement with canonical_formal_statement exactly",
            )
        )
    if claim.get("scope") != FORMAL_ONLY_SCOPE:
        findings.append(
            Finding(
                Severity.BLOCKED,
                "THEOREM_SCOPE_NOT_FORMAL_ONLY",
                "claim.scope",
                "closed theorem scope cannot extend beyond the exact formal identity",
                witness={
                    "required_scope": FORMAL_ONLY_SCOPE,
                    "provided_scope_sha256": _semantic_hash_or_none(
                        claim.get("scope")
                    ),
                    "scientific_truth": SCIENTIFIC_TRUTH_STATE,
                },
                repair="use the fixed formal-only scope exactly",
            )
        )
    if claim.get("evidence_maturity") != "structurally_checked":
        findings.append(
            Finding(
                Severity.BLOCKED,
                "THEOREM_MATURITY_OUT_OF_SCOPE",
                "claim.evidence_maturity",
                "the exact polynomial replay supports structural checking only, not empirical or replication maturity",
                witness={
                    "required": "structurally_checked",
                    "declared": claim.get("evidence_maturity"),
                },
            )
        )
    if claim.get("deployment_status") not in THEOREM_PROFILE_DEPLOYMENT_STATES:
        findings.append(
            Finding(
                Severity.BLOCKED,
                "THEOREM_DEPLOYMENT_OUT_OF_SCOPE",
                "claim.deployment_status",
                "the exact polynomial replay grants no candidate, admitted, or operational deployment authority",
                witness={
                    "allowed": sorted(THEOREM_PROFILE_DEPLOYMENT_STATES),
                    "declared": claim.get("deployment_status"),
                    "deployment_authority": "not_granted",
                },
            )
        )
    return findings


def _verified_evidence_ids(
    raw: dict[str, Any],
    artifact_root: Path | None,
    audit_context: _ManifestAuditContext,
) -> set[str]:
    theorem_contract = _closed_theorem_contract(raw)
    verified: set[str] = set()
    for item in _evidence_records(raw):
        evidence_id = item.get("id")
        if not isinstance(evidence_id, str):
            continue
        if item.get("status") != "verified":
            continue
        theorem_artifact = (
            theorem_contract and item.get("kind") == "exact_certificate"
        )
        max_bytes = MAX_CERTIFICATE_BYTES if theorem_artifact else MAX_ARTIFACT_BYTES
        ok, _, _ = _verify_local_artifact_cached(
            audit_context,
            artifact_root,
            item.get("artifact"),
            item.get("sha256"),
            max_bytes=max_bytes,
            theorem_artifact=theorem_artifact,
        )
        if ok:
            verified.add(evidence_id)
    return verified


def verified_evidence_ids(
    raw: dict[str, Any],
    artifact_root: Path | None,
) -> set[str]:
    """Return artifact-verified identifiers using a fresh, non-injectable audit context."""

    return _verified_evidence_ids(raw, artifact_root, _ManifestAuditContext())


def evidence_index(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in _evidence_records(raw):
        evidence_id = item.get("id")
        if isinstance(evidence_id, str) and evidence_id not in result:
            result[evidence_id] = item
    return result


def _replayed_theorem_evidence(
    raw: dict[str, Any],
    artifact_root: Path | None,
    verified_ids: set[str],
    audit_context: _ManifestAuditContext,
) -> tuple[dict[str, CheckedJudgment], list[Finding]]:
    """Replay only the closed v0.4 exact-Q theorem evidence contract."""

    claim = raw.get("claim")
    if not _closed_theorem_contract(raw):
        return {}, []
    assert isinstance(claim, dict)
    claim_id = claim.get("id")
    formal_statement = claim.get("formal_statement")
    if not isinstance(claim_id, str) or not isinstance(formal_statement, dict):
        return {}, []
    try:
        formal_statement_sha256 = sha256_json(formal_statement)
    except (TypeError, ValueError):
        formal_statement_sha256 = None

    results: dict[str, CheckedJudgment] = {}
    findings: list[Finding] = []
    for index, item in enumerate(_evidence_records(raw)):
        evidence_id = item.get("id")
        claim_bindings = item.get("verifies_claims", [])
        if (
            not isinstance(evidence_id, str)
            or evidence_id not in verified_ids
            or item.get("kind") != "exact_certificate"
            or not isinstance(claim_bindings, list)
            or claim_id not in claim_bindings
        ):
            continue
        path = f"evidence.{index}"
        artifact = item.get("artifact")
        digest = item.get("sha256")
        replay_key = (
            (digest, claim_id, formal_statement_sha256)
            if (
                isinstance(artifact, str)
                and isinstance(digest, str)
                and isinstance(formal_statement_sha256, str)
            )
            else None
        )
        if replay_key is not None and replay_key in audit_context.theorem_replays:
            replay = audit_context.theorem_replays[replay_key]
        else:
            if audit_context.theorem_replays_started >= MAX_THEOREM_REPLAYS_PER_AUDIT:
                findings.append(
                    Finding(
                        Severity.ERROR,
                        "THEOREM_RESOURCE_LIMIT",
                        f"{path}.artifact",
                        "exact theorem replay exceeds the per-audit unique-certificate limit",
                        witness={
                            "evidence_id": evidence_id,
                            "max_unique_certificate_digests": MAX_THEOREM_REPLAYS_PER_AUDIT,
                        },
                    )
                )
                continue
            audit_context.theorem_replays_started += 1
            replay = load_and_replay_theorem_certificate(
                artifact_root,
                artifact,
                expected_sha256=digest,
                expected_claim_id=claim_id,
                expected_formal_statement=formal_statement,
            )
            if replay_key is not None:
                audit_context.theorem_replays[replay_key] = replay
        if not replay.valid or replay.result is None:
            for finding in replay.findings:
                suffix = "" if finding.path == "$" else finding.path.removeprefix("$")
                witness = {
                    "evidence_id": evidence_id,
                    "replay_witness": finding.witness,
                }
                findings.append(
                    Finding(
                        finding.severity,
                        finding.code,
                        f"{path}.artifact{suffix}",
                        finding.message,
                        witness=witness,
                        repair=finding.repair,
                    )
                )
            continue
        if item.get("result") != replay.result:
            findings.append(
                Finding(
                    Severity.ERROR,
                    "THEOREM_EVIDENCE_RESULT_MISMATCH",
                    f"{path}.result",
                    "declared evidence result differs from exact theorem replay",
                    witness={
                        "evidence_id": evidence_id,
                        "declared": item.get("result"),
                        "computed": replay.result,
                        "formal_statement_sha256": replay.formal_statement_sha256,
                    },
                )
            )
            continue
        assert isinstance(digest, str)
        assert isinstance(replay.formal_statement_sha256, str)
        judgment = CheckedJudgment(
            subject_id=claim_id,
            subject_sha256=replay.formal_statement_sha256,
            predicate=THEOREM_GATE_ID,
            scope=THEOREM_AUTHORITY_SCOPE,
            method_id=LANGUAGE,
            evidence_id=evidence_id,
            evidence_sha256=digest,
            authority=THEOREM_AUTHORITY,
            result=replay.result,
        )
        results[evidence_id] = judgment
        for finding in replay.findings:
            suffix = "" if finding.path == "$" else finding.path.removeprefix("$")
            findings.append(
                Finding(
                    finding.severity,
                    finding.code,
                    f"{path}.artifact{suffix}",
                    finding.message,
                    witness={
                        "evidence_id": evidence_id,
                        "judgment": judgment.to_dict(),
                        "replay_witness": finding.witness,
                    },
                    repair=finding.repair,
                )
            )
    return results, findings


def replayed_theorem_evidence(
    raw: dict[str, Any],
    artifact_root: Path | None,
) -> tuple[dict[str, CheckedJudgment], list[Finding]]:
    """Replay theorem evidence in a fresh context that callers cannot pre-populate."""

    audit_context = _ManifestAuditContext()
    verified_ids = _verified_evidence_ids(raw, artifact_root, audit_context)
    return _replayed_theorem_evidence(
        raw,
        artifact_root,
        verified_ids,
        audit_context,
    )


def lint_manifest(
    raw: dict[str, Any],
    artifact_root: Path | None = None,
    *,
    checks_run: list[str] | None = None,
) -> list[Finding]:
    """Lint one manifest in a fresh, non-injectable audit context."""

    return _lint_manifest(
        raw,
        artifact_root,
        checks_run=checks_run,
        audit_context=_ManifestAuditContext(),
    )


def _lint_manifest(
    raw: dict[str, Any],
    artifact_root: Path | None = None,
    *,
    checks_run: list[str] | None = None,
    audit_context: _ManifestAuditContext,
) -> list[Finding]:
    audit_cache = audit_context
    findings: list[Finding] = []
    if checks_run is not None and "claim_manifest_lint" not in checks_run:
        checks_run.append("claim_manifest_lint")
    for field in REQUIRED_TOP:
        if field not in raw:
            findings.append(Finding(Severity.ERROR, "MANIFEST_REQUIRED", field, "required top-level field is missing"))
    if findings:
        return findings

    version = raw.get("manifest_version")
    if version not in SUPPORTED_MANIFEST_VERSIONS:
        findings.append(
            Finding(
                Severity.ERROR,
                "MANIFEST_VERSION_UNSUPPORTED",
                "manifest_version",
                f"supported manifest versions are {sorted(SUPPORTED_MANIFEST_VERSIONS)}",
                witness=version,
            )
        )
    if not isinstance(raw.get("draft"), bool):
        findings.append(Finding(Severity.ERROR, "DRAFT_TYPE", "draft", "draft must be a boolean"))
    elif raw["draft"]:
        findings.append(Finding(Severity.BLOCKED, "DRAFT_MANIFEST", "draft", "draft manifests cannot support promotion"))
    for field in sorted(OBJECT_TOP):
        if not isinstance(raw.get(field), dict):
            findings.append(Finding(Severity.ERROR, "MANIFEST_OBJECT_TYPE", field, "top-level field must be an object"))
    if any(f.code == "MANIFEST_OBJECT_TYPE" for f in findings):
        return findings

    claim = raw["claim"]
    domain_checks = raw.get("domain_checks", {})
    if not isinstance(domain_checks, dict):
        findings.append(
            Finding(
                Severity.ERROR,
                "DOMAIN_CHECKS_TYPE",
                "domain_checks",
                "domain_checks must be an object when present",
            )
        )
    else:
        for name in sorted(set(domain_checks) - SUPPORTED_DOMAIN_CHECKS):
            findings.append(
                Finding(
                    Severity.ERROR,
                    "DOMAIN_CHECK_UNREGISTERED",
                    f"domain_checks.{name}",
                    "domain check has no registered checker and cannot be silently ignored",
                )
            )
        for name in sorted(set(domain_checks) & SUPPORTED_DOMAIN_CHECKS):
            config = domain_checks[name]
            if not isinstance(config, dict):
                findings.append(
                    Finding(
                        Severity.ERROR,
                        "DOMAIN_CHECK_CONFIG_TYPE",
                        f"domain_checks.{name}",
                        "registered domain check configuration must be an object",
                    )
                )
                continue
            for field_name in sorted(set(config) - DOMAIN_CHECK_FIELDS[name]):
                findings.append(
                    Finding(
                        Severity.ERROR,
                        "DOMAIN_CHECK_FIELD_UNREGISTERED",
                        f"domain_checks.{name}.{field_name}",
                        "domain check field has no registered meaning and cannot be silently ignored",
                    )
                )
            if name == "arithmetic_trace":
                obligations = config.get("certified_obligations")
                if isinstance(obligations, list) and all(
                    isinstance(obligation, str) for obligation in obligations
                ):
                    for index, obligation in enumerate(obligations):
                        if obligation not in TRACE_REQUIRED_OBLIGATIONS:
                            findings.append(
                                Finding(
                                    Severity.ERROR,
                                    "DOMAIN_CHECK_VALUE_UNREGISTERED",
                                    f"domain_checks.arithmetic_trace.certified_obligations.{index}",
                                    "certified obligation has no registered replay predicate",
                                    witness=obligation,
                                )
                            )
                bindings = config.get("obligation_evidence")
                if isinstance(bindings, dict):
                    for obligation in sorted(
                        set(bindings) - TRACE_REQUIRED_OBLIGATIONS
                    ):
                        findings.append(
                            Finding(
                                Severity.ERROR,
                                "DOMAIN_CHECK_FIELD_UNREGISTERED",
                                f"domain_checks.arithmetic_trace.obligation_evidence.{obligation}",
                                "arithmetic-trace obligation has no registered replay predicate",
                            )
                        )
                    for obligation, identifiers in sorted(bindings.items()):
                        if not isinstance(identifiers, list) or not all(
                            isinstance(identifier, str)
                            for identifier in identifiers
                        ):
                            findings.append(
                                Finding(
                                    Severity.ERROR,
                                    "DOMAIN_CHECK_FIELD_TYPE",
                                    f"domain_checks.arithmetic_trace.obligation_evidence.{obligation}",
                                    "obligation evidence must be a list of evidence identifiers",
                                )
                            )
        if (
            "arithmetic_trace" in domain_checks
            and claim.get("family") != "arithmetic_trace"
        ):
            findings.append(
                Finding(
                    Severity.ERROR,
                    "DOMAIN_CHECK_NOT_APPLICABLE",
                    "domain_checks.arithmetic_trace",
                    "arithmetic_trace is configured for a claim outside the arithmetic_trace family",
                )
            )
    theorem_contract = _closed_theorem_contract(raw)
    if "epistemic_status" in claim:
        findings.append(
            Finding(
                Severity.ERROR,
                "EPISTEMIC_STATUS_PROHIBITED",
                "claim.epistemic_status",
                "epistemic_status is not part of manifest 0.3.0; use evidence_maturity",
            )
        )
    _required_string(findings, claim, "id", "claim", minimum=3)
    _required_string(findings, claim, "title", "claim", minimum=3)
    _required_string(findings, claim, "statement", "claim", minimum=12)
    _required_string(findings, claim, "scope", "claim", minimum=3)
    if isinstance(claim.get("id"), str) and not ID_PATTERN.fullmatch(claim["id"]):
        findings.append(Finding(Severity.ERROR, "CLAIM_ID_FORMAT", "claim.id", "claim identifier contains unsupported characters"))
    if claim.get("deployment_status") not in DEPLOYMENT_STATES:
        findings.append(Finding(Severity.ERROR, "DEPLOYMENT_STATUS", "claim.deployment_status", f"status must be one of {sorted(DEPLOYMENT_STATES)}"))
    if claim.get("type") not in CLAIM_TYPES:
        findings.append(Finding(Severity.ERROR, "CLAIM_TYPE", "claim.type", f"type must be one of {sorted(CLAIM_TYPES)}"))
    maturity = claim.get("evidence_maturity")
    if maturity not in EVIDENCE_MATURITY:
        findings.append(Finding(Severity.ERROR, "EVIDENCE_MATURITY", "claim.evidence_maturity", f"maturity must be one of {sorted(EVIDENCE_MATURITY)}"))
    if theorem_contract:
        findings.extend(_closed_theorem_profile_findings(claim))

    system = raw["system"]
    _required_string(findings, system, "domain", "system")
    _required_string(findings, system, "state_type", "system")
    observation = raw["observation"]
    _required_string(findings, observation, "kernel_or_instrument", "observation")
    if not isinstance(observation.get("legal_filtration"), dict):
        findings.append(Finding(Severity.ERROR, "LEGAL_FILTRATION_TYPE", "observation.legal_filtration", "legal filtration must be an object"))
    target = raw["target"]
    for field in ("outcome", "horizon", "loss_or_score"):
        _required_string(findings, target, field, "target")
    experiment = raw["experiment"]
    _required_string(findings, experiment, "baseline_model", "experiment")
    _required_string(findings, experiment, "search_budget", "experiment")

    admission = raw["admission"]
    hard_gates = admission.get("hard_gates")
    if not isinstance(hard_gates, list) or not hard_gates or not all(isinstance(item, str) and ID_PATTERN.fullmatch(item) for item in hard_gates):
        findings.append(Finding(Severity.ERROR, "HARD_GATES_TYPE", "admission.hard_gates", "hard gates must be a nonempty list of identifiers"))
        hard_gates = []
    elif len(hard_gates) != len(set(hard_gates)):
        findings.append(Finding(Severity.ERROR, "HARD_GATES_DUPLICATE", "admission.hard_gates", "hard gate identifiers must be unique"))
    if not isinstance(admission.get("gate_results"), list):
        findings.append(Finding(Severity.ERROR, "GATE_RESULTS_TYPE", "admission.gate_results", "gate results must be a list"))

    demotion = raw["demotion"]
    _required_string(findings, demotion, "owner", "demotion")
    if not isinstance(demotion.get("rules"), list) or not demotion.get("rules"):
        findings.append(Finding(Severity.ERROR, "DEMOTION_RULES_MISSING", "demotion.rules", "a promoted claim must have a way to lose"))
    _required_string(findings, demotion, "negative_result_destination", "demotion")

    representation = raw["representation"]
    _required_string(findings, representation, "kind", "representation")
    if representation.get("kind") == "exact_quotient" and not isinstance(representation.get("equivalence_test"), str):
        findings.append(Finding(Severity.ERROR, "QUOTIENT_TEST_MISSING", "representation.equivalence_test", "exact quotient requires an equivalence test"))

    preservation = raw["preservation"]
    known_failures = preservation.get("known_failures")
    if not isinstance(known_failures, list) or not known_failures:
        findings.append(Finding(Severity.WARNING, "KNOWN_FAILURES_EMPTY", "preservation.known_failures", "no known failure case is recorded"))
    for role in ("source", "code"):
        hash_field = f"{role}_hash"
        artifact_field = f"{role}_artifact"
        digest = preservation.get(hash_field)
        artifact = preservation.get(artifact_field)
        if digest is None and artifact is None:
            continue
        if not is_sha256(digest):
            findings.append(Finding(Severity.ERROR, "HASH_FORMAT", f"preservation.{hash_field}", "expected lowercase sha256:<64 hex>"))
            continue
        if is_placeholder_sha256(digest):
            findings.append(Finding(Severity.ERROR, "HASH_PLACEHOLDER", f"preservation.{hash_field}", "all-zero hashes are placeholders, not provenance"))
            continue
        ok, reason, actual = _verify_local_artifact_cached(
            audit_cache,
            artifact_root,
            artifact,
            digest,
        )
        if not ok:
            severity = Severity.ERROR if reason in {"invalid_hash", "placeholder_hash", "unsafe_path"} else Severity.BLOCKED
            findings.append(
                Finding(
                    severity,
                    "PRESERVATION_ARTIFACT_UNVERIFIED",
                    f"preservation.{artifact_field}",
                    "declared preservation hash was not verified against a local artifact",
                    witness={"reason": reason, "actual_hash": actual} if actual else {"reason": reason},
                )
            )

    if checks_run is not None and "local_artifact_hashes" not in checks_run:
        checks_run.append("local_artifact_hashes")
    evidence = raw.get("evidence", [])
    if not isinstance(evidence, list):
        findings.append(Finding(Severity.ERROR, "EVIDENCE_TYPE", "evidence", "evidence must be a list"))
        evidence = []
    seen_ids: set[str] = set()
    verified_ids: set[str] = set()
    hash_bound_proof_ids: set[str] = set()
    empirical_kinds = {"dataset", "statistical_certificate", "experimental_record", "independent_replication"}
    for index, item in enumerate(evidence):
        path = f"evidence.{index}"
        if not isinstance(item, dict):
            findings.append(Finding(Severity.ERROR, "EVIDENCE_RECORD_TYPE", path, "evidence record must be an object"))
            continue
        evidence_id = item.get("id")
        if not isinstance(evidence_id, str) or not ID_PATTERN.fullmatch(evidence_id) or evidence_id in seen_ids:
            findings.append(Finding(Severity.ERROR, "EVIDENCE_ID", f"{path}.id", "evidence identifiers must be valid and unique"))
            continue
        seen_ids.add(evidence_id)
        kind = item.get("kind")
        status = item.get("status")
        result = item.get("result")
        if kind not in EVIDENCE_KINDS:
            findings.append(Finding(Severity.ERROR, "EVIDENCE_KIND", f"{path}.kind", f"kind must be one of {sorted(EVIDENCE_KINDS)}"))
        if status not in EVIDENCE_STATUS:
            findings.append(Finding(Severity.ERROR, "EVIDENCE_STATUS", f"{path}.status", f"status must be one of {sorted(EVIDENCE_STATUS)}"))
            continue
        if result not in EVIDENCE_RESULTS:
            findings.append(Finding(Severity.ERROR, "EVIDENCE_RESULT", f"{path}.result", f"result must be one of {sorted(EVIDENCE_RESULTS)}"))
        bindings = item.get("verifies_gates")
        if not isinstance(bindings, list) or not all(isinstance(value, str) for value in bindings):
            findings.append(Finding(Severity.ERROR, "EVIDENCE_GATE_BINDING_TYPE", f"{path}.verifies_gates", "gate bindings must be a list of identifiers"))
        elif any(value not in set(hard_gates) for value in bindings):
            findings.append(Finding(Severity.ERROR, "EVIDENCE_GATE_UNDECLARED", f"{path}.verifies_gates", "evidence binds to an undeclared hard gate"))
        claim_bindings = item.get("verifies_claims", [])
        if not isinstance(claim_bindings, list) or not all(isinstance(value, str) and ID_PATTERN.fullmatch(value) for value in claim_bindings):
            findings.append(Finding(Severity.ERROR, "EVIDENCE_CLAIM_BINDING_TYPE", f"{path}.verifies_claims", "claim bindings must be a list of identifiers"))
            claim_bindings = []
        elif any(value != claim.get("id") for value in claim_bindings):
            findings.append(Finding(Severity.ERROR, "EVIDENCE_CLAIM_UNDECLARED", f"{path}.verifies_claims", "evidence binds to a claim other than the manifest claim"))

        has_artifact = "artifact" in item
        has_hash = "sha256" in item
        artifact_pair_valid = has_artifact and has_hash
        if has_artifact != has_hash:
            artifact_pair_valid = False
            findings.append(
                Finding(
                    Severity.ERROR,
                    "EVIDENCE_ARTIFACT_PAIR",
                    path,
                    "artifact and sha256 must be declared together",
                )
            )
        if has_hash and not is_sha256(item.get("sha256")):
            artifact_pair_valid = False
            findings.append(Finding(Severity.ERROR, "HASH_FORMAT", f"{path}.sha256", "expected lowercase sha256:<64 hex>"))
        elif has_hash and is_placeholder_sha256(item.get("sha256")):
            artifact_pair_valid = False
            findings.append(Finding(Severity.ERROR, "HASH_PLACEHOLDER", f"{path}.sha256", "all-zero hashes are placeholders, not provenance"))

        if status == "verified":
            if not artifact_pair_valid:
                ok, reason, actual = False, "artifact_hash_pair_invalid", None
            else:
                theorem_artifact = theorem_contract and kind == "exact_certificate"
                max_bytes = (
                    MAX_CERTIFICATE_BYTES
                    if theorem_artifact
                    else MAX_ARTIFACT_BYTES
                )
                ok, reason, actual = _verify_local_artifact_cached(
                    audit_cache,
                    artifact_root,
                    item.get("artifact"),
                    item.get("sha256"),
                    max_bytes=max_bytes,
                    theorem_artifact=theorem_artifact,
                )
            if ok:
                verified_ids.add(evidence_id)
                if kind in PROOF_KINDS and result == "pass" and claim.get("id") in claim_bindings:
                    hash_bound_proof_ids.add(evidence_id)
            else:
                theorem_resource_limit = reason == "theorem_artifact_limit"
                severity = (
                    Severity.ERROR
                    if theorem_resource_limit
                    or reason in {"invalid_hash", "placeholder_hash", "unsafe_path"}
                    else Severity.BLOCKED
                )
                findings.append(
                    Finding(
                        severity,
                        (
                            "THEOREM_RESOURCE_LIMIT"
                            if theorem_resource_limit
                            else "EVIDENCE_ARTIFACT_UNVERIFIED"
                        ),
                        path,
                        (
                            "closed theorem evidence exceeds the per-audit unique-artifact limit"
                            if theorem_resource_limit
                            else "verified evidence requires a matching local artifact hash"
                        ),
                        witness=(
                            {
                                "id": evidence_id,
                                "reason": reason,
                                "max_unique_artifacts": MAX_THEOREM_ARTIFACTS_PER_AUDIT,
                            }
                            if theorem_resource_limit
                            else (
                                {"id": evidence_id, "reason": reason, "actual_hash": actual}
                                if actual
                                else {"id": evidence_id, "reason": reason}
                            )
                        ),
                    )
                )

    replay_results, replay_findings = _replayed_theorem_evidence(
        raw,
        artifact_root,
        verified_ids,
        audit_context,
    )
    findings.extend(replay_findings)
    if checks_run is not None and "semantic_theorem_replay" not in checks_run:
        checks_run.append("semantic_theorem_replay")

    claim_subject_sha256 = _semantic_hash_or_none(claim.get("formal_statement"))
    evidence_by_id = evidence_index(raw)
    semantic_pass_ids = {
        evidence_id
        for evidence_id, judgment in replay_results.items()
        if (
            isinstance(claim.get("id"), str)
            and isinstance(claim_subject_sha256, str)
            and judgment.supports(
                subject_id=claim["id"],
                subject_sha256=claim_subject_sha256,
                predicate=THEOREM_GATE_ID,
                scope=THEOREM_AUTHORITY_SCOPE,
                method_id=LANGUAGE,
                evidence_id=evidence_id,
                evidence_sha256=evidence_by_id[evidence_id]["sha256"],
                authority=THEOREM_AUTHORITY,
                result="pass",
            )
        )
    }
    semantic_empirical_pass_ids = {
        evidence_id
        for evidence_id in semantic_pass_ids
        if evidence_by_id.get(evidence_id, {}).get("kind") in empirical_kinds
    }
    semantic_replication_pass_ids = {
        evidence_id
        for evidence_id in semantic_pass_ids
        if evidence_by_id.get(evidence_id, {}).get("kind")
        == "independent_replication"
    }
    if (
        maturity
        in {"structurally_checked", "empirically_passed", "externally_replicated"}
        and not semantic_pass_ids
    ):
        findings.append(
            Finding(
                Severity.BLOCKED,
                "EVIDENCE_MATURITY_UNSUPPORTED",
                "claim.evidence_maturity",
                "maturity beyond declared requires a passing result recomputed by a registered exact replay; artifact hashes establish provenance only",
                witness={
                    "verified_artifact_evidence": sorted(verified_ids),
                    "registered_semantic_passes": sorted(semantic_pass_ids),
                },
            )
        )
    if (
        maturity in {"empirically_passed", "externally_replicated"}
        and not semantic_empirical_pass_ids
    ):
        findings.append(
            Finding(
                Severity.BLOCKED,
                "EMPIRICAL_EVIDENCE_MISSING",
                "claim.evidence_maturity",
                "empirical maturity requires a passing result from a registered empirical replay; declared results and matching hashes are nonsemantic",
                witness={
                    "registered_empirical_passes": sorted(
                        semantic_empirical_pass_ids
                    )
                },
            )
        )
    if maturity == "externally_replicated" and not semantic_replication_pass_ids:
        findings.append(
            Finding(
                Severity.BLOCKED,
                "REPLICATION_EVIDENCE_MISSING",
                "evidence",
                "external replication maturity requires a passing result from a registered independent-replication replay",
                witness={
                    "registered_replication_passes": sorted(
                        semantic_replication_pass_ids
                    )
                },
            )
        )
    if claim.get("type") in {"theorem", "theorem_schema"} and not replay_results:
        findings.append(
            Finding(
                Severity.BLOCKED,
                "THEOREM_CERTIFICATE_MISSING",
                "evidence",
                "no admissible semantic theorem replay is bound to this claim; matching local proof bytes alone do not establish proof validity",
                witness={"hash_bound_proof_evidence": sorted(hash_bound_proof_ids)},
                repair=f"use manifest 0.4.0 with a claim-bound {LANGUAGE} exact certificate, or leave the theorem blocked",
            )
        )

    if not any(f.severity in {Severity.ERROR, Severity.BLOCKED, Severity.DEMOTION} for f in findings):
        findings.append(Finding(Severity.INFO, "MANIFEST_STRUCTURALLY_VALID", "$", "manifest structure and declared local artifact bindings are valid; scientific truth has not been inferred"))
    return findings
