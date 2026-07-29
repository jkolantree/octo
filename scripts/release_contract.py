"""Closed semantic contract for exact tagged release artifacts and judgments."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping


RECEIPT_VERSION = "bsc-release-verification-receipt/v1"
RECEIPT_SCOPE = "local_release_assembly_observations_only"
RECEIPT_AUTHORITY = "bsc_release_builder_local_execution"
SHA256_ID = re.compile(r"sha256:[0-9a-f]{64}")
HEX64 = re.compile(r"[0-9a-f]{64}")
PORTABLE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*")

STAGE_CONTRACTS: tuple[tuple[str, str, str], ...] = (
    (
        "exact-release-identity",
        "git-exact-tag-and-clean-tree-v1",
        "candidate_git_identity",
    ),
    ("toolchain-binding", "toolchain-lock-replay-v1", "toolchain_identity"),
    (
        "candidate-profile",
        "scripts/verify.py:candidate",
        "verification_harness_execution",
    ),
    ("distribution-build", "scripts/build_dist.py", "artifact_construction"),
    (
        "reproducible-distributions",
        "sha256-byte-comparison-v1",
        "artifact_reproducibility",
    ),
    (
        "tracked-source-archive",
        "git-object-source-archive-v1",
        "artifact_source_identity",
    ),
    (
        "conformance-bundle",
        "bsc-conformance-runner-v1",
        "conformance_artifact_construction",
    ),
    (
        "publication-assets",
        "scripts/build_publication_assets.py",
        "publication_artifact_construction",
    ),
    (
        "custom-gpt-package",
        "scripts/build_gpt_package.py",
        "custom_gpt_package_construction",
    ),
    (
        "software-bill-of-materials",
        "spdx-builder-v1",
        "software_bill_of_materials_construction",
    ),
    (
        "tracked-tree-recheck",
        "git-worktree-source-recheck-v1",
        "post_gate_source_identity",
    ),
    (
        "artifact-payload-privacy",
        "scripts/check_privacy.py:artifacts",
        "artifact_payload_privacy_scan",
    ),
)
STAGE_METHOD_BY_ID = {
    stage_id: method_id for stage_id, method_id, _ in STAGE_CONTRACTS
}
STAGE_SCOPE_BY_ID = {
    stage_id: scope for stage_id, _, scope in STAGE_CONTRACTS
}
STAGE_IDS = tuple(stage_id for stage_id, _, _ in STAGE_CONTRACTS)

STATIC_ARTIFACT_NAMES: Mapping[str, str] = {
    "orientation_text": "START_HERE.txt",
    "copy_paste_protocol": "BSC_AUDIT_COPY_PASTE.txt",
    "upload_protocol": "BSC_AUDIT_UPLOAD_TO_LLM.txt",
    "system_prompt_protocol": "BSC_AUDIT_SYSTEM_PROMPT.txt",
    "canonical_protocol": "BSC_AUDIT_LLM_PACKET.md",
    "claim_manifest_schema": "BSC_AUDIT_SCHEMA.json",
    "worked_examples": "BSC_AUDIT_EXAMPLES.zip",
    "publication_metadata": "BSC_AUDIT_PUBLICATION.json",
    "software_bill_of_materials": "SBOM.spdx.json",
}

REQUIRED_ARTIFACT_ROLES = frozenset(
    {
        "python_wheel",
        "python_sdist",
        "tracked_source_archive",
        "conformance_bundle",
        "custom_gpt_package",
        *STATIC_ARTIFACT_NAMES,
    }
)

STAGE_EVIDENCE_FIELDS: Mapping[str, frozenset[str]] = {
    "exact-release-identity": frozenset(
        {"commit", "tree", "tag", "worktree_status"}
    ),
    "toolchain-binding": frozenset(
        {
            "python",
            "node",
            "setuptools",
            "source_date_epoch",
            "toolchain_lock_sha256",
        }
    ),
    "candidate-profile": frozenset({"profile", "exit_code"}),
    "distribution-build": frozenset({"exit_code", "artifacts"}),
    "reproducible-distributions": frozenset({"comparison", "artifacts"}),
    "tracked-source-archive": frozenset(
        {"name", "sha256", "tracked_entries"}
    ),
    "conformance-bundle": frozenset({"name", "sha256"}),
    "publication-assets": frozenset({"artifacts"}),
    "custom-gpt-package": frozenset({"name", "sha256"}),
    "software-bill-of-materials": frozenset(
        {"name", "sha256", "wheel_sha256"}
    ),
    "tracked-tree-recheck": frozenset(
        {"commit", "tree", "expected_source_entries", "tracked_source_state"}
    ),
    "artifact-payload-privacy": frozenset(
        {"exit_code", "scan_scope", "artifacts"}
    ),
}


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_identity(value: object) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def release_subject(commit: str, tree: str, tag: str) -> dict[str, str]:
    return {"commit": commit, "tree": tree, "tag": tag}


def stage_judgment(
    stage_id: str,
    *,
    subject: Mapping[str, str],
    evidence: Mapping[str, object],
) -> dict[str, object]:
    try:
        method_id = STAGE_METHOD_BY_ID[stage_id]
    except KeyError as exc:
        raise ValueError(f"unknown release verification stage: {stage_id}") from exc
    evidence_record = dict(evidence)
    return {
        "stage_id": stage_id,
        "subject": dict(subject),
        "predicate": f"release:{stage_id}",
        "scope": STAGE_SCOPE_BY_ID[stage_id],
        "method_id": method_id,
        "evidence": evidence_record,
        "evidence_record_sha256": sha256_identity(evidence_record),
        "authority": RECEIPT_AUTHORITY,
        "result": "pass",
    }


def verification_receipt(
    subject: Mapping[str, str],
    judgments: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "receipt_version": RECEIPT_VERSION,
        "subject": dict(subject),
        "scope": RECEIPT_SCOPE,
        "authority": RECEIPT_AUTHORITY,
        "judgments": judgments,
    }


def _artifact_references(
    value: object,
    *,
    label: str,
    failures: list[str],
) -> list[dict[str, str]]:
    if not isinstance(value, list):
        failures.append(f"{label} must be an array")
        return []
    references: list[dict[str, str]] = []
    names: set[str] = set()
    for index, item in enumerate(value):
        item_label = f"{label} artifact {index}"
        if not isinstance(item, dict) or set(item) != {"name", "sha256"}:
            failures.append(f"{item_label} must contain exactly name and sha256")
            continue
        name = item.get("name")
        digest = item.get("sha256")
        if (
            not isinstance(name, str)
            or PORTABLE_NAME.fullmatch(name) is None
            or name in names
        ):
            failures.append(f"{item_label} name is invalid or duplicated")
            continue
        if not isinstance(digest, str) or HEX64.fullmatch(digest) is None:
            failures.append(f"{item_label} sha256 is invalid")
            continue
        names.add(name)
        references.append({"name": name, "sha256": digest})
    if references != sorted(references, key=lambda item: item["name"].encode("utf-8")):
        failures.append(f"{label} must be sorted by artifact name")
    return references


def validate_verification_receipt(
    value: object,
    *,
    expected_subject: Mapping[str, str],
    expected_toolchain_evidence: Mapping[str, object],
    expected_artifacts: list[dict[str, object]] | None = None,
) -> list[str]:
    failures: list[str] = []
    if not isinstance(value, dict):
        return ["verification receipt must be an object"]
    if set(value) != {
        "receipt_version",
        "subject",
        "scope",
        "authority",
        "judgments",
    }:
        failures.append("verification receipt has unknown or missing top-level fields")
    if value.get("receipt_version") != RECEIPT_VERSION:
        failures.append("verification receipt version is unsupported")
    if value.get("subject") != dict(expected_subject):
        failures.append("verification receipt subject differs from the release candidate")
    if value.get("scope") != RECEIPT_SCOPE:
        failures.append("verification receipt scope is unsupported")
    if value.get("authority") != RECEIPT_AUTHORITY:
        failures.append("verification receipt authority is unsupported")

    judgments = value.get("judgments")
    if not isinstance(judgments, list):
        return failures + ["verification receipt judgments must be an array"]
    observed_ids = [
        item.get("stage_id") if isinstance(item, dict) else None
        for item in judgments
    ]
    if tuple(observed_ids) != STAGE_IDS:
        failures.append(
            "verification receipt stage order or roster differs: "
            f"expected={list(STAGE_IDS)!r}, found={observed_ids!r}"
        )
    if len(observed_ids) != len(set(observed_ids)):
        failures.append("verification receipt contains duplicate stage identifiers")

    expected_keys = {
        "stage_id",
        "subject",
        "predicate",
        "scope",
        "method_id",
        "evidence",
        "evidence_record_sha256",
        "authority",
        "result",
    }
    evidence_by_stage: dict[str, dict[str, object]] = {}
    for index, item in enumerate(judgments):
        label = f"verification judgment {index}"
        if not isinstance(item, dict):
            failures.append(f"{label} must be an object")
            continue
        if set(item) != expected_keys:
            failures.append(f"{label} has unknown or missing fields")
            continue
        stage_id = item.get("stage_id")
        if stage_id not in STAGE_METHOD_BY_ID:
            failures.append(f"{label} stage_id is unknown")
            continue
        if item.get("subject") != dict(expected_subject):
            failures.append(f"{label} subject differs from the release candidate")
        if item.get("predicate") != f"release:{stage_id}":
            failures.append(f"{label} predicate does not match its stage")
        if item.get("scope") != STAGE_SCOPE_BY_ID[stage_id]:
            failures.append(f"{label} scope is unsupported for its stage")
        if item.get("method_id") != STAGE_METHOD_BY_ID[stage_id]:
            failures.append(f"{label} method_id is unsupported for its stage")
        if item.get("authority") != RECEIPT_AUTHORITY:
            failures.append(f"{label} authority is unsupported")
        if item.get("result") != "pass":
            failures.append(f"{label} is not a passing judgment")
        evidence = item.get("evidence")
        if not isinstance(evidence, dict) or not evidence:
            failures.append(f"{label} evidence must be a nonempty object")
        else:
            evidence_by_stage[stage_id] = evidence
            expected_fields = STAGE_EVIDENCE_FIELDS[stage_id]
            if set(evidence) != expected_fields:
                failures.append(
                    f"{label} evidence has unknown or missing fields"
                )
            if "exit_code" in evidence and evidence.get("exit_code") != 0:
                failures.append(f"{label} did not record exit code zero")
            if "artifacts" in evidence:
                _artifact_references(
                    evidence.get("artifacts"),
                    label=f"{label} evidence artifacts",
                    failures=failures,
                )
            if stage_id == "exact-release-identity" and evidence != {
                **dict(expected_subject),
                "worktree_status": "clean",
            }:
                failures.append(
                    f"{label} evidence differs from the exact release identity"
                )
            if stage_id == "candidate-profile" and evidence.get("profile") != "candidate":
                failures.append(f"{label} profile is not the candidate profile")
            if (
                stage_id == "toolchain-binding"
                and evidence != dict(expected_toolchain_evidence)
            ):
                failures.append(
                    f"{label} evidence differs from the authoritative toolchain lock"
                )
            if (
                stage_id == "reproducible-distributions"
                and evidence.get("comparison") != "exact_filename_sha256_map"
            ):
                failures.append(
                    f"{label} comparison is not the exact artifact map"
                )
            if stage_id == "tracked-tree-recheck":
                if (
                    evidence.get("commit") != expected_subject.get("commit")
                    or evidence.get("tree") != expected_subject.get("tree")
                    or evidence.get("tracked_source_state") != "unchanged"
                ):
                    failures.append(
                        f"{label} evidence differs from the rechecked source identity"
                    )
            if (
                stage_id == "artifact-payload-privacy"
                and evidence.get("scan_scope")
                != "role_artifact_payloads_before_manifest"
            ):
                failures.append(f"{label} privacy scan scope is unsupported")
            for integer_field in (
                "source_date_epoch",
                "tracked_entries",
                "expected_source_entries",
            ):
                if integer_field in evidence and (
                    type(evidence.get(integer_field)) is not int
                    or evidence[integer_field] < 0
                ):
                    failures.append(
                        f"{label} {integer_field} must be a nonnegative integer"
                    )
            for digest_field in (
                "toolchain_lock_sha256",
                "sha256",
                "wheel_sha256",
            ):
                if digest_field in evidence and (
                    not isinstance(evidence.get(digest_field), str)
                    or HEX64.fullmatch(evidence[digest_field]) is None
                ):
                    failures.append(f"{label} {digest_field} is invalid")
            expected_digest = sha256_identity(evidence)
            actual_digest = item.get("evidence_record_sha256")
            if (
                not isinstance(actual_digest, str)
                or SHA256_ID.fullmatch(actual_digest) is None
                or actual_digest != expected_digest
            ):
                failures.append(f"{label} evidence digest does not replay")

    tracked_source = evidence_by_stage.get("tracked-source-archive", {})
    tracked_recheck = evidence_by_stage.get("tracked-tree-recheck", {})
    tracked_entries = tracked_source.get("tracked_entries")
    expected_source_entries = tracked_recheck.get("expected_source_entries")
    if (
        type(tracked_entries) is int
        and type(expected_source_entries) is int
        and (
            tracked_entries <= 0
            or expected_source_entries <= 0
            or tracked_entries != expected_source_entries
        )
    ):
        failures.append(
            "tracked source entry counts must be positive and identical across construction and recheck"
        )

    if expected_artifacts is not None:
        artifacts_by_role: dict[str, dict[str, str]] = {}
        for record in expected_artifacts:
            if not isinstance(record, dict):
                continue
            role = record.get("role")
            name = record.get("name")
            digest = record.get("sha256")
            if (
                isinstance(role, str)
                and role in REQUIRED_ARTIFACT_ROLES
                and isinstance(name, str)
                and isinstance(digest, str)
                and HEX64.fullmatch(digest) is not None
                and role not in artifacts_by_role
            ):
                artifacts_by_role[role] = {"name": name, "sha256": digest}
        if set(artifacts_by_role) == REQUIRED_ARTIFACT_ROLES:
            judgments_by_id = {
                item.get("stage_id"): item
                for item in judgments
                if isinstance(item, dict)
                and isinstance(item.get("stage_id"), str)
            }

            def stage_references(stage_id: str) -> list[dict[str, str]]:
                item = judgments_by_id.get(stage_id)
                evidence = item.get("evidence") if isinstance(item, dict) else None
                if not isinstance(evidence, dict):
                    return []
                if "artifacts" in evidence and isinstance(
                    evidence.get("artifacts"), list
                ):
                    return [
                        dict(reference)
                        for reference in evidence["artifacts"]
                        if isinstance(reference, dict)
                    ]
                if isinstance(evidence.get("name"), str) and isinstance(
                    evidence.get("sha256"), str
                ):
                    return [
                        {
                            "name": evidence["name"],
                            "sha256": evidence["sha256"],
                        }
                    ]
                return []

            publication_roles = set(STATIC_ARTIFACT_NAMES) - {
                "software_bill_of_materials"
            }
            expected_roles_by_stage = {
                "distribution-build": {"python_wheel", "python_sdist"},
                "reproducible-distributions": {
                    "python_wheel",
                    "python_sdist",
                },
                "tracked-source-archive": {"tracked_source_archive"},
                "conformance-bundle": {"conformance_bundle"},
                "publication-assets": publication_roles,
                "custom-gpt-package": {"custom_gpt_package"},
                "software-bill-of-materials": {
                    "software_bill_of_materials"
                },
                "artifact-payload-privacy": set(REQUIRED_ARTIFACT_ROLES),
            }
            for stage_id, roles in expected_roles_by_stage.items():
                expected = sorted(
                    (artifacts_by_role[role] for role in roles),
                    key=lambda item: item["name"].encode("utf-8"),
                )
                if stage_references(stage_id) != expected:
                    failures.append(
                        f"verification judgment {stage_id!r} artifacts "
                        "differ from the semantic release roster"
                    )
            sbom_item = judgments_by_id.get("software-bill-of-materials")
            sbom_evidence = (
                sbom_item.get("evidence")
                if isinstance(sbom_item, dict)
                else None
            )
            if (
                not isinstance(sbom_evidence, dict)
                or sbom_evidence.get("wheel_sha256")
                != artifacts_by_role["python_wheel"]["sha256"]
            ):
                failures.append(
                    "software-bill-of-materials wheel binding differs "
                    "from the release wheel"
                )
        else:
            failures.append(
                "verification receipt cannot bind an incomplete semantic artifact roster"
            )
    return failures


def expected_artifact_names(
    *,
    engine_version: str,
    public_version: str,
) -> dict[str, str]:
    return {
        "python_wheel": (
            f"bsc_audit_engine-{engine_version}-py3-none-any.whl"
        ),
        "python_sdist": f"bsc_audit_engine-{engine_version}.tar.gz",
        "tracked_source_archive": f"bsc-audit-engine-{public_version}.zip",
        "conformance_bundle": f"bsc-audit-conformance-{public_version}.zip",
        "custom_gpt_package": f"BSC_CUSTOM_GPT_PACKAGE_{public_version}.zip",
        **STATIC_ARTIFACT_NAMES,
    }


def role_for_artifact_name(
    name: str,
    *,
    engine_version: str,
    public_version: str,
) -> str | None:
    matches = [
        role
        for role, expected_name in expected_artifact_names(
            engine_version=engine_version,
            public_version=public_version,
        ).items()
        if name == expected_name
    ]
    return matches[0] if len(matches) == 1 else None
