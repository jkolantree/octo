from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_localization import (  # noqa: E402
    HASH_POLICY,
    JAPANESE_BETA_MARKER,
    MANIFEST_SCHEMA,
    REQUIRED_PAIRS,
    REQUIRED_SUPPLEMENTS,
    REVIEW_PENDING_MARKER,
    VERIFICATION_SCOPE,
    manifest_payload_sha256,
    sha256_bytes,
    validate_localization,
)


class LocalizationManifestTests(unittest.TestCase):
    def _write_file(self, root: Path, relative: str, data: bytes) -> None:
        path = root / Path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def _valid_tree(self, root: Path) -> dict[str, object]:
        entries = []
        for ordinal, (source, target) in enumerate(sorted(REQUIRED_PAIRS, key=lambda pair: pair[1]), 1):
            source_bytes = f"Canonical English source {ordinal}: {source}\n".encode("utf-8")
            target_bytes = (
                f"# 日本語資料 {ordinal}\n\n"
                f"> {JAPANESE_BETA_MARKER}: {REVIEW_PENDING_MARKER}です。\n"
            ).encode("utf-8")
            self._write_file(root, source, source_bytes)
            self._write_file(root, target, target_bytes)
            entries.append(
                {
                    "source": source,
                    "source_sha256": sha256_bytes(source_bytes),
                    "target": target,
                    "target_sha256": sha256_bytes(target_bytes),
                }
            )
        supplements = []
        for ordinal, (path, role) in enumerate(sorted(REQUIRED_SUPPLEMENTS.items()), 1):
            data = (
                f"# 日本語補助資料 {ordinal}\n\n"
                f"> {JAPANESE_BETA_MARKER}: {REVIEW_PENDING_MARKER}です。\n"
            ).encode("utf-8")
            self._write_file(root, path, data)
            supplements.append({"path": path, "sha256": sha256_bytes(data), "role": role})
        manifest: dict[str, object] = {
            "manifest_schema": MANIFEST_SCHEMA,
            "locale": "ja",
            "canonical_language": "en",
            "translation_status": "beta",
            "native_speaker_terminology_review": "pending",
            "hash_policy": HASH_POLICY,
            "verification_scope": VERIFICATION_SCOPE,
            "entries": entries,
            "supplements": supplements,
        }
        self._write_manifest(root, manifest)
        return manifest

    def _write_manifest(self, root: Path, manifest: dict[str, object]) -> None:
        value = copy.deepcopy(manifest)
        value["manifest_payload_sha256"] = manifest_payload_sha256(value)
        path = root / "docs" / "ja" / "TRANSLATION_MANIFEST.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def test_valid_manifest_binds_exact_source_and_target_bytes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-localization-valid-") as directory:
            root = Path(directory)
            self._valid_tree(root)
            self.assertEqual(validate_localization(root), [])

    def test_stale_source_and_target_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-localization-stale-") as directory:
            root = Path(directory)
            manifest = self._valid_tree(root)
            first = manifest["entries"][0]
            self._write_file(root, first["source"], b"changed canonical bytes\n")
            self.assertTrue(any("canonical source hash is stale" in item for item in validate_localization(root)))

            self._valid_tree(root)
            self._write_file(root, first["target"], f"{JAPANESE_BETA_MARKER}\nchanged\n".encode("utf-8"))
            self.assertTrue(any("localization target hash is stale" in item for item in validate_localization(root)))

    def test_malformed_and_duplicate_key_json_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-localization-json-") as directory:
            root = Path(directory)
            self._valid_tree(root)
            manifest_path = root / "docs" / "ja" / "TRANSLATION_MANIFEST.json"
            manifest_path.write_text("{not-json}\n", encoding="utf-8")
            self.assertTrue(any("not strict UTF-8 JSON" in item for item in validate_localization(root)))

            manifest_path.write_text(
                '{"manifest_schema":"x","manifest_schema":"y"}\n', encoding="utf-8"
            )
            self.assertTrue(any("duplicate JSON key" in item for item in validate_localization(root)))

    def test_duplicate_source_and_target_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-localization-duplicate-") as directory:
            root = Path(directory)
            manifest = self._valid_tree(root)
            entries = manifest["entries"]
            entries[1]["source"] = entries[0]["source"]
            entries[1]["source_sha256"] = entries[0]["source_sha256"]
            entries[2]["target"] = entries[0]["target"]
            entries[2]["target_sha256"] = entries[0]["target_sha256"]
            self._write_manifest(root, manifest)
            failures = validate_localization(root)
            self.assertTrue(any("duplicate canonical source" in item for item in failures))
            self.assertTrue(any("duplicate localization target" in item for item in failures))

    def test_traversal_is_rejected_even_with_a_fresh_manifest_self_hash(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-localization-traversal-") as directory:
            root = Path(directory)
            manifest = self._valid_tree(root)
            manifest["entries"][0]["source"] = "../outside.md"
            self._write_manifest(root, manifest)
            self.assertTrue(any("is unsafe" in item for item in validate_localization(root)))

    def test_missing_required_pair_and_missing_file_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-localization-missing-") as directory:
            root = Path(directory)
            manifest = self._valid_tree(root)
            removed = manifest["entries"].pop()
            self._write_manifest(root, manifest)
            failures = validate_localization(root)
            self.assertTrue(any("required translation pair is missing" in item for item in failures))

            manifest = self._valid_tree(root)
            missing_target = root / Path(manifest["entries"][0]["target"])
            missing_target.unlink()
            self.assertTrue(any("target is missing" in item for item in validate_localization(root)))

    def test_manifest_self_staleness_is_detected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-localization-self-") as directory:
            root = Path(directory)
            self._valid_tree(root)
            path = root / "docs" / "ja" / "TRANSLATION_MANIFEST.json"
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace('"translation_status": "beta"', '"translation_status": "changed"'), encoding="utf-8")
            self.assertTrue(any("payload hash is stale" in item for item in validate_localization(root)))

    def test_hashing_does_not_unicode_normalize_source_bytes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-localization-unicode-") as directory:
            root = Path(directory)
            manifest = self._valid_tree(root)
            entry = manifest["entries"][0]
            composed = "Café\n".encode("utf-8")
            decomposed = "Cafe\u0301\n".encode("utf-8")
            self.assertNotEqual(composed, decomposed)
            self._write_file(root, entry["source"], composed)
            entry["source_sha256"] = sha256_bytes(composed)
            self._write_manifest(root, manifest)
            self.assertEqual(validate_localization(root), [])
            self._write_file(root, entry["source"], decomposed)
            self.assertTrue(any("canonical source hash is stale" in item for item in validate_localization(root)))

    def test_pages_html_and_locale_catalog_pairs_are_required(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-localization-pages-") as directory:
            root = Path(directory)
            manifest = self._valid_tree(root)
            pairs = {(entry["source"], entry["target"]) for entry in manifest["entries"]}
            self.assertIn(("pages/index.html", "pages/ja.html"), pairs)
            self.assertIn(("pages/locale-en.js", "pages/locale-ja.js"), pairs)
            self.assertEqual(validate_localization(root), [])

    def test_japanese_supplements_are_exactly_inventoried_and_byte_bound(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-localization-supplements-") as directory:
            root = Path(directory)
            manifest = self._valid_tree(root)
            observed = {item["path"]: item["role"] for item in manifest["supplements"]}
            self.assertEqual(observed, REQUIRED_SUPPLEMENTS)

            first = manifest["supplements"][0]
            self._write_file(root, first["path"], f"{JAPANESE_BETA_MARKER}\nchanged\n".encode("utf-8"))
            self.assertTrue(any("supplement hash is stale" in item for item in validate_localization(root)))

            manifest = self._valid_tree(root)
            manifest["supplements"].pop()
            self._write_manifest(root, manifest)
            self.assertTrue(any("supplement inventory differs" in item for item in validate_localization(root)))

    def test_manifest_discloses_that_quality_and_native_review_are_not_certified(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-localization-scope-") as directory:
            root = Path(directory)
            manifest = self._valid_tree(root)
            self.assertEqual(manifest["verification_scope"], VERIFICATION_SCOPE)
            manifest["verification_scope"] = "translation_quality_certified"
            self._write_manifest(root, manifest)
            self.assertTrue(any("verification_scope" in item for item in validate_localization(root)))


if __name__ == "__main__":
    unittest.main()
