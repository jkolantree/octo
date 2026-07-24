#!/usr/bin/env python3
"""Fail-closed aggregate checker for the frozen 39-case GPT Preview suite."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

try:
    from scripts.check_gpt_eval_bundle import (
        SCIENTIFIC_RESEARCH_PROJECTION_REQUIRED,
        STATUS_ONLY_RESEARCH_PROJECTION_EMPTY,
        check_bundle,
    )
    from scripts.check_gpt_frozen_candidate import (
        EXCLUDED_CYCLE_PATHS,
        MANIFEST_SCHEMA,
        REGISTRY_VERSION,
        registry_entries,
    )
    from scripts.gpt_eval_controller import (
        CANDIDATE_FAILED,
        CANDIDATE_NOT_SCORED,
        CANDIDATE_PASSED,
        CONTROLLER_RECORD_FIELDS,
        CONTROLLER_VALID,
        FROZEN_PROTOCOL_RELATIVE,
        RAW_RESPONSE_FILENAME,
        TRANSPORT_IDENTITY_RESOLVED,
        TRANSPORT_IDENTITY_UNRESOLVED,
        TRANSPORT_NOT_APPLICABLE,
        TRIAL_INVALID_CONTROLLER,
        canonical_json_bytes,
        derive_disposition,
        frozen_trial_bindings,
    )
except ModuleNotFoundError:  # Direct ``python scripts/check_gpt_eval_suite.py``.
    from check_gpt_eval_bundle import (  # type: ignore[no-redef]
        SCIENTIFIC_RESEARCH_PROJECTION_REQUIRED,
        STATUS_ONLY_RESEARCH_PROJECTION_EMPTY,
        check_bundle,
    )
    from check_gpt_frozen_candidate import (  # type: ignore[no-redef]
        EXCLUDED_CYCLE_PATHS,
        MANIFEST_SCHEMA,
        REGISTRY_VERSION,
        registry_entries,
    )
    from gpt_eval_controller import (  # type: ignore[no-redef]
        CANDIDATE_FAILED,
        CANDIDATE_NOT_SCORED,
        CANDIDATE_PASSED,
        CONTROLLER_RECORD_FIELDS,
        CONTROLLER_VALID,
        FROZEN_PROTOCOL_RELATIVE,
        RAW_RESPONSE_FILENAME,
        TRANSPORT_IDENTITY_RESOLVED,
        TRANSPORT_IDENTITY_UNRESOLVED,
        TRANSPORT_NOT_APPLICABLE,
        TRIAL_INVALID_CONTROLLER,
        canonical_json_bytes,
        derive_disposition,
        frozen_trial_bindings,
    )


ROOT = Path(__file__).resolve().parents[1]
LEDGER_FIELDS = {
    "suite_ledger_version",
    "frozen_protocol",
    "overall_status",
    "suites",
}
SUITE_FIELDS = {
    "suite_id",
    "repair_number",
    "restart_of",
    "status",
    "freeze_manifest",
    "candidate_source_root",
    "candidate_identity_sha256",
    "trials",
}
TRIAL_FIELDS = {"trial_id", "case_id", "attempts"}
ATTEMPT_FIELDS = {
    "attempt_id",
    "parent_attempt_id",
    "pre_score_controller",
    "post_score_controller",
    "checker_result",
    "score_result",
    "raw_response",
    "evidence_directory",
    "controller",
    "candidate",
    "transport",
}
FILE_RECORD_FIELDS = {"filename", "bytes", "sha256"}
CHECKER_RESULT_FIELDS = {
    "checker",
    "output_version",
    "evidence_directory",
    "status",
    "outcomes",
    "checks",
    "findings",
    "bindings",
    "score_result",
    "return_desk",
    "limitations",
}
STATUS_ONLY_CASE_IDS = {
    "official-service-status-separation",
    "official-first-reproduction-route",
}
FREEZE_MANIFEST_FIELDS = {
    "excluded_paths",
    "file_count",
    "files",
    "manifest_schema",
    "registry_version",
}
FREEZE_FILE_FIELDS = {"bytes", "category", "path", "sha256"}
SUITE_STATUSES = {"complete_pass", "stopped_candidate_failed"}
OVERALL_STATUSES = {"passed", "repair_pending", "failed_closed"}
TRANSPORT_OUTCOMES = {
    TRANSPORT_IDENTITY_RESOLVED,
    TRANSPORT_IDENTITY_UNRESOLVED,
    TRANSPORT_NOT_APPLICABLE,
}
HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class SuiteLedgerError(ValueError):
    """A stable aggregate-ledger finding."""

    def __init__(self, code: str, path: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.path = path
        self.message = message


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strict_json(data: bytes, label: str) -> Any:
    try:
        return json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_strict_object,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON number: {value}")
            ),
        )
    except (UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise SuiteLedgerError(
            "SUITE_JSON_INVALID",
            label,
            "file must be strict UTF-8 JSON without duplicate keys or non-finite numbers",
        ) from exc


def _portable_relative(value: object) -> bool:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or "\x00" in value
    ):
        return False
    pure = PurePosixPath(value)
    return (
        not pure.is_absolute()
        and ".." not in pure.parts
        and all(part not in {"", "."} for part in pure.parts)
        and pure.as_posix() == value
    )


def _is_link_or_junction(path: Path) -> bool:
    try:
        return path.is_symlink() or (
            hasattr(path, "is_junction") and path.is_junction()
        )
    except OSError:
        return True


def _read_ref(
    root: Path,
    record: object,
    *,
    label: str,
) -> tuple[bytes, Path]:
    if not isinstance(record, dict) or set(record) != FILE_RECORD_FIELDS:
        raise SuiteLedgerError(
            "SUITE_FILE_RECORD_INVALID",
            label,
            "file record fields must be exactly filename, bytes, and sha256",
        )
    filename = record.get("filename")
    if not _portable_relative(filename):
        raise SuiteLedgerError(
            "SUITE_FILE_PATH_UNSAFE",
            label,
            "suite file references must be portable relative paths",
        )
    path = root.joinpath(*PurePosixPath(str(filename)).parts)
    current = root
    try:
        for part in PurePosixPath(str(filename)).parts:
            current = current / part
            if _is_link_or_junction(current):
                raise OSError("symlink")
        resolved_root = root.resolve(strict=True)
        resolved = path.resolve(strict=True)
        resolved.relative_to(resolved_root)
        if not resolved.is_file():
            raise OSError("not file")
        data = resolved.read_bytes()
    except (OSError, RuntimeError, ValueError) as exc:
        raise SuiteLedgerError(
            "SUITE_FILE_MISSING_OR_UNSAFE",
            label,
            "suite-bound file is missing, unsafe, symlinked, or unreadable",
        ) from exc
    size = record.get("bytes")
    digest = record.get("sha256")
    if (
        isinstance(size, bool)
        or not isinstance(size, int)
        or size != len(data)
        or not isinstance(digest, str)
        or not HASH_RE.fullmatch(digest)
        or digest != _sha256(data)
    ):
        raise SuiteLedgerError(
            "SUITE_FILE_BINDING_MISMATCH",
            label,
            "suite file byte count or SHA-256 differs from preserved bytes",
        )
    return data, resolved


def _resolve_relative_directory(root: Path, value: object, *, label: str) -> Path:
    if not _portable_relative(value):
        raise SuiteLedgerError(
            "SUITE_DIRECTORY_PATH_UNSAFE",
            label,
            "suite directory references must be portable relative paths",
        )
    pure = PurePosixPath(str(value))
    current = root
    try:
        for part in pure.parts:
            current = current / part
            if _is_link_or_junction(current):
                raise OSError("symlink")
        resolved_root = root.resolve(strict=True)
        resolved = current.resolve(strict=True)
        resolved.relative_to(resolved_root)
        if not resolved.is_dir():
            raise OSError("not directory")
    except (OSError, RuntimeError, ValueError) as exc:
        raise SuiteLedgerError(
            "SUITE_DIRECTORY_MISSING_OR_UNSAFE",
            label,
            "suite directory is missing, unsafe, symlinked, or unreadable",
        ) from exc
    return resolved


def _read_snapshot_file(root: Path, relative: str, *, label: str) -> bytes:
    if not _portable_relative(relative):
        raise SuiteLedgerError(
            "SUITE_SNAPSHOT_PATH_UNSAFE",
            label,
            "frozen snapshot paths must be portable relative paths",
        )
    pure = PurePosixPath(relative)
    current = root
    try:
        for part in pure.parts:
            current = current / part
            if _is_link_or_junction(current):
                raise OSError("symlink")
        resolved = current.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
        if not resolved.is_file():
            raise OSError("not file")
        return resolved.read_bytes()
    except (OSError, RuntimeError, ValueError) as exc:
        raise SuiteLedgerError(
            "SUITE_SNAPSHOT_FILE_MISSING_OR_UNSAFE",
            label,
            "frozen snapshot file is missing, unsafe, symlinked, or unreadable",
        ) from exc


def _validate_candidate_snapshot(
    *,
    ledger_root: Path,
    suite: dict[str, Any],
    freeze_bytes: bytes,
    protocol_bytes: bytes,
    label: str,
) -> tuple[Path, tuple[tuple[str, int, str], ...]]:
    source_root = _resolve_relative_directory(
        ledger_root,
        suite.get("candidate_source_root"),
        label=f"{label}.candidate_source_root",
    )
    snapshot_freeze = _read_snapshot_file(
        source_root,
        "docs/GPT_FROZEN_CANDIDATE.json",
        label=f"{label}.candidate_source_root/docs/GPT_FROZEN_CANDIDATE.json",
    )
    if snapshot_freeze != freeze_bytes:
        raise SuiteLedgerError(
            "SUITE_SNAPSHOT_FREEZE_MISMATCH",
            f"{label}.candidate_source_root",
            "candidate snapshot contains a different frozen-candidate manifest",
        )
    manifest = _strict_json(freeze_bytes, f"{label}.freeze_manifest")
    if (
        not isinstance(manifest, dict)
        or set(manifest) != FREEZE_MANIFEST_FIELDS
        or manifest.get("manifest_schema") != MANIFEST_SCHEMA
        or manifest.get("registry_version") != REGISTRY_VERSION
    ):
        raise SuiteLedgerError(
            "SUITE_FREEZE_MANIFEST_INVALID",
            f"{label}.freeze_manifest",
            "frozen-candidate manifest schema or fields are invalid",
        )
    rows = manifest.get("files")
    file_count = manifest.get("file_count")
    excluded = manifest.get("excluded_paths")
    expected_registry = registry_entries()
    if (
        not isinstance(rows, list)
        or not rows
        or isinstance(file_count, bool)
        or not isinstance(file_count, int)
        or file_count != len(rows)
        or file_count != len(expected_registry)
        or excluded != list(EXCLUDED_CYCLE_PATHS)
    ):
        raise SuiteLedgerError(
            "SUITE_FREEZE_MANIFEST_INVALID",
            f"{label}.freeze_manifest",
            "frozen-candidate manifest count or cyclic exclusions differ from the closed registry",
        )
    seen_paths: set[str] = set()
    observed_registry: list[tuple[str, str]] = []
    registered_file_bindings: list[tuple[str, int, str]] = []
    for index, row in enumerate(rows):
        row_label = f"{label}.freeze_manifest.files[{index}]"
        if (
            not isinstance(row, dict)
            or set(row) != FREEZE_FILE_FIELDS
            or not isinstance(row.get("category"), str)
            or not row["category"]
            or not _portable_relative(row.get("path"))
            or row["path"] in seen_paths
            or isinstance(row.get("bytes"), bool)
            or not isinstance(row.get("bytes"), int)
            or row["bytes"] < 0
            or not isinstance(row.get("sha256"), str)
            or not HASH_RE.fullmatch(row["sha256"])
        ):
            raise SuiteLedgerError(
                "SUITE_FREEZE_FILE_RECORD_INVALID",
                row_label,
                "frozen-candidate file record is malformed or duplicated",
            )
        seen_paths.add(row["path"])
        observed_registry.append((row["category"], row["path"]))
        data = _read_snapshot_file(source_root, row["path"], label=row_label)
        if len(data) != row["bytes"] or _sha256(data) != row["sha256"]:
            raise SuiteLedgerError(
                "SUITE_SNAPSHOT_FILE_BINDING_MISMATCH",
                row_label,
                "candidate snapshot bytes differ from the frozen manifest",
            )
        registered_file_bindings.append(
            (row["path"], row["bytes"], row["sha256"])
        )
    if tuple(observed_registry) != expected_registry:
        raise SuiteLedgerError(
            "SUITE_FREEZE_MANIFEST_REGISTRY_MISMATCH",
            f"{label}.freeze_manifest.files",
            "manifest category/path order and membership must exactly equal the canonical closed registry",
        )
    snapshot_protocol = _read_snapshot_file(
        source_root,
        FROZEN_PROTOCOL_RELATIVE.as_posix(),
        label=f"{label}.candidate_source_root/{FROZEN_PROTOCOL_RELATIVE.as_posix()}",
    )
    if snapshot_protocol != protocol_bytes:
        raise SuiteLedgerError(
            "SUITE_SNAPSHOT_PROTOCOL_MISMATCH",
            f"{label}.candidate_source_root",
            "candidate snapshot uses a different frozen evaluation protocol",
        )
    return source_root, tuple(registered_file_bindings)


def _validate_evidence_snapshot(
    *,
    ledger_root: Path,
    attempt: dict[str, Any],
    pre_bytes: bytes,
    post_bytes: bytes,
    score_bytes: bytes | None,
    raw_response_bytes: bytes,
    label: str,
) -> Path:
    evidence_root = _resolve_relative_directory(
        ledger_root,
        attempt.get("evidence_directory"),
        label=f"{label}.evidence_directory",
    )
    expected = {
        "controller_record.json": post_bytes,
        RAW_RESPONSE_FILENAME: raw_response_bytes,
    }
    if score_bytes is not None:
        expected["pre_score_controller.json"] = pre_bytes
        expected["score_result.json"] = score_bytes
    for relative, expected_bytes in expected.items():
        actual = _read_snapshot_file(
            evidence_root,
            relative,
            label=f"{label}.evidence_directory/{relative}",
        )
        if actual != expected_bytes:
            raise SuiteLedgerError(
                "SUITE_EVIDENCE_BINDING_MISMATCH",
                f"{label}.evidence_directory/{relative}",
                "evidence snapshot bytes differ from the aggregate file references",
            )
    if score_bytes is None and any(
        (evidence_root / filename).exists()
        for filename in ("pre_score_controller.json", "score_result.json")
    ):
        raise SuiteLedgerError(
            "SUITE_INVALID_EVIDENCE_HAS_SCORE",
            f"{label}.evidence_directory",
            "an invalid-controller evidence snapshot must not contain score artifacts",
        )
    return evidence_root


def _normalized_checker_bytes(document: object) -> bytes:
    if not isinstance(document, dict):
        raise SuiteLedgerError(
            "SUITE_CHECKER_RESULT_INVALID",
            "checker_result",
            "checker result must be a JSON object",
        )
    normalized = copy.deepcopy(document)
    normalized["evidence_directory"] = "<bound-evidence-directory>"
    try:
        return canonical_json_bytes(normalized)
    except (TypeError, ValueError) as exc:
        raise SuiteLedgerError(
            "SUITE_CHECKER_RESULT_INVALID",
            "checker_result",
            "checker result is not canonicalizable strict JSON",
        ) from exc


def _identity_digest(controller: dict[str, Any]) -> str:
    identity = controller.get("candidate_identity")
    if not isinstance(identity, list):
        raise SuiteLedgerError(
            "SUITE_CANDIDATE_IDENTITY_INVALID",
            "candidate_identity",
            "controller record lacks a candidate-identity roster",
        )
    try:
        return _sha256(canonical_json_bytes(identity))
    except (TypeError, ValueError) as exc:
        raise SuiteLedgerError(
            "SUITE_CANDIDATE_IDENTITY_INVALID",
            "candidate_identity",
            "candidate-identity roster is not canonical JSON",
        ) from exc


def _freeze_digest(controller: dict[str, Any]) -> str:
    identity = controller.get("candidate_identity")
    rows = (
        [
            item
            for item in identity
            if isinstance(item, dict)
            and item.get("kind") == "freeze_manifest"
            and item.get("filename") == "GPT_FROZEN_CANDIDATE.json"
        ]
        if isinstance(identity, list)
        else []
    )
    if (
        len(rows) != 1
        or not isinstance(rows[0].get("sha256"), str)
        or not HASH_RE.fullmatch(rows[0]["sha256"])
    ):
        raise SuiteLedgerError(
            "SUITE_FREEZE_IDENTITY_INVALID",
            "candidate_identity",
            "controller must bind exactly one frozen-candidate manifest digest",
        )
    return rows[0]["sha256"]


def _controller_document(data: bytes, label: str) -> dict[str, Any]:
    document = _strict_json(data, label)
    if not isinstance(document, dict) or set(document) != CONTROLLER_RECORD_FIELDS:
        raise SuiteLedgerError(
            "SUITE_CONTROLLER_RECORD_INVALID",
            label,
            "preserved controller record fields differ from the strict contract",
        )
    return document


def _post_score_artifact_digest(
    controller: dict[str, Any],
    filename: str,
) -> str | None:
    rows = controller.get("controller_artifacts")
    matches = (
        [
            item
            for item in rows
            if isinstance(item, dict) and item.get("filename") == filename
        ]
        if isinstance(rows, list)
        else []
    )
    if len(matches) != 1:
        return None
    digest = matches[0].get("sha256")
    return digest if isinstance(digest, str) and HASH_RE.fullmatch(digest) else None


def _validate_score_for_pass(
    score: dict[str, Any],
    *,
    expected_case_id: str,
) -> bool:
    dimensions = score.get("dimension_scores")
    total = score.get("total_score")
    observable = score.get("observable_behavior_results")
    forbidden = score.get("forbidden_behavior_results")
    projection = score.get("observed_research_projection")
    projection_requirement = score.get("research_projection_requirement")
    scientific_projection = (
        projection_requirement == SCIENTIFIC_RESEARCH_PROJECTION_REQUIRED
    )
    status_only_projection = (
        projection_requirement == STATUS_ONLY_RESEARCH_PROJECTION_EMPTY
    )
    expected_projection_requirement = (
        STATUS_ONLY_RESEARCH_PROJECTION_EMPTY
        if expected_case_id in STATUS_ONLY_CASE_IDS
        else SCIENTIFIC_RESEARCH_PROJECTION_REQUIRED
    )
    projection_mode_coherent = (
        projection_requirement == expected_projection_requirement
        and score.get("case_id") == expected_case_id
        and isinstance(projection, dict)
        and all(
            isinstance(claim_id, str)
            and bool(claim_id)
            and isinstance(verdict, str)
            and bool(verdict)
            for claim_id, verdict in projection.items()
        )
        and (
            (
                scientific_projection
                and bool(projection)
                and score.get("research_verdict_allowed") is True
            )
            or (
                status_only_projection
                and projection == {}
                and score.get("research_verdict_allowed") is None
            )
        )
    )
    return bool(
        score.get("score_result_version") == "2.0"
        and isinstance(dimensions, dict)
        and len(dimensions) == 10
        and all(
            not isinstance(value, bool)
            and isinstance(value, int)
            and 0 <= value <= 2
            for value in dimensions.values()
        )
        and not isinstance(total, bool)
        and isinstance(total, int)
        and total == sum(dimensions.values())
        and 18 <= total <= 20
        and score.get("automatic_failure") is False
        and isinstance(observable, dict)
        and bool(observable)
        and all(value is True for value in observable.values())
        and isinstance(forbidden, dict)
        and all(value is False for value in forbidden.values())
        and projection_mode_coherent
        and score.get("research_projection_contract_satisfied") is True
        and score.get("terminal_response_complete") is True
    )


def _validate_attempt(
    *,
    root: Path,
    suite: dict[str, Any],
    trial: dict[str, Any],
    attempt: dict[str, Any],
    attempt_number: int,
    previous_attempt: dict[str, Any] | None,
    expected_trial_id: str,
    expected_case_id: str,
    freeze_digest: str,
    candidate_identity_digest: str,
    candidate_source_root: Path,
    seen_session_references: set[str],
) -> tuple[str, str, str]:
    label = (
        f"$.suites[{suite['suite_id']}].trials[{expected_trial_id}]"
        f".attempts[{attempt_number - 1}]"
    )
    if not isinstance(attempt, dict) or set(attempt) != ATTEMPT_FIELDS:
        raise SuiteLedgerError(
            "SUITE_ATTEMPT_FIELDS_INVALID",
            label,
            "attempt fields differ from the strict aggregate contract",
        )
    expected_attempt_id = f"{expected_trial_id}-A{attempt_number:02d}"
    if attempt.get("attempt_id") != expected_attempt_id:
        raise SuiteLedgerError(
            "SUITE_ATTEMPT_ID_INVALID",
            f"{label}.attempt_id",
            "attempt IDs must be deterministic and sequential within the trial",
        )
    expected_parent = (
        None if previous_attempt is None else previous_attempt.get("attempt_id")
    )
    if attempt.get("parent_attempt_id") != expected_parent:
        raise SuiteLedgerError(
            "SUITE_RETRY_ANCESTRY_INVALID",
            f"{label}.parent_attempt_id",
            "retry must point to the immediately preceding invalid-controller attempt",
        )

    pre_bytes, _ = _read_ref(
        root,
        attempt.get("pre_score_controller"),
        label=f"{label}.pre_score_controller",
    )
    post_bytes, _ = _read_ref(
        root,
        attempt.get("post_score_controller"),
        label=f"{label}.post_score_controller",
    )
    checker_bytes, _ = _read_ref(
        root,
        attempt.get("checker_result"),
        label=f"{label}.checker_result",
    )
    raw_response_bytes, _ = _read_ref(
        root,
        attempt.get("raw_response"),
        label=f"{label}.raw_response",
    )
    pre = _controller_document(pre_bytes, f"{label}.pre_score_controller")
    post = _controller_document(post_bytes, f"{label}.post_score_controller")
    checker = _strict_json(checker_bytes, f"{label}.checker_result")
    if (
        not isinstance(checker, dict)
        or set(checker) != CHECKER_RESULT_FIELDS
        or checker.get("checker") != "gpt_eval_bundle"
        or checker.get("output_version") != "2.0"
        or checker.get("status") not in {"pass", "blocked"}
    ):
        raise SuiteLedgerError(
            "SUITE_CHECKER_RESULT_INVALID",
            f"{label}.checker_result",
            "checker result must be a gpt_eval_bundle output_version 2.0 object",
        )
    conversation = pre.get("fresh_conversation")
    session_reference = (
        conversation.get("session_reference")
        if isinstance(conversation, dict)
        else None
    )
    if (
        not isinstance(session_reference, str)
        or not session_reference
        or session_reference in seen_session_references
    ):
        raise SuiteLedgerError(
            "SUITE_FRESH_CONVERSATION_REUSED",
            label,
            "every counted attempt and invalid retry requires a globally unique Preview conversation",
        )
    seen_session_references.add(session_reference)

    controller_outcome = attempt.get("controller")
    candidate_outcome = attempt.get("candidate")
    transport_outcome = attempt.get("transport")
    if (
        controller_outcome not in {CONTROLLER_VALID, TRIAL_INVALID_CONTROLLER}
        or candidate_outcome
        not in {CANDIDATE_PASSED, CANDIDATE_FAILED, CANDIDATE_NOT_SCORED}
        or transport_outcome not in TRANSPORT_OUTCOMES
        or checker.get("outcomes") != {
            "controller": controller_outcome,
            "candidate": candidate_outcome,
            "transport": transport_outcome,
            "disposition": derive_disposition(
                controller=controller_outcome,
                candidate=candidate_outcome,
                transport=transport_outcome,
            ),
            "scoring_allowed": controller_outcome == CONTROLLER_VALID,
        }
    ):
        raise SuiteLedgerError(
            "SUITE_OUTCOME_MISMATCH",
            label,
            "attempt outcomes differ from the preserved per-trial checker result",
        )
    bindings = checker.get("bindings")
    if (
        not isinstance(bindings, dict)
        or bindings.get("controller_record_sha256") != _sha256(post_bytes)
        or bindings.get("pre_score_controller_sha256")
        != (
            _sha256(pre_bytes)
            if attempt.get("score_result") is not None
            else None
        )
        or bindings.get("candidate_identity_sha256") != candidate_identity_digest
    ):
        raise SuiteLedgerError(
            "SUITE_CHECKER_BINDING_MISMATCH",
            f"{label}.checker_result",
            "checker result does not cryptographically bind the preserved controller records",
        )

    expected_state = "counted" if attempt_number == 1 else "invalid_retry"
    stable_fields = CONTROLLER_RECORD_FIELDS - {"controller_artifacts", "counting_state"}
    if (
        pre.get("trial_id") != expected_trial_id
        or post.get("trial_id") != expected_trial_id
        or pre.get("case_id") != expected_case_id
        or post.get("case_id") != expected_case_id
        or pre.get("counting_state") != expected_state
        or post.get("counting_state") != expected_state
        or any(pre.get(field) != post.get(field) for field in stable_fields)
        or _identity_digest(pre) != candidate_identity_digest
        or _identity_digest(post) != candidate_identity_digest
        or _freeze_digest(pre) != freeze_digest
        or _freeze_digest(post) != freeze_digest
        or not raw_response_bytes
        or pre.get("raw_response", {}).get("filename") != RAW_RESPONSE_FILENAME
        or post.get("raw_response", {}).get("filename") != RAW_RESPONSE_FILENAME
        or pre.get("raw_response", {}).get("sha256") != _sha256(raw_response_bytes)
        or post.get("raw_response", {}).get("sha256") != _sha256(raw_response_bytes)
        or pre.get("raw_response", {}).get("bytes") != len(raw_response_bytes)
        or post.get("raw_response", {}).get("bytes") != len(raw_response_bytes)
    ):
        raise SuiteLedgerError(
            "SUITE_TRIAL_FREEZE_OR_MAPPING_MISMATCH",
            label,
            "attempt mapping, stable controller state, candidate identity, or freeze differs",
        )

    score_ref = attempt.get("score_result")
    score_bytes: bytes | None = None
    if controller_outcome == TRIAL_INVALID_CONTROLLER:
        if (
            candidate_outcome != CANDIDATE_NOT_SCORED
            or score_ref is not None
            or post_bytes != pre_bytes
        ):
            raise SuiteLedgerError(
                "SUITE_INVALID_RETRY_CLASSIFICATION_INVALID",
                label,
                "invalid-controller attempts are unscored and preserve identical pre/post records",
            )
    else:
        if candidate_outcome == CANDIDATE_NOT_SCORED or score_ref is None:
            raise SuiteLedgerError(
                "SUITE_COUNTED_SCORE_MISSING",
                label,
                "controller-valid counted attempts require a preserved score result",
            )
        score_bytes, _ = _read_ref(
            root,
            score_ref,
            label=f"{label}.score_result",
        )
        score = _strict_json(score_bytes, f"{label}.score_result")
        if (
            not isinstance(score, dict)
            or score.get("trial_id") != expected_trial_id
            or score.get("case_id") != expected_case_id
            or score.get("pre_score_controller_sha256") != _sha256(pre_bytes)
            or _post_score_artifact_digest(post, "pre_score_controller.json")
            != _sha256(pre_bytes)
            or _post_score_artifact_digest(post, "score_result.json")
            != _sha256(score_bytes)
            or bindings.get("score_result_sha256") != _sha256(score_bytes)
        ):
            raise SuiteLedgerError(
                "SUITE_PRE_POST_SCORE_LINK_INVALID",
                label,
                "post-score controller and score do not form an exact post->score->pre hash chain",
            )
        if candidate_outcome == CANDIDATE_PASSED and not _validate_score_for_pass(
            score,
            expected_case_id=expected_case_id,
        ):
            raise SuiteLedgerError(
                "SUITE_PASS_SCORE_INVALID",
                label,
                "candidate_passed lacks the frozen 18/20, zero-auto-failure, and oracle closure",
            )

    evidence_root = _validate_evidence_snapshot(
        ledger_root=root,
        attempt=attempt,
        pre_bytes=pre_bytes,
        post_bytes=post_bytes,
        score_bytes=score_bytes,
        raw_response_bytes=raw_response_bytes,
        label=label,
    )
    try:
        recomputed_exit, recomputed_checker = check_bundle(
            evidence_root,
            expected_case_id=expected_case_id,
            candidate_source_root=candidate_source_root,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise SuiteLedgerError(
            "SUITE_CHECKER_RECOMPUTATION_FAILED",
            f"{label}.evidence_directory",
            f"per-trial checker could not be recomputed from preserved evidence: {exc}",
        ) from exc
    if (
        recomputed_exit not in {0, 1}
        or _normalized_checker_bytes(recomputed_checker)
        != _normalized_checker_bytes(checker)
    ):
        raise SuiteLedgerError(
            "SUITE_CHECKER_RECOMPUTATION_MISMATCH",
            f"{label}.checker_result",
            "archived checker JSON differs from a fresh check of the bound evidence snapshot",
        )

    if previous_attempt is not None and previous_attempt.get("controller") != TRIAL_INVALID_CONTROLLER:
        raise SuiteLedgerError(
            "SUITE_RETRY_AFTER_NONCONTROLLER_FAILURE",
            label,
            "only an invalid-controller attempt may have a retry descendant",
        )
    return controller_outcome, candidate_outcome, transport_outcome


def _validate_suite(
    *,
    root: Path,
    suite: object,
    suite_number: int,
    expected_counted: list[tuple[str, str]],
    protocol_bytes: bytes,
    seen_session_references: set[str],
) -> tuple[str, str, str, tuple[tuple[str, int, str], ...]]:
    label = f"$.suites[{suite_number - 1}]"
    if not isinstance(suite, dict) or set(suite) != SUITE_FIELDS:
        raise SuiteLedgerError(
            "SUITE_RUN_FIELDS_INVALID",
            label,
            "suite-run fields differ from the strict aggregate contract",
        )
    suite_id = f"S{suite_number:02d}"
    if (
        suite.get("suite_id") != suite_id
        or suite.get("repair_number") != suite_number - 1
        or suite.get("status") not in SUITE_STATUSES
    ):
        raise SuiteLedgerError(
            "SUITE_RUN_IDENTITY_INVALID",
            label,
            "suite ID, repair number, or status is invalid",
        )
    freeze_bytes, _ = _read_ref(
        root,
        suite.get("freeze_manifest"),
        label=f"{label}.freeze_manifest",
    )
    freeze_digest = _sha256(freeze_bytes)
    candidate_source_root, registered_file_bindings = _validate_candidate_snapshot(
        ledger_root=root,
        suite=suite,
        freeze_bytes=freeze_bytes,
        protocol_bytes=protocol_bytes,
        label=label,
    )
    candidate_identity_digest = suite.get("candidate_identity_sha256")
    if (
        not isinstance(candidate_identity_digest, str)
        or not HASH_RE.fullmatch(candidate_identity_digest)
    ):
        raise SuiteLedgerError(
            "SUITE_CANDIDATE_IDENTITY_INVALID",
            f"{label}.candidate_identity_sha256",
            "suite candidate identity must be one SHA-256 digest",
        )

    trials = suite.get("trials")
    if not isinstance(trials, list) or not trials or len(trials) > 39:
        raise SuiteLedgerError(
            "SUITE_TRIAL_ROSTER_INVALID",
            f"{label}.trials",
            "suite must contain a nonempty prefix of at most 39 frozen trials",
        )
    final_outcomes: list[str] = []
    for index, trial in enumerate(trials):
        expected_trial_id, expected_case_id = expected_counted[index]
        trial_label = f"{label}.trials[{index}]"
        if (
            not isinstance(trial, dict)
            or set(trial) != TRIAL_FIELDS
            or trial.get("trial_id") != expected_trial_id
            or trial.get("case_id") != expected_case_id
            or not isinstance(trial.get("attempts"), list)
            or not trial["attempts"]
        ):
            raise SuiteLedgerError(
                "SUITE_TRIAL_ORDER_OR_MAPPING_INVALID",
                trial_label,
                "counted trials must occur exactly once in frozen C001..C039 order",
            )
        previous: dict[str, Any] | None = None
        final_candidate = CANDIDATE_NOT_SCORED
        for attempt_number, attempt in enumerate(trial["attempts"], 1):
            controller_outcome, final_candidate, _ = _validate_attempt(
                root=root,
                suite=suite,
                trial=trial,
                attempt=attempt,
                attempt_number=attempt_number,
                previous_attempt=previous,
                expected_trial_id=expected_trial_id,
                expected_case_id=expected_case_id,
                freeze_digest=freeze_digest,
                candidate_identity_digest=candidate_identity_digest,
                candidate_source_root=candidate_source_root,
                seen_session_references=seen_session_references,
            )
            previous = attempt
            if (
                attempt_number < len(trial["attempts"])
                and controller_outcome != TRIAL_INVALID_CONTROLLER
            ):
                raise SuiteLedgerError(
                    "SUITE_RETRY_AFTER_NONCONTROLLER_FAILURE",
                    trial_label,
                    "only invalid-controller attempts may be retried",
                )
        if previous is None or previous.get("controller") != CONTROLLER_VALID:
            raise SuiteLedgerError(
                "SUITE_TRIAL_UNRESOLVED_CONTROLLER",
                trial_label,
                "each counted trial must end with one controller-valid scored attempt",
            )
        final_outcomes.append(final_candidate)

    status = suite["status"]
    if status == "complete_pass":
        if len(trials) != 39 or any(
            outcome != CANDIDATE_PASSED for outcome in final_outcomes
        ):
            raise SuiteLedgerError(
                "SUITE_COMPLETE_PASS_INVALID",
                label,
                "complete_pass requires all 39 cases exactly once and every case passing",
            )
    else:
        if (
            final_outcomes[-1] != CANDIDATE_FAILED
            or any(outcome != CANDIDATE_PASSED for outcome in final_outcomes[:-1])
        ):
            raise SuiteLedgerError(
                "SUITE_STOPPING_RULE_VIOLATION",
                label,
                "a stopped suite must end at its first substantive candidate failure",
            )
    return (
        status,
        freeze_digest,
        candidate_identity_digest,
        registered_file_bindings,
    )


def check_suite_ledger(path: Path) -> tuple[int, dict[str, Any]]:
    findings: list[dict[str, str]] = []
    checks = {
        "ledger_schema": {"status": "not_run"},
        "frozen_protocol": {"status": "not_run"},
        "candidate_source_snapshot": {"status": "not_run"},
        "trial_order": {"status": "not_run"},
        "freeze_identity": {"status": "not_run"},
        "retry_ancestry": {"status": "not_run"},
        "pre_post_score_chain": {"status": "not_run"},
        "evidence_recomputation": {"status": "not_run"},
        "fresh_conversations": {"status": "not_run"},
        "repair_and_stopping_rule": {"status": "not_run"},
        "promotion_gate": {"status": "not_run"},
    }
    try:
        ledger_path = path.resolve(strict=True)
        if not ledger_path.is_file() or ledger_path.is_symlink():
            raise OSError("not a regular file")
        root = ledger_path.parent
        ledger = _strict_json(ledger_path.read_bytes(), ledger_path.name)
        if not isinstance(ledger, dict) or set(ledger) != LEDGER_FIELDS:
            raise SuiteLedgerError(
                "SUITE_LEDGER_FIELDS_INVALID",
                "$",
                "suite-ledger fields differ from the strict aggregate contract",
            )
        if (
            ledger.get("suite_ledger_version") != "1.0"
            or ledger.get("overall_status") not in OVERALL_STATUSES
            or not isinstance(ledger.get("suites"), list)
            or not 1 <= len(ledger["suites"]) <= 2
        ):
            raise SuiteLedgerError(
                "SUITE_LEDGER_HEADER_INVALID",
                "$",
                "ledger version, overall status, or suite count is invalid",
            )
        checks["ledger_schema"]["status"] = "pass"

        protocol_bytes, _ = _read_ref(
            root,
            ledger.get("frozen_protocol"),
            label="$.frozen_protocol",
        )
        canonical_protocol = (ROOT / FROZEN_PROTOCOL_RELATIVE).read_bytes()
        if protocol_bytes != canonical_protocol:
            raise SuiteLedgerError(
                "SUITE_FROZEN_PROTOCOL_MISMATCH",
                "$.frozen_protocol",
                "ledger protocol bytes differ from the canonical frozen protocol",
            )
        protocol_document = _strict_json(
            protocol_bytes,
            "$.frozen_protocol",
        )
        projection_oracle = (
            protocol_document.get("research_projection_oracle")
            if isinstance(protocol_document, dict)
            else None
        )
        status_case_ids = (
            projection_oracle.get("status_only_case_ids")
            if isinstance(projection_oracle, dict)
            else None
        )
        if (
            not isinstance(protocol_document, dict)
            or protocol_document.get("protocol_schema")
            != "bsc-gpt-frozen-evaluation/v5"
            or not isinstance(projection_oracle, dict)
            or projection_oracle.get("score_result_version") != "2.0"
            or projection_oracle.get("default_requirement")
            != SCIENTIFIC_RESEARCH_PROJECTION_REQUIRED
            or projection_oracle.get("status_only_requirement")
            != STATUS_ONLY_RESEARCH_PROJECTION_EMPTY
            or not isinstance(status_case_ids, list)
            or set(status_case_ids) != STATUS_ONLY_CASE_IDS
            or len(status_case_ids) != len(STATUS_ONLY_CASE_IDS)
        ):
            raise SuiteLedgerError(
                "SUITE_FROZEN_PROTOCOL_MISMATCH",
                "$.frozen_protocol",
                "frozen protocol research projection contract differs from the aggregate checker",
            )
        bindings = frozen_trial_bindings(ROOT)
        expected_counted = [
            (f"C{number:03d}", bindings[f"C{number:03d}"][1])
            for number in range(1, 40)
        ]
        checks["frozen_protocol"]["status"] = "pass"

        seen_session_references: set[str] = set()
        suite_results = [
            _validate_suite(
                root=root,
                suite=suite,
                suite_number=index,
                expected_counted=expected_counted,
                protocol_bytes=protocol_bytes,
                seen_session_references=seen_session_references,
            )
            for index, suite in enumerate(ledger["suites"], 1)
        ]
        for name in (
            "trial_order",
            "candidate_source_snapshot",
            "freeze_identity",
            "retry_ancestry",
            "pre_post_score_chain",
            "evidence_recomputation",
            "fresh_conversations",
        ):
            checks[name]["status"] = "pass"

        first_status, first_freeze, first_identity, first_registered_files = (
            suite_results[0]
        )
        if ledger["suites"][0].get("restart_of") is not None:
            raise SuiteLedgerError(
                "SUITE_REPAIR_RESTART_INVALID",
                "$.suites[0].restart_of",
                "the first suite cannot restart another suite",
            )
        if len(suite_results) == 2:
            (
                second_status,
                second_freeze,
                second_identity,
                second_registered_files,
            ) = suite_results[1]
            second_suite = ledger["suites"][1]
            if (
                first_status != "stopped_candidate_failed"
                or second_suite.get("restart_of") != "S01"
                or second_freeze == first_freeze
                or second_identity == first_identity
            ):
                raise SuiteLedgerError(
                    "SUITE_REPAIR_RESTART_INVALID",
                    "$.suites[1]",
                    "the sole repair requires a new freeze and full S02 restart after S01 failure",
                )
            if second_registered_files == first_registered_files:
                raise SuiteLedgerError(
                    "SUITE_REPAIR_REGISTERED_FILES_UNCHANGED",
                    "$.suites[1]",
                    "S02 must change at least one frozen registered file path byte count or SHA-256",
                )
            expected_overall = (
                "passed"
                if second_status == "complete_pass"
                else "failed_closed"
            )
        else:
            expected_overall = (
                "passed"
                if first_status == "complete_pass"
                else ledger["overall_status"]
            )
            if (
                first_status == "stopped_candidate_failed"
                and ledger["overall_status"] not in {"repair_pending", "failed_closed"}
            ):
                raise SuiteLedgerError(
                    "SUITE_OVERALL_STATUS_INVALID",
                    "$.overall_status",
                    "a stopped first suite is repair_pending or explicitly failed_closed",
                )
        if ledger["overall_status"] != expected_overall:
            raise SuiteLedgerError(
                "SUITE_OVERALL_STATUS_INVALID",
                "$.overall_status",
                "overall status does not follow the bounded repair/stopping state",
            )
        checks["repair_and_stopping_rule"]["status"] = "pass"
        if ledger["overall_status"] == "passed":
            checks["promotion_gate"]["status"] = "pass"
            status = "pass"
            exit_code = 0
        else:
            checks["promotion_gate"] = {
                "status": "blocked",
                "details": ["aggregate counted-suite promotion gate is not passed"],
            }
            status = "blocked"
            exit_code = 1
    except (OSError, SuiteLedgerError, ValueError) as exc:
        if isinstance(exc, SuiteLedgerError):
            finding = {
                "severity": "ERROR",
                "code": exc.code,
                "path": exc.path,
                "message": exc.message,
            }
        else:
            finding = {
                "severity": "ERROR",
                "code": "SUITE_LEDGER_UNAVAILABLE",
                "path": str(path),
                "message": str(exc),
            }
        findings.append(finding)
        for check in checks.values():
            if check["status"] == "not_run":
                check["status"] = "blocked"
        status = "blocked"
        exit_code = 1
    payload = {
        "checker": "gpt_eval_suite",
        "output_version": "1.0",
        "ledger": str(path),
        "status": status,
        "checks": checks,
        "findings": findings,
    }
    return exit_code, payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_gpt_eval_suite.py",
        description="Validate frozen 39-case Preview suite closure and repair bounds",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check")
    check.add_argument("ledger", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    status, payload = check_suite_ledger(args.ledger)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
