from __future__ import annotations

import codecs
import hashlib
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .findings import BLOCKING, Finding, Severity
from .provenance import MAX_ARTIFACT_BYTES, is_placeholder_sha256, resolve_local_artifact, verify_local_artifact


CANONICAL_ACTIVITIES = (
    "model_reasoning",
    "web_research",
    "independent_source_check",
    "chatgpt_data_analysis",
    "bsc_python_checker",
    "external_proof_tool",
    "empirical_test",
    "proposed_computation",
)

EXPECTED_PROTOCOL_VERSION = "0.3.0-alpha.8"
EXPECTED_PROTOCOL_SHA256 = "sha256:f7036ad49643b0d4a7e7b1befa7f8cf9f6c905182dbcc64c8d860938abeda12a"
MAX_RETURN_ARTIFACTS = 32
MAX_RETURN_TOTAL_ARTIFACT_BYTES = 256 * 1024 * 1024

MECHANICAL_ACTIVITIES = {
    "chatgpt_data_analysis",
    "bsc_python_checker",
    "external_proof_tool",
    "empirical_test",
}

EVIDENCE_ARTIFACT_ROLES = {"evidence", "source", "execution_output"}
TEXTUAL_APPLICATION_MEDIA_TYPES = {
    "application/ecmascript",
    "application/javascript",
    "application/json",
    "application/sql",
    "application/xml",
    "application/yaml",
}
ALLOWED_TEXT_CONTROL_BYTES = {0x09, 0x0A, 0x0D}
DATA_ANALYSIS_LEDGER_HEADER = "bsc_chatgpt_data_analysis_output_version: 2"
DATA_ANALYSIS_LEDGER_SECTION = "finalized_artifacts:"
WINDOWS_RESERVED_BASENAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
    "COM¹", "COM²", "COM³", "LPT¹", "LPT²", "LPT³",
}


def _portable_filename(name: str) -> tuple[str, bool]:
    normalized = unicodedata.normalize("NFC", name)
    base = normalized.split(".", 1)[0].rstrip(" .").upper()
    unsafe = (
        normalized in {".", ".."}
        or normalized.endswith((" ", "."))
        or any(ord(character) < 32 or ord(character) == 127 for character in normalized)
        or any(unicodedata.category(character) in {"Cc", "Cf", "Cs", "Zl", "Zp"} for character in normalized)
        or any(ord(character) > 127 and character.lower() != character.upper() for character in normalized)
        or any(character in '<>:"/\\|?*' for character in normalized)
        or base in WINDOWS_RESERVED_BASENAMES
    )
    ascii_folded = "".join(
        chr(ord(character) + 32) if "A" <= character <= "Z" else character
        for character in normalized
    )
    return ascii_folded, unsafe


def _has_visible_text(value: str) -> bool:
    return any(
        not character.isspace() and unicodedata.category(character)[0] not in {"C", "M", "Z"}
        for character in value
    )


def _is_textual_media_type(value: str) -> bool:
    media_type = value.split(";", 1)[0].strip().lower()
    return (
        media_type.startswith("text/")
        or media_type in TEXTUAL_APPLICATION_MEDIA_TYPES
        or media_type.endswith(("+json", "+xml", "+yaml"))
    )


def _has_exact_runtime_binding(
    text: str,
    version: str,
    expected_rows: Iterable[tuple[str, int, str]],
) -> bool:
    normalized_rows = sorted(expected_rows, key=lambda row: row[2])
    expected_lines = [
        DATA_ANALYSIS_LEDGER_HEADER,
        f"session_reported_runtime={version}",
        "runtime_provenance=session_reported",
        DATA_ANALYSIS_LEDGER_SECTION,
        *(
            f"{digest}  {size}  {filename}"
            for digest, size, filename in normalized_rows
        ),
    ]
    return text == "\n".join(expected_lines) + "\n"


def _inspect_text_artifact(
    root: Path,
    filename: str,
    expected_hash: str,
    *,
    max_bytes: int,
    capture_text: bool,
) -> tuple[bool, str, Any | None, str | None]:
    """Re-read a hash-matched textual artifact with strict UTF-8 and byte controls."""

    try:
        candidate = resolve_local_artifact(root, filename)
    except (ValueError, OSError, RuntimeError):
        return False, "unsafe_path", None, None

    digest = hashlib.sha256()
    decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
    decoded_parts: list[str] | None = [] if capture_text else None
    forbidden: list[dict[str, Any]] = []
    bytes_read = 0
    try:
        with candidate.open("rb") as stream:
            while True:
                remaining = max_bytes - bytes_read
                chunk = stream.read(min(1024 * 1024, remaining + 1))
                if not chunk:
                    break
                chunk_offset = bytes_read
                bytes_read += len(chunk)
                if bytes_read > max_bytes:
                    return False, "artifact_too_large", {"max_bytes": max_bytes}, None
                digest.update(chunk)
                if len(forbidden) < 16:
                    for offset, byte in enumerate(chunk):
                        if (byte < 0x20 and byte not in ALLOWED_TEXT_CONTROL_BYTES) or byte == 0x7F:
                            forbidden.append({"offset": chunk_offset + offset, "byte": f"0x{byte:02X}"})
                            if len(forbidden) == 16:
                                break
                decoded = decoder.decode(chunk, final=False)
                if decoded_parts is not None:
                    decoded_parts.append(decoded)
            decoded = decoder.decode(b"", final=True)
            if decoded_parts is not None:
                decoded_parts.append(decoded)
    except UnicodeDecodeError as exc:
        return False, "invalid_utf8", {"error": str(exc)}, None
    except OSError:
        return False, "unreadable_artifact", None, None

    actual_hash = f"sha256:{digest.hexdigest()}"
    if actual_hash != expected_hash:
        return False, "hash_mismatch", {"actual_sha256": actual_hash}, None
    if forbidden:
        return False, "prohibited_control_bytes", forbidden, None
    return True, "verified_text", None, ("".join(decoded_parts) if decoded_parts is not None else None)


def _preflight_return_artifacts(
    artifacts: dict[str, dict[str, Any]],
    root: Path | None,
) -> tuple[dict[str, tuple[str, int | None]], int]:
    """Reserve a bounded, order-independent byte budget before hashing anything."""

    if root is None:
        return ({identifier: ("artifact_root_unavailable", None) for identifier in artifacts}, 0)
    preflight: dict[str, tuple[str, int | None]] = {}
    total_bytes = 0
    for identifier, artifact in artifacts.items():
        try:
            candidate = resolve_local_artifact(root, artifact["filename"])
        except (ValueError, OSError, RuntimeError):
            preflight[identifier] = ("unsafe_path", None)
            continue
        try:
            if not candidate.is_file():
                preflight[identifier] = ("missing_artifact", None)
                continue
            size = candidate.stat().st_size
        except OSError:
            preflight[identifier] = ("unreadable_artifact", None)
            continue
        total_bytes += size
        preflight[identifier] = (("artifact_too_large" if size > MAX_ARTIFACT_BYTES else "ready"), size)
    return preflight, total_bytes


def _finding(
    severity: Severity,
    code: str,
    path: str,
    message: str,
    *,
    witness: Any | None = None,
    repair: str | None = None,
) -> Finding:
    return Finding(severity, code, path, message, witness=witness, repair=repair)


def _index(records: list[dict[str, Any]], label: str, findings: list[Finding]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for position, record in enumerate(records):
        identifier = record["id"]
        if identifier in result:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_DUPLICATE_ID",
                    f"$.{label}.{position}.id",
                    f"duplicate {label} identifier makes references ambiguous",
                    witness=identifier,
                )
            )
        else:
            result[identifier] = record
    return result


def _missing_refs(
    identifiers: Iterable[str],
    index: dict[str, Any],
    path: str,
    kind: str,
    findings: list[Finding],
) -> set[str]:
    missing = {identifier for identifier in identifiers if identifier not in index}
    if missing:
        findings.append(
            _finding(
                Severity.BLOCKED,
                "RETURN_REFERENCE_MISSING",
                path,
                f"one or more referenced {kind} identifiers do not exist",
                witness=sorted(missing),
            )
        )
    return missing


def _binding_mismatch(
    declared: set[str],
    reverse: set[str],
    path: str,
    code: str,
    label: str,
    findings: list[Finding],
) -> None:
    if declared == reverse:
        return
    findings.append(
        _finding(
            Severity.BLOCKED,
            code,
            path,
            f"the two directions of the {label} binding disagree",
            witness={
                "missing_from_forward_record": sorted(reverse - declared),
                "missing_from_reverse_record": sorted(declared - reverse),
            },
            repair="make both identifier lists describe exactly the same bindings",
        )
    )


def _claim_cycles(claims: dict[str, dict[str, Any]]) -> set[str]:
    state: dict[str, int] = {}
    cyclic: set[str] = set()
    for start in claims:
        if state.get(start, 0) != 0:
            continue
        stack: list[tuple[str, int]] = [(start, 0)]
        path: list[str] = []
        positions: dict[str, int] = {}
        while stack:
            identifier, dependency_index = stack[-1]
            if state.get(identifier, 0) == 0:
                state[identifier] = 1
                positions[identifier] = len(path)
                path.append(identifier)
            dependencies = claims[identifier]["depends_on"]
            if dependency_index < len(dependencies):
                dependency = dependencies[dependency_index]
                stack[-1] = (identifier, dependency_index + 1)
                if dependency not in claims:
                    continue
                dependency_state = state.get(dependency, 0)
                if dependency_state == 0:
                    stack.append((dependency, 0))
                elif dependency_state == 1:
                    cyclic.update(path[positions[dependency] :])
                continue
            stack.pop()
            state[identifier] = 2
            positions.pop(identifier, None)
            path.pop()
    return cyclic


def _derive_gate_state(records: list[dict[str, Any]], effective: dict[str, bool]) -> str:
    verified_results = {
        record["result"]
        for record in records
        if effective.get(record["id"], False)
    }
    has_unverified = any(not effective.get(record["id"], False) for record in records)
    decisive = bool(verified_results & {"pass", "fail"})
    if {"pass", "fail"}.issubset(verified_results) or (decisive and "inconclusive" in verified_results):
        return "conflict"
    if "fail" in verified_results:
        return "fail"
    if has_unverified or "inconclusive" in verified_results or not records:
        return "unrun"
    if verified_results == {"pass"}:
        return "pass"
    return "unrun"


def _derive_admission(states: list[str]) -> str:
    if "conflict" in states:
        return "conflict"
    if "fail" in states:
        return "fail"
    if not states or "unrun" in states:
        return "unrun"
    return "pass"


def audit_return_document(raw: dict[str, Any], artifact_root: Path | None) -> list[Finding]:
    """Inspect a draft audit return as a finite, non-admissive consistency object.

    This route validates only the supplied envelope, its local byte bindings, and
    cross-record projections. It never assigns a research verdict, proves a
    claim, verifies external execution merely from prose, or grants deployment.
    """

    findings: list[Finding] = []
    if raw["protocol"]["version"] != EXPECTED_PROTOCOL_VERSION:
        findings.append(
            _finding(
                Severity.BLOCKED,
                "RETURN_PROTOCOL_VERSION_MISMATCH",
                "$.protocol.version",
                "return protocol version differs from the protocol bound to this checker",
                witness={"expected": EXPECTED_PROTOCOL_VERSION, "observed": raw["protocol"]["version"]},
            )
        )
    if raw["protocol"]["sha256"] != EXPECTED_PROTOCOL_SHA256:
        findings.append(
            _finding(
                Severity.BLOCKED,
                "RETURN_PROTOCOL_HASH_MISMATCH",
                "$.protocol.sha256",
                "return protocol hash differs from the protocol bound to this checker",
                witness={"expected": EXPECTED_PROTOCOL_SHA256, "observed": raw["protocol"]["sha256"]},
            )
        )
    claims = _index(raw["claims"], "claims", findings)
    sources = _index(raw["sources"], "sources", findings)
    artifacts = _index(raw["artifacts"], "artifacts", findings)
    evidence = _index(raw["evidence"], "evidence", findings)
    gates = _index(raw["fatal_gates"], "fatal_gates", findings)
    receipts = _index(raw["receipts"], "receipts", findings)
    obligations = _index(raw["unresolved_obligations"], "unresolved_obligations", findings)

    global_ids = Counter(
        identifier
        for index in (claims, sources, artifacts, evidence, gates, receipts, obligations)
        for identifier in index
    )
    collisions = sorted(identifier for identifier, count in global_ids.items() if count > 1)
    if collisions:
        findings.append(
            _finding(
                Severity.BLOCKED,
                "RETURN_GLOBAL_ID_COLLISION",
                "$",
                "record identifiers must be globally unambiguous across all return ledgers",
                witness=collisions,
            )
        )

    semantic_text: list[tuple[str, str | None]] = []
    semantic_text.extend((f"$.claims[{position}].statement", item["statement"]) for position, item in enumerate(raw["claims"]))
    for position, item in enumerate(raw["sources"]):
        semantic_text.append((f"$.sources[{position}].label", item["label"]))
        semantic_text.extend(
            (f"$.sources[{position}].inspected_scope[{text_position}]", value)
            for text_position, value in enumerate(item["inspected_scope"])
        )
        semantic_text.extend(
            (f"$.sources[{position}].omissions[{text_position}]", value)
            for text_position, value in enumerate(item["omissions"])
        )
    semantic_text.extend((f"$.artifacts[{position}].media_type", item["media_type"]) for position, item in enumerate(raw["artifacts"]))
    for position, item in enumerate(raw["execution"]):
        semantic_text.extend(
            (
                (f"$.execution[{position}].tool", item["tool"]),
                (f"$.execution[{position}].version", item["version"]),
                (f"$.execution[{position}].notes", item["notes"]),
            )
        )
    semantic_text.extend(
        (f"$.unresolved_obligations[{position}].statement", item["statement"])
        for position, item in enumerate(raw["unresolved_obligations"])
    )
    for path, value in semantic_text:
        if value is not None and not _has_visible_text(value):
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_SEMANTIC_TEXT_INVISIBLE",
                    path,
                    "human-semantic text must contain a visible letter, number, punctuation mark, or symbol",
                    witness=[f"U+{ord(character):04X}" for character in value],
                )
            )

    artifacts_by_hash: dict[str, list[str]] = {}
    for artifact_id, artifact in artifacts.items():
        artifacts_by_hash.setdefault(artifact["sha256"], []).append(artifact_id)
    hash_aliases = {
        digest: sorted(artifact_ids)
        for digest, artifact_ids in artifacts_by_hash.items()
        if len(artifact_ids) > 1
    }
    if hash_aliases:
        findings.append(
            _finding(
                Severity.BLOCKED,
                "RETURN_ARTIFACT_HASH_ALIAS",
                "$.artifacts",
                "identical bytes cannot be redeclared under multiple artifact identifiers or roles",
                witness=hash_aliases,
                repair="use one artifact identifier for each exact byte sequence and reference it without role laundering",
            )
        )

    execution_counts = Counter(item["activity"] for item in raw["execution"])
    missing_activities = sorted(set(CANONICAL_ACTIVITIES) - set(execution_counts))
    duplicate_activities = sorted(name for name, count in execution_counts.items() if count != 1)
    if missing_activities or duplicate_activities:
        findings.append(
            _finding(
                Severity.BLOCKED,
                "RETURN_EXECUTION_LEDGER_INCOMPLETE",
                "$.execution",
                "the execution ledger must contain each canonical activity exactly once",
                witness={"missing": missing_activities, "not_exactly_once": duplicate_activities},
            )
        )
    execution = {item["activity"]: item for item in raw["execution"] if execution_counts[item["activity"]] == 1}

    primary_id = raw["primary_claim_id"]
    _missing_refs([primary_id], claims, "$.primary_claim_id", "claim", findings)
    if primary_id in claims and not claims[primary_id]["fatal_gate_ids"]:
        findings.append(
            _finding(
                Severity.BLOCKED,
                "RETURN_PRIMARY_CLAIM_GATE_MISSING",
                "$.primary_claim_id",
                "the primary claim must declare at least one independently evaluated fatal gate",
            )
        )

    for claim_id, claim in claims.items():
        _missing_refs(claim["depends_on"], claims, f"$.claims[{claim_id}].depends_on", "claim", findings)
        _missing_refs(claim["source_ids"], sources, f"$.claims[{claim_id}].source_ids", "source", findings)
        _missing_refs(claim["evidence_ids"], evidence, f"$.claims[{claim_id}].evidence_ids", "evidence", findings)
        _missing_refs(claim["fatal_gate_ids"], gates, f"$.claims[{claim_id}].fatal_gate_ids", "fatal gate", findings)
        reverse_evidence = {item_id for item_id, item in evidence.items() if claim_id in item["claim_ids"]}
        _binding_mismatch(
            set(claim["evidence_ids"]),
            reverse_evidence,
            f"$.claims[{claim_id}].evidence_ids",
            "RETURN_CLAIM_EVIDENCE_BINDING_MISMATCH",
            "claim/evidence",
            findings,
        )

    cyclic_claims = sorted(_claim_cycles(claims))
    if cyclic_claims:
        findings.append(
            _finding(
                Severity.BLOCKED,
                "RETURN_CLAIM_DEPENDENCY_CYCLE",
                "$.claims",
                "claim dependencies contain a cycle",
                witness=cyclic_claims,
            )
        )

    artifact_budget_blocked = len(raw["artifacts"]) > MAX_RETURN_ARTIFACTS
    if artifact_budget_blocked:
        findings.append(
            _finding(
                Severity.BLOCKED,
                "RETURN_ARTIFACT_COUNT_LIMIT",
                "$.artifacts",
                "the Python Return Desk refuses to inspect more than its bounded artifact count",
                witness={"maximum": MAX_RETURN_ARTIFACTS, "observed": len(raw["artifacts"])},
                repair="split the material into a smaller explicitly scoped return without omitting relevant evidence",
            )
        )
        artifact_preflight: dict[str, tuple[str, int | None]] = {}
    else:
        artifact_preflight, total_artifact_bytes = _preflight_return_artifacts(artifacts, artifact_root)
        if total_artifact_bytes > MAX_RETURN_TOTAL_ARTIFACT_BYTES:
            artifact_budget_blocked = True
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_ARTIFACT_TOTAL_LIMIT",
                    "$.artifacts",
                    "the Python Return Desk refuses to hash an artifact set above its aggregate byte budget",
                    witness={"maximum_bytes": MAX_RETURN_TOTAL_ARTIFACT_BYTES, "observed_bytes": total_artifact_bytes},
                    repair="reduce the explicitly scoped artifact set without omitting evidence material to the claim",
                )
            )

    request_id = raw["bindings"]["request_artifact_id"]
    report_id = raw["bindings"]["report_artifact_id"]
    filenames: dict[str, str] = {}
    artifact_verified: dict[str, bool] = {}
    verified_artifact_text: dict[str, str] = {}
    bound_report_text: str | None = None
    for artifact_id, artifact in artifacts.items():
        filename = artifact["filename"]
        filename_key, filename_unsafe = _portable_filename(filename)
        if filename_unsafe:
            artifact_verified[artifact_id] = False
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_ARTIFACT_FILENAME_UNSAFE",
                    f"$.artifacts[{artifact_id}].filename",
                    "artifact filenames must be portable basenames without controls, reserved device names, or trailing dot/space",
                    witness=filename,
                )
            )
            continue
        if filename_key in filenames and filenames[filename_key] != artifact_id:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_DUPLICATE_FILENAME",
                    f"$.artifacts[{artifact_id}].filename",
                    "multiple artifact identifiers collide after portable Unicode and case normalization",
                    witness={"filename": filename, "artifact_ids": sorted([filenames[filename_key], artifact_id])},
                )
            )
        else:
            filenames[filename_key] = artifact_id
        if is_placeholder_sha256(artifact["sha256"]):
            artifact_verified[artifact_id] = False
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_ARTIFACT_HASH_PLACEHOLDER",
                    f"$.artifacts[{artifact_id}].sha256",
                    "an all-zero SHA-256 is a placeholder, not a byte binding",
                )
            )
            continue
        if artifact_budget_blocked:
            artifact_verified[artifact_id] = False
            continue
        reason, reserved_size = artifact_preflight.get(artifact_id, ("unreadable_artifact", None))
        if reason == "ready" and reserved_size is not None:
            ok, reason, actual = verify_local_artifact(
                artifact_root,
                filename,
                artifact["sha256"],
                max_bytes=min(MAX_ARTIFACT_BYTES, reserved_size),
            )
        else:
            ok, actual = False, None
        artifact_verified[artifact_id] = ok
        if ok and artifact_root is not None and _is_textual_media_type(artifact["media_type"]):
            text_ok, text_reason, text_witness, captured_text = _inspect_text_artifact(
                artifact_root,
                filename,
                artifact["sha256"],
                max_bytes=min(MAX_ARTIFACT_BYTES, reserved_size),
                capture_text=(
                    artifact_id == report_id
                    or artifact["role"] in {"execution_output", "receipt"}
                ),
            )
            if not text_ok:
                artifact_verified[artifact_id] = False
                if text_reason == "invalid_utf8":
                    findings.append(
                        _finding(
                            Severity.BLOCKED,
                            "RETURN_ARTIFACT_TEXT_ENCODING_INVALID",
                            f"$.artifacts[{artifact_id}]",
                            "a locally hash-matched textual artifact must decode as strict UTF-8",
                            witness=text_witness,
                            repair="re-export the exact textual artifact as strict UTF-8 and update its SHA-256",
                        )
                    )
                elif text_reason == "prohibited_control_bytes":
                    findings.append(
                        _finding(
                            Severity.BLOCKED,
                            "RETURN_ARTIFACT_TEXT_CONTROL_INVALID",
                            f"$.artifacts[{artifact_id}]",
                            "textual artifacts may contain no ASCII control bytes except TAB, LF, and CR",
                            witness=text_witness,
                            repair="remove the prohibited control bytes, re-export, and update the artifact SHA-256",
                        )
                    )
                else:
                    findings.append(
                        _finding(
                            Severity.BLOCKED,
                            "RETURN_ARTIFACT_BINDING_INVALID",
                            f"$.artifacts[{artifact_id}]",
                            "the textual artifact changed or became unreadable during final local inspection",
                            witness={"artifact_id": artifact_id, "reason": text_reason, "detail": text_witness},
                            repair="freeze the exact artifact bytes, recompute SHA-256, and inspect again",
                        )
                    )
                continue
            if captured_text is not None:
                verified_artifact_text[artifact_id] = captured_text
            if artifact_id == report_id:
                bound_report_text = captured_text
        if artifact_verified[artifact_id]:
            continue
        witness: dict[str, Any] = {"artifact_id": artifact_id, "reason": reason}
        if actual is not None:
            witness["actual_sha256"] = actual
        if reason in {"invalid_hash", "placeholder_hash", "unsafe_path", "hash_mismatch"}:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_ARTIFACT_BINDING_INVALID",
                    f"$.artifacts[{artifact_id}]",
                    "the declared artifact path or SHA-256 contradicts the locally inspected bytes",
                    witness=witness,
                    repair="use a safe basename and the exact lowercase SHA-256 of the intended local file",
                )
            )
        else:
            findings.append(
                _finding(
                    Severity.WARNING,
                    "RETURN_ARTIFACT_UNAVAILABLE",
                    f"$.artifacts[{artifact_id}]",
                    "the declared artifact could not be locally inspected; its binding remains unverified",
                    witness=witness,
                    repair="place the exact artifact beside the return JSON and inspect again",
                )
            )

    _missing_refs([request_id], artifacts, "$.bindings.request_artifact_id", "artifact", findings)
    _missing_refs([report_id], artifacts, "$.bindings.report_artifact_id", "artifact", findings)
    if request_id == report_id:
        findings.append(
            _finding(
                Severity.BLOCKED,
                "RETURN_REQUEST_REPORT_ALIAS",
                "$.bindings",
                "request and report must be independently identified artifacts",
            )
        )
    for identifier, expected_role, path in (
        (request_id, "request", "$.bindings.request_artifact_id"),
        (report_id, "report", "$.bindings.report_artifact_id"),
    ):
        if identifier in artifacts and artifacts[identifier]["role"] != expected_role:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_BINDING_ROLE_MISMATCH",
                    path,
                    f"the bound {expected_role} artifact does not declare role {expected_role!r}",
                    witness={"artifact_id": identifier, "actual_role": artifacts[identifier]["role"]},
                )
            )

    for source_id, source in sources.items():
        artifact_id = source["artifact_id"]
        if artifact_id is not None:
            _missing_refs([artifact_id], artifacts, f"$.sources[{source_id}].artifact_id", "artifact", findings)
            if artifact_id in artifacts and artifacts[artifact_id]["role"] != "source":
                findings.append(
                    _finding(
                        Severity.BLOCKED,
                        "RETURN_SOURCE_ARTIFACT_ROLE_MISMATCH",
                        f"$.sources[{source_id}].artifact_id",
                        "a source record must bind an artifact with role 'source'",
                    )
                )
        coverage = source["coverage_state"]
        access = source["access_mode"]
        inspected = source["inspected_scope"]
        omissions = source["omissions"]
        contradiction = False
        if coverage == "fully_inspected":
            contradiction = artifact_id is None or not inspected or bool(omissions) or access in {"citation_only", "unavailable"}
        elif coverage in {"partially_inspected", "possibly_truncated"}:
            contradiction = not omissions
        elif coverage == "missing":
            contradiction = artifact_id is not None or access != "unavailable" or bool(inspected) or not omissions
        elif coverage == "unreadable":
            contradiction = bool(inspected) or not omissions
        if contradiction:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_SOURCE_COVERAGE_CONTRADICTION",
                    f"$.sources[{source_id}]",
                    "source coverage, access, inspected scope, omissions, and artifact binding contradict one another",
                )
            )
        if coverage != "fully_inspected":
            findings.append(
                _finding(
                    Severity.WARNING,
                    "RETURN_SOURCE_COVERAGE_INCOMPLETE",
                    f"$.sources[{source_id}].coverage_state",
                    "incomplete source coverage remains review-needed and is not itself a scientific verdict",
                    witness=coverage,
                )
            )
        if artifact_id is None:
            findings.append(
                _finding(
                    Severity.WARNING,
                    "RETURN_SOURCE_BYTES_UNBOUND",
                    f"$.sources[{source_id}].artifact_id",
                    "the source bytes are not bound to a declared local artifact",
                )
            )

    for evidence_id, record in evidence.items():
        _missing_refs(record["claim_ids"], claims, f"$.evidence[{evidence_id}].claim_ids", "claim", findings)
        _missing_refs(record["gate_ids"], gates, f"$.evidence[{evidence_id}].gate_ids", "fatal gate", findings)
        _missing_refs(record["artifact_ids"], artifacts, f"$.evidence[{evidence_id}].artifact_ids", "artifact", findings)
        _missing_refs(record["receipt_ids"], receipts, f"$.evidence[{evidence_id}].receipt_ids", "receipt", findings)
        if record["status"] == "missing" and record["result"] == "pass":
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_MISSING_EVIDENCE_PASS",
                    f"$.evidence[{evidence_id}]",
                    "missing evidence cannot carry a passing result",
                )
            )
        if record["status"] != "verified":
            findings.append(
                _finding(
                    Severity.WARNING,
                    "RETURN_EVIDENCE_UNVERIFIED",
                    f"$.evidence[{evidence_id}].status",
                    "unverified or missing evidence remains review-needed and cannot pass a fatal gate",
                )
            )

    for gate_id, gate in gates.items():
        _missing_refs(gate["evidence_ids"], evidence, f"$.fatal_gates[{gate_id}].evidence_ids", "evidence", findings)
        _missing_refs(gate["obligation_ids"], obligations, f"$.fatal_gates[{gate_id}].obligation_ids", "obligation", findings)
        reverse_evidence = {item_id for item_id, item in evidence.items() if gate_id in item["gate_ids"]}
        _binding_mismatch(
            set(gate["evidence_ids"]),
            reverse_evidence,
            f"$.fatal_gates[{gate_id}].evidence_ids",
            "RETURN_GATE_EVIDENCE_BINDING_MISMATCH",
            "gate/evidence",
            findings,
        )
        owning_claim_ids = {claim_id for claim_id, claim in claims.items() if gate_id in claim["fatal_gate_ids"]}
        if not owning_claim_ids:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_GATE_OWNER_MISSING",
                    f"$.fatal_gates[{gate_id}]",
                    "every fatal gate must be owned by at least one declared claim",
                )
            )
        scope_mismatches = sorted(
            evidence_id
            for evidence_id in set(gate["evidence_ids"]) | reverse_evidence
            if evidence_id in evidence and not owning_claim_ids.issubset(evidence[evidence_id]["claim_ids"])
        )
        if scope_mismatches:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_GATE_CLAIM_SCOPE_MISMATCH",
                    f"$.fatal_gates[{gate_id}].evidence_ids",
                    "every evidence record used to derive a gate must bind every claim that declares that gate",
                    witness={"claim_ids": sorted(owning_claim_ids), "evidence_ids": scope_mismatches},
                )
            )
        omitted_failures = sorted(
            item_id
            for item_id in reverse_evidence - set(gate["evidence_ids"])
            if evidence[item_id]["result"] == "fail"
        )
        if omitted_failures:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_CONCEALED_GATE_FAILURE",
                    f"$.fatal_gates[{gate_id}].evidence_ids",
                    "the gate record omits failing evidence that binds itself to this gate",
                    witness=omitted_failures,
                )
            )
        reverse_obligations = {item_id for item_id, item in obligations.items() if gate_id in item["gate_ids"]}
        _binding_mismatch(
            set(gate["obligation_ids"]),
            reverse_obligations,
            f"$.fatal_gates[{gate_id}].obligation_ids",
            "RETURN_GATE_OBLIGATION_BINDING_MISMATCH",
            "gate/obligation",
            findings,
        )

    for obligation_id, obligation in obligations.items():
        _missing_refs(obligation["claim_ids"], claims, f"$.unresolved_obligations[{obligation_id}].claim_ids", "claim", findings)
        _missing_refs(obligation["gate_ids"], gates, f"$.unresolved_obligations[{obligation_id}].gate_ids", "fatal gate", findings)
        _missing_refs(obligation["evidence_ids"], evidence, f"$.unresolved_obligations[{obligation_id}].evidence_ids", "evidence", findings)
        declared_claim_ids = set(obligation["claim_ids"])
        declared_gate_ids = set(obligation["gate_ids"])
        owning_claim_ids = {
            claim_id
            for claim_id, claim in claims.items()
            if declared_gate_ids & set(claim["fatal_gate_ids"])
        }
        if (
            not declared_claim_ids
            or not declared_gate_ids
            or declared_claim_ids != owning_claim_ids
        ):
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_OBLIGATION_SCOPE_MISMATCH",
                    f"$.unresolved_obligations[{obligation_id}]",
                    "an unresolved obligation must bind exactly the claims that own its declared fatal gates",
                    witness={
                        "declared_claim_ids": sorted(declared_claim_ids),
                        "declared_gate_ids": sorted(declared_gate_ids),
                        "gate_owner_claim_ids": sorted(owning_claim_ids),
                    },
                )
            )
        evidence_scope_failures: dict[str, list[str]] = {}
        for evidence_id in obligation["evidence_ids"]:
            evidence_record = evidence.get(evidence_id)
            if evidence_record is None:
                continue
            failures: list[str] = []
            if not declared_claim_ids.issubset(evidence_record["claim_ids"]):
                failures.append("obligation_claim_scope_not_covered")
            if not (declared_gate_ids & set(evidence_record["gate_ids"])):
                failures.append("obligation_gate_scope_not_covered")
            if failures:
                evidence_scope_failures[evidence_id] = failures
        if evidence_scope_failures:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_OBLIGATION_SCOPE_MISMATCH",
                    f"$.unresolved_obligations[{obligation_id}].evidence_ids",
                    "evidence cited by an unresolved obligation must cover its claim scope and at least one declared gate",
                    witness=evidence_scope_failures,
                )
            )

    receipt_artifact_counts = Counter(receipt["artifact_id"] for receipt in receipts.values())
    reused_receipt_artifacts = {
        artifact_id for artifact_id, count in receipt_artifact_counts.items() if count > 1
    }
    if reused_receipt_artifacts:
        findings.append(
            _finding(
                Severity.BLOCKED,
                "RETURN_RECEIPT_ARTIFACT_REUSED",
                "$.receipts",
                "one receipt artifact cannot be relabeled as multiple receipt records",
                witness=sorted(reused_receipt_artifacts),
                repair="use one receipt record with every applicable claim and gate binding",
            )
        )

    receipt_execution_activities = {
        receipt_id: sorted(
            activity
            for activity, record in execution.items()
            if receipt_id in record["receipt_ids"]
        )
        for receipt_id in receipts
    }
    receipt_execution_binding_ok: dict[str, bool] = {}
    for receipt_id, receipt in receipts.items():
        activities = receipt_execution_activities[receipt_id]
        if len(activities) > 1:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_EXECUTION_RECEIPT_REUSED",
                    f"$.receipts[{receipt_id}]",
                    "one receipt cannot serve as the execution record for multiple activities",
                    witness=activities,
                )
            )
        bound_to_one_ran_execution = (
            len(activities) == 1 and execution[activities[0]]["status"] == "ran"
        )
        receipt_execution_binding_ok[receipt_id] = bound_to_one_ran_execution
        if (
            receipt["status"] == "verified"
            and receipt["authority"] == "execution_record"
            and receipt["kind"] != "adapter_receipt"
            and not bound_to_one_ran_execution
        ):
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_RECEIPT_EXECUTION_BINDING_INVALID",
                    f"$.receipts[{receipt_id}]",
                    "a verified execution record must bind exactly one execution activity recorded as ran",
                    witness=activities,
                )
            )

    receipt_effective: dict[str, bool] = {}
    for receipt_id, receipt in receipts.items():
        _missing_refs([receipt["artifact_id"]], artifacts, f"$.receipts[{receipt_id}].artifact_id", "artifact", findings)
        _missing_refs(receipt["claim_ids"], claims, f"$.receipts[{receipt_id}].claim_ids", "claim", findings)
        _missing_refs(receipt["gate_ids"], gates, f"$.receipts[{receipt_id}].gate_ids", "fatal gate", findings)
        artifact = artifacts.get(receipt["artifact_id"])
        role_ok = artifact is not None and artifact["role"] == "receipt"
        if artifact is not None and not role_ok:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_RECEIPT_ARTIFACT_ROLE_MISMATCH",
                    f"$.receipts[{receipt_id}].artifact_id",
                    "a receipt must bind an artifact with role 'receipt'",
                )
            )
        if receipt["kind"] == "adapter_receipt" and receipt["authority"] == "execution_record":
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_ADAPTER_AUTHORITY_OVERREACH",
                    f"$.receipts[{receipt_id}].authority",
                    "a submitted adapter receipt is non-admissive provenance, not independently established execution",
                )
            )
        receipt_effective[receipt_id] = (
            receipt["status"] == "verified"
            and receipt["authority"] == "execution_record"
            and receipt["kind"] != "adapter_receipt"
            and role_ok
            and receipt["artifact_id"] not in reused_receipt_artifacts
            and receipt_execution_binding_ok[receipt_id]
            and artifact_verified.get(receipt["artifact_id"], False)
        )
        if receipt["status"] != "verified":
            findings.append(
                _finding(
                    Severity.WARNING,
                    "RETURN_RECEIPT_UNVERIFIED",
                    f"$.receipts[{receipt_id}].status",
                    "an unverified or missing receipt cannot support an execution claim",
                )
            )

    for activity, record in execution.items():
        _missing_refs(record["input_artifact_ids"], artifacts, f"$.execution[{activity}].input_artifact_ids", "artifact", findings)
        _missing_refs(record["output_artifact_ids"], artifacts, f"$.execution[{activity}].output_artifact_ids", "artifact", findings)
        _missing_refs(record["receipt_ids"], receipts, f"$.execution[{activity}].receipt_ids", "receipt", findings)
        status = record["status"]
        if status == "file_read_only" and activity != "chatgpt_data_analysis":
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_FILE_READ_STATUS_MISUSED",
                    f"$.execution[{activity}].status",
                    "file_read_only is valid only for ChatGPT Data Analysis file access",
                )
            )
        if activity in {"bsc_python_checker", "external_proof_tool", "empirical_test"} and status == "not_applicable":
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_EXECUTION_NOT_APPLICABLE_MISUSED",
                    f"$.execution[{activity}].status",
                    "an unexecuted BSC checker, external proof tool, or empirical test must be recorded as not_run, never not_applicable",
                    witness=activity,
                )
            )
        if status == "ran" and activity != "model_reasoning":
            version = record["version"]
            support_artifact_ids = set(record["output_artifact_ids"])
            support_artifact_ids.update(
                receipts[receipt_id]["artifact_id"]
                for receipt_id in record["receipt_ids"]
                if receipt_id in receipts
            )
            version_artifact_ids = sorted(
                artifact_id
                for artifact_id in support_artifact_ids
                if (
                    isinstance(version, str)
                    and version in verified_artifact_text.get(artifact_id, "")
                )
            )
            if not version_artifact_ids:
                findings.append(
                    _finding(
                        Severity.BLOCKED,
                        "RETURN_EXECUTION_VERSION_UNBOUND",
                        f"$.execution[{activity}].version",
                        "the exact version for every ran non-model activity must appear in a locally verified bound execution output or receipt",
                        witness={
                            "activity": activity,
                            "version": version,
                            "support_artifact_ids": sorted(support_artifact_ids),
                            "text_artifact_ids": sorted(
                                support_artifact_ids & set(verified_artifact_text)
                            ),
                        },
                    )
                )
            support_references = sorted(
                {
                    reference
                    for artifact_id in version_artifact_ids
                    if artifact_id in artifacts
                    for reference in (
                        artifact_id,
                        artifacts[artifact_id]["filename"],
                    )
                }
            )
            if (
                bound_report_text is None
                or not any(
                    reference in bound_report_text
                    for reference in support_references
                )
            ):
                findings.append(
                    _finding(
                        Severity.BLOCKED,
                        "RETURN_EXECUTION_OUTPUT_NOT_REFERENCED",
                        f"$.execution[{activity}]",
                        "the verified human report must reference a bound version-bearing execution output or receipt instead of independently reproducing its version",
                        witness={
                            "activity": activity,
                            "report_artifact_id": report_id,
                            "report_text_verified": bound_report_text is not None,
                            "accepted_references": support_references,
                        },
                    )
                )
            if activity == "chatgpt_data_analysis":
                runtime_artifact_ids = sorted(
                    artifact_id
                    for artifact_id in record["output_artifact_ids"]
                    if (
                        artifact_id in artifacts
                        and artifacts[artifact_id]["role"] == "execution_output"
                        and artifacts[artifact_id]["filename"]
                        == "chatgpt_data_analysis_output.txt"
                    )
                )
                runtime_texts = [
                    verified_artifact_text.get(artifact_id)
                    for artifact_id in runtime_artifact_ids
                ]
                runtime_ledger_rows: list[tuple[str, int, str]] = []
                runtime_ledger_members_verified = True
                runtime_artifact_id = (
                    runtime_artifact_ids[0]
                    if len(runtime_artifact_ids) == 1
                    else None
                )
                for artifact_id in record["output_artifact_ids"]:
                    if artifact_id == runtime_artifact_id:
                        continue
                    artifact = artifacts.get(artifact_id)
                    if artifact is None or artifact["role"] in {"request", "source"}:
                        continue
                    reason, size = artifact_preflight.get(
                        artifact_id, ("unreadable_artifact", None)
                    )
                    if (
                        reason != "ready"
                        or size is None
                        or not artifact_verified.get(artifact_id, False)
                    ):
                        runtime_ledger_members_verified = False
                        continue
                    runtime_ledger_rows.append(
                        (
                            artifact["sha256"].removeprefix("sha256:"),
                            size,
                            artifact["filename"],
                        )
                    )
                runtime_binding_ok = (
                    len(runtime_artifact_ids) == 1
                    and len(runtime_texts) == 1
                    and isinstance(runtime_texts[0], str)
                    and isinstance(version, str)
                    and runtime_ledger_members_verified
                    and _has_exact_runtime_binding(
                        runtime_texts[0], version, runtime_ledger_rows
                    )
                )
                if not runtime_binding_ok:
                    findings.append(
                        _finding(
                            Severity.BLOCKED,
                            "RETURN_DATA_ANALYSIS_RUNTIME_BINDING_INVALID",
                            f"$.execution[{activity}]",
                            "ChatGPT Data Analysis must bind one verified chatgpt_data_analysis_output.txt that deterministically projects the structured version as a session-reported, not independently authenticated runtime",
                            witness={
                                "runtime_artifact_ids": runtime_artifact_ids,
                                "structured_version": version,
                            },
                        )
                    )
        if activity == "proposed_computation" and status in {"ran", "file_read_only"}:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_PROPOSED_COMPUTATION_RAN",
                    f"$.execution[{activity}].status",
                    "a proposed-only computation cannot simultaneously be recorded as executed",
                )
            )
        if status in {"not_run", "not_applicable", "file_read_only"} and (record["output_artifact_ids"] or record["receipt_ids"]):
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_EXECUTION_STATUS_CONTRADICTION",
                    f"$.execution[{activity}]",
                    "an unexecuted or read-only activity cannot declare execution outputs or receipts",
                )
            )
        if status == "reported_but_unverified":
            findings.append(
                _finding(
                    Severity.WARNING,
                    "RETURN_EXECUTION_UNVERIFIED",
                    f"$.execution[{activity}]",
                    "execution is reported but lacks an adequate verified record",
                )
            )

    execution_effective: dict[str, bool] = {}
    for activity, record in execution.items():
        if activity == "model_reasoning":
            execution_effective[activity] = record["status"] == "ran"
            continue
        if record["status"] != "ran" or activity == "proposed_computation":
            execution_effective[activity] = False
            continue
        inputs_ok = bool(record["input_artifact_ids"]) and all(
            artifact_verified.get(identifier, False) for identifier in record["input_artifact_ids"]
        )
        outputs_ok = bool(record["output_artifact_ids"]) and all(
            artifact_verified.get(identifier, False) for identifier in record["output_artifact_ids"]
        )
        receipts_ok = bool(record["receipt_ids"]) and all(receipt_effective.get(identifier, False) for identifier in record["receipt_ids"])
        allowed_receipt_kinds = {
            "web_research": {"citation_access"},
            "independent_source_check": {"citation_access"},
            "chatgpt_data_analysis": {"chatgpt_tool_output"},
            "bsc_python_checker": {"bsc_cli_output"},
            "external_proof_tool": {"external_tool_transcript"},
            "empirical_test": {"empirical_record"},
        }.get(activity, set())
        receipt_kinds_ok = all(
            identifier in receipts and receipts[identifier]["kind"] in allowed_receipt_kinds
            for identifier in record["receipt_ids"]
        )
        tool_ok = (
            isinstance(record["tool"], str)
            and bool(record["tool"].strip())
            and isinstance(record["version"], str)
            and bool(record["version"].strip())
        )
        if activity in {"bsc_python_checker", "external_proof_tool", "empirical_test"}:
            record_ok = outputs_ok and receipts_ok and receipt_kinds_ok
        elif record["receipt_ids"]:
            record_ok = receipts_ok and receipt_kinds_ok
        else:
            record_ok = outputs_ok
        execution_effective[activity] = inputs_ok and tool_ok and record_ok
        if not execution_effective[activity]:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_EXECUTION_RECORD_INADEQUATE",
                    f"$.execution[{activity}]",
                    "status 'ran' requires bound inputs, a named versioned tool, and a verified output or admissible execution record",
                )
            )

    receipt_scope_ok: dict[str, bool] = {}
    for receipt_id, receipt in receipts.items():
        citing_evidence = [record for record in evidence.values() if receipt_id in record["receipt_ids"]]
        if not citing_evidence:
            receipt_scope_ok[receipt_id] = True
            continue
        claim_scope = {claim_id for record in citing_evidence for claim_id in record["claim_ids"]}
        gate_scope = {gate_id for record in citing_evidence for gate_id in record["gate_ids"]}
        receipt_scope_ok[receipt_id] = (
            set(receipt["claim_ids"]) == claim_scope and set(receipt["gate_ids"]) == gate_scope
        )
        if not receipt_scope_ok[receipt_id]:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_RECEIPT_SCOPE_MISMATCH",
                    f"$.receipts[{receipt_id}]",
                    "receipt claim and gate scope must equal the union of evidence records that cite it",
                    witness={
                        "declared_claim_ids": sorted(receipt["claim_ids"]),
                        "evidence_claim_ids": sorted(claim_scope),
                        "declared_gate_ids": sorted(receipt["gate_ids"]),
                        "evidence_gate_ids": sorted(gate_scope),
                    },
                )
            )

    evidence_effective: dict[str, bool] = {}
    for evidence_id, record in evidence.items():
        artifact_ids = record["artifact_ids"]
        artifact_id_set = set(artifact_ids)
        artifacts_ok = bool(artifact_ids) and all(artifact_verified.get(identifier, False) for identifier in artifact_ids)
        invalid_role_artifacts = sorted(
            identifier
            for identifier in artifact_ids
            if identifier in artifacts and artifacts[identifier]["role"] not in EVIDENCE_ARTIFACT_ROLES | {"receipt"}
        )
        if invalid_role_artifacts:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_EVIDENCE_ARTIFACT_ROLE_INVALID",
                    f"$.evidence[{evidence_id}].artifact_ids",
                    "evidence artifacts may use only evidence, source, execution_output, or receipt roles",
                    witness=invalid_role_artifacts,
                )
            )

        source_scope_failures: list[str] = []
        for identifier in artifact_ids:
            if identifier not in artifacts or artifacts[identifier]["role"] != "source":
                continue
            matching_source_ids = {source_id for source_id, source in sources.items() if source["artifact_id"] == identifier}
            if any(
                claim_id not in claims or not (matching_source_ids & set(claims[claim_id]["source_ids"]))
                for claim_id in record["claim_ids"]
            ):
                source_scope_failures.append(identifier)
        if source_scope_failures:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_EVIDENCE_SOURCE_SCOPE_MISMATCH",
                    f"$.evidence[{evidence_id}].artifact_ids",
                    "a source artifact used as evidence must be declared by every claim it supports",
                    witness=sorted(source_scope_failures),
                )
            )

        execution_output_failures = sorted(
            identifier
            for identifier in artifact_ids
            if identifier in artifacts
            and artifacts[identifier]["role"] == "execution_output"
            and not any(
                activity in execution and identifier in execution[activity]["output_artifact_ids"]
                for activity in record["execution_activities"]
            )
        )
        if execution_output_failures:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_EVIDENCE_OUTPUT_SCOPE_MISMATCH",
                    f"$.evidence[{evidence_id}].artifact_ids",
                    "an execution-output artifact must be an output of an execution activity cited by the evidence",
                    witness=execution_output_failures,
                )
            )
        verified_evidence_output_failures = sorted(
            identifier
            for identifier in artifact_ids
            if record["status"] == "verified"
            and identifier in artifacts
            and artifacts[identifier]["role"] == "evidence"
            and not any(
                activity in execution and identifier in execution[activity]["output_artifact_ids"]
                for activity in record["execution_activities"]
            )
        )
        if verified_evidence_output_failures:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_EVIDENCE_SUPPORT_OUTPUT_MISMATCH",
                    f"$.evidence[{evidence_id}].artifact_ids",
                    "every role=evidence artifact in a verified evidence record must be an output of a cited execution activity",
                    witness=verified_evidence_output_failures,
                )
            )
        receipt_ids = record["receipt_ids"]
        receipts_ok = all(receipt_effective.get(identifier, False) for identifier in receipt_ids)
        activities_ok = bool(record["execution_activities"]) and all(
            execution_effective.get(activity, False) for activity in record["execution_activities"]
        )
        unbound_activities: list[str] = []
        input_unbound_activities: list[str] = []
        required_inputs = {request_id}
        for claim_id in record["claim_ids"]:
            claim = claims.get(claim_id)
            if claim is None:
                continue
            for source_id in claim["source_ids"]:
                source = sources.get(source_id)
                if source is not None and source["artifact_id"] is not None and artifact_verified.get(source["artifact_id"], False):
                    required_inputs.add(source["artifact_id"])
        for activity in record["execution_activities"]:
            execution_record = execution.get(activity)
            if execution_record is None:
                unbound_activities.append(activity)
                continue
            output_bound = bool(artifact_id_set & set(execution_record["output_artifact_ids"]))
            receipt_bound = bool(set(receipt_ids) & set(execution_record["receipt_ids"]))
            if activity in {"bsc_python_checker", "external_proof_tool", "empirical_test"}:
                linked = output_bound and receipt_bound
            elif activity == "model_reasoning":
                linked = output_bound
            else:
                linked = output_bound or receipt_bound
            if not linked:
                unbound_activities.append(activity)
            if not required_inputs.issubset(execution_record["input_artifact_ids"]):
                input_unbound_activities.append(activity)
        execution_bindings_ok = not unbound_activities
        if unbound_activities:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_EVIDENCE_EXECUTION_BINDING_MISMATCH",
                    f"$.evidence[{evidence_id}].execution_activities",
                    "evidence cannot reuse an unrelated execution; each cited activity must bind this evidence's output or receipt",
                    witness=sorted(unbound_activities),
                )
            )
        execution_inputs_ok = not input_unbound_activities
        if input_unbound_activities:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_EVIDENCE_EXECUTION_INPUT_UNBOUND",
                    f"$.evidence[{evidence_id}].execution_activities",
                    "each cited execution must bind the request and every locally available source for the evidence's claims",
                    witness={"activities": sorted(input_unbound_activities), "required_artifact_ids": sorted(required_inputs)},
                )
            )

        receipt_binding_failures: dict[str, list[str]] = {}
        for receipt_id in receipt_ids:
            receipt = receipts.get(receipt_id)
            if receipt is None:
                continue
            failures: list[str] = []
            if receipt["artifact_id"] not in artifact_id_set:
                failures.append("receipt_artifact_not_bound_to_evidence")
            if not set(record["claim_ids"]).issubset(receipt["claim_ids"]):
                failures.append("claim_binding_missing")
            if not set(record["gate_ids"]).issubset(receipt["gate_ids"]):
                failures.append("gate_binding_missing")
            if not any(
                receipt_id in execution[activity]["receipt_ids"]
                for activity in record["execution_activities"]
                if activity in execution
            ):
                failures.append("execution_binding_missing")
            if not receipt_scope_ok.get(receipt_id, False):
                failures.append("receipt_scope_mismatch")
            if failures:
                receipt_binding_failures[receipt_id] = failures
        receipt_bindings_ok = not receipt_binding_failures
        if receipt_binding_failures:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_EVIDENCE_RECEIPT_BINDING_MISMATCH",
                    f"$.evidence[{evidence_id}].receipt_ids",
                    "a receipt used as evidence must bind its own bytes, the same claims and gates, and a cited execution",
                    witness=receipt_binding_failures,
                )
            )
        has_support_artifact = any(
            identifier in artifacts and artifacts[identifier]["role"] in EVIDENCE_ARTIFACT_ROLES
            for identifier in artifact_ids
        )
        artifact_roles_ok = (
            not invalid_role_artifacts
            and not source_scope_failures
            and not execution_output_failures
            and not verified_evidence_output_failures
        )
        evidence_effective[evidence_id] = (
            record["status"] == "verified"
            and artifacts_ok
            and receipts_ok
            and activities_ok
            and execution_bindings_ok
            and execution_inputs_ok
            and receipt_bindings_ok
            and artifact_roles_ok
            and has_support_artifact
        )
        if record["status"] == "verified" and not artifact_ids:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_VERIFIED_EVIDENCE_UNBOUND",
                    f"$.evidence[{evidence_id}].artifact_ids",
                    "verified evidence requires at least one locally bound artifact",
                )
            )
        receipt_only = bool(artifact_ids) and all(
            identifier in artifacts and artifacts[identifier]["role"] == "receipt" for identifier in artifact_ids
        )
        if record["result"] == "pass" and record["status"] == "verified" and receipt_only:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_RECEIPT_ONLY_PROMOTION",
                    f"$.evidence[{evidence_id}]",
                    "a receipt alone cannot promote a passing evidence record",
                )
            )
        unsupported_activities = [
            activity for activity in record["execution_activities"] if not execution_effective.get(activity, False)
        ]
        if unsupported_activities and (record["result"] == "pass" or record["gate_ids"]):
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_UNSUPPORTED_EXECUTION_EVIDENCE",
                    f"$.evidence[{evidence_id}].execution_activities",
                    "evidence relied on an activity that was not adequately executed and bound",
                    witness=sorted(unsupported_activities),
                )
            )
        if "chatgpt_data_analysis" in record["execution_activities"] and execution.get("chatgpt_data_analysis", {}).get("status") == "file_read_only":
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_FILE_READ_PROMOTION",
                    f"$.evidence[{evidence_id}].execution_activities",
                    "read-only file access cannot support evidence or a fatal gate",
                )
            )
        evidence_path = f"$.evidence[{evidence_id}]"
        if (
            record["status"] == "verified"
            and not evidence_effective[evidence_id]
            and not any(item.severity == Severity.BLOCKED and item.path == evidence_path for item in findings)
        ):
            findings.append(
                _finding(
                    Severity.WARNING,
                    "RETURN_EVIDENCE_UNVERIFIED_LOCALLY",
                    evidence_path,
                    "evidence marked verified is not fully supported by locally hash-matched artifacts and adequate execution records",
                    witness=evidence_id,
                )
            )

    derived_gates: dict[str, str] = {}
    for gate_id, gate in gates.items():
        reverse_ids = {item_id for item_id, item in evidence.items() if gate_id in item["gate_ids"]}
        all_ids = set(gate["evidence_ids"]) | reverse_ids
        records = [evidence[identifier] for identifier in sorted(all_ids) if identifier in evidence]
        derived = _derive_gate_state(records, evidence_effective)
        derived_gates[gate_id] = derived
        if gate["state"] != derived:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_GATE_STATE_MISMATCH",
                    f"$.fatal_gates[{gate_id}].state",
                    "the submitted fatal-gate state disagrees with the state derived from all bound evidence",
                    witness={"submitted": gate["state"], "derived": derived},
                )
            )
        if gate["state"] == "pass" and derived != "pass":
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_UNSUPPORTED_GATE_PASS",
                    f"$.fatal_gates[{gate_id}].state",
                    "a fatal gate cannot pass without complete locally bound verified passing evidence",
                )
            )
        if gate["state"] == "pass" and gate["obligation_ids"]:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_PASSED_GATE_HAS_OPEN_OBLIGATION",
                    f"$.fatal_gates[{gate_id}]",
                    "a passing fatal gate cannot retain an implicitly open obligation",
                )
            )
        if gate["state"] != "pass" and not gate["obligation_ids"]:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_UNRESOLVED_GATE_OBLIGATION_OMITTED",
                    f"$.fatal_gates[{gate_id}].obligation_ids",
                    "a nonpassing fatal gate must preserve at least one open obligation",
                )
            )

    summary = raw["summary_projection"]
    if summary["primary_claim_id"] != primary_id:
        findings.append(
            _finding(
                Severity.BLOCKED,
                "RETURN_SUMMARY_PRIMARY_MISMATCH",
                "$.summary_projection.primary_claim_id",
                "the summary projects a different primary claim",
                witness={"top_level": primary_id, "summary": summary["primary_claim_id"]},
            )
        )
    primary = claims.get(primary_id)
    primary_gate_ids: set[str] = set(primary["fatal_gate_ids"]) if primary is not None else set()
    if primary is not None and summary["research_verdict"] != primary["research_verdict"]:
        findings.append(
            _finding(
                Severity.BLOCKED,
                "RETURN_SUMMARY_VERDICT_MISMATCH",
                "$.summary_projection.research_verdict",
                "the summary research verdict must exactly equal the primary claim verdict",
                witness={"claim": primary["research_verdict"], "summary": summary["research_verdict"]},
            )
        )
    summary_gate_ids = set(gates)
    if set(summary["fatal_gate_ids"]) != summary_gate_ids:
        findings.append(
            _finding(
                Severity.BLOCKED,
                "RETURN_SUMMARY_GATE_OMISSION",
                "$.summary_projection.fatal_gate_ids",
                "the summary must project exactly every declared fatal gate",
                witness={"expected": sorted(summary_gate_ids), "summary": sorted(summary["fatal_gate_ids"])},
            )
        )
    expected_obligations = set(obligations)
    if set(summary["unresolved_obligation_ids"]) != expected_obligations:
        findings.append(
            _finding(
                Severity.BLOCKED,
                "RETURN_SUMMARY_OBLIGATION_OMISSION",
                "$.summary_projection.unresolved_obligation_ids",
                "the summary must project exactly every declared open obligation",
                witness={"expected": sorted(expected_obligations), "summary": sorted(summary["unresolved_obligation_ids"])},
            )
        )
    admission = _derive_admission([derived_gates.get(identifier, "unrun") for identifier in summary_gate_ids])
    if summary["admission"] != admission:
        findings.append(
            _finding(
                Severity.BLOCKED,
                "RETURN_SUMMARY_ADMISSION_MISMATCH",
                "$.summary_projection.admission",
                "the summary admission disagrees with the independently derived fatal-gate product",
                witness={"submitted": summary["admission"], "derived": admission},
            )
        )

    for claim_id, claim in claims.items():
        verdict = claim["research_verdict"]
        claim_gate_ids = set(claim["fatal_gate_ids"])
        direct_evidence = [evidence[identifier] for identifier in claim["evidence_ids"] if identifier in evidence]
        claim_sources = [sources[identifier] for identifier in claim["source_ids"] if identifier in sources]
        sources_complete = bool(claim_sources) and len(claim_sources) == len(claim["source_ids"]) and all(
            source["coverage_state"] == "fully_inspected" for source in claim_sources
        )
        source_bytes_verified = sources_complete and all(
            source["artifact_id"] is not None and artifact_verified.get(source["artifact_id"], False)
            for source in claim_sources
        )
        effective_nonpass = [
            {"id": record["id"], "result": record["result"]}
            for record in direct_evidence
            if record["result"] in {"fail", "inconclusive"} and evidence_effective.get(record["id"], False)
        ]
        if verdict in {"proven", "strongly_supported"} and effective_nonpass:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_HIGH_VERDICT_EVIDENCE_CONFLICT",
                    f"$.claims[{claim_id}].research_verdict",
                    "a high verdict cannot coexist with direct locally effective failing or inconclusive evidence",
                    witness={"claim_id": claim_id, "evidence": effective_nonpass},
                    repair="resolve the contradictory or inconclusive evidence or demote the verdict; do not remove a valid negative result",
                )
            )

        if verdict == "refuted":
            if not sources_complete:
                findings.append(
                    _finding(
                        Severity.BLOCKED,
                        "RETURN_REFUTED_WITH_SOURCE_GAP",
                        f"$.claims[{claim_id}].research_verdict",
                        "refuted requires complete coverage of every source that defines the claim and counterexample scope",
                    )
                )
            if not source_bytes_verified:
                findings.append(
                    _finding(
                        Severity.BLOCKED,
                        "RETURN_REFUTED_SOURCE_BYTES_UNVERIFIED",
                        f"$.claims[{claim_id}].research_verdict",
                        "refuted requires locally hash-matched bytes for every bound source",
                    )
                )
            if not any(
                record["result"] == "fail" and evidence_effective.get(record["id"], False)
                for record in direct_evidence
            ):
                findings.append(
                    _finding(
                        Severity.BLOCKED,
                        "RETURN_REFUTED_WITHOUT_COUNTEREVIDENCE",
                        f"$.claims[{claim_id}].research_verdict",
                        "refuted requires direct locally effective failing evidence; missing material alone is not refutation",
                    )
                )

        if verdict == "strongly_supported":
            if not sources_complete:
                findings.append(
                    _finding(
                        Severity.BLOCKED,
                        "RETURN_STRONGLY_SUPPORTED_WITH_SOURCE_GAP",
                        f"$.claims[{claim_id}].research_verdict",
                        "strongly_supported requires complete coverage of every bound source",
                    )
                )
            if not source_bytes_verified:
                findings.append(
                    _finding(
                        Severity.BLOCKED,
                        "RETURN_STRONGLY_SUPPORTED_SOURCE_BYTES_UNVERIFIED",
                        f"$.claims[{claim_id}].research_verdict",
                        "strongly_supported requires locally hash-matched bytes for every bound source",
                    )
                )
            if not any(
                record["result"] == "pass" and evidence_effective.get(record["id"], False)
                for record in direct_evidence
            ):
                findings.append(
                    _finding(
                        Severity.BLOCKED,
                        "RETURN_STRONGLY_SUPPORTED_WITHOUT_EVIDENCE",
                        f"$.claims[{claim_id}].research_verdict",
                        "strongly_supported requires direct, locally effective passing evidence",
                    )
                )
            if not claim_gate_ids or not all(derived_gates.get(identifier) == "pass" for identifier in claim_gate_ids):
                findings.append(
                    _finding(
                        Severity.BLOCKED,
                        "RETURN_STRONGLY_SUPPORTED_WITH_BLOCKED_GATE",
                        f"$.claims[{claim_id}].research_verdict",
                        "strongly_supported requires every bound fatal gate to derive pass",
                    )
                )
            unsupported_dependencies = [
                dependency
                for dependency in claim["depends_on"]
                if dependency in claims and claims[dependency]["research_verdict"] not in {"proven", "strongly_supported"}
            ]
            if unsupported_dependencies:
                findings.append(
                    _finding(
                        Severity.BLOCKED,
                        "RETURN_STRONGLY_SUPPORTED_DEPENDENCY_UNCLOSED",
                        f"$.claims[{claim_id}].depends_on",
                        "strongly_supported cannot depend on a claim below strongly_supported",
                        witness=unsupported_dependencies,
                    )
                )

        if verdict != "proven":
            continue
        gate_support = bool(claim_gate_ids) and all(derived_gates.get(identifier) == "pass" for identifier in claim_gate_ids)
        if not gate_support:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_PROVEN_WITH_BLOCKED_GATE",
                    f"$.claims[{claim_id}].research_verdict",
                    "a proven verdict requires every declared fatal gate to derive pass",
                )
            )
        if not sources_complete:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_PROVEN_WITH_SOURCE_GAP",
                    f"$.claims[{claim_id}].research_verdict",
                    "a proven verdict cannot coexist with missing, partial, unreadable, or truncated source coverage",
                )
            )
        if not source_bytes_verified:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_PROVEN_SOURCE_BYTES_UNVERIFIED",
                    f"$.claims[{claim_id}].research_verdict",
                    "a proven verdict requires locally hash-matched bytes for every bound source",
                )
            )
        proof_bound = any(
            record["result"] == "pass"
            and evidence_effective.get(record["id"], False)
            and any(
                identifier in artifacts and artifacts[identifier]["role"] == "evidence" and artifact_verified.get(identifier, False)
                for identifier in record["artifact_ids"]
            )
            for record in direct_evidence
        )
        if not proof_bound:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_PROVEN_EVIDENCE_UNBOUND",
                    f"$.claims[{claim_id}].research_verdict",
                    "a proven verdict requires a locally hash-bound role=evidence artifact; a receipt alone is insufficient",
                )
            )
        open_for_claim = [
            identifier
            for identifier, obligation in obligations.items()
            if claim_id in obligation["claim_ids"] or bool(claim_gate_ids & set(obligation["gate_ids"]))
        ]
        if open_for_claim:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_PROVEN_WITH_OPEN_OBLIGATION",
                    f"$.claims[{claim_id}].research_verdict",
                    "a proven verdict cannot retain an unresolved obligation",
                    witness=sorted(open_for_claim),
                )
            )
        unsupported_dependencies = [
            dependency for dependency in claim["depends_on"] if dependency in claims and claims[dependency]["research_verdict"] != "proven"
        ]
        if unsupported_dependencies:
            findings.append(
                _finding(
                    Severity.BLOCKED,
                    "RETURN_PROVEN_DEPENDENCY_UNCLOSED",
                    f"$.claims[{claim_id}].depends_on",
                    "a proven verdict cannot depend on a claim that is not itself recorded as proven",
                    witness=unsupported_dependencies,
                )
            )

    if summary["deployment_status"] == "admitted":
        findings.append(
            _finding(
                Severity.BLOCKED,
                "RETURN_DEPLOYMENT_AUTHORITY_MISSING",
                "$.summary_projection.deployment_status",
                "this non-admissive return inspection cannot grant or certify deployment admission",
                repair="record deployment authority only in an accountable external approval system",
            )
        )

    findings.append(
        _finding(
            Severity.INFO,
            "RETURN_DESK_NON_ADMISSIVE",
            "$.authority",
            "the Return Desk checks envelope consistency and local byte bindings only; it does not establish truth, proof, execution beyond the bound records, or deployment permission",
        )
    )
    if not any(finding.severity in BLOCKING for finding in findings):
        findings.append(
            _finding(
                Severity.INFO,
                "RETURN_INTERNALLY_CONSISTENT",
                "$",
                "the submitted projections, ledgers, references, and inspected local byte bindings are internally consistent within the implemented checks",
            )
        )
    return findings
