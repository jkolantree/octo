#!/usr/bin/env python3
"""Fail closed when a localized document drifts from its canonical source."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_RELATIVE = PurePosixPath("docs/ja/TRANSLATION_MANIFEST.json")
MANIFEST_SCHEMA = "bsc-localization-manifest/v2"
HASH_POLICY = "sha256_raw_file_bytes_no_normalization"
VERIFICATION_SCOPE = "exact_byte_binding_and_staleness_only_not_translation_quality"
MAX_MANIFEST_BYTES = 1_048_576
JAPANESE_BETA_MARKER = "**日本語ベータ版**"
JAPANESE_BETA_TEXT = "日本語ベータ版"
REVIEW_PENDING_MARKER = "母語話者による用語レビューは未完了"

REQUIRED_PAIRS = {
    ("README.md", "README.ja.md"),
    ("START_HERE.md", "START_HERE.ja.md"),
    ("docs/index.md", "docs/ja/index.md"),
    ("docs/STATUS_MODEL.md", "docs/ja/STATUS_MODEL.md"),
    ("docs/AUDIT_RETURN_DESK.md", "docs/ja/AUDIT_RETURN_DESK.md"),
    ("docs/CUSTOM_GPT_STATUS.md", "docs/ja/CUSTOM_GPT_STATUS.md"),
    ("pages/index.html", "pages/ja.html"),
    ("pages/locale-en.js", "pages/locale-ja.js"),
}
REQUIRED_SUPPLEMENTS = {
    "docs/ja/GLOSSARY.md": "japanese_machine_token_glossary",
    "docs/ja/GPT_INTERFACE.md": "japanese_custom_gpt_usage_guide",
}

TOP_LEVEL_KEYS = {
    "manifest_schema",
    "locale",
    "canonical_language",
    "translation_status",
    "native_speaker_terminology_review",
    "hash_policy",
    "verification_scope",
    "entries",
    "supplements",
    "manifest_payload_sha256",
}
ENTRY_KEYS = {"source", "source_sha256", "target", "target_sha256"}
SUPPLEMENT_KEYS = {"path", "sha256", "role"}
SHA256_RE = re.compile(r"[0-9a-f]{64}")


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _load_strict_json(data: bytes) -> dict[str, Any]:
    try:
        text = data.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=lambda item: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON value: {item}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"manifest is not strict UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("manifest root must be a JSON object")
    return value


def sha256_bytes(data: bytes) -> str:
    """Hash exact bytes; never decode, normalize, transliterate, or change newlines."""

    return hashlib.sha256(data).hexdigest()


def manifest_payload_sha256(manifest: dict[str, Any]) -> str:
    """Bind the logical manifest while excluding its self-hash field."""

    payload = dict(manifest)
    payload.pop("manifest_payload_sha256", None)
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256_bytes(canonical)


def _portable_path(raw: object, *, field: str) -> PurePosixPath:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        raise ValueError(f"{field} must be a non-empty portable repository path")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} or ":" in part for part in path.parts):
        raise ValueError(f"{field} is unsafe: {raw!r}")
    return path


def _regular_repository_file(root: Path, relative: PurePosixPath, *, field: str) -> Path:
    candidate = root
    for part in relative.parts:
        candidate /= part
        try:
            info = candidate.lstat()
        except OSError as exc:
            raise ValueError(f"{field} is missing: {relative.as_posix()}") from exc
        attributes = getattr(info, "st_file_attributes", 0)
        is_reparse = bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
        if candidate.is_symlink() or is_reparse:
            raise ValueError(f"{field} traverses a link or reparse point: {relative.as_posix()}")
    try:
        resolved_root = root.resolve(strict=True)
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise ValueError(f"{field} escapes the repository: {relative.as_posix()}") from exc
    if not resolved.is_file():
        raise ValueError(f"{field} is not a regular file: {relative.as_posix()}")
    return resolved


def validate_localization(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    root = root.resolve()
    try:
        manifest_path = _regular_repository_file(
            root, MANIFEST_RELATIVE, field="translation manifest"
        )
        raw_manifest = manifest_path.read_bytes()
    except (OSError, ValueError) as exc:
        return [f"translation manifest is missing: {exc}"]
    if len(raw_manifest) > MAX_MANIFEST_BYTES:
        return [f"translation manifest exceeds {MAX_MANIFEST_BYTES} bytes"]
    try:
        manifest = _load_strict_json(raw_manifest)
    except ValueError as exc:
        return [str(exc)]

    if set(manifest) != TOP_LEVEL_KEYS:
        failures.append("translation manifest top-level contract differs from the reviewed schema")
    expected_metadata = {
        "manifest_schema": MANIFEST_SCHEMA,
        "locale": "ja",
        "canonical_language": "en",
        "translation_status": "beta",
        "native_speaker_terminology_review": "pending",
        "hash_policy": HASH_POLICY,
        "verification_scope": VERIFICATION_SCOPE,
    }
    for key, expected in expected_metadata.items():
        if manifest.get(key) != expected:
            failures.append(f"translation manifest {key} must equal {expected!r}")

    claimed_payload_hash = manifest.get("manifest_payload_sha256")
    if not isinstance(claimed_payload_hash, str) or not SHA256_RE.fullmatch(claimed_payload_hash):
        failures.append("manifest_payload_sha256 must be a lowercase SHA-256 digest")
    elif claimed_payload_hash != manifest_payload_sha256(manifest):
        failures.append("translation manifest payload hash is stale")

    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        failures.append("translation manifest entries must be a non-empty array")
        return sorted(set(failures))

    sources: set[str] = set()
    targets: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    observed_target_order: list[str] = []
    for index, entry in enumerate(entries):
        prefix = f"entries[{index}]"
        if not isinstance(entry, dict):
            failures.append(f"{prefix} must be an object")
            continue
        if set(entry) != ENTRY_KEYS:
            failures.append(f"{prefix} contract differs from the reviewed schema")
        try:
            source = _portable_path(entry.get("source"), field=f"{prefix}.source")
            target = _portable_path(entry.get("target"), field=f"{prefix}.target")
        except ValueError as exc:
            failures.append(str(exc))
            continue
        source_name = source.as_posix()
        target_name = target.as_posix()
        observed_target_order.append(target_name)
        if source_name in sources:
            failures.append(f"duplicate canonical source: {source_name}")
        if target_name in targets:
            failures.append(f"duplicate localization target: {target_name}")
        sources.add(source_name)
        targets.add(target_name)
        pairs.add((source_name, target_name))

        if source == target or source_name.endswith(".ja.md") or source.parts[:2] == ("docs", "ja"):
            failures.append(f"canonical source is not an English-source path: {source_name}")
        allowed_target = (
            target_name
            in {
                "README.ja.md",
                "START_HERE.ja.md",
                "pages/ja.html",
                "pages/locale-ja.js",
            }
            or target.parts[:2] == ("docs", "ja")
        )
        if not allowed_target or target == MANIFEST_RELATIVE:
            failures.append(f"localization target is outside the reviewed locale paths: {target_name}")

        for hash_field in ("source_sha256", "target_sha256"):
            digest = entry.get(hash_field)
            if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
                failures.append(f"{prefix}.{hash_field} must be a lowercase SHA-256 digest")

        try:
            source_path = _regular_repository_file(root, source, field=f"{prefix}.source")
        except ValueError as exc:
            failures.append(str(exc))
        else:
            if entry.get("source_sha256") != sha256_bytes(source_path.read_bytes()):
                failures.append(f"canonical source hash is stale: {source_name}")

        try:
            target_path = _regular_repository_file(root, target, field=f"{prefix}.target")
        except ValueError as exc:
            failures.append(str(exc))
        else:
            target_bytes = target_path.read_bytes()
            if entry.get("target_sha256") != sha256_bytes(target_bytes):
                failures.append(f"localization target hash is stale: {target_name}")
            try:
                target_text = target_bytes.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                failures.append(f"localization target is not UTF-8: {target_name}")
            else:
                if target.suffix.lower() in {".md", ".html"}:
                    if JAPANESE_BETA_TEXT not in target_text:
                        failures.append(f"Japanese beta marker is missing: {target_name}")
                    if REVIEW_PENDING_MARKER not in target_text:
                        failures.append(f"native-speaker review marker is missing: {target_name}")

    if observed_target_order != sorted(observed_target_order):
        failures.append("translation manifest entries must be sorted by target path")
    for source, target in sorted(REQUIRED_PAIRS - pairs):
        failures.append(f"required translation pair is missing: {source} -> {target}")

    supplements = manifest.get("supplements")
    if not isinstance(supplements, list) or not supplements:
        failures.append("translation manifest supplements must be a non-empty array")
        return sorted(set(failures))
    observed_supplements: dict[str, str] = {}
    observed_supplement_order: list[str] = []
    for index, supplement in enumerate(supplements):
        prefix = f"supplements[{index}]"
        if not isinstance(supplement, dict):
            failures.append(f"{prefix} must be an object")
            continue
        if set(supplement) != SUPPLEMENT_KEYS:
            failures.append(f"{prefix} contract differs from the reviewed schema")
        try:
            relative = _portable_path(supplement.get("path"), field=f"{prefix}.path")
        except ValueError as exc:
            failures.append(str(exc))
            continue
        name = relative.as_posix()
        observed_supplement_order.append(name)
        if name in observed_supplements:
            failures.append(f"duplicate Japanese supplement: {name}")
        role = supplement.get("role")
        if not isinstance(role, str) or not role:
            failures.append(f"{prefix}.role must be a non-empty string")
            role = ""
        observed_supplements[name] = role
        expected_role = REQUIRED_SUPPLEMENTS.get(name)
        if expected_role is None:
            failures.append(f"unreviewed Japanese supplement path: {name}")
        elif role != expected_role:
            failures.append(f"Japanese supplement role differs from the reviewed registry: {name}")
        if name in targets:
            failures.append(f"Japanese supplement is also declared as a translation target: {name}")
        digest = supplement.get("sha256")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            failures.append(f"{prefix}.sha256 must be a lowercase SHA-256 digest")
        try:
            path = _regular_repository_file(root, relative, field=f"{prefix}.path")
        except ValueError as exc:
            failures.append(str(exc))
            continue
        data = path.read_bytes()
        if digest != sha256_bytes(data):
            failures.append(f"Japanese supplement hash is stale: {name}")
        try:
            text = data.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            failures.append(f"Japanese supplement is not UTF-8: {name}")
        else:
            if JAPANESE_BETA_TEXT not in text:
                failures.append(f"Japanese beta marker is missing: {name}")
            if REVIEW_PENDING_MARKER not in text:
                failures.append(f"native-speaker review marker is missing: {name}")
    if observed_supplement_order != sorted(observed_supplement_order):
        failures.append("translation manifest supplements must be sorted by path")
    if observed_supplements != REQUIRED_SUPPLEMENTS:
        missing = sorted(set(REQUIRED_SUPPLEMENTS) - set(observed_supplements))
        extra = sorted(set(observed_supplements) - set(REQUIRED_SUPPLEMENTS))
        failures.append(
            f"Japanese supplement inventory differs from the reviewed registry; missing={missing}; extra={extra}"
        )
    return sorted(set(failures))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root to inspect")
    args = parser.parse_args()
    failures = validate_localization(args.root)
    if failures:
        for failure in failures:
            print(f"localization check failed: {failure}", file=sys.stderr)
        return 1
    print(
        "Localization byte bindings verified: "
        f"{len(REQUIRED_PAIRS)} translation pairs and {len(REQUIRED_SUPPLEMENTS)} Japanese beta supplements; "
        "translation quality and native-speaker review are not certified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
