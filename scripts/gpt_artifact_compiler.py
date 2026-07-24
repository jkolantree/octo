#!/usr/bin/env python3
"""Deterministic, pure-stdlib compiler for Custom GPT audit artifacts.

The Custom GPT must execute this compiler for any machine-record transaction.
It freezes caller-supplied bytes, derives every identity from those bytes,
builds the one runtime ledger, validates execution/evidence topology, and
serializes ``audit_return.json`` last.  The Base64 transport fallback compresses
one stable-read payload and emits only fixed-bound chunks whose identities are
derived from that same byte value.
"""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import os
import re
import shlex
import sys
import unicodedata
import zlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


COMPILER_VERSION = "bsc-gpt-artifact-compiler-v3"
TRANSPORT_CHUNK_VERSION = "bsc-gpt-export-chunk-v1"
TRANSPORT_ENCODING = "zlib+base64"
TRANSPORT_CHUNK_BYTES = 2048
MAX_TRANSPORT_PAYLOAD_BYTES = 64 * 1024 * 1024
MAX_TRANSPORT_ENCODED_BYTES = 65 * 1024 * 1024
MAX_TRANSPORT_CHUNKS = 100_000
EXPORT_CHUNK_FIELDS = {
    "transport_version",
    "filename",
    "encoding",
    "payload_size_bytes",
    "payload_sha256",
    "encoded_size_bytes",
    "encoded_sha256",
    "chunk_index",
    "chunk_count",
    "offset_bytes",
    "chunk_size_bytes",
    "chunk_sha256",
    "base64",
}
RUNTIME_PREFIX = "session_reported_runtime="
RUNTIME_BASIS_LINE = "runtime_provenance=session_reported"
BOUND_RUNTIME_ARTIFACT = "chatgpt_data_analysis_output.txt"
BOUND_REPORT_ARTIFACT = "audit_report.md"
BOUND_RETURN_ARTIFACT = "audit_return.json"
REPORT_RUNTIME_REFERENCE = (
    "Session-reported runtime: see the bound execution-output artifact "
    f"`{BOUND_RUNTIME_ARTIFACT}`; this reference is not independent authentication."
)
REPORT_PROJECTION_MARKER = "## Deterministic audit-return projection"
FULL_SYS_VERSION_RE = re.compile(
    r"^\d+\.\d+\.\d+(?:[A-Za-z0-9.+-]*)? "
    r"\([^\r\n()]+\) \[[^\r\n\[\]]+\]$"
)
ANY_SYS_VERSION_RE = re.compile(
    r"\d+\.\d+\.\d+(?:[A-Za-z0-9.+-]*)? "
    r"\([^\r\n()]+\) \[[^\r\n\[\]]+\]"
)
OUTPUT_RECORD_FIELDS = {"filename", "bytes", "sha256"}
CANONICAL_EXECUTION_ACTIVITIES = (
    "model_reasoning",
    "web_research",
    "independent_source_check",
    "chatgpt_data_analysis",
    "bsc_python_checker",
    "external_proof_tool",
    "empirical_test",
    "proposed_computation",
)
EXECUTION_ROW_FIELDS = {
    "activity",
    "status",
    "tool",
    "version",
    "input_artifact_ids",
    "output_artifact_ids",
    "receipt_ids",
    "notes",
}
EXECUTION_STATUSES = {
    "ran",
    "not_run",
    "reported_but_unverified",
    "not_applicable",
    "file_read_only",
}
CRITICAL_EXECUTION_ACTIVITIES = {
    "bsc_python_checker",
    "external_proof_tool",
    "empirical_test",
}
WINDOWS_RESERVED_BASENAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_transport_wrapper_bytes(value: object) -> bytes:
    """Serialize a transport wrapper without Markdown-sensitive terminal LF."""

    canonical = canonical_json_bytes(value)
    if not canonical.endswith(b"\n"):
        raise AssertionError("canonical JSON artifact bytes must end in LF")
    return canonical[:-1]


def output_record(filename: str, data: bytes) -> dict[str, Any]:
    return {
        "filename": filename,
        "bytes": len(data),
        "sha256": sha256_bytes(data),
    }


def _portable_basename(value: object) -> bool:
    if (
        not isinstance(value, str)
        or not value
        or value != unicodedata.normalize("NFC", value)
        or "\\" in value
        or "/" in value
        or "\x00" in value
    ):
        return False
    pure = PurePosixPath(value)
    if pure.is_absolute() or len(pure.parts) != 1 or pure.as_posix() != value:
        return False
    stem = value.rstrip(" .").split(".", 1)[0].upper()
    return (
        value == value.rstrip(" .")
        and stem not in WINDOWS_RESERVED_BASENAMES
        and ":" not in value
    )


def _assert_unique_basenames(values: Iterable[object], label: str) -> None:
    names = list(values)
    if any(not _portable_basename(value) for value in names):
        raise ValueError(f"{label} must use portable NFC basenames")
    folded = [str(value).casefold() for value in names]
    if len(folded) != len(set(folded)):
        raise ValueError(f"{label} contains a normalized or case-insensitive collision")


def _validate_runtime(value: object) -> str:
    if not isinstance(value, str) or not FULL_SYS_VERSION_RE.fullmatch(value):
        raise ValueError(
            "session-reported runtime must contain the complete sys.version-shaped value"
        )
    return value


def _contains_base64_key(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).casefold() == "base64" or _contains_base64_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_base64_key(item) for item in value)
    return False


def _json_contains_runtime_literal(
    value: Any,
    *,
    structured_runtime_record: dict[str, Any] | None = None,
) -> bool:
    if isinstance(value, str):
        return ANY_SYS_VERSION_RE.search(value) is not None
    if isinstance(value, list):
        return any(
            _json_contains_runtime_literal(
                item,
                structured_runtime_record=structured_runtime_record,
            )
            for item in value
        )
    if isinstance(value, dict):
        return any(
            not (value is structured_runtime_record and key == "version")
            and _json_contains_runtime_literal(
                item,
                structured_runtime_record=structured_runtime_record,
            )
            for key, item in value.items()
        )
    return False


def runtime_ledger_text(
    session_reported_runtime: str,
    artifact_records: Iterable[dict[str, Any]],
) -> str:
    runtime = _validate_runtime(session_reported_runtime)
    normalized: list[tuple[str, int, str]] = []
    for record in artifact_records:
        if not isinstance(record, dict) or set(record) != OUTPUT_RECORD_FIELDS:
            raise ValueError("artifact identity record has unexpected fields")
        filename = record["filename"]
        size = record["bytes"]
        digest = record["sha256"]
        if (
            not _portable_basename(filename)
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
            or not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            raise ValueError("artifact identity record is invalid")
        if filename in {BOUND_RUNTIME_ARTIFACT, BOUND_RETURN_ARTIFACT}:
            raise ValueError("runtime ledger cannot contain its own or return identity")
        normalized.append((filename, size, digest))
    _assert_unique_basenames(
        (filename for filename, _, _ in normalized),
        "artifact identity filenames",
    )
    lines = [
        "bsc_chatgpt_data_analysis_output_version: 2",
        RUNTIME_PREFIX + runtime,
        RUNTIME_BASIS_LINE,
        "finalized_artifacts:",
    ]
    lines.extend(
        f"{digest}  {size}  {filename}"
        for filename, size, digest in sorted(normalized)
    )
    return "\n".join(lines) + "\n"


def parse_runtime_ledger(
    text: str,
) -> tuple[str, tuple[dict[str, Any], ...]]:
    if not isinstance(text, str):
        raise ValueError("execution-output ledger must be text")
    if not text.endswith("\n") or "\r" in text:
        raise ValueError("execution-output ledger must use final LF and no CR")
    lines = text.splitlines()
    if len(lines) < 4 or lines[0] != "bsc_chatgpt_data_analysis_output_version: 2":
        raise ValueError("execution-output ledger header is invalid")
    if lines[2] != RUNTIME_BASIS_LINE or lines.count(RUNTIME_BASIS_LINE) != 1:
        raise ValueError(
            "execution-output ledger must contain runtime_provenance=session_reported once"
        )
    if (
        not lines[1].startswith(RUNTIME_PREFIX)
        or sum(line.startswith(RUNTIME_PREFIX) for line in lines) != 1
    ):
        raise ValueError(
            "execution-output ledger must contain session_reported_runtime=<execution.version> once"
        )
    runtime = _validate_runtime(lines[1][len(RUNTIME_PREFIX) :])
    if lines[3] != "finalized_artifacts:":
        raise ValueError("execution-output ledger artifact header is invalid")
    records: list[dict[str, Any]] = []
    row_re = re.compile(r"^([0-9a-f]{64})  (0|[1-9][0-9]*)  (.+)$")
    for line in lines[4:]:
        match = row_re.fullmatch(line)
        if match is None:
            raise ValueError("execution-output ledger artifact row is invalid")
        digest, size_text, filename = match.groups()
        if not _portable_basename(filename):
            raise ValueError("execution-output ledger filename is not portable")
        if filename in {BOUND_RUNTIME_ARTIFACT, BOUND_RETURN_ARTIFACT}:
            raise ValueError("runtime ledger cannot contain its own or return identity")
        records.append(
            {"filename": filename, "bytes": int(size_text), "sha256": digest}
        )
    _assert_unique_basenames(
        (record["filename"] for record in records),
        "artifact identity filenames",
    )
    if records != sorted(records, key=lambda item: item["filename"]):
        raise ValueError("execution-output ledger artifact rows are not sorted")
    return runtime, tuple(records)


def extract_session_reported_runtime(text: str) -> str:
    return parse_runtime_ledger(text)[0]


def _stable_read_payload(path: Path) -> bytes:
    """Read one payload once and reject an identity change during the read."""

    if isinstance(path, Path):
        is_junction = getattr(path, "is_junction", None)
        if (
            path.is_symlink()
            or (callable(is_junction) and is_junction())
            or not path.is_file()
        ):
            raise ValueError(
                f"export payload must be one regular non-linked file: {path.name}"
            )
    before = path.stat()
    data = path.read_bytes()
    after = path.stat()
    identity_fields = (
        "st_dev",
        "st_ino",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    before_identity = tuple(getattr(before, field, None) for field in identity_fields)
    after_identity = tuple(getattr(after, field, None) for field in identity_fields)
    if (
        before_identity != after_identity
        or isinstance(after.st_size, bool)
        or after.st_size < 0
        or len(data) != after.st_size
    ):
        raise ValueError(f"export payload changed during stable read: {path.name}")
    return data


def _transport_chunks(encoded: bytes) -> tuple[bytes, ...]:
    """Split an encoded payload into a nonempty fixed-bound chunk sequence."""

    if not isinstance(encoded, bytes):
        raise ValueError("encoded transport payload must be exact bytes")
    if not encoded:
        return (b"",)
    return tuple(
        encoded[offset : offset + TRANSPORT_CHUNK_BYTES]
        for offset in range(0, len(encoded), TRANSPORT_CHUNK_BYTES)
    )


def _validate_expected_hash(value: str | None, label: str) -> None:
    if value is not None and (
        not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None
    ):
        raise ValueError(f"{label} must be one lowercase SHA-256")


def export_payload_chunk(
    filename: str,
    data: bytes,
    chunk_index: int,
    *,
    expected_payload_sha256: str | None = None,
    expected_encoded_sha256: str | None = None,
) -> dict[str, Any]:
    """Derive one bounded fallback chunk from one exact payload byte object."""

    if not _portable_basename(filename):
        raise ValueError("export payload filename must be a portable basename")
    if not isinstance(data, bytes):
        raise ValueError("export payload must be exact bytes")
    if len(data) > MAX_TRANSPORT_PAYLOAD_BYTES:
        raise ValueError("export payload exceeds the bounded transport limit")
    if isinstance(chunk_index, bool) or not isinstance(chunk_index, int) or chunk_index < 0:
        raise ValueError("transport chunk index must be a nonnegative integer")
    if chunk_index >= MAX_TRANSPORT_CHUNKS:
        raise ValueError("transport chunk index exceeds the bounded transport limit")
    _validate_expected_hash(
        expected_payload_sha256,
        "expected payload SHA-256",
    )
    _validate_expected_hash(
        expected_encoded_sha256,
        "expected encoded SHA-256",
    )
    if (expected_payload_sha256 is None) != (expected_encoded_sha256 is None):
        raise ValueError("expected payload and encoded SHA-256 values must be paired")
    if chunk_index > 0 and expected_payload_sha256 is None:
        raise ValueError("later transport chunks require both expected SHA-256 values")

    encoded = zlib.compress(data, level=9)
    if len(encoded) > MAX_TRANSPORT_ENCODED_BYTES:
        raise ValueError("encoded payload exceeds the bounded transport limit")
    if zlib.decompress(encoded) != data:
        raise AssertionError("compressed transport payload did not round trip")
    payload_sha256 = sha256_bytes(data)
    encoded_sha256 = sha256_bytes(encoded)
    if (
        expected_payload_sha256 is not None
        and expected_payload_sha256 != payload_sha256
    ):
        raise ValueError("export payload SHA-256 differs from the expected first chunk")
    if (
        expected_encoded_sha256 is not None
        and expected_encoded_sha256 != encoded_sha256
    ):
        raise ValueError("encoded payload SHA-256 differs from the expected first chunk")

    chunks = _transport_chunks(encoded)
    if len(chunks) > MAX_TRANSPORT_CHUNKS:
        raise ValueError("transport chunk count exceeds the bounded transport limit")
    if chunk_index >= len(chunks):
        raise ValueError(
            f"transport chunk index {chunk_index} is outside 0..{len(chunks) - 1}"
        )
    chunk = chunks[chunk_index]
    chunk_base64 = base64.b64encode(chunk).decode("ascii")
    wrapper = {
        "transport_version": TRANSPORT_CHUNK_VERSION,
        "filename": filename,
        "encoding": TRANSPORT_ENCODING,
        "payload_size_bytes": len(data),
        "payload_sha256": payload_sha256,
        "encoded_size_bytes": len(encoded),
        "encoded_sha256": encoded_sha256,
        "chunk_index": chunk_index,
        "chunk_count": len(chunks),
        "offset_bytes": chunk_index * TRANSPORT_CHUNK_BYTES,
        "chunk_size_bytes": len(chunk),
        "chunk_sha256": sha256_bytes(chunk),
        "base64": chunk_base64,
    }
    if set(wrapper) != EXPORT_CHUNK_FIELDS:
        raise AssertionError("derived transport chunk fields differ from the contract")
    decoded = base64.b64decode(chunk_base64, validate=True)
    if (
        decoded != chunk
        or len(decoded) != wrapper["chunk_size_bytes"]
        or len(decoded) > TRANSPORT_CHUNK_BYTES
        or sha256_bytes(decoded) != wrapper["chunk_sha256"]
    ):
        raise AssertionError("derived fallback chunk did not round trip")
    return wrapper


def transport_fallback_prompt(
    filename: str,
    chunk_index: int = 0,
    *,
    expected_payload_sha256: str | None = None,
    expected_encoded_sha256: str | None = None,
) -> str:
    if not _portable_basename(filename):
        raise ValueError("transport payload filename must be a portable basename")
    if isinstance(chunk_index, bool) or not isinstance(chunk_index, int) or chunk_index < 0:
        raise ValueError("transport chunk index must be a nonnegative integer")
    if chunk_index >= MAX_TRANSPORT_CHUNKS:
        raise ValueError("transport chunk index exceeds the bounded transport limit")
    _validate_expected_hash(
        expected_payload_sha256,
        "expected payload SHA-256",
    )
    _validate_expected_hash(
        expected_encoded_sha256,
        "expected encoded SHA-256",
    )
    if (expected_payload_sha256 is None) != (expected_encoded_sha256 is None):
        raise ValueError("expected payload and encoded SHA-256 values must be paired")
    if chunk_index > 0 and expected_payload_sha256 is None:
        raise ValueError("later transport chunks require both expected SHA-256 values")
    command = (
        "python /mnt/data/gpt_artifact_compiler.py export-chunk "
        + shlex.quote(f"/mnt/data/{filename}")
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
        "Do not regenerate or alter that file. "
        "Do not read, trim, normalize, or encode the payload yourself. Execute this "
        f"literal command exactly once: {command} . Return the command's complete "
        "stdout byte-for-byte as the only strict JSON object in one code block. "
        "The canonical stdout has no trailing line feed; do not reimplement it or "
        "reuse a hash, size, ledger row, return field, or "
        "prose value. The controller alone requests later chunk indices using the "
        "payload and encoded SHA-256 values from chunk 0. If the command reports "
        "any failure, emit no chunk and state export_failed. This identifies only "
        "the exported compressed chunk received here and its strictly reconstructed "
        "payload, never unavailable download-button bytes."
    )


def _semantic_report_projection(document: dict[str, Any]) -> dict[str, Any]:
    """Project report-facing semantics from the return object, without identities."""

    execution_projection: list[dict[str, Any]] = []
    for row in document.get("execution", []):
        if not isinstance(row, dict):
            continue
        projected = {
            key: copy.deepcopy(row.get(key))
            for key in (
                "activity",
                "status",
                "tool",
                "version",
                "input_artifact_ids",
                "output_artifact_ids",
                "receipt_ids",
                "notes",
            )
        }
        if row.get("activity") == "chatgpt_data_analysis":
            projected["version"] = None
            projected["version_reference"] = BOUND_RUNTIME_ARTIFACT
        execution_projection.append(projected)
    return {
        "primary_claim_id": copy.deepcopy(document.get("primary_claim_id")),
        "claims": [
            {
                key: copy.deepcopy(claim.get(key))
                for key in (
                    "id",
                    "statement",
                    "research_verdict",
                    "depends_on",
                    "source_ids",
                    "evidence_ids",
                    "fatal_gate_ids",
                )
            }
            for claim in document.get("claims", [])
            if isinstance(claim, dict)
        ],
        "fatal_gates": [
            {
                key: copy.deepcopy(gate.get(key))
                for key in ("id", "state", "evidence_ids", "obligation_ids")
            }
            for gate in document.get("fatal_gates", [])
            if isinstance(gate, dict)
        ],
        "summary_projection": copy.deepcopy(document.get("summary_projection")),
        "execution": execution_projection,
        "unresolved_obligations": [
            {
                key: copy.deepcopy(obligation.get(key))
                for key in ("id", "claim_ids", "gate_ids", "description")
            }
            for obligation in document.get("unresolved_obligations", [])
            if isinstance(obligation, dict)
        ],
    }


def _render_report(
    report_body: str,
    document: dict[str, Any],
) -> bytes:
    if REPORT_PROJECTION_MARKER in report_body:
        raise ValueError(
            "report body must not reproduce the compiler-owned semantic projection"
        )
    projection = canonical_json_bytes(_semantic_report_projection(document)).decode(
        "utf-8"
    )
    report_text = (
        report_body.rstrip()
        + "\n\n"
        + REPORT_PROJECTION_MARKER
        + "\n\n"
        + "This block is generated from the same semantic object serialized in "
        "`audit_return.json`; do not edit it independently.\n\n"
        + "```json\n"
        + projection
        + "```\n\n"
        + REPORT_RUNTIME_REFERENCE
        + "\n"
    )
    return report_text.encode("utf-8")


def _normalize_execution_contract(
    document: dict[str, Any],
    artifacts_by_id: dict[str, dict[str, Any]],
    runtime: str,
) -> None:
    """Canonicalize the complete execution ledger before deriving any output bytes."""

    execution = document.get("execution")
    if not isinstance(execution, list):
        raise ValueError("return template execution must be an array")
    execution_by_activity: dict[str, dict[str, Any]] = {}
    for row in execution:
        if not isinstance(row, dict) or set(row) != EXECUTION_ROW_FIELDS:
            raise ValueError("return template execution rows differ from the strict contract")
        activity = row.get("activity")
        if (
            not isinstance(activity, str)
            or activity not in CANONICAL_EXECUTION_ACTIVITIES
            or activity in execution_by_activity
        ):
            raise ValueError("return template execution roster is invalid")
        execution_by_activity[activity] = row
    if set(execution_by_activity) != set(CANONICAL_EXECUTION_ACTIVITIES):
        raise ValueError("return template must contain every canonical activity exactly once")
    document["execution"] = [
        execution_by_activity[activity]
        for activity in CANONICAL_EXECUTION_ACTIVITIES
    ]

    receipts = document.get("receipts")
    if not isinstance(receipts, list):
        raise ValueError("return template receipts must be an array")
    receipt_ids: set[str] = set()
    for receipt in receipts:
        identifier = receipt.get("id") if isinstance(receipt, dict) else None
        if not isinstance(identifier, str) or not identifier or identifier in receipt_ids:
            raise ValueError("return template receipt roster is invalid")
        receipt_ids.add(identifier)

    artifact_ids = set(artifacts_by_id)
    request_and_source_ids = {
        artifact_id
        for artifact_id, artifact in artifacts_by_id.items()
        if artifact.get("role") in {"request", "source"}
    }
    evidence_and_report_ids = {
        artifact_id
        for artifact_id, artifact in artifacts_by_id.items()
        if artifact.get("role") in {"evidence", "report"}
    }
    data_analysis_output_ids = {
        artifact_id
        for artifact_id, artifact in artifacts_by_id.items()
        if artifact.get("role") in {"evidence", "report", "execution_output"}
    }
    protocol = document.get("protocol")
    protocol_version = protocol.get("version") if isinstance(protocol, dict) else None
    if not isinstance(protocol_version, str) or not protocol_version.strip():
        raise ValueError("return template protocol version is invalid")

    reasoning = execution_by_activity["model_reasoning"]
    reasoning.update(
        status="ran",
        tool="BSC Custom GPT",
        version=protocol_version,
        input_artifact_ids=sorted(request_and_source_ids),
        output_artifact_ids=sorted(evidence_and_report_ids),
        receipt_ids=[],
        notes=(
            "Compiler-owned topology binds the exact request and sources to the "
            "generated evidence and report."
        ),
    )
    analysis = execution_by_activity["chatgpt_data_analysis"]
    analysis.update(
        status="ran",
        tool="ChatGPT Data Analysis",
        version=runtime,
        input_artifact_ids=sorted(request_and_source_ids),
        output_artifact_ids=sorted(data_analysis_output_ids),
        receipt_ids=[],
        notes=(
            "Runtime value is session-reported and bound to "
            f"{BOUND_RUNTIME_ARTIFACT}; it is not independently authenticated."
        ),
    )

    for activity in CANONICAL_EXECUTION_ACTIVITIES:
        if activity in {"model_reasoning", "chatgpt_data_analysis"}:
            continue
        row = execution_by_activity[activity]
        status = row.get("status")
        notes = row.get("notes")
        if status not in EXECUTION_STATUSES:
            raise ValueError(f"{activity} execution status is invalid")
        if not isinstance(notes, str) or not notes.strip():
            raise ValueError(f"{activity} execution notes are invalid")
        for field in ("tool", "version"):
            value = row.get(field)
            if value is not None and (
                not isinstance(value, str) or not value.strip()
            ):
                raise ValueError(f"{activity} execution {field} is invalid")
        for field, allowed in (
            ("input_artifact_ids", artifact_ids),
            ("output_artifact_ids", artifact_ids),
            ("receipt_ids", receipt_ids),
        ):
            values = row.get(field)
            if (
                not isinstance(values, list)
                or any(not isinstance(item, str) for item in values)
                or len(values) != len(set(values))
                or not set(values).issubset(allowed)
            ):
                raise ValueError(f"{activity} execution {field} is invalid")

        outputs = row["output_artifact_ids"]
        row_receipts = row["receipt_ids"]
        if status == "file_read_only":
            raise ValueError("file_read_only is valid only for ChatGPT Data Analysis")
        if activity == "proposed_computation" and status == "ran":
            raise ValueError("proposed_computation cannot be recorded as ran")
        if activity in CRITICAL_EXECUTION_ACTIVITIES and status == "not_applicable":
            if outputs or row_receipts:
                raise ValueError(
                    f"{activity} not_applicable contradicts bound outputs or receipts"
                )
            status = "not_run"
            row["status"] = status

        if status in {"not_run", "not_applicable"}:
            if outputs or row_receipts:
                raise ValueError(
                    f"{activity} unexecuted status contradicts outputs or receipts"
                )
            row["tool"] = None
            row["version"] = None
            row["input_artifact_ids"] = []
        elif status == "reported_but_unverified":
            if outputs or row_receipts:
                raise ValueError(
                    f"{activity} reported_but_unverified cannot bind verified outputs "
                    "or receipts"
                )
        elif status == "ran":
            if (
                not isinstance(row["tool"], str)
                or not row["tool"].strip()
                or not isinstance(row["version"], str)
                or not row["version"].strip()
            ):
                raise ValueError(
                    f"{activity} ran status requires an exact tool and version"
                )
            if not request_and_source_ids.issubset(row["input_artifact_ids"]):
                raise ValueError(
                    f"{activity} ran status must bind the request and every source"
                )
            if not outputs and not row_receipts:
                raise ValueError(
                    f"{activity} ran status needs a bound output or receipt"
                )
            if activity in CRITICAL_EXECUTION_ACTIVITIES and (
                not outputs or not row_receipts
            ):
                raise ValueError(
                    f"{activity} ran status needs both output and receipt bindings"
                )

        for field in (
            "input_artifact_ids",
            "output_artifact_ids",
            "receipt_ids",
        ):
            row[field] = sorted(row[field])


def _validate_execution_contract(
    document: dict[str, Any],
    artifacts_by_id: dict[str, dict[str, Any]],
) -> None:
    receipts = document.get("receipts", [])
    if not isinstance(receipts, list):
        raise ValueError("return template receipts must be an array")
    receipt_ids: set[str] = set()
    for receipt in receipts:
        if not isinstance(receipt, dict) or not isinstance(receipt.get("id"), str):
            raise ValueError("return template receipt roster is invalid")
        if receipt["id"] in receipt_ids:
            raise ValueError("return template receipt identifiers are not unique")
        receipt_ids.add(receipt["id"])
        artifact = artifacts_by_id.get(receipt.get("artifact_id"))
        if artifact is None or artifact.get("role") != "receipt":
            raise ValueError("every receipt must bind a distinct role-receipt artifact")

    execution = document.get("execution")
    if not isinstance(execution, list):
        raise ValueError("return template execution must be an array")
    execution_by_activity: dict[str, dict[str, Any]] = {}
    for row in execution:
        activity = row.get("activity") if isinstance(row, dict) else None
        if (
            not isinstance(activity, str)
            or not activity
            or activity in execution_by_activity
        ):
            raise ValueError("return template execution roster is invalid")
        execution_by_activity[activity] = row
        inputs = row.get("input_artifact_ids")
        outputs = row.get("output_artifact_ids")
        row_receipts = row.get("receipt_ids")
        if (
            not isinstance(inputs, list)
            or not isinstance(outputs, list)
            or not isinstance(row_receipts, list)
            or any(not isinstance(item, str) for item in inputs + outputs + row_receipts)
            or not set(row_receipts).issubset(receipt_ids)
        ):
            raise ValueError("return template execution bindings are invalid")

    if tuple(execution_by_activity) != CANONICAL_EXECUTION_ACTIVITIES:
        raise ValueError("return template execution roster is not canonical")

    request_and_source_ids = {
        artifact_id
        for artifact_id, artifact in artifacts_by_id.items()
        if artifact.get("role") in {"request", "source"}
    }
    evidence_and_report_ids = {
        artifact_id
        for artifact_id, artifact in artifacts_by_id.items()
        if artifact.get("role") in {"evidence", "report"}
    }
    data_analysis_output_ids = {
        artifact_id
        for artifact_id, artifact in artifacts_by_id.items()
        if artifact.get("role") in {"evidence", "report", "execution_output"}
    }
    reasoning = execution_by_activity["model_reasoning"]
    analysis = execution_by_activity["chatgpt_data_analysis"]
    if (
        reasoning.get("status") != "ran"
        or set(reasoning["input_artifact_ids"]) != request_and_source_ids
        or set(reasoning["output_artifact_ids"]) != evidence_and_report_ids
        or reasoning["receipt_ids"]
    ):
        raise ValueError(
            "model_reasoning must bind exactly request and sources as inputs, "
            "evidence and report as outputs, and no receipts"
        )
    if (
        analysis.get("status") != "ran"
        or set(analysis["input_artifact_ids"]) != request_and_source_ids
        or set(analysis["output_artifact_ids"]) != data_analysis_output_ids
        or analysis["receipt_ids"]
    ):
        raise ValueError(
            "chatgpt_data_analysis must bind exactly request and sources as inputs, "
            "evidence, report, and execution output as outputs, and no receipts"
        )
    evidence = document.get("evidence", [])
    if not isinstance(evidence, list):
        raise ValueError("return template evidence must be an array")
    for item in evidence:
        if not isinstance(item, dict) or item.get("status") != "verified":
            continue
        activities = item.get("execution_activities")
        artifact_ids = item.get("artifact_ids")
        if not isinstance(activities, list) or not activities:
            raise ValueError("verified evidence needs an execution activity")
        if not isinstance(artifact_ids, list):
            raise ValueError("verified evidence artifact roster is invalid")
        evidence_output_ids = {
            artifact_id
            for artifact_id in artifact_ids
            if artifacts_by_id.get(artifact_id, {}).get("role") == "evidence"
        }
        for activity in activities:
            row = execution_by_activity.get(activity)
            if row is None or row.get("status") != "ran":
                raise ValueError("verified evidence cites an execution that did not run")
            inputs = row.get("input_artifact_ids")
            outputs = row.get("output_artifact_ids")
            if not isinstance(inputs, list) or not request_and_source_ids.issubset(inputs):
                raise ValueError(
                    "evidence-cited execution must bind request and every source input"
                )
            if (
                evidence_output_ids
                and (
                    not isinstance(outputs, list)
                    or not evidence_output_ids.issubset(outputs)
                )
            ):
                raise ValueError(
                    "evidence-cited execution must output every cited role-evidence artifact"
                )


@dataclass(frozen=True)
class FinalizedArtifactSet:
    files: dict[str, bytes]
    identities: tuple[dict[str, Any], ...]
    audit_return: dict[str, Any]


def finalize_candidate_artifacts(
    *,
    session_reported_runtime: str,
    report_body: str,
    frozen_artifacts: dict[str, bytes],
    audit_return_template: dict[str, Any],
) -> FinalizedArtifactSet:
    """Finalize one acyclic artifact transaction and serialize the return last."""

    runtime = _validate_runtime(session_reported_runtime)
    if not isinstance(report_body, str):
        raise ValueError("report body must be text")
    if runtime in report_body or ANY_SYS_VERSION_RE.search(report_body):
        raise ValueError(
            "report body must reference the bound runtime output, not copy a runtime"
        )
    if not isinstance(frozen_artifacts, dict):
        raise ValueError("frozen artifacts must be a filename-to-bytes mapping")
    _assert_unique_basenames(frozen_artifacts, "frozen artifact filenames")
    if {
        BOUND_REPORT_ARTIFACT,
        BOUND_RUNTIME_ARTIFACT,
        BOUND_RETURN_ARTIFACT,
    } & set(frozen_artifacts):
        raise ValueError("caller must not precreate report, runtime ledger, or return")
    if any(not isinstance(data, bytes) for data in frozen_artifacts.values()):
        raise ValueError("all frozen artifacts must be exact bytes")

    document = copy.deepcopy(audit_return_template)
    if not isinstance(document, dict):
        raise ValueError("return template must be an object")
    if _contains_base64_key(document):
        raise ValueError("Base64 is prohibited from the primary finalization path")
    artifact_rows = document.get("artifacts")
    execution_rows = document.get("execution")
    if not isinstance(artifact_rows, list) or not isinstance(execution_rows, list):
        raise ValueError("return template must contain artifact and execution arrays")

    artifacts_by_filename: dict[str, dict[str, Any]] = {}
    artifacts_by_id: dict[str, dict[str, Any]] = {}
    filenames: list[str] = []
    for row in artifact_rows:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("filename"), str)
            or not isinstance(row.get("id"), str)
            or not row["id"]
            or row["filename"] in artifacts_by_filename
            or row["id"] in artifacts_by_id
        ):
            raise ValueError("return template artifact roster is invalid")
        filenames.append(row["filename"])
        artifacts_by_filename[row["filename"]] = row
        artifacts_by_id[row["id"]] = row
    _assert_unique_basenames(filenames, "return artifact filenames")

    expected_names = set(frozen_artifacts) | {
        BOUND_REPORT_ARTIFACT,
        BOUND_RUNTIME_ARTIFACT,
    }
    if set(artifacts_by_filename) != expected_names:
        raise ValueError("return template artifact roster differs from finalizer inputs")
    report_row = artifacts_by_filename[BOUND_REPORT_ARTIFACT]
    ledger_row = artifacts_by_filename[BOUND_RUNTIME_ARTIFACT]
    if report_row.get("role") != "report" or ledger_row.get("role") != "execution_output":
        raise ValueError("report and runtime ledger roles are invalid")
    for filename, data in frozen_artifacts.items():
        if artifacts_by_filename[filename].get("role") in {"request", "source"}:
            continue
        try:
            text = data.decode("utf-8", errors="strict")
        except UnicodeError:
            continue
        if ANY_SYS_VERSION_RE.search(text):
            raise ValueError(
                "generated text artifact must reference the bound runtime output, "
                f"not copy a runtime: {filename}"
            )

    _normalize_execution_contract(document, artifacts_by_id, runtime)
    analysis = next(
        row
        for row in document["execution"]
        if row["activity"] == "chatgpt_data_analysis"
    )
    if _json_contains_runtime_literal(
        document,
        structured_runtime_record=analysis,
    ):
        raise ValueError(
            "audit_return strings must not copy a runtime outside execution.version"
        )
    _validate_execution_contract(document, artifacts_by_id)

    report_bytes = _render_report(report_body, document)
    prior_files = dict(frozen_artifacts)
    prior_files[BOUND_REPORT_ARTIFACT] = report_bytes
    for filename, data in prior_files.items():
        artifacts_by_filename[filename]["sha256"] = f"sha256:{sha256_bytes(data)}"

    ledger_members = [
        output_record(filename, data)
        for filename, data in prior_files.items()
        if artifacts_by_filename[filename].get("role") not in {"request", "source"}
    ]
    ledger_bytes = runtime_ledger_text(runtime, ledger_members).encode("utf-8")
    ledger_row["sha256"] = f"sha256:{sha256_bytes(ledger_bytes)}"

    files = prior_files
    files[BOUND_RUNTIME_ARTIFACT] = ledger_bytes
    return_bytes = canonical_json_bytes(document)
    files[BOUND_RETURN_ARTIFACT] = return_bytes
    identities = tuple(
        output_record(filename, data) for filename, data in sorted(files.items())
    )
    for filename, data in files.items():
        if sha256_bytes(data) != next(
            item["sha256"] for item in identities if item["filename"] == filename
        ):
            raise AssertionError("post-finalization byte identity changed")
    return FinalizedArtifactSet(
        files=files,
        identities=identities,
        audit_return=document,
    )


def _load_strict_json(path: Path) -> dict[str, Any]:
    def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate key: {key}")
            value[key] = item
        return value

    try:
        text = _stable_read_payload(path).decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise ValueError("compiler spec must be strict UTF-8") from exc
    value = json.loads(
        text,
        object_pairs_hook=strict_object,
        parse_constant=lambda item: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON number: {item}")
        ),
    )
    if not isinstance(value, dict):
        raise ValueError("JSON document must be an object")
    return value


def _compile_from_spec(spec_path: Path, output_dir: Path) -> dict[str, Any]:
    spec = _load_strict_json(spec_path)
    if set(spec) != {
        "report_body",
        "frozen_artifact_paths",
        "audit_return_template",
    }:
        raise ValueError("compiler spec fields differ from the strict contract")
    paths = spec["frozen_artifact_paths"]
    if not isinstance(paths, dict):
        raise ValueError("frozen_artifact_paths must be an object")
    frozen: dict[str, bytes] = {}
    for filename, raw_path in paths.items():
        if not _portable_basename(filename) or not isinstance(raw_path, str):
            raise ValueError("frozen artifact path mapping is invalid")
        frozen[filename] = _stable_read_payload(Path(raw_path))
    # The executed compiler owns the sole runtime capture.  The model-authored
    # spec cannot supply, copy, or override this value.
    session_reported_runtime = sys.version
    finalized = finalize_candidate_artifacts(
        session_reported_runtime=session_reported_runtime,
        report_body=spec["report_body"],
        frozen_artifacts=frozen,
        audit_return_template=spec["audit_return_template"],
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, data in finalized.files.items():
        destination = output_dir / filename
        if filename in frozen:
            if not destination.is_file() or _stable_read_payload(destination) != data:
                raise ValueError(f"frozen output path differs from source bytes: {filename}")
            continue
        temporary = output_dir / f".{filename}.{os.getpid()}.tmp"
        if destination.exists() or destination.is_symlink() or temporary.exists():
            raise ValueError(f"refusing to overwrite an artifact: {filename}")
        try:
            with temporary.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(destination)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
    for filename, data in finalized.files.items():
        if _stable_read_payload(output_dir / filename) != data:
            raise ValueError(f"post-write verification failed: {filename}")
    return {
        "compiler": COMPILER_VERSION,
        "status": "pass",
        "outputs": list(finalized.identities),
        "return_serialized_last": list(finalized.files)[-1] == BOUND_RETURN_ARTIFACT,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compile or export deterministic Custom GPT audit artifacts"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    compile_command = commands.add_parser("compile")
    compile_command.add_argument("--spec", required=True, type=Path)
    compile_command.add_argument("--output-dir", required=True, type=Path)
    export_command = commands.add_parser("export-chunk")
    export_command.add_argument("payload", type=Path)
    export_command.add_argument("--chunk-index", required=True, type=int)
    export_command.add_argument("--expect-payload-sha256")
    export_command.add_argument("--expect-encoded-sha256")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "compile":
            result = _compile_from_spec(args.spec, args.output_dir)
        else:
            payload = _stable_read_payload(args.payload)
            result = export_payload_chunk(
                args.payload.name,
                payload,
                args.chunk_index,
                expected_payload_sha256=args.expect_payload_sha256,
                expected_encoded_sha256=args.expect_encoded_sha256,
            )
    except (OSError, ValueError, TypeError, AssertionError) as exc:
        print(
            json.dumps(
                {
                    "compiler": COMPILER_VERSION,
                    "status": "blocked",
                    "error": str(exc),
                },
                sort_keys=True,
                ensure_ascii=False,
            )
        )
        return 1
    print(canonical_transport_wrapper_bytes(result).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
