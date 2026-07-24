#!/usr/bin/env python3
"""Controller boundary and deterministic finalization for Custom GPT trials.

The module deliberately separates controller validity, candidate scoring, and
transport observability.  A controller record is an immutable byte inventory;
it is validated before Return Desk or any candidate scorer may run.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

try:
    from scripts.gpt_artifact_compiler import (
        BOUND_REPORT_ARTIFACT,
        BOUND_RETURN_ARTIFACT,
        BOUND_RUNTIME_ARTIFACT,
        REPORT_RUNTIME_REFERENCE,
        RUNTIME_BASIS_LINE,
        RUNTIME_PREFIX,
        canonical_json_bytes,
        export_payload_wrapper,
        extract_session_reported_runtime,
        finalize_candidate_artifacts,
        output_record,
        parse_runtime_ledger,
        runtime_ledger_text,
        sha256_bytes,
        transport_fallback_prompt,
    )
except ModuleNotFoundError:  # Direct execution from scripts/.
    from gpt_artifact_compiler import (  # type: ignore[no-redef]
        BOUND_REPORT_ARTIFACT,
        BOUND_RETURN_ARTIFACT,
        BOUND_RUNTIME_ARTIFACT,
        REPORT_RUNTIME_REFERENCE,
        RUNTIME_BASIS_LINE,
        RUNTIME_PREFIX,
        canonical_json_bytes,
        export_payload_wrapper,
        extract_session_reported_runtime,
        finalize_candidate_artifacts,
        output_record,
        parse_runtime_ledger,
        runtime_ledger_text,
        sha256_bytes,
        transport_fallback_prompt,
    )


CONTROLLER_RECORD_VERSION = "2.0"
CONTROLLER_RECORD_FIELDS = {
    "controller_record_version",
    "case_id",
    "trial_id",
    "counting_state",
    "preview_prompt",
    "raw_response",
    "fresh_conversation",
    "candidate_identity",
    "controller_artifacts",
    "inputs",
    "observed_outputs",
    "wrapper_captures",
}
BYTE_RECORD_FIELDS = {"kind", "filename", "bytes", "sha256"}
OUTPUT_RECORD_FIELDS = {"filename", "bytes", "sha256"}
WRAPPER_CAPTURE_FIELDS = {
    "payload_filename",
    "raw_filename",
    "parser_input_filename",
    "raw_bytes",
    "raw_sha256",
    "transport_prompt_filename",
    "transport_prompt_bytes",
    "transport_prompt_sha256",
    "transport_response_filename",
    "transport_response_bytes",
    "transport_response_sha256",
}

KNOWLEDGE_FILENAMES = (
    "BSC_PROTOCOL.md",
    "BSC_STATUS_AND_EVIDENCE_MODEL.md",
    "BSC_EXECUTION_AND_RECEIPTS.md",
    "BSC_SUPPORTED_CHECKS.md",
    "BSC_WORKED_EXAMPLES.md",
    "BSC_JAPANESE_INTERFACE.md",
)
CANDIDATE_IDENTITY_FILENAMES = (
    ("freeze_manifest", "GPT_FROZEN_CANDIDATE.json"),
    ("profile", "GPT_PROFILE.json"),
    ("instructions", "GPT_INSTRUCTIONS.md"),
    ("eval_spec", "GPT_EVAL_SPEC.json"),
)
CONTROLLER_ARTIFACT_FILENAMES = (
    "artifact_transport.json",
    "visible_response_dom.txt",
    "preview_prompt.txt",
)
OPTIONAL_CONTROLLER_ARTIFACT_FILENAMES = (
    "pre_score_controller.json",
    "score_result.json",
)

RAW_RESPONSE_FILENAME = "raw/response.outerHTML.html"

CONTROLLER_VALID = "controller_valid"
TRIAL_INVALID_CONTROLLER = "trial_invalid_controller"
CANDIDATE_PASSED = "candidate_passed"
CANDIDATE_FAILED = "candidate_failed"
CANDIDATE_NOT_SCORED = "not_scored"
CANDIDATE_PENDING_DISPOSITION = "candidate_not_scored"
TRANSPORT_IDENTITY_RESOLVED = "transport_identity_resolved"
TRANSPORT_IDENTITY_UNRESOLVED = "transport_identity_unresolved"
TRANSPORT_NOT_APPLICABLE = "not_applicable"
COUNTING_STATES = {"preflight", "counted", "invalid_retry"}
FRESH_CONVERSATION_FIELDS = {
    "required",
    "observed",
    "session_reference",
    "observability_boundary",
}

WINDOWS_RESERVED_BASENAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
TRIAL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
FROZEN_PROTOCOL_RELATIVE = Path("gpt") / "_source" / "GPT_FROZEN_EVALUATION_PROTOCOL.json"
FROZEN_CASES_RELATIVE = Path("gpt") / "evals" / "GPT_EVAL_CASES.jsonl"
DEVELOPMENT_TRIAL_BINDINGS = (
    ("D01", 1, "known-true-induction"),
    ("D02", 27, "return-envelope-positive-control"),
)


def byte_record(kind: str, filename: str, data: bytes) -> dict[str, Any]:
    return {
        "kind": kind,
        "filename": filename,
        "bytes": len(data),
        "sha256": sha256_bytes(data),
    }


def _strict_json_document(data: bytes, label: str) -> Any:
    def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key in {label}: {key}")
            result[key] = value
        return result

    try:
        text = data.decode("utf-8", errors="strict")
        return json.loads(
            text,
            object_pairs_hook=strict_object,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite number in {label}: {value}")
            ),
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"{label} is not strict UTF-8 JSON") from exc


def frozen_trial_bindings(
    repository_root: Path | None = None,
) -> dict[str, tuple[int, str, str]]:
    """Return the exact frozen D01/D02 and C001..C039 protocol registry.

    The registry is independently reconstructed from the frozen case order and
    then compared byte-semantically with the protocol mapping.  A syntactically
    valid protocol edit therefore cannot silently redefine a trial.
    """

    repository_root = (
        Path(__file__).resolve().parents[1]
        if repository_root is None
        else repository_root.resolve(strict=True)
    )
    cases_path = repository_root / FROZEN_CASES_RELATIVE
    try:
        case_lines = cases_path.read_bytes().decode("utf-8", errors="strict").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ValueError("frozen evaluation cases are unavailable") from exc
    case_ids: list[str] = []
    for line_number, line in enumerate(case_lines, 1):
        if not line:
            continue
        value = _strict_json_document(
            line.encode("utf-8"),
            f"{FROZEN_CASES_RELATIVE.as_posix()}:{line_number}",
        )
        case_id = value.get("id") if isinstance(value, dict) else None
        if not isinstance(case_id, str) or not case_id or case_id in case_ids:
            raise ValueError("frozen evaluation case identifiers are invalid")
        case_ids.append(case_id)
    if len(case_ids) != 39:
        raise ValueError("frozen counted suite must contain exactly 39 ordered cases")

    expected_development = [
        {
            "trial_id": trial_id,
            "case_number": number,
            "case_id": case_id,
            "counted": False,
        }
        for trial_id, number, case_id in DEVELOPMENT_TRIAL_BINDINGS
    ]
    for _, number, case_id in DEVELOPMENT_TRIAL_BINDINGS:
        if case_ids[number - 1] != case_id:
            raise ValueError("development preflight mapping differs from frozen case order")
    expected_counted = [
        {
            "trial_id": f"C{number:03d}",
            "case_number": number,
            "case_id": case_id,
            "counted": True,
        }
        for number, case_id in enumerate(case_ids, 1)
    ]
    protocol_path = repository_root / FROZEN_PROTOCOL_RELATIVE
    try:
        protocol = _strict_json_document(
            protocol_path.read_bytes(),
            FROZEN_PROTOCOL_RELATIVE.as_posix(),
        )
    except OSError as exc:
        raise ValueError("frozen evaluation protocol is unavailable") from exc
    if (
        not isinstance(protocol, dict)
        or protocol.get("development_preflights") != expected_development
        or protocol.get("counted_regression_trials") != expected_counted
    ):
        raise ValueError(
            "frozen evaluation protocol trial mapping differs from the exact case registry"
        )

    result = {
        item["trial_id"]: (
            item["case_number"],
            item["case_id"],
            "preflight",
        )
        for item in expected_development
    }
    result.update(
        {
            item["trial_id"]: (
                item["case_number"],
                item["case_id"],
                "counted",
            )
            for item in expected_counted
        }
    )
    return result


def validate_frozen_trial_binding(
    *,
    trial_id: object,
    case_id: object,
    counting_state: object,
    repository_root: Path | None = None,
) -> None:
    bindings = frozen_trial_bindings(repository_root)
    binding = bindings.get(trial_id) if isinstance(trial_id, str) else None
    if binding is None:
        raise ValueError("trial_id is not in the exact frozen protocol registry")
    _, expected_case_id, primary_state = binding
    if case_id != expected_case_id:
        raise ValueError("trial_id is mapped to a different frozen case")
    if counting_state not in {primary_state, "invalid_retry"}:
        raise ValueError(
            f"{trial_id} requires counting_state={primary_state} or invalid_retry"
        )


def _portable_relative(value: object) -> bool:
    if (
        not isinstance(value, str)
        or not value
        or value != unicodedata.normalize("NFC", value)
        or "\\" in value
        or "\x00" in value
    ):
        return False
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or pure.as_posix() != value:
        return False
    if any(part in {"", "."} for part in pure.parts):
        return False
    for part in pure.parts:
        stem = part.rstrip(" .").split(".", 1)[0].upper()
        if part != part.rstrip(" .") or stem in WINDOWS_RESERVED_BASENAMES or ":" in part:
            return False
    return True


def _portable_basename(value: object) -> bool:
    return (
        _portable_relative(value)
        and isinstance(value, str)
        and len(PurePosixPath(value).parts) == 1
    )


def _assert_portable_unique_basenames(values: Iterable[object], label: str) -> None:
    names = list(values)
    if any(not _portable_basename(value) for value in names):
        raise ValueError(f"{label} must use portable NFC basenames")
    normalized = [str(value).casefold() for value in names]
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{label} contains a normalized or case-insensitive collision")


def _transport_capture_names(payload: str) -> tuple[str, str, str]:
    if not _portable_basename(payload):
        raise ValueError("transport payload filename must be a portable basename")
    return (
        f"raw/{payload}.export.json",
        f"raw/{payload}.transport.prompt.txt",
        f"raw/{payload}.transport.outerHTML.html",
    )


class _CodeBlockTextExtractor(HTMLParser):
    """Recover decoded DOM text from code elements in preserved outerHTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._code_depth = 0
        self._current: list[str] | None = None
        self.invalid_nesting = False

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        del attrs
        if tag.casefold() != "code":
            return
        if self._code_depth:
            self.invalid_nesting = True
        else:
            self._current = []
        self._code_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() != "code":
            return
        if self._code_depth == 0:
            self.invalid_nesting = True
            return
        self._code_depth -= 1
        if self._code_depth == 0:
            assert self._current is not None
            self.blocks.append("".join(self._current))
            self._current = None

    def handle_data(self, data: str) -> None:
        if self._code_depth and self._current is not None:
            self._current.append(data)


def _extract_single_code_block_bytes(response_outer_html: bytes) -> bytes:
    try:
        html = response_outer_html.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise ValueError("transport response outerHTML is not strict UTF-8") from exc
    parser = _CodeBlockTextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:
        raise ValueError("transport response outerHTML could not be parsed") from exc
    if (
        parser.invalid_nesting
        or parser._code_depth != 0
        or parser._current is not None
        or len(parser.blocks) != 1
    ):
        raise ValueError(
            "transport response outerHTML must contain exactly one complete code block"
        )
    return parser.blocks[0].encode("utf-8")


def _files_are_pairwise_distinct(paths: Iterable[Path | None]) -> bool:
    resolved = list(paths)
    if any(path is None for path in resolved):
        return False
    regular = [path for path in resolved if path is not None]
    for index, left in enumerate(regular):
        for right in regular[index + 1 :]:
            try:
                if left == right or os.path.samefile(left, right):
                    return False
            except OSError:
                return False
    return True


def derive_disposition(*, controller: str, candidate: str, transport: str) -> str:
    """Derive a headline without allowing one axis to rescue another."""

    if controller not in {CONTROLLER_VALID, TRIAL_INVALID_CONTROLLER}:
        raise ValueError("unknown controller axis")
    if candidate not in {CANDIDATE_PASSED, CANDIDATE_FAILED, CANDIDATE_NOT_SCORED}:
        raise ValueError("unknown candidate axis")
    if transport not in {
        TRANSPORT_IDENTITY_RESOLVED,
        TRANSPORT_IDENTITY_UNRESOLVED,
        TRANSPORT_NOT_APPLICABLE,
    }:
        raise ValueError("unknown transport axis")
    if controller == TRIAL_INVALID_CONTROLLER:
        if candidate != CANDIDATE_NOT_SCORED:
            raise ValueError("an invalid controller trial cannot be scored")
        return TRIAL_INVALID_CONTROLLER
    if candidate == CANDIDATE_FAILED:
        return CANDIDATE_FAILED
    if candidate == CANDIDATE_NOT_SCORED:
        return CANDIDATE_PENDING_DISPOSITION
    if transport == TRANSPORT_IDENTITY_UNRESOLVED:
        return TRANSPORT_IDENTITY_UNRESOLVED
    return CANDIDATE_PASSED


def _safe_file(root: Path, relative: object) -> Path | None:
    if not _portable_relative(relative):
        return None
    root_resolved = root.resolve()
    candidate = root.joinpath(*PurePosixPath(str(relative)).parts)
    current = root
    try:
        for part in PurePosixPath(str(relative)).parts:
            current = current / part
            if current.is_symlink():
                return None
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root_resolved)
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        return None
    return resolved if resolved.is_file() else None


def _is_link_or_junction(path: Path) -> bool:
    try:
        return path.is_symlink() or (
            hasattr(path, "is_junction") and path.is_junction()
        )
    except OSError:
        return True


def validate_closed_evidence_layout(root: Path) -> None:
    """Reject hidden trial state outside the one closed raw-capture directory."""

    if _is_link_or_junction(root) or not root.is_dir():
        raise ValueError("evidence root must be a real directory, not a link or junction")
    try:
        root_entries = list(root.iterdir())
    except OSError as exc:
        raise ValueError("evidence root is unreadable") from exc
    for entry in root_entries:
        if _is_link_or_junction(entry):
            raise ValueError(f"evidence entry is a link or junction: {entry.name}")
        if entry.is_dir() and entry.name != "raw":
            raise ValueError(f"unexpected evidence directory: {entry.name}")
        if not entry.is_dir() and not entry.is_file():
            raise ValueError(f"evidence entry is not a regular file: {entry.name}")

    raw_root = root / "raw"
    if (
        not raw_root.is_dir()
        or _is_link_or_junction(raw_root)
        or raw_root.resolve(strict=True).parent != root.resolve(strict=True)
    ):
        raise ValueError("raw must be one real in-tree capture directory")
    active_wrappers = {
        entry.name
        for entry in root_entries
        if entry.is_file() and entry.name.endswith(".export.json")
    }
    _assert_portable_unique_basenames(active_wrappers, "active wrapper filenames")
    expected_raw = {PurePosixPath(RAW_RESPONSE_FILENAME).name}
    for wrapper in active_wrappers:
        payload = wrapper[: -len(".export.json")]
        raw_wrapper, transport_prompt, transport_response = _transport_capture_names(
            payload
        )
        expected_raw.update(
            {
                PurePosixPath(raw_wrapper).name,
                PurePosixPath(transport_prompt).name,
                PurePosixPath(transport_response).name,
            }
        )
    try:
        raw_entries = list(raw_root.iterdir())
    except OSError as exc:
        raise ValueError("raw capture directory is unreadable") from exc
    actual_raw: set[str] = set()
    for entry in raw_entries:
        if (
            _is_link_or_junction(entry)
            or not entry.is_file()
            or entry.parent.resolve(strict=True) != raw_root.resolve(strict=True)
        ):
            raise ValueError(f"raw capture is not one regular in-tree file: {entry.name}")
        actual_raw.add(entry.name)
    if actual_raw != expected_raw:
        raise ValueError(
            "raw capture roster must equal response.outerHTML.html plus each active "
            "wrapper, controller prompt, and complete transport response"
        )


def _issue(code: str, path: str, message: str) -> dict[str, str]:
    return {"severity": "ERROR", "code": code, "path": path, "message": message}


def _read_bound_file(
    root: Path,
    record: dict[str, Any],
    *,
    path: str,
    filename_field: str = "filename",
    bytes_field: str = "bytes",
    sha256_field: str = "sha256",
) -> tuple[bytes | None, list[dict[str, str]]]:
    candidate = _safe_file(root, record.get(filename_field))
    if candidate is None:
        return None, [
            _issue(
                "CONTROLLER_FILE_MISSING_OR_UNSAFE",
                path,
                "controller-bound file is missing, unsafe, symlinked, or not a regular file",
            )
        ]
    try:
        data = candidate.read_bytes()
    except OSError:
        return None, [
            _issue(
                "CONTROLLER_FILE_UNREADABLE",
                path,
                "controller-bound file is unreadable",
            )
        ]
    size = record.get(bytes_field)
    digest = record.get(sha256_field)
    if (
        isinstance(size, bool)
        or not isinstance(size, int)
        or size != len(data)
        or not isinstance(digest, str)
        or digest != sha256_bytes(data)
    ):
        return data, [
            _issue(
                "CONTROLLER_FILE_BINDING_MISMATCH",
                path,
                "controller-record byte count or SHA-256 differs from preserved bytes",
            )
        ]
    return data, []


def _validate_bound_roster(
    *,
    root: Path,
    value: object,
    expected: list[dict[str, Any]],
    label: str,
    code_prefix: str,
    fields: set[str],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not isinstance(value, list):
        return [
            _issue(
                f"{code_prefix}_ROSTER_INVALID",
                label,
                "bound roster must be an array",
            )
        ]
    observed_names: list[str] = []
    for index, item in enumerate(value):
        path = f"{label}[{index}]"
        if not isinstance(item, dict) or set(item) != fields:
            issues.append(
                _issue(
                    f"{code_prefix}_RECORD_INVALID",
                    path,
                    "bound record fields differ from the strict contract",
                )
            )
            continue
        filename = item.get("filename")
        if not _portable_basename(filename):
            issues.append(
                _issue(
                    f"{code_prefix}_FILENAME_INVALID",
                    path,
                    "bound filename must be a portable NFC basename",
                )
            )
        elif isinstance(filename, str):
            observed_names.append(filename)
        _, file_issues = _read_bound_file(root, item, path=path)
        issues.extend(file_issues)
    try:
        _assert_portable_unique_basenames(observed_names, "bound roster filenames")
    except ValueError:
        issues.append(
            _issue(
                f"{code_prefix}_DUPLICATE",
                label,
                "bound roster filenames must be unique after normalization and case-folding",
            )
        )
    if value != expected:
        issues.append(
            _issue(
                f"{code_prefix}_ROSTER_MISMATCH",
                label,
                "bound roster differs from the controller-derived byte inventory",
            )
        )
    return issues


def validate_controller_record(
    *,
    root: Path,
    record: dict[str, Any],
    expected_case_id: str,
    expected_preview_prompt: bytes,
    expected_inputs: list[dict[str, Any]],
    expected_candidate_identity: list[dict[str, Any]],
    expected_output_filenames: set[str],
    required_output_filenames: set[str] | None = None,
    repository_root: Path | None = None,
) -> list[dict[str, str]]:
    """Validate all controller-owned state before replay or candidate scoring."""

    issues: list[dict[str, str]] = []
    try:
        validate_closed_evidence_layout(root)
    except ValueError as exc:
        issues.append(
            _issue(
                "CONTROLLER_EVIDENCE_LAYOUT_INVALID",
                "evidence:$",
                str(exc),
            )
        )
    if not isinstance(record, dict) or set(record) != CONTROLLER_RECORD_FIELDS:
        return [
            _issue(
                "CONTROLLER_RECORD_FIELDS_INVALID",
                "controller_record.json:$",
                "controller record fields differ from the strict contract",
            )
        ]
    if record.get("controller_record_version") != CONTROLLER_RECORD_VERSION:
        issues.append(
            _issue(
                "CONTROLLER_RECORD_VERSION_INVALID",
                "controller_record.json:$.controller_record_version",
                "controller record version is not supported",
            )
        )
    if record.get("case_id") != expected_case_id:
        issues.append(
            _issue(
                "CONTROLLER_CASE_ID_MISMATCH",
                "controller_record.json:$.case_id",
                "controller case identity differs from the selected frozen case",
            )
        )
    trial_id = record.get("trial_id")
    if not isinstance(trial_id, str) or not TRIAL_ID_RE.fullmatch(trial_id):
        issues.append(
            _issue(
                "CONTROLLER_TRIAL_ID_INVALID",
                "controller_record.json:$.trial_id",
                "trial_id must be a nonempty portable controller identifier",
            )
        )
    if record.get("counting_state") not in COUNTING_STATES:
        issues.append(
            _issue(
                "CONTROLLER_COUNTING_STATE_INVALID",
                "controller_record.json:$.counting_state",
                "counting_state must be preflight, counted, or invalid_retry",
            )
        )
    try:
        validate_frozen_trial_binding(
            trial_id=trial_id,
            case_id=record.get("case_id"),
            counting_state=record.get("counting_state"),
            repository_root=repository_root,
        )
    except ValueError as exc:
        issues.append(
            _issue(
                "CONTROLLER_TRIAL_MAPPING_INVALID",
                "controller_record.json:$.trial_id",
                str(exc),
            )
        )

    prompt = record.get("preview_prompt")
    if not isinstance(prompt, dict) or set(prompt) != OUTPUT_RECORD_FIELDS:
        issues.append(
            _issue(
                "CONTROLLER_PREVIEW_PROMPT_INVALID",
                "controller_record.json:$.preview_prompt",
                "preview prompt must be one strict byte record",
            )
        )
    else:
        prompt_bytes, prompt_issues = _read_bound_file(
            root,
            prompt,
            path="controller_record.json:$.preview_prompt",
        )
        issues.extend(prompt_issues)
        if (
            prompt.get("filename") != "preview_prompt.txt"
            or prompt_bytes != expected_preview_prompt
            or prompt != output_record("preview_prompt.txt", expected_preview_prompt)
        ):
            issues.append(
                _issue(
                    "CONTROLLER_PREVIEW_PROMPT_MISMATCH",
                    "controller_record.json:$.preview_prompt",
                    "preserved preview_prompt.txt must exactly match the frozen case prompt bytes",
                )
            )

    raw_response = record.get("raw_response")
    if not isinstance(raw_response, dict) or set(raw_response) != OUTPUT_RECORD_FIELDS:
        issues.append(
            _issue(
                "CONTROLLER_RAW_RESPONSE_INVALID",
                "controller_record.json:$.raw_response",
                "raw response must be one strict byte record",
            )
        )
    else:
        raw_bytes, raw_issues = _read_bound_file(
            root,
            raw_response,
            path="controller_record.json:$.raw_response",
        )
        issues.extend(raw_issues)
        if (
            raw_response.get("filename") != RAW_RESPONSE_FILENAME
            or not raw_bytes
        ):
            issues.append(
                _issue(
                    "CONTROLLER_RAW_RESPONSE_INVALID",
                    "controller_record.json:$.raw_response",
                    "complete raw assistant outerHTML must be preserved at raw/response.outerHTML.html",
                )
            )

    conversation = record.get("fresh_conversation")
    if not isinstance(conversation, dict) or set(conversation) != FRESH_CONVERSATION_FIELDS:
        issues.append(
            _issue(
                "CONTROLLER_FRESH_CONVERSATION_INVALID",
                "controller_record.json:$.fresh_conversation",
                "fresh-conversation capture fields differ from the strict contract",
            )
        )
    elif (
        conversation.get("required") is not True
        or conversation.get("observed") is not True
        or not isinstance(conversation.get("session_reference"), str)
        or not conversation["session_reference"].strip()
        or not isinstance(conversation.get("observability_boundary"), str)
        or not conversation["observability_boundary"].strip()
    ):
        issues.append(
            _issue(
                "CONTROLLER_FRESH_CONVERSATION_UNESTABLISHED",
                "controller_record.json:$.fresh_conversation",
                "a fresh isolated Preview conversation and its observability boundary must be recorded",
            )
        )

    issues.extend(
        _validate_bound_roster(
            root=root,
            value=record.get("inputs"),
            expected=expected_inputs,
            label="controller_record.json:$.inputs",
            code_prefix="CONTROLLER_INPUT",
            fields=BYTE_RECORD_FIELDS,
        )
    )
    issues.extend(
        _validate_bound_roster(
            root=root,
            value=record.get("candidate_identity"),
            expected=expected_candidate_identity,
            label="controller_record.json:$.candidate_identity",
            code_prefix="CONTROLLER_CANDIDATE_IDENTITY",
            fields=BYTE_RECORD_FIELDS,
        )
    )

    expected_controller_names = list(CONTROLLER_ARTIFACT_FILENAMES)
    expected_controller_names.extend(
        filename
        for filename in OPTIONAL_CONTROLLER_ARTIFACT_FILENAMES
        if (root / filename).is_file()
    )
    expected_controller_artifacts: list[dict[str, Any]] = []
    for filename in expected_controller_names:
        path = _safe_file(root, filename)
        if path is None:
            continue
        expected_controller_artifacts.append(
            byte_record("controller", filename, path.read_bytes())
        )
    issues.extend(
        _validate_bound_roster(
            root=root,
            value=record.get("controller_artifacts"),
            expected=expected_controller_artifacts,
            label="controller_record.json:$.controller_artifacts",
            code_prefix="CONTROLLER_ARTIFACT",
            fields=BYTE_RECORD_FIELDS,
        )
    )
    missing_controller_artifacts = [
        filename
        for filename in CONTROLLER_ARTIFACT_FILENAMES
        if _safe_file(root, filename) is None
    ]
    if missing_controller_artifacts:
        issues.append(
            _issue(
                "CONTROLLER_ARTIFACT_REQUIRED_MISSING",
                "controller_record.json:$.controller_artifacts",
                f"required controller artifacts are missing: {missing_controller_artifacts!r}",
            )
        )

    outputs = record.get("observed_outputs")
    expected_outputs: list[dict[str, Any]] = []
    for filename in sorted(expected_output_filenames):
        path = _safe_file(root, filename)
        if path is not None:
            expected_outputs.append(output_record(filename, path.read_bytes()))
    issues.extend(
        _validate_bound_roster(
            root=root,
            value=outputs,
            expected=expected_outputs,
            label="controller_record.json:$.observed_outputs",
            code_prefix="CONTROLLER_OUTPUT",
            fields=OUTPUT_RECORD_FIELDS,
        )
    )
    missing_required_outputs = sorted(
        (required_output_filenames or set()) - expected_output_filenames
    )
    if missing_required_outputs:
        issues.append(
            _issue(
                "CONTROLLER_REQUIRED_OUTPUT_MISSING",
                "controller_record.json:$.observed_outputs",
                f"frozen case requires outputs that were not captured: {missing_required_outputs!r}",
            )
        )

    captures = record.get("wrapper_captures")
    if not isinstance(captures, list):
        issues.append(
            _issue(
                "CONTROLLER_WRAPPER_CAPTURE_INVALID",
                "controller_record.json:$.wrapper_captures",
                "wrapper capture roster must be an array",
            )
        )
        captures = []
    active_wrappers = {
        path.name for path in root.glob("*.export.json") if path.is_file()
    }
    captured_parser_inputs: list[str] = []
    seen_payloads: set[str] = set()
    seen_capture_paths: set[str] = set()
    for index, item in enumerate(captures):
        label = f"controller_record.json:$.wrapper_captures[{index}]"
        if not isinstance(item, dict) or set(item) != WRAPPER_CAPTURE_FIELDS:
            issues.append(
                _issue(
                    "CONTROLLER_WRAPPER_CAPTURE_INVALID",
                    label,
                    "wrapper capture fields differ from the strict contract",
                )
            )
            continue
        payload = item.get("payload_filename")
        raw_filename = item.get("raw_filename")
        parser_filename = item.get("parser_input_filename")
        prompt_filename = item.get("transport_prompt_filename")
        response_filename = item.get("transport_response_filename")
        canonical_names: tuple[str, str, str] | None = None
        if isinstance(payload, str) and _portable_basename(payload):
            canonical_names = _transport_capture_names(payload)
        capture_paths = [
            value
            for value in (
                raw_filename,
                prompt_filename,
                response_filename,
                parser_filename,
            )
            if isinstance(value, str)
        ]
        if (
            not _portable_basename(payload)
            or not _portable_basename(parser_filename)
            or parser_filename != f"{payload}.export.json"
            or canonical_names is None
            or (
                raw_filename,
                prompt_filename,
                response_filename,
            )
            != canonical_names
            or payload in seen_payloads
            or parser_filename in captured_parser_inputs
            or any(value in seen_capture_paths for value in capture_paths)
        ):
            issues.append(
                _issue(
                    "CONTROLLER_WRAPPER_CAPTURE_INVALID",
                    label,
                    "wrapper, controller prompt, complete response, and parser paths "
                    "must be canonical and unique",
                )
            )
        if isinstance(payload, str):
            seen_payloads.add(payload)
        seen_capture_paths.update(capture_paths)
        if isinstance(parser_filename, str):
            captured_parser_inputs.append(parser_filename)
        raw_bytes, raw_issues = _read_bound_file(
            root,
            item,
            path=label,
            filename_field="raw_filename",
            bytes_field="raw_bytes",
            sha256_field="raw_sha256",
        )
        issues.extend(raw_issues)
        prompt_bytes, prompt_issues = _read_bound_file(
            root,
            item,
            path=label,
            filename_field="transport_prompt_filename",
            bytes_field="transport_prompt_bytes",
            sha256_field="transport_prompt_sha256",
        )
        issues.extend(prompt_issues)
        response_bytes, response_issues = _read_bound_file(
            root,
            item,
            path=label,
            filename_field="transport_response_filename",
            bytes_field="transport_response_bytes",
            sha256_field="transport_response_sha256",
        )
        issues.extend(response_issues)
        parser_path = _safe_file(root, parser_filename)
        raw_path = _safe_file(root, raw_filename)
        prompt_path = _safe_file(root, prompt_filename)
        response_path = _safe_file(root, response_filename)
        if parser_path is None:
            issues.append(
                _issue(
                    "CONTROLLER_PARSER_INPUT_MISSING_OR_UNSAFE",
                    label,
                    "parser input wrapper is missing or unsafe",
                )
            )
        if not _files_are_pairwise_distinct(
            (parser_path, raw_path, prompt_path, response_path)
        ):
            issues.append(
                _issue(
                    "CONTROLLER_RAW_CAPTURE_NOT_DISTINCT",
                    label,
                    "parser input, raw wrapper, controller prompt, and transport "
                    "outerHTML must be four distinct regular files",
                )
            )
        parser_bytes: bytes | None = None
        if parser_path is not None:
            try:
                parser_bytes = parser_path.read_bytes()
            except OSError:
                pass
        if parser_path is not None and parser_bytes is None:
            issues.append(
                _issue(
                    "CONTROLLER_PARSER_INPUT_UNREADABLE",
                    label,
                    "parser input wrapper is unreadable",
                )
            )
        if raw_bytes is not None and raw_bytes != parser_bytes:
            issues.append(
                _issue(
                    "CONTROLLER_PARSER_ROUND_TRIP_MISMATCH",
                    label,
                    "parser input bytes differ from the preserved raw wrapper bytes",
                )
            )
        if (
            isinstance(payload, str)
            and _portable_basename(payload)
            and prompt_bytes is not None
            and prompt_bytes != transport_fallback_prompt(payload).encode("utf-8")
        ):
            issues.append(
                _issue(
                    "CONTROLLER_TRANSPORT_PROMPT_MISMATCH",
                    label,
                    "preserved transport prompt differs from the exact "
                    "controller-generated one-file prompt",
                )
            )
        code_bytes: bytes | None = None
        if response_bytes is not None:
            try:
                code_bytes = _extract_single_code_block_bytes(response_bytes)
            except ValueError as exc:
                issues.append(
                    _issue(
                        "CONTROLLER_TRANSPORT_RESPONSE_INVALID",
                        label,
                        str(exc),
                    )
                )
        if code_bytes is not None and (
            raw_bytes is None
            or parser_bytes is None
            or code_bytes != raw_bytes
            or code_bytes != parser_bytes
        ):
            issues.append(
                _issue(
                    "CONTROLLER_TRANSPORT_PROVENANCE_MISMATCH",
                    label,
                    "the one browser code block does not equal both the preserved "
                    "raw wrapper and parser input byte-for-byte",
                )
            )
    if set(captured_parser_inputs) != active_wrappers:
        issues.append(
            _issue(
                "CONTROLLER_WRAPPER_CAPTURE_ROSTER_MISMATCH",
                "controller_record.json:$.wrapper_captures",
                "every active Base64 wrapper requires one exact prompt, complete "
                "response, raw code-text, and parser-input capture",
            )
        )
    return issues


def _stable_read(path: Path) -> bytes:
    before = path.stat()
    data = path.read_bytes()
    after = path.stat()
    if (
        before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or len(data) != after.st_size
    ):
        raise ValueError(f"file changed during controller capture: {path.name}")
    return data


def build_controller_record(
    *,
    root: Path,
    case_id: str,
    trial_id: str,
    counting_state: str,
    target_filename: str,
    output_filenames: Iterable[str],
    session_reference: str,
    observability_boundary: str,
) -> dict[str, Any]:
    """Capture an explicit, independent controller inventory.

    Output filenames are mandatory caller observations; they are never derived
    from ``audit_return.artifacts``.
    """

    validate_closed_evidence_layout(root)
    root = root.resolve(strict=True)
    if not TRIAL_ID_RE.fullmatch(trial_id):
        raise ValueError("invalid trial_id")
    if counting_state not in COUNTING_STATES:
        raise ValueError("invalid counting_state")
    if not isinstance(case_id, str) or not case_id:
        raise ValueError("case_id must be nonempty")
    validate_frozen_trial_binding(
        trial_id=trial_id,
        case_id=case_id,
        counting_state=counting_state,
    )
    if not session_reference.strip() or not observability_boundary.strip():
        raise ValueError("session reference and observability boundary are required")

    input_specs = [("target", target_filename)]
    input_specs.extend(("knowledge", filename) for filename in KNOWLEDGE_FILENAMES)
    inputs: list[dict[str, Any]] = []
    for kind, filename in input_specs:
        if not _portable_basename(filename):
            raise ValueError("input filenames must be portable basenames")
        path = _safe_file(root, filename)
        if path is None:
            raise ValueError(f"required input is unavailable: {filename}")
        inputs.append(byte_record(kind, filename, _stable_read(path)))

    candidate_identity: list[dict[str, Any]] = []
    for kind, filename in CANDIDATE_IDENTITY_FILENAMES:
        path = _safe_file(root, filename)
        if path is None:
            raise ValueError(f"candidate identity is unavailable: {filename}")
        candidate_identity.append(byte_record(kind, filename, _stable_read(path)))

    controller_artifacts: list[dict[str, Any]] = []
    controller_names = list(CONTROLLER_ARTIFACT_FILENAMES)
    controller_names.extend(
        filename
        for filename in OPTIONAL_CONTROLLER_ARTIFACT_FILENAMES
        if _safe_file(root, filename) is not None
    )
    for filename in controller_names:
        path = _safe_file(root, filename)
        if path is None:
            raise ValueError(f"controller artifact is unavailable: {filename}")
        controller_artifacts.append(
            byte_record("controller", filename, _stable_read(path))
        )

    output_names = list(output_filenames)
    _assert_portable_unique_basenames(output_names, "observed output filenames")
    outputs: list[dict[str, Any]] = []
    for filename in sorted(output_names):
        path = _safe_file(root, filename)
        if path is None:
            raise ValueError(f"observed output is unavailable: {filename}")
        outputs.append(output_record(filename, _stable_read(path)))

    captures: list[dict[str, Any]] = []
    for parser_path in sorted(root.glob("*.export.json")):
        if not parser_path.is_file() or parser_path.is_symlink():
            raise ValueError(f"active wrapper is unsafe: {parser_path.name}")
        payload = parser_path.name[: -len(".export.json")]
        if not _portable_basename(payload):
            raise ValueError(f"wrapper payload name is unsafe: {payload}")
        raw_name, transport_prompt_name, transport_response_name = (
            _transport_capture_names(payload)
        )
        raw_path = _safe_file(root, raw_name)
        transport_prompt_path = _safe_file(root, transport_prompt_name)
        transport_response_path = _safe_file(root, transport_response_name)
        if not _files_are_pairwise_distinct(
            (
                parser_path,
                raw_path,
                transport_prompt_path,
                transport_response_path,
            )
        ):
            raise ValueError(
                f"distinct fallback provenance files are unavailable for: {payload}"
            )
        assert raw_path is not None
        assert transport_prompt_path is not None
        assert transport_response_path is not None
        raw = _stable_read(raw_path)
        parser = _stable_read(parser_path)
        transport_prompt = _stable_read(transport_prompt_path)
        transport_response = _stable_read(transport_response_path)
        expected_transport_prompt = transport_fallback_prompt(payload).encode("utf-8")
        if transport_prompt != expected_transport_prompt:
            raise ValueError(
                f"transport prompt differs from controller output: {payload}"
            )
        if raw != parser:
            raise ValueError(f"raw/parser round trip differs: {parser_path.name}")
        code_bytes = _extract_single_code_block_bytes(transport_response)
        if code_bytes != raw or code_bytes != parser:
            raise ValueError(
                f"transport code block differs from raw/parser bytes: {payload}"
            )
        captures.append(
            {
                "payload_filename": payload,
                "raw_filename": raw_name,
                "parser_input_filename": parser_path.name,
                "raw_bytes": len(raw),
                "raw_sha256": sha256_bytes(raw),
                "transport_prompt_filename": transport_prompt_name,
                "transport_prompt_bytes": len(transport_prompt),
                "transport_prompt_sha256": sha256_bytes(transport_prompt),
                "transport_response_filename": transport_response_name,
                "transport_response_bytes": len(transport_response),
                "transport_response_sha256": sha256_bytes(transport_response),
            }
        )

    prompt_path = _safe_file(root, "preview_prompt.txt")
    if prompt_path is None:
        raise ValueError("preview_prompt.txt is unavailable")
    prompt = _stable_read(prompt_path)
    raw_response_path = _safe_file(root, RAW_RESPONSE_FILENAME)
    if raw_response_path is None:
        raise ValueError(
            "complete raw response capture is unavailable: "
            f"{RAW_RESPONSE_FILENAME}"
        )
    raw_response = _stable_read(raw_response_path)
    if not raw_response:
        raise ValueError("complete raw response capture must not be empty")
    return {
        "controller_record_version": CONTROLLER_RECORD_VERSION,
        "case_id": case_id,
        "trial_id": trial_id,
        "counting_state": counting_state,
        "preview_prompt": output_record("preview_prompt.txt", prompt),
        "raw_response": output_record(RAW_RESPONSE_FILENAME, raw_response),
        "fresh_conversation": {
            "required": True,
            "observed": True,
            "session_reference": session_reference,
            "observability_boundary": observability_boundary,
        },
        "candidate_identity": candidate_identity,
        "controller_artifacts": controller_artifacts,
        "inputs": inputs,
        "observed_outputs": outputs,
        "wrapper_captures": captures,
    }


def atomic_write(path: Path, data: bytes) -> None:
    """Atomically replace a regular record without following a symlink."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("refusing to overwrite a symlink")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists() or temporary.is_symlink():
        raise ValueError("refusing to reuse an existing temporary path")
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gpt_eval_controller.py",
        description="Build an immutable controller record for one preserved GPT trial",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser(
        "build-record",
        help="capture exact inputs, candidate identity, outputs, and wrapper round trips",
    )
    build.add_argument("evidence_directory", type=Path)
    build.add_argument("--case-id", required=True)
    build.add_argument("--trial-id", required=True)
    build.add_argument("--counting-state", choices=sorted(COUNTING_STATES), required=True)
    build.add_argument("--target", required=True, dest="target_filename")
    build.add_argument(
        "--output",
        action="append",
        default=[],
        dest="output_filenames",
        help="independently observed candidate output basename; repeat for every output",
    )
    build.add_argument("--session-reference", required=True)
    build.add_argument("--observability-boundary", required=True)
    transport = subparsers.add_parser(
        "transport-request",
        help="emit the exact one-file fallback prompt with no trailing newline",
    )
    transport.add_argument(
        "--output",
        required=True,
        dest="payload_filename",
        help="one finalized output basename to acquire through the fallback",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "transport-request":
        try:
            prompt = transport_fallback_prompt(args.payload_filename)
        except (ValueError, TypeError) as exc:
            print(
                json.dumps(
                    {
                        "controller": "transport_request",
                        "output_version": "2.0",
                        "status": "blocked",
                        "error": str(exc),
                    },
                    sort_keys=True,
                    ensure_ascii=False,
                )
            )
            return 1
        print(prompt, end="")
        return 0
    try:
        record = build_controller_record(
            root=args.evidence_directory,
            case_id=args.case_id,
            trial_id=args.trial_id,
            counting_state=args.counting_state,
            target_filename=args.target_filename,
            output_filenames=args.output_filenames,
            session_reference=args.session_reference,
            observability_boundary=args.observability_boundary,
        )
        destination = args.evidence_directory / "controller_record.json"
        atomic_write(destination, canonical_json_bytes(record))
    except (OSError, ValueError, TypeError) as exc:
        print(
            json.dumps(
                {
                    "controller": "build_record",
                    "output_version": "2.0",
                    "status": "blocked",
                    "error": str(exc),
                },
                sort_keys=True,
                ensure_ascii=False,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "controller": "build_record",
                "output_version": "2.0",
                "status": "pass",
                "record": str(destination.resolve()),
                "sha256": sha256_bytes(destination.read_bytes()),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
