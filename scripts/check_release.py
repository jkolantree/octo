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
from bsc_audit.contracts import verify_repository_component_contract  # noqa: E402
from build_gpt_package import verify_package  # noqa: E402
from check_documentation import documentation_failures  # noqa: E402
from check_pages import verify_pages  # noqa: E402
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

    component_failures = verify_repository_component_contract(ROOT)
    if component_failures:
        fail(f"component contract failed verification: {component_failures[0]}")

    packet_failures = verify_packet()
    if packet_failures:
        fail(f"derived witnessed-descent packet failed verification: {packet_failures[0]}")

    page_failures = verify_pages()
    if page_failures:
        fail(f"GitHub Pages packet builder failed verification: {page_failures[0]}")

    gpt_failures = verify_package()
    if gpt_failures:
        fail(f"Custom GPT package failed verification: {gpt_failures[0]}")

    doc_failures = documentation_failures()
    if doc_failures:
        fail(f"documentation failed verification: {doc_failures[0]}")

    for directory in ("examples", "templates", "schemas", "src/bsc_audit/schema_data"):
        for path in sorted((ROOT / directory).glob("*.json")):
            load_strict_json(path)

    source_manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8").splitlines()
    for required_line in (
        "include README.ja.md",
        "include START_HERE.ja.md",
        "include .github/workflows/ci.yml",
        "include .github/workflows/release.yml",
        "recursive-include docs *.md *.css *.json",
    ):
        if source_manifest.count(required_line) != 1:
            fail(f"source distribution manifest must contain exactly once: {required_line}")
    for relative in (
        ".zenodo.json",
        "docs/PUBLICATION_STATUS.json",
        "docs/ja/TRANSLATION_MANIFEST.json",
        "research/zenodo.json",
        "toolchain.lock.json",
    ):
        load_strict_json(ROOT / relative)
    privacy_policy = load_strict_json(ROOT / "privacy-policy.json")
    if not isinstance(privacy_policy, dict) or privacy_policy.get("policy_version") != "1.0.1":
        fail("privacy policy is missing or has an unsupported version")

    for schema in sorted((ROOT / "schemas").glob("*.json")):
        packaged = ROOT / "src" / "bsc_audit" / "schema_data" / schema.name
        if not packaged.is_file() or schema.read_bytes() != packaged.read_bytes():
            fail(f"packaged schema differs from {schema.relative_to(ROOT)}")

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
    if software_zenodo.get("publication_date") != "2026-07-30":
        fail("software archive metadata must use the alpha.20 release date")

    toolchain = load_strict_json(ROOT / "toolchain.lock.json")
    if not isinstance(toolchain, dict):
        fail("toolchain lock must be an object")
    if (
        toolchain.get("release_python") != "3.12.13"
        or toolchain.get("return_desk_node") != "22.23.1"
        or toolchain.get("setuptools") != "82.0.1"
    ):
        fail("release Python, Return Desk Node, and setuptools must remain patch-pinned")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    if project.get("build-system", {}).get("requires") != ["setuptools==82.0.1"]:
        fail("pyproject build backend must exactly match the toolchain lock")
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    if "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020 # v7.0.0" not in ci:
        fail("CI must use the reviewed immutable setup-node v7.0.0 pin")
    if ci.count('node-version: "22.23.1"') != 1 or "package-manager-cache: false" not in ci:
        fail("CI Return Desk Node configuration differs from the toolchain lock")
    if ci.count("python scripts/verify.py core") != 1:
        fail("the three-version CI matrix must use the Python-only core profile")
    if ci.count("python scripts/verify.py candidate") != 1:
        fail("pinned integration CI must use the complete candidate profile")
    if ci.count("node --test tests/return_desk_runtime.test.cjs") != 1:
        fail("CI must rerun the Return Desk runtime suite from the source distribution")
    for token in (
        "SOURCE_DATE_EPOCH=1784505600 python scripts/build_dist.py",
        "Reproducible distributions",
        "python -m pip install --force-reinstall dist/*.whl",
        "Test the source distribution payload",
    ):
        if token not in ci:
            fail(f"CI package, reproducibility, or install checks lost required token: {token}")
    if ci.count("python scripts/build_dist.py") != 2:
        fail("CI must perform exactly one primary and one independent distribution build")
    pages_workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    if "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020 # v7.0.0" not in pages_workflow:
        fail("Pages must use the reviewed immutable setup-node v7.0.0 pin")
    if pages_workflow.count('node-version: "22.23.1"') != 1 or pages_workflow.count("package-manager-cache: false") != 1:
        fail("Pages Return Desk Node configuration differs from the toolchain lock")
    if pages_workflow.count("python scripts/verify.py pages") != 1:
        fail("Pages must run the complete Pages verification profile before deployment")
    release_builder = (ROOT / "scripts" / "build_release.py").read_text(encoding="utf-8")
    for token in (
        'require_node(lock)',
        "candidate_command = [",
        '"scripts/verify.py"',
        '"candidate"',
        "git_source_entries(commit)",
        "require_tracked_tree_clean(",
        "allowed_untracked_root=output",
        "expected_source_entries=source_entries",
        "release source rejects symlinks",
        'stage_judgment(',
        '"verification_receipt": receipt',
        "role_for_artifact_name(",
        "REQUIRED_ARTIFACT_ROLES",
        '"embedded_artifact_signatures": "not_performed"',
        '"keyless_release_attestations": "required_before_publication"',
    ):
        if token not in release_builder:
            fail(f"release builder is missing the exact Return Desk runtime gate: {token}")
    if '"return_desk_runtime": "pass"' in release_builder:
        fail("release builder must not manufacture fine-grained pass labels")
    if "bsc-audit-complete.zip" in release_builder:
        fail("release builder must not emit the duplicate unversioned source archive")
    release_workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    required_release_tokens = (
        "permissions: {}",
        "contents: write",
        "id-token: write",
        "attestations: write",
        "artifact-metadata: write",
        "persist-credentials: false",
        '"refs/tags/${GITHUB_REF_NAME}:refs/tags/${GITHUB_REF_NAME}"',
        "actions/attest@f7c74d28b9d84cb8768d0b8ca14a4bac6ef463e6 # v4.2.0",
        'subject-path: "${{ github.workspace }}/release/*"',
        "python scripts/check_release_directory.py",
        "gh attestation verify",
        "--source-digest \"$GITHUB_SHA\"",
        "--signer-workflow \"$GITHUB_REPOSITORY/.github/workflows/release.yml\"",
        "--deny-self-hosted-runners",
        "--draft",
        "--verify-tag",
        "--draft=false",
    )
    for token in required_release_tokens:
        if token not in release_workflow:
            fail(f"exact-release workflow is missing required token: {token}")
    restored_tag = release_workflow.index(
        '"refs/tags/${GITHUB_REF_NAME}:refs/tags/${GITHUB_REF_NAME}"'
    )
    asserted_tag_type = release_workflow.index(
        'test "$(git cat-file -t "$GITHUB_REF_NAME")" = "tag"'
    )
    if restored_tag >= asserted_tag_type:
        fail("exact-release workflow must restore the remote annotated tag before testing its type")
    if release_workflow.count("python scripts/check_release_directory.py") != 3:
        fail("exact-release workflow must verify build, draft download, and published download")
    if "--expected-count" in release_workflow or ".assets | length" in release_workflow:
        fail("exact-release workflow must derive completeness from semantic artifact roles")
    attestation = release_workflow.index(
        "actions/attest@f7c74d28b9d84cb8768d0b8ca14a4bac6ef463e6"
    )
    prepublication_verify = release_workflow.index(
        "Verify keyless provenance before creating a release"
    )
    draft = release_workflow.index("Create a draft release with the attested bytes")
    publish = release_workflow.index("Publish the verified prerelease")
    published_verify = release_workflow.index(
        "Verify the published assets and provenance"
    )
    if not attestation < prepublication_verify < draft < publish < published_verify:
        fail("exact-release workflow must attest and verify before draft publication")
    if not (ROOT / "scripts" / "check_release_directory.py").is_file():
        fail("closed release-directory verifier is missing")

    stale_identifier = "jkolantree/" + "bsc-audit-engine"
    text_suffixes = {".cjs", ".css", ".html", ".js", ".json", ".jsonl", ".md", ".mjs", ".py", ".toml", ".ts", ".txt", ".yml", ".yaml", ".cff"}
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix in text_suffixes and not any(part in {"build", "dist", "release"} for part in path.relative_to(ROOT).parts):
            if stale_identifier in path.read_text(encoding="utf-8"):
                fail(f"stale repository identifier in {path.relative_to(ROOT)}")

    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    if "date-released: 2026-07-30" not in citation:
        fail("CITATION.cff must use the alpha.20 release date")
    public_version = __version__.replace("a", "-alpha.", 1)
    if ".dev" in __version__:
        release_match = re.search(
            r"\*\*Current GitHub release:\*\* `v([^`]+)`",
            (ROOT / "README.md").read_text(encoding="utf-8"),
        )
        if not release_match or f"version: {release_match.group(1)}" not in citation:
            fail("development builds must preserve citation metadata for the named current GitHub release")
    elif f"version: {public_version}" not in citation:
        fail(f"CITATION.cff does not match package version {__version__}")

    print(f"release checks passed for {__version__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
