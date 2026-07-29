from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts.check_release_directory import (
    CHECKSUM_NAME,
    MANIFEST_NAME,
    verify_release_directory,
)


COMMIT = "1" * 40
TREE = "2" * 40
TAG = "v0.3.0-alpha.12"
ARTIFACT_COUNT = 15
RELEASE_FILE_COUNT = ARTIFACT_COUNT + 2


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReleaseDirectoryTests(unittest.TestCase):
    def write_release(self, root: Path) -> None:
        root.mkdir()
        records = []
        for index in range(ARTIFACT_COUNT):
            name = f"artifact-{index:02d}.bin"
            path = root / name
            path.write_bytes(f"artifact {index}\n".encode("utf-8"))
            records.append(
                {
                    "name": name,
                    "bytes": path.stat().st_size,
                    "sha256": digest(path),
                }
            )
        manifest = {
            "artifacts": records,
            "commit": COMMIT,
            "git_tag": TAG,
            "git_tree": TREE,
            "release": TAG,
            "verification": {
                "embedded_artifact_signatures": "not_performed",
                "keyless_release_attestations": "required_before_publication",
            },
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
            expected_count=RELEASE_FILE_COUNT,
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
            (root / "artifact-00.bin").write_bytes(b"tampered\n")
            failures = self.verify(root)
        self.assertTrue(
            any("artifact digest differs for artifact-00.bin" in item for item in failures)
        )
        self.assertTrue(
            any("checksum digest differs for artifact-00.bin" in item for item in failures)
        )

    def test_extra_and_missing_files_fail_closed_roster(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "release"
            self.write_release(root)
            (root / "artifact-00.bin").unlink()
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
                expected_count=RELEASE_FILE_COUNT,
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
            manifest["verification"]["keyless_release_attestations"] = "optional"
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
        self.assertTrue(any("line 18 is malformed" in item for item in failures))

    def test_manifest_size_tampering_is_rejected_even_with_updated_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "release"
            self.write_release(root)
            path = root / MANIFEST_NAME
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["artifacts"][0]["bytes"] += 1
            path.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            self.rewrite_manifest_checksum(root)
            failures = self.verify(root)
        self.assertTrue(
            any("artifact size differs for artifact-00.bin" in item for item in failures)
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
                os.symlink(root / "artifact-00.bin", root / "linked.bin")
            except (OSError, NotImplementedError):
                self.skipTest("symlinks are unavailable in this environment")
            failures = self.verify(root)
        self.assertTrue(
            any("contains a non-regular file: linked.bin" in item for item in failures)
        )


if __name__ == "__main__":
    unittest.main()
