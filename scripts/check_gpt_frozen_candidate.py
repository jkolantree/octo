#!/usr/bin/env python3
"""Write or verify a deterministic, closed Custom GPT candidate manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCHEMA = "bsc-gpt-frozen-candidate-manifest/v1"
REGISTRY_VERSION = "bsc-gpt-frozen-candidate-registry/v3"
OUTPUT_VERSION = "1.0"
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_REGISTRY_FILE_BYTES = 64 * 1024 * 1024
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
CATEGORY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
WINDOWS_RESERVED_BASENAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
ENTRY_KEYS = {"category", "path", "bytes", "sha256"}
MANIFEST_KEYS = {
    "manifest_schema",
    "registry_version",
    "file_count",
    "excluded_paths",
    "files",
}
EXCLUDED_CYCLE_PATHS = (
    "gpt/GPT_RELEASE_MANIFEST.json",
    "gpt/SHA256SUMS",
)

EVAL_FIXTURE_FILENAMES = (
    "assumption_present.txt",
    "assumption_removed.txt",
    "bsc_self_audit.txt",
    "claim_valid.json",
    "complex_valid_transport.json",
    "conventional_counterexample.txt",
    "decisive_calculation_not_executed.txt",
    "deployment_overreach.txt",
    "equation_sign_baseline.txt",
    "equation_sign_mutant.txt",
    "exact_quotient_missing_test.txt",
    "formal_looking_not_proof.txt",
    "ja_contradictory_verified_evidence.txt",
    "ja_decisive_calculation_not_executed.txt",
    "ja_known_false_continuity.txt",
    "ja_known_true_induction.txt",
    "ja_poisoned_all_tests_passed.txt",
    "ja_poisoned_prompt_injection.txt",
    "ja_return_envelope_impossible_binding.txt",
    "ja_truncated_proof.txt",
    "known_false_continuity.txt",
    "known_true_induction.txt",
    "missing_companion_report.txt",
    "nonadmissive_adapter_receipt.txt",
    "null_conflicting_referenced.json",
    "null_failed_proof.json",
    "null_missing_arithmetic_config.json",
    "null_omitted_bound_failure.json",
    "observation_failure.json",
    "official_first_reproduction.txt",
    "official_service_status.txt",
    "outside_checker_domain.txt",
    "poisoned_all_tests_passed.txt",
    "poisoned_prompt_injection.txt",
    "return_envelope_impossible_binding.txt",
    "return_envelope_positive_control.txt",
    "truncated_proof.txt",
    "unconventional_hypothesis.txt",
    "unverifiable_citation.txt",
)

KNOWLEDGE_FILENAMES = (
    "BSC_JAPANESE_INTERFACE.md",
    "BSC_PROTOCOL.md",
    "BSC_STATUS_AND_EVIDENCE_MODEL.md",
    "BSC_SUPPORTED_CHECKS.md",
    "BSC_WORKED_EXAMPLES.md",
)

SOURCE_CONTROL_FILENAMES = (
    "GPT_EVAL_PROVENANCE.md",
    "GPT_EVAL_SPEC.json",
    "GPT_FROZEN_EVALUATION_PROTOCOL.json",
    "GPT_INVARIANT_ENFORCEMENT_MATRIX.md",
    "GPT_PROFILE.json",
)

BSC_MODULE_FILENAMES = (
    "__init__.py",
    "adapters.py",
    "atomic.py",
    "bicomplex.py",
    "cli.py",
    "defect.py",
    "exact.py",
    "exact_linear.py",
    "findings.py",
    "gates.py",
    "holonomy.py",
    "manifest.py",
    "observation.py",
    "plugins.py",
    "provenance.py",
    "return_desk.py",
    "schema_validation.py",
    "theorem.py",
)

SCHEMA_FILENAMES = (
    "adapter-receipt-v0.1.schema.json",
    "atomic-modulus-v0.3.schema.json",
    "audit-return-v0.1.schema.json",
    "claim-manifest-v0.3.schema.json",
    "claim-manifest-v0.4.schema.json",
    "complex-v0.3.schema.json",
    "defect-v0.3.schema.json",
    "derived-holonomy-v0.1.schema.json",
    "derived-holonomy-v0.2.schema.json",
    "observation-v0.3.schema.json",
    "output-0.3.0.schema.json",
    "theorem-certificate-v0.1.schema.json",
)

TEST_FILENAMES = (
    "return_desk_runtime.test.cjs",
    "test_adapters.py",
    "test_atomic.py",
    "test_bicomplex.py",
    "test_cli.py",
    "test_compact_preview_response.py",
    "test_defect.py",
    "test_exact.py",
    "test_gpt_artifact_compiler.py",
    "test_gpt_eval_bundle.py",
    "test_gpt_eval_controller.py",
    "test_gpt_eval_suite.py",
    "test_gpt_frozen_candidate.py",
    "test_gpt_package.py",
    "test_holonomy.py",
    "test_localization.py",
    "test_manifest.py",
    "test_null_discrimination.py",
    "test_observation.py",
    "test_pages.py",
    "test_pages_checker_hardening.py",
    "test_privacy.py",
    "test_provenance.py",
    "test_publication_status.py",
    "test_release_directory.py",
    "test_research_packet.py",
    "test_return_desk.py",
    "test_run_tests.py",
    "test_theorem.py",
)

REGISTRY: dict[str, tuple[str, ...]] = {
    "browser_return_desk": (
        "pages/app.js",
        "pages/index.html",
        "pages/ja.html",
        "pages/locale-en.js",
        "pages/locale-ja.js",
        "pages/profile.js",
        "pages/protocol/BSC_AUDIT_LLM_PACKET.md",
        "pages/protocol/meta.js",
        "pages/return-desk-core.js",
        "scripts/build_publication_assets.py",
        "scripts/check_pages.py",
    ),
    "candidate": (
        "gpt/GPT_INSTRUCTIONS.md",
        "gpt/_source/GPT_PROFILE.json",
        "gpt/knowledge/BSC_JAPANESE_INTERFACE.md",
        "gpt/knowledge/BSC_PROTOCOL.md",
        "gpt/knowledge/BSC_STATUS_AND_EVIDENCE_MODEL.md",
        "gpt/knowledge/BSC_SUPPORTED_CHECKS.md",
        "gpt/knowledge/BSC_WORKED_EXAMPLES.md",
    ),
    "evaluation": (
        "gpt/_source/GPT_EVAL_SPEC.json",
        "gpt/evals/GPT_EVAL_CASES.jsonl",
        "gpt/evals/GPT_EVAL_EXPECTATIONS.md",
        "gpt/evals/GPT_EVAL_PROVENANCE.md",
        "gpt/evals/GPT_FROZEN_EVALUATION_PROTOCOL.json",
        "gpt/evals/GPT_INVARIANT_ENFORCEMENT_MATRIX.md",
        "gpt/evals/GPT_MANUAL_SCORECARD.md",
        "gpt/evals/README.md",
    ),
    "evaluation_fixtures": tuple(
        f"gpt/evals/fixtures/{filename}" for filename in EVAL_FIXTURE_FILENAMES
    ),
    "protocol_and_provenance": (
        "BSC_AUDIT_LLM_PACKET.md",
        "docs/ALPHA8_PREFLIGHT_REPAIR_ADDENDUM.md",
        "docs/R01_FORENSIC_ADDENDUM.md",
        "docs/standalone/BSC_EXECUTION_AND_RECEIPTS.md",
        "gpt/_source/GPT_EVAL_PROVENANCE.md",
        "gpt/_source/GPT_FROZEN_EVALUATION_PROTOCOL.json",
        "gpt/_source/GPT_INVARIANT_ENFORCEMENT_MATRIX.md",
    ),
    "python_return_desk": tuple(
        sorted(
            [f"schemas/{filename}" for filename in SCHEMA_FILENAMES]
            + [
                f"src/bsc_audit/{filename}"
                for filename in BSC_MODULE_FILENAMES
            ]
            + [
                f"src/bsc_audit/schema_data/{filename}"
                for filename in SCHEMA_FILENAMES
            ]
        )
    ),
    "tests": tuple(f"tests/{filename}" for filename in TEST_FILENAMES),
    "tooling": (
        ".github/workflows/release.yml",
        "scripts/build_gpt_package.py",
        "scripts/check_compact_preview_response.py",
        "scripts/check_gpt_eval_bundle.py",
        "scripts/check_gpt_eval_suite.py",
        "scripts/check_gpt_frozen_candidate.py",
        "scripts/check_gpt_package.py",
        "scripts/check_release_directory.py",
        "scripts/gpt_artifact_compiler.py",
        "scripts/gpt_eval_controller.py",
        "scripts/run_null_discrimination.py",
        "scripts/run_tests.py",
        "toolchain.lock.json",
    ),
}

CLOSED_DIRECTORIES: dict[str, tuple[str, ...]] = {
    "gpt/_source": SOURCE_CONTROL_FILENAMES,
    "gpt/evals": (
        "GPT_EVAL_CASES.jsonl",
        "GPT_EVAL_EXPECTATIONS.md",
        "GPT_EVAL_PROVENANCE.md",
        "GPT_FROZEN_EVALUATION_PROTOCOL.json",
        "GPT_INVARIANT_ENFORCEMENT_MATRIX.md",
        "GPT_MANUAL_SCORECARD.md",
        "README.md",
    ),
    "gpt/evals/fixtures": EVAL_FIXTURE_FILENAMES,
    "gpt/knowledge": KNOWLEDGE_FILENAMES,
    "schemas": SCHEMA_FILENAMES,
    "src/bsc_audit": BSC_MODULE_FILENAMES,
    "src/bsc_audit/schema_data": SCHEMA_FILENAMES,
    "tests": TEST_FILENAMES,
}

CLOSED_DIRECTORY_SUFFIXES: dict[str, tuple[str, ...]] = {
    "schemas": (".json",),
    "src/bsc_audit": (".py",),
    "src/bsc_audit/schema_data": (".json",),
    "tests": (".cjs", ".py"),
}


class StrictJsonError(ValueError):
    """Raised when a manifest is not strict JSON."""


class CliUsageError(ValueError):
    """Raised when command-line arguments are invalid."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CliUsageError(message)


def registry_entries() -> tuple[tuple[str, str], ...]:
    return tuple(
        (category, path)
        for category in sorted(REGISTRY)
        for path in REGISTRY[category]
    )


def _finding(
    code: str,
    path: str,
    message: str,
    *,
    detail: Any | None = None,
) -> dict[str, Any]:
    finding: dict[str, Any] = {
        "severity": "ERROR",
        "code": code,
        "path": path,
        "message": message,
    }
    if detail is not None:
        finding["detail"] = detail
    return finding


def _sort_findings(findings: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        findings,
        key=lambda item: (
            str(item.get("code", "")),
            str(item.get("path", "")),
            str(item.get("message", "")),
            json.dumps(item.get("detail"), sort_keys=True, ensure_ascii=False),
        ),
    )


def _safe_relative_path(value: object) -> bool:
    if (
        not isinstance(value, str)
        or not value
        or not value.isascii()
        or "\\" in value
    ):
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and value == path.as_posix()
        and all(
            part not in {"", ".", ".."}
            and not part.endswith((" ", "."))
            and not any(character in '<>:"|?*' for character in part)
            and not any(
                ord(character) < 32 or ord(character) == 127
                for character in part
            )
            and part.split(".", 1)[0].rstrip(" .").upper()
            not in WINDOWS_RESERVED_BASENAMES
            for part in path.parts
        )
    )


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise StrictJsonError(f"non-finite JSON number is prohibited: {value}")


def _strict_json(data: bytes) -> Any:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise StrictJsonError("manifest is not strict UTF-8") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise StrictJsonError("manifest is not valid strict JSON") from exc


def _manifest_bytes(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            document,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _relative_to_root(root: Path, path: Path) -> str | None:
    try:
        return path.resolve(strict=False).relative_to(root.resolve()).as_posix()
    except (OSError, RuntimeError, ValueError):
        return None


def _validate_registry_definition() -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if tuple(REGISTRY) != tuple(sorted(REGISTRY)):
        findings.append(
            _finding(
                "REGISTRY_ORDER_INVALID",
                "$.registry",
                "registry categories must be declared in deterministic sorted order",
            )
        )

    pairs = registry_entries()
    paths = [path for _, path in pairs]
    if len(paths) != len(set(paths)) or len(paths) != len({path.casefold() for path in paths}):
        findings.append(
            _finding(
                "REGISTRY_DUPLICATE_PATH",
                "$.registry",
                "registry paths must be globally unique, including portable case folding",
            )
        )
    for category, category_paths in REGISTRY.items():
        if CATEGORY_RE.fullmatch(category) is None:
            findings.append(
                _finding(
                    "REGISTRY_CATEGORY_INVALID",
                    f"$.registry.{category}",
                    "registry category is not a canonical lowercase token",
                )
            )
        if category_paths != tuple(sorted(category_paths)):
            findings.append(
                _finding(
                    "REGISTRY_ORDER_INVALID",
                    f"$.registry.{category}",
                    "registry paths must be declared in deterministic sorted order",
                )
            )
        for path in category_paths:
            if not _safe_relative_path(path):
                findings.append(
                    _finding(
                        "REGISTRY_PATH_UNSAFE",
                        f"$.registry.{category}",
                        "registry contains an unsafe relative path",
                        detail=path,
                    )
                )

    for relative_directory, expected_names in CLOSED_DIRECTORIES.items():
        if not _safe_relative_path(relative_directory):
            findings.append(
                _finding(
                    "REGISTRY_CLOSED_DIRECTORY_INVALID",
                    "$.closed_directories",
                    "closed registry directory path is unsafe",
                    detail=relative_directory,
                )
            )
            continue
        if (
            expected_names != tuple(sorted(expected_names))
            or len(expected_names) != len(set(expected_names))
            or len(expected_names)
            != len({name.casefold() for name in expected_names})
        ):
            findings.append(
                _finding(
                    "REGISTRY_CLOSED_DIRECTORY_INVALID",
                    relative_directory,
                    "closed registry member names must be sorted and portable-unique",
                )
            )
        expected_paths = {
            f"{relative_directory}/{name}" for name in expected_names
        }
        registered_paths = {
            path
            for path in paths
            if PurePosixPath(path).parent.as_posix() == relative_directory
        }
        if (
            any(
                not _safe_relative_path(name)
                or len(PurePosixPath(name).parts) != 1
                for name in expected_names
            )
            or expected_paths != registered_paths
        ):
            findings.append(
                _finding(
                    "REGISTRY_CLOSED_DIRECTORY_INVALID",
                    relative_directory,
                    "closed directory membership must exactly match the explicit registry",
                    detail={
                        "missing": sorted(registered_paths - expected_paths),
                        "unexpected": sorted(expected_paths - registered_paths),
                    },
                )
            )

    if not set(CLOSED_DIRECTORY_SUFFIXES) <= set(CLOSED_DIRECTORIES):
        findings.append(
            _finding(
                "REGISTRY_CLOSED_DIRECTORY_INVALID",
                "$.closed_directory_suffixes",
                "closed-directory suffix rules must target declared closed directories",
            )
        )
    for relative_directory, suffixes in CLOSED_DIRECTORY_SUFFIXES.items():
        expected_names = CLOSED_DIRECTORIES.get(relative_directory, ())
        if (
            suffixes != tuple(sorted(suffixes))
            or not suffixes
            or any(not suffix.startswith(".") for suffix in suffixes)
            or any(not name.endswith(suffixes) for name in expected_names)
        ):
            findings.append(
                _finding(
                    "REGISTRY_CLOSED_DIRECTORY_INVALID",
                    relative_directory,
                    "closed-directory suffix rules must be sorted and cover every expected member",
                )
            )

    excluded = set(EXCLUDED_CYCLE_PATHS)
    included_excluded = sorted(excluded & set(paths))
    if included_excluded:
        findings.append(
            _finding(
                "REGISTRY_CYCLE_PATH_INCLUDED",
                "$.registry",
                "cyclic release manifest or checksum files must not be frozen",
                detail=included_excluded,
            )
        )

    fixture_paths = REGISTRY.get("evaluation_fixtures", ())
    expected_fixture_paths = tuple(
        f"gpt/evals/fixtures/{filename}" for filename in EVAL_FIXTURE_FILENAMES
    )
    if len(EVAL_FIXTURE_FILENAMES) != 39 or fixture_paths != expected_fixture_paths:
        findings.append(
            _finding(
                "REGISTRY_EVAL_FIXTURE_SET_INVALID",
                "$.registry.evaluation_fixtures",
                "the explicit generated evaluation fixture registry must contain exactly the canonical 39 files",
            )
        )

    required_paths = {
        "gpt/GPT_INSTRUCTIONS.md",
        "gpt/_source/GPT_PROFILE.json",
        "scripts/build_gpt_package.py",
        "scripts/check_compact_preview_response.py",
        "scripts/check_gpt_frozen_candidate.py",
        "scripts/gpt_artifact_compiler.py",
        "tests/test_compact_preview_response.py",
        "tests/test_gpt_artifact_compiler.py",
        "tests/test_gpt_frozen_candidate.py",
        "src/bsc_audit/return_desk.py",
        "pages/return-desk-core.js",
        "schemas/audit-return-v0.1.schema.json",
        "gpt/_source/GPT_EVAL_SPEC.json",
        "gpt/evals/GPT_MANUAL_SCORECARD.md",
        "gpt/evals/GPT_EVAL_EXPECTATIONS.md",
        "gpt/_source/GPT_EVAL_PROVENANCE.md",
        "gpt/_source/GPT_INVARIANT_ENFORCEMENT_MATRIX.md",
        "gpt/_source/GPT_FROZEN_EVALUATION_PROTOCOL.json",
        "BSC_AUDIT_LLM_PACKET.md",
    }
    missing_required = sorted(required_paths - set(paths))
    if missing_required:
        findings.append(
            _finding(
                "REGISTRY_REQUIRED_PATH_MISSING",
                "$.registry",
                "the frozen registry omits one or more mandatory candidate controls",
                detail=missing_required,
            )
        )
    return findings


def _has_symlink_component(root: Path, relative_path: str) -> bool:
    cursor = root
    for part in PurePosixPath(relative_path).parts:
        cursor = cursor / part
        try:
            if cursor.is_symlink():
                return True
        except OSError:
            return True
    return False


def _hash_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        while True:
            remaining = MAX_REGISTRY_FILE_BYTES - count
            chunk = stream.read(min(1024 * 1024, remaining + 1))
            if not chunk:
                break
            count += len(chunk)
            if count > MAX_REGISTRY_FILE_BYTES:
                raise ValueError("registry file exceeds byte limit")
            digest.update(chunk)
    return count, digest.hexdigest()


def _read_manifest_bounded(path: Path) -> bytes:
    data = bytearray()
    with path.open("rb") as stream:
        while True:
            remaining = MAX_MANIFEST_BYTES - len(data)
            chunk = stream.read(min(1024 * 1024, remaining + 1))
            if not chunk:
                return bytes(data)
            data.extend(chunk)
            if len(data) > MAX_MANIFEST_BYTES:
                raise ValueError("manifest exceeds byte limit")


def _inspect_registry(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    findings = _validate_registry_definition()
    records: list[dict[str, Any]] = []
    try:
        resolved_root = root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        findings.append(
            _finding(
                "REGISTRY_ROOT_INVALID",
                "$.root",
                "repository root could not be resolved",
                detail=str(exc),
            )
        )
        return records, findings
    if not resolved_root.is_dir():
        findings.append(
            _finding(
                "REGISTRY_ROOT_INVALID",
                "$.root",
                "repository root is not a directory",
            )
        )
        return records, findings

    for relative_directory, expected_names in CLOSED_DIRECTORIES.items():
        directory = resolved_root.joinpath(*PurePosixPath(relative_directory).parts)
        suffixes = CLOSED_DIRECTORY_SUFFIXES.get(relative_directory)
        try:
            actual_names = sorted(
                child.name
                for child in directory.iterdir()
                if child.is_file() or child.is_symlink()
                if suffixes is None or child.name.endswith(suffixes)
            )
        except OSError as exc:
            findings.append(
                _finding(
                    "REGISTRY_DIRECTORY_UNREADABLE",
                    relative_directory,
                    "a closed registry directory could not be read",
                    detail=str(exc),
                )
            )
            continue
        if actual_names != list(expected_names):
            findings.append(
                _finding(
                    "REGISTRY_DIRECTORY_MEMBERSHIP_MISMATCH",
                    relative_directory,
                    "a closed registry directory differs from its explicit file membership",
                    detail={
                        "missing": sorted(set(expected_names) - set(actual_names)),
                        "unexpected": sorted(set(actual_names) - set(expected_names)),
                    },
                )
            )

    for category, relative_path in registry_entries():
        if not _safe_relative_path(relative_path):
            continue
        candidate = resolved_root.joinpath(*PurePosixPath(relative_path).parts)
        try:
            resolved_candidate = candidate.resolve(strict=False)
            if not resolved_candidate.is_relative_to(resolved_root):
                raise ValueError("path escapes repository root")
        except (OSError, RuntimeError, ValueError) as exc:
            findings.append(
                _finding(
                    "REGISTRY_PATH_UNSAFE",
                    relative_path,
                    "registry path does not remain below the repository root",
                    detail=str(exc),
                )
            )
            continue
        if _has_symlink_component(resolved_root, relative_path):
            findings.append(
                _finding(
                    "REGISTRY_FILE_SYMLINK",
                    relative_path,
                    "registry files and their in-repository path components must not be symbolic links",
                )
            )
            continue
        try:
            if not candidate.is_file():
                findings.append(
                    _finding(
                        "REGISTRY_FILE_MISSING",
                        relative_path,
                        "required registry file is missing or is not a regular file",
                    )
                )
                continue
            byte_count, digest = _hash_file(candidate)
        except ValueError:
            findings.append(
                _finding(
                    "REGISTRY_FILE_TOO_LARGE",
                    relative_path,
                    "registry file exceeds the per-file inspection limit",
                    detail={"max_bytes": MAX_REGISTRY_FILE_BYTES},
                )
            )
            continue
        except OSError as exc:
            findings.append(
                _finding(
                    "REGISTRY_FILE_UNREADABLE",
                    relative_path,
                    "required registry file could not be read",
                    detail=str(exc),
                )
            )
            continue
        records.append(
            {
                "category": category,
                "path": relative_path,
                "bytes": byte_count,
                "sha256": digest,
            }
        )
    return records, findings


def build_manifest(root: Path = ROOT) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    records, findings = _inspect_registry(root)
    document = {
        "manifest_schema": MANIFEST_SCHEMA,
        "registry_version": REGISTRY_VERSION,
        "file_count": len(registry_entries()),
        "excluded_paths": list(EXCLUDED_CYCLE_PATHS),
        "files": sorted(records, key=lambda item: (item["category"], item["path"])),
    }
    return document, findings


def _manifest_self_path(root: Path, manifest_path: Path) -> str | None:
    relative = _relative_to_root(root, manifest_path)
    return relative if relative is not None and _safe_relative_path(relative) else None


def _validate_manifest_document(
    document: Any,
    raw_bytes: bytes,
    manifest_path: Path,
    root: Path,
    current_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not isinstance(document, dict):
        return [
            _finding(
                "MANIFEST_SHAPE_INVALID",
                "$",
                "manifest top level must be an object",
            )
        ]
    if set(document) != MANIFEST_KEYS:
        findings.append(
            _finding(
                "MANIFEST_SHAPE_INVALID",
                "$",
                "manifest top-level keys do not exactly match the closed schema",
                detail={
                    "missing": sorted(MANIFEST_KEYS - set(document)),
                    "unexpected": sorted(set(document) - MANIFEST_KEYS),
                },
            )
        )
    if document.get("manifest_schema") != MANIFEST_SCHEMA:
        findings.append(
            _finding(
                "MANIFEST_SCHEMA_MISMATCH",
                "$.manifest_schema",
                "manifest schema identifier is not the expected frozen-candidate schema",
            )
        )
    if document.get("registry_version") != REGISTRY_VERSION:
        findings.append(
            _finding(
                "MANIFEST_REGISTRY_VERSION_MISMATCH",
                "$.registry_version",
                "manifest registry version differs from this checker",
            )
        )
    if document.get("excluded_paths") != list(EXCLUDED_CYCLE_PATHS):
        findings.append(
            _finding(
                "MANIFEST_EXCLUSION_SET_MISMATCH",
                "$.excluded_paths",
                "manifest must record the exact deterministic cyclic-path exclusions",
            )
        )

    files = document.get("files")
    if not isinstance(files, list):
        findings.append(
            _finding(
                "MANIFEST_SHAPE_INVALID",
                "$.files",
                "manifest files must be an array",
            )
        )
        return findings
    file_count = document.get("file_count")
    if (
        not isinstance(file_count, int)
        or isinstance(file_count, bool)
        or file_count != len(files)
        or file_count != len(registry_entries())
    ):
        findings.append(
            _finding(
                "MANIFEST_FILE_COUNT_MISMATCH",
                "$.file_count",
                "file_count must exactly equal both the manifest entry count and closed registry count",
                detail={
                    "declared": file_count,
                    "manifest_entries": len(files),
                    "registry_entries": len(registry_entries()),
                },
            )
        )

    parsed_entries: list[dict[str, Any]] = []
    observed_pairs: list[tuple[str, str]] = []
    observed_paths: list[str] = []
    manifest_relative = _manifest_self_path(root, manifest_path)
    for index, entry in enumerate(files):
        entry_path = f"$.files[{index}]"
        if not isinstance(entry, dict) or set(entry) != ENTRY_KEYS:
            findings.append(
                _finding(
                    "MANIFEST_ENTRY_INVALID",
                    entry_path,
                    "each manifest entry must contain exactly category, path, bytes, and sha256",
                )
            )
            continue
        category = entry.get("category")
        relative_path = entry.get("path")
        byte_count = entry.get("bytes")
        digest = entry.get("sha256")
        valid = True
        if not isinstance(category, str) or CATEGORY_RE.fullmatch(category) is None:
            valid = False
        if not _safe_relative_path(relative_path):
            valid = False
            findings.append(
                _finding(
                    "MANIFEST_PATH_UNSAFE",
                    f"{entry_path}.path",
                    "manifest entry path must be a canonical safe POSIX relative path",
                    detail=relative_path,
                )
            )
        if (
            not isinstance(byte_count, int)
            or isinstance(byte_count, bool)
            or byte_count < 0
        ):
            valid = False
        if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
            valid = False
        if not valid:
            findings.append(
                _finding(
                    "MANIFEST_ENTRY_INVALID",
                    entry_path,
                    "manifest entry field types or values are invalid",
                )
            )
            continue
        if relative_path in EXCLUDED_CYCLE_PATHS:
            findings.append(
                _finding(
                    "MANIFEST_CYCLE_PATH_INCLUDED",
                    f"{entry_path}.path",
                    "cyclic release manifest or checksum paths must be excluded",
                    detail=relative_path,
                )
            )
        if manifest_relative is not None and relative_path == manifest_relative:
            findings.append(
                _finding(
                    "MANIFEST_SELF_REFERENCE",
                    f"{entry_path}.path",
                    "a frozen candidate manifest must not hash itself",
                    detail=relative_path,
                )
            )
        parsed_entries.append(entry)
        observed_pairs.append((category, relative_path))
        observed_paths.append(relative_path)

    if len(observed_pairs) != len(set(observed_pairs)) or len(observed_paths) != len(set(observed_paths)):
        findings.append(
            _finding(
                "MANIFEST_DUPLICATE_ENTRY",
                "$.files",
                "manifest category/path pairs and paths must be globally unique",
            )
        )
    if observed_pairs != sorted(observed_pairs):
        findings.append(
            _finding(
                "MANIFEST_ORDER_INVALID",
                "$.files",
                "manifest entries must be sorted deterministically by category then path",
            )
        )

    expected_pairs = set(registry_entries())
    observed_pair_set = set(observed_pairs)
    if observed_pair_set != expected_pairs:
        findings.append(
            _finding(
                "MANIFEST_MEMBERSHIP_MISMATCH",
                "$.files",
                "manifest membership must exactly equal the explicit frozen registry",
                detail={
                    "missing": [
                        {"category": category, "path": path}
                        for category, path in sorted(expected_pairs - observed_pair_set)
                    ],
                    "unexpected": [
                        {"category": category, "path": path}
                        for category, path in sorted(observed_pair_set - expected_pairs)
                    ],
                },
            )
        )

    current_by_pair = {
        (entry["category"], entry["path"]): entry for entry in current_records
    }
    for index, entry in enumerate(parsed_entries):
        pair = (entry["category"], entry["path"])
        current = current_by_pair.get(pair)
        if current is None:
            continue
        if entry["bytes"] != current["bytes"]:
            findings.append(
                _finding(
                    "MANIFEST_BYTES_MISMATCH",
                    f"$.files[{index}].bytes",
                    "manifest byte count differs from the current frozen file",
                    detail={
                        "path": entry["path"],
                        "expected": entry["bytes"],
                        "observed": current["bytes"],
                    },
                )
            )
        if entry["sha256"] != current["sha256"]:
            findings.append(
                _finding(
                    "MANIFEST_SHA256_MISMATCH",
                    f"$.files[{index}].sha256",
                    "manifest SHA-256 differs from the current frozen file bytes",
                    detail={
                        "path": entry["path"],
                        "expected": entry["sha256"],
                        "observed": current["sha256"],
                    },
                )
            )

    try:
        canonical = _manifest_bytes(document)
    except (TypeError, ValueError):
        canonical = b""
    if raw_bytes != canonical:
        findings.append(
            _finding(
                "MANIFEST_SERIALIZATION_NONCANONICAL",
                "$",
                "manifest bytes must use the deterministic canonical JSON serialization",
            )
        )
    return findings


def check_manifest(
    manifest_path: Path,
    root: Path = ROOT,
    *,
    expected_manifest_sha256: str | None = None,
) -> tuple[int, dict[str, Any]]:
    current_records, findings = _inspect_registry(root)
    raw_bytes: bytes | None = None
    document: Any = None
    try:
        if manifest_path.is_symlink():
            findings.append(
                _finding(
                    "MANIFEST_READ_TARGET_INVALID",
                    str(manifest_path),
                    "manifest read target must not be a symbolic link",
                )
            )
        else:
            raw_bytes = _read_manifest_bounded(manifest_path)
    except ValueError:
        findings.append(
            _finding(
                "MANIFEST_TOO_LARGE",
                str(manifest_path),
                "manifest exceeds the inspection byte limit",
                detail={"max_bytes": MAX_MANIFEST_BYTES},
            )
        )
    except OSError as exc:
        findings.append(
            _finding(
                "MANIFEST_READ_FAILED",
                str(manifest_path),
                "manifest could not be read",
                detail=str(exc),
            )
        )
    if raw_bytes is not None:
        observed_manifest_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        if expected_manifest_sha256 is not None:
            if SHA256_RE.fullmatch(expected_manifest_sha256) is None:
                findings.append(
                    _finding(
                        "MANIFEST_EXPECTED_SHA256_INVALID",
                        "$.expected_manifest_sha256",
                        "expected manifest SHA-256 must be 64 lowercase hexadecimal characters",
                    )
                )
            elif observed_manifest_sha256 != expected_manifest_sha256:
                findings.append(
                    _finding(
                        "MANIFEST_EXPECTED_SHA256_MISMATCH",
                        str(manifest_path),
                        "manifest bytes differ from the predeclared frozen digest",
                        detail={
                            "expected": expected_manifest_sha256,
                            "observed": observed_manifest_sha256,
                        },
                    )
                )
        try:
            document = _strict_json(raw_bytes)
        except StrictJsonError as exc:
            findings.append(
                _finding(
                    "MANIFEST_JSON_INVALID",
                    str(manifest_path),
                    str(exc),
                )
            )
        else:
            findings.extend(
                _validate_manifest_document(
                    document,
                    raw_bytes,
                    manifest_path,
                    root,
                    current_records,
                )
            )

    else:
        observed_manifest_sha256 = None
    sorted_findings = _sort_findings(findings)
    payload = {
        "checker": "gpt_frozen_candidate",
        "output_version": OUTPUT_VERSION,
        "operation": "check",
        "status": "blocked" if sorted_findings else "pass",
        "manifest_path": str(manifest_path),
        "manifest_sha256": observed_manifest_sha256,
        "registry_file_count": len(registry_entries()),
        "findings": sorted_findings,
    }
    return (1 if sorted_findings else 0), payload


def _validate_write_target(
    manifest_path: Path,
    root: Path,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    relative = _manifest_self_path(root, manifest_path)
    registry_paths = {path for _, path in registry_entries()}
    if manifest_path.is_symlink():
        findings.append(
            _finding(
                "MANIFEST_WRITE_TARGET_INVALID",
                str(manifest_path),
                "manifest write target must not be a symbolic link",
            )
        )
    if relative in registry_paths:
        findings.append(
            _finding(
                "MANIFEST_SELF_REFERENCE",
                str(manifest_path),
                "manifest write target cannot overwrite a frozen registry file",
                detail=relative,
            )
        )
    if relative in EXCLUDED_CYCLE_PATHS:
        findings.append(
            _finding(
                "MANIFEST_WRITE_TARGET_RESERVED",
                str(manifest_path),
                "frozen manifest must not overwrite a cyclic release manifest or checksum file",
                detail=relative,
            )
        )
    if relative is not None:
        parent = PurePosixPath(relative).parent.as_posix()
        if parent in CLOSED_DIRECTORIES:
            findings.append(
                _finding(
                    "MANIFEST_WRITE_TARGET_RESERVED",
                    str(manifest_path),
                    "manifest must not be written inside a closed registry directory",
                    detail=relative,
                )
            )
    try:
        if manifest_path.exists() and not manifest_path.is_file():
            findings.append(
                _finding(
                    "MANIFEST_WRITE_TARGET_INVALID",
                    str(manifest_path),
                    "manifest write target exists and is not a regular file",
                )
            )
        if not manifest_path.parent.is_dir():
            findings.append(
                _finding(
                    "MANIFEST_WRITE_TARGET_INVALID",
                    str(manifest_path),
                    "manifest parent directory must already exist",
                )
            )
    except OSError as exc:
        findings.append(
            _finding(
                "MANIFEST_WRITE_TARGET_INVALID",
                str(manifest_path),
                "manifest write target could not be inspected",
                detail=str(exc),
            )
        )
    return findings


def _atomic_write(path: Path, data: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass


def write_manifest(
    manifest_path: Path,
    root: Path = ROOT,
) -> tuple[int, dict[str, Any]]:
    findings = _validate_write_target(manifest_path, root)
    document, registry_findings = build_manifest(root)
    findings.extend(registry_findings)
    data = _manifest_bytes(document)
    if not findings:
        try:
            _atomic_write(manifest_path, data)
            if manifest_path.read_bytes() != data:
                raise OSError("post-write byte verification failed")
        except OSError as exc:
            findings.append(
                _finding(
                    "MANIFEST_WRITE_FAILED",
                    str(manifest_path),
                    "manifest could not be atomically written and reverified",
                    detail=str(exc),
                )
            )
    sorted_findings = _sort_findings(findings)
    payload = {
        "checker": "gpt_frozen_candidate",
        "output_version": OUTPUT_VERSION,
        "operation": "write",
        "status": "blocked" if sorted_findings else "pass",
        "manifest_path": str(manifest_path),
        "manifest_sha256": hashlib.sha256(data).hexdigest(),
        "registry_file_count": len(registry_entries()),
        "findings": sorted_findings,
    }
    return (1 if sorted_findings else 0), payload


def _parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(
        prog="check_gpt_frozen_candidate.py",
        description="Write or verify the deterministic closed Custom GPT candidate manifest",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", metavar="MANIFEST", type=Path)
    mode.add_argument("--check", metavar="MANIFEST", type=Path)
    parser.add_argument("--expect-manifest-sha256")
    return parser


def main(argv: list[str] | None = None, *, root: Path = ROOT) -> int:
    try:
        args = _parser().parse_args(argv)
        if args.write is not None and args.expect_manifest_sha256 is not None:
            raise CliUsageError(
                "--expect-manifest-sha256 is valid only with --check"
            )
    except CliUsageError as exc:
        payload = {
            "checker": "gpt_frozen_candidate",
            "output_version": OUTPUT_VERSION,
            "operation": "cli",
            "status": "blocked",
            "manifest_path": None,
            "registry_file_count": len(registry_entries()),
            "findings": [
                _finding(
                    "CLI_USAGE",
                    "$",
                    str(exc),
                )
            ],
        }
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return 2

    if args.write is not None:
        status, payload = write_manifest(args.write, root)
    else:
        status, payload = check_manifest(
            args.check,
            root,
            expected_manifest_sha256=args.expect_manifest_sha256,
        )
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
