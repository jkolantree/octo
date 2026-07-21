#!/usr/bin/env python3
"""Fail closed on inexpensive release-integrity invariants."""

from __future__ import annotations

import json
import hashlib
import re
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bsc_audit import __version__  # noqa: E402
from check_research_packet import verify_packet  # noqa: E402


def fail(message: str) -> None:
    raise SystemExit(f"release check failed: {message}")


def strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate key {key!r}")
        value[key] = item
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_strict_json(path: Path) -> object:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=strict_object,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (json.JSONDecodeError, ValueError) as exc:
        fail(f"{path.relative_to(ROOT)} is not strict JSON: {exc}")


def main() -> int:
    if len((ROOT / "LICENSE").read_text(encoding="utf-8").splitlines()) < 150:
        fail("LICENSE is not the complete Apache-2.0 text")

    packet_failures = verify_packet()
    if packet_failures:
        fail(f"derived witnessed-descent packet failed verification: {packet_failures[0]}")

    for directory in ("examples", "templates", "schemas", "src/bsc_audit/schema_data"):
        for path in sorted((ROOT / directory).glob("*.json")):
            load_strict_json(path)
    for relative in (".zenodo.json", "research/zenodo.json", "toolchain.lock.json"):
        load_strict_json(ROOT / relative)
    privacy_policy = load_strict_json(ROOT / "privacy-policy.json")
    if not isinstance(privacy_policy, dict) or privacy_policy.get("policy_version") != "1.0.0":
        fail("privacy policy is missing or has an unsupported version")

    for schema in sorted((ROOT / "schemas").glob("*.json")):
        packaged = ROOT / "src" / "bsc_audit" / "schema_data" / schema.name
        if not packaged.is_file() or schema.read_bytes() != packaged.read_bytes():
            fail(f"packaged schema differs from {schema.relative_to(ROOT)}")

    for markdown in sorted(path for path in ROOT.rglob("*.md") if not any(part in {"build", "dist", "release"} or part.endswith(".egg-info") for part in path.relative_to(ROOT).parts)):
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", markdown.read_text(encoding="utf-8")):
            target = target.split("#", 1)[0]
            if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE):
                continue
            if not (markdown.parent / target).resolve().exists():
                fail(f"broken local link in {markdown.relative_to(ROOT)}: {target}")

    html = (ROOT / "START_HERE.html").read_text(encoding="utf-8")
    if not re.search(r"<html[^>]+lang=[\"']en(?:-US)?[\"']", html, re.IGNORECASE):
        fail("START_HERE.html must declare an English document language")
    if len(re.findall(r"<h1(?:\s|>)", html, re.IGNORECASE)) != 1:
        fail("START_HERE.html must contain exactly one h1")
    if "focus-visible" not in (ROOT / "docs" / "starter.css").read_text(encoding="utf-8"):
        fail("starter stylesheet lacks visible keyboard focus")

    digest_lines = (ROOT / "research" / "DIGESTS.sha256").read_text(encoding="utf-8").splitlines()
    declared_digests: dict[str, str] = {}
    for line in digest_lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line)
        if not match or match.group(2) in declared_digests:
            fail("research/DIGESTS.sha256 is malformed or contains duplicate names")
        declared_digests[match.group(2)] = match.group(1)
    expected_research = {"Audit_Descent_Calculus.pdf", "Audit_Descent_Calculus.docx"}
    if set(declared_digests) != expected_research:
        fail("research digest ledger must name exactly the PDF and DOCX source")
    for filename, expected in declared_digests.items():
        path = ROOT / "research" / filename
        if not path.is_file() or sha256(path) != expected:
            fail(f"research artifact is missing or differs from its declared digest: {filename}")

    research_license = (ROOT / "research" / "LICENSE").read_text(encoding="utf-8")
    if "CC-BY-4.0" not in research_license or "Creative Commons Attribution 4.0" not in research_license:
        fail("research paper must carry an explicit CC-BY-4.0 grant")
    software_zenodo = load_strict_json(ROOT / ".zenodo.json")
    paper_zenodo = load_strict_json(ROOT / "research" / "zenodo.json")
    if not isinstance(software_zenodo, dict) or software_zenodo.get("license") != "Apache-2.0":
        fail("software Zenodo metadata must declare Apache-2.0")
    if not isinstance(paper_zenodo, dict) or paper_zenodo.get("license") != "CC-BY-4.0":
        fail("paper Zenodo metadata must declare CC-BY-4.0")
    if software_zenodo.get("publication_date") != "2026-07-21":
        fail("software archive metadata must use the corrected public release date")

    toolchain = load_strict_json(ROOT / "toolchain.lock.json")
    if not isinstance(toolchain, dict):
        fail("toolchain lock must be an object")
    if toolchain.get("release_python") != "3.12.13" or toolchain.get("setuptools") != "82.0.1":
        fail("release Python and setuptools must remain patch-pinned")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    if project.get("build-system", {}).get("requires") != ["setuptools==82.0.1"]:
        fail("pyproject build backend must exactly match the toolchain lock")

    stale_identifier = "jkolantree/" + "bsc-audit-engine"
    text_suffixes = {".json", ".md", ".py", ".toml", ".yml", ".yaml", ".cff"}
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix in text_suffixes and not any(part in {"build", "dist", "release"} for part in path.relative_to(ROOT).parts):
            if stale_identifier in path.read_text(encoding="utf-8"):
                fail(f"stale repository identifier in {path.relative_to(ROOT)}")

    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    if "date-released: 2026-07-21" not in citation:
        fail("CITATION.cff must use the corrected public release date")
    public_version = __version__.replace("a", "-alpha.", 1)
    if ".dev" in __version__:
        release_match = re.search(r"\*\*Current release:\*\* `v([^`]+)`", (ROOT / "README.md").read_text(encoding="utf-8"))
        if not release_match or f"version: {release_match.group(1)}" not in citation:
            fail("development builds must preserve citation metadata for the named current release")
    elif f"version: {public_version}" not in citation:
        fail(f"CITATION.cff does not match package version {__version__}")

    print(f"release checks passed for {__version__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
