import os
import tempfile
import unittest
from pathlib import Path

from bsc_audit.provenance import (
    ZERO_SHA256,
    canonical_json,
    resolve_local_artifact,
    sha256_bytes,
    sha256_json,
    verify_local_artifact,
)


class ProvenanceTests(unittest.TestCase):
    def test_canonical_hash_is_stable_across_object_order(self):
        left = {"b": [2, 1], "a": {"x": True}}
        right = {"a": {"x": True}, "b": [2, 1]}
        self.assertEqual(canonical_json(left), canonical_json(right))
        self.assertEqual(sha256_json(left), sha256_json(right))

    def test_raw_hash_preserves_byte_level_distinctions(self):
        self.assertNotEqual(sha256_bytes(b'{"a":1}'), sha256_bytes(b'{ "a": 1 }'))

    def test_local_artifact_verifies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = b"certificate fixture\n"
            (root / "proof.bin").write_bytes(content)
            ok, reason, actual = verify_local_artifact(root, "proof.bin", sha256_bytes(content))
        self.assertTrue(ok)
        self.assertEqual(reason, "verified")
        self.assertEqual(actual, sha256_bytes(content))

    def test_hash_mismatch_returns_computed_witness(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = b"actual bytes"
            (root / "proof.bin").write_bytes(content)
            ok, reason, actual = verify_local_artifact(root, "proof.bin", "sha256:" + "1" * 64)
        self.assertFalse(ok)
        self.assertEqual(reason, "hash_mismatch")
        self.assertEqual(actual, sha256_bytes(content))

    def test_zero_hash_is_never_accepted(self):
        ok, reason, actual = verify_local_artifact(None, "proof.bin", ZERO_SHA256)
        self.assertFalse(ok)
        self.assertEqual(reason, "placeholder_hash")
        self.assertIsNone(actual)

    def test_missing_artifact_root_is_not_implicitly_trusted(self):
        ok, reason, actual = verify_local_artifact(None, "proof.bin", "sha256:" + "1" * 64)
        self.assertFalse(ok)
        self.assertEqual(reason, "artifact_root_unavailable")
        self.assertIsNone(actual)

    def test_absolute_and_parent_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for value in (str(root / "proof.bin"), "../proof.bin", "..\\proof.bin"):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    resolve_local_artifact(root, value)

    @unittest.skipIf(os.name == "nt", "symlink semantics differ on Windows")
    def test_symlink_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            target = Path(outside) / "proof.bin"
            target.write_bytes(b"outside")
            (root / "escape.bin").symlink_to(target)
            ok, reason, _actual = verify_local_artifact(root, "escape.bin", sha256_bytes(b"outside"))
        self.assertFalse(ok)
        self.assertEqual(reason, "unsafe_path")

    def test_artifact_size_limit_is_checked_before_reading(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "large.bin").write_bytes(b"1234")
            ok, reason, actual = verify_local_artifact(
                root,
                "large.bin",
                sha256_bytes(b"1234"),
                max_bytes=3,
            )
        self.assertFalse(ok)
        self.assertEqual(reason, "artifact_too_large")
        self.assertIsNone(actual)


if __name__ == "__main__":
    unittest.main()
