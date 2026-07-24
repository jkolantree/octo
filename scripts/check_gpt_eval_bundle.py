#!/usr/bin/env python3
"""Fail-closed verification for a preserved Custom GPT evaluation bundle."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import html
import io
import json
import re
import sys
import tempfile
import unicodedata
import zlib
from contextlib import redirect_stdout
from pathlib import Path, PurePosixPath
from typing import Any

try:
    from scripts.gpt_eval_controller import (
        BOUND_RUNTIME_ARTIFACT,
        CANDIDATE_IDENTITY_FILENAMES,
        CANDIDATE_FAILED,
        CANDIDATE_NOT_SCORED,
        CANDIDATE_PASSED,
        CONTROLLER_ARTIFACT_FILENAMES,
        DIRECT_ACQUISITION_ATTEMPT_FIELDS,
        DIRECT_ACQUISITION_OUTCOMES,
        CONTROLLER_RECORD_VERSION,
        CONTROLLER_RECORD_FIELDS,
        CONTROLLER_VALID,
        KNOWLEDGE_FILENAMES,
        OPTIONAL_CONTROLLER_ARTIFACT_FILENAMES,
        RAW_RESPONSE_FILENAME,
        RECONSTRUCTED_OUTPUT_DIRECTORY,
        TRANSPORT_IDENTITY_RESOLVED,
        TRANSPORT_IDENTITY_UNRESOLVED,
        TRANSPORT_NOT_APPLICABLE,
        TRIAL_INVALID_CONTROLLER,
        byte_record,
        canonical_json_bytes,
        derive_disposition,
        output_record,
        parse_runtime_ledger,
        validate_closed_evidence_layout,
        validate_controller_record,
    )
except ModuleNotFoundError:  # Direct ``python scripts/check_gpt_eval_bundle.py``.
    from gpt_eval_controller import (  # type: ignore[no-redef]
        BOUND_RUNTIME_ARTIFACT,
        CANDIDATE_IDENTITY_FILENAMES,
        CANDIDATE_FAILED,
        CANDIDATE_NOT_SCORED,
        CANDIDATE_PASSED,
        CONTROLLER_ARTIFACT_FILENAMES,
        DIRECT_ACQUISITION_ATTEMPT_FIELDS,
        DIRECT_ACQUISITION_OUTCOMES,
        CONTROLLER_RECORD_VERSION,
        CONTROLLER_RECORD_FIELDS,
        CONTROLLER_VALID,
        KNOWLEDGE_FILENAMES,
        OPTIONAL_CONTROLLER_ARTIFACT_FILENAMES,
        RAW_RESPONSE_FILENAME,
        RECONSTRUCTED_OUTPUT_DIRECTORY,
        TRANSPORT_IDENTITY_RESOLVED,
        TRANSPORT_IDENTITY_UNRESOLVED,
        TRANSPORT_NOT_APPLICABLE,
        TRIAL_INVALID_CONTROLLER,
        byte_record,
        canonical_json_bytes,
        derive_disposition,
        output_record,
        parse_runtime_ledger,
        validate_closed_evidence_layout,
        validate_controller_record,
    )


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bsc_audit.cli import main as bsc_audit_main  # noqa: E402

try:
    from scripts.gpt_artifact_compiler import (  # noqa: E402
        COMPILER_VERSION,
        EXPORT_CHUNK_FIELDS,
        MAX_TRANSPORT_ENCODED_BYTES,
        MAX_TRANSPORT_PAYLOAD_BYTES,
        SAME_RESPONSE_TRANSPORT_VERSION,
        TRANSPORT_CHUNK_BYTES,
        TRANSPORT_CHUNK_VERSION,
        TRANSPORT_ENCODING,
    )
except ModuleNotFoundError:  # Direct ``python scripts/check_gpt_eval_bundle.py``.
    from gpt_artifact_compiler import (  # type: ignore[no-redef] # noqa: E402
        COMPILER_VERSION,
        EXPORT_CHUNK_FIELDS,
        MAX_TRANSPORT_ENCODED_BYTES,
        MAX_TRANSPORT_PAYLOAD_BYTES,
        SAME_RESPONSE_TRANSPORT_VERSION,
        TRANSPORT_CHUNK_BYTES,
        TRANSPORT_CHUNK_VERSION,
        TRANSPORT_ENCODING,
    )


ACTIVE_EXPORT_SUFFIX = ".export."
CONTROLLER_RECORD_NAME = "controller_record.json"
TRANSPORT_RECORD_FIELDS = {
    "filename",
    "method",
    "direct_download_outcome",
    "bytes",
    "sha256",
    "export_chunks",
}
LEGACY_TRANSPORT_RECORD_VERSION = "2.0"
TRANSPORT_RECORD_VERSION = "3.0"
SUPPORTED_TRANSPORT_RECORD_VERSIONS = {
    LEGACY_TRANSPORT_RECORD_VERSION,
    TRANSPORT_RECORD_VERSION,
}
SAME_RESPONSE_TRANSPORT_METHOD = "in_turn_compiler_bundle"
TRANSPORT_CHUNK_FILENAME_RE = re.compile(
    r"^(?P<payload>.+)\.export\.(?P<index>[0-9]{5})\.json$"
)
HASH_RE = re.compile(r"^(?:sha256:)?([0-9a-fA-F]{64})$")
SYS_VERSION_RE = re.compile(
    r"\d+\.\d+\.\d+(?:[A-Za-z0-9.+-]*)? \([^\r\n()]+\) \[[^\r\n\[\]]+\]"
)
EXPECTATION_FILES = {
    "profile_hash": "GPT_PROFILE.json",
    "instructions_hash": "GPT_INSTRUCTIONS.md",
    "eval_spec_hash": "GPT_EVAL_SPEC.json",
}
SCORE_RESULT_FIELDS = {
    "score_result_version",
    "case_id",
    "trial_id",
    "pre_score_controller_sha256",
    "dimension_scores",
    "total_score",
    "automatic_failure",
    "observable_behavior_results",
    "forbidden_behavior_results",
    "observed_research_projection",
    "research_projection_requirement",
    "research_verdict_allowed",
    "research_projection_contract_satisfied",
    "terminal_response_complete",
    "scorer",
    "notes",
}
SCIENTIFIC_RESEARCH_PROJECTION_REQUIRED = "scientific_verdict_required"
STATUS_ONLY_RESEARCH_PROJECTION_EMPTY = "status_only_empty"
RESEARCH_PROJECTION_REQUIREMENTS = {
    SCIENTIFIC_RESEARCH_PROJECTION_REQUIRED,
    STATUS_ONLY_RESEARCH_PROJECTION_EMPTY,
}
LIMITATION = (
    "Strict same-response compiler-bundle or legacy chunk reconstruction validates "
    "the captured encoding, declared identities, and local-byte equality; they do "
    "not establish download-button identity or prove which bytes a UI download "
    "button served."
)
TRANSPORT_LIMITATION = (
    "The transport record preserves the controller's observed download exposure/event outcome; "
    "the record is not independent proof that the UI exposed or emitted a download."
)


class StrictJsonError(ValueError):
    """Raised when JSON violates the checker's strict decoding contract."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise StrictJsonError(message)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise StrictJsonError(f"non-finite JSON number is prohibited: {value}")


def _strict_json(text: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, RecursionError, StrictJsonError) as exc:
        raise StrictJsonError("input is not valid strict JSON") from exc


def _digest(value: Any, *, prefixed: bool = False) -> str | None:
    if not isinstance(value, str):
        return None
    if prefixed and not value.startswith("sha256:"):
        return None
    match = HASH_RE.fullmatch(value)
    return match.group(1).lower() if match else None


def _relative_label(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _add_finding(
    findings: list[dict[str, str]],
    code: str,
    path: str,
    message: str,
) -> None:
    findings.append(
        {
            "severity": "ERROR",
            "code": code,
            "path": path,
            "message": message,
        }
    )


def _set_check(
    checks: dict[str, dict[str, Any]],
    name: str,
    status: str,
    detail: str | None = None,
) -> None:
    record = checks.setdefault(name, {"status": status})
    if record["status"] == "blocked":
        pass
    elif status == "blocked" or record["status"] == "not_run":
        record["status"] = status
    if detail:
        record.setdefault("details", []).append(detail)


def _forbidden_controls(text: str) -> list[str]:
    controls = {
        f"U+{ord(character):04X}"
        for character in text
        if character not in "\t\n\r" and unicodedata.category(character) == "Cc"
    }
    return sorted(controls)


def _decode_text(
    data: bytes,
    label: str,
    findings: list[dict[str, str]],
    checks: dict[str, dict[str, Any]],
) -> str | None:
    if data.startswith(b"\xef\xbb\xbf"):
        _add_finding(
            findings,
            "TEXT_UTF8_BOM",
            label,
            "UTF-8 text must not begin with a byte-order mark",
        )
        _set_check(checks, "text_sanitation", "blocked", label)
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        _add_finding(
            findings,
            "TEXT_NOT_UTF8",
            label,
            "text payload is not strict UTF-8",
        )
        _set_check(checks, "text_sanitation", "blocked", label)
        return None
    controls = _forbidden_controls(text)
    if controls:
        _add_finding(
            findings,
            "TEXT_CONTROL_CHARACTER",
            label,
            "text contains prohibited control characters; only TAB, LF, and CR are allowed",
        )
        _set_check(
            checks,
            "text_sanitation",
            "blocked",
            f"{label}: {', '.join(controls)}",
        )
    return text


def _walk_string_controls(
    value: Any,
    label: str,
    findings: list[dict[str, str]],
    checks: dict[str, dict[str, Any]],
) -> None:
    if isinstance(value, str):
        controls = _forbidden_controls(value)
        if controls:
            _add_finding(
                findings,
                "JSON_STRING_CONTROL_CHARACTER",
                label,
                "decoded JSON string contains prohibited control characters",
            )
            _set_check(
                checks,
                "text_sanitation",
                "blocked",
                f"{label}: {', '.join(controls)}",
            )
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _walk_string_controls(
                item,
                f"{label}[{index}]",
                findings,
                checks,
            )
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _walk_string_controls(
                item,
                f"{label}.{key}",
                findings,
                checks,
            )


def _safe_file(root: Path, filename: Any) -> Path | None:
    if (
        not isinstance(filename, str)
        or not filename
        or filename in {".", ".."}
        or "/" in filename
        or "\\" in filename
        or "\x00" in filename
        or Path(filename).is_absolute()
    ):
        return None
    candidate = root / filename
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        return None
    return resolved if resolved.is_file() else None


def _load_json_path(
    root: Path,
    path: Path,
    findings: list[dict[str, str]],
    checks: dict[str, dict[str, Any]],
    check_name: str,
) -> dict[str, Any] | None:
    label = _relative_label(root, path)
    try:
        data = path.read_bytes()
    except OSError:
        _add_finding(findings, "FILE_UNREADABLE", label, "required JSON file is unreadable")
        _set_check(checks, check_name, "blocked", label)
        return None
    text = _decode_text(data, label, findings, checks)
    if text is None:
        _set_check(checks, check_name, "blocked", label)
        return None
    try:
        value = _strict_json(text)
    except StrictJsonError as exc:
        _add_finding(findings, "JSON_INVALID", label, str(exc))
        _set_check(checks, check_name, "blocked", label)
        return None
    if not isinstance(value, dict):
        _add_finding(findings, "JSON_TOP_LEVEL_NOT_OBJECT", label, "top-level JSON value must be an object")
        _set_check(checks, check_name, "blocked", label)
        return None
    _walk_string_controls(value, "$", findings, checks)
    return value


def _safe_repo_relative_file(root: Path, relative: Any) -> Path | None:
    """Resolve a frozen repo-relative fixture without relaxing bundle basenames."""

    if (
        not isinstance(relative, str)
        or not relative
        or "\\" in relative
        or "\x00" in relative
    ):
        return None
    pure = PurePosixPath(relative)
    if (
        pure.is_absolute()
        or ".." in pure.parts
        or any(part in {"", "."} for part in pure.parts)
        or pure.as_posix() != relative
    ):
        return None
    candidate = root.joinpath(*pure.parts)
    current = root
    try:
        for part in pure.parts:
            current = current / part
            if current.is_symlink():
                return None
        resolved_root = root.resolve(strict=True)
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        return None
    return resolved if resolved.is_file() else None


def _expected_case_context(
    case_id: str,
    repository_root: Path = ROOT,
) -> tuple[
    list[dict[str, Any]],
    bytes,
    set[str],
    list[str],
    list[str],
    list[str],
    list[str],
    str,
    dict[str, Any] | None,
]:
    cases_path = repository_root / "gpt" / "evals" / "GPT_EVAL_CASES.jsonl"
    selected: dict[str, Any] | None = None
    try:
        lines = cases_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise StrictJsonError("generated evaluation cases are unavailable") from exc
    for line in lines:
        if not line:
            continue
        value = _strict_json(line)
        if isinstance(value, dict) and value.get("id") == case_id:
            if selected is not None:
                raise StrictJsonError("evaluation case identifier is duplicated")
            selected = value
    if selected is None:
        raise StrictJsonError("controller case identifier is not in the frozen suite")
    fixture_paths = selected.get("fixture_paths")
    if (
        not isinstance(fixture_paths, list)
        or len(fixture_paths) != 1
        or not isinstance(fixture_paths[0], str)
    ):
        raise StrictJsonError("selected evaluation case must bind exactly one target")
    target = _safe_repo_relative_file(repository_root / "gpt", fixture_paths[0])
    if target is None:
        raise StrictJsonError("selected evaluation target is unavailable or unsafe")
    target_data = target.read_bytes()
    expected_fixture_hash = _digest(selected.get("fixture_sha256"))
    if expected_fixture_hash != _sha256(target_data):
        raise StrictJsonError("selected evaluation target differs from its frozen digest")
    preview_prompt = selected.get("preview_prompt")
    if not isinstance(preview_prompt, str) or not preview_prompt:
        raise StrictJsonError("selected evaluation case lacks an exact preview prompt")
    values = [byte_record("target", target.name, target_data)]
    for filename in KNOWLEDGE_FILENAMES:
        path = repository_root / "gpt" / "knowledge" / filename
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise StrictJsonError(
                f"canonical Knowledge file is unavailable: {filename}"
            ) from exc
        values.append(byte_record("knowledge", filename, data))
    expected = selected.get("expected")
    behavior_text = json.dumps(
        {
            "user_request": selected.get("user_request"),
            "workflow_requirement": selected.get("workflow_requirement"),
            "expected": expected,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    required_outputs = (
        {"audit_report.md", "audit_return.json"}
        if "audit_return.json" in behavior_text and "audit_report.md" in behavior_text
        else set()
    )
    scoring_criteria = selected.get("scoring_criteria")
    observable = expected.get("observable_behaviors") if isinstance(expected, dict) else None
    forbidden = expected.get("forbidden_behaviors") if isinstance(expected, dict) else None
    allowed_verdicts = (
        expected.get("research_verdict_any_of")
        if isinstance(expected, dict)
        else None
    )
    projection_requirement = (
        expected.get("research_projection_requirement")
        if isinstance(expected, dict)
        else None
    )
    scientific_oracle_valid = (
        projection_requirement == SCIENTIFIC_RESEARCH_PROJECTION_REQUIRED
        and isinstance(expected, dict)
        and expected.get("execution") != "status_record_read_only"
        and isinstance(allowed_verdicts, list)
        and bool(allowed_verdicts)
        and all(isinstance(item, str) and item for item in allowed_verdicts)
        and len(set(allowed_verdicts)) == len(allowed_verdicts)
    )
    status_only_oracle_valid = (
        projection_requirement == STATUS_ONLY_RESEARCH_PROJECTION_EMPTY
        and isinstance(expected, dict)
        and expected.get("execution") == "status_record_read_only"
        and "research_verdict_any_of" not in expected
        and "research_projection_exact" not in expected
    )
    exact_projection = (
        expected.get("research_projection_exact")
        if isinstance(expected, dict)
        else None
    )
    exact_projection_valid = exact_projection is None
    if exact_projection is not None:
        exact_claim_ids = (
            exact_projection.get("primary_claim_ids")
            if isinstance(exact_projection, dict)
            else None
        )
        exact_verdicts = (
            exact_projection.get("verdicts_by_claim")
            if isinstance(exact_projection, dict)
            else None
        )
        exact_projection_valid = (
            projection_requirement == SCIENTIFIC_RESEARCH_PROJECTION_REQUIRED
            and isinstance(allowed_verdicts, list)
            and isinstance(exact_projection, dict)
            and set(exact_projection)
            == {
                "primary_claim_ids",
                "verdicts_by_claim",
                "allow_additional_primary_claims",
            }
            and isinstance(exact_claim_ids, list)
            and bool(exact_claim_ids)
            and all(
                isinstance(claim_id, str) and claim_id
                for claim_id in exact_claim_ids
            )
            and len(set(exact_claim_ids)) == len(exact_claim_ids)
            and isinstance(exact_verdicts, dict)
            and set(exact_verdicts) == set(exact_claim_ids)
            and all(
                isinstance(verdict, str)
                and verdict
                and verdict in allowed_verdicts
                for verdict in exact_verdicts.values()
            )
            and isinstance(
                exact_projection.get("allow_additional_primary_claims"),
                bool,
            )
        )
    if (
        not isinstance(scoring_criteria, list)
        or len(scoring_criteria) != 10
        or not all(isinstance(item, str) and item for item in scoring_criteria)
        or len(set(scoring_criteria)) != len(scoring_criteria)
        or not isinstance(observable, list)
        or not all(isinstance(item, str) and item for item in observable)
        or not isinstance(forbidden, list)
        or not all(isinstance(item, str) and item for item in forbidden)
        or projection_requirement not in RESEARCH_PROJECTION_REQUIREMENTS
        or not (scientific_oracle_valid or status_only_oracle_valid)
        or not exact_projection_valid
    ):
        raise StrictJsonError("selected evaluation case has an invalid frozen scoring oracle")
    return (
        values,
        preview_prompt.encode("utf-8"),
        required_outputs,
        scoring_criteria,
        observable,
        forbidden,
        allowed_verdicts if isinstance(allowed_verdicts, list) else [],
        projection_requirement,
        exact_projection,
    )


def _expected_candidate_identity(
    repository_root: Path = ROOT,
) -> list[dict[str, Any]]:
    source_by_kind = {
        "freeze_manifest": repository_root / "docs" / "GPT_FROZEN_CANDIDATE.json",
        "profile": repository_root / "gpt" / "_source" / "GPT_PROFILE.json",
        "instructions": repository_root / "gpt" / "GPT_INSTRUCTIONS.md",
        "eval_spec": repository_root / "gpt" / "_source" / "GPT_EVAL_SPEC.json",
    }
    result: list[dict[str, Any]] = []
    for kind, filename in CANDIDATE_IDENTITY_FILENAMES:
        path = source_by_kind[kind]
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise StrictJsonError(
                f"canonical candidate identity is unavailable: {filename}"
            ) from exc
        result.append(byte_record(kind, filename, data))
    return result


def _uses_same_response_transport(controller_record: object) -> bool:
    return (
        isinstance(controller_record, dict)
        and controller_record.get("controller_record_version")
        == CONTROLLER_RECORD_VERSION
        and "compiler_transport_capture" in controller_record
        and "reconstructed_outputs" in controller_record
    )


def _candidate_output_root(
    root: Path,
    controller_record: object,
) -> Path:
    if _uses_same_response_transport(controller_record):
        return root / RECONSTRUCTED_OUTPUT_DIRECTORY
    return root


def _actual_candidate_output_filenames(
    root: Path,
    *,
    input_filenames: set[str],
    controller_record: object = None,
) -> set[str]:
    """Inventory candidate outputs independently of audit_return declarations."""

    output_root = _candidate_output_root(root, controller_record)
    if output_root != root:
        outputs: set[str] = set()
        try:
            if (
                output_root.is_symlink()
                or not output_root.is_dir()
                or output_root.resolve(strict=True).parent != root.resolve(strict=True)
            ):
                entries: list[Path] = []
            else:
                entries = list(output_root.iterdir())
        except (OSError, RuntimeError):
            entries = []
        for path in entries:
            if (
                not path.is_file()
                or path.is_symlink()
                or _safe_file(output_root.resolve(strict=True), path.name) is None
            ):
                continue
            outputs.add(path.name)
        observed_direct = (
            controller_record.get("observed_outputs")
            if isinstance(controller_record, dict)
            else None
        )
        if isinstance(observed_direct, list):
            for item in observed_direct:
                filename = item.get("filename") if isinstance(item, dict) else None
                if isinstance(filename, str) and _safe_file(root, filename) is not None:
                    outputs.add(filename)
        excluded_root_names = {
            CONTROLLER_RECORD_NAME,
            *input_filenames,
            *(filename for _, filename in CANDIDATE_IDENTITY_FILENAMES),
            *CONTROLLER_ARTIFACT_FILENAMES,
            *OPTIONAL_CONTROLLER_ARTIFACT_FILENAMES,
        }
        try:
            root_entries = list(root.iterdir())
        except OSError:
            root_entries = []
        for path in root_entries:
            if (
                path.name in excluded_root_names
                or path.name in outputs
                or TRANSPORT_CHUNK_FILENAME_RE.fullmatch(path.name) is not None
                or not path.is_file()
                or path.is_symlink()
                or _safe_file(root, path.name) is None
            ):
                continue
            outputs.add(path.name)
        return outputs

    excluded = {
        CONTROLLER_RECORD_NAME,
        *input_filenames,
        *(filename for _, filename in CANDIDATE_IDENTITY_FILENAMES),
        *CONTROLLER_ARTIFACT_FILENAMES,
        *OPTIONAL_CONTROLLER_ARTIFACT_FILENAMES,
    }
    outputs: set[str] = set()
    for path in root.iterdir():
        if (
            path.name in excluded
            or TRANSPORT_CHUNK_FILENAME_RE.fullmatch(path.name) is not None
            or not path.is_file()
            or path.is_symlink()
        ):
            continue
        outputs.add(path.name)
    return outputs


def _declared_candidate_outputs(
    audit_return: dict[str, Any],
    *,
    input_filenames: set[str],
) -> set[str] | None:
    artifacts = audit_return.get("artifacts")
    if not isinstance(artifacts, list):
        return None
    names: set[str] = {"audit_return.json"}
    for item in artifacts:
        if not isinstance(item, dict) or not isinstance(item.get("filename"), str):
            return None
        if (
            item["filename"] not in input_filenames
            and item.get("role") != "source"
        ):
            names.add(item["filename"])
    return names


def _load_controller_record(
    root: Path,
) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    path = root / CONTROLLER_RECORD_NAME
    try:
        data = path.read_bytes()
    except OSError:
        return None, [
            {
                "severity": "ERROR",
                "code": "CONTROLLER_RECORD_MISSING",
                "path": CONTROLLER_RECORD_NAME,
                "message": "strict controller_record.json is required before replay or scoring",
            }
        ]
    try:
        text = data.decode("utf-8", errors="strict")
        if text.encode("utf-8") != data:
            raise UnicodeError("UTF-8 round trip differs")
        record = _strict_json(text)
    except (UnicodeError, StrictJsonError):
        return None, [
            {
                "severity": "ERROR",
                "code": "CONTROLLER_RECORD_INVALID",
                "path": CONTROLLER_RECORD_NAME,
                "message": "controller record must be strict round-tripping UTF-8 JSON",
            }
        ]
    if not isinstance(record, dict):
        return None, [
            {
                "severity": "ERROR",
                "code": "CONTROLLER_RECORD_INVALID",
                "path": CONTROLLER_RECORD_NAME,
                "message": "controller record must be a JSON object",
            }
        ]
    return record, []


def _transport_identity_axis(
    records: dict[str, dict[str, Any]],
    observed_output_controls: set[str],
    *,
    has_transport_attempts: bool,
    has_same_response_capture: bool = False,
    required_output_filenames: set[str] | None = None,
    direct_download_filenames: set[str] | None = None,
) -> str:
    if (
        not records
        and not observed_output_controls
        and not has_transport_attempts
        and not has_same_response_capture
    ):
        return TRANSPORT_NOT_APPLICABLE
    required_controls = (
        set(required_output_filenames or set()) & observed_output_controls
    )
    if not required_controls and observed_output_controls:
        required_controls = set(observed_output_controls)
    if required_controls and required_controls.issubset(
        direct_download_filenames or set()
    ):
        return TRANSPORT_IDENTITY_RESOLVED
    # File controls, self-reported download events, same-response compiler
    # reconstruction, and legacy fallback payloads preserve different
    # observations. None independently authenticates the bytes that a UI
    # download button would have served.
    return TRANSPORT_IDENTITY_UNRESOLVED


def _verify_artifacts(
    root: Path,
    audit_return: dict[str, Any],
    findings: list[dict[str, str]],
    checks: dict[str, dict[str, Any]],
    *,
    unavailable_filenames: set[str] | None = None,
    source_root: Path | None = None,
) -> tuple[dict[str, tuple[Path, bytes, str | None]], tuple[Path, str] | None]:
    unavailable = unavailable_filenames or set()
    artifacts_raw = audit_return.get("artifacts")
    if not isinstance(artifacts_raw, list):
        _add_finding(
            findings,
            "ARTIFACT_LEDGER_INVALID",
            "audit_return.json",
            "audit_return.artifacts must be an array",
        )
        _set_check(checks, "audit_return_artifacts", "blocked")
        return {}, None

    artifacts: dict[str, tuple[Path, bytes, str | None]] = {}
    records: dict[str, dict[str, Any]] = {}
    for index, artifact in enumerate(artifacts_raw):
        path_label = f"audit_return.json:$.artifacts[{index}]"
        if not isinstance(artifact, dict):
            _add_finding(findings, "ARTIFACT_RECORD_INVALID", path_label, "artifact record must be an object")
            _set_check(checks, "audit_return_artifacts", "blocked", path_label)
            continue
        identifier = artifact.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in records:
            _add_finding(
                findings,
                "ARTIFACT_ID_INVALID",
                path_label,
                "artifact identifier must be a unique nonempty string",
            )
            _set_check(checks, "audit_return_artifacts", "blocked", path_label)
            continue
        records[identifier] = artifact
        filename = artifact.get("filename")
        local_path = _safe_file(root, filename)
        if (
            local_path is None
            and artifact.get("role") == "source"
            and source_root is not None
        ):
            local_path = _safe_file(source_root, filename)
        if local_path is None:
            if isinstance(filename, str) and filename in unavailable:
                _set_check(
                    checks,
                    "audit_return_artifacts",
                    "not_run",
                    (
                        f"{filename}: file control was observed, but payload bytes "
                        "were not acquired"
                    ),
                )
                continue
            _add_finding(
                findings,
                "ARTIFACT_MISSING_OR_UNSAFE",
                path_label,
                "bound artifact is missing, non-file, symlink-escaped, or has a non-portable relative name",
            )
            _set_check(checks, "audit_return_artifacts", "blocked", str(filename))
            continue
        try:
            data = local_path.read_bytes()
        except OSError:
            _add_finding(
                findings,
                "ARTIFACT_UNREADABLE",
                str(filename),
                "bound artifact cannot be read",
            )
            _set_check(checks, "audit_return_artifacts", "blocked", str(filename))
            continue
        expected = _digest(artifact.get("sha256"), prefixed=True)
        observed = _sha256(data)
        if expected is None:
            _add_finding(
                findings,
                "ARTIFACT_HASH_INVALID",
                path_label,
                "artifact sha256 must use sha256:<64 hexadecimal characters>",
            )
            _set_check(checks, "audit_return_artifacts", "blocked", str(filename))
        elif expected != observed:
            _add_finding(
                findings,
                "ARTIFACT_HASH_MISMATCH",
                str(filename),
                "local artifact bytes do not match audit_return.sha256",
            )
            _set_check(checks, "audit_return_artifacts", "blocked", str(filename))
        text = _decode_text(data, str(filename), findings, checks)
        if text is not None and local_path.suffix.lower() == ".json":
            try:
                decoded_json = _strict_json(text)
            except StrictJsonError:
                decoded_json = None
            if decoded_json is not None:
                _walk_string_controls(decoded_json, f"artifact:{identifier}", findings, checks)
        artifacts[identifier] = (local_path, data, text)

    binding = audit_return.get("bindings")
    report: tuple[Path, str] | None = None
    report_id = binding.get("report_artifact_id") if isinstance(binding, dict) else None
    if not isinstance(report_id, str) or report_id not in records:
        _add_finding(
            findings,
            "REPORT_BINDING_MISSING",
            "audit_return.json:$.bindings.report_artifact_id",
            "the report binding must resolve to one artifact record",
        )
        _set_check(checks, "audit_return_artifacts", "blocked", "report binding")
    elif report_id in artifacts:
        report_path, _, report_text = artifacts[report_id]
        if report_text is None:
            _add_finding(
                findings,
                "REPORT_NOT_UTF8",
                report_path.name,
                "bound report is not strict UTF-8 text",
            )
            _set_check(checks, "audit_return_artifacts", "blocked", report_path.name)
        else:
            report = (report_path, report_text)

    return artifacts, report


def _audit_return_string_values(
    document: Any,
    *,
    structured_runtime_record: dict[str, Any],
) -> list[tuple[str, str]]:
    """Enumerate every return-envelope string except the one runtime projection."""

    results: list[tuple[str, str]] = []
    stack: list[tuple[str, Any]] = [("$", document)]
    while stack:
        path, value = stack.pop()
        if isinstance(value, str):
            results.append((f"audit_return.json:{path}", value))
        elif isinstance(value, list):
            stack.extend(
                (f"{path}[{index}]", item)
                for index, item in reversed(list(enumerate(value)))
            )
        elif isinstance(value, dict):
            children = []
            for key, item in value.items():
                if value is structured_runtime_record and key == "version":
                    continue
                encoded_key = json.dumps(str(key), ensure_ascii=False)
                children.append((f"{path}[{encoded_key}]", item))
            stack.extend(reversed(children))
    return results


def _strict_direct_acquisition_map(
    controller_record: dict[str, Any],
) -> dict[str, str] | None:
    """Index only a complete, canonical direct-acquisition field shape."""

    attempts = controller_record.get("direct_acquisition_attempts")
    if not isinstance(attempts, list):
        return None
    records: list[dict[str, str]] = []
    for item in attempts:
        if (
            not isinstance(item, dict)
            or set(item) != DIRECT_ACQUISITION_ATTEMPT_FIELDS
        ):
            return None
        filename = item.get("filename")
        outcome = item.get("outcome")
        if (
            not isinstance(filename, str)
            or not filename
            or filename != unicodedata.normalize("NFC", filename)
            or filename in {".", ".."}
            or "/" in filename
            or "\\" in filename
            or "\x00" in filename
            or ":" in filename
            or filename != filename.rstrip(" .")
            or PurePosixPath(filename).is_absolute()
            or len(PurePosixPath(filename).parts) != 1
            or outcome not in DIRECT_ACQUISITION_OUTCOMES
        ):
            return None
        records.append({"filename": filename, "outcome": outcome})
    if records != sorted(records, key=lambda item: item["filename"]):
        return None
    normalized_names = [item["filename"].casefold() for item in records]
    if len(normalized_names) != len(set(normalized_names)):
        return None
    return {item["filename"]: item["outcome"] for item in records}


def _verify_transport_record(
    root: Path,
    audit_return: dict[str, Any] | None,
    expected_output_filenames: set[str],
    controller_record: dict[str, Any],
    findings: list[dict[str, str]],
    checks: dict[str, dict[str, Any]],
    *,
    payload_root: Path | None = None,
    allow_incomplete_candidate_capture: bool = False,
) -> dict[str, dict[str, Any]]:
    path = root / "artifact_transport.json"
    document = _load_json_path(
        root,
        path,
        findings,
        checks,
        "artifact_transport",
    ) if path.is_file() else None
    if document is None:
        if not path.is_file():
            _add_finding(
                findings,
                "ARTIFACT_TRANSPORT_RECORD_MISSING",
                path.name,
                "a frozen evaluation bundle requires artifact_transport.json",
            )
            _set_check(checks, "artifact_transport", "blocked")
        return {}
    record_version = document.get("transport_version")
    if (
        set(document) != {"transport_version", "records"}
        or not isinstance(record_version, str)
        or record_version not in SUPPORTED_TRANSPORT_RECORD_VERSIONS
    ):
        _add_finding(
            findings,
            "ARTIFACT_TRANSPORT_RECORD_INVALID",
            path.name,
            (
                "transport record must contain only a supported transport_version "
                f"{sorted(SUPPORTED_TRANSPORT_RECORD_VERSIONS)!r} and records"
            ),
        )
        _set_check(checks, "artifact_transport", "blocked")
    same_response_controller = _uses_same_response_transport(controller_record)
    if (
        record_version == TRANSPORT_RECORD_VERSION
    ) != same_response_controller:
        _add_finding(
            findings,
            "ARTIFACT_TRANSPORT_RECORD_VERSION_MISMATCH",
            path.name,
            (
                "controller v4 same-response captures require transport_version "
                f"{TRANSPORT_RECORD_VERSION}; legacy records require "
                f"{LEGACY_TRANSPORT_RECORD_VERSION}"
            ),
        )
        _set_check(checks, "artifact_transport", "blocked")

    observed_direct_by_filename: dict[str, dict[str, Any]] = {}
    observed_direct = controller_record.get("observed_outputs")
    if isinstance(observed_direct, list):
        for direct_item in observed_direct:
            if (
                isinstance(direct_item, dict)
                and isinstance(direct_item.get("filename"), str)
            ):
                observed_direct_by_filename[direct_item["filename"]] = direct_item
    expected = set(expected_output_filenames) | set(observed_direct_by_filename)
    allowed = set(expected)
    local_root = payload_root if payload_root is not None else root
    records_raw = document.get("records")
    if not isinstance(records_raw, list):
        _add_finding(
            findings,
            "ARTIFACT_TRANSPORT_RECORD_INVALID",
            f"{path.name}:$.records",
            "transport records must be an array",
        )
        _set_check(checks, "artifact_transport", "blocked")
        return {}

    records: dict[str, dict[str, Any]] = {}
    captured_chunks: dict[str, list[tuple[int, str]]] = {}
    reconstructed_by_filename: dict[str, dict[str, Any]] = {}
    reconstructed = controller_record.get("reconstructed_outputs")
    if isinstance(reconstructed, list):
        for reconstructed_item in reconstructed:
            if (
                isinstance(reconstructed_item, dict)
                and isinstance(reconstructed_item.get("filename"), str)
            ):
                reconstructed_by_filename[reconstructed_item["filename"]] = (
                    reconstructed_item
                )
    direct_acquisition_map = _strict_direct_acquisition_map(controller_record)
    if same_response_controller:
        observed_controls = controller_record.get("observed_output_controls")
        observed_control_names = (
            {
                item
                for item in observed_controls
                if isinstance(item, str)
            }
            if isinstance(observed_controls, list)
            else set()
        )
        expected_attempt_names = (
            set(reconstructed_by_filename)
            | set(observed_direct_by_filename)
            | observed_control_names
        )
        if direct_acquisition_map is None:
            _add_finding(
                findings,
                "ARTIFACT_TRANSPORT_DIRECT_ACQUISITION_INVALID",
                "controller_record.json:$.direct_acquisition_attempts",
                (
                    "controller v4 requires canonical sorted "
                    "{filename,outcome} direct-acquisition records"
                ),
            )
            _set_check(checks, "artifact_transport", "blocked")
        elif set(direct_acquisition_map) != expected_attempt_names:
            _add_finding(
                findings,
                "ARTIFACT_TRANSPORT_DIRECT_ACQUISITION_ROSTER_MISMATCH",
                "controller_record.json:$.direct_acquisition_attempts",
                (
                    "direct-acquisition records must exactly cover reconstructed "
                    "outputs, direct outputs, and visible output controls"
                ),
            )
            _set_check(checks, "artifact_transport", "blocked")
        else:
            outcome_mismatches = []
            for filename in sorted(expected_attempt_names):
                expected_outcome = (
                    "download_event"
                    if filename in observed_direct_by_filename
                    else (
                        "no_download_event"
                        if filename in observed_control_names
                        else "unavailable"
                    )
                )
                if direct_acquisition_map[filename] != expected_outcome:
                    outcome_mismatches.append(filename)
            if outcome_mismatches:
                _add_finding(
                    findings,
                    "ARTIFACT_TRANSPORT_DIRECT_ACQUISITION_OUTCOME_MISMATCH",
                    "controller_record.json:$.direct_acquisition_attempts",
                    (
                        "direct-acquisition outcomes contradict the bound direct, "
                        f"visible-control, or reconstructed evidence: "
                        f"{outcome_mismatches!r}"
                    ),
                )
                _set_check(checks, "artifact_transport", "blocked")
    captures = controller_record.get("wrapper_captures")
    if isinstance(captures, list):
        for capture in captures:
            if not isinstance(capture, dict):
                continue
            payload = capture.get("payload_filename")
            chunk_index = capture.get("chunk_index")
            parser_name = capture.get("parser_input_filename")
            if (
                isinstance(payload, str)
                and isinstance(chunk_index, int)
                and not isinstance(chunk_index, bool)
                and isinstance(parser_name, str)
            ):
                captured_chunks.setdefault(payload, []).append(
                    (chunk_index, parser_name)
                )
    for index, item in enumerate(records_raw):
        label = f"{path.name}:$.records[{index}]"
        if not isinstance(item, dict) or set(item) != TRANSPORT_RECORD_FIELDS:
            _add_finding(
                findings,
                "ARTIFACT_TRANSPORT_ENTRY_INVALID",
                label,
                "transport entry fields differ from the frozen transport contract",
            )
            _set_check(checks, "artifact_transport", "blocked", label)
            continue
        filename = item.get("filename")
        if (
            not isinstance(filename, str)
            or filename in records
            or filename not in allowed
        ):
            _add_finding(
                findings,
                "ARTIFACT_TRANSPORT_FILENAME_INVALID",
                label,
                "transport filename must uniquely identify audit_return.json or a declared artifact",
            )
            _set_check(checks, "artifact_transport", "blocked", str(filename))
            continue
        records[filename] = item
        method = item.get("method")
        outcome = item.get("direct_download_outcome")
        export_chunks = item.get("export_chunks")
        local_path = _safe_file(
            root if method == "direct_download" else local_root,
            filename,
        )
        if local_path is None:
            _add_finding(
                findings,
                "ARTIFACT_TRANSPORT_LOCAL_FILE_INVALID",
                label,
                "transported payload does not resolve to a safe local file",
            )
            _set_check(checks, "artifact_transport", "blocked", filename)
            continue
        try:
            data = local_path.read_bytes()
        except OSError:
            _add_finding(
                findings,
                "ARTIFACT_TRANSPORT_LOCAL_FILE_INVALID",
                label,
                "transported payload became unreadable during verification",
            )
            _set_check(checks, "artifact_transport", "blocked", filename)
            continue
        expected_hash = _digest(item.get("sha256"))
        size = item.get("bytes")
        if (
            expected_hash != _sha256(data)
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size != len(data)
        ):
            _add_finding(
                findings,
                "ARTIFACT_TRANSPORT_BYTE_BINDING_MISMATCH",
                label,
                "transport record size or digest differs from the preserved local payload",
            )
            _set_check(checks, "artifact_transport", "blocked", filename)

        if method == "direct_download":
            direct_item = observed_direct_by_filename.get(filename)
            explicit_outcome = (
                direct_acquisition_map.get(filename)
                if same_response_controller
                and direct_acquisition_map is not None
                else outcome
            )
            valid_method = (
                explicit_outcome == "download_event"
                and outcome == explicit_outcome
                and export_chunks is None
                and isinstance(direct_item, dict)
                and direct_item.get("bytes") == len(data)
                and direct_item.get("sha256") == _sha256(data)
            )
        elif method == SAME_RESPONSE_TRANSPORT_METHOD:
            reconstructed_item = reconstructed_by_filename.get(filename)
            explicit_outcome = (
                direct_acquisition_map.get(filename)
                if direct_acquisition_map is not None
                else None
            )
            valid_method = (
                record_version == TRANSPORT_RECORD_VERSION
                and same_response_controller
                and explicit_outcome in {"unavailable", "no_download_event"}
                and outcome == explicit_outcome
                and export_chunks is None
                and filename not in observed_direct_by_filename
                and isinstance(reconstructed_item, dict)
                and reconstructed_item.get("bytes") == len(data)
                and reconstructed_item.get("sha256") == _sha256(data)
            )
        elif method == "chunked_base64_export":
            valid_method = (
                record_version == LEGACY_TRANSPORT_RECORD_VERSION
                and not same_response_controller
                and outcome in {"unavailable", "no_download_event"}
                and isinstance(export_chunks, list)
                and bool(export_chunks)
            )
            if valid_method:
                assert isinstance(export_chunks, list)
                expected_chunks = [
                    f"{filename}{ACTIVE_EXPORT_SUFFIX}{index:05d}.json"
                    for index in range(len(export_chunks))
                ]
                if (
                    export_chunks != expected_chunks
                    or any(
                        not isinstance(chunk_name, str)
                        for chunk_name in export_chunks
                    )
                ):
                    valid_method = False
                else:
                    for chunk_name in export_chunks:
                        if _safe_file(root, chunk_name) is None:
                            _add_finding(
                                findings,
                                "ARTIFACT_TRANSPORT_CHUNK_MISSING",
                                label,
                                (
                                    "transport record references a missing, unsafe, "
                                    f"or non-regular chunk wrapper: {chunk_name}"
                                ),
                            )
                            _set_check(
                                checks,
                                "artifact_transport",
                                "blocked",
                                chunk_name,
                            )
                    captured_names = [
                        name
                        for _, name in sorted(captured_chunks.get(filename, []))
                    ]
                    if export_chunks != captured_names:
                        _add_finding(
                            findings,
                            "ARTIFACT_TRANSPORT_CHUNK_ROSTER_MISMATCH",
                            label,
                            (
                                "successful chunk transport record must exactly "
                                "match the controller-bound indexed wrapper captures"
                            ),
                        )
                        _set_check(
                            checks,
                            "artifact_transport",
                            "blocked",
                            filename,
                        )
        else:
            valid_method = False
        if not valid_method:
            _add_finding(
                findings,
                "ARTIFACT_TRANSPORT_METHOD_INVALID",
                label,
                (
                    "direct download requires download_event and export_chunks=null; "
                    f"{SAME_RESPONSE_TRANSPORT_METHOD} requires a controller-v4 "
                    "reconstructed member, unavailable/no_download_event, and "
                    "export_chunks=null; "
                    "chunked Base64 requires unavailable/no_download_event and an "
                    "ordered, contiguous list of indexed wrapper filenames"
                ),
            )
            _set_check(checks, "artifact_transport", "blocked", filename)

    if same_response_controller and record_version == TRANSPORT_RECORD_VERSION:
        expected_v4_record_names = (
            set(reconstructed_by_filename) | set(observed_direct_by_filename)
        )
        if set(records) != expected_v4_record_names:
            _add_finding(
                findings,
                "ARTIFACT_TRANSPORT_RECONSTRUCTED_ROSTER_MISMATCH",
                f"{path.name}:$.records",
                (
                    "transport records must exactly cover the union of "
                    "controller-bound direct bytes and reconstructed outputs"
                ),
            )
            _set_check(checks, "artifact_transport", "blocked")

    missing = sorted(expected - set(records))
    if missing and not allow_incomplete_candidate_capture:
        _add_finding(
            findings,
            "ARTIFACT_TRANSPORT_COVERAGE_MISSING",
            f"{path.name}:$.records",
            "every generated or returned artifact requires one transport record",
        )
        _set_check(checks, "artifact_transport", "blocked", f"missing={missing!r}")

    if checks["artifact_transport"]["status"] == "not_run":
        _set_check(checks, "artifact_transport", "pass")
    return records


def _verify_same_response_candidate_transport(
    *,
    root: Path,
    controller_record: dict[str, Any],
    required_output_filenames: set[str],
    actual_output_filenames: set[str],
    observed_output_controls: set[str],
    transport_records: dict[str, dict[str, Any]],
    findings: list[dict[str, str]],
    checks: dict[str, dict[str, Any]],
) -> bool:
    """Classify controller-valid same-response transport as candidate evidence.

    The controller validator owns raw-response and parser identity. This layer
    treats a faithfully recorded compiler failure as candidate evidence rather
    than converting it into an invalid trial.
    """

    if not _uses_same_response_transport(controller_record):
        return False
    capture = controller_record.get("compiler_transport_capture")
    reconstructed = controller_record.get("reconstructed_outputs")
    status = capture.get("status") if isinstance(capture, dict) else None
    reconstructed_names = {
        item["filename"]
        for item in reconstructed
        if isinstance(item, dict) and isinstance(item.get("filename"), str)
    } if isinstance(reconstructed, list) else set()
    observed_direct = controller_record.get("observed_outputs")
    direct_names = {
        item["filename"]
        for item in observed_direct
        if isinstance(item, dict) and isinstance(item.get("filename"), str)
    } if isinstance(observed_direct, list) else set()
    applicable = bool(
        required_output_filenames
        or actual_output_filenames
        or observed_output_controls
        or reconstructed_names
        or direct_names
        or transport_records
        or status not in {None, "missing"}
    )
    if not applicable:
        if checks["export_wrappers"]["status"] == "not_run":
            _set_check(
                checks,
                "export_wrappers",
                "pass",
                "same-response transport was not required for this frozen case",
            )
        return False

    if status != "verified":
        suffix = (
            status.upper()
            if isinstance(status, str) and re.fullmatch(r"[a-z_]+", status)
            else "INVALID"
        )
        _add_finding(
            findings,
            f"CANDIDATE_COMPILER_TRANSPORT_{suffix}",
            "controller_record.json:$.compiler_transport_capture",
            (
                "the controller faithfully preserved a candidate same-response "
                f"compiler transport outcome of {status!r}; exact payload identity "
                "remains unresolved and no corruption or equality claim is made"
            ),
        )
        _set_check(
            checks,
            "export_wrappers",
            "blocked",
            f"same-response compiler transport status={status!r}",
        )
        return True

    expected_transport_names = reconstructed_names | direct_names
    missing_records = sorted(expected_transport_names - set(transport_records))
    if missing_records:
        _add_finding(
            findings,
            "CANDIDATE_TRANSPORT_COVERAGE_MISSING",
            "artifact_transport.json:$.records",
            (
                "verified same-response reconstruction lacks transport records "
                f"for locally materialized outputs: {missing_records!r}"
            ),
        )
        _set_check(
            checks,
            "export_wrappers",
            "blocked",
            f"missing transport records={missing_records!r}",
        )
    elif reconstructed_names != actual_output_filenames:
        _add_finding(
            findings,
            "CANDIDATE_RECONSTRUCTED_OUTPUT_ROSTER_MISMATCH",
            "controller_record.json:$.reconstructed_outputs",
            (
                "controller-bound reconstructed output names differ from the "
                "independently inventoried local member bytes"
            ),
        )
        _set_check(checks, "export_wrappers", "blocked")
    else:
        for filename in sorted(reconstructed_names):
            record = transport_records.get(filename)
            expected_method = (
                "direct_download"
                if filename in direct_names
                else SAME_RESPONSE_TRANSPORT_METHOD
            )
            if not isinstance(record, dict) or record.get("method") != expected_method:
                _add_finding(
                    findings,
                    "CANDIDATE_TRANSPORT_PRIMARY_METHOD_MISMATCH",
                    f"artifact_transport.json:{filename}",
                    (
                        "exact direct-download bytes are primary when captured; "
                        "same-response reconstruction is the fallback"
                    ),
                )
                _set_check(checks, "export_wrappers", "blocked", filename)
                continue
            if filename in direct_names:
                direct_path = _safe_file(root, filename)
                bundle_path = _safe_file(
                    root / RECONSTRUCTED_OUTPUT_DIRECTORY,
                    filename,
                )
                if direct_path is None or bundle_path is None:
                    _add_finding(
                        findings,
                        "CANDIDATE_DIRECT_BUNDLE_CAPTURE_MISSING",
                        filename,
                        "direct and reconstructed copies must both be preserved",
                    )
                    _set_check(checks, "export_wrappers", "blocked", filename)
                    continue
                try:
                    direct_data = direct_path.read_bytes()
                    bundle_data = bundle_path.read_bytes()
                except OSError:
                    direct_data = b""
                    bundle_data = b"\x00"
                if direct_data != bundle_data:
                    _add_finding(
                        findings,
                        "CANDIDATE_DIRECT_BUNDLE_MISMATCH",
                        filename,
                        (
                            "captured download bytes differ from the exact "
                            "same-response reconstructed member"
                        ),
                    )
                    _set_check(checks, "export_wrappers", "blocked", filename)
        if checks["export_wrappers"]["status"] == "not_run":
            _set_check(
                checks,
                "export_wrappers",
                "pass",
                (
                    "direct bytes were primary where captured and every remaining "
                    "member used the exact same-response reconstruction"
                ),
            )
    return True


def _strict_chunk_hash(value: Any) -> str | None:
    if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value):
        return value
    return None


def _bounded_zlib_decompress(
    encoded: bytes,
    *,
    declared_size: int,
) -> tuple[bytes | None, str | None]:
    if declared_size > MAX_TRANSPORT_PAYLOAD_BYTES:
        return None, "declared payload exceeds the bounded decompression limit"
    try:
        decompressor = zlib.decompressobj()
        payload = decompressor.decompress(
            encoded,
            MAX_TRANSPORT_PAYLOAD_BYTES + 1,
        )
        if len(payload) > MAX_TRANSPORT_PAYLOAD_BYTES:
            return None, "decompressed payload exceeds the bounded decompression limit"
        if decompressor.unconsumed_tail:
            return None, "compressed stream exceeds the bounded decompression limit"
        payload += decompressor.flush(
            MAX_TRANSPORT_PAYLOAD_BYTES + 1 - len(payload)
        )
    except zlib.error:
        return None, "encoded aggregate is not one valid zlib stream"
    if len(payload) > MAX_TRANSPORT_PAYLOAD_BYTES:
        return None, "decompressed payload exceeds the bounded decompression limit"
    if not decompressor.eof:
        return None, "encoded aggregate ends before the zlib stream is complete"
    if decompressor.unused_data:
        return None, "encoded aggregate has trailing or concatenated stream bytes"
    return payload, None


def _verify_export_chunks(
    root: Path,
    report: tuple[Path, str] | None,
    transport_records: dict[str, dict[str, Any]],
    controller_record: dict[str, Any],
    findings: list[dict[str, str]],
    checks: dict[str, dict[str, Any]],
) -> None:
    report_filename = report[0].name if report else None
    captured_by_payload: dict[str, list[tuple[int, str]]] = {}
    captures = controller_record.get("wrapper_captures")
    if isinstance(captures, list):
        for capture in captures:
            if not isinstance(capture, dict):
                continue
            payload = capture.get("payload_filename")
            chunk_index = capture.get("chunk_index")
            parser_name = capture.get("parser_input_filename")
            if (
                isinstance(payload, str)
                and isinstance(chunk_index, int)
                and not isinstance(chunk_index, bool)
                and isinstance(parser_name, str)
            ):
                captured_by_payload.setdefault(payload, []).append(
                    (chunk_index, parser_name)
                )

    attempts = controller_record.get("transport_attempts")
    if isinstance(attempts, list):
        for attempt in attempts:
            if (
                isinstance(attempt, dict)
                and attempt.get("response_outcome") != "chunk_wrapper_captured"
            ):
                payload = attempt.get("payload_filename")
                chunk_index = attempt.get("chunk_index")
                outcome = attempt.get("response_outcome")
                _add_finding(
                    findings,
                    "CANDIDATE_TRANSPORT_ATTEMPT_FAILED",
                    (
                        f"{payload}.transport.{chunk_index:05d}"
                        if isinstance(payload, str)
                        and isinstance(chunk_index, int)
                        and not isinstance(chunk_index, bool)
                        else "controller_record.json:$.transport_attempts"
                    ),
                    (
                        "the exact fallback attempt completed without one captured "
                        f"chunk wrapper (outcome={outcome!r}); payload identity "
                        "remains unresolved"
                    ),
                )
                _set_check(
                    checks,
                    "export_wrappers",
                    "blocked",
                    f"{payload}: {outcome}",
                )

    for payload_filename, indexed_names in sorted(captured_by_payload.items()):
        indexed_names.sort()
        captured_indices = [index for index, _ in indexed_names]
        chunk_names = [name for _, name in indexed_names]
        wrappers: list[tuple[str, dict[str, Any], bytes]] = []
        expected_payload_size: int | None = None
        expected_payload_hash: str | None = None
        expected_encoded_size: int | None = None
        expected_encoded_hash: str | None = None
        expected_chunk_count: int | None = None
        encoded_parts: list[bytes] = []

        for position, chunk_name in enumerate(chunk_names):
            if not isinstance(chunk_name, str):
                continue
            wrapper_path = _safe_file(root, chunk_name)
            if wrapper_path is None:
                continue
            wrapper = _load_json_path(
                root,
                wrapper_path,
                findings,
                checks,
                "export_wrappers",
            )
            if wrapper is None:
                continue
            if set(wrapper) != EXPORT_CHUNK_FIELDS:
                _add_finding(
                    findings,
                    "EXPORT_CHUNK_FIELDS_INVALID",
                    chunk_name,
                    "export chunk fields differ from the strict chunk contract",
                )
                _set_check(checks, "export_wrappers", "blocked", chunk_name)
            if (
                wrapper.get("transport_version") != TRANSPORT_CHUNK_VERSION
                or wrapper.get("encoding") != TRANSPORT_ENCODING
                or wrapper.get("filename") != payload_filename
            ):
                _add_finding(
                    findings,
                    "EXPORT_CHUNK_IDENTITY_INVALID",
                    chunk_name,
                    "chunk transport version, encoding, or payload filename is invalid",
                )
                _set_check(checks, "export_wrappers", "blocked", chunk_name)

            payload_size = wrapper.get("payload_size_bytes")
            encoded_size = wrapper.get("encoded_size_bytes")
            chunk_index = wrapper.get("chunk_index")
            chunk_count = wrapper.get("chunk_count")
            offset = wrapper.get("offset_bytes")
            chunk_size = wrapper.get("chunk_size_bytes")
            payload_hash = _strict_chunk_hash(wrapper.get("payload_sha256"))
            encoded_hash = _strict_chunk_hash(wrapper.get("encoded_sha256"))
            chunk_hash = _strict_chunk_hash(wrapper.get("chunk_sha256"))
            encoded_size_valid = (
                isinstance(encoded_size, int)
                and not isinstance(encoded_size, bool)
                and 0 < encoded_size <= MAX_TRANSPORT_ENCODED_BYTES
            )
            calculated_chunk_count = (
                (encoded_size + TRANSPORT_CHUNK_BYTES - 1)
                // TRANSPORT_CHUNK_BYTES
                if encoded_size_valid
                else None
            )
            calculated_chunk_size = (
                min(
                    TRANSPORT_CHUNK_BYTES,
                    encoded_size - position * TRANSPORT_CHUNK_BYTES,
                )
                if encoded_size_valid
                else None
            )
            integer_fields_valid = (
                isinstance(payload_size, int)
                and not isinstance(payload_size, bool)
                and 0 <= payload_size <= MAX_TRANSPORT_PAYLOAD_BYTES
                and encoded_size_valid
                and isinstance(chunk_index, int)
                and not isinstance(chunk_index, bool)
                and chunk_index == position
                and isinstance(chunk_count, int)
                and not isinstance(chunk_count, bool)
                and chunk_count == calculated_chunk_count
                and position < chunk_count
                and isinstance(offset, int)
                and not isinstance(offset, bool)
                and offset == position * TRANSPORT_CHUNK_BYTES
                and isinstance(chunk_size, int)
                and not isinstance(chunk_size, bool)
                and chunk_size == calculated_chunk_size
                and chunk_size > 0
            )
            if not integer_fields_valid or None in {
                payload_hash,
                encoded_hash,
                chunk_hash,
            }:
                _add_finding(
                    findings,
                    "EXPORT_CHUNK_METADATA_INVALID",
                    chunk_name,
                    (
                        "chunk indices, counts, offsets, bounded sizes, and lowercase "
                        "SHA-256 values must match the strict chunk contract"
                    ),
                )
                _set_check(checks, "export_wrappers", "blocked", chunk_name)

            encoded_text = wrapper.get("base64")
            decoded_chunk: bytes | None = None
            max_base64_chars = ((TRANSPORT_CHUNK_BYTES + 2) // 3) * 4
            if (
                isinstance(encoded_text, str)
                and encoded_text.isascii()
                and len(encoded_text) <= max_base64_chars
            ):
                try:
                    decoded_chunk = base64.b64decode(encoded_text, validate=True)
                    if base64.b64encode(decoded_chunk).decode("ascii") != encoded_text:
                        raise binascii.Error("non-canonical Base64")
                except (binascii.Error, ValueError):
                    decoded_chunk = None
            if decoded_chunk is None:
                _add_finding(
                    findings,
                    "EXPORT_CHUNK_BASE64_INVALID",
                    chunk_name,
                    "chunk Base64 must be strict and canonical",
                )
                _set_check(checks, "export_wrappers", "blocked", chunk_name)
            elif (
                not isinstance(chunk_size, int)
                or isinstance(chunk_size, bool)
                or chunk_size != len(decoded_chunk)
                or chunk_hash != _sha256(decoded_chunk)
                or (
                    isinstance(calculated_chunk_size, int)
                    and len(decoded_chunk) != calculated_chunk_size
                )
            ):
                _add_finding(
                    findings,
                    "EXPORT_CHUNK_BYTE_BINDING_MISMATCH",
                    chunk_name,
                    "decoded chunk bytes differ from their declared size or digest",
                )
                _set_check(checks, "export_wrappers", "blocked", chunk_name)

            if position == 0:
                expected_payload_size = (
                    payload_size
                    if isinstance(payload_size, int)
                    and not isinstance(payload_size, bool)
                    else None
                )
                expected_payload_hash = payload_hash
                expected_encoded_size = (
                    encoded_size
                    if encoded_size_valid
                    else None
                )
                expected_encoded_hash = encoded_hash
                expected_chunk_count = (
                    chunk_count
                    if isinstance(chunk_count, int)
                    and not isinstance(chunk_count, bool)
                    and chunk_count == calculated_chunk_count
                    else None
                )
            elif (
                payload_size != expected_payload_size
                or payload_hash != expected_payload_hash
                or encoded_size != expected_encoded_size
                or encoded_hash != expected_encoded_hash
            ):
                _add_finding(
                    findings,
                    "EXPORT_CHUNK_REPEATED_IDENTITY_MISMATCH",
                    chunk_name,
                    (
                        "every chunk must repeat one identical payload and encoded "
                        "stream identity"
                    ),
                )
                _set_check(checks, "export_wrappers", "blocked", chunk_name)

            if decoded_chunk is not None:
                encoded_parts.append(decoded_chunk)
            wrappers.append((chunk_name, wrapper, decoded_chunk or b""))

        if len(wrappers) != len(chunk_names):
            continue
        sequence_complete = (
            expected_chunk_count is not None
            and captured_indices == list(range(expected_chunk_count))
        )
        if not sequence_complete:
            # A valid captured prefix followed by an exact terminal failed attempt
            # is candidate evidence, but it is not a false aggregate mismatch.
            continue
        encoded = b"".join(encoded_parts)
        aggregate_valid = (
            expected_encoded_size is not None
            and expected_encoded_hash is not None
            and len(encoded) == expected_encoded_size
            and _sha256(encoded) == expected_encoded_hash
        )
        if not aggregate_valid:
            _add_finding(
                findings,
                "EXPORT_ENCODED_AGGREGATE_MISMATCH",
                payload_filename,
                "concatenated compressed chunks differ from the repeated encoded identity",
            )
            _set_check(checks, "export_wrappers", "blocked", payload_filename)

        payload: bytes | None = None
        if aggregate_valid and expected_payload_size is not None:
            payload, decompression_error = _bounded_zlib_decompress(
                encoded,
                declared_size=expected_payload_size,
            )
            if decompression_error is not None:
                _add_finding(
                    findings,
                    "EXPORT_ZLIB_STREAM_INVALID",
                    payload_filename,
                    decompression_error,
                )
                _set_check(checks, "export_wrappers", "blocked", payload_filename)
        if payload is not None and (
            len(payload) != expected_payload_size
            or expected_payload_hash is None
            or _sha256(payload) != expected_payload_hash
        ):
            _add_finding(
                findings,
                "EXPORT_PAYLOAD_IDENTITY_MISMATCH",
                payload_filename,
                "decompressed payload differs from the repeated payload identity",
            )
            _set_check(checks, "export_wrappers", "blocked", payload_filename)
            payload = None

        local_path = _safe_file(root, payload_filename)
        try:
            local_bytes = local_path.read_bytes() if local_path is not None else None
        except OSError:
            local_bytes = None
        if payload is not None and local_bytes != payload:
            code = (
                "REPORT_TRANSPORT_MISMATCH"
                if payload_filename == report_filename
                else "EXPORT_LOCAL_BYTE_MISMATCH"
            )
            _add_finding(
                findings,
                code,
                payload_filename,
                (
                    "reconstructed report bytes differ from the bound local report"
                    if payload_filename == report_filename
                    else "reconstructed payload differs from the local file bytes"
                ),
            )
            _set_check(checks, "export_wrappers", "blocked", payload_filename)
        if payload is not None:
            _decode_text(
                payload,
                f"{payload_filename}:reconstructed",
                findings,
                checks,
            )


def _verify_version_literal(
    root: Path,
    audit_return: dict[str, Any],
    artifacts: dict[str, tuple[Path, bytes, str | None]],
    report: tuple[Path, str] | None,
    findings: list[dict[str, str]],
    checks: dict[str, dict[str, Any]],
) -> None:
    execution = audit_return.get("execution")
    records = (
        [
            item
            for item in execution
            if isinstance(item, dict) and item.get("activity") == "chatgpt_data_analysis"
        ]
        if isinstance(execution, list)
        else []
    )
    if len(records) != 1:
        _add_finding(
            findings,
            "CHATGPT_DATA_ANALYSIS_RECORD_INVALID",
            "audit_return.json:$.execution",
            "exactly one chatgpt_data_analysis execution record is required",
        )
        _set_check(checks, "chatgpt_data_analysis_version", "blocked")
        return
    record = records[0]
    version = record.get("version")
    if (
        record.get("status") != "ran"
        or not isinstance(version, str)
        or SYS_VERSION_RE.fullmatch(version) is None
    ):
        _add_finding(
            findings,
            "CHATGPT_DATA_ANALYSIS_VERSION_NOT_EXACT",
            "audit_return.json:$.execution[chatgpt_data_analysis].version",
            "a ran ChatGPT Data Analysis activity must record the complete sys.version-shaped session-reported runtime",
        )
        _set_check(checks, "chatgpt_data_analysis_version", "blocked")
        return

    artifact_records = {
        item.get("id"): item
        for item in audit_return.get("artifacts", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    output_ids = record.get("output_artifact_ids")
    output_ids = output_ids if isinstance(output_ids, list) else []
    ledger_records = [
        item
        for item in artifact_records.values()
        if item.get("filename") == BOUND_RUNTIME_ARTIFACT
        and item.get("role") == "execution_output"
    ]
    ledger_text: str | None = None
    ledger_id: str | None = None
    if len(ledger_records) != 1:
        _add_finding(
            findings,
            "CHATGPT_DATA_ANALYSIS_OUTPUT_ARTIFACT_INVALID",
            "audit_return.json:$.artifacts",
            f"exactly one role-execution_output artifact named {BOUND_RUNTIME_ARTIFACT} is required",
        )
        _set_check(checks, "chatgpt_data_analysis_output", "blocked")
    else:
        ledger_id = ledger_records[0]["id"]
        if ledger_id not in output_ids:
            _add_finding(
                findings,
                "CHATGPT_DATA_ANALYSIS_OUTPUT_BINDING_MISSING",
                "audit_return.json:$.execution[chatgpt_data_analysis].output_artifact_ids",
                "the dedicated Data Analysis output artifact must be bound as an output",
            )
            _set_check(checks, "chatgpt_data_analysis_output", "blocked")
        artifact = artifacts.get(ledger_id)
        if artifact is None or artifact[2] is None:
            _add_finding(
                findings,
                "CHATGPT_DATA_ANALYSIS_OUTPUT_UNVERIFIED",
                BOUND_RUNTIME_ARTIFACT,
                "the dedicated Data Analysis output artifact must exist, hash-match, and decode as strict UTF-8",
            )
            _set_check(checks, "chatgpt_data_analysis_output", "blocked")
        else:
            ledger_text = artifact[2]
            own_hash = ledger_records[0].get("sha256")
            if isinstance(own_hash, str) and own_hash in ledger_text:
                _add_finding(
                    findings,
                    "CHATGPT_DATA_ANALYSIS_OUTPUT_SELF_HASHED",
                    BOUND_RUNTIME_ARTIFACT,
                    "the Data Analysis output ledger must not claim its own final digest",
                )
                _set_check(checks, "chatgpt_data_analysis_output", "blocked")
            expected_ledger_records: list[dict[str, Any]] = []
            unavailable_output_ids: list[str] = []
            for output_id in output_ids:
                if output_id == ledger_id:
                    continue
                declared_output = artifact_records.get(output_id)
                bound_output = artifacts.get(output_id)
                filename = (
                    declared_output.get("filename")
                    if isinstance(declared_output, dict)
                    else None
                )
                if (
                    not isinstance(filename, str)
                    or bound_output is None
                ):
                    unavailable_output_ids.append(str(output_id))
                    continue
                expected_ledger_records.append(
                    output_record(filename, bound_output[1])
                )
            try:
                captured_runtime, observed_ledger_records = parse_runtime_ledger(
                    ledger_text
                )
            except ValueError as exc:
                _add_finding(
                    findings,
                    "CHATGPT_DATA_ANALYSIS_RUNTIME_BINDING_INVALID",
                    BOUND_RUNTIME_ARTIFACT,
                    str(exc),
                )
                captured_runtime = None
                _set_check(
                    checks,
                    "chatgpt_data_analysis_version",
                    "blocked",
                )
                _set_check(checks, "chatgpt_data_analysis_output", "blocked")
            else:
                expected_ledger_records.sort(key=lambda item: item["filename"])
                if (
                    unavailable_output_ids
                    or tuple(expected_ledger_records) != observed_ledger_records
                ):
                    _add_finding(
                        findings,
                        "CHATGPT_DATA_ANALYSIS_OUTPUT_LEDGER_ROSTER_MISMATCH",
                        BOUND_RUNTIME_ARTIFACT,
                        (
                            "runtime ledger rows must exactly equal every other bound "
                            "execution output filename, byte count, and SHA-256"
                        ),
                    )
                    _set_check(
                        checks,
                        "chatgpt_data_analysis_output",
                        "blocked",
                        f"unavailable output IDs: {unavailable_output_ids!r}",
                    )
                elif checks["chatgpt_data_analysis_output"]["status"] == "not_run":
                    _set_check(checks, "chatgpt_data_analysis_output", "pass")
            if captured_runtime is not None:
                if captured_runtime != version or ledger_text.count(version) != 1:
                    _add_finding(
                        findings,
                        "CHATGPT_DATA_ANALYSIS_VERSION_MISMATCH",
                        BOUND_RUNTIME_ARTIFACT,
                        "structured return runtime differs from the one session-reported value in the bound execution output",
                    )
                    _set_check(
                        checks,
                        "chatgpt_data_analysis_version",
                        "blocked",
                    )

    texts: dict[str, str] = {}
    for identifier, artifact_record in artifact_records.items():
        if (
            artifact_record.get("role") in {"request", "source"}
            or artifact_record.get("filename") == BOUND_RUNTIME_ARTIFACT
        ):
            continue
        bound_artifact = artifacts.get(identifier)
        if bound_artifact is not None and bound_artifact[2] is not None:
            texts[str(artifact_record.get("filename"))] = bound_artifact[2]

    if report is None:
        _set_check(
            checks,
            "chatgpt_data_analysis_version",
            "blocked",
            "bound report unavailable",
        )
    else:
        texts[report[0].name] = report[1]
    for label, text in _audit_return_string_values(
        audit_return,
        structured_runtime_record=record,
    ):
        texts[label] = text

    raw_path = _safe_repo_relative_file(root, RAW_RESPONSE_FILENAME)
    if raw_path is None:
        _add_finding(
            findings,
            "RAW_RESPONSE_MISSING_OR_UNSAFE",
            RAW_RESPONSE_FILENAME,
            "the complete assistant outerHTML capture is missing or unsafe",
        )
        _set_check(
            checks,
            "chatgpt_data_analysis_version",
            "blocked",
            "raw response unavailable",
        )
    else:
        try:
            raw_bytes = raw_path.read_bytes()
        except OSError:
            raw_bytes = b""
            _add_finding(
                findings,
                "RAW_RESPONSE_UNREADABLE",
                RAW_RESPONSE_FILENAME,
                "the complete assistant outerHTML capture is unreadable",
            )
            _set_check(
                checks,
                "chatgpt_data_analysis_version",
                "blocked",
                "raw response unreadable",
            )
        raw_text = _decode_text(
            raw_bytes,
            RAW_RESPONSE_FILENAME,
            findings,
            checks,
        )
        if raw_text is not None:
            texts[RAW_RESPONSE_FILENAME] = html.unescape(raw_text)

    visible_path = root / "visible_response_dom.txt"
    if visible_path.exists():
        if not visible_path.is_file():
            _add_finding(
                findings,
                "VISIBLE_RESPONSE_INVALID",
                visible_path.name,
                "visible_response_dom.txt is not a regular file",
            )
            _set_check(checks, "chatgpt_data_analysis_version", "blocked", visible_path.name)
        else:
            try:
                visible_bytes = visible_path.read_bytes()
            except OSError:
                visible_bytes = b""
                _add_finding(
                    findings,
                    "VISIBLE_RESPONSE_UNREADABLE",
                    visible_path.name,
                    "visible_response_dom.txt cannot be read",
                )
                _set_check(checks, "chatgpt_data_analysis_version", "blocked", visible_path.name)
            visible_text = _decode_text(visible_bytes, visible_path.name, findings, checks)
            if visible_text is not None:
                texts[visible_path.name] = visible_text
    else:
        _add_finding(
            findings,
            "VISIBLE_RESPONSE_MISSING",
            visible_path.name,
            "a frozen evaluation bundle requires the preserved visible terminal response",
        )
        _set_check(
            checks,
            "visible_response_version",
            "blocked",
            "visible_response_dom.txt not present",
        )

    report_label = report[0].name if report is not None else None
    for label, text in texts.items():
        observed = set(SYS_VERSION_RE.findall(text))
        if observed and observed != {version}:
            _add_finding(
                findings,
                "CHATGPT_DATA_ANALYSIS_VERSION_MISMATCH",
                label,
                "an optional prose runtime literal contradicts the one bound session-reported value",
            )
            _set_check(
                checks,
                "chatgpt_data_analysis_version",
                "blocked",
                f"{label}: observed={sorted(observed)!r}",
            )
            if label == "visible_response_dom.txt":
                _set_check(
                    checks,
                    "visible_response_version",
                    "blocked",
                    f"observed={sorted(observed)!r}",
                )
            continue
        if observed:
            _add_finding(
                findings,
                "CHATGPT_DATA_ANALYSIS_RUNTIME_LITERAL_PROHIBITED",
                label,
                (
                    "model-authored prose must reference the bound runtime output; "
                    "it may not independently reproduce even the matching runtime literal"
                ),
            )
            _set_check(
                checks,
                "chatgpt_data_analysis_version",
                "blocked",
                f"{label}: runtime literal reproduced",
            )
            if label == "visible_response_dom.txt":
                _set_check(
                    checks,
                    "visible_response_version",
                    "blocked",
                    "runtime literal reproduced",
                )
        if label == report_label and BOUND_RUNTIME_ARTIFACT not in text:
            _add_finding(
                findings,
                "CHATGPT_DATA_ANALYSIS_RUNTIME_REFERENCE_MISSING",
                label,
                f"the report must reference {BOUND_RUNTIME_ARTIFACT} as the bound runtime source",
            )
            _set_check(
                checks,
                "chatgpt_data_analysis_version",
                "blocked",
                f"{label}: bound runtime reference absent",
            )
        if label == "visible_response_dom.txt" and not (
            observed and observed != {version}
        ):
            _set_check(checks, "visible_response_version", "pass")


def _invoke_return_desk(
    audit_return_path: Path,
    findings: list[dict[str, str]],
    checks: dict[str, dict[str, Any]],
    *,
    source_root: Path | None = None,
) -> dict[str, Any] | None:
    temporary: tempfile.TemporaryDirectory[str] | None = None
    verification_path = audit_return_path
    if source_root is not None and audit_return_path.parent != source_root:
        try:
            document = _strict_json(audit_return_path.read_text(encoding="utf-8"))
            artifact_rows = document.get("artifacts")
            if isinstance(artifact_rows, list):
                temporary = tempfile.TemporaryDirectory()
                verification_root = Path(temporary.name)
                verification_path = verification_root / audit_return_path.name
                verification_path.write_bytes(audit_return_path.read_bytes())
                for item in artifact_rows:
                    if not isinstance(item, dict):
                        continue
                    filename = item.get("filename")
                    candidate = _safe_file(audit_return_path.parent, filename)
                    if candidate is None and item.get("role") == "source":
                        candidate = _safe_file(source_root, filename)
                    if candidate is not None:
                        (verification_root / candidate.name).write_bytes(
                            candidate.read_bytes()
                        )
        except (OSError, StrictJsonError):
            verification_path = audit_return_path
    output = io.StringIO()
    try:
        with redirect_stdout(output):
            exit_status = bsc_audit_main(["return-desk", str(verification_path)])
        result = _strict_json(output.getvalue())
    except Exception as exc:  # pragma: no cover - last-resort checker boundary
        _add_finding(
            findings,
            "RETURN_DESK_INVOCATION_FAILED",
            audit_return_path.name,
            f"Python Return Desk invocation failed ({type(exc).__name__})",
        )
        _set_check(checks, "python_return_desk", "blocked")
        if temporary is not None:
            temporary.cleanup()
        return None
    if temporary is not None:
        temporary.cleanup()
    decision = result.get("decision") if isinstance(result, dict) else None
    severities = {
        item.get("severity")
        for item in result.get("findings", [])
        if isinstance(item, dict)
    } if isinstance(result, dict) else {"ERROR"}
    if (
        exit_status != 0
        or not isinstance(decision, str)
        or not decision.startswith("no_blocking_findings")
        or bool(severities & {"ERROR", "BLOCKED"})
    ):
        _add_finding(
            findings,
            "RETURN_DESK_BLOCKED",
            audit_return_path.name,
            "Python Return Desk reported a blocking or malformed result",
        )
        _set_check(
            checks,
            "python_return_desk",
            "blocked",
            f"exit={exit_status}; decision={decision}",
        )
    else:
        _set_check(
            checks,
            "python_return_desk",
            "pass",
            f"decision={decision}",
        )
    return {
        "exit_code": exit_status,
        "decision": decision,
        "findings": result.get("findings", []) if isinstance(result, dict) else [],
    }


def _verify_expectations(
    root: Path,
    expectations: dict[str, str | None],
    findings: list[dict[str, str]],
    checks: dict[str, dict[str, Any]],
) -> None:
    for name, filename in EXPECTATION_FILES.items():
        expected_value = expectations.get(name)
        check_name = f"expected_{name}"
        if expected_value is None:
            _set_check(checks, check_name, "not_run", "expectation argument not supplied")
            continue
        expected = _digest(expected_value)
        if expected is None:
            _add_finding(
                findings,
                "EXPECTATION_HASH_INVALID",
                filename,
                "expected SHA-256 must be 64 hexadecimal characters with an optional sha256: prefix",
            )
            _set_check(checks, check_name, "blocked")
            continue
        path = _safe_file(root, filename)
        if path is None:
            _add_finding(
                findings,
                "EXPECTED_COPY_MISSING_OR_UNSAFE",
                filename,
                "expected copied GPT source file is missing or unsafe",
            )
            _set_check(checks, check_name, "blocked")
            continue
        try:
            data = path.read_bytes()
        except OSError:
            data = b""
            _add_finding(
                findings,
                "EXPECTED_COPY_UNREADABLE",
                filename,
                "expected copied GPT source file cannot be read",
            )
            _set_check(checks, check_name, "blocked")
        _decode_text(data, filename, findings, checks)
        if _sha256(data) != expected:
            _add_finding(
                findings,
                "EXPECTED_COPY_HASH_MISMATCH",
                filename,
                "copied GPT source bytes do not match the supplied expected SHA-256",
            )
            _set_check(checks, check_name, "blocked")
        else:
            _set_check(checks, check_name, "pass")


def _load_score_result(
    root: Path,
    *,
    controller_record: dict[str, Any],
    case_id: str,
    trial_id: str,
    scoring_criteria: list[str],
    observable_behaviors: list[str],
    forbidden_behaviors: list[str],
    allowed_research_verdicts: list[str],
    research_projection_requirement: str,
    exact_research_projection: dict[str, Any] | None,
) -> tuple[str, dict[str, Any] | None, list[dict[str, str]]]:
    """Load a strict preserved manual score without trusting its total."""

    path = root / "score_result.json"
    if not path.is_file():
        return CANDIDATE_NOT_SCORED, None, []
    try:
        data = path.read_bytes()
        text = data.decode("utf-8", errors="strict")
        document = _strict_json(text)
    except (OSError, UnicodeError, StrictJsonError):
        return CANDIDATE_NOT_SCORED, None, [
            {
                "severity": "ERROR",
                "code": "CONTROLLER_SCORE_RESULT_INVALID",
                "path": "score_result.json",
                "message": "score result must be strict UTF-8 JSON",
            }
        ]
    if not isinstance(document, dict) or set(document) != SCORE_RESULT_FIELDS:
        return CANDIDATE_NOT_SCORED, None, [
            {
                "severity": "ERROR",
                "code": "CONTROLLER_SCORE_RESULT_INVALID",
                "path": "score_result.json:$",
                "message": "score-result fields differ from the frozen scoring contract",
            }
        ]
    dimensions = document.get("dimension_scores")
    observable = document.get("observable_behavior_results")
    forbidden = document.get("forbidden_behavior_results")
    projection = document.get("observed_research_projection")
    total = document.get("total_score")
    pre_score_path = root / "pre_score_controller.json"
    try:
        pre_score_bytes = pre_score_path.read_bytes()
        pre_score_document = _strict_json(
            pre_score_bytes.decode("utf-8", errors="strict")
        )
    except (OSError, UnicodeError, StrictJsonError):
        pre_score_bytes = b""
        pre_score_document = None
    expected_pre_digest = _digest(document.get("pre_score_controller_sha256"))
    stable_fields = CONTROLLER_RECORD_FIELDS - {"controller_artifacts"}
    current_controller_artifacts = controller_record.get("controller_artifacts")
    pre_controller_artifacts = (
        pre_score_document.get("controller_artifacts")
        if isinstance(pre_score_document, dict)
        else None
    )
    expected_base_controller_artifacts = (
        current_controller_artifacts[: len(CONTROLLER_ARTIFACT_FILENAMES)]
        if isinstance(current_controller_artifacts, list)
        else None
    )
    pre_score_binding_valid = (
        expected_pre_digest == _sha256(pre_score_bytes)
        and isinstance(pre_score_document, dict)
        and set(pre_score_document) == CONTROLLER_RECORD_FIELDS
        and all(
            pre_score_document.get(field) == controller_record.get(field)
            for field in stable_fields
        )
        and pre_controller_artifacts == expected_base_controller_artifacts
        and all(
            item.get("filename")
            not in {"pre_score_controller.json", "score_result.json"}
            for item in pre_controller_artifacts
            if isinstance(item, dict)
        )
    )
    valid_dimensions = (
        isinstance(dimensions, dict)
        and set(dimensions) == set(scoring_criteria)
        and all(
            not isinstance(value, bool)
            and isinstance(value, int)
            and 0 <= value <= 2
            for value in dimensions.values()
        )
    )
    recomputed_total = sum(dimensions.values()) if valid_dimensions else None
    valid_projection_shape = (
        isinstance(projection, dict)
        and all(
            isinstance(claim_id, str)
            and bool(claim_id)
            and isinstance(verdict, str)
            and bool(verdict)
            for claim_id, verdict in projection.items()
        )
    )
    scientific_projection = (
        research_projection_requirement
        == SCIENTIFIC_RESEARCH_PROJECTION_REQUIRED
    )
    recomputed_verdict_allowed: bool | None
    if valid_projection_shape and scientific_projection:
        recomputed_verdict_allowed = bool(projection) and all(
            verdict in allowed_research_verdicts for verdict in projection.values()
        )
    else:
        recomputed_verdict_allowed = None
    exact_projection_satisfied = True
    if (
        scientific_projection
        and valid_projection_shape
        and isinstance(exact_research_projection, dict)
    ):
        expected_projection = exact_research_projection["verdicts_by_claim"]
        exact_projection_satisfied = all(
            projection.get(claim_id) == verdict
            for claim_id, verdict in expected_projection.items()
        ) and (
            exact_research_projection["allow_additional_primary_claims"]
            or set(projection) == set(expected_projection)
        )
    recomputed_projection_contract_satisfied = (
        recomputed_verdict_allowed is True and exact_projection_satisfied
        if scientific_projection
        else valid_projection_shape and projection == {}
    )
    submitted_verdict_allowed = document.get("research_verdict_allowed")
    verdict_allowed_field_valid = (
        isinstance(submitted_verdict_allowed, bool)
        and submitted_verdict_allowed == recomputed_verdict_allowed
        if scientific_projection
        else submitted_verdict_allowed is None
    )
    valid = (
        document.get("score_result_version") == "2.0"
        and document.get("case_id") == case_id
        and document.get("trial_id") == trial_id
        and pre_score_binding_valid
        and valid_dimensions
        and not isinstance(total, bool)
        and isinstance(total, int)
        and total == recomputed_total
        and isinstance(document.get("automatic_failure"), bool)
        and isinstance(observable, dict)
        and set(observable) == set(observable_behaviors)
        and all(isinstance(value, bool) for value in observable.values())
        and isinstance(forbidden, dict)
        and set(forbidden) == set(forbidden_behaviors)
        and all(isinstance(value, bool) for value in forbidden.values())
        and valid_projection_shape
        and document.get("research_projection_requirement")
        == research_projection_requirement
        and verdict_allowed_field_valid
        and isinstance(
            document.get("research_projection_contract_satisfied"),
            bool,
        )
        and document["research_projection_contract_satisfied"]
        == recomputed_projection_contract_satisfied
        and isinstance(document.get("terminal_response_complete"), bool)
        and isinstance(document.get("scorer"), str)
        and bool(document["scorer"].strip())
        and isinstance(document.get("notes"), str)
    )
    if not valid:
        return CANDIDATE_NOT_SCORED, None, [
            {
                "severity": "ERROR",
                "code": "CONTROLLER_SCORE_RESULT_INVALID",
                "path": "score_result.json:$",
                "message": (
                    "score result must bind the case/trial, all ten 0-2 dimensions, "
                    "their recomputed total, every exact observable/forbidden behavior, "
                    "the exact scientific or status-only research projection contract, "
                    "terminal-response completeness, "
                    "and the immutable pre-score controller record"
                ),
            }
        ]
    candidate_passed = (
        total >= 18
        and document["automatic_failure"] is False
        and all(observable.values())
        and not any(forbidden.values())
        and document["research_projection_contract_satisfied"] is True
        and document["terminal_response_complete"] is True
    )
    summary = {
        "total_score": total,
        "pre_score_controller_sha256": expected_pre_digest,
        "dimension_scores": dimensions,
        "automatic_failure": document["automatic_failure"],
        "observable_behaviors_complete": all(observable.values()),
        "forbidden_behaviors_absent": not any(forbidden.values()),
        "observed_research_projection": projection,
        "research_projection_requirement": research_projection_requirement,
        "research_projection_exact_required": exact_research_projection is not None,
        "research_verdict_allowed": submitted_verdict_allowed,
        "research_projection_contract_satisfied": document[
            "research_projection_contract_satisfied"
        ],
        "terminal_response_complete": document["terminal_response_complete"],
        "scorer": document["scorer"],
    }
    return (
        CANDIDATE_PASSED if candidate_passed else CANDIDATE_FAILED,
        summary,
        [],
    )


def check_bundle(
    evidence_directory: Path,
    *,
    expected_case_id: str | None = None,
    expected_profile_sha256: str | None = None,
    expected_instructions_sha256: str | None = None,
    expected_eval_spec_sha256: str | None = None,
    candidate_source_root: Path | None = None,
) -> tuple[int, dict[str, Any]]:
    findings: list[dict[str, str]] = []
    checks: dict[str, dict[str, Any]] = {
        "evidence_directory": {"status": "not_run"},
        "controller_record": {"status": "not_run"},
        "controller_input_roster": {"status": "not_run"},
        "controller_candidate_identity": {"status": "not_run"},
        "controller_output_roster": {"status": "not_run"},
        "controller_parser_round_trip": {"status": "not_run"},
        "candidate_output_consistency": {"status": "not_run"},
        "audit_return_parse": {"status": "not_run"},
        "audit_return_artifacts": {"status": "not_run"},
        "text_sanitation": {"status": "pass"},
        "artifact_transport": {"status": "not_run"},
        "export_wrappers": {"status": "not_run"},
        "python_return_desk": {"status": "not_run"},
        "chatgpt_data_analysis_output": {"status": "not_run"},
        "chatgpt_data_analysis_version": {"status": "not_run"},
        "visible_response_version": {"status": "not_run"},
        "score_result": {"status": "not_run"},
        "expected_profile_hash": {"status": "not_run"},
        "expected_instructions_hash": {"status": "not_run"},
        "expected_eval_spec_hash": {"status": "not_run"},
    }
    return_desk_result: dict[str, Any] | None = None
    score_summary: dict[str, Any] | None = None
    controller_axis = TRIAL_INVALID_CONTROLLER
    candidate_axis = CANDIDATE_NOT_SCORED
    transport_axis = TRANSPORT_NOT_APPLICABLE
    transport_records: dict[str, dict[str, Any]] = {}
    observed_output_controls: set[str] = set()
    controller_record: dict[str, Any] | None = None
    source_root = ROOT
    source_root_error: str | None = None
    if candidate_source_root is not None:
        try:
            source_root = candidate_source_root.resolve(strict=True)
            if not source_root.is_dir():
                raise OSError("not a directory")
        except (FileNotFoundError, OSError, RuntimeError) as exc:
            source_root_error = (
                "candidate source root is unavailable, unsafe, or not a directory"
            )

    try:
        root = evidence_directory.resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError):
        root = evidence_directory.absolute()
    if not root.is_dir():
        _add_finding(
            findings,
            "EVIDENCE_DIRECTORY_INVALID",
            str(evidence_directory),
            "evidence directory does not exist or is not a directory",
        )
        _set_check(checks, "evidence_directory", "blocked")
        _set_check(checks, "controller_record", "blocked", "evidence directory invalid")
    else:
        _set_check(checks, "evidence_directory", "pass")
        controller_record, controller_issues = _load_controller_record(root)
        try:
            validate_closed_evidence_layout(evidence_directory)
        except (OSError, RuntimeError, ValueError) as exc:
            controller_issues.append(
                {
                    "severity": "ERROR",
                    "code": "CONTROLLER_EVIDENCE_LAYOUT_INVALID",
                    "path": ".",
                    "message": str(exc),
                }
            )
        if source_root_error is not None:
            controller_issues.append(
                {
                    "severity": "ERROR",
                    "code": "CONTROLLER_CANDIDATE_SOURCE_UNAVAILABLE",
                    "path": str(candidate_source_root),
                    "message": source_root_error,
                }
            )
        selected_case_id: str | None = None
        expected_inputs: list[dict[str, Any]] = []
        expected_prompt = b""
        required_outputs: set[str] = set()
        scoring_criteria: list[str] = []
        observable_behaviors: list[str] = []
        forbidden_behaviors: list[str] = []
        allowed_research_verdicts: list[str] = []
        research_projection_requirement = ""
        exact_research_projection: dict[str, Any] | None = None
        expected_identity: list[dict[str, Any]] = []
        actual_outputs: set[str] = set()

        if controller_record is not None:
            controls = controller_record.get("observed_output_controls")
            if (
                isinstance(controls, list)
                and all(isinstance(item, str) for item in controls)
            ):
                observed_output_controls = set(controls)
            selected_case_id = (
                expected_case_id
                if expected_case_id is not None
                else controller_record.get("case_id")
            )
        if not isinstance(selected_case_id, str) or not selected_case_id:
            controller_issues.append(
                {
                    "severity": "ERROR",
                    "code": "CONTROLLER_CASE_ID_INVALID",
                    "path": f"{CONTROLLER_RECORD_NAME}:$.case_id",
                    "message": "controller case identity must be a nonempty frozen case identifier",
                }
            )
        else:
            try:
                (
                    expected_inputs,
                    expected_prompt,
                    required_outputs,
                    scoring_criteria,
                    observable_behaviors,
                    forbidden_behaviors,
                    allowed_research_verdicts,
                    research_projection_requirement,
                    exact_research_projection,
                ) = _expected_case_context(selected_case_id, source_root)
                expected_identity = _expected_candidate_identity(source_root)
            except (OSError, StrictJsonError) as exc:
                controller_issues.append(
                    {
                        "severity": "ERROR",
                        "code": "CONTROLLER_EXPECTED_CONTEXT_UNAVAILABLE",
                        "path": CONTROLLER_RECORD_NAME,
                        "message": str(exc),
                    }
                )
            else:
                input_names = {item["filename"] for item in expected_inputs}
                actual_outputs = _actual_candidate_output_filenames(
                    root,
                    input_filenames=input_names,
                    controller_record=controller_record,
                )

        candidate_output_root = _candidate_output_root(root, controller_record)
        audit_return_path = candidate_output_root / "audit_return.json"
        audit_return: dict[str, Any] | None = None
        parse_findings: list[dict[str, str]] = []
        parse_checks: dict[str, dict[str, Any]] = {
            "audit_return_parse": {"status": "not_run"},
            "text_sanitation": {"status": "pass"},
        }
        if audit_return_path.is_file():
            audit_return = _load_json_path(
                root,
                audit_return_path,
                parse_findings,
                parse_checks,
                "audit_return_parse",
            )
            if audit_return is not None:
                _set_check(parse_checks, "audit_return_parse", "pass")
        elif "audit_return.json" in required_outputs:
            _set_check(
                parse_checks,
                "audit_return_parse",
                "not_run",
                (
                    "required audit_return.json bytes were not acquired; output-control "
                    "observation is classified after controller validation"
                ),
            )
        else:
            _set_check(
                parse_checks,
                "audit_return_parse",
                "not_run",
                "frozen case did not require a return envelope",
            )

        if (
            controller_record is not None
            and selected_case_id is not None
            and expected_inputs
            and expected_identity
        ):
            controller_issues.extend(
                validate_controller_record(
                    root=root,
                    record=controller_record,
                    expected_case_id=selected_case_id,
                    expected_preview_prompt=expected_prompt,
                    expected_inputs=expected_inputs,
                    expected_candidate_identity=expected_identity,
                    expected_output_filenames=(
                        {
                            item["filename"]
                            for item in controller_record["observed_outputs"]
                            if isinstance(item, dict)
                            and isinstance(item.get("filename"), str)
                        }
                        if isinstance(
                            controller_record.get("observed_outputs"),
                            list,
                        )
                        else set()
                    ),
                    required_output_filenames=required_outputs,
                    repository_root=source_root,
                )
            )
            attempts = controller_record.get("transport_attempts")
            attempted_chunk_zero = (
                {
                    item["payload_filename"]
                    for item in attempts
                    if isinstance(item, dict)
                    and item.get("chunk_index") == 0
                    and isinstance(item.get("payload_filename"), str)
                }
                if isinstance(attempts, list)
                else set()
            )
            missing_required_attempts = (
                []
                if _uses_same_response_transport(controller_record)
                else sorted(
                    (
                        required_outputs
                        & observed_output_controls
                        - actual_outputs
                    )
                    - attempted_chunk_zero
                )
            )
            if missing_required_attempts:
                controller_issues.append(
                    {
                        "severity": "ERROR",
                        "code": "CONTROLLER_TRANSPORT_ATTEMPT_MISSING",
                        "path": f"{CONTROLLER_RECORD_NAME}:$.transport_attempts",
                        "message": (
                            "a required visible file control without acquired bytes "
                            "requires one exact chunk-0 fallback attempt: "
                            f"{missing_required_attempts!r}"
                        ),
                    }
                )
            if audit_return is not None:
                declared = _declared_candidate_outputs(
                    audit_return,
                    input_filenames={item["filename"] for item in expected_inputs},
                )
                if declared is not None:
                    missing_capture = sorted(
                        declared
                        - actual_outputs
                        - observed_output_controls
                    )
                    if missing_capture:
                        controller_issues.append(
                            {
                                "severity": "ERROR",
                                "code": "CONTROLLER_DECLARED_OUTPUT_NOT_CAPTURED",
                                "path": f"{CONTROLLER_RECORD_NAME}:$.observed_outputs",
                                "message": (
                                    "candidate-declared outputs were omitted from the "
                                    f"independent capture: {missing_capture!r}"
                                ),
                            }
                        )

            canonical_hashes = {
                item["filename"]: item["sha256"] for item in expected_identity
            }
            expectation_findings: list[dict[str, str]] = []
            expectation_checks = {
                "expected_profile_hash": {"status": "not_run"},
                "expected_instructions_hash": {"status": "not_run"},
                "expected_eval_spec_hash": {"status": "not_run"},
                "text_sanitation": {"status": "pass"},
            }
            _verify_expectations(
                root,
                {
                    "profile_hash": (
                        expected_profile_sha256
                        if expected_profile_sha256 is not None
                        else canonical_hashes["GPT_PROFILE.json"]
                    ),
                    "instructions_hash": (
                        expected_instructions_sha256
                        if expected_instructions_sha256 is not None
                        else canonical_hashes["GPT_INSTRUCTIONS.md"]
                    ),
                    "eval_spec_hash": (
                        expected_eval_spec_sha256
                        if expected_eval_spec_sha256 is not None
                        else canonical_hashes["GPT_EVAL_SPEC.json"]
                    ),
                },
                expectation_findings,
                expectation_checks,
            )
            controller_issues.extend(expectation_findings)
            for name in (
                "expected_profile_hash",
                "expected_instructions_hash",
                "expected_eval_spec_hash",
            ):
                checks[name] = expectation_checks[name]

            transport_findings: list[dict[str, str]] = []
            transport_checks = {
                "artifact_transport": {"status": "not_run"},
                "text_sanitation": {"status": "pass"},
            }
            transport_records = _verify_transport_record(
                root,
                audit_return,
                actual_outputs,
                controller_record,
                transport_findings,
                transport_checks,
                payload_root=candidate_output_root,
                allow_incomplete_candidate_capture=(
                    _uses_same_response_transport(controller_record)
                ),
            )
            controller_issues.extend(transport_findings)
            checks["artifact_transport"] = transport_checks["artifact_transport"]

            score_axis, score_summary, score_issues = _load_score_result(
                root,
                controller_record=controller_record,
                case_id=selected_case_id,
                trial_id=str(controller_record.get("trial_id", "")),
                scoring_criteria=scoring_criteria,
                observable_behaviors=observable_behaviors,
                forbidden_behaviors=forbidden_behaviors,
                allowed_research_verdicts=allowed_research_verdicts,
                research_projection_requirement=research_projection_requirement,
                exact_research_projection=exact_research_projection,
            )
            controller_issues.extend(score_issues)
        else:
            score_axis = CANDIDATE_NOT_SCORED

        if controller_issues:
            findings.extend(controller_issues)
            _set_check(
                checks,
                "controller_record",
                "blocked",
                f"{len(controller_issues)} controller preflight finding(s)",
            )
            issue_codes = {item["code"] for item in controller_issues}
            _set_check(
                checks,
                "controller_input_roster",
                "blocked" if any("INPUT" in code for code in issue_codes) else "not_run",
                "controller preflight failed",
            )
            _set_check(
                checks,
                "controller_candidate_identity",
                (
                    "blocked"
                    if any(
                        "CANDIDATE_IDENTITY" in code
                        or code.startswith("EXPECTED_COPY")
                        for code in issue_codes
                    )
                    else "not_run"
                ),
                "controller preflight failed",
            )
            _set_check(
                checks,
                "controller_output_roster",
                (
                    "blocked"
                    if any(
                        "OUTPUT" in code or "ARTIFACT_TRANSPORT" in code
                        for code in issue_codes
                    )
                    else "not_run"
                ),
                "controller preflight failed",
            )
            _set_check(
                checks,
                "controller_parser_round_trip",
                (
                    "blocked"
                    if any(
                        "PARSER" in code or "WRAPPER" in code
                        for code in issue_codes
                    )
                    else "not_run"
                ),
                "controller preflight failed",
            )
            if any("SCORE_RESULT" in code for code in issue_codes):
                _set_check(checks, "score_result", "blocked")
            for name in (
                "candidate_output_consistency",
                "audit_return_artifacts",
                "export_wrappers",
                "python_return_desk",
                "chatgpt_data_analysis_output",
                "chatgpt_data_analysis_version",
                "visible_response_version",
            ):
                _set_check(
                    checks,
                    name,
                    "not_run",
                    "trial_invalid_controller; candidate scoring prohibited",
                )
        else:
            controller_axis = CONTROLLER_VALID
            _set_check(checks, "controller_record", "pass")
            _set_check(checks, "controller_input_roster", "pass")
            _set_check(checks, "controller_candidate_identity", "pass")
            _set_check(checks, "controller_output_roster", "pass")
            _set_check(checks, "controller_parser_round_trip", "pass")
            checks["audit_return_parse"] = parse_checks["audit_return_parse"]
            findings.extend(parse_findings)
            candidate_finding_start = len(findings) - len(parse_findings)

            missing_required = sorted(
                required_outputs
                - actual_outputs
                - observed_output_controls
            )
            if missing_required:
                _add_finding(
                    findings,
                    "CANDIDATE_REQUIRED_OUTPUT_MISSING",
                    ".",
                    f"frozen case required candidate outputs that were not produced: {missing_required!r}",
                )
            unavailable_controls = observed_output_controls - actual_outputs
            if unavailable_controls:
                _set_check(
                    checks,
                    "candidate_output_consistency",
                    "not_run",
                    (
                        "visible file controls lacked acquired payload bytes; "
                        f"transport identity remains unresolved: "
                        f"{sorted(unavailable_controls)!r}"
                    ),
                )
                _set_check(
                    checks,
                    "candidate_output_consistency",
                    "blocked",
                    f"missing={missing_required!r}",
                )

            same_response_transport_applicable = (
                _verify_same_response_candidate_transport(
                    root=root,
                    controller_record=controller_record,
                    required_output_filenames=required_outputs,
                    actual_output_filenames=actual_outputs,
                    observed_output_controls=observed_output_controls,
                    transport_records=transport_records,
                    findings=findings,
                    checks=checks,
                )
            )
            report: tuple[Path, str] | None = None
            if audit_return is not None:
                declared = _declared_candidate_outputs(
                    audit_return,
                    input_filenames={item["filename"] for item in expected_inputs},
                )
                if declared is None:
                    _add_finding(
                        findings,
                        "CANDIDATE_OUTPUT_DECLARATION_INVALID",
                        "audit_return.json:$.artifacts",
                        "candidate output declarations must be a complete filename roster",
                    )
                    _set_check(checks, "candidate_output_consistency", "blocked")
                else:
                    undeclared = sorted(actual_outputs - declared)
                    if undeclared:
                        _add_finding(
                            findings,
                            "CANDIDATE_OUTPUT_UNDECLARED",
                            "audit_return.json:$.artifacts",
                            f"independently captured outputs were not declared: {undeclared!r}",
                        )
                        _set_check(
                            checks,
                            "candidate_output_consistency",
                            "blocked",
                            f"undeclared={undeclared!r}",
                        )
                    elif checks["candidate_output_consistency"]["status"] == "not_run":
                        _set_check(checks, "candidate_output_consistency", "pass")

                artifacts, report = _verify_artifacts(
                    candidate_output_root,
                    audit_return,
                    findings,
                    checks,
                    unavailable_filenames=unavailable_controls,
                    source_root=root,
                )
                if (
                    checks["audit_return_artifacts"]["status"] == "not_run"
                    and not unavailable_controls
                ):
                    _set_check(checks, "audit_return_artifacts", "pass")
                if not _uses_same_response_transport(controller_record):
                    _verify_export_chunks(
                        root,
                        report,
                        transport_records,
                        controller_record,
                        findings,
                        checks,
                    )
                if checks["export_wrappers"]["status"] == "not_run":
                    _set_check(checks, "export_wrappers", "pass")
                _verify_version_literal(
                    root,
                    audit_return,
                    artifacts,
                    report,
                    findings,
                    checks,
                )
                if checks["chatgpt_data_analysis_version"]["status"] == "not_run":
                    _set_check(checks, "chatgpt_data_analysis_version", "pass")
                return_desk_result = _invoke_return_desk(
                    audit_return_path,
                    findings,
                    checks,
                    source_root=root,
                )
            else:
                if not _uses_same_response_transport(controller_record):
                    _verify_export_chunks(
                        root,
                        None,
                        transport_records,
                        controller_record,
                        findings,
                        checks,
                    )
                if checks["export_wrappers"]["status"] == "not_run":
                    _set_check(checks, "export_wrappers", "pass")
                visible_path = root / "visible_response_dom.txt"
                if visible_path.is_file():
                    visible_text = _decode_text(
                        visible_path.read_bytes(),
                        visible_path.name,
                        findings,
                        checks,
                    )
                    if visible_text is not None:
                        _set_check(checks, "visible_response_version", "pass")
                for name in (
                    "audit_return_artifacts",
                    "python_return_desk",
                    "chatgpt_data_analysis_output",
                    "chatgpt_data_analysis_version",
                ):
                    _set_check(
                        checks,
                        name,
                        "not_run",
                        "no return envelope was available for this case",
                    )
                if checks["candidate_output_consistency"]["status"] == "not_run":
                    _set_check(checks, "candidate_output_consistency", "pass")

            direct_acquisition_map = (
                _strict_direct_acquisition_map(controller_record) or {}
            )
            transport_axis = _transport_identity_axis(
                transport_records,
                observed_output_controls,
                has_transport_attempts=bool(
                    controller_record.get("transport_attempts")
                )
                or bool(direct_acquisition_map),
                has_same_response_capture=same_response_transport_applicable,
                required_output_filenames=required_outputs,
                direct_download_filenames={
                    filename
                    for filename, item in transport_records.items()
                    if item.get("method") == "direct_download"
                    and item.get("direct_download_outcome") == "download_event"
                    and direct_acquisition_map.get(filename) == "download_event"
                },
            )
            candidate_findings = findings[candidate_finding_start:]
            candidate_blocked = bool(candidate_findings) or any(
                checks[name]["status"] == "blocked"
                for name in (
                    "candidate_output_consistency",
                    "audit_return_parse",
                    "audit_return_artifacts",
                    "text_sanitation",
                    "export_wrappers",
                    "python_return_desk",
                    "chatgpt_data_analysis_output",
                    "chatgpt_data_analysis_version",
                    "visible_response_version",
                )
            )
            if candidate_blocked:
                candidate_axis = CANDIDATE_FAILED
                _set_check(
                    checks,
                    "score_result",
                    "blocked",
                    "candidate contradiction or artifact failure overrides any score",
                )
            else:
                candidate_axis = score_axis
                if score_axis == CANDIDATE_NOT_SCORED:
                    _set_check(
                        checks,
                        "score_result",
                        "not_run",
                        "no separately preserved valid manual score/oracle record",
                    )
                elif score_axis == CANDIDATE_PASSED:
                    _set_check(
                        checks,
                        "score_result",
                        "pass",
                        f"recomputed total={score_summary['total_score']}",
                    )
                else:
                    _add_finding(
                        findings,
                        "CANDIDATE_SCORE_GATE_FAILED",
                        "score_result.json",
                        "manual threshold, automatic-failure, or exact behavior oracle failed",
                    )
                    _set_check(
                        checks,
                        "score_result",
                        "blocked",
                        f"recomputed total={score_summary['total_score']}",
                    )

    blocked = (
        controller_axis == TRIAL_INVALID_CONTROLLER
        or candidate_axis == CANDIDATE_FAILED
        or any(record["status"] == "blocked" for record in checks.values())
    )
    disposition = derive_disposition(
        controller=controller_axis,
        candidate=candidate_axis,
        transport=transport_axis,
    )
    binding_hashes: dict[str, str | None] = {}
    for label, filename in (
        ("controller_record_sha256", "controller_record.json"),
        ("pre_score_controller_sha256", "pre_score_controller.json"),
        ("score_result_sha256", "score_result.json"),
    ):
        path = root / filename
        try:
            binding_hashes[label] = _sha256(path.read_bytes()) if path.is_file() else None
        except OSError:
            binding_hashes[label] = None
    try:
        binding_hashes["candidate_identity_sha256"] = (
            _sha256(canonical_json_bytes(controller_record["candidate_identity"]))
            if isinstance(controller_record, dict)
            and isinstance(controller_record.get("candidate_identity"), list)
            else None
        )
    except (TypeError, ValueError):
        binding_hashes["candidate_identity_sha256"] = None
    payload: dict[str, Any] = {
        "checker": "gpt_eval_bundle",
        "output_version": "2.0",
        "evidence_directory": str(root),
        "status": "blocked" if blocked else "pass",
        "outcomes": {
            "controller": controller_axis,
            "candidate": candidate_axis,
            "transport": transport_axis,
            "disposition": disposition,
            "scoring_allowed": controller_axis == CONTROLLER_VALID,
        },
        "checks": checks,
        "findings": findings,
        "bindings": binding_hashes,
        "score_result": score_summary,
        "return_desk": return_desk_result,
        "limitations": [
            LIMITATION,
            TRANSPORT_LIMITATION,
            (
                "Only active <payload>.export.<index>.json chunk wrappers are "
                "transport-checked; "
                "archived mismatch captures remain preserved evidence."
            ),
        ],
    }
    return (1 if blocked else 0), payload


def _parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(
        prog="check_gpt_eval_bundle.py",
        description="Fail-closed verification for a preserved Custom GPT evaluation bundle",
    )
    parser.add_argument("evidence_directory", type=Path)
    parser.add_argument(
        "--expect-case-id",
        dest="expected_case_id",
        help="require the controller record to bind this frozen evaluation case",
    )
    parser.add_argument(
        "--expect-profile-sha256",
        "--expect-gpt-profile-sha256",
        dest="expected_profile_sha256",
    )
    parser.add_argument(
        "--expect-instructions-sha256",
        "--expect-gpt-instructions-sha256",
        dest="expected_instructions_sha256",
    )
    parser.add_argument(
        "--expect-eval-spec-sha256",
        "--expect-gpt-eval-spec-sha256",
        dest="expected_eval_spec_sha256",
    )
    parser.add_argument(
        "--candidate-source-root",
        type=Path,
        help=(
            "validate frozen cases, candidate identity, and trial mapping against "
            "this preserved candidate source snapshot"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except StrictJsonError as exc:
        payload = {
            "checker": "gpt_eval_bundle",
            "output_version": "2.0",
            "status": "blocked",
            "checks": {"cli_arguments": {"status": "blocked"}},
            "findings": [
                {
                    "severity": "ERROR",
                    "code": "CLI_USAGE",
                    "path": "$",
                    "message": str(exc),
                }
            ],
            "limitations": [LIMITATION],
        }
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return 2
    status, payload = check_bundle(
        args.evidence_directory,
        expected_case_id=args.expected_case_id,
        expected_profile_sha256=args.expected_profile_sha256,
        expected_instructions_sha256=args.expected_instructions_sha256,
        expected_eval_spec_sha256=args.expected_eval_spec_sha256,
        candidate_source_root=args.candidate_source_root,
    )
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
