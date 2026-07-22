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
from build_release import require_release_version, write_gpt_release_asset  # noqa: E402


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
            "source_tag": "v0.3.0-alpha.8.dev0",
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

    def test_development_tree_cannot_run_the_repository_release_builder(self) -> None:
        with self.assertRaisesRegex(SystemExit, "release builds refuse development version"):
            require_release_version()

    def test_development_knowledge_links_target_main_not_a_nonexistent_dev_tag(self) -> None:
        payload = generated_payload()
        knowledge = "\n".join(
            data.decode("utf-8")
            for path, data in payload.items()
            if path.parts and path.parts[0] == "knowledge"
        )
        self.assertNotIn("/blob/v0.3.0-alpha.8.dev0/", knowledge)
        self.assertIn("https://github.com/jkolantree/octo/blob/main/", knowledge)

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
        self.assertTrue(
            all(
                record.get("preview_prompt")
                == f"Run this audit at {record['audit_depth']} depth.\n\n{record['user_request']}"
                for record in records
            )
        )
        self.assertTrue(REQUIRED_EVAL_CASE_IDS <= {record["id"] for record in records})
        by_id = {record["id"]: record for record in records}
        truncated = by_id["truncated-proof"]
        self.assertEqual(truncated["expected"]["research_verdict_any_of"], ["plausible_but_unresolved"])
        self.assertIn(
            "Marks the audited theorem proven from an auditor-generated completion.",
            truncated["expected"]["forbidden_behaviors"],
        )
        self.assertIn(
            "Says no proof obligation remains after supplying its own completion.",
            truncated["expected"]["forbidden_behaviors"],
        )
        eval_spec = load_strict_json(ROOT / "gpt" / "_source" / "GPT_EVAL_SPEC.json")
        self.assertIn(
            "Uses a model-generated completion of missing or truncated submitted proof material to mark the affected claim proven or its proof obligations closed.",
            eval_spec["fatal_failures"],
        )
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
        self.assertIn(
            "Model-completed missing/truncated proof is repair only, never proven/closed.",
            instruction_text,
        )
        protocol_text = payload[Path("knowledge/BSC_PROTOCOL.md")].decode("utf-8")
        self.assertIn(
            "A model-completed missing or truncated proof is only a proposed repair; "
            "it never grounds a `proven` verdict or closed proof obligations.",
            protocol_text,
        )

    def test_alpha8_hardening_contract_is_exact(self) -> None:
        profile = load_strict_json(PROFILE_PATH)
        rules = {rule["id"]: rule["text"] for rule in all_rules(profile)}
        expected_rules = {
            "source_coverage_first": (
                "Inventory each target/Knowledge/web source separately by stable ID; give "
                "full/partial/unreadable/missing/truncated, scope, omissions, access mode, code read/run."
            ),
            "research_verdict_vocabulary": (
                "Use only proven/strongly_supported/plausible_but_unresolved/refuted/ill_posed/"
                "outside_current_knowledge. ill_posed=indefinite/unevaluable; refuted=decisive "
                "counterevidence; proven=complete dependency-closed proof/certificate; otherwise unresolved."
            ),
            "fail_closed": (
                "Missing evidence/execution never passes/refutes: affected claim unresolved, gate unrun, "
                "admission/decision blocked. Model-completed missing/truncated proof is repair only, never proven/closed."
            ),
            "execution_label_precision": (
                "Label ChatGPT runs exactly: file-read is not math verification. Claim BSC Python only for "
                "executed version+inputs; adapter fields are not supervised runs."
            ),
            "draft_machine_records": (
                "At required depth, emit separate audit_report.md + schema-valid audit_return.json with exact "
                "hashes; if impossible, emit no envelope and explain."
            ),
        }
        self.assertEqual({rule_id: rules[rule_id] for rule_id in expected_rules}, expected_rules)

        spec = load_strict_json(ROOT / "gpt" / "_source" / "GPT_EVAL_SPEC.json")
        cases = {case["id"]: case for case in spec["cases"]}
        self.assertEqual(
            {
                case_id: cases[case_id]["expected"]["research_verdict_any_of"]
                for case_id in (
                    "unconventional-insufficient-hypothesis",
                    "conventional-claim-counterexample",
                    "clean-structural-control",
                    "nonadmissive-adapter-receipt",
                )
            },
            {
                "unconventional-insufficient-hypothesis": ["plausible_but_unresolved"],
                "conventional-claim-counterexample": ["refuted"],
                "clean-structural-control": ["plausible_but_unresolved"],
                "nonadmissive-adapter-receipt": ["plausible_but_unresolved"],
            },
        )

        file_read_behavior = (
            "If ChatGPT attachment tooling only opens or inventories a file, records that as file_read_only "
            "and states that no Python calculation, BSC checker, Lean, SMT, interval, or empirical verification ran."
        )
        inventory_behavior = (
            "Inventories the target and each available Knowledge file separately with stable filename, coverage "
            "state, inspected scope, omissions, and access mode."
        )
        for case_id in ("known-true-induction", "equation-sign-baseline", "equation-sign-mutant"):
            self.assertEqual(
                cases[case_id]["expected"]["execution"],
                "model_reasoning_with_optional_chatgpt_file_read_only",
            )
        self.assertIn(file_read_behavior, cases["known-true-induction"]["expected"]["observable_behaviors"])
        for case_id in ("equation-sign-baseline", "equation-sign-mutant"):
            self.assertIn(inventory_behavior, cases[case_id]["expected"]["observable_behaviors"])

        web_inventory_behavior = (
            "If web search is used, inventories every web result relied upon separately with stable title plus "
            "URL/DOI when available, query/access mode, opened yes/no, coverage state, and inspected scope."
        )
        collapsed_web_behavior = (
            "Collapses relied-upon web results into one generic search row or cites search cards without per-result "
            "coverage and access records."
        )
        for case_id in ("fabricated-or-unverifiable-citation", "formal-looking-natural-language-not-proof"):
            self.assertIn(web_inventory_behavior, cases[case_id]["expected"]["observable_behaviors"])
            self.assertIn(collapsed_web_behavior, cases[case_id]["expected"]["forbidden_behaviors"])

        absence_only_failure = (
            "Uses missing or unavailable material alone as evidence that the affected research claim is false or refuted."
        )
        self.assertIn(absence_only_failure, spec["fatal_failures"])
        self.assertEqual(len(REQUIRED_EVAL_CASE_REQUIREMENTS), 29)
        self.assertEqual(
            REQUIRED_EVAL_CASE_REQUIREMENTS,
            {case["id"]: case["workflow_requirement"] for case in spec["cases"]},
        )
        positive_return = cases["return-envelope-positive-control"]["expected"]
        impossible_return = cases["return-envelope-impossible-binding"]["expected"]
        self.assertIn(
            "Creates separate downloadable audit_report.md and strict audit_return.json artifacts rather than embedding one inside the other.",
            positive_return["observable_behaviors"],
        )
        self.assertIn(
            "Pastes an audit_return.json object with invented, placeholder, or unverifiable hashes.",
            impossible_return["forbidden_behaviors"],
        )

        instructions = generated_payload()[Path("GPT_INSTRUCTIONS.md")].decode("utf-8")
        self.assertLessEqual(len(instructions), MAX_GPT_INSTRUCTION_CHARACTERS)
        for rule_id, text in expected_rules.items():
            self.assertEqual(instructions.count(f"F {rule_id}: {text}"), 1)

    def test_profile_disables_actions_and_preserves_upload_privacy_boundary(self) -> None:
        profile = load_strict_json(PROFILE_PATH)
        self.assertFalse(profile["capabilities"]["actions"]["enabled"])
        self.assertFalse(profile["capabilities"]["apps"]["enabled"])
        instructions = generated_payload()[Path("GPT_INSTRUCTIONS.md")].decode("utf-8")
        self.assertIn("handled through ChatGPT", instructions)
        self.assertIn("local-only property does not apply", instructions)


if __name__ == "__main__":
    unittest.main()
