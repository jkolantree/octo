from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts.check_release_directory import (
    CHECKSUM_NAME,
    EXPECTED_COMPONENT_CONTRACT,
    MANIFEST_NAME,
    verify_release_directory,
)
from scripts.release_contract import (
    REQUIRED_ARTIFACT_ROLES,
    STAGE_IDS,
    expected_artifact_names,
    release_subject,
    sha256_identity,
    stage_judgment,
    verification_receipt,
)


ROOT = Path(__file__).resolve().parents[1]
COMMIT = "1" * 40
TREE = "2" * 40
TAG = "v0.3.0-alpha.15"
ENGINE_VERSION = "0.3.0a15"
PUBLIC_VERSION = "0.3.0-alpha.15"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_name(role: str) -> str:
    return expected_artifact_names(
        engine_version=ENGINE_VERSION,
        public_version=PUBLIC_VERSION,
    )[role]


def stage_evidence(
    stage_id: str,
    subject: dict[str, str],
    records: list[dict[str, object]],
    toolchain_lock: dict[str, object],
) -> dict[str, object]:
    by_role = {record["role"]: record for record in records}

    def refs(roles: set[str]) -> list[dict[str, str]]:
        return sorted(
            [
                {
                    "name": str(by_role[role]["name"]),
                    "sha256": str(by_role[role]["sha256"]),
                }
                for role in roles
            ],
            key=lambda item: item["name"].encode("utf-8"),
        )

    publication_roles = {
        "orientation_text",
        "copy_paste_protocol",
        "upload_protocol",
        "system_prompt_protocol",
        "canonical_protocol",
        "claim_manifest_schema",
        "worked_examples",
        "publication_metadata",
    }
    evidence_by_stage: dict[str, dict[str, object]] = {
        "exact-release-identity": {**subject, "worktree_status": "clean"},
        "toolchain-binding": {
            "python": toolchain_lock["release_python"],
            "node": toolchain_lock["return_desk_node"],
            "setuptools": toolchain_lock["setuptools"],
            "source_date_epoch": toolchain_lock["source_date_epoch"],
            "toolchain_lock_sha256": digest(ROOT / "toolchain.lock.json"),
        },
        "candidate-profile": {"profile": "candidate", "exit_code": 0},
        "distribution-build": {
            "exit_code": 0,
            "artifacts": refs({"python_wheel", "python_sdist"}),
        },
        "reproducible-distributions": {
            "comparison": "exact_filename_sha256_map",
            "artifacts": refs({"python_wheel", "python_sdist"}),
        },
        "tracked-source-archive": {
            **refs({"tracked_source_archive"})[0],
            "tracked_entries": 1,
        },
        "conformance-bundle": refs({"conformance_bundle"})[0],
        "publication-assets": {"artifacts": refs(publication_roles)},
        "custom-gpt-package": refs({"custom_gpt_package"})[0],
        "software-bill-of-materials": {
            **refs({"software_bill_of_materials"})[0],
            "wheel_sha256": by_role["python_wheel"]["sha256"],
        },
        "tracked-tree-recheck": {
            "commit": subject["commit"],
            "tree": subject["tree"],
            "expected_source_entries": 1,
            "tracked_source_state": "unchanged",
        },
        "artifact-payload-privacy": {
            "exit_code": 0,
            "scan_scope": "role_artifact_payloads_before_manifest",
            "artifacts": refs(set(REQUIRED_ARTIFACT_ROLES)),
        },
    }
    return evidence_by_stage[stage_id]


class ReleaseDirectoryTests(unittest.TestCase):
    def write_release(self, root: Path) -> None:
        root.mkdir()
        records = []
        expected_names = expected_artifact_names(
            engine_version=ENGINE_VERSION,
            public_version=PUBLIC_VERSION,
        )
        for index, (role, name) in enumerate(sorted(expected_names.items())):
            path = root / name
            path.write_bytes(f"artifact {index}\n".encode("utf-8"))
            records.append(
                {
                    "role": role,
                    "name": name,
                    "bytes": path.stat().st_size,
                    "sha256": digest(path),
                }
            )
        toolchain_lock = json.loads(
            (ROOT / "toolchain.lock.json").read_text(encoding="utf-8")
        )
        subject = release_subject(COMMIT, TREE, TAG)
        receipt = verification_receipt(
            subject,
            [
                stage_judgment(
                    stage_id,
                    subject=subject,
                    evidence=stage_evidence(
                        stage_id,
                        subject,
                        records,
                        toolchain_lock,
                    ),
                )
                for stage_id in STAGE_IDS
            ],
        )
        manifest = {
            "artifacts": records,
            "commit": COMMIT,
            "component_contract": copy.deepcopy(EXPECTED_COMPONENT_CONTRACT),
            "engine_version": ENGINE_VERSION,
            "git_tag": TAG,
            "git_tree": TREE,
            "manifest_version": "0.4.0",
            "publication_policy": {
                "embedded_artifact_signatures": "not_performed",
                "keyless_release_attestations": "required_before_publication",
            },
            "release": TAG,
            "source_date_epoch": toolchain_lock["source_date_epoch"],
            "source_exclusions": [
                "research/Audit_Descent_Calculus.docx",
                "research/Audit_Descent_Calculus.pdf",
            ],
            "toolchain": {
                "python": toolchain_lock["release_python"],
                "node": toolchain_lock["return_desk_node"],
                "setuptools": toolchain_lock["setuptools"],
                "lock_sha256": digest(ROOT / "toolchain.lock.json"),
                "container_digest": toolchain_lock.get("container_digest"),
            },
            "verification_receipt": receipt,
        }
        manifest_path = root / MANIFEST_NAME
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        checksum_paths = [root / record["name"] for record in records] + [
            manifest_path
        ]
        (root / CHECKSUM_NAME).write_text(
            "".join(
                f"{digest(path)}  {path.name}\n"
                for path in sorted(
                    checksum_paths, key=lambda item: item.name.encode("utf-8")
                )
            ),
            encoding="utf-8",
            newline="\n",
        )

    def verify(self, root: Path) -> list[str]:
        return verify_release_directory(
            root,
            commit=COMMIT,
            tree=TREE,
            tag=TAG,
        )

    def rewrite_manifest_checksum(self, root: Path) -> None:
        manifest_path = root / MANIFEST_NAME
        ledger_path = root / CHECKSUM_NAME
        lines = []
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            prior, name = line.split("  ", 1)
            lines.append(
                f"{digest(manifest_path) if name == MANIFEST_NAME else prior}  {name}"
            )
        ledger_path.write_text(
            "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
        )

    def test_valid_closed_release_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "release"
            self.write_release(root)
            failures = self.verify(root)
        self.assertEqual(failures, [])

    def test_modified_artifact_fails_manifest_and_checksum_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "release"
            self.write_release(root)
            name = artifact_name("python_wheel")
            (root / name).write_bytes(b"tampered\n")
            failures = self.verify(root)
        self.assertTrue(
            any(f"artifact digest differs for {name}" in item for item in failures)
        )
        self.assertTrue(
            any(f"checksum digest differs for {name}" in item for item in failures)
        )

    def test_extra_and_missing_files_fail_closed_roster(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "release"
            self.write_release(root)
            (root / artifact_name("python_wheel")).unlink()
            (root / "unexpected.bin").write_bytes(b"unexpected\n")
            failures = self.verify(root)
        self.assertTrue(any("manifest artifact is missing" in item for item in failures))
        self.assertTrue(any("release roster differs" in item for item in failures))

    def test_identity_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "release"
            self.write_release(root)
            failures = verify_release_directory(
                root,
                commit="3" * 40,
                tree=TREE,
                tag=TAG,
            )
        self.assertIn(
            f"manifest commit differs: expected {'3' * 40!r}, found {COMMIT!r}",
            failures,
        )

    def test_missing_keyless_attestation_requirement_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "release"
            self.write_release(root)
            path = root / MANIFEST_NAME
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["publication_policy"]["keyless_release_attestations"] = "optional"
            path.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            self.rewrite_manifest_checksum(root)
            failures = self.verify(root)
        self.assertTrue(
            any(
                "must require keyless attestations before publication" in item
                for item in failures
            )
        )

    def test_missing_or_changed_component_contract_is_rejected(self) -> None:
        for mutation in ("missing", "changed"):
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory) / "release"
                    self.write_release(root)
                    path = root / MANIFEST_NAME
                    manifest = json.loads(path.read_text(encoding="utf-8"))
                    if mutation == "missing":
                        manifest.pop("component_contract")
                    else:
                        manifest["component_contract"]["protocol"]["version"] = "forged"
                    path.write_text(
                        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                        newline="\n",
                    )
                    self.rewrite_manifest_checksum(root)
                    failures = self.verify(root)
                self.assertIn(
                    "manifest component_contract differs from the tagged package contract",
                    failures,
                )

    def test_duplicate_manifest_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "release"
            self.write_release(root)
            path = root / MANIFEST_NAME
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace(
                    f'  "commit": "{COMMIT}",',
                    f'  "commit": "{COMMIT}",\n  "commit": "{COMMIT}",',
                    1,
                ),
                encoding="utf-8",
                newline="\n",
            )
            failures = self.verify(root)
        self.assertTrue(any("duplicate JSON key 'commit'" in item for item in failures))

    def test_duplicate_and_traversal_checksum_names_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "release"
            self.write_release(root)
            ledger = root / CHECKSUM_NAME
            first = ledger.read_text(encoding="utf-8").splitlines()[0]
            ledger.write_text(
                ledger.read_text(encoding="utf-8")
                + first
                + "\n"
                + f"{'0' * 64}  ../escape\n",
                encoding="utf-8",
                newline="\n",
            )
            failures = self.verify(root)
        self.assertTrue(any("contains duplicate name" in item for item in failures))
        self.assertTrue(any("is malformed" in item for item in failures))

    def test_manifest_size_tampering_is_rejected_even_with_updated_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "release"
            self.write_release(root)
            path = root / MANIFEST_NAME
            manifest = json.loads(path.read_text(encoding="utf-8"))
            name = manifest["artifacts"][0]["name"]
            manifest["artifacts"][0]["bytes"] += 1
            path.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            self.rewrite_manifest_checksum(root)
            failures = self.verify(root)
        self.assertTrue(
            any(f"artifact size differs for {name}" in item for item in failures)
        )

    def test_same_count_wrong_role_and_role_name_swap_are_rejected(self) -> None:
        for mutation in ("unknown_role", "role_name_swap"):
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory) / "release"
                    self.write_release(root)
                    path = root / MANIFEST_NAME
                    manifest = json.loads(path.read_text(encoding="utf-8"))
                    if mutation == "unknown_role":
                        manifest["artifacts"][0]["role"] = "arbitrary_blob"
                    else:
                        first = manifest["artifacts"][0]
                        second = manifest["artifacts"][1]
                        first["role"], second["role"] = (
                            second["role"],
                            first["role"],
                        )
                    path.write_text(
                        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                        newline="\n",
                    )
                    self.rewrite_manifest_checksum(root)
                    failures = self.verify(root)
                self.assertTrue(
                    any(
                        "role is unknown" in item
                        or "name does not match semantic role" in item
                        for item in failures
                    )
                )

    def test_stale_receipt_and_unknown_manifest_field_are_rejected(self) -> None:
        for mutation in ("stale_receipt", "unknown_field"):
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory) / "release"
                    self.write_release(root)
                    path = root / MANIFEST_NAME
                    manifest = json.loads(path.read_text(encoding="utf-8"))
                    if mutation == "stale_receipt":
                        manifest["verification_receipt"]["subject"]["commit"] = "3" * 40
                    else:
                        manifest["untyped_claim"] = "pass"
                    path.write_text(
                        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                        newline="\n",
                    )
                    self.rewrite_manifest_checksum(root)
                    failures = self.verify(root)
                self.assertTrue(
                    any(
                        "receipt subject differs" in item
                        or "unknown or missing top-level fields" in item
                        for item in failures
                    )
                )

    def test_receipt_toolchain_is_bound_to_repository_lock(self) -> None:
        for field, value in {
            "python": "0.0.0",
            "node": {},
            "toolchain_lock_sha256": "0" * 64,
        }.items():
            with self.subTest(field=field):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory) / "release"
                    self.write_release(root)
                    path = root / MANIFEST_NAME
                    manifest = json.loads(path.read_text(encoding="utf-8"))
                    judgment = next(
                        item
                        for item in manifest["verification_receipt"]["judgments"]
                        if item["stage_id"] == "toolchain-binding"
                    )
                    judgment["evidence"][field] = value
                    judgment["evidence_record_sha256"] = sha256_identity(
                        judgment["evidence"]
                    )
                    path.write_text(
                        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                        newline="\n",
                    )
                    self.rewrite_manifest_checksum(root)
                    failures = self.verify(root)
                self.assertTrue(
                    any(
                        "authoritative toolchain lock" in item
                        for item in failures
                    )
                )

    def test_nested_entry_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "release"
            self.write_release(root)
            (root / "nested").mkdir()
            failures = self.verify(root)
        self.assertTrue(any("contains a non-regular file: nested" in item for item in failures))

    def test_symlink_entry_is_rejected_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "release"
            self.write_release(root)
            try:
                os.symlink(root / artifact_name("python_wheel"), root / "linked.bin")
            except (OSError, NotImplementedError):
                self.skipTest("symlinks are unavailable in this environment")
            failures = self.verify(root)
        self.assertTrue(
            any("contains a non-regular file: linked.bin" in item for item in failures)
        )


if __name__ == "__main__":
    unittest.main()
