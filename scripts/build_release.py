#!/usr/bin/env python3
"""Build a deterministic, certificate-bearing public preview bundle.

The script runs the repository's checks before it writes any release manifest.
It does not embed signatures. The exact-release tag workflow keyless-attests
every final file before it creates or publishes the GitHub prerelease.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from importlib.metadata import version as distribution_version
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bsc_audit import __version__  # noqa: E402
from bsc_audit.contracts import COMPONENT_CONTRACT  # noqa: E402
from build_publication_assets import write_release_assets  # noqa: E402
from build_gpt_package import write_release_asset as write_gpt_release_asset  # noqa: E402
from release_contract import (  # noqa: E402
    REQUIRED_ARTIFACT_ROLES,
    release_subject,
    role_for_artifact_name,
    stage_judgment,
    validate_verification_receipt,
    verification_receipt,
)


PUBLIC_VERSION = __version__.replace("a", "-alpha.", 1)
SOURCE_DATE_EPOCH = int(os.environ.get("SOURCE_DATE_EPOCH", "1784505600"))
ZIP_TIME = time.gmtime(max(SOURCE_DATE_EPOCH, 315532800))[:6]
EXCLUDED_TRACKED_FILES = {
    "research/Audit_Descent_Calculus.docx",
    "research/Audit_Descent_Calculus.pdf",
}


def run(command: list[str], *, expected: int = 0, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode != expected:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(f"command returned {result.returncode}, expected {expected}: {' '.join(command)}")
    return result


def run_bytes(command: list[str], *, cwd: Path = ROOT) -> bytes:
    result = subprocess.run(command, cwd=cwd, capture_output=True, check=False)
    if result.returncode != 0:
        sys.stderr.write(result.stdout.decode("utf-8", errors="replace"))
        sys.stderr.write(result.stderr.decode("utf-8", errors="replace"))
        raise SystemExit(
            f"command returned {result.returncode}, expected 0: {' '.join(command)}"
        )
    return result.stdout


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def zip_tree(destination: Path, paths: list[Path], base: Path) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(paths, key=lambda item: item.relative_to(base).as_posix()):
            relative = path.relative_to(base).as_posix()
            data = path.read_bytes()
            info = zipfile.ZipInfo(relative, ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(info, data)


def repository_identity() -> tuple[str, str, str]:
    status = run(["git", "status", "--porcelain", "--untracked-files=all"]).stdout.strip()
    if status:
        raise SystemExit("release builds require a clean Git worktree")
    commit = run(["git", "rev-parse", "HEAD"]).stdout.strip()
    tree = run(["git", "rev-parse", "HEAD^{tree}"]).stdout.strip()
    expected_tag = f"v{PUBLIC_VERSION}"
    tags = set(run(["git", "tag", "--points-at", "HEAD"]).stdout.split())
    if expected_tag not in tags:
        raise SystemExit(f"release commit must carry exact immutable tag {expected_tag}")
    return commit, tree, expected_tag


def require_tracked_tree_clean(
    commit: str,
    tree: str,
    *,
    root: Path = ROOT,
    allowed_untracked_root: Path | None = None,
    expected_source_entries: list[tuple[str, bytes]] | None = None,
) -> None:
    """Reassert that generators did not change tagged or add source bytes."""

    observed_commit = run(["git", "rev-parse", "HEAD"], cwd=root).stdout.strip()
    observed_tree = run(["git", "rev-parse", "HEAD^{tree}"], cwd=root).stdout.strip()
    raw_status = run_bytes(
        [
            "git",
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
        ],
        cwd=root,
    )
    allowed_relative: str | None = None
    if allowed_untracked_root is not None:
        try:
            allowed_relative = (
                allowed_untracked_root.resolve()
                .relative_to(root.resolve())
                .as_posix()
            )
        except (OSError, RuntimeError, ValueError):
            allowed_relative = None
    unexpected_status = False
    for raw_record in raw_status.split(b"\0"):
        if not raw_record:
            continue
        if not raw_record.startswith(b"?? "):
            unexpected_status = True
            break
        try:
            relative = raw_record[3:].decode("utf-8")
        except UnicodeDecodeError:
            unexpected_status = True
            break
        if (
            allowed_relative is None
            or (
                relative != allowed_relative
                and not relative.startswith(f"{allowed_relative}/")
            )
        ):
            unexpected_status = True
            break
    source_bytes_differ = False
    entries = (
        expected_source_entries
        if expected_source_entries is not None
        else git_source_entries(commit, root=root)
    )
    for relative, expected in entries:
        path = root.joinpath(*PurePosixPath(relative).parts)
        try:
            if path.is_symlink() or not path.is_file() or path.read_bytes() != expected:
                source_bytes_differ = True
                break
        except OSError:
            source_bytes_differ = True
            break
    if (
        observed_commit != commit
        or observed_tree != tree
        or unexpected_status
        or source_bytes_differ
    ):
        raise SystemExit(
            "release generation changed tracked source bytes, added untracked "
            "source, or changed the index, commit, or tree"
        )


def require_release_version() -> None:
    if ".dev" in __version__:
        raise SystemExit(f"release builds refuse development version {__version__}")


def git_source_entries(
    commit: str,
    *,
    root: Path = ROOT,
) -> list[tuple[str, bytes]]:
    """Read release-source bytes from an immutable Git tree, never the checkout."""

    raw_tree = run_bytes(
        ["git", "ls-tree", "-r", "-z", "--full-tree", commit],
        cwd=root,
    )
    entries: list[tuple[str, bytes]] = []
    folded_paths: set[str] = set()
    for raw_record in raw_tree.split(b"\0"):
        if not raw_record:
            continue
        try:
            metadata, raw_path = raw_record.split(b"\t", 1)
            mode, object_type, object_id = metadata.decode("ascii").split()
            relative = raw_path.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as exc:
            raise SystemExit("Git tree contains an undecodable source entry") from exc
        if relative in EXCLUDED_TRACKED_FILES:
            continue
        pure = PurePosixPath(relative)
        if (
            pure.is_absolute()
            or pure.as_posix() != relative
            or "\\" in relative
            or any(
                ord(character) < 32 or ord(character) == 127
                for character in relative
            )
            or any(part in {"", ".", ".."} or ":" in part for part in pure.parts)
        ):
            raise SystemExit(f"Git tree contains an unsafe source path: {relative!r}")
        folded = relative.casefold()
        if folded in folded_paths:
            raise SystemExit(
                f"Git tree contains a case-folding source collision: {relative!r}"
            )
        folded_paths.add(folded)
        if object_type != "blob" or mode not in {"100644", "100755"}:
            raise SystemExit(
                "release source rejects symlinks, submodules, and non-regular "
                f"Git entries: {relative!r} ({mode} {object_type})"
            )
        data = run_bytes(["git", "cat-file", "blob", object_id], cwd=root)
        entries.append((relative, data))
    return sorted(entries)


def zip_git_source(
    destination: Path,
    entries: list[tuple[str, bytes]],
) -> None:
    with zipfile.ZipFile(
        destination,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for relative, data in entries:
            info = zipfile.ZipInfo(relative, ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(info, data)


def toolchain_lock() -> dict[str, object]:
    lock_path = ROOT / "toolchain.lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    actual_python = sys.version.split()[0]
    actual_setuptools = distribution_version("setuptools")
    if lock.get("release_python") != actual_python:
        raise SystemExit(f"release Python {actual_python} does not match toolchain lock {lock.get('release_python')}")
    if lock.get("setuptools") != actual_setuptools:
        raise SystemExit(f"setuptools {actual_setuptools} does not match toolchain lock {lock.get('setuptools')}")
    if lock.get("source_date_epoch") != SOURCE_DATE_EPOCH:
        raise SystemExit("SOURCE_DATE_EPOCH does not match toolchain.lock.json")
    return lock


def require_node(lock: dict[str, object]) -> str:
    node = shutil.which("node")
    if node is None:
        raise SystemExit("release builds require Node from toolchain.lock.json on PATH")
    actual = run([node, "--version"]).stdout.strip().removeprefix("v")
    expected = lock.get("return_desk_node")
    if actual != expected:
        raise SystemExit(f"Return Desk Node {actual} does not match toolchain lock {expected}")
    return node


def conformance_bundle(destination: Path) -> None:
    cases = [
        ("legacy-hash-only-blocked", "audit", "examples/claim_valid.json", 1),
        (
            "closed-polynomial-claim",
            "audit",
            "examples/claim_polynomial_identity.json",
            0,
        ),
        ("finite-prime-comb-no-go", "audit", "examples/claim_arithmetic_no_go.json", 1),
        ("observation-descent-failure", "observe", "examples/observation_failure.json", 1),
        ("natural-transport", "complex", "examples/complex_valid_transport.json", 0),
        ("broken-transport", "complex", "examples/complex_broken_transport.json", 1),
        ("atomic-record", "atomic", "examples/atomic_modulus_valid.json", 0),
        ("defect-understatement", "defect", "examples/defect_composition_understated.json", 1),
        ("q-polynomial-identity", "theorem", "examples/theorem_binomial_identity.json", 0),
    ]
    with tempfile.TemporaryDirectory(prefix="bsc-conformance-") as temporary:
        base = Path(temporary) / f"bsc-audit-conformance-{PUBLIC_VERSION}"
        base.mkdir()
        records: list[dict[str, object]] = []
        for name, command, source, expected in cases:
            source_path = ROOT / source
            copied = base / f"{name}.input.json"
            shutil.copyfile(source_path, copied)
            result = run([sys.executable, "run_audit.py", command, str(source_path)], expected=expected)
            output = base / f"{name}.output.json"
            output.write_text(result.stdout, encoding="utf-8")
            records.append({"name": name, "command": command, "expected_exit": expected, "input": copied.name, "output": output.name})

        malformed = base / "malformed.input.json"
        malformed.write_text('{"duplicate": 1, "duplicate": 2}\n', encoding="utf-8")
        result = run([sys.executable, "run_audit.py", "audit", str(malformed)], expected=2)
        (base / "malformed.output.json").write_text(result.stdout, encoding="utf-8")
        records.append({"name": "malformed", "command": "audit", "expected_exit": 2, "input": malformed.name, "output": "malformed.output.json"})

        write_json(base / "CONFORMANCE.json", {"engine_version": __version__, "cases": records})
        (base / "README.md").write_text(
            "# BSC Audit Engine conformance bundle\n\n"
            "Each case contains an input, the exact JSON output produced by the release build, "
            "and an expected process exit code recorded in `CONFORMANCE.json`. A conforming implementation "
            "must reproduce the decision and finding codes; byte-for-byte formatting is not required.\n",
            encoding="utf-8",
        )
        zip_tree(destination, [path for path in base.rglob("*") if path.is_file()], base.parent)


def sbom(destination: Path, wheel: Path) -> None:
    created = datetime.fromtimestamp(SOURCE_DATE_EPOCH, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    namespace_hash = hashlib.sha256(f"bsc-audit-engine:{PUBLIC_VERSION}".encode()).hexdigest()
    write_json(
        destination,
        {
            "spdxVersion": "SPDX-2.3",
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "name": f"bsc-audit-engine-{PUBLIC_VERSION}",
            "documentNamespace": f"https://github.com/jkolantree/octo/releases/{PUBLIC_VERSION}/sbom-{namespace_hash}",
            "creationInfo": {"created": created, "creators": ["Tool: bsc-audit-engine/scripts/build_release.py"]},
            "packages": [
                {
                    "name": "bsc-audit-engine",
                    "SPDXID": "SPDXRef-Package",
                    "versionInfo": PUBLIC_VERSION,
                    "downloadLocation": "NOASSERTION",
                    "filesAnalyzed": False,
                    "licenseConcluded": "Apache-2.0",
                    "licenseDeclared": "Apache-2.0",
                    "copyrightText": "Copyright J. Tree",
                    "externalRefs": [
                        {
                            "referenceCategory": "PACKAGE-MANAGER",
                            "referenceType": "purl",
                            "referenceLocator": f"pkg:pypi/bsc-audit-engine@{__version__}",
                        }
                    ],
                    "checksums": [{"algorithm": "SHA256", "checksumValue": sha256(wheel)}],
                }
            ],
        },
    )


def main() -> int:
    require_release_version()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "release")
    args = parser.parse_args()
    output = args.output.resolve()
    commit, tree, tag = repository_identity()
    subject = release_subject(commit, tree, tag)
    judgments = [
        stage_judgment(
            "exact-release-identity",
            subject=subject,
            evidence={
                "commit": commit,
                "tree": tree,
                "tag": tag,
                "worktree_status": "clean",
            },
        )
    ]
    source_entries = git_source_entries(commit)
    lock = toolchain_lock()
    node = require_node(lock)
    toolchain_evidence = {
        "python": lock["release_python"],
        "node": lock["return_desk_node"],
        "setuptools": lock["setuptools"],
        "source_date_epoch": lock["source_date_epoch"],
        "toolchain_lock_sha256": sha256(ROOT / "toolchain.lock.json"),
    }
    judgments.append(
        stage_judgment(
            "toolchain-binding",
            subject=subject,
            evidence=toolchain_evidence,
        )
    )
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"release output directory must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)

    candidate_command = [
        sys.executable,
        "scripts/verify.py",
        "candidate",
        "--node-executable",
        node,
    ]
    candidate = run(candidate_command)
    judgments.append(
        stage_judgment(
            "candidate-profile",
            subject=subject,
            evidence={
                "profile": "candidate",
                "exit_code": candidate.returncode,
            },
        )
    )
    env = dict(os.environ, SOURCE_DATE_EPOCH=str(SOURCE_DATE_EPOCH))
    build_command = [
        sys.executable,
        "scripts/build_dist.py",
        "--outdir",
        str(output),
    ]
    build = subprocess.run(build_command, cwd=ROOT, env=env, text=True, capture_output=True, check=False)
    if build.returncode != 0:
        sys.stderr.write(build.stdout)
        sys.stderr.write(build.stderr)
        raise SystemExit("distribution build failed")
    first_distributions = sorted(
        path for path in output.iterdir() if path.suffix in {".whl", ".gz"}
    )
    judgments.append(
        stage_judgment(
            "distribution-build",
            subject=subject,
            evidence={
                "exit_code": build.returncode,
                "artifacts": [
                    {"name": path.name, "sha256": sha256(path)}
                    for path in first_distributions
                ],
            },
        )
    )
    with tempfile.TemporaryDirectory(prefix="bsc-repro-build-") as temporary:
        second_output = Path(temporary)
        second_command = [
            sys.executable,
            "scripts/build_dist.py",
            "--outdir",
            str(second_output),
        ]
        second = subprocess.run(second_command, cwd=ROOT, env=env, text=True, capture_output=True, check=False)
        if second.returncode != 0:
            sys.stderr.write(second.stdout)
            sys.stderr.write(second.stderr)
            raise SystemExit("reproducibility build failed")
        first_map = {
            path.name: sha256(path) for path in first_distributions
        }
        second_map = {
            path.name: sha256(path)
            for path in sorted(
                candidate
                for candidate in second_output.iterdir()
                if candidate.is_file()
            )
        }
        if first_map != second_map:
            raise SystemExit(
                "distribution artifact maps are not reproducible: "
                f"first={sorted(first_map)!r}, second={sorted(second_map)!r}"
            )
        judgments.append(
            stage_judgment(
                "reproducible-distributions",
                subject=subject,
                evidence={
                    "comparison": "exact_filename_sha256_map",
                    "artifacts": [
                        {"name": name, "sha256": first_map[name]}
                        for name in sorted(first_map, key=lambda item: item.encode("utf-8"))
                    ],
                },
            )
        )

    source_zip = output / f"bsc-audit-engine-{PUBLIC_VERSION}.zip"
    zip_git_source(source_zip, source_entries)
    judgments.append(
        stage_judgment(
            "tracked-source-archive",
            subject=subject,
            evidence={
                "name": source_zip.name,
                "sha256": sha256(source_zip),
                "tracked_entries": len(source_entries),
            },
        )
    )
    conformance = output / f"bsc-audit-conformance-{PUBLIC_VERSION}.zip"
    conformance_bundle(conformance)
    judgments.append(
        stage_judgment(
            "conformance-bundle",
            subject=subject,
            evidence={"name": conformance.name, "sha256": sha256(conformance)},
        )
    )
    publication_paths = write_release_assets(output)
    judgments.append(
        stage_judgment(
            "publication-assets",
            subject=subject,
            evidence={
                "artifacts": [
                    {"name": path.name, "sha256": sha256(path)}
                    for path in sorted(publication_paths)
                ]
            },
        )
    )
    gpt_path = write_gpt_release_asset(
        output,
        source_commit=commit,
        source_tree=tree,
        source_tag=tag,
    )
    judgments.append(
        stage_judgment(
            "custom-gpt-package",
            subject=subject,
            evidence={"name": gpt_path.name, "sha256": sha256(gpt_path)},
        )
    )
    artifacts = sorted(
        path
        for path in output.iterdir()
        if path.is_file()
        and path.name not in {
            "SHA256SUMS",
            "RELEASE_MANIFEST.json",
            "SBOM.spdx.json",
        }
    )
    sbom_path = output / "SBOM.spdx.json"
    wheel = next(path for path in artifacts if path.suffix == ".whl")
    sbom(sbom_path, wheel)
    judgments.append(
        stage_judgment(
            "software-bill-of-materials",
            subject=subject,
            evidence={
                "name": sbom_path.name,
                "sha256": sha256(sbom_path),
                "wheel_sha256": sha256(wheel),
            },
        )
    )
    artifacts.append(sbom_path)
    require_tracked_tree_clean(
        commit,
        tree,
        allowed_untracked_root=output,
        expected_source_entries=source_entries,
    )
    judgments.append(
        stage_judgment(
            "tracked-tree-recheck",
            subject=subject,
            evidence={
                "commit": commit,
                "tree": tree,
                "expected_source_entries": len(source_entries),
                "tracked_source_state": "unchanged",
            },
        )
    )
    privacy_command = [
        sys.executable,
        "scripts/check_privacy.py",
        "--protected-history",
        "HEAD",
        "--artifacts",
        str(output),
    ]
    privacy = run(privacy_command)
    judgments.append(
        stage_judgment(
            "artifact-payload-privacy",
            subject=subject,
            evidence={
                "exit_code": privacy.returncode,
                "scan_scope": "role_artifact_payloads_before_manifest",
                "artifacts": [
                    {"name": path.name, "sha256": sha256(path)}
                    for path in sorted(artifacts)
                ],
            },
        )
    )
    artifact_records = []
    observed_roles: set[str] = set()
    for path in sorted(artifacts):
        role = role_for_artifact_name(
            path.name,
            engine_version=__version__,
            public_version=PUBLIC_VERSION,
        )
        if role is None or role in observed_roles:
            raise SystemExit(
                f"release artifact has no unique semantic role: {path.name}"
            )
        observed_roles.add(role)
        artifact_records.append(
            {
                "role": role,
                "name": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    if observed_roles != REQUIRED_ARTIFACT_ROLES:
        raise SystemExit(
            "release semantic artifact roster differs: "
            f"missing={sorted(REQUIRED_ARTIFACT_ROLES - observed_roles)!r}, "
            f"extra={sorted(observed_roles - REQUIRED_ARTIFACT_ROLES)!r}"
        )
    receipt = verification_receipt(subject, judgments)
    receipt_failures = validate_verification_receipt(
        receipt,
        expected_subject=subject,
        expected_toolchain_evidence=toolchain_evidence,
        expected_artifacts=artifact_records,
    )
    if receipt_failures:
        raise SystemExit(
            "internal release verification receipt failed: "
            + "; ".join(receipt_failures)
        )
    manifest = {
        "release": f"v{PUBLIC_VERSION}",
        "engine_version": __version__,
        "component_contract": COMPONENT_CONTRACT.release_record(),
        "manifest_version": "0.4.0",
        "commit": commit,
        "git_tree": tree,
        "git_tag": tag,
        "source_exclusions": sorted(EXCLUDED_TRACKED_FILES),
        "source_date_epoch": SOURCE_DATE_EPOCH,
        "toolchain": {
            "python": lock["release_python"],
            "node": lock["return_desk_node"],
            "setuptools": lock["setuptools"],
            "lock_sha256": sha256(ROOT / "toolchain.lock.json"),
            "container_digest": lock.get("container_digest"),
        },
        "verification_receipt": receipt,
        "publication_policy": {
            "embedded_artifact_signatures": "not_performed",
            "keyless_release_attestations": "required_before_publication",
        },
        "artifacts": artifact_records,
    }
    manifest_path = output / "RELEASE_MANIFEST.json"
    write_json(manifest_path, manifest)
    checksum_paths = sorted(artifacts + [manifest_path])
    (output / "SHA256SUMS").write_text("".join(f"{sha256(path)}  {path.name}\n" for path in checksum_paths), encoding="utf-8")
    # Re-scan the closed directory, including its receipt, manifest, and ledger.
    run([sys.executable, "scripts/check_privacy.py", "--protected-history", "HEAD", "--artifacts", str(output)])
    print(f"release assets written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
