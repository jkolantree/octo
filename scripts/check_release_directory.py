#!/usr/bin/env python3
"""Verify a closed release directory before attestation or publication."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
from pathlib import Path
from typing import Any


HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")
PORTABLE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*")
MANIFEST_NAME = "RELEASE_MANIFEST.json"
CHECKSUM_NAME = "SHA256SUMS"
CONTROL_BYTES = {chr(value) for value in range(32)} - {"\t", "\n", "\r"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key {key!r}")
        value[key] = item
    return value


def load_strict_json(path: Path) -> object:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=strict_object,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON number {value!r}")
        ),
    )


def portable_basename(name: object) -> bool:
    return (
        isinstance(name, str)
        and PORTABLE_NAME.fullmatch(name) is not None
        and "/" not in name
        and "\\" not in name
        and name not in {".", ".."}
    )


def _identity_error(label: str, actual: object, expected: str) -> str | None:
    if actual != expected:
        return f"manifest {label} differs: expected {expected!r}, found {actual!r}"
    return None


def verify_release_directory(
    directory: Path,
    *,
    commit: str,
    tree: str,
    tag: str,
    expected_count: int | None = None,
) -> list[str]:
    """Return fail-closed release-directory findings."""

    failures: list[str] = []
    root = directory.resolve()

    if HEX40.fullmatch(commit) is None:
        failures.append("expected commit must be 40 lowercase hexadecimal characters")
    if HEX40.fullmatch(tree) is None:
        failures.append("expected tree must be 40 lowercase hexadecimal characters")
    if not portable_basename(tag):
        failures.append("expected tag is not a portable Git tag literal")
    if expected_count is not None and expected_count < 1:
        failures.append("expected file count must be positive")
    if failures:
        return failures

    if not directory.exists() or not directory.is_dir() or directory.is_symlink():
        return [f"release directory is missing, not a directory, or a symlink: {directory}"]

    actual: dict[str, Path] = {}
    folded_names: dict[str, str] = {}
    for entry in sorted(directory.iterdir(), key=lambda path: path.name.encode("utf-8")):
        try:
            mode = entry.lstat().st_mode
        except OSError as exc:
            failures.append(f"release entry cannot be inspected: {entry.name}: {exc}")
            continue
        if entry.is_symlink() or not stat.S_ISREG(mode):
            failures.append(f"release directory contains a non-regular file: {entry.name}")
            continue
        if not portable_basename(entry.name):
            failures.append(f"release filename is not a portable basename: {entry.name!r}")
            continue
        folded = entry.name.casefold()
        if folded in folded_names:
            failures.append(
                "release filenames collide under case folding: "
                f"{folded_names[folded]!r} and {entry.name!r}"
            )
            continue
        folded_names[folded] = entry.name
        actual[entry.name] = entry

    if expected_count is not None and len(actual) != expected_count:
        failures.append(
            f"release file count differs: expected {expected_count}, found {len(actual)}"
        )

    manifest_path = actual.get(MANIFEST_NAME)
    checksum_path = actual.get(CHECKSUM_NAME)
    if manifest_path is None:
        failures.append(f"release directory is missing {MANIFEST_NAME}")
    if checksum_path is None:
        failures.append(f"release directory is missing {CHECKSUM_NAME}")
    if manifest_path is None or checksum_path is None:
        return failures

    try:
        manifest = load_strict_json(manifest_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        failures.append(f"{MANIFEST_NAME} is not strict UTF-8 JSON: {exc}")
        return failures
    if not isinstance(manifest, dict):
        failures.append(f"{MANIFEST_NAME} must contain one JSON object")
        return failures

    for label, expected in (
        ("commit", commit),
        ("git_tree", tree),
        ("git_tag", tag),
        ("release", tag),
    ):
        finding = _identity_error(label, manifest.get(label), expected)
        if finding is not None:
            failures.append(finding)

    verification = manifest.get("verification")
    if not isinstance(verification, dict):
        failures.append("manifest verification must be an object")
    else:
        if verification.get("embedded_artifact_signatures") != "not_performed":
            failures.append(
                "manifest must state that artifact signatures are not embedded"
            )
        if (
            verification.get("keyless_release_attestations")
            != "required_before_publication"
        ):
            failures.append(
                "manifest must require keyless attestations before publication"
            )

    records = manifest.get("artifacts")
    if not isinstance(records, list):
        failures.append("manifest artifacts must be an array")
        return failures

    manifest_names: set[str] = set()
    folded_manifest_names: dict[str, str] = {}
    for index, record in enumerate(records):
        label = f"manifest artifact {index}"
        if not isinstance(record, dict) or set(record) != {"name", "bytes", "sha256"}:
            failures.append(
                f"{label} must contain exactly name, bytes, and sha256"
            )
            continue
        name = record.get("name")
        size = record.get("bytes")
        digest = record.get("sha256")
        if not portable_basename(name):
            failures.append(f"{label} name is not a portable basename: {name!r}")
            continue
        assert isinstance(name, str)
        folded = name.casefold()
        if name in manifest_names or folded in folded_manifest_names:
            failures.append(f"manifest contains a duplicate artifact name: {name!r}")
            continue
        manifest_names.add(name)
        folded_manifest_names[folded] = name
        if name in {MANIFEST_NAME, CHECKSUM_NAME}:
            failures.append(
                f"manifest artifact roster must exclude cyclic file {name}"
            )
        if type(size) is not int or size < 0:
            failures.append(f"{label} bytes must be a nonnegative integer")
        if not isinstance(digest, str) or HEX64.fullmatch(digest) is None:
            failures.append(
                f"{label} sha256 must be 64 lowercase hexadecimal characters"
            )
        path = actual.get(name)
        if path is None:
            failures.append(f"manifest artifact is missing from release directory: {name}")
            continue
        if type(size) is int and path.stat().st_size != size:
            failures.append(
                f"artifact size differs for {name}: expected {size}, "
                f"found {path.stat().st_size}"
            )
        if isinstance(digest, str) and HEX64.fullmatch(digest) is not None:
            observed = sha256(path)
            if observed != digest:
                failures.append(
                    f"artifact digest differs for {name}: expected {digest}, "
                    f"found {observed}"
                )

    expected_names = manifest_names | {MANIFEST_NAME, CHECKSUM_NAME}
    actual_names = set(actual)
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        extra = sorted(actual_names - expected_names)
        failures.append(
            f"release roster differs: missing={missing!r}, extra={extra!r}"
        )
    if expected_count is not None and len(expected_names) != expected_count:
        failures.append(
            "manifest-derived file count differs: "
            f"expected {expected_count}, found {len(expected_names)}"
        )

    try:
        checksum_text = checksum_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        failures.append(f"{CHECKSUM_NAME} is not strict UTF-8 text: {exc}")
        return failures
    if not checksum_text or not checksum_text.endswith("\n"):
        failures.append(f"{CHECKSUM_NAME} must be nonempty and newline-terminated")
    if any(character in checksum_text for character in CONTROL_BYTES):
        failures.append(f"{CHECKSUM_NAME} contains a forbidden control character")

    checksum_records: dict[str, str] = {}
    folded_checksum_names: dict[str, str] = {}
    for number, line in enumerate(checksum_text.splitlines(), start=1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9._+-]*)", line)
        if match is None:
            failures.append(f"{CHECKSUM_NAME} line {number} is malformed")
            continue
        digest, name = match.groups()
        if not portable_basename(name):
            failures.append(
                f"{CHECKSUM_NAME} line {number} has a non-portable name"
            )
            continue
        folded = name.casefold()
        if name in checksum_records or folded in folded_checksum_names:
            failures.append(f"{CHECKSUM_NAME} contains duplicate name {name!r}")
            continue
        checksum_records[name] = digest
        folded_checksum_names[folded] = name

    expected_checksum_names = manifest_names | {MANIFEST_NAME}
    if set(checksum_records) != expected_checksum_names:
        missing = sorted(expected_checksum_names - set(checksum_records))
        extra = sorted(set(checksum_records) - expected_checksum_names)
        failures.append(
            f"checksum roster differs: missing={missing!r}, extra={extra!r}"
        )
    if CHECKSUM_NAME in checksum_records:
        failures.append(f"{CHECKSUM_NAME} must not contain a cyclic self-digest")

    for name, expected_digest in checksum_records.items():
        path = actual.get(name)
        if path is None:
            failures.append(f"checksum target is missing: {name}")
            continue
        observed = sha256(path)
        if observed != expected_digest:
            failures.append(
                f"checksum digest differs for {name}: expected {expected_digest}, "
                f"found {observed}"
            )

    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--tree", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--expected-count", type=int)
    args = parser.parse_args(argv)

    failures = verify_release_directory(
        args.directory,
        commit=args.commit,
        tree=args.tree,
        tag=args.tag,
        expected_count=args.expected_count,
    )
    if failures:
        for failure in failures:
            print(f"release directory check failed: {failure}")
        return 1
    count = len(list(args.directory.iterdir()))
    print(
        "release directory checks passed: "
        f"{count} files, commit={args.commit}, tree={args.tree}, tag={args.tag}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
