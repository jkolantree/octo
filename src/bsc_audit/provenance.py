from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


HASH_PREFIX = "sha256:"
ZERO_SHA256 = HASH_PREFIX + "0" * 64
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_json(value: Any) -> str:
    return HASH_PREFIX + hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return HASH_PREFIX + hashlib.sha256(value).hexdigest()


def is_sha256(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith(HASH_PREFIX):
        return False
    digest = value[len(HASH_PREFIX) :]
    return len(digest) == 64 and all(character in "0123456789abcdef" for character in digest)


def is_placeholder_sha256(value: object) -> bool:
    return value == ZERO_SHA256


def resolve_local_artifact(root: Path, relative_path: object) -> Path:
    """Resolve a declared artifact without allowing absolute or escaping paths."""

    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ValueError("artifact path must be a nonempty relative string")
    if "\\" in relative_path:
        raise ValueError("artifact paths must use portable forward-slash separators")
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("artifact path must remain below the manifest directory")
    resolved_root = root.resolve()
    candidate = (resolved_root / relative).resolve()
    if not candidate.is_relative_to(resolved_root):
        raise ValueError("artifact path escapes the manifest directory")
    return candidate


def verify_local_artifact(
    root: Path | None,
    relative_path: object,
    expected_hash: object,
    *,
    max_bytes: int = MAX_ARTIFACT_BYTES,
) -> tuple[bool, str, str | None]:
    """Verify an artifact and return ``(ok, reason, actual_hash)``.

    A missing root is deliberately unresolved rather than implicitly trusted.
    """

    if not is_sha256(expected_hash):
        return False, "invalid_hash", None
    if is_placeholder_sha256(expected_hash):
        return False, "placeholder_hash", None
    if root is None:
        return False, "artifact_root_unavailable", None
    try:
        candidate = resolve_local_artifact(root, relative_path)
    except (ValueError, OSError, RuntimeError):
        return False, "unsafe_path", None
    if not candidate.is_file():
        return False, "missing_artifact", None
    try:
        size = candidate.stat().st_size
    except OSError:
        return False, "unreadable_artifact", None
    if size > max_bytes:
        return False, "artifact_too_large", None
    try:
        digest = hashlib.sha256()
        with candidate.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
    except OSError:
        return False, "unreadable_artifact", None
    actual = HASH_PREFIX + digest.hexdigest()
    if actual != expected_hash:
        return False, "hash_mismatch", actual
    return True, "verified", actual
