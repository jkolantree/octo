from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Callable

from . import __version__
from .adapters import audit_adapter_receipt
from .atomic import audit_atomic_modulus
from .bicomplex import audit_complex_document
from .defect import audit_defect_composition
from .findings import Finding, Severity, decision, exit_code
from .gates import audit_gate_product
from .holonomy import audit_holonomy_document
from .manifest import ManifestAuditCache, lint_manifest
from .observation import audit_observation_document
from .plugins import arithmetic_trace_findings, recovery_findings
from .provenance import sha256_bytes, sha256_json
from .return_desk import audit_return_document
from .schema_validation import ROUTE_SCHEMAS, validate_route_schema
from .theorem import audit_theorem_certificate


MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_JSON_DEPTH = 64
MAX_CONTAINER_ITEMS = 100_000
MAX_STRING_CHARS = 1_000_000
MAX_INTEGER_DIGITS = 256
DOMAIN_CHECKS = {"arithmetic_trace", "global_recovery"}


@dataclass(frozen=True)
class AuditResult:
    findings: list[Finding]
    checks_run: list[str]
    checks_not_run: list[str]


Auditor = Callable[[dict[str, Any], Path | None], list[Finding] | AuditResult]


class InputError(ValueError):
    pass


@dataclass(frozen=True)
class LoadedDocument:
    value: dict[str, Any]
    raw_hash: str
    semantic_hash: str
    artifact_root: Path


def _safe_label(path: str) -> str:
    return path.replace("\\", "/").rsplit("/", 1)[-1] or "input.json"


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise InputError(f"non-finite JSON number is forbidden: {value}")


def _enforce_resource_limits(value: Any) -> None:
    item_count = 0

    def enforce_unicode_scalars(text: str) -> None:
        if any(0xD800 <= ord(character) <= 0xDFFF for character in text):
            raise InputError("JSON text contains an unpaired UTF-16 surrogate")

    def visit(item: Any, depth: int) -> None:
        nonlocal item_count
        if depth > MAX_JSON_DEPTH:
            raise InputError(f"JSON nesting exceeds {MAX_JSON_DEPTH}")
        if isinstance(item, dict):
            item_count += len(item)
            if item_count > MAX_CONTAINER_ITEMS:
                raise InputError(f"JSON container entries exceed {MAX_CONTAINER_ITEMS}")
            for key, nested in item.items():
                enforce_unicode_scalars(key)
                if len(key) > MAX_STRING_CHARS:
                    raise InputError("JSON object key is too long")
                visit(nested, depth + 1)
        elif isinstance(item, list):
            item_count += len(item)
            if item_count > MAX_CONTAINER_ITEMS:
                raise InputError(f"JSON container entries exceed {MAX_CONTAINER_ITEMS}")
            for nested in item:
                visit(nested, depth + 1)
        elif isinstance(item, str):
            enforce_unicode_scalars(item)
            if len(item) > MAX_STRING_CHARS:
                raise InputError(f"JSON string exceeds {MAX_STRING_CHARS} characters")
        elif isinstance(item, bool) or item is None:
            return
        elif isinstance(item, int):
            if len(str(abs(item))) > MAX_INTEGER_DIGITS:
                raise InputError(f"JSON integer exceeds {MAX_INTEGER_DIGITS} digits")
        elif isinstance(item, float):
            if not math.isfinite(item):
                raise InputError("non-finite JSON numbers are forbidden")
        else:
            raise InputError(f"unsupported decoded JSON type: {type(item).__name__}")

    visit(value, 0)


def _read_stream_bounded(stream: BinaryIO, max_bytes: int) -> bytes:
    payload = bytearray()
    while True:
        remaining = max_bytes - len(payload)
        chunk = stream.read(min(1024 * 1024, remaining + 1))
        if not chunk:
            return bytes(payload)
        payload.extend(chunk)
        if len(payload) > max_bytes:
            raise InputError(f"input exceeds the {max_bytes}-byte limit")


def load_document(path: str) -> LoadedDocument:
    source = Path(path)
    try:
        size = source.stat().st_size
    except OSError as exc:
        raise InputError("input file is unavailable") from exc
    if not source.is_file():
        raise InputError("input path must identify a regular file")
    if size > MAX_INPUT_BYTES:
        raise InputError(f"input exceeds the {MAX_INPUT_BYTES}-byte limit")
    try:
        with source.open("rb") as stream:
            raw_bytes = _read_stream_bounded(stream, MAX_INPUT_BYTES)
    except OSError as exc:
        raise InputError("input file could not be read") from exc
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InputError("input must be UTF-8 JSON") from exc
    try:
        value = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except InputError:
        raise
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise InputError("input is not valid strict JSON") from exc
    if not isinstance(value, dict):
        raise InputError("top-level JSON value must be an object")
    _enforce_resource_limits(value)
    return LoadedDocument(value, sha256_bytes(raw_bytes), sha256_json(value), source.resolve().parent)


def load_json(path: str) -> dict[str, Any]:
    """Compatibility helper returning only the decoded strict JSON object."""

    return load_document(path).value


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False))


def _manifest_check_order(command_name: str) -> list[str]:
    checks = [
        f"schema_validation:{command_name}",
        "claim_manifest_lint",
        "local_artifact_hashes",
        "semantic_theorem_replay",
    ]
    if command_name == "audit":
        checks.extend(["gate_product", "dependency_graph"])
        checks.extend(f"domain_plugin:{name}" for name in sorted(DOMAIN_CHECKS))
    return checks


def _semantic_check_name(command_name: str) -> str:
    return {
        "complex": "exact_certificate_complex",
        "observe": "finite_observation_descent",
        "atomic": "finite_atomic_modulus_record",
        "defect": "affine_upper_bound_propagation",
        "adapter": "proof_carrying_adapter_receipt",
        "holonomy": "exact_derived_holonomy",
        "theorem": "exact_q_polynomial_identity",
        "return-desk": "non_admissive_audit_return_inspection",
    }.get(command_name, "custom_auditor")


def _lint_stages(raw: dict[str, Any], artifact_root: Path | None) -> AuditResult:
    executed: list[str] = []
    audit_cache = ManifestAuditCache()
    findings = lint_manifest(
        raw,
        artifact_root,
        checks_run=executed,
        audit_cache=audit_cache,
    )
    order = _manifest_check_order("lint")
    return AuditResult(findings, executed, [name for name in order if name not in executed])


def _audit_stages(raw: dict[str, Any], artifact_root: Path | None) -> AuditResult:
    executed: list[str] = []
    audit_cache = ManifestAuditCache()
    findings = lint_manifest(
        raw,
        artifact_root,
        checks_run=executed,
        audit_cache=audit_cache,
    )
    order = _manifest_check_order("audit")
    if any(finding.severity == Severity.ERROR for finding in findings):
        return AuditResult(findings, executed, [name for name in order if name not in executed])

    executed.append("gate_product")
    findings.extend(audit_gate_product(raw, artifact_root, audit_cache))
    if raw.get("dependency_graph"):
        executed.append("dependency_graph")

    claim = raw.get("claim", {})
    domain = raw.get("domain_checks", {})
    if isinstance(claim, dict) and claim.get("family") == "arithmetic_trace":
        executed.append("domain_plugin:arithmetic_trace")
        findings.extend(
            arithmetic_trace_findings(
                raw,
                audit_cache.registered_replay_results,
            )
        )
    if isinstance(domain, dict) and "global_recovery" in domain:
        executed.append("domain_plugin:global_recovery")
        findings.extend(recovery_findings(raw))
    return AuditResult(findings, executed, [name for name in order if name not in executed])


def render(path: str, result: AuditResult, document: LoadedDocument) -> int:
    payload = {
        "engine_version": __version__,
        "output_version": "0.3.0",
        "input": _safe_label(path),
        "input_hashes": {"raw": document.raw_hash, "semantic": document.semantic_hash},
        "checks": {"run": ["strict_json_parse"] + result.checks_run, "not_run": result.checks_not_run},
        "decision": decision(result.findings),
        "findings": [finding.to_dict() for finding in result.findings],
    }
    _emit(payload)
    return exit_code(result.findings)


def _render_error(path: str, message: str, *, internal: bool = False) -> int:
    _emit(
        {
            "engine_version": __version__,
            "output_version": "0.3.0",
            "input": _safe_label(path),
            "checks": {
                "run": ["strict_json_parse"] if not internal else ["strict_json_parse", "semantic_audit"],
                "not_run": ["semantic_audit"] if not internal else [],
            },
            "decision": "internal_error" if internal else "prohibited",
            "findings": [
                {
                    "severity": "ERROR",
                    "code": "INTERNAL_ERROR" if internal else "INPUT_MALFORMED",
                    "path": "$",
                    "message": message,
                }
            ],
        }
    )
    return 70 if internal else 2


def command(path: str, auditor: Auditor, command_name: str = "custom") -> int:
    try:
        document = load_document(path)
    except InputError as exc:
        return _render_error(path, str(exc))
    except Exception as exc:  # pragma: no cover - last-resort input-boundary guard
        return _render_error(path, f"input loader failed unexpectedly ({type(exc).__name__})", internal=True)
    try:
        schema_check = f"schema_validation:{command_name}"
        schema_findings = validate_route_schema(command_name, document.value)
        if schema_findings:
            remaining = _manifest_check_order(command_name) if command_name in {"lint", "audit"} else [schema_check, _semantic_check_name(command_name)]
            result = AuditResult(schema_findings, [schema_check], [name for name in remaining if name != schema_check])
        else:
            outcome = auditor(document.value, document.artifact_root)
            if isinstance(outcome, AuditResult):
                result = AuditResult(
                    outcome.findings,
                    [schema_check] + outcome.checks_run,
                    [name for name in outcome.checks_not_run if name != schema_check],
                )
            else:
                result = AuditResult(outcome, ([schema_check] if command_name in ROUTE_SCHEMAS else []) + [_semantic_check_name(command_name)], ["claim_manifest_lint", "gate_product", "domain_plugins"])
        return render(path, result, document)
    except Exception as exc:  # pragma: no cover - last-resort trust-boundary guard
        return _render_error(path, f"checker failed unexpectedly ({type(exc).__name__})", internal=True)


def audit_claim(raw: dict[str, Any], artifact_root: Path | None = None) -> list[Finding]:
    schema = validate_route_schema("audit", raw)
    if schema:
        return schema
    return _audit_stages(raw, artifact_root).findings


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        _emit(
            {
                "engine_version": __version__,
                "output_version": "0.3.0",
                "checks": {"run": [], "not_run": ["input_parse", "semantic_audit"]},
                "decision": "prohibited",
                "findings": [{"severity": "ERROR", "code": "CLI_USAGE", "path": "$", "message": message}],
            }
        )
        raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    parser = JsonArgumentParser(prog="bsc-audit", description="Certificate-producing BSC claim auditor")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("lint", "validate a claim manifest"),
        ("audit", "validate a manifest and run domain kill gates"),
        ("complex", "audit exact certificate complexes and transports"),
        ("observe", "audit finite observation/query descent"),
        ("atomic", "audit an off-origin concentration-modulus certificate"),
        ("defect", "audit compositional transport-defect bounds"),
        ("adapter", "audit a non-admissive proof-carrying adapter receipt"),
        ("holonomy", "audit strict, derived, observed-derived, and exact-kernel path holonomy"),
        ("theorem", "replay a closed exact-Q polynomial identity certificate"),
        ("return-desk", "inspect a non-admissive audit-return envelope and its local byte bindings"),
    ):
        child = subparsers.add_parser(name, help=help_text)
        child.add_argument("path")
    args = parser.parse_args(argv)
    auditors: dict[str, Auditor] = {
        "lint": _lint_stages,
        "audit": _audit_stages,
        "complex": lambda raw, _root: audit_complex_document(raw),
        "observe": lambda raw, _root: audit_observation_document(raw),
        "atomic": lambda raw, _root: audit_atomic_modulus(raw),
        "defect": lambda raw, _root: audit_defect_composition(raw),
        "adapter": audit_adapter_receipt,
        "holonomy": lambda raw, _root: audit_holonomy_document(raw),
        "theorem": audit_theorem_certificate,
        "return-desk": audit_return_document,
    }
    return command(args.path, auditors[args.command], args.command)


if __name__ == "__main__":
    raise SystemExit(main())
