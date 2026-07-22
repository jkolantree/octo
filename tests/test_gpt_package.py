from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_gpt_package import (  # noqa: E402
    GPT_ROOT,
    MAX_GPT_INSTRUCTION_CHARACTERS,
    PROFILE_PATH,
    REQUIRED_EVAL_CASE_REQUIREMENTS,
    REQUIRED_EVAL_CASE_IDS,
    REQUIRED_RULE_IDS,
    REQUIRED_RULE_SEVERITIES,
    all_rules,
    archive_name,
    generated_payload,
    load_strict_json,
    materialize_eval_cases,
    package_files,
    provenance_paths,
    sha256_bytes,
    verify_archive,
    verify_package,
    write_archive,
    write_package,
)
from build_release import write_gpt_release_asset  # noqa: E402


class CustomGptPackageTests(unittest.TestCase):
    def test_committed_package_is_current_and_valid(self) -> None:
        self.assertEqual(verify_package(GPT_ROOT), [])

    def test_package_regeneration_is_byte_for_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-gpt-a-") as first_dir, tempfile.TemporaryDirectory(
            prefix="bsc-gpt-b-"
        ) as second_dir:
            first = Path(first_dir)
            second = Path(second_dir)
            write_package(first)
            write_package(second)
            self.assertEqual(package_files(first), package_files(second))
            self.assertEqual(package_files(first), generated_payload())

    def test_release_archive_is_deterministic_safe_and_complete(self) -> None:
        self.assertTrue(callable(write_gpt_release_asset))
        with tempfile.TemporaryDirectory(prefix="bsc-gpt-zip-") as directory:
            root = Path(directory)
            first = write_archive(root / f"first-{archive_name()}")
            second = write_archive(root / f"second-{archive_name()}")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(verify_archive(first), [])
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(len(archive.namelist()), len(set(archive.namelist())))

    def test_release_archive_binds_exact_commit_tree_and_tag(self) -> None:
        binding = {
            "source_commit": "1" * 40,
            "source_tree": "2" * 40,
            "source_tag": "v0.3.0-alpha.6",
        }
        with tempfile.TemporaryDirectory(prefix="bsc-gpt-bound-zip-") as directory:
            path = write_gpt_release_asset(Path(directory), **binding)
            self.assertEqual(verify_archive(path, **binding), [])
            with zipfile.ZipFile(path) as archive:
                manifest_name = next(name for name in archive.namelist() if name.endswith("/GPT_RELEASE_MANIFEST.json"))
                manifest = json.loads(archive.read(manifest_name))
            self.assertEqual(
                (manifest["source_commit"], manifest["source_tree"], manifest["source_tag"]),
                (binding["source_commit"], binding["source_tree"], binding["source_tag"]),
            )

    def test_strict_json_rejects_duplicate_keys_and_nonfinite_values(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-gpt-json-") as directory:
            duplicate = Path(directory) / "duplicate.json"
            duplicate.write_text('{"a":1,"a":2}\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_strict_json(duplicate)
            nonfinite = Path(directory) / "nonfinite.json"
            nonfinite.write_text('{"a":NaN}\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_strict_json(nonfinite)

    def test_manifest_and_checksum_ledgers_bind_every_payload_file(self) -> None:
        payload = generated_payload()
        manifest = json.loads(payload[Path("GPT_RELEASE_MANIFEST.json")])
        self.assertIsNone(manifest["source_commit"])
        self.assertIsNone(manifest["source_tree"])
        self.assertIsNone(manifest["source_tag"])
        self.assertEqual(
            {item["path"] for item in manifest["generated_artifacts"]},
            {path.as_posix() for path in payload if path.as_posix() not in {"GPT_RELEASE_MANIFEST.json", "SHA256SUMS"}},
        )
        expected = {
            path.as_posix(): sha256_bytes(data)
            for path, data in payload.items()
            if path.as_posix() != "SHA256SUMS"
        }
        actual = {}
        for line in payload[Path("SHA256SUMS")].decode("utf-8").splitlines():
            digest, name = line.split("  ", 1)
            actual[name] = digest
        self.assertEqual(actual, expected)

    def test_every_eval_case_binds_scoring_criteria(self) -> None:
        records = [
            json.loads(line)
            for line in generated_payload()[Path("evals/GPT_EVAL_CASES.jsonl")].decode("utf-8").splitlines()
        ]
        self.assertTrue(records)
        self.assertTrue(all(len(record.get("scoring_criteria", [])) == 10 for record in records))
        self.assertTrue(REQUIRED_EVAL_CASE_IDS <= {record["id"] for record in records})
        self.assertEqual(
            {
                record["id"]: record["workflow_requirement"]
                for record in records
                if record["id"] in REQUIRED_EVAL_CASE_IDS
            },
            REQUIRED_EVAL_CASE_REQUIREMENTS,
        )

    def test_eval_source_paths_cannot_escape_the_reviewed_repository_prefix(self) -> None:
        spec = {
            "scoring_dimensions": [],
            "cases": [
                {
                    "id": "escape",
                    "input": {"source_path": "../private.txt"},
                }
            ],
        }
        with self.assertRaises(ValueError):
            materialize_eval_cases(spec)

    def test_instructions_are_bounded_and_profile_bound(self) -> None:
        payload = generated_payload()
        profile = load_strict_json(PROFILE_PATH)
        rules = all_rules(profile)
        self.assertEqual({rule["id"] for rule in rules}, REQUIRED_RULE_IDS)
        self.assertEqual({rule["id"]: rule["severity"] for rule in rules}, REQUIRED_RULE_SEVERITIES)
        self.assertEqual(len(REQUIRED_RULE_IDS), 38)
        self.assertEqual(sum(severity == "fatal" for severity in REQUIRED_RULE_SEVERITIES.values()), 29)
        self.assertNotIn("BSC_CODEX_PUBLIC_GPT_WORKFLOW.md", "\n".join(provenance_paths(profile)))
        instructions = payload[Path("GPT_INSTRUCTIONS.md")]
        instruction_text = instructions.decode("utf-8")
        self.assertLessEqual(len(instruction_text), MAX_GPT_INSTRUCTION_CHARACTERS)
        self.assertIn(f"Profile SHA-256: {hashlib.sha256(PROFILE_PATH.read_bytes()).hexdigest()}".encode(), instructions)
        self.assertTrue(instructions.startswith(b"BSC_CUSTOM_GPT_INSTRUCTIONS_BEGIN\n"))
        self.assertTrue(instructions.endswith(b"BSC_CUSTOM_GPT_INSTRUCTIONS_END\n"))
        for rule in rules:
            marker = "F" if rule["severity"] == "fatal" else "R"
            self.assertEqual(instruction_text.count(f"{marker} {rule['id']}: {rule['text']}"), 1)

    def test_profile_disables_actions_and_preserves_upload_privacy_boundary(self) -> None:
        profile = load_strict_json(PROFILE_PATH)
        self.assertFalse(profile["capabilities"]["actions"]["enabled"])
        self.assertFalse(profile["capabilities"]["apps"]["enabled"])
        instructions = generated_payload()[Path("GPT_INSTRUCTIONS.md")].decode("utf-8")
        self.assertIn("handled through ChatGPT", instructions)
        self.assertIn("local-only property does not apply", instructions)


if __name__ == "__main__":
    unittest.main()
