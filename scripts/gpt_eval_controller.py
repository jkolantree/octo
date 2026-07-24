#!/usr/bin/env python3
"""Controller boundary and deterministic finalization for Custom GPT trials.

The module deliberately separates controller validity, candidate scoring, and
transport observability.  A controller record is an immutable byte inventory;
it is validated before Return Desk or any candidate scorer may run.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shlex
import unicodedata
import zlib
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

try:
    from scripts.gpt_artifact_compiler import (
        BOUND_REPORT_ARTIFACT,
        BOUND_RETURN_ARTIFACT,
        BOUND_RUNTIME_ARTIFACT,
        COMPILER_VERSION,
        EXPORT_CHUNK_FIELDS,
        MAX_TRANSPORT_CHUNKS,
        MAX_TRANSPORT_ENCODED_BYTES,
        MAX_TRANSPORT_PAYLOAD_BYTES,
        REPORT_RUNTIME_REFERENCE,
        RECOVERY_STATE_DATA_SHARD_RECOVERED,
        RECOVERY_STATE_NOT_NEEDED,
        RECOVERY_STATE_PARITY_DEGRADED_NOT_USED,
        RUNTIME_BASIS_LINE,
        RUNTIME_PREFIX,
        SAME_RESPONSE_RECOVERY_RECEIPT_FIELDS,
        SAME_RESPONSE_RECOVERY_STATES,
        SAME_RESPONSE_TRANSPORT_VERSION,
        TRANSPORT_CHUNK_BYTES,
        TRANSPORT_CHUNK_VERSION,
        TRANSPORT_ENCODING,
        XOR_PARITY_SCHEME,
        canonical_json_bytes,
        canonical_transport_wrapper_bytes,
        export_payload_chunk,
        extract_session_reported_runtime,
        finalize_candidate_artifacts,
        output_record,
        parse_compile_transport_stdout,
        parse_compile_transport_stdout_with_receipt,
        parse_runtime_ledger,
        runtime_ledger_text,
        sha256_bytes,
    )
except ModuleNotFoundError:  # Direct execution from scripts/.
    from gpt_artifact_compiler import (  # type: ignore[no-redef]
        BOUND_REPORT_ARTIFACT,
        BOUND_RETURN_ARTIFACT,
        BOUND_RUNTIME_ARTIFACT,
        COMPILER_VERSION,
        EXPORT_CHUNK_FIELDS,
        MAX_TRANSPORT_CHUNKS,
        MAX_TRANSPORT_ENCODED_BYTES,
        MAX_TRANSPORT_PAYLOAD_BYTES,
        REPORT_RUNTIME_REFERENCE,
        RECOVERY_STATE_DATA_SHARD_RECOVERED,
        RECOVERY_STATE_NOT_NEEDED,
        RECOVERY_STATE_PARITY_DEGRADED_NOT_USED,
        RUNTIME_BASIS_LINE,
        RUNTIME_PREFIX,
        SAME_RESPONSE_RECOVERY_RECEIPT_FIELDS,
        SAME_RESPONSE_RECOVERY_STATES,
        SAME_RESPONSE_TRANSPORT_VERSION,
        TRANSPORT_CHUNK_BYTES,
        TRANSPORT_CHUNK_VERSION,
        TRANSPORT_ENCODING,
        XOR_PARITY_SCHEME,
        canonical_json_bytes,
        canonical_transport_wrapper_bytes,
        export_payload_chunk,
        extract_session_reported_runtime,
        finalize_candidate_artifacts,
        output_record,
        parse_compile_transport_stdout,
        parse_compile_transport_stdout_with_receipt,
        parse_runtime_ledger,
        runtime_ledger_text,
        sha256_bytes,
    )


CONTROLLER_RECORD_VERSION = "5.0"
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
    "observed_output_controls",
    "observed_outputs",
    "direct_acquisition_attempts",
    "compiler_transport_capture",
    "reconstructed_outputs",
}
BYTE_RECORD_FIELDS = {"kind", "filename", "bytes", "sha256"}
OUTPUT_RECORD_FIELDS = {"filename", "bytes", "sha256"}
DIRECT_ACQUISITION_ATTEMPT_FIELDS = {"filename", "outcome"}
DIRECT_ACQUISITION_OUTCOMES = {
    "download_event",
    "no_download_event",
    "unavailable",
}
COMPILER_BLOCK_IDENTITY_FIELDS = {"code_block_index", "bytes", "sha256"}
RECONSTRUCTED_OUTPUT_FIELDS = {
    "filename",
    "materialized_filename",
    "bytes",
    "sha256",
}
COMPILER_TRANSPORT_CAPTURE_FIELDS = {
    "status",
    "candidate_evidence",
    "detail",
    "compiler_blocks",
    "compiler",
    "transport_version",
    "recovery_receipt",
}
COMPILER_TRANSPORT_STATUSES = {
    "verified",
    "missing",
    "malformed",
    "blocked",
    "extra",
    "duplicate",
    "truncated",
}
WRAPPER_CAPTURE_FIELDS = {
    "payload_filename",
    "chunk_index",
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
TRANSPORT_ATTEMPT_FIELDS = {
    "payload_filename",
    "chunk_index",
    "transport_prompt_filename",
    "transport_prompt_bytes",
    "transport_prompt_sha256",
    "transport_response_filename",
    "transport_response_bytes",
    "transport_response_sha256",
    "response_outcome",
    "response_file_controls",
    "parser_input_filename",
}
TRANSPORT_ATTEMPT_OUTCOMES = {
    "chunk_wrapper_captured",
    "blank_response",
    "file_control_only",
    "invalid_response",
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
RECONSTRUCTED_OUTPUT_DIRECTORY = "reconstructed"
ARTIFACT_TRANSPORT_VERSION = "3.0"
SAME_RESPONSE_TRANSPORT_METHOD = "in_turn_compiler_bundle"

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


def _direct_acquisition_argument(value: str) -> tuple[str, str]:
    """Parse one explicit ``FILENAME=OUTCOME`` controller observation."""

    try:
        filename, outcome = value.rsplit("=", 1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "direct acquisition must use FILENAME=OUTCOME"
        ) from exc
    if not _portable_basename(filename):
        raise argparse.ArgumentTypeError(
            "direct acquisition filename must be a portable NFC basename"
        )
    if outcome not in DIRECT_ACQUISITION_OUTCOMES:
        raise argparse.ArgumentTypeError(
            "direct acquisition outcome must be download_event, "
            "no_download_event, or unavailable"
        )
    return filename, outcome


def _direct_acquisition_records(
    attempts: Iterable[tuple[str, str]],
) -> list[dict[str, str]]:
    """Normalize caller-supplied direct-acquisition observations."""

    records: list[dict[str, str]] = []
    for attempt in attempts:
        if (
            not isinstance(attempt, (tuple, list))
            or len(attempt) != 2
            or not _portable_basename(attempt[0])
            or attempt[1] not in DIRECT_ACQUISITION_OUTCOMES
        ):
            raise ValueError(
                "direct acquisition attempts must be portable "
                "(filename, outcome) pairs"
            )
        records.append({"filename": attempt[0], "outcome": attempt[1]})
    records.sort(key=lambda item: item["filename"])
    _assert_portable_unique_basenames(
        (item["filename"] for item in records),
        "direct acquisition filenames",
    )
    return records


def _direct_acquisition_map(value: object) -> dict[str, str]:
    """Validate and index the serialized direct-acquisition evidence."""

    if not isinstance(value, list) or any(
        not isinstance(item, dict)
        or set(item) != DIRECT_ACQUISITION_ATTEMPT_FIELDS
        or not _portable_basename(item.get("filename"))
        or item.get("outcome") not in DIRECT_ACQUISITION_OUTCOMES
        for item in value
    ):
        raise ValueError(
            "direct acquisition attempts differ from the strict v5 contract"
        )
    records = [
        {"filename": item["filename"], "outcome": item["outcome"]}
        for item in value
    ]
    if records != sorted(records, key=lambda item: item["filename"]):
        raise ValueError("direct acquisition attempts must be sorted by filename")
    _assert_portable_unique_basenames(
        (item["filename"] for item in records),
        "direct acquisition filenames",
    )
    return {item["filename"]: item["outcome"] for item in records}


INDEXED_WRAPPER_RE = re.compile(
    r"^(?P<payload>.+)\.export\.(?P<chunk_index>[0-9]{5})\.json$"
)
TRANSPORT_PROMPT_RE = re.compile(
    r"^(?P<payload>.+)\.transport\.(?P<chunk_index>[0-9]{5})\.prompt\.txt$"
)
TRANSPORT_RESPONSE_RE = re.compile(
    r"^(?P<payload>.+)\.transport\.(?P<chunk_index>[0-9]{5})"
    r"\.outerHTML\.html$"
)
LOWER_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
FILE_CONTROL_PREFIXES = (
    "Download file: ",
    "Download file ",
    "Download: ",
    "Download ",
    "File: ",
)


def _recovery_receipt_contract_valid(value: object) -> bool:
    if (
        not isinstance(value, dict)
        or set(value) != SAME_RESPONSE_RECOVERY_RECEIPT_FIELDS
        or value.get("scheme") != XOR_PARITY_SCHEME
        or value.get("state") not in SAME_RESPONSE_RECOVERY_STATES
    ):
        return False
    recovered_index = value.get("recovered_chunk_index")
    received_digest = value.get("received_base64_sha256")
    reconstructed_digest = value.get("reconstructed_chunk_sha256")
    for digest in (received_digest, reconstructed_digest):
        if digest is not None and (
            not isinstance(digest, str)
            or LOWER_SHA256_RE.fullmatch(digest) is None
        ):
            return False
    state = value["state"]
    if state == RECOVERY_STATE_NOT_NEEDED:
        return (
            recovered_index is None
            and received_digest is None
            and reconstructed_digest is None
        )
    if state == RECOVERY_STATE_DATA_SHARD_RECOVERED:
        return (
            isinstance(recovered_index, int)
            and not isinstance(recovered_index, bool)
            and recovered_index >= 0
            and received_digest is not None
            and reconstructed_digest is not None
        )
    if state == RECOVERY_STATE_PARITY_DEGRADED_NOT_USED:
        return (
            recovered_index is None
            and received_digest is not None
            and reconstructed_digest is None
        )
    return False


def _transport_parser_name(payload: str, chunk_index: int) -> str:
    if not _portable_basename(payload):
        raise ValueError("transport payload filename must be a portable basename")
    if (
        isinstance(chunk_index, bool)
        or not isinstance(chunk_index, int)
        or not 0 <= chunk_index < MAX_TRANSPORT_CHUNKS
    ):
        raise ValueError("transport chunk index must be in 0..99999")
    return f"{payload}.export.{chunk_index:05d}.json"


def _transport_capture_names(
    payload: str,
    chunk_index: int,
) -> tuple[str, str, str]:
    parser_name = _transport_parser_name(payload, chunk_index)
    return (
        f"raw/{parser_name}",
        f"raw/{payload}.transport.{chunk_index:05d}.prompt.txt",
        f"raw/{payload}.transport.{chunk_index:05d}.outerHTML.html",
    )


def _legacy_transport_fallback_prompt(
    filename: str,
    chunk_index: int = 0,
    *,
    expected_payload_sha256: str | None = None,
    expected_encoded_sha256: str | None = None,
) -> str:
    """Reproduce a v3 prompt only when validating preserved historical evidence."""

    if not _portable_basename(filename):
        raise ValueError("transport payload filename must be a portable basename")
    if (
        isinstance(chunk_index, bool)
        or not isinstance(chunk_index, int)
        or not 0 <= chunk_index < MAX_TRANSPORT_CHUNKS
    ):
        raise ValueError("transport chunk index must be in 0..99999")
    for value, label in (
        (expected_payload_sha256, "expected payload SHA-256"),
        (expected_encoded_sha256, "expected encoded SHA-256"),
    ):
        if value is not None and (
            not isinstance(value, str)
            or LOWER_SHA256_RE.fullmatch(value) is None
        ):
            raise ValueError(f"{label} must be lowercase hexadecimal")
    if (expected_payload_sha256 is None) != (expected_encoded_sha256 is None):
        raise ValueError("expected payload and encoded SHA-256 values must be paired")
    if chunk_index > 0 and expected_payload_sha256 is None:
        raise ValueError("later transport chunks require both expected SHA-256 values")
    snapshot_path = f"/mnt/data/.bsc-transport-v1/{filename}"
    command = (
        "python /mnt/data/gpt_artifact_compiler.py export-chunk "
        + shlex.quote(snapshot_path)
        + f" --chunk-index {chunk_index}"
    )
    if expected_payload_sha256 is not None:
        command += (
            " --expect-payload-sha256 "
            + expected_payload_sha256
            + " --expect-encoded-sha256 "
            + expected_encoded_sha256
        )
    return (
        "TRANSPORT FALLBACK ONLY. The direct file control emitted no observable "
        f"download event for {filename}. Requesting bounded chunk {chunk_index}. "
        "Use the enabled Data Analysis tool now. A visible Data Analysis invocation "
        "of the exact command below is mandatory before any answer; do not answer "
        "from reasoning or infer that execution occurred. "
        "The compiler sealed the final bytes in a private unexposed transport "
        "snapshot during the original compile transaction. Do not regenerate or "
        "alter that snapshot. "
        "Do not read, trim, normalize, or encode the payload yourself. Execute this "
        f"literal command exactly once: {command} . Return the command's complete "
        "stdout byte-for-byte as the only strict JSON object in one code block, "
        "whether it is a chunk wrapper or a compiler-generated blocked record. "
        "The canonical stdout has no trailing line feed; do not reimplement it or "
        "reuse a hash, size, ledger row, return field, or "
        "prose value. The controller alone requests later chunk indices using the "
        "payload and encoded SHA-256 values from chunk 0. If the command reports "
        "a handled failure, return only its exact JSON stdout. If no invocation or "
        "stdout occurs, emit no substitute token or prose. Never infer or emit "
        "export_failed. This identifies only "
        "the exported compressed chunk received here and its strictly reconstructed "
        "payload, never unavailable download-button bytes."
    )


def _parse_indexed_name(
    name: str,
    pattern: re.Pattern[str],
) -> tuple[str, int] | None:
    match = pattern.fullmatch(name)
    if match is None:
        return None
    payload = match.group("payload")
    if not _portable_basename(payload):
        return None
    return payload, int(match.group("chunk_index"))


class _CodeBlockTextExtractor(HTMLParser):
    """Recover decoded DOM text from code elements in preserved outerHTML."""

    _NON_CONTENT_TAGS = {
        "button",
        "noscript",
        "script",
        "style",
        "svg",
        "template",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self.block_fenced: list[bool] = []
        self.outside_text_positions: list[tuple[int, str]] = []
        self._code_depth = 0
        self._pre_depth = 0
        self._current: list[str] | None = None
        self._current_fenced = False
        self._non_content_depth = 0
        self.invalid_nesting = False

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        del attrs
        normalized = tag.casefold()
        if normalized in self._NON_CONTENT_TAGS:
            self._non_content_depth += 1
        if normalized == "pre":
            self._pre_depth += 1
        if normalized != "code":
            return
        if self._code_depth:
            self.invalid_nesting = True
        else:
            self._current = []
            self._current_fenced = self._pre_depth > 0
        self._code_depth += 1

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.casefold()
        if normalized in self._NON_CONTENT_TAGS:
            if self._non_content_depth == 0:
                self.invalid_nesting = True
            else:
                self._non_content_depth -= 1
        if normalized == "pre":
            if self._pre_depth == 0:
                self.invalid_nesting = True
            else:
                self._pre_depth -= 1
        if normalized != "code":
            return
        if self._code_depth == 0:
            self.invalid_nesting = True
            return
        self._code_depth -= 1
        if self._code_depth == 0:
            assert self._current is not None
            self.blocks.append("".join(self._current))
            self.block_fenced.append(self._current_fenced)
            self._current = None
            self._current_fenced = False

    def handle_data(self, data: str) -> None:
        if self._code_depth and self._current is not None:
            self._current.append(data)
        elif self._non_content_depth == 0 and data.strip():
            self.outside_text_positions.append((len(self.blocks), data))


class _ResponseInspector(HTMLParser):
    """Inspect response text and explicit generated-file button labels."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self.file_controls: set[str] = set()

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.casefold() != "button":
            return
        attributes = {
            key.casefold(): value
            for key, value in attrs
            if isinstance(key, str) and value is not None
        }
        label = attributes.get("aria-label")
        if not isinstance(label, str):
            return
        for prefix in FILE_CONTROL_PREFIXES:
            if not label.startswith(prefix):
                continue
            filename = label[len(prefix) :]
            if _portable_basename(filename):
                self.file_controls.add(filename)
            return
        if "." in label and _portable_basename(label):
            self.file_controls.add(label)

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def _inspect_response_outer_html(
    response_outer_html: bytes,
) -> tuple[str, tuple[str, ...]]:
    try:
        html = response_outer_html.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise ValueError("transport response outerHTML is not strict UTF-8") from exc
    parser = _ResponseInspector()
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:
        raise ValueError("transport response outerHTML could not be parsed") from exc
    return "".join(parser.text), tuple(sorted(parser.file_controls))


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


def _extract_code_block_bytes(
    response_outer_html: bytes,
) -> tuple[
    list[bytes],
    tuple[int, bytes] | None,
    bool,
    tuple[tuple[int, str], ...],
    tuple[bool, ...],
    bool,
]:
    """Return every complete code block and any exact unterminated final block."""

    try:
        html = response_outer_html.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise ValueError("original response outerHTML is not strict UTF-8") from exc
    parser = _CodeBlockTextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:
        raise ValueError("original response outerHTML could not be parsed") from exc
    blocks = [value.encode("utf-8") for value in parser.blocks]
    partial = None
    if parser._current is not None:
        partial = (len(blocks), "".join(parser._current).encode("utf-8"))
    return (
        blocks,
        partial,
        parser.invalid_nesting,
        tuple(parser.outside_text_positions),
        tuple(parser.block_fenced),
        parser._current_fenced,
    )


def _compiler_block_identity(index: int, data: bytes) -> dict[str, Any]:
    return {
        "code_block_index": index,
        "bytes": len(data),
        "sha256": sha256_bytes(data),
    }


def _candidate_transport_error_status(message: str) -> str:
    lowered = message.casefold()
    if any(token in lowered for token in ("duplicate", "collision", "not unique")):
        return "duplicate"
    if any(
        token in lowered
        for token in ("extra", "unexpected", "roster differs")
    ):
        return "extra"
    return "malformed"


def _capture_same_response_transport(
    response_outer_html: bytes,
    *,
    expected_untransported_files: dict[str, bytes] | None = None,
    required_untransported_filenames: Iterable[str] = (),
) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Classify and verify the compiler-v8 block in the original response.

    Candidate-emitted transport defects are returned as evidence states.  Only
    loss or mutation of the original response itself raises a controller error.
    """

    (
        blocks,
        partial,
        invalid_nesting,
        outside_text_positions,
        block_fenced,
        partial_fenced,
    ) = (
        _extract_code_block_bytes(
        response_outer_html
        )
    )
    marker = COMPILER_VERSION.encode("utf-8")
    compiler_stdout_prefix = re.compile(
        rb'^\s*\{\s*"compiler"\s*:\s*"'
        + re.escape(marker)
        + rb'"'
    )

    def looks_like_compiler_stdout(data: bytes) -> bool:
        return compiler_stdout_prefix.match(data) is not None

    candidates = [
        (index, data)
        for index, data in enumerate(blocks)
        if looks_like_compiler_stdout(data)
    ]
    partial_candidate = (
        partial
        if (
            partial is not None
            and looks_like_compiler_stdout(partial[1])
        )
        else None
    )
    identities = [
        _compiler_block_identity(index, data) for index, data in candidates
    ]
    if partial_candidate is not None:
        identities.append(
            _compiler_block_identity(partial_candidate[0], partial_candidate[1])
        )

    base: dict[str, Any] = {
        "status": "missing",
        "candidate_evidence": True,
        "detail": "no compiler-v8 stdout block was present in the completed response",
        "compiler_blocks": identities,
        "compiler": None,
        "transport_version": None,
        "recovery_receipt": None,
    }
    if len(identities) > 1:
        base["status"] = "duplicate"
        base["detail"] = "more than one compiler-v8 stdout block was present"
        return base, {}
    if partial_candidate is not None:
        base["status"] = "truncated"
        base["detail"] = (
            "the compiler-v8 stdout fenced code block was not complete"
            if partial_fenced
            else "the compiler-v8 stdout was not in a fenced code block"
        )
        base["compiler"] = COMPILER_VERSION
        return base, {}
    if not candidates:
        if invalid_nesting:
            base["status"] = "malformed"
            base["detail"] = "response code-block nesting was malformed"
        return base, {}

    candidate_index, compiler_stdout = candidates[0]
    base["compiler"] = COMPILER_VERSION
    if not block_fenced[candidate_index]:
        base["status"] = "malformed"
        base["detail"] = "the compiler-v8 stdout was not in a fenced code block"
        return base, {}
    trailing_text = [
        text
        for completed_blocks, text in outside_text_positions
        if completed_blocks > candidate_index
    ]
    if (
        candidate_index != len(blocks) - 1
        or (partial is not None and partial_candidate is None)
        or trailing_text
    ):
        base["status"] = "extra"
        base["detail"] = (
            "the compiler-v8 stdout block was not the final response content"
        )
        return base, {}
    try:
        parsed = _strict_json_document(compiler_stdout, "compiler stdout")
    except ValueError as exc:
        base["status"] = "malformed"
        base["detail"] = str(exc)
        return base, {}
    if not isinstance(parsed, dict):
        base["status"] = "malformed"
        base["detail"] = "compiler stdout must be one JSON object"
        return base, {}
    transport = parsed.get("transport")
    if isinstance(transport, dict):
        value = transport.get("transport_version")
        if isinstance(value, str):
            base["transport_version"] = value
    if parsed.get("status") == "blocked":
        if (
            set(parsed) == {"compiler", "status", "error"}
            and parsed.get("compiler") == COMPILER_VERSION
            and isinstance(parsed.get("error"), str)
            and parsed["error"]
            and canonical_transport_wrapper_bytes(parsed) == compiler_stdout
        ):
            base["status"] = "blocked"
            base["detail"] = parsed["error"]
        else:
            base["status"] = "malformed"
            base["detail"] = "compiler blocked record differs from the canonical contract"
        return base, {}
    try:
        _, reconstructed, recovery_receipt = (
            parse_compile_transport_stdout_with_receipt(
                compiler_stdout,
                expected_untransported_files=expected_untransported_files,
                required_untransported_filenames=required_untransported_filenames,
            )
        )
    except (TypeError, ValueError) as exc:
        base["status"] = _candidate_transport_error_status(str(exc))
        base["detail"] = str(exc)
        return base, {}
    if invalid_nesting:
        base["status"] = "malformed"
        base["detail"] = "response code-block nesting was malformed"
        return base, {}
    base.update(
        {
            "status": "verified",
            "candidate_evidence": False,
            "detail": (
                "compiler-v8 same-response transport verified"
                if recovery_receipt["state"] == RECOVERY_STATE_NOT_NEEDED
                else (
                    "compiler-v8 same-response transport verified with "
                    f"bounded recovery state {recovery_receipt['state']}"
                )
            ),
            "transport_version": SAME_RESPONSE_TRANSPORT_VERSION,
            "recovery_receipt": recovery_receipt,
        }
    )
    return base, reconstructed


def _strict_export_chunk(
    data: bytes,
    *,
    expected_filename: str | None = None,
    expected_chunk_index: int | None = None,
) -> tuple[dict[str, Any], bytes]:
    """Parse and verify one compiler-emitted canonical transport chunk."""

    document = _strict_json_document(data, "transport chunk wrapper")
    if not isinstance(document, dict) or set(document) != EXPORT_CHUNK_FIELDS:
        raise ValueError("transport chunk wrapper fields differ from the contract")
    if canonical_transport_wrapper_bytes(document) != data:
        raise ValueError("transport chunk wrapper is not canonical compiler stdout")

    filename = document.get("filename")
    payload_size = document.get("payload_size_bytes")
    payload_sha256 = document.get("payload_sha256")
    encoded_size = document.get("encoded_size_bytes")
    encoded_sha256 = document.get("encoded_sha256")
    chunk_index = document.get("chunk_index")
    chunk_count = document.get("chunk_count")
    offset = document.get("offset_bytes")
    chunk_size = document.get("chunk_size_bytes")
    chunk_sha256 = document.get("chunk_sha256")
    encoded_base64 = document.get("base64")
    integer_values = (
        payload_size,
        encoded_size,
        chunk_index,
        chunk_count,
        offset,
        chunk_size,
    )
    if (
        not _portable_basename(filename)
        or document.get("transport_version") != TRANSPORT_CHUNK_VERSION
        or document.get("encoding") != TRANSPORT_ENCODING
        or any(isinstance(value, bool) or not isinstance(value, int) for value in integer_values)
        or payload_size < 0
        or payload_size > MAX_TRANSPORT_PAYLOAD_BYTES
        or encoded_size <= 0
        or encoded_size > MAX_TRANSPORT_ENCODED_BYTES
        or chunk_index < 0
        or chunk_count <= 0
        or offset < 0
        or chunk_size <= 0
        or not isinstance(payload_sha256, str)
        or LOWER_SHA256_RE.fullmatch(payload_sha256) is None
        or not isinstance(encoded_sha256, str)
        or LOWER_SHA256_RE.fullmatch(encoded_sha256) is None
        or not isinstance(chunk_sha256, str)
        or LOWER_SHA256_RE.fullmatch(chunk_sha256) is None
        or not isinstance(encoded_base64, str)
        or not encoded_base64.isascii()
    ):
        raise ValueError("transport chunk wrapper values differ from the contract")
    if expected_filename is not None and filename != expected_filename:
        raise ValueError("transport chunk payload filename differs from its capture name")
    if expected_chunk_index is not None and chunk_index != expected_chunk_index:
        raise ValueError("transport chunk index differs from its capture name")

    expected_count = (encoded_size + TRANSPORT_CHUNK_BYTES - 1) // TRANSPORT_CHUNK_BYTES
    expected_size = min(
        TRANSPORT_CHUNK_BYTES,
        encoded_size - chunk_index * TRANSPORT_CHUNK_BYTES,
    )
    if (
        chunk_count != expected_count
        or not 0 <= chunk_index < chunk_count
        or offset != chunk_index * TRANSPORT_CHUNK_BYTES
        or expected_size <= 0
        or chunk_size != expected_size
        or chunk_size > TRANSPORT_CHUNK_BYTES
    ):
        raise ValueError("transport chunk geometry is invalid")
    try:
        chunk = base64.b64decode(encoded_base64, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("transport chunk Base64 is invalid") from exc
    if (
        base64.b64encode(chunk).decode("ascii") != encoded_base64
        or len(chunk) != chunk_size
        or sha256_bytes(chunk) != chunk_sha256
    ):
        raise ValueError("transport chunk Base64 identity is invalid")
    return document, chunk


def _prompt_identity_from_canonical_wrapper(
    data: bytes,
    *,
    expected_filename: str,
) -> tuple[str, str] | None:
    """Extract only the two first-chunk values needed for the next exact prompt."""

    try:
        document = _strict_json_document(data, "transport chunk wrapper")
    except ValueError:
        return None
    if (
        not isinstance(document, dict)
        or canonical_transport_wrapper_bytes(document) != data
        or document.get("filename") != expected_filename
        or document.get("chunk_index") != 0
        or not isinstance(document.get("payload_sha256"), str)
        or LOWER_SHA256_RE.fullmatch(document["payload_sha256"]) is None
        or not isinstance(document.get("encoded_sha256"), str)
        or LOWER_SHA256_RE.fullmatch(document["encoded_sha256"]) is None
    ):
        return None
    return document["payload_sha256"], document["encoded_sha256"]


def assemble_verified_chunks(wrapper_bytes: Iterable[bytes]) -> tuple[str, bytes]:
    """Verify an ordered complete chunk sequence and return its exact payload."""

    parsed = [_strict_export_chunk(data) for data in wrapper_bytes]
    if not parsed:
        raise ValueError("at least one transport chunk wrapper is required")
    documents = [item[0] for item in parsed]
    chunks = [item[1] for item in parsed]
    first = documents[0]
    repeated_fields = (
        "transport_version",
        "filename",
        "encoding",
        "payload_size_bytes",
        "payload_sha256",
        "encoded_size_bytes",
        "encoded_sha256",
        "chunk_count",
    )
    for document in documents[1:]:
        if any(document[field] != first[field] for field in repeated_fields):
            raise ValueError("transport chunks disagree on repeated payload identity")
    expected_indices = list(range(first["chunk_count"]))
    observed_indices = [document["chunk_index"] for document in documents]
    if observed_indices != expected_indices:
        raise ValueError(
            "transport chunk indices must be complete, contiguous, and ordered"
        )

    encoded = b"".join(chunks)
    if (
        len(encoded) != first["encoded_size_bytes"]
        or sha256_bytes(encoded) != first["encoded_sha256"]
    ):
        raise ValueError("reassembled encoded payload identity is invalid")
    decompressor = zlib.decompressobj()
    try:
        payload = decompressor.decompress(
            encoded,
            first["payload_size_bytes"] + 1,
        )
        if len(payload) > first["payload_size_bytes"] or decompressor.unconsumed_tail:
            raise ValueError("reassembled payload exceeds its declared bounded size")
        payload += decompressor.flush(
            first["payload_size_bytes"] + 1 - len(payload)
        )
    except zlib.error as exc:
        raise ValueError("reassembled encoded payload is not valid zlib") from exc
    if (
        not decompressor.eof
        or decompressor.unused_data
        or decompressor.unconsumed_tail
    ):
        raise ValueError("reassembled payload is not one complete bounded zlib stream")
    if (
        len(payload) != first["payload_size_bytes"]
        or sha256_bytes(payload) != first["payload_sha256"]
    ):
        raise ValueError("reassembled final payload identity is invalid")
    return first["filename"], payload


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


def _discover_indexed_wrappers(root: Path) -> dict[tuple[str, int], Path]:
    wrappers: dict[tuple[str, int], Path] = {}
    for path in root.iterdir():
        if not path.is_file():
            continue
        name = path.name
        parsed = _parse_indexed_name(name, INDEXED_WRAPPER_RE)
        if parsed is None:
            if name.endswith(".export.json") or (
                ".export." in name and name.endswith(".json")
            ):
                raise ValueError(
                    f"active wrapper filename is not canonical indexed transport: {name}"
                )
            continue
        if _is_link_or_junction(path) or parsed in wrappers:
            raise ValueError(f"active wrapper is unsafe or duplicated: {name}")
        wrappers[parsed] = path
    return wrappers


def _discover_transport_attempt_files(
    raw_root: Path,
) -> tuple[
    dict[tuple[str, int], Path],
    dict[tuple[str, int], Path],
]:
    prompts: dict[tuple[str, int], Path] = {}
    responses: dict[tuple[str, int], Path] = {}
    for path in raw_root.iterdir():
        if not path.is_file():
            continue
        parsed_prompt = _parse_indexed_name(path.name, TRANSPORT_PROMPT_RE)
        parsed_response = _parse_indexed_name(path.name, TRANSPORT_RESPONSE_RE)
        if parsed_prompt is not None:
            if parsed_prompt in prompts:
                raise ValueError(f"duplicate transport prompt: {path.name}")
            prompts[parsed_prompt] = path
        if parsed_response is not None:
            if parsed_response in responses:
                raise ValueError(f"duplicate transport response: {path.name}")
            responses[parsed_response] = path
    return prompts, responses


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
        if entry.is_dir() and entry.name not in {
            "raw",
            RECONSTRUCTED_OUTPUT_DIRECTORY,
        }:
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
    active_wrappers = _discover_indexed_wrappers(root)
    _assert_portable_unique_basenames(
        (path.name for path in active_wrappers.values()),
        "active wrapper filenames",
    )
    prompts, responses = _discover_transport_attempt_files(raw_root)
    attempt_keys = set(prompts) | set(responses)
    if set(prompts) != set(responses):
        raise ValueError(
            "every exact transport prompt requires one complete response outerHTML"
        )
    if not set(active_wrappers).issubset(attempt_keys):
        raise ValueError(
            "every active indexed wrapper requires its exact prompt and complete response"
        )
    expected_raw = {PurePosixPath(RAW_RESPONSE_FILENAME).name}
    for payload, chunk_index in attempt_keys:
        _, transport_prompt, transport_response = _transport_capture_names(
            payload,
            chunk_index,
        )
        expected_raw.update(
            {
                PurePosixPath(transport_prompt).name,
                PurePosixPath(transport_response).name,
            }
        )
    for payload, chunk_index in active_wrappers:
        raw_wrapper, transport_prompt, transport_response = _transport_capture_names(
            payload,
            chunk_index,
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
            "raw capture roster must equal response.outerHTML.html, every exact "
            "prompt/complete response pair, and every captured indexed wrapper"
        )
    reconstructed_root = root / RECONSTRUCTED_OUTPUT_DIRECTORY
    if reconstructed_root.exists():
        if (
            _is_link_or_junction(reconstructed_root)
            or not reconstructed_root.is_dir()
            or reconstructed_root.resolve(strict=True).parent
            != root.resolve(strict=True)
        ):
            raise ValueError("reconstructed must be one real in-tree directory")
        for entry in reconstructed_root.iterdir():
            if (
                _is_link_or_junction(entry)
                or not entry.is_file()
                or not _portable_basename(entry.name)
                or entry.parent.resolve(strict=True)
                != reconstructed_root.resolve(strict=True)
            ):
                raise ValueError(
                    f"reconstructed output is not one regular portable file: {entry.name}"
                )


def _legacy_transport_evidence_names(root: Path) -> list[str]:
    """Inventory well-formed historical v3 transport state in a v5 trial."""

    names = [
        path.name
        for path in _discover_indexed_wrappers(root).values()
    ]
    raw_root = root / "raw"
    prompts, responses = _discover_transport_attempt_files(raw_root)
    names.extend(path.name for path in prompts.values())
    names.extend(path.name for path in responses.values())
    return sorted(set(names))


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


def _capture_transport_inventory(
    root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Bind every exact prompt/response attempt and every successful wrapper."""

    validate_closed_evidence_layout(root)
    wrappers = _discover_indexed_wrappers(root)
    prompts, responses = _discover_transport_attempt_files(root / "raw")
    captures: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    captured_provenance_keys: set[tuple[str, int]] = set()
    semantic_invalid_keys: set[tuple[str, int]] = set()
    prompt_identities: dict[str, tuple[str, str]] = {}
    wrapper_documents: dict[tuple[str, int], dict[str, Any]] = {}
    wrapper_bytes: dict[tuple[str, int], bytes] = {}

    for payload, chunk_index in sorted(prompts):
        key = (payload, chunk_index)
        raw_name, prompt_name, response_name = _transport_capture_names(
            payload,
            chunk_index,
        )
        prompt_path = _safe_file(root, prompt_name)
        response_path = _safe_file(root, response_name)
        if prompt_path is None or response_path is None:
            raise ValueError(
                f"transport prompt/response capture is missing or unsafe: {key!r}"
            )
        prompt = _stable_read(prompt_path)
        response = _stable_read(response_path)
        if not response:
            raise ValueError(
                f"complete transport response outerHTML is empty: {key!r}"
            )

        if chunk_index == 0:
            expected_prompt = _legacy_transport_fallback_prompt(payload, 0)
        else:
            first_identity = prompt_identities.get(payload)
            if first_identity is None:
                raise ValueError(
                    f"later transport prompt lacks a captured chunk-0 identity: {key!r}"
                )
            expected_prompt = _legacy_transport_fallback_prompt(
                payload,
                chunk_index,
                expected_payload_sha256=first_identity[0],
                expected_encoded_sha256=first_identity[1],
            )
        if prompt != expected_prompt.encode("utf-8"):
            raise ValueError(
                f"transport prompt differs from the exact controller output: {key!r}"
            )

        _, response_file_controls = _inspect_response_outer_html(response)
        parser_path = wrappers.get(key)
        parser_name: str | None = None
        response_outcome: str
        if parser_path is not None:
            parser_name = _transport_parser_name(payload, chunk_index)
            raw_path = _safe_file(root, raw_name)
            if not _files_are_pairwise_distinct(
                (parser_path, raw_path, prompt_path, response_path)
            ):
                raise ValueError(
                    f"wrapper provenance files are missing or not distinct: {key!r}"
                )
            assert raw_path is not None
            parser = _stable_read(parser_path)
            raw = _stable_read(raw_path)
            if parser != raw:
                raise ValueError(
                    f"raw wrapper differs from the parser input: {key!r}"
                )
            try:
                code = _extract_single_code_block_bytes(response)
            except ValueError as exc:
                raise ValueError(
                    f"captured wrapper response is not one complete code block: {key!r}"
                ) from exc
            if code != raw or code != parser:
                raise ValueError(
                    f"response code block differs from raw/parser bytes: {key!r}"
                )
            captured_provenance_keys.add(key)
            if chunk_index == 0:
                prompt_identity = _prompt_identity_from_canonical_wrapper(
                    parser,
                    expected_filename=payload,
                )
                if prompt_identity is not None:
                    prompt_identities[payload] = prompt_identity
            try:
                document, _ = _strict_export_chunk(
                    parser,
                    expected_filename=payload,
                    expected_chunk_index=chunk_index,
                )
            except (ValueError, TypeError):
                semantic_invalid_keys.add(key)
            else:
                wrapper_documents[key] = document
                wrapper_bytes[key] = parser
            response_outcome = "chunk_wrapper_captured"
            captures.append(
                {
                    "payload_filename": payload,
                    "chunk_index": chunk_index,
                    "raw_filename": raw_name,
                    "parser_input_filename": parser_name,
                    "raw_bytes": len(raw),
                    "raw_sha256": sha256_bytes(raw),
                    "transport_prompt_filename": prompt_name,
                    "transport_prompt_bytes": len(prompt),
                    "transport_prompt_sha256": sha256_bytes(prompt),
                    "transport_response_filename": response_name,
                    "transport_response_bytes": len(response),
                    "transport_response_sha256": sha256_bytes(response),
                }
            )
        else:
            try:
                _extract_single_code_block_bytes(response)
                has_code_block = True
            except ValueError:
                has_code_block = False
            if has_code_block:
                raise ValueError(
                    f"response code block lacks bound raw/parser captures: {key!r}"
                )
            visible_text, _ = _inspect_response_outer_html(response)
            if not has_code_block and not visible_text.strip() and not response_file_controls:
                response_outcome = "blank_response"
            elif not has_code_block and response_file_controls:
                response_outcome = "file_control_only"
            else:
                response_outcome = "invalid_response"
        attempts.append(
            {
                "payload_filename": payload,
                "chunk_index": chunk_index,
                "transport_prompt_filename": prompt_name,
                "transport_prompt_bytes": len(prompt),
                "transport_prompt_sha256": sha256_bytes(prompt),
                "transport_response_filename": response_name,
                "transport_response_bytes": len(response),
                "transport_response_sha256": sha256_bytes(response),
                "response_outcome": response_outcome,
                "response_file_controls": list(response_file_controls),
                "parser_input_filename": parser_name,
            }
        )

    by_payload: dict[str, list[dict[str, Any]]] = {}
    for attempt in attempts:
        by_payload.setdefault(attempt["payload_filename"], []).append(attempt)
    for payload, payload_attempts in by_payload.items():
        indices = [attempt["chunk_index"] for attempt in payload_attempts]
        if indices != list(range(len(indices))):
            raise ValueError(
                f"transport attempts must be contiguous from chunk zero: {payload}"
            )
        first = wrapper_documents.get((payload, 0))
        if first is None:
            if (payload, 0) not in semantic_invalid_keys and len(payload_attempts) != 1:
                raise ValueError(
                    f"failed chunk-zero attempt must be terminal: {payload}"
                )
            continue
        repeated_fields = (
            "transport_version",
            "filename",
            "encoding",
            "payload_size_bytes",
            "payload_sha256",
            "encoded_size_bytes",
            "encoded_sha256",
            "chunk_count",
        )
        semantic_invalid = {
            index
            for candidate_payload, index in semantic_invalid_keys
            if candidate_payload == payload
        }
        for index in indices[1:]:
            document = wrapper_documents.get((payload, index))
            if document is not None and any(
                document[field] != first[field] for field in repeated_fields
            ):
                semantic_invalid.add(index)
        if semantic_invalid:
            if (
                len(semantic_invalid) != 1
                or next(iter(semantic_invalid)) != indices[-1]
            ):
                raise ValueError(
                    f"semantically invalid captured wrapper must be terminal: {payload}"
                )
            continue
        chunk_count = first["chunk_count"]
        if any(index >= chunk_count for index in indices):
            raise ValueError(f"transport attempt exceeds declared chunk count: {payload}")
        failed = [
            attempt
            for attempt in payload_attempts
            if attempt["response_outcome"] != "chunk_wrapper_captured"
        ]
        if failed:
            first_failed_index = failed[0]["chunk_index"]
            if (
                len(failed) != 1
                or first_failed_index != indices[-1]
                or any(
                    attempt["chunk_index"] > first_failed_index
                    for attempt in payload_attempts
                )
            ):
                raise ValueError(
                    f"failed transport attempt must be the terminal attempt: {payload}"
                )
            continue
        if indices != list(range(chunk_count)):
            raise ValueError(
                f"complete transport capture is missing declared chunks: {payload}"
            )
        ordered = [wrapper_bytes[(payload, index)] for index in indices]
        try:
            assembled_filename, _ = assemble_verified_chunks(ordered)
        except (ValueError, TypeError):
            # Exact byte provenance is valid. Aggregate, decompression, and final
            # payload contradictions remain candidate failures for the checker.
            continue
        if assembled_filename != payload:
            raise AssertionError("verified assembler changed the payload filename")
        if _safe_file(root, payload) is None:
            raise ValueError(
                f"complete transport payload was not assembled locally: {payload}"
            )

    if captured_provenance_keys != set(wrappers):
        raise ValueError("active wrapper roster differs from captured wrapper attempts")
    return captures, attempts


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
    try:
        legacy_transport_names = _legacy_transport_evidence_names(root)
    except ValueError:
        legacy_transport_names = []
    if legacy_transport_names:
        issues.append(
            _issue(
                "CONTROLLER_LEGACY_TRANSPORT_EVIDENCE_FORBIDDEN",
                "evidence:$",
                (
                    "controller-v5 trials forbid historical export-chunk prompts, "
                    f"responses, or wrappers: {legacy_transport_names!r}"
                ),
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

    raw_response_bytes: bytes | None = None
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
        raw_response_bytes, raw_issues = _read_bound_file(
            root,
            raw_response,
            path="controller_record.json:$.raw_response",
        )
        issues.extend(raw_issues)
        if (
            raw_response.get("filename") != RAW_RESPONSE_FILENAME
            or not raw_response_bytes
        ):
            issues.append(
                _issue(
                    "CONTROLLER_RAW_RESPONSE_INVALID",
                    "controller_record.json:$.raw_response",
                    "complete raw assistant outerHTML must be preserved at raw/response.outerHTML.html",
                )
            )

    observed_controls = record.get("observed_output_controls")
    observed_controls_contract_valid = not (
        not isinstance(observed_controls, list)
        or any(not _portable_basename(item) for item in observed_controls)
        or observed_controls != sorted(set(observed_controls))
    )
    if not observed_controls_contract_valid:
        issues.append(
            _issue(
                "CONTROLLER_OUTPUT_CONTROL_ROSTER_INVALID",
                "controller_record.json:$.observed_output_controls",
                "observed file-control names must be sorted unique portable filenames",
            )
        )
    elif raw_response_bytes is not None:
        try:
            _, response_controls = _inspect_response_outer_html(raw_response_bytes)
        except ValueError as exc:
            issues.append(
                _issue(
                    "CONTROLLER_OUTPUT_CONTROL_CAPTURE_INVALID",
                    "controller_record.json:$.observed_output_controls",
                    str(exc),
                )
            )
        else:
            if observed_controls != list(response_controls):
                issues.append(
                    _issue(
                        "CONTROLLER_OUTPUT_CONTROL_ROSTER_MISMATCH",
                        "controller_record.json:$.observed_output_controls",
                        "observed controls must equal the portable generated-file "
                        "button aria-labels in the bound response",
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
    expected_direct_output_bytes: dict[str, bytes] = {}
    for filename in sorted(expected_output_filenames):
        path = _safe_file(root, filename)
        if path is not None:
            data = _stable_read(path)
            expected_direct_output_bytes[filename] = data
            expected_outputs.append(output_record(filename, data))
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
    capture = record.get("compiler_transport_capture")
    capture_contract_valid = (
        isinstance(capture, dict)
        and set(capture) == COMPILER_TRANSPORT_CAPTURE_FIELDS
        and capture.get("status") in COMPILER_TRANSPORT_STATUSES
        and isinstance(capture.get("candidate_evidence"), bool)
        and isinstance(capture.get("detail"), str)
        and isinstance(capture.get("compiler_blocks"), list)
        and all(
            isinstance(item, dict)
            and set(item) == COMPILER_BLOCK_IDENTITY_FIELDS
            and isinstance(item.get("code_block_index"), int)
            and not isinstance(item.get("code_block_index"), bool)
            and item["code_block_index"] >= 0
            and isinstance(item.get("bytes"), int)
            and not isinstance(item.get("bytes"), bool)
            and item["bytes"] >= 0
            and isinstance(item.get("sha256"), str)
            and LOWER_SHA256_RE.fullmatch(item["sha256"]) is not None
            for item in capture.get("compiler_blocks", [])
        )
        and capture.get("compiler") in {None, COMPILER_VERSION}
        and capture.get("transport_version")
        in {None, SAME_RESPONSE_TRANSPORT_VERSION}
        and (
            (
                capture.get("status") == "verified"
                and _recovery_receipt_contract_valid(
                    capture.get("recovery_receipt")
                )
            )
            or (
                capture.get("status") != "verified"
                and capture.get("recovery_receipt") is None
            )
        )
    )
    if not capture_contract_valid:
        issues.append(
            _issue(
                "CONTROLLER_COMPILER_CAPTURE_INVALID",
                "controller_record.json:$.compiler_transport_capture",
                "compiler transport capture fields differ from the v5 contract",
            )
        )

    expected_capture: dict[str, Any] | None = None
    expected_reconstructed: dict[str, bytes] = {}
    if raw_response_bytes is not None:
        try:
            expected_input_files: dict[str, bytes] = {}
            required_input_names: set[str] = set()
            for expected_input in expected_inputs:
                filename = (
                    expected_input.get("filename")
                    if isinstance(expected_input, dict)
                    else None
                )
                path = _safe_file(root, filename)
                if isinstance(filename, str) and path is not None:
                    expected_input_files[filename] = _stable_read(path)
                    required_input_names.add(filename)
            expected_capture, expected_reconstructed = (
                _capture_same_response_transport(
                    raw_response_bytes,
                    expected_untransported_files=expected_input_files,
                    required_untransported_filenames=required_input_names,
                )
            )
        except (OSError, TypeError, ValueError) as exc:
            issues.append(
                _issue(
                    "CONTROLLER_COMPILER_CAPTURE_INVALID",
                    "controller_record.json:$.compiler_transport_capture",
                    str(exc),
                )
            )
        else:
            if capture_contract_valid and capture != expected_capture:
                issues.append(
                    _issue(
                        "CONTROLLER_COMPILER_CAPTURE_MISMATCH",
                        "controller_record.json:$.compiler_transport_capture",
                        "compiler block identity or classification differs from the bound original response",
                    )
                )

    reconstructed_outputs = record.get("reconstructed_outputs")
    reconstructed_contract_valid = isinstance(
        reconstructed_outputs, list
    ) and all(
        isinstance(item, dict)
        and set(item) == RECONSTRUCTED_OUTPUT_FIELDS
        for item in reconstructed_outputs
    )
    if not reconstructed_contract_valid:
        issues.append(
            _issue(
                "CONTROLLER_RECONSTRUCTED_OUTPUT_ROSTER_INVALID",
                "controller_record.json:$.reconstructed_outputs",
                "reconstructed output roster differs from the v5 contract",
            )
        )
    else:
        expected_records = [
            _reconstructed_record(filename, data)
            for filename, data in sorted(expected_reconstructed.items())
        ]
        for index, item in enumerate(reconstructed_outputs):
            label = f"controller_record.json:$.reconstructed_outputs[{index}]"
            filename = item.get("filename")
            expected_materialized = (
                f"{RECONSTRUCTED_OUTPUT_DIRECTORY}/{filename}"
                if _portable_basename(filename)
                else None
            )
            if (
                expected_materialized is None
                or item.get("materialized_filename") != expected_materialized
            ):
                issues.append(
                    _issue(
                        "CONTROLLER_RECONSTRUCTED_OUTPUT_FILENAME_INVALID",
                        label,
                        "logical and materialized reconstructed filenames differ",
                    )
                )
                continue
            _, bound_issues = _read_bound_file(
                root,
                item,
                path=label,
                filename_field="materialized_filename",
            )
            issues.extend(bound_issues)
        if reconstructed_outputs != expected_records:
            issues.append(
                _issue(
                    "CONTROLLER_RECONSTRUCTED_OUTPUT_ROSTER_MISMATCH",
                    "controller_record.json:$.reconstructed_outputs",
                    "materialized roster differs from the compiler bundle reconstructed from the original response",
                )
            )

    direct_acquisition_map: dict[str, str] | None = None
    try:
        direct_acquisition_map = _direct_acquisition_map(
            record.get("direct_acquisition_attempts")
        )
        expected_transport = _build_artifact_transport_record(
            reconstructed=expected_reconstructed,
            direct_outputs=expected_direct_output_bytes,
            observed_output_controls=(
                set(observed_controls)
                if observed_controls_contract_valid
                else set()
            ),
            direct_acquisition_attempts=direct_acquisition_map,
        )
    except (TypeError, ValueError) as exc:
        issues.append(
            _issue(
                "CONTROLLER_DIRECT_ACQUISITION_INVALID",
                "controller_record.json:$.direct_acquisition_attempts",
                str(exc),
            )
        )
    else:
        transport_path = _safe_file(root, "artifact_transport.json")
        if (
            transport_path is not None
            and _stable_read(transport_path)
            != canonical_json_bytes(expected_transport)
        ):
            issues.append(
                _issue(
                    "CONTROLLER_ARTIFACT_TRANSPORT_MISMATCH",
                    "artifact_transport.json:$",
                    "transport selection differs from the explicit direct-acquisition observations and bound bytes",
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


def _reconstructed_record(filename: str, data: bytes) -> dict[str, Any]:
    return {
        "filename": filename,
        "materialized_filename": (
            f"{RECONSTRUCTED_OUTPUT_DIRECTORY}/{filename}"
        ),
        "bytes": len(data),
        "sha256": sha256_bytes(data),
    }


def _materialize_reconstructed_outputs(
    root: Path,
    reconstructed: dict[str, bytes],
) -> list[dict[str, Any]]:
    """Create or verify the exact in-turn bundle members under one local root."""

    _assert_portable_unique_basenames(
        reconstructed,
        "reconstructed output filenames",
    )
    destination_root = root / RECONSTRUCTED_OUTPUT_DIRECTORY
    if destination_root.exists() and (
        _is_link_or_junction(destination_root)
        or not destination_root.is_dir()
    ):
        raise ValueError("reconstructed output root is linked or not a directory")
    if destination_root.exists():
        existing = {
            path.name
            for path in destination_root.iterdir()
            if path.is_file() and not _is_link_or_junction(path)
        }
        if existing != set(reconstructed):
            raise ValueError(
                "reconstructed output roster differs from the verified in-turn bundle"
            )
    elif reconstructed:
        destination_root.mkdir()

    records: list[dict[str, Any]] = []
    for filename, data in sorted(reconstructed.items()):
        destination = destination_root / filename
        if destination.exists() or destination.is_symlink():
            if (
                _is_link_or_junction(destination)
                or not destination.is_file()
                or _stable_read(destination) != data
            ):
                raise ValueError(
                    f"materialized reconstructed output differs: {filename}"
                )
        else:
            atomic_write(destination, data)
        if _stable_read(destination) != data:
            raise ValueError(
                f"reconstructed output failed post-write verification: {filename}"
            )
        records.append(_reconstructed_record(filename, data))
    return records


def _write_or_verify_exact(path: Path, data: bytes) -> None:
    """Create one controller artifact, or prove an existing copy is identical."""

    if path.exists() or path.is_symlink():
        if (
            _is_link_or_junction(path)
            or not path.is_file()
            or _stable_read(path) != data
        ):
            raise ValueError(
                f"refusing to overwrite a different controller artifact: {path.name}"
            )
        return
    atomic_write(path, data)


def _build_artifact_transport_record(
    *,
    reconstructed: dict[str, bytes],
    direct_outputs: dict[str, bytes],
    observed_output_controls: set[str],
    direct_acquisition_attempts: dict[str, str],
) -> dict[str, Any]:
    """Derive v3 transport only from explicit controller-bound observations."""

    _assert_portable_unique_basenames(
        reconstructed,
        "reconstructed transport filenames",
    )
    _assert_portable_unique_basenames(
        direct_outputs,
        "direct transport filenames",
    )
    _assert_portable_unique_basenames(
        observed_output_controls,
        "observed transport controls",
    )
    _assert_portable_unique_basenames(
        direct_acquisition_attempts,
        "direct acquisition filenames",
    )
    expected_attempt_names = (
        set(reconstructed) | set(direct_outputs) | observed_output_controls
    )
    if set(direct_acquisition_attempts) != expected_attempt_names:
        raise ValueError(
            "direct acquisition attempts must exactly cover every visible "
            "output control and every available direct or reconstructed output"
        )
    for filename in sorted(expected_attempt_names):
        outcome = direct_acquisition_attempts[filename]
        if filename in direct_outputs:
            expected_outcome = "download_event"
        elif filename in observed_output_controls:
            expected_outcome = "no_download_event"
        else:
            expected_outcome = "unavailable"
        if outcome != expected_outcome:
            raise ValueError(
                f"direct acquisition outcome for {filename} must be "
                f"{expected_outcome}"
            )

    records: list[dict[str, Any]] = []
    transported_names = set(reconstructed) | set(direct_outputs)
    for filename in sorted(transported_names):
        direct_data = direct_outputs.get(filename)
        if direct_data is not None:
            method = "direct_download"
            data = direct_data
        else:
            method = SAME_RESPONSE_TRANSPORT_METHOD
            data = reconstructed[filename]
        records.append(
            {
                "filename": filename,
                "method": method,
                "direct_download_outcome": direct_acquisition_attempts[filename],
                "bytes": len(data),
                "sha256": sha256_bytes(data),
                "export_chunks": None,
            }
        )
    return {
        "transport_version": ARTIFACT_TRANSPORT_VERSION,
        "records": records,
    }


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
    output_control_filenames: Iterable[str] = (),
    direct_acquisition_attempts: Iterable[tuple[str, str]] = (),
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
    input_files: dict[str, bytes] = {}
    for kind, filename in input_specs:
        if not _portable_basename(filename):
            raise ValueError("input filenames must be portable basenames")
        path = _safe_file(root, filename)
        if path is None:
            raise ValueError(f"required input is unavailable: {filename}")
        data = _stable_read(path)
        input_files[filename] = data
        inputs.append(byte_record(kind, filename, data))

    candidate_identity: list[dict[str, Any]] = []
    for kind, filename in CANDIDATE_IDENTITY_FILENAMES:
        path = _safe_file(root, filename)
        if path is None:
            raise ValueError(f"candidate identity is unavailable: {filename}")
        candidate_identity.append(byte_record(kind, filename, _stable_read(path)))

    output_names = list(output_filenames)
    _assert_portable_unique_basenames(output_names, "observed output filenames")
    outputs: list[dict[str, Any]] = []
    output_files: dict[str, bytes] = {}
    for filename in sorted(output_names):
        path = _safe_file(root, filename)
        if path is None:
            raise ValueError(f"observed output is unavailable: {filename}")
        data = _stable_read(path)
        output_files[filename] = data
        outputs.append(output_record(filename, data))

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
    compiler_transport_capture, reconstructed = _capture_same_response_transport(
        raw_response,
        expected_untransported_files=input_files,
        required_untransported_filenames=set(input_files),
    )
    output_control_names = list(output_control_filenames)
    _assert_portable_unique_basenames(
        output_control_names,
        "observed output-control filenames",
    )
    output_control_names = sorted(output_control_names)
    _, response_controls = _inspect_response_outer_html(raw_response)
    if output_control_names != list(response_controls):
        raise ValueError(
            "observed output controls must equal the portable generated-file "
            "button aria-labels in the bound response"
        )
    direct_acquisition_records = _direct_acquisition_records(
        direct_acquisition_attempts
    )
    direct_acquisition_map = _direct_acquisition_map(
        direct_acquisition_records
    )
    transport_record = _build_artifact_transport_record(
        reconstructed=reconstructed,
        direct_outputs=output_files,
        observed_output_controls=set(output_control_names),
        direct_acquisition_attempts=direct_acquisition_map,
    )
    reconstructed_outputs = _materialize_reconstructed_outputs(
        root,
        reconstructed,
    )
    _write_or_verify_exact(
        root / "artifact_transport.json",
        canonical_json_bytes(transport_record),
    )

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
        "observed_output_controls": output_control_names,
        "observed_outputs": outputs,
        "direct_acquisition_attempts": direct_acquisition_records,
        "compiler_transport_capture": compiler_transport_capture,
        "reconstructed_outputs": reconstructed_outputs,
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


def assemble_verified_chunk_files(
    wrapper_paths: Iterable[Path],
    destination: Path,
) -> dict[str, Any]:
    """Assemble verified wrappers and create, or verify, one exact payload file."""

    paths = list(wrapper_paths)
    if not paths:
        raise ValueError("at least one wrapper path is required")
    data: list[bytes] = []
    parsed_names: list[tuple[str, int]] = []
    for path in paths:
        if _is_link_or_junction(path) or not path.is_file():
            raise ValueError(f"wrapper path is missing, linked, or not a file: {path}")
        parsed = _parse_indexed_name(path.name, INDEXED_WRAPPER_RE)
        if parsed is None:
            raise ValueError(f"wrapper path name is not canonical indexed transport: {path}")
        parsed_names.append(parsed)
        data.append(_stable_read(path))
    filename, payload = assemble_verified_chunks(data)
    if parsed_names != [
        (filename, index)
        for index in range(len(parsed_names))
    ]:
        raise ValueError(
            "wrapper path names must match one payload in contiguous index order"
        )
    if destination.name != filename:
        raise ValueError(
            "assembly output basename must equal the wrapper payload filename"
        )
    write_state = "created"
    if destination.exists() or destination.is_symlink():
        if _is_link_or_junction(destination) or not destination.is_file():
            raise ValueError("refusing to replace a linked or non-file payload")
        if _stable_read(destination) != payload:
            raise ValueError("refusing to overwrite an existing different payload")
        write_state = "verified_unchanged"
    else:
        atomic_write(destination, payload)
    if _stable_read(destination) != payload:
        raise ValueError("assembled payload failed post-write verification")
    return {
        "filename": filename,
        "bytes": len(payload),
        "sha256": sha256_bytes(payload),
        "write_state": write_state,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gpt_eval_controller.py",
        description="Build an immutable controller record for one preserved GPT trial",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser(
        "build-record",
        help=(
            "capture exact inputs, candidate identity, direct outputs, and the "
            "compiler-v8 bundle in the original response"
        ),
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
    build.add_argument(
        "--observed-control",
        action="append",
        default=[],
        dest="output_control_filenames",
        help=(
            "portable filename explicitly observed in a matching file-control "
            "button aria-label; repeat for every observed control"
        ),
    )
    build.add_argument(
        "--direct-acquisition",
        action="append",
        default=[],
        type=_direct_acquisition_argument,
        dest="direct_acquisition_attempts",
        metavar="FILENAME=OUTCOME",
        help=(
            "explicit per-file direct acquisition result; OUTCOME is "
            "download_event, no_download_event, or unavailable; repeat for "
            "every visible output control and every direct or reconstructed output"
        ),
    )
    build.add_argument("--session-reference", required=True)
    build.add_argument("--observability-boundary", required=True)
    transport = subparsers.add_parser(
        "transport-request",
        help=(
            "offline historical-v3 diagnostic only; forbidden as a v5 trial "
            "transport or rescue path"
        ),
    )
    transport.add_argument(
        "--offline-historical-v3",
        action="store_true",
        required=True,
        help=(
            "acknowledge that the emitted bytes reproduce historical evidence "
            "and must not be sent in a v5 Preview trial"
        ),
    )
    transport.add_argument(
        "--output",
        required=True,
        dest="payload_filename",
        help="one finalized output basename to acquire through the fallback",
    )
    transport.add_argument("--chunk-index", required=True, type=int)
    transport.add_argument("--expect-payload-sha256")
    transport.add_argument("--expect-encoded-sha256")
    assemble = subparsers.add_parser(
        "assemble-chunks",
        help=(
            "offline historical-v3 diagnostic: verify and assemble one complete "
            "ordered chunk sequence; never establishes download-button identity"
        ),
    )
    assemble.add_argument("wrappers", nargs="+", type=Path)
    assemble.add_argument("--output", required=True, type=Path, dest="destination")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "transport-request":
        try:
            prompt = _legacy_transport_fallback_prompt(
                args.payload_filename,
                args.chunk_index,
                expected_payload_sha256=args.expect_payload_sha256,
                expected_encoded_sha256=args.expect_encoded_sha256,
            )
        except (ValueError, TypeError) as exc:
            print(
                json.dumps(
                    {
                        "controller": "transport_request",
                        "output_version": "3.0",
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
    if args.command == "assemble-chunks":
        try:
            result = assemble_verified_chunk_files(
                args.wrappers,
                args.destination,
            )
        except (OSError, ValueError, TypeError) as exc:
            print(
                json.dumps(
                    {
                        "controller": "assemble_chunks",
                        "output_version": "3.0",
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
                    "controller": "assemble_chunks",
                    "output_version": "3.0",
                    "status": "pass",
                    **result,
                },
                sort_keys=True,
                ensure_ascii=False,
            )
        )
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
            output_control_filenames=args.output_control_filenames,
            direct_acquisition_attempts=args.direct_acquisition_attempts,
        )
        destination = args.evidence_directory / "controller_record.json"
        _write_or_verify_exact(destination, canonical_json_bytes(record))
    except (OSError, ValueError, TypeError) as exc:
        print(
            json.dumps(
                {
                    "controller": "build_record",
                    "output_version": CONTROLLER_RECORD_VERSION,
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
                "output_version": CONTROLLER_RECORD_VERSION,
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
