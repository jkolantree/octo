from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .findings import Finding, Severity
from .provenance import (
    is_placeholder_sha256,
    is_sha256,
    verify_local_artifact,
)


SUPPORTED_MANIFEST_VERSIONS = {"0.3.0"}
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


def verified_evidence_ids(raw: dict[str, Any], artifact_root: Path | None) -> set[str]:
    verified: set[str] = set()
    for item in _evidence_records(raw):
        evidence_id = item.get("id")
        if not isinstance(evidence_id, str):
            continue
        if item.get("status") != "verified":
            continue
        ok, _, _ = verify_local_artifact(artifact_root, item.get("artifact"), item.get("sha256"))
        if ok:
            verified.add(evidence_id)
    return verified


def evidence_index(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in _evidence_records(raw):
        evidence_id = item.get("id")
        if isinstance(evidence_id, str) and evidence_id not in result:
            result[evidence_id] = item
    return result


def lint_manifest(
    raw: dict[str, Any],
    artifact_root: Path | None = None,
    *,
    checks_run: list[str] | None = None,
) -> list[Finding]:
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
        ok, reason, actual = verify_local_artifact(artifact_root, artifact, digest)
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
    independently_replicated_ids: set[str] = set()
    proof_ids: set[str] = set()
    verified_pass_ids: set[str] = set()
    empirical_pass_ids: set[str] = set()
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
                ok, reason, actual = verify_local_artifact(artifact_root, item.get("artifact"), item.get("sha256"))
            if ok:
                verified_ids.add(evidence_id)
                if result == "pass":
                    verified_pass_ids.add(evidence_id)
                if kind in PROOF_KINDS and result == "pass" and claim.get("id") in claim_bindings:
                    proof_ids.add(evidence_id)
                if kind in empirical_kinds and result == "pass":
                    empirical_pass_ids.add(evidence_id)
                if kind == "independent_replication" and result == "pass":
                    independently_replicated_ids.add(evidence_id)
            else:
                severity = Severity.ERROR if reason in {"invalid_hash", "placeholder_hash", "unsafe_path"} else Severity.BLOCKED
                findings.append(
                    Finding(
                        severity,
                        "EVIDENCE_ARTIFACT_UNVERIFIED",
                        path,
                        "verified evidence requires a matching local artifact hash",
                        witness={"id": evidence_id, "reason": reason, "actual_hash": actual} if actual else {"id": evidence_id, "reason": reason},
                    )
                )

    if maturity in {"structurally_checked", "empirically_passed", "externally_replicated"} and not verified_pass_ids:
        findings.append(Finding(Severity.BLOCKED, "EVIDENCE_MATURITY_UNSUPPORTED", "claim.evidence_maturity", "artifact-backed maturity requires at least one locally verified passing artifact"))
    if maturity in {"empirically_passed", "externally_replicated"} and not empirical_pass_ids:
        findings.append(Finding(Severity.BLOCKED, "EMPIRICAL_EVIDENCE_MISSING", "claim.evidence_maturity", "empirical maturity requires verified passing data, statistical, experimental, or replication evidence"))
    if maturity == "externally_replicated" and not independently_replicated_ids:
        findings.append(Finding(Severity.BLOCKED, "REPLICATION_EVIDENCE_MISSING", "evidence", "independent maturity requires a verified independent-replication artifact"))
    if claim.get("type") in {"theorem", "theorem_schema"} and not proof_ids:
        findings.append(Finding(Severity.BLOCKED, "THEOREM_CERTIFICATE_MISSING", "evidence", "a theorem requires a locally verified passing proof or exact certificate bound to this claim"))

    if not any(f.severity in {Severity.ERROR, Severity.BLOCKED, Severity.DEMOTION} for f in findings):
        findings.append(Finding(Severity.INFO, "MANIFEST_STRUCTURALLY_VALID", "$", "manifest structure and declared local artifact bindings are valid; scientific truth has not been inferred"))
    return findings
