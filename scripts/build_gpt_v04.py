#!/usr/bin/env python3
"""Build and verify the active BSC Claim Auditor v0.4 source candidate."""

from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import os
import re
import stat
import tempfile
import unicodedata
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
V04_ROOT = ROOT / "gpt-v0.4"
SOURCE_ROOT = V04_ROOT / "source"
EVAL_ROOT = V04_ROOT / "evals"
DIST_ROOT = V04_ROOT / "dist"
BUILDER_PATH = ROOT / "scripts" / "build_gpt_v04.py"

PROFILE_PATH = SOURCE_ROOT / "profile.json"
METADATA_PATH = SOURCE_ROOT / "public_metadata.json"
STARTERS_PATH = SOURCE_ROOT / "conversation_starters.json"
CATALOG_PATH = SOURCE_ROOT / "checks_catalog.json"

SOURCE_MEMBERS = (
    "checks_catalog.json",
    "conversation_starters.json",
    "instructions.md",
    "knowledge/01-core-guide.md",
    "knowledge/02-checks-catalog.md",
    "knowledge/03-worked-examples.md",
    "knowledge/04-japanese-glossary.md",
    "profile.json",
    "public_metadata.json",
)
EVAL_MEMBERS = (
    "development-regressions.json",
    "evaluation-status.json",
    "evaluator-calibration.json",
    "hard-gates.md",
    "prospective-canaries.json",
)
DIST_MEMBERS = (
    "GPT_CONVERSATION_STARTERS.md",
    "GPT_EVALUATION_STATUS.json",
    "GPT_INSTRUCTIONS.md",
    "GPT_PRODUCT_LOCK.json",
    "GPT_PUBLIC_METADATA.md",
    "GPT_SETUP.md",
    "README.md",
    "SHA256SUMS",
    "knowledge/BSC_CHECKS_CATALOG.md",
    "knowledge/BSC_CORE_GUIDE.md",
    "knowledge/BSC_EXAMPLES.md",
    "knowledge/BSC_JAPANESE_GLOSSARY.md",
)
KNOWLEDGE_UPLOADS = (
    "knowledge/BSC_CORE_GUIDE.md",
    "knowledge/BSC_CHECKS_CATALOG.md",
    "knowledge/BSC_EXAMPLES.md",
    "knowledge/BSC_JAPANESE_GLOSSARY.md",
)
MODEL_FACING_MEMBERS = (
    "GPT_INSTRUCTIONS.md",
    "GPT_PUBLIC_METADATA.md",
    "GPT_CONVERSATION_STARTERS.md",
    *KNOWLEDGE_UPLOADS,
)
ENGINE_COMMANDS = (
    "lint",
    "audit",
    "complex",
    "observe",
    "atomic",
    "defect",
    "adapter",
    "holonomy",
    "theorem",
    "census",
    "return-desk",
)
CASE_IDS = (
    "correct-closed-proof",
    "decisive-counterexample",
    "missing-or-truncated-source",
    "planned-unexecuted-calculation",
    "contradictory-evidence",
    "quoted-prompt-injection",
    "mathematics-to-deployment",
    "upload-privacy-and-disabled-export",
    "japanese-official-status-separation",
)
CALIBRATION_PRINCIPLES = (
    "authority",
    "format",
    "execution",
    "conflict",
    "injection",
    "missing-proof",
    "upload-privacy",
    "japanese",
    "identifiers",
    "controller",
)
HARD_GATE_IDS = tuple(f"H{number:02d}" for number in range(1, 10))
EXPECTED_CAPABILITIES = {
    "web_search": True,
    "code_interpreter_and_data_analysis": True,
    "image_generation": False,
    "apps": False,
    "actions": False,
    "canvas": False,
}
ARCHIVE_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
ARCHIVE_ROOT = "BSC_CLAIM_AUDITOR_0.4.0-preview.1"
CANONICAL_ARCHIVE_PATH = V04_ROOT / "BSC-Claim-Auditor-v0.4.0-preview.1.zip"
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
WINDOWS_DEVICE_RE = re.compile(
    r"(?i)(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?\Z"
)
PRIVATE_PATTERNS = (
    ("CODEX_PATH", re.compile(r"(?i)(?:^|[/\\])\.codex(?:[/\\]|$)")),
    ("ATTACHMENT_PATH", re.compile(r"(?i)(?:^|[/\\])attachments?(?:[/\\]|$)")),
    (
        "LOCAL_ABSOLUTE_PATH",
        re.compile(r"(?i)(?:[a-z]:[/\\](?:users|windows|temp)[/\\]|/(?:users|home|root|tmp|private/tmp)/)"),
    ),
    ("PRIVATE_CHAT_URL", re.compile(r"(?i)https?://chatgpt\.com/(?:c|share)/")),
    ("OPAQUE_GPT_ID", re.compile(r"\bg-[0-9a-f]{20,}\b")),
    ("SESSION_ID", re.compile(r"\b019[0-9a-f]{5,}(?:-[0-9a-f]{4,}){3,}\b", re.I)),
    ("PERSONAL_USERNAME", re.compile(r"(?i)Pirate[ _-]?Dude|DESKTOP-[A-Z0-9]+")),
    ("GITHUB_TOKEN", re.compile(r"(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{20,}")),
    ("OPENAI_KEY", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
    ("AWS_KEY", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("SLACK_TOKEN", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")),
    ("BEARER_SECRET", re.compile(r"(?i)\bauthorization\s*[:=]\s*bearer\s+[A-Za-z0-9._~-]{12,}")),
    ("COOKIE_SECRET", re.compile(r"(?i)\bcookie\s*[:=]\s*[^\s;]{12,}")),
)


class BuildError(ValueError):
    """Raised when active source, output, or archive bytes violate the contract."""


class StrictJsonError(BuildError):
    """Raised when authored JSON is ambiguous or non-canonical in type."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise StrictJsonError(f"non-finite JSON constant: {value}")


def strict_json_bytes(data: bytes, *, label: str) -> Any:
    if data.startswith(b"\xef\xbb\xbf"):
        raise StrictJsonError(f"{label}: UTF-8 BOM is forbidden")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrictJsonError(f"{label}: JSON is not strict UTF-8") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, TypeError) as exc:
        raise StrictJsonError(f"{label}: invalid strict JSON") from exc


def canonical_json(document: Any) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _portable_part_key(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def safe_member_name(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    if value != unicodedata.normalize("NFC", value):
        return False
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return False
    if re.match(r"^[A-Za-z]:", value) or value.startswith(("/", "//")):
        return False
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts:
        return False
    for part in path.parts:
        if part in {"", ".", ".."} or ":" in part:
            return False
        if part.endswith((".", " ")) or WINDOWS_DEVICE_RE.fullmatch(part):
            return False
    return True


def validate_path_roster(paths: Iterable[str], *, label: str) -> tuple[str, ...]:
    values = tuple(paths)
    if len(values) != len(set(values)):
        raise BuildError(f"{label}: duplicate path")
    folded: dict[tuple[str, ...], str] = {}
    for value in values:
        if not safe_member_name(value):
            raise BuildError(f"{label}: unsafe path: {value!r}")
        key = tuple(_portable_part_key(part) for part in PurePosixPath(value).parts)
        if key in folded:
            raise BuildError(
                f"{label}: portable case/Unicode collision: {folded[key]!r}, {value!r}"
            )
        folded[key] = value
    return values


def _is_reparse_or_symlink(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError as exc:
        raise BuildError(f"cannot inspect path: {path}") from exc
    attributes = int(getattr(info, "st_file_attributes", 0))
    return path.is_symlink() or bool(attributes & 0x400)


def assert_safe_regular_file(root: Path, relative: str) -> Path:
    if not safe_member_name(relative):
        raise BuildError(f"unsafe declared source path: {relative!r}")
    root_resolved = root.resolve()
    target = root / PurePosixPath(relative)
    try:
        target.resolve().relative_to(root_resolved)
    except (OSError, ValueError) as exc:
        raise BuildError(f"declared source escapes its root: {relative}") from exc
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        if not current.exists():
            raise BuildError(f"declared source is missing: {relative}")
        if _is_reparse_or_symlink(current):
            raise BuildError(f"declared source uses symlink/reparse component: {relative}")
    if not target.is_file():
        raise BuildError(f"declared source is not a regular file: {relative}")
    return target


def read_text_bytes(path: Path, *, label: str) -> tuple[bytes, str]:
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        raise BuildError(f"{label}: UTF-8 BOM is forbidden")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BuildError(f"{label}: not strict UTF-8") from exc
    if "\r" in text:
        raise BuildError(f"{label}: CR bytes are forbidden; use LF")
    if not text.endswith("\n"):
        raise BuildError(f"{label}: one terminal LF is required")
    if "\x00" in text:
        raise BuildError(f"{label}: NUL is forbidden")
    for char in text:
        if ord(char) < 32 and char not in {"\n", "\t"}:
            raise BuildError(f"{label}: nonportable control character is forbidden")
    return data, text


def read_json(path: Path, *, label: str) -> dict[str, Any]:
    data, _ = read_text_bytes(path, label=label)
    value = strict_json_bytes(data, label=label)
    if not isinstance(value, dict):
        raise StrictJsonError(f"{label}: top level must be an object")
    return value


def exact_keys(value: dict[str, Any], expected: set[str], *, label: str) -> None:
    if set(value) != expected:
        raise BuildError(
            f"{label}: fields differ; missing={sorted(expected - set(value))}; "
            f"extra={sorted(set(value) - expected)}"
        )


def require_nonempty_string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise BuildError(f"{label}: expected a trimmed nonempty string")
    return value


def scan_private_material(label: str, data: bytes) -> None:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return
    for code, pattern in PRIVATE_PATTERNS:
        if pattern.search(text):
            raise BuildError(f"{label}: private/operator material rejected ({code})")


def file_record(path: str, data: bytes) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": path,
        "bytes": len(data),
        "sha256": sha256_bytes(data),
    }
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return record
    record["characters"] = len(text)
    record["lines"] = len(text.splitlines())
    return record


def _actual_files(root: Path) -> set[str]:
    if not root.is_dir():
        raise BuildError(f"required directory is missing: {root}")
    values: set[str] = set()
    for path in root.rglob("*"):
        if _is_reparse_or_symlink(path):
            raise BuildError(f"symlink/reparse point is forbidden: {path}")
        if path.is_file():
            values.add(path.relative_to(root).as_posix())
    return values


def validate_source_closure() -> None:
    validate_path_roster(SOURCE_MEMBERS, label="source roster")
    validate_path_roster(EVAL_MEMBERS, label="evaluation roster")
    actual_source = _actual_files(SOURCE_ROOT)
    actual_eval = _actual_files(EVAL_ROOT)
    if actual_source != set(SOURCE_MEMBERS):
        raise BuildError(
            f"source closure differs; missing={sorted(set(SOURCE_MEMBERS) - actual_source)}; "
            f"extra={sorted(actual_source - set(SOURCE_MEMBERS))}"
        )
    if actual_eval != set(EVAL_MEMBERS):
        raise BuildError(
            f"evaluation closure differs; missing={sorted(set(EVAL_MEMBERS) - actual_eval)}; "
            f"extra={sorted(actual_eval - set(EVAL_MEMBERS))}"
        )
    for relative in SOURCE_MEMBERS:
        assert_safe_regular_file(SOURCE_ROOT, relative)
    for relative in EVAL_MEMBERS:
        assert_safe_regular_file(EVAL_ROOT, relative)


def validate_profile(profile: dict[str, Any]) -> None:
    exact_keys(
        profile,
        {
            "schema",
            "authority_state",
            "product_version",
            "candidate_id",
            "dependencies",
            "model_recommendation",
            "capabilities",
            "source_paths",
            "authority_homes",
            "build",
        },
        label="profile",
    )
    if profile["schema"] != "bsc-claim-auditor-profile/v2":
        raise BuildError("profile schema mismatch")
    if profile["authority_state"] != "ACTIVE":
        raise BuildError("product profile must be the sole ACTIVE profile")
    if profile["product_version"] != "0.4.0-preview.1":
        raise BuildError("product version mismatch")
    if profile["candidate_id"] != "bsc-claim-auditor-v0.4.0-preview.1":
        raise BuildError("candidate identity mismatch")
    dependencies = profile["dependencies"]
    if not isinstance(dependencies, dict):
        raise BuildError("dependencies must be an object")
    exact_keys(dependencies, {"bsc_engine", "canonical_protocol"}, label="dependencies")
    if dependencies["bsc_engine"] != {
        "public_version": "v0.3.0-alpha.20",
        "python_version": "0.3.0a20",
        "behavior": "UNCHANGED",
    }:
        raise BuildError("BSC engine dependency changed")
    if dependencies["canonical_protocol"] != {
        "version": "0.3.0-alpha.13",
        "component_contract_schema": "bsc-component-contract/v2",
        "behavior": "UNCHANGED",
    }:
        raise BuildError("canonical protocol/schema dependency changed")
    if profile["model_recommendation"] != {
        "mode": "default",
        "fixed_engine_identity": False,
    }:
        raise BuildError("model recommendation must remain default and unpinned")
    if profile["capabilities"] != EXPECTED_CAPABILITIES:
        raise BuildError("capability, Apps, Actions, or Canvas boundary changed")
    source_paths = profile["source_paths"]
    if not isinstance(source_paths, dict):
        raise BuildError("source_paths must be an object")
    exact_keys(
        source_paths,
        {
            "instructions",
            "public_metadata",
            "conversation_starters",
            "checks_catalog",
            "knowledge",
        },
        label="source_paths",
    )
    expected_top = {
        "instructions": "gpt-v0.4/source/instructions.md",
        "public_metadata": "gpt-v0.4/source/public_metadata.json",
        "conversation_starters": "gpt-v0.4/source/conversation_starters.json",
        "checks_catalog": "gpt-v0.4/source/checks_catalog.json",
    }
    for key, expected in expected_top.items():
        if source_paths[key] != expected:
            raise BuildError(f"profile source path changed: {key}")
    knowledge = source_paths["knowledge"]
    if not isinstance(knowledge, list) or len(knowledge) != 4:
        raise BuildError("profile must declare exactly four Knowledge sources")
    observed_uploads: list[str] = []
    observed_sources: list[str] = []
    for index, item in enumerate(knowledge, 1):
        if not isinstance(item, dict):
            raise BuildError("Knowledge declaration must be an object")
        keys = {"order", "source", "upload"}
        if index == 2:
            keys.add("generated_from")
        exact_keys(item, keys, label=f"knowledge[{index}]")
        if item["order"] != index:
            raise BuildError("Knowledge order must be 1 through 4")
        observed_sources.append(require_nonempty_string(item["source"], label="Knowledge source"))
        observed_uploads.append(require_nonempty_string(item["upload"], label="Knowledge upload"))
    if tuple(observed_uploads) != KNOWLEDGE_UPLOADS:
        raise BuildError("Knowledge upload roster/order changed")
    expected_sources = tuple(f"gpt-v0.4/source/{item}" for item in SOURCE_MEMBERS if item.startswith("knowledge/"))
    if tuple(observed_sources) != expected_sources:
        raise BuildError("Knowledge source roster/order changed")
    homes = profile["authority_homes"]
    if not isinstance(homes, dict) or len(homes) != 10:
        raise BuildError("authority-home map must declare exactly ten rule families")
    normative = [value for value in homes.values() if value != "NON_NORMATIVE"]
    if len(normative) != len(set(normative)):
        raise BuildError("two normative rule families share an ambiguous authority home")
    build = profile["build"]
    if build != {
        "encoding": "UTF-8",
        "newline": "LF",
        "instructions_target_min_characters": 3000,
        "instructions_target_max_characters": 4000,
        "instructions_hard_max_characters": 4500,
        "knowledge_file_count": 4,
        "output": "gpt-v0.4/dist",
        "archive_compression": "ZIP_STORED",
        "archive_timestamp": "1980-01-01T00:00:00Z",
    }:
        raise BuildError("build settings differ from the reviewed deterministic contract")


def validate_engine_dependencies(profile: dict[str, Any]) -> None:
    init_text = (ROOT / "src" / "bsc_audit" / "__init__.py").read_text(encoding="utf-8")
    if '__version__ = "0.3.0a20"' not in init_text:
        raise BuildError("BSC engine Python version changed")
    contract = read_json(
        ROOT / "src" / "bsc_audit" / "component_contract.json",
        label="component contract",
    )
    if contract.get("contract_schema") != "bsc-component-contract/v2":
        raise BuildError("component contract schema changed")
    protocol = contract.get("protocol")
    if not isinstance(protocol, dict) or protocol.get("version") != "0.3.0-alpha.13":
        raise BuildError("canonical protocol version changed")
    expected = profile["dependencies"]["canonical_protocol"]
    if expected["component_contract_schema"] != contract["contract_schema"]:
        raise BuildError("profile and component contract schema disagree")


def validate_metadata(metadata: dict[str, Any]) -> None:
    exact_keys(
        metadata,
        {"schema", "name", "description", "category_recommendation"},
        label="public metadata",
    )
    if metadata["schema"] != "bsc-claim-auditor-public-metadata/v1":
        raise BuildError("public metadata schema mismatch")
    if metadata["name"] != "BSC Claim Auditor":
        raise BuildError("product name changed")
    description = require_nonempty_string(metadata["description"], label="description")
    if len(description) > 300 or "Research aid" not in description or "Japanese beta" not in description:
        raise BuildError("public description is not the reviewed concise boundary")
    if metadata["category_recommendation"] != "Education":
        raise BuildError("category recommendation changed")
    mutable_tokens = ("LIVE", "PENDING", "installed", "validated", "public_url")
    if any(token.lower() in description.lower() for token in mutable_tokens):
        raise BuildError("mutable current-service status appears in public metadata")


def validate_starters(starters: dict[str, Any]) -> None:
    exact_keys(starters, {"schema", "starters"}, label="conversation starters")
    if starters["schema"] != "bsc-claim-auditor-conversation-starters/v1":
        raise BuildError("conversation-starter schema mismatch")
    values = starters["starters"]
    if not isinstance(values, list) or len(values) != 4 or len(set(values)) != 4:
        raise BuildError("exactly four distinct conversation starters are required")
    if any(not isinstance(value, str) or not value.strip() or len(value) > 100 for value in values):
        raise BuildError("conversation starter is empty or too long")
    if not any(re.search(r"[ぁ-んァ-ヶ一-龠]", value) for value in values):
        raise BuildError("one natural Japanese starter is required")


def validate_instructions(text: str, profile: dict[str, Any]) -> None:
    headings = re.findall(r"^(#{1,6}) (.+)$", text, flags=re.MULTILINE)
    expected = [
        ("#", "1. Role and promise"),
        ("##", "2. Intake and depth"),
        ("##", "3. Three semantic lanes"),
        ("##", "4. Evidence and execution honesty"),
        ("##", "5. Adversarial review and smallest repair"),
        ("##", "6. Security, privacy, citations, and tools"),
        ("##", "7. Response shape and boundary"),
    ]
    if headings != expected:
        raise BuildError("Instructions must contain the exact seven-section structure once")
    settings = profile["build"]
    if len(text) < settings["instructions_target_min_characters"]:
        raise BuildError("Instructions are below the 3,000-character target")
    if len(text) > settings["instructions_target_max_characters"]:
        raise BuildError("Instructions exceed the 4,000-character target")
    if len(text) > settings["instructions_hard_max_characters"]:
        raise BuildError("Instructions exceed the 4,500-character hard maximum")
    forbidden = (
        r"\bT1\b",
        r"\bC1\b",
        r"nine[- ]duty",
        r"Base64",
        r"\bshards?\b",
        r"Return Desk",
        r"artifact compiler",
        r"Section 10",
        r"exact response-token",
        r"claim cardinality",
    )
    for pattern in forbidden:
        if re.search(pattern, text, flags=re.IGNORECASE):
            raise BuildError(f"legacy evaluator jargon remains in Instructions: {pattern}")
    required = (
        "If a claim is supplied, audit it immediately.",
        "Otherwise ask for one sentence",
        "Bottom line, Why, Weakest point, Best next check",
        "Custom GPT uploads are not local-only",
        "Allow a requested hash when byte identity is relevant and safe",
        "Mathematics never substitutes",
        "A model completion is a proposed repair, not evidence",
        "Use the requested language",
    )
    if any(token not in text for token in required):
        raise BuildError("Instructions omit a reviewed product or safety invariant")


def validate_catalog(catalog: dict[str, Any]) -> None:
    exact_keys(catalog, {"schema", "authority_state", "engine_version", "checks"}, label="checks catalog")
    if catalog["schema"] != "bsc-claim-auditor-checks-catalog/v1":
        raise BuildError("checks catalog schema mismatch")
    if catalog["authority_state"] != "ACTIVE_IMPLEMENTATION_PROJECTION":
        raise BuildError("checks catalog authority state mismatch")
    if catalog["engine_version"] != "v0.3.0-alpha.20":
        raise BuildError("checks catalog engine identity changed")
    checks = catalog["checks"]
    if not isinstance(checks, list) or len(checks) != len(ENGINE_COMMANDS):
        raise BuildError("checks catalog must cover every implemented CLI route exactly once")
    fields = {
        "id",
        "command",
        "accepted_input",
        "establishes",
        "does_not_establish",
        "required_executor",
        "execution_evidence_required",
        "known_limitations",
    }
    commands: list[str] = []
    ids: list[str] = []
    for index, item in enumerate(checks):
        if not isinstance(item, dict):
            raise BuildError("check record must be an object")
        exact_keys(item, fields, label=f"checks[{index}]")
        for field in fields:
            require_nonempty_string(item[field], label=f"checks[{index}].{field}")
        commands.append(item["command"])
        ids.append(item["id"])
    if tuple(commands) != ENGINE_COMMANDS or len(ids) != len(set(ids)):
        raise BuildError("implemented check command order or IDs differ")


def hard_gate_ids(text: str) -> tuple[str, ...]:
    values = tuple(re.findall(r"\*\*(H\d{2})\s+—", text))
    if values != HARD_GATE_IDS:
        raise BuildError("hard-gates.md must define H01 through H09 exactly once in order")
    return values


def classify_calibration_record(record: dict[str, Any]) -> str:
    state = record["controller_state"]
    if state == "TRIAL_INVALID_CONTROLLER":
        return "TRIAL_INVALID_CONTROLLER"
    if state != "CAPTURE_VALID":
        raise BuildError("unknown calibration controller state")
    return "HARD_FAIL" if record["triggered_hard_gates"] else "HARD_PASS"


def validate_development_regressions(document: dict[str, Any]) -> None:
    exact_keys(
        document,
        {
            "schema",
            "authority_state",
            "result_transfer",
            "legacy_authority_routes",
            "campaigns",
            "limits",
        },
        label="development regressions",
    )
    if document["schema"] != "bsc-claim-auditor-development-regressions/v1":
        raise BuildError("development-regression schema mismatch")
    if document["authority_state"] != "HISTORICAL_NONCONTROLLING" or document["result_transfer"] != "FORBIDDEN":
        raise BuildError("historical evidence must be noncontrolling with no transfer")
    routes = document["legacy_authority_routes"]
    if not isinstance(routes, list) or not routes:
        raise BuildError("legacy authority routes are missing")
    route_paths: list[str] = []
    for item in routes:
        if not isinstance(item, dict):
            raise BuildError("legacy route must be an object")
        exact_keys(item, {"path", "state"}, label="legacy route")
        path = require_nonempty_string(item["path"], label="legacy route path")
        if path.startswith("gpt-v0.4/"):
            raise BuildError("active v0.4 path cannot be routed as historical")
        if item["state"] not in {"HISTORICAL_NONCONTROLLING", "HISTORICAL_REPRODUCIBILITY_ONLY"}:
            raise BuildError("legacy route has an active or unknown state")
        route_paths.append(path)
    required_routes = {
        "gpt/_source/",
        "gpt/evals/",
        "gpt/knowledge/",
        "scripts/build_gpt_package.py",
        "scripts/check_gpt_frozen_candidate.py",
    }
    if not required_routes <= set(route_paths):
        raise BuildError("legacy r5 profiles, suites, builders, or Knowledge are not explicitly routed")
    campaigns = document["campaigns"]
    if not isinstance(campaigns, list) or len(campaigns) != 4:
        raise BuildError("sanitized historical campaign aggregate changed")
    r5 = next((item for item in campaigns if item.get("id") == "r5-frozen-26-case-campaign"), None)
    if not isinstance(r5, dict) or "Cases 1–9 passed" not in r5.get("summary", "") or "Case 10 failed" not in r5.get("summary", "") or "Cases 11–26 were not run" not in r5.get("summary", ""):
        raise BuildError("material r5 negative result was not preserved")
    if any(item.get("state") != "HISTORICAL_NONCONTROLLING" for item in campaigns):
        raise BuildError("historical campaign taxonomy is ambiguous or active")
    if any(item.get("evidence_transfer") != "NONE" for item in campaigns):
        raise BuildError("historical campaign attempts result transfer")


def validate_evaluation_status(document: dict[str, Any], *, allow_draft: bool) -> None:
    exact_keys(
        document,
        {
            "schema",
            "evaluator_profile_id",
            "candidate_state",
            "prospective_case_status",
            "prospective_case_count",
            "historical_status_source",
            "evidence_transfer",
            "live_binding_state",
            "installation_state",
            "release_state",
            "publication_state",
            "claims_not_supported",
        },
        label="evaluation status source",
    )
    if document["schema"] != "bsc-claim-auditor-evaluation-status-source/v1":
        raise BuildError("evaluation-status source schema mismatch")
    allowed_state = "PRODUCT_FREEZE_PENDING" if allow_draft else "FROZEN_LOCAL_SOURCE_CANDIDATE"
    if document["candidate_state"] != allowed_state:
        raise BuildError(f"evaluation candidate state must be {allowed_state}")
    if document["prospective_case_status"] != "NOT_RUN_PREVIEW_NOT_AUTHORIZED" or document["prospective_case_count"] != 9:
        raise BuildError("prospective case count/status changed")
    if document["evidence_transfer"] != "NONE_FROM_R2_R5":
        raise BuildError("evaluation status attempts historical result transfer")
    if document["live_binding_state"] != "NON_ADMISSIBLE_UNHASHABLE":
        raise BuildError("opaque live binding state changed")
    if document["installation_state"] != "NOT_ASSESSED" or document["release_state"] != "NOT_AUTHORIZED" or document["publication_state"] != "NOT_AUTHORIZED":
        raise BuildError("installation, release, or publication authority was invented")


def validate_canaries(
    document: dict[str, Any],
    *,
    product_lock_sha256: str,
    allow_draft: bool,
) -> None:
    if allow_draft:
        exact_keys(
            document,
            {"schema", "authority_state", "protocol_id", "state", "product_lock_sha256", "case_count", "cases"},
            label="draft prospective canaries",
        )
        if document != {
            "schema": "bsc-claim-auditor-prospective-canaries/v1",
            "authority_state": "ACTIVE",
            "protocol_id": "bsc-claim-auditor-nine-canaries-v0.4.0-preview.1",
            "state": "AWAITING_PRODUCT_FREEZE",
            "product_lock_sha256": None,
            "case_count": 0,
            "cases": [],
        }:
            raise BuildError("draft prospective protocol differs from the pre-freeze placeholder")
        return
    exact_keys(
        document,
        {
            "schema",
            "authority_state",
            "protocol_id",
            "state",
            "product_lock_sha256",
            "hard_gate_source",
            "controller_contract",
            "future_run_rules",
            "case_count",
            "cases",
        },
        label="prospective canaries",
    )
    if document["schema"] != "bsc-claim-auditor-prospective-canaries/v1" or document["authority_state"] != "ACTIVE":
        raise BuildError("prospective protocol identity/authority mismatch")
    if document["state"] != "FROZEN_NOT_RUN" or document["product_lock_sha256"] != product_lock_sha256:
        raise BuildError("prospective protocol is not bound to the frozen product lock")
    if document["hard_gate_source"] != "gpt-v0.4/evals/hard-gates.md":
        raise BuildError("prospective protocol hard-gate authority changed")
    if document["controller_contract"] != {
        "fresh_default_preview": True,
        "attachments": 0,
        "exact_sends": 1,
        "regenerations": 0,
        "human_semantic_review": True,
        "machine_semantic_grading": False,
    }:
        raise BuildError("prospective controller contract changed")
    future = document["future_run_rules"]
    if not isinstance(future, list) or len(future) < 8 or len(set(future)) != len(future):
        raise BuildError("future live-run rules are incomplete or duplicated")
    cases = document["cases"]
    if document["case_count"] != 9 or not isinstance(cases, list) or len(cases) != 9:
        raise BuildError("prospective protocol must contain exactly nine cases")
    fields = {
        "order",
        "id",
        "title",
        "language",
        "prompt",
        "attachments",
        "status",
        "outcome_oracle",
        "applicable_hard_gates",
        "emergency_stop_on_failure",
    }
    prompts: list[str] = []
    ids: list[str] = []
    for index, item in enumerate(cases, 1):
        if not isinstance(item, dict):
            raise BuildError("prospective case must be an object")
        exact_keys(item, fields, label=f"prospective case {index}")
        if item["order"] != index or item["attachments"] != 0:
            raise BuildError("prospective case order/attachment contract changed")
        if item["status"] != "NOT_RUN_PREVIEW_NOT_AUTHORIZED":
            raise BuildError("prospective case was incorrectly marked run")
        if item["language"] not in {"en", "ja"}:
            raise BuildError("prospective case language must be en or ja")
        prompt = require_nonempty_string(item["prompt"], label="prospective prompt")
        if len(prompt) > 1200 or any(token in prompt.lower() for token in ("hard_pass", "hard_fail", "h01", "rubric", "required heading", "case id")):
            raise BuildError("prospective prompt exposes evaluator machinery or is too long")
        oracle = item["outcome_oracle"]
        if not isinstance(oracle, dict):
            raise BuildError("case outcome oracle must be an object")
        exact_keys(oracle, {"must", "must_not"}, label="case outcome oracle")
        if any(not isinstance(values, list) or not values for values in oracle.values()):
            raise BuildError("case outcome oracle must contain nonempty must/must_not lists")
        gates = item["applicable_hard_gates"]
        if not isinstance(gates, list) or not gates or not set(gates) <= set(HARD_GATE_IDS):
            raise BuildError("case references an unknown or empty hard-gate set")
        if not isinstance(item["emergency_stop_on_failure"], bool):
            raise BuildError("emergency stop flag must be boolean")
        prompts.append(prompt)
        ids.append(item["id"])
    if tuple(ids) != CASE_IDS or len(set(prompts)) != 9:
        raise BuildError("prospective case IDs/order or prompt uniqueness changed")
    if cases[-1]["language"] != "ja" or any(item["language"] == "ja" for item in cases[:-1]):
        raise BuildError("exactly the ninth prospective case must require Japanese")


def validate_calibration(
    document: dict[str, Any],
    *,
    product_lock_sha256: str,
    allow_draft: bool,
) -> None:
    invariant = {
        "controller_invalid": "TRIAL_INVALID_CONTROLLER",
        "controller_valid_with_any_triggered_hard_gate": "HARD_FAIL",
        "controller_valid_with_no_triggered_hard_gate": "HARD_PASS",
        "soft_findings_change_hard_result": False,
    }
    if allow_draft:
        exact_keys(
            document,
            {"schema", "state", "product_lock_sha256", "classification_invariant", "pairs"},
            label="draft evaluator calibration",
        )
        if document != {
            "schema": "bsc-claim-auditor-evaluator-calibration/v1",
            "state": "AWAITING_PRODUCT_FREEZE",
            "product_lock_sha256": None,
            "classification_invariant": invariant,
            "pairs": [],
        }:
            raise BuildError("draft evaluator calibration differs from the pre-freeze placeholder")
        return
    exact_keys(
        document,
        {"schema", "state", "product_lock_sha256", "hard_gate_source", "classification_invariant", "pairs"},
        label="evaluator calibration",
    )
    if document["schema"] != "bsc-claim-auditor-evaluator-calibration/v1" or document["state"] != "FROZEN":
        raise BuildError("evaluator calibration identity/state mismatch")
    if document["product_lock_sha256"] != product_lock_sha256:
        raise BuildError("evaluator calibration is not bound to the frozen product lock")
    if document["hard_gate_source"] != "gpt-v0.4/evals/hard-gates.md" or document["classification_invariant"] != invariant:
        raise BuildError("calibration general invariant changed")
    pairs = document["pairs"]
    if not isinstance(pairs, list) or len(pairs) != 10:
        raise BuildError("evaluator calibration must contain exactly ten contrast pairs")
    principles: list[str] = []
    for pair in pairs:
        if not isinstance(pair, dict):
            raise BuildError("calibration pair must be an object")
        exact_keys(pair, {"id", "principle", "records"}, label="calibration pair")
        principle = require_nonempty_string(pair["principle"], label="calibration principle")
        records = pair["records"]
        if not isinstance(records, list) or len(records) != 2:
            raise BuildError("each calibration pair must contain two records")
        for record in records:
            if not isinstance(record, dict):
                raise BuildError("calibration record must be an object")
            exact_keys(
                record,
                {
                    "label",
                    "response",
                    "controller_state",
                    "triggered_hard_gates",
                    "soft_findings",
                    "expected_result",
                    "rationale",
                },
                label="calibration record",
            )
            for field in ("label", "response", "expected_result", "rationale"):
                require_nonempty_string(record[field], label=f"calibration {field}")
            gates = record["triggered_hard_gates"]
            soft = record["soft_findings"]
            if not isinstance(gates, list) or not set(gates) <= set(HARD_GATE_IDS):
                raise BuildError("calibration record references unknown hard gate")
            if not isinstance(soft, list) or any(not isinstance(item, str) or not item for item in soft):
                raise BuildError("calibration soft findings must be strings")
            if classify_calibration_record(record) != record["expected_result"]:
                raise BuildError("calibration record violates the general classification invariant")
        principles.append(principle)
    if tuple(principles) != CALIBRATION_PRINCIPLES:
        raise BuildError("calibration principle roster/order changed")


def validate_active_authorities() -> None:
    active_profiles: list[Path] = []
    active_protocols: list[Path] = []
    for path in ROOT.rglob("profile.json"):
        value = read_json(path, label=path.relative_to(ROOT).as_posix())
        if value.get("schema") == "bsc-claim-auditor-profile/v2" and value.get("authority_state") == "ACTIVE":
            active_profiles.append(path)
    for path in ROOT.rglob("prospective-canaries.json"):
        value = read_json(path, label=path.relative_to(ROOT).as_posix())
        if value.get("schema") == "bsc-claim-auditor-prospective-canaries/v1" and value.get("authority_state") == "ACTIVE":
            active_protocols.append(path)
    if active_profiles != [PROFILE_PATH]:
        raise BuildError(f"expected exactly one active product profile: {active_profiles}")
    expected_protocol = EVAL_ROOT / "prospective-canaries.json"
    if active_protocols != [expected_protocol]:
        raise BuildError(f"expected exactly one active evaluation protocol: {active_protocols}")


def render_catalog(catalog: dict[str, Any]) -> bytes:
    lines = [
        "# BSC Implemented Checks Catalog",
        "",
        f"**Engine dependency:** `{catalog['engine_version']}` (unchanged)",
        "",
        "This is a generated projection of `checks_catalog.json`, the authority for implemented check scope. It describes available routes; it does not assert that any route ran for the current user.",
        "",
    ]
    labels = (
        ("Accepted input", "accepted_input"),
        ("Establishes", "establishes"),
        ("Does not establish", "does_not_establish"),
        ("Required executor", "required_executor"),
        ("Execution evidence required", "execution_evidence_required"),
        ("Known limitations", "known_limitations"),
    )
    for item in catalog["checks"]:
        lines.extend((f"## `{item['command']}` — {item['id']}", ""))
        for title, key in labels:
            lines.append(f"- **{title}:** {item[key]}")
        lines.append("")
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def render_metadata(metadata: dict[str, Any], profile: dict[str, Any]) -> bytes:
    capability_lines = [
        f"- **Web Search:** {'enabled' if profile['capabilities']['web_search'] else 'disabled'}",
        f"- **Code Interpreter and Data Analysis:** {'enabled' if profile['capabilities']['code_interpreter_and_data_analysis'] else 'disabled'}",
        f"- **Image Generation:** {'enabled' if profile['capabilities']['image_generation'] else 'disabled'}",
        f"- **Apps:** {'enabled' if profile['capabilities']['apps'] else 'disabled'}",
        f"- **Actions:** {'enabled' if profile['capabilities']['actions'] else 'disabled'}",
        f"- **Canvas:** {'enabled' if profile['capabilities']['canvas'] else 'disabled'}",
    ]
    text = "\n".join(
        [
            "# GPT Public Metadata",
            "",
            f"- **Name:** {metadata['name']}",
            f"- **Description:** {metadata['description']}",
            f"- **Category recommendation:** {metadata['category_recommendation']}",
            "- **Model recommendation:** default mode; no fixed engine identity",
            "",
            "## Capability settings",
            "",
            *capability_lines,
            "",
            "These are source-candidate settings, not an observation of a live installation.",
            "",
        ]
    )
    return text.encode("utf-8")


def render_starters(starters: dict[str, Any]) -> bytes:
    lines = ["# Conversation Starters", ""]
    for index, value in enumerate(starters["starters"], 1):
        lines.extend((f"## {index}", "", value, ""))
    return "\n".join(lines).encode("utf-8")


def source_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for relative in SOURCE_MEMBERS:
        data = (SOURCE_ROOT / PurePosixPath(relative)).read_bytes()
        records.append(file_record(f"gpt-v0.4/source/{relative}", data))
    return sorted(records, key=lambda item: item["path"])


def evaluation_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for relative in EVAL_MEMBERS:
        data = (EVAL_ROOT / PurePosixPath(relative)).read_bytes()
        records.append(file_record(f"gpt-v0.4/evals/{relative}", data))
    return sorted(records, key=lambda item: item["path"])


def build_product_payload(
    profile: dict[str, Any],
    metadata: dict[str, Any],
    starters: dict[str, Any],
    catalog: dict[str, Any],
) -> dict[str, bytes]:
    instructions = (SOURCE_ROOT / "instructions.md").read_bytes()
    product: dict[str, bytes] = {
        "GPT_INSTRUCTIONS.md": instructions,
        "GPT_PUBLIC_METADATA.md": render_metadata(metadata, profile),
        "GPT_CONVERSATION_STARTERS.md": render_starters(starters),
        "knowledge/BSC_CORE_GUIDE.md": (SOURCE_ROOT / "knowledge" / "01-core-guide.md").read_bytes(),
        "knowledge/BSC_CHECKS_CATALOG.md": render_catalog(catalog),
        "knowledge/BSC_EXAMPLES.md": (SOURCE_ROOT / "knowledge" / "03-worked-examples.md").read_bytes(),
        "knowledge/BSC_JAPANESE_GLOSSARY.md": (SOURCE_ROOT / "knowledge" / "04-japanese-glossary.md").read_bytes(),
    }
    instruction_record = file_record("GPT_INSTRUCTIONS.md", instructions)
    knowledge_records = [file_record(path, product[path]) for path in KNOWLEDGE_UPLOADS]
    metadata_record = file_record("GPT_PUBLIC_METADATA.md", product["GPT_PUBLIC_METADATA.md"])
    starter_record = file_record("GPT_CONVERSATION_STARTERS.md", product["GPT_CONVERSATION_STARTERS.md"])
    lock = {
        "schema": "bsc-claim-auditor-product-lock/v1",
        "product_version": profile["product_version"],
        "candidate_id": profile["candidate_id"],
        "model_recommendation": profile["model_recommendation"],
        "capabilities": profile["capabilities"],
        "apps_state": "disabled",
        "actions_state": "disabled",
        "dependencies": profile["dependencies"],
        "instructions": instruction_record,
        "knowledge_upload_order": knowledge_records,
        "public_metadata": {
            "fields": metadata,
            "file": metadata_record,
        },
        "conversation_starters": {
            "values": starters["starters"],
            "file": starter_record,
        },
        "model_facing_files": [file_record(path, product[path]) for path in MODEL_FACING_MEMBERS],
        "source_files": source_records(),
        "builder": {
            "path": "scripts/build_gpt_v04.py",
            "bytes": BUILDER_PATH.stat().st_size,
            "sha256": sha256_bytes(BUILDER_PATH.read_bytes()),
        },
        "live_binding_state": "NON_ADMISSIBLE_UNHASHABLE",
        "binding_scope": "This lock identifies reproducible source and upload bytes, not opaque indexed service bytes.",
        "excluded_from_product_identity": [
            "generated README and setup guidance",
            "evaluation definitions and status",
            "SHA256SUMS",
            "final Git commit identity",
            "current service or deployment observations",
        ],
    }
    product["GPT_PRODUCT_LOCK.json"] = canonical_json(lock)
    return product


def render_readme(profile: dict[str, Any], *, evaluation_state: str) -> bytes:
    return (
        "# BSC Claim Auditor v0.4.0-preview.1\n\n"
        "This directory is deterministic generated upload material for the local source candidate "
        f"`{profile['candidate_id']}`. Its evaluation source state is `{evaluation_state}`.\n\n"
        "It is not validated, certified, installed, released, published, production-ready, generally reliable, "
        "or authorized for deployment. `GPT_PRODUCT_LOCK.json` binds the reproducible model-facing bytes and "
        "settings. It does not identify opaque indexed service bytes, whose binding remains "
        "`NON_ADMISSIBLE_UNHASHABLE`.\n\n"
        "Authored product source is under `../source`; authored evaluation definitions are under `../evals`. "
        "Generated files must not be edited by hand.\n"
    ).encode("utf-8")


def render_setup(profile: dict[str, Any], metadata: dict[str, Any]) -> bytes:
    lines = [
        "# Local Candidate Setup Boundary",
        "",
        f"Candidate: `{profile['candidate_id']}`",
        "",
        "This file describes reproducible upload material. It is not authority to create, update, install, share, or publish a GPT.",
        "",
        "For a separately authorized future editor operation:",
        "",
        f"1. Use the Name, Description, and category recommendation in `GPT_PUBLIC_METADATA.md` (`{metadata['name']}`).",
        "2. Paste all of `GPT_INSTRUCTIONS.md`.",
        "3. Upload exactly these four Knowledge files in order:",
    ]
    lines.extend(f"   {index}. `{path.split('/')[-1]}`" for index, path in enumerate(KNOWLEDGE_UPLOADS, 1))
    lines.extend(
        [
            "4. Enable Web Search and Code Interpreter/Data Analysis. Leave Image Generation, Apps, Actions, and Canvas disabled.",
            "5. Add the four exact starters from `GPT_CONVERSATION_STARTERS.md`.",
            "6. Freeze editor-visible settings before any fresh behavioral evaluation.",
            "",
            "Do not infer installation, validation, live binding, release, publication, or deployment authority from these files. Uploads to a Custom GPT are not local-only. Data Analysis may create a safe user-requested in-chat artifact; disabled Apps and Actions provide no external export path.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def render_evaluation_status(
    status: dict[str, Any],
    canaries: dict[str, Any],
    development: dict[str, Any],
    *,
    product_lock_sha256: str,
) -> bytes:
    records = evaluation_records()
    identity_basis = {
        "evaluator_profile_id": status["evaluator_profile_id"],
        "protocol_id": canaries["protocol_id"],
        "source_files": records,
    }
    evaluator_sha = sha256_bytes(canonical_json(identity_basis))
    cases = [
        {
            "id": item["id"],
            "status": item["status"],
        }
        for item in canaries["cases"]
    ]
    document = {
        "schema": "bsc-claim-auditor-evaluation-status/v1",
        "product_lock_sha256": product_lock_sha256,
        "evaluator_identity": {
            "profile_id": status["evaluator_profile_id"],
            "protocol_id": canaries["protocol_id"],
            "sha256": evaluator_sha,
            "source_files": records,
        },
        "candidate_state": status["candidate_state"],
        "prospective_behavioral_cases": {
            "count": status["prospective_case_count"],
            "status": status["prospective_case_status"],
            "cases": cases,
        },
        "evidence_transfer": status["evidence_transfer"],
        "historical_development_evidence": development["campaigns"],
        "historical_limits": development["limits"],
        "live_binding_state": status["live_binding_state"],
        "installation_state": status["installation_state"],
        "release_state": status["release_state"],
        "publication_state": status["publication_state"],
        "claims_not_supported": status["claims_not_supported"],
        "statement": "Candidate source is locally frozen only; no live behavioral case was run in this task.",
    }
    return canonical_json(document)


def build_payload(*, allow_draft_evaluation: bool = False) -> dict[str, bytes]:
    validate_source_closure()
    validate_active_authorities()
    profile = read_json(PROFILE_PATH, label="profile.json")
    metadata = read_json(METADATA_PATH, label="public_metadata.json")
    starters = read_json(STARTERS_PATH, label="conversation_starters.json")
    catalog = read_json(CATALOG_PATH, label="checks_catalog.json")
    development = read_json(EVAL_ROOT / "development-regressions.json", label="development-regressions.json")
    status = read_json(EVAL_ROOT / "evaluation-status.json", label="evaluation-status.json")
    canaries = read_json(EVAL_ROOT / "prospective-canaries.json", label="prospective-canaries.json")
    calibration = read_json(EVAL_ROOT / "evaluator-calibration.json", label="evaluator-calibration.json")
    hard_gate_data, hard_gate_text = read_text_bytes(EVAL_ROOT / "hard-gates.md", label="hard-gates.md")

    validate_profile(profile)
    validate_engine_dependencies(profile)
    validate_metadata(metadata)
    validate_starters(starters)
    validate_catalog(catalog)
    instruction_data, instruction_text = read_text_bytes(SOURCE_ROOT / "instructions.md", label="instructions.md")
    validate_instructions(instruction_text, profile)
    stub = (SOURCE_ROOT / "knowledge" / "02-checks-catalog.md").read_text(encoding="utf-8")
    if stub != "# BSC Implemented Checks Catalog\n\nThis file is generated from `checks_catalog.json`. Do not edit it by hand.\n":
        raise BuildError("authored checks-catalog projection stub contains a second semantic authority")
    for relative in SOURCE_MEMBERS:
        data = (SOURCE_ROOT / PurePosixPath(relative)).read_bytes()
        scan_private_material(f"source/{relative}", data)
        if relative.endswith(".md"):
            read_text_bytes(SOURCE_ROOT / PurePosixPath(relative), label=f"source/{relative}")
    for relative in EVAL_MEMBERS:
        data = (EVAL_ROOT / PurePosixPath(relative)).read_bytes()
        scan_private_material(f"evals/{relative}", data)
    knowledge_text = "\n".join(
        (SOURCE_ROOT / PurePosixPath(relative)).read_text(encoding="utf-8")
        for relative in SOURCE_MEMBERS
        if relative.startswith("knowledge/")
    )
    for token in ("service_availability=", "preview_validation_state", "public_url=", "updated link-access"):
        if token.lower() in knowledge_text.lower():
            raise BuildError("mutable current-service status appears in immutable Knowledge")
    hard_gate_ids(hard_gate_text)
    validate_development_regressions(development)
    validate_evaluation_status(status, allow_draft=allow_draft_evaluation)

    product = build_product_payload(profile, metadata, starters, catalog)
    product_lock_sha = sha256_bytes(product["GPT_PRODUCT_LOCK.json"])
    validate_canaries(
        canaries,
        product_lock_sha256=product_lock_sha,
        allow_draft=allow_draft_evaluation,
    )
    validate_calibration(
        calibration,
        product_lock_sha256=product_lock_sha,
        allow_draft=allow_draft_evaluation,
    )
    if not allow_draft_evaluation:
        model_source = b"\n".join(
            (SOURCE_ROOT / PurePosixPath(relative)).read_bytes()
            for relative in SOURCE_MEMBERS
        )
        for case in canaries["cases"]:
            prompt = case["prompt"].encode("utf-8")
            if prompt in model_source:
                raise BuildError("prospective prompt appears verbatim in model-facing source")

    payload = dict(product)
    payload["README.md"] = render_readme(profile, evaluation_state=canaries["state"])
    payload["GPT_SETUP.md"] = render_setup(profile, metadata)
    payload["GPT_EVALUATION_STATUS.json"] = render_evaluation_status(
        status,
        canaries,
        development,
        product_lock_sha256=product_lock_sha,
    )
    checksum_lines = [
        f"{sha256_bytes(data)}  {path}\n"
        for path, data in sorted(payload.items())
        if path != "SHA256SUMS"
    ]
    payload["SHA256SUMS"] = "".join(checksum_lines).encode("utf-8")
    validate_payload(payload)
    return payload


def validate_payload(payload: dict[str, bytes]) -> None:
    validate_path_roster(DIST_MEMBERS, label="dist roster")
    if set(payload) != set(DIST_MEMBERS):
        raise BuildError(
            f"generated dist closure differs; missing={sorted(set(DIST_MEMBERS) - set(payload))}; "
            f"extra={sorted(set(payload) - set(DIST_MEMBERS))}"
        )
    for path, data in payload.items():
        scan_private_material(f"dist/{path}", data)
        if path.endswith((".md", ".json", "SHA256SUMS")):
            if b"\r" in data or not data.endswith(b"\n"):
                raise BuildError(f"dist/{path}: generated text must be LF-only with terminal LF")
    instructions = payload["GPT_INSTRUCTIONS.md"].decode("utf-8")
    if len(instructions) > 4500:
        raise BuildError("generated Instructions exceed hard maximum")
    lock = strict_json_bytes(payload["GPT_PRODUCT_LOCK.json"], label="GPT_PRODUCT_LOCK.json")
    if not isinstance(lock, dict) or lock.get("live_binding_state") != "NON_ADMISSIBLE_UNHASHABLE":
        raise BuildError("product lock live-binding boundary changed")
    if lock.get("model_facing_files") != [file_record(path, payload[path]) for path in MODEL_FACING_MEMBERS]:
        raise BuildError("product lock model-facing ledger is incomplete")
    checksums = payload["SHA256SUMS"].decode("utf-8").splitlines()
    expected_paths = sorted(path for path in payload if path != "SHA256SUMS")
    observed_paths: list[str] = []
    for line in checksums:
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_./-]+)", line)
        if not match:
            raise BuildError("SHA256SUMS contains a malformed line")
        digest, path = match.groups()
        if path == "SHA256SUMS" or path not in payload or digest != sha256_bytes(payload[path]):
            raise BuildError("SHA256SUMS contains a self, unknown, or mismatched entry")
        observed_paths.append(path)
    if observed_paths != expected_paths or len(observed_paths) != len(set(observed_paths)):
        raise BuildError("SHA256SUMS membership differs from dist closure")


def _absolute_without_resolution(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _assert_no_reparse_components(path: Path, *, label: str) -> Path:
    absolute = _absolute_without_resolution(path)
    current = Path(absolute.anchor)
    parts = absolute.parts[1:] if absolute.anchor else absolute.parts
    for part in parts:
        current /= part
        try:
            current.lstat()
        except FileNotFoundError:
            break
        except OSError as exc:
            raise BuildError(f"cannot inspect {label} component: {current}") from exc
        if _is_reparse_or_symlink(current):
            raise BuildError(f"{label} uses a symlink/reparse component: {current}")
    return absolute


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _assert_safe_output(output: Path) -> Path:
    absolute = _assert_no_reparse_components(output, label="output path")
    root = _absolute_without_resolution(ROOT)
    canonical = _absolute_without_resolution(DIST_ROOT)
    if _is_within(absolute, root) and absolute != canonical:
        raise BuildError("repository-local generated output must be the canonical gpt-v0.4/dist directory")
    if absolute == Path(absolute.anchor):
        raise BuildError(f"unsafe output directory: {absolute}")
    return absolute


def _assert_safe_archive_destination(destination: Path, *, require_existing: bool) -> Path:
    absolute = _assert_no_reparse_components(destination, label="archive path")
    if absolute.suffix.casefold() != ".zip":
        raise BuildError("archive target must use a .zip extension")
    root = _absolute_without_resolution(ROOT)
    canonical = _absolute_without_resolution(CANONICAL_ARCHIVE_PATH)
    if _is_within(absolute, root) and absolute != canonical:
        raise BuildError("repository-local archive target must be the canonical v0.4 archive path")
    if require_existing and not absolute.is_file():
        raise BuildError("archive to verify is missing or not a regular file")
    if absolute.exists() and not absolute.is_file():
        raise BuildError("archive target is not a regular file")
    return absolute


def _validate_output_closure(output: Path, *, allow_missing: bool) -> dict[str, bytes]:
    if not output.exists():
        if allow_missing:
            return {}
        raise BuildError(f"generated output directory is missing: {output}")
    if _is_reparse_or_symlink(output) or not output.is_dir():
        raise BuildError("output root must be a regular directory, not a symlink/reparse point")
    files: dict[str, bytes] = {}
    directories: set[str] = set()
    for path in output.rglob("*"):
        if _is_reparse_or_symlink(path):
            raise BuildError(f"output contains symlink/reparse point: {path}")
        relative = path.relative_to(output).as_posix()
        if path.is_dir():
            directories.add(relative)
        elif path.is_file():
            files[relative] = path.read_bytes()
        else:
            raise BuildError(f"output contains a non-regular member: {relative}")
    if directories - {"knowledge"}:
        raise BuildError(f"output contains undeclared directories: {sorted(directories - {'knowledge'})}")
    if set(files) - set(DIST_MEMBERS):
        raise BuildError(f"output contains undeclared files: {sorted(set(files) - set(DIST_MEMBERS))}")
    return files


def _atomic_write(path: Path, data: bytes) -> None:
    if path.exists() and (_is_reparse_or_symlink(path) or not path.is_file()):
        raise BuildError(f"refusing to overwrite non-regular generated target: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if _is_reparse_or_symlink(path.parent):
        raise BuildError(f"generated parent is a symlink/reparse point: {path.parent}")
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_output(output: Path, payload: dict[str, bytes]) -> None:
    output = _assert_safe_output(output)
    _validate_output_closure(output, allow_missing=True)
    output.mkdir(parents=True, exist_ok=True)
    for relative in sorted(payload):
        _atomic_write(output / PurePosixPath(relative), payload[relative])
    observed = _validate_output_closure(output, allow_missing=False)
    if observed != payload:
        raise BuildError("generated output does not match terminal payload bytes")


def check_output(output: Path, payload: dict[str, bytes]) -> None:
    output = _assert_safe_output(output)
    observed = _validate_output_closure(output, allow_missing=False)
    if set(observed) != set(payload):
        raise BuildError(
            f"generated output closure is stale; missing={sorted(set(payload) - set(observed))}; "
            f"extra={sorted(set(observed) - set(payload))}"
        )
    stale = sorted(path for path in payload if observed[path] != payload[path])
    if stale:
        raise BuildError(f"generated output bytes are stale: {stale}")


def archive_member_names(payload: dict[str, bytes]) -> tuple[str, ...]:
    return tuple(f"{ARCHIVE_ROOT}/{path}" for path in sorted(payload))


def write_archive(destination: Path, payload: dict[str, bytes]) -> Path:
    destination = _assert_safe_archive_destination(destination, require_existing=False)
    destination.parent.mkdir(parents=True, exist_ok=True)
    _assert_no_reparse_components(destination.parent, label="archive parent")
    handle, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED, strict_timestamps=True) as archive:
            archive.comment = b""
            for relative in sorted(payload):
                name = f"{ARCHIVE_ROOT}/{relative}"
                if not safe_member_name(name):
                    raise BuildError(f"unsafe archive member: {name}")
                info = zipfile.ZipInfo(name, date_time=ARCHIVE_TIMESTAMP)
                info.compress_type = zipfile.ZIP_STORED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.extra = b""
                info.comment = b""
                archive.writestr(info, payload[relative])
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    verify_archive(destination, payload)
    return destination


def verify_archive(path: Path, payload: dict[str, bytes]) -> None:
    try:
        with zipfile.ZipFile(path, "r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            expected_names = list(archive_member_names(payload))
            if names != expected_names or len(names) != len(set(names)):
                raise BuildError("archive member order, closure, or uniqueness differs")
            if archive.comment:
                raise BuildError("archive comment must be empty")
            for info in infos:
                if not safe_member_name(info.filename) or info.is_dir():
                    raise BuildError("archive contains an unsafe or directory member")
                relative = info.filename.removeprefix(f"{ARCHIVE_ROOT}/")
                if relative not in payload:
                    raise BuildError("archive member escapes declared root/closure")
                unix_mode = info.external_attr >> 16
                if stat.S_ISLNK(unix_mode):
                    raise BuildError("archive contains a symlink member")
                if info.compress_type != zipfile.ZIP_STORED or info.date_time != ARCHIVE_TIMESTAMP:
                    raise BuildError("archive compression or timestamp is nondeterministic")
                if info.create_system != 3 or unix_mode != 0o100644 or info.extra or info.comment:
                    raise BuildError("archive member metadata differs from deterministic contract")
                data = archive.read(info)
                if data != payload[relative] or info.file_size != len(data):
                    raise BuildError("archive member bytes or size differ")
                if info.CRC != binascii.crc32(data) & 0xFFFFFFFF:
                    raise BuildError("archive member CRC differs")
                scan_private_material(f"archive/{relative}", data)
    except (OSError, zipfile.BadZipFile) as exc:
        raise BuildError("archive is unreadable") from exc


def product_lock_sha256(payload: dict[str, bytes]) -> str:
    return sha256_bytes(payload["GPT_PRODUCT_LOCK.json"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DIST_ROOT)
    parser.add_argument("--check", action="store_true", help="verify generated dist without writing")
    parser.add_argument("--archive", type=Path, help="also write a deterministic ZIP_STORED archive")
    parser.add_argument(
        "--allow-draft-evaluation",
        action="store_true",
        help="pre-freeze product-only build; forbidden for final candidate verification",
    )
    parser.add_argument("--print-product-lock", action="store_true")
    args = parser.parse_args(argv)
    try:
        payload = build_payload(allow_draft_evaluation=args.allow_draft_evaluation)
        if args.check:
            check_output(args.output, payload)
        else:
            write_output(args.output, payload)
        archive_sha: str | None = None
        if args.archive is not None:
            if args.check:
                archive = _assert_safe_archive_destination(args.archive, require_existing=True)
                verify_archive(archive, payload)
            else:
                archive = write_archive(args.archive, payload)
            archive_sha = sha256_bytes(archive.read_bytes())
        summary = {
            "status": "pass",
            "operation": "check" if args.check else "build",
            "product_version": "0.4.0-preview.1",
            "candidate_id": "bsc-claim-auditor-v0.4.0-preview.1",
            "product_lock_sha256": product_lock_sha256(payload),
            "dist_member_count": len(payload),
            "archive_sha256": archive_sha,
            "draft_evaluation_allowed": bool(args.allow_draft_evaluation),
        }
        if args.print_product_lock:
            print(summary["product_lock_sha256"])
        else:
            print(canonical_json(summary).decode("utf-8"), end="")
        return 0
    except BuildError as exc:
        print(
            canonical_json(
                {
                    "status": "blocked",
                    "operation": "check" if args.check else "build",
                    "error": str(exc),
                }
            ).decode("utf-8"),
            end="",
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
