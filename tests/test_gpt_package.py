from __future__ import annotations

import copy
import json
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_gpt_package import (  # noqa: E402
    COMPACT_PREVIEW_CASE_IDS,
    EVAL_GOVERNANCE_SOURCES,
    EXPECTED_CONVERSATION_STARTERS,
    EXPECTED_STARTER_ROUTE_BINDINGS,
    EXPECTED_STARTER_ROUTE_TEXT,
    GPT_ROOT,
    MAX_GPT_INSTRUCTION_CHARACTERS,
    NONADMISSIVE_RECEIPT_RESEARCH_PROJECTION_EXACT,
    OFFICIAL_GPT_URL,
    OPERATING_GPT_INSTRUCTION_CHARACTERS,
    PROFILE_PATH,
    REQUIRED_EVAL_CASE_REQUIREMENTS,
    REQUIRED_EVAL_CASE_IDS,
    REQUIRED_JAPANESE_CRITICAL_EVAL_CASE_IDS,
    REQUIRED_OUTPUT_IDS,
    REQUIRED_RULE_IDS,
    REQUIRED_RULE_SEVERITIES,
    REQUIRED_STATUS_REPRODUCTION_EVAL_CASE_IDS,
    SCIENTIFIC_RESEARCH_PROJECTION_REQUIRED,
    STATUS_ONLY_RESEARCH_PROJECTION_EMPTY,
    all_rules,
    archive_name,
    generated_payload,
    load_strict_json,
    materialize_eval_cases,
    package_files,
    provenance_paths,
    render_instructions,
    render_preview_prompt,
    sha256_bytes,
    validate_evaluation_governance,
    validate_exact_eval_oracles,
    validate_starter_routing,
    verify_archive,
    verify_package,
    write_archive,
    write_package,
)
from build_release import (  # noqa: E402
    PUBLIC_VERSION,
    __version__ as RELEASE_ENGINE_VERSION,
    require_release_version,
    write_gpt_release_asset,
)


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
            "source_tag": "v0.3.0-alpha.10",
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

    def test_final_tree_has_the_exact_release_identity(self) -> None:
        self.assertEqual(RELEASE_ENGINE_VERSION, "0.3.0a10")
        self.assertEqual(PUBLIC_VERSION, "0.3.0-alpha.10")
        self.assertIsNone(require_release_version())

    def test_final_knowledge_links_target_the_exact_release_tag(self) -> None:
        payload = generated_payload()
        knowledge = "\n".join(
            data.decode("utf-8")
            for path, data in payload.items()
            if path.parts and path.parts[0] == "knowledge"
        )
        self.assertNotIn("/blob/v0.3.0-alpha.10.dev1/", knowledge)
        self.assertNotIn("https://github.com/jkolantree/octo/blob/main/", knowledge)
        self.assertIn(
            "https://github.com/jkolantree/octo/blob/v0.3.0-alpha.10/",
            knowledge,
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
        canonical_sources = {item["path"] for item in manifest["canonical_sources"]}
        self.assertTrue(
            {
                "scripts/check_gpt_eval_bundle.py",
                "scripts/check_gpt_eval_suite.py",
                "scripts/gpt_artifact_compiler.py",
                "scripts/gpt_eval_controller.py",
                "tests/test_gpt_artifact_compiler.py",
                "tests/test_gpt_eval_bundle.py",
                "tests/test_gpt_eval_controller.py",
                "tests/test_gpt_eval_suite.py",
            }
            <= canonical_sources
        )
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
        validate_evaluation_governance(records)
        self.assertTrue(records)
        self.assertTrue(all(len(record.get("scoring_criteria", [])) == 10 for record in records))
        for record in records:
            prompt = record["preview_prompt"]
            self.assertEqual(
                prompt,
                render_preview_prompt(
                    record,
                    Path(record["fixture_paths"][0]).name,
                ),
            )
            if (
                record["expected"]["research_projection_requirement"]
                == STATUS_ONLY_RESEARCH_PROJECTION_EMPTY
            ):
                self.assertIn("STATUS-ONLY route:", prompt)
                self.assertIn("status_record_read_only", prompt)
                self.assertIn("exact key=value form", prompt)
                self.assertNotIn("Cover compact audit duties 1-9", prompt)
            elif record["id"] == "known-false-continuity":
                self.assertIn("Use the configured default route", prompt)
                self.assertIn("select and state the configured default", prompt)
                self.assertNotIn("Quick", prompt)
                self.assertNotIn("`quick`", prompt)
                self.assertNotIn("Cover compact audit duties 1-9", prompt)
                self.assertNotIn("Run this audit at standard depth", prompt)
            else:
                self.assertIn("Cover compact audit duties 1-9", prompt)
                self.assertIn("Never reproduce a hash or digest value", prompt)
                self.assertNotIn("STATUS-ONLY route:", prompt)
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
        protocol = load_strict_json(
            ROOT / "gpt" / "_source" / "GPT_FROZEN_EVALUATION_PROTOCOL.json"
        )
        self.assertEqual(
            protocol["protocol_schema"],
            "bsc-gpt-frozen-evaluation/v6",
        )
        for obsolete_key in (
            "regression_trials",
            "prospective_base_trials",
            "high_risk_subset_selected_before_results",
        ):
            self.assertNotIn(obsolete_key, protocol)
        self.assertEqual(
            [
                (
                    item["trial_id"],
                    item["case_number"],
                    item["case_id"],
                    item["counted"],
                )
                for item in protocol["development_preflights"]
            ],
            [
                ("D01", 1, "known-true-induction", False),
                ("D02", 27, "return-envelope-positive-control", False),
            ],
        )
        self.assertEqual(
            protocol["development_preflight_policy"],
            {
                "evidence_classification": (
                    "development_regressions_not_independent_evaluation_evidence"
                ),
                "run_order": "case_1_then_case_27",
                "candidate_defect_repair_allowance": 3,
                "repair_scope": "three_explicitly_authorized_consolidated_root_cause_repairs",
                "regenerate_all_candidate_artifacts": "required",
                "rerun_all_local_gates": "required",
                "restart_preflights": "both_from_case_1",
            },
        )
        self.assertEqual(
            protocol["trial_counts"],
            {
                "development_preflights": 2,
                "counted_regressions_per_complete_suite": 39,
                "maximum_post_suite_root_cause_repairs": 3,
                "maximum_complete_counted_suites": 4,
            },
        )
        self.assertEqual(
            [
                (item["trial_id"], item["case_number"], item["case_id"], item["counted"])
                for item in protocol["counted_regression_trials"]
            ],
            [
                (f"C{number:03d}", number, case_id, True)
                for number, case_id in enumerate(
                    [record["id"] for record in records],
                    start=1,
                )
            ],
        )

    def test_preview_promotion_gate_is_mandatory_per_case(self) -> None:
        payload = generated_payload()
        mandatory_gate = (
            "Promotion or validation requires every case to score at least 18/20 and incur no "
            "automatic failure; never average away a failed case."
        )
        for relative in ("GPT_SETUP_AND_PUBLISHING.md", "evals/GPT_MANUAL_SCORECARD.md"):
            text = payload[Path(relative)].decode("utf-8")
            self.assertIn(mandatory_gate, text, relative)
            self.assertNotIn("Recommended pass", text, relative)
            self.assertNotIn("18/20 is recommended", text, relative)
        setup = payload[Path("GPT_SETUP_AND_PUBLISHING.md")].decode("utf-8")
        readme = payload[Path("README.md")].decode("utf-8")
        for text in (setup, readme):
            self.assertIn("12", text)
            self.assertIn("compact", text.lower())
            self.assertIn("exact immutable tag `v0.3.0-alpha.10`", text)
            self.assertIn("new version and tag", text)
            self.assertIn("freeze", text.lower())
            self.assertIn("historical", text.lower())
            self.assertIn("39", text)
            self.assertNotIn("Case 1 and Case 27", text)
        self.assertIn("artifact-export-disabled-control", setup)
        self.assertIn("no files", setup)
        self.assertIn("complete restart from Case 1", setup)
        self.assertIn("same frozen candidate", setup)
        self.assertIn("normal/default model mode", setup)
        self.assertIn("remove any **Heavy** model-mode selection", setup)
        self.assertIn("separate from the BSC audit depth", setup)
        self.assertIn("ordinary default remains Quick", setup)

    def test_frozen_evaluation_protocol_mutation_fails_closed(self) -> None:
        cases = load_strict_json(
            ROOT / "gpt" / "_source" / "GPT_EVAL_SPEC.json"
        )["cases"]
        protocol = load_strict_json(
            ROOT / "gpt" / "_source" / "GPT_FROZEN_EVALUATION_PROTOCOL.json"
        )
        mutations = []

        score_weakened = copy.deepcopy(protocol)
        score_weakened["pass_criteria"]["minimum_score_each_counted_trial"] = 17
        mutations.append(("score", score_weakened))

        counted_case_dropped = copy.deepcopy(protocol)
        counted_case_dropped["counted_regression_trials"].pop()
        mutations.append(("counted_case", counted_case_dropped))

        candidate_changed_on_retry = copy.deepcopy(protocol)
        candidate_changed_on_retry["invalid_controller_retry"][
            "same_frozen_candidate_required"
        ] = False
        mutations.append(("retry_candidate", candidate_changed_on_retry))

        candidate_failure_reclassified = copy.deepcopy(protocol)
        candidate_failure_reclassified["invalid_controller_retry"][
            "candidate_failed_retry_as_controller_invalid"
        ] = "allowed"
        mutations.append(("candidate_failure", candidate_failure_reclassified))

        transport_identity_claimed = copy.deepcopy(protocol)
        transport_identity_claimed["artifact_transport"][
            "download_button_identity_from_base64"
        ] = "allowed"
        mutations.append(("transport_identity", transport_identity_claimed))

        cross_turn_path_allowed = copy.deepcopy(protocol)
        cross_turn_path_allowed["artifact_transport"][
            "cross_turn_filesystem_path_dependency"
        ] = "allowed"
        mutations.append(("cross_turn_path", cross_turn_path_allowed))

        with tempfile.TemporaryDirectory(prefix="bsc-gpt-governance-") as directory:
            for name, mutated_protocol in mutations:
                with self.subTest(name=name):
                    mutated_path = Path(directory) / f"{name}.json"
                    mutated_path.write_text(
                        json.dumps(mutated_protocol, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    with patch.dict(
                        EVAL_GOVERNANCE_SOURCES,
                        {
                            "evals/GPT_FROZEN_EVALUATION_PROTOCOL.json": str(
                                mutated_path
                            )
                        },
                    ):
                        with self.assertRaisesRegex(ValueError, "gate weakened"):
                            validate_evaluation_governance(cases)

    def test_evaluation_governance_records_preserve_r01_boundaries(self) -> None:
        cases = load_strict_json(
            ROOT / "gpt" / "_source" / "GPT_EVAL_SPEC.json"
        )["cases"]
        provenance_key = "evals/GPT_EVAL_PROVENANCE.md"
        provenance = (
            ROOT / EVAL_GOVERNANCE_SOURCES[provenance_key]
        ).read_text(encoding="utf-8")
        matrix_key = "evals/GPT_INVARIANT_ENFORCEMENT_MATRIX.md"
        matrix = (
            ROOT / EVAL_GOVERNANCE_SOURCES[matrix_key]
        ).read_text(encoding="utf-8")
        mutations = (
            (
                "candidate_failure",
                provenance_key,
                provenance.replace(
                    "`candidate_failed`",
                    "`candidate_neutral`",
                    1,
                ),
                "R01",
            ),
            (
                "runtime_replication",
                matrix_key,
                matrix.replace(
                    "one bound execution-output artifact",
                    "three manually replicated runtime literals",
                    1,
                ),
                "controller or R01",
            ),
        )
        with tempfile.TemporaryDirectory(prefix="bsc-gpt-governance-record-") as directory:
            for name, source_key, mutated_text, expected_error in mutations:
                with self.subTest(name=name):
                    mutated_path = Path(directory) / f"{name}.md"
                    mutated_path.write_text(mutated_text, encoding="utf-8")
                    with patch.dict(
                        EVAL_GOVERNANCE_SOURCES,
                        {source_key: str(mutated_path)},
                    ):
                        with self.assertRaisesRegex(ValueError, expected_error):
                            validate_evaluation_governance(cases)

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
        self.assertEqual(len(REQUIRED_RULE_IDS), 40)
        self.assertEqual(sum(severity == "fatal" for severity in REQUIRED_RULE_SEVERITIES.values()), 31)
        self.assertNotIn("BSC_CODEX_PUBLIC_GPT_WORKFLOW.md", "\n".join(provenance_paths(profile)))
        instructions = payload[Path("GPT_INSTRUCTIONS.md")]
        instruction_text = instructions.decode("utf-8")
        self.assertLessEqual(
            len(instruction_text),
            OPERATING_GPT_INSTRUCTION_CHARACTERS,
        )
        self.assertEqual(
            OPERATING_GPT_INSTRUCTION_CHARACTERS,
            MAX_GPT_INSTRUCTION_CHARACTERS * 3 // 4,
        )
        self.assertNotIn("Profile SHA-256:", instruction_text)
        self.assertIsNone(
            re.search(
                r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{64}(?![0-9A-Fa-f])",
                instruction_text,
            )
        )
        self.assertTrue(instructions.startswith(b"BSC_BEGIN\n"))
        self.assertTrue(instructions.endswith(b"BSC_END"))
        for fixed_contract_line in (
            "K missing=>unavailable;blocks affected pass/proven/run.",
            "PUBLIC:visible human audit;never compute/emit/copy/quote "
            "hash/digest values.",
            "FATAL(all depths):",
            "REQUIRED(all depths):",
        ):
            self.assertIn(fixed_contract_line, instruction_text)
        instruction_lines = instruction_text.splitlines()
        for rule in rules:
            marker = "F" if rule["severity"] == "fatal" else "R"
            self.assertEqual(instruction_lines.count(rule["text"]), 1)
            self.assertNotIn(f"{marker}:{rule['id']}:", instruction_text)
        self.assertIn(
            "Missing/truncated proof=>THEOREM PBU; never true/no-counterexample/proven; completion=repair.",
            instruction_text,
        )
        protocol_text = payload[Path("knowledge/BSC_PROTOCOL.md")].decode("utf-8")
        self.assertIn(
            "A model-completed missing or truncated proof is only a proposed repair; "
            "it never grounds a `proven` verdict or closed proof obligations.",
            protocol_text,
        )
        self.assertIn("If no depth is requested, use `quick`.", protocol_text)
        self.assertIn(
            "For `quick`, use at most 250 words and four visible blocks, with no table "
            "unless one is materially necessary.",
            protocol_text,
        )
        self.assertIn(
            "The default `quick` route does not use this nine-duty template; it uses at "
            "most four visible blocks",
            protocol_text,
        )
        self.assertNotIn("If no depth is requested, use `standard`.", protocol_text)
        self.assertNotIn("Including tables, use at most 300 words for `quick`", protocol_text)
        self.assertIn(
            "Requested language; preserve exact non-hash canonical tokens and URLs; "
            "label translations. Hash-value ban overrides.",
            instruction_text,
        )
        japanese_knowledge = payload[Path("knowledge/BSC_JAPANESE_INTERFACE.md")].decode("utf-8")
        for token in (
            "LIVE",
            "REPRODUCIBLE_SOURCE_AND_UPDATE_CANDIDATE",
            "PENDING",
            "PENDING_VERIFICATION",
            "VERIFIED",
        ):
            self.assertIn(token, japanese_knowledge)
        self.assertIn("正規トークン", japanese_knowledge)
        self.assertNotIn("Return Desk", japanese_knowledge)
        self.assertNotIn("| `inconsistent` |", japanese_knowledge)
        self.assertNotIn(
            Path("knowledge/BSC_EXECUTION_AND_RECEIPTS.md"),
            payload,
        )
        self.assertEqual(
            [
                path.name
                for path in payload
                if path.parts and path.parts[0] == "knowledge"
            ],
            [
                "BSC_PROTOCOL.md",
                "BSC_STATUS_AND_EVIDENCE_MODEL.md",
                "BSC_SUPPORTED_CHECKS.md",
                "BSC_WORKED_EXAMPLES.md",
                "BSC_JAPANESE_INTERFACE.md",
            ],
        )
        self.assertIn(
            "never compute/emit/copy/quote hash/digest values",
            instruction_text,
        )
        self.assertIn("Intake<=40 words", instruction_text)
        self.assertIn("Follow-up<=120", instruction_text)
        self.assertIn("Quick<=250 words", instruction_text)
        for literal, _marker in EXPECTED_STARTER_ROUTE_BINDINGS:
            self.assertEqual(instruction_text.count(literal), 1)
        self.assertIn(EXPECTED_STARTER_ROUTE_TEXT, instruction_text)
        self.assertIn("I=ask only 1-sentence same-language claim", instruction_text)
        self.assertIn("E=one brief Quick example", instruction_text)
        self.assertIn("No claim:example=>E;else I", instruction_text)
        self.assertIn("else Quick", instruction_text)
        self.assertIn("Deep=Standard/Adversarial", instruction_text)
        self.assertIn("Formal=formal-mathematical", instruction_text)
        self.assertIn("Standard<=650", instruction_text)
        self.assertIn("Adversarial/Formal<=1000", instruction_text)
        self.assertNotIn("\n1:Source coverage\n", instruction_text)
        durable_knowledge = "\n".join(
            data.decode("utf-8")
            for path, data in payload.items()
            if path.parts and path.parts[0] == "knowledge"
        ).lower()
        for assertion in (
            "the official custom gpt is live",
            ") is live. a repository package",
            "official custom gpt は live",
            "は公開されています。通常の利用者",
            "公式 gpt はすでに利用できます",
        ):
            self.assertNotIn(assertion, durable_knowledge)

    def test_alpha8_hardening_contract_is_exact(self) -> None:
        profile = load_strict_json(PROFILE_PATH)
        rules = {rule["id"]: rule["text"] for rule in all_rules(profile)}
        expected_rules = {
            "source_coverage_first": (
                "Quick: verdict first, then one-line basis; no table unless source coverage affects the verdict. "
                "Deep/Formal: source table ID|source|access|coverage|omissions|code_read/run; include relied-on "
                "pages. Missing stays missing. Knowledge=method, never case evidence/full inspection."
            ),
            "separate_status_axes": (
                "STATUS-ONLY FIRST: official service/package/candidate/binding/Preview overrides duties => output "
                "status_record_read_only and each supplied canonical key=value exactly; requested language; stop. "
                "No research IDs/claims/verdicts/gates/admission or invented states. Other status: no research "
                "verdict; CLI only if BSC ran."
            ),
            "research_verdict_vocabulary": (
                "Verdicts=proven/strongly_supported/plausible_but_unresolved/refuted/ill_posed/"
                "outside_current_knowledge only. Missing=>PBU; closed exact proof=>proven without author work; "
                "ill_posed=undefined; refuted=disproof."
            ),
            "fail_closed": (
                "Missing evidence/execution: unresolved, no pass/refute, gates unrun. Missing/truncated proof=>"
                "THEOREM PBU; never true/no-counterexample/proven; completion=repair. Exact countertrace refutes "
                "universal; replay unrun."
            ),
            "independent_fatal_gates": (
                "Gates independent; admission iff all fatal gates pass; unrun/fail/conflict blocks; no score "
                "rescue. Proven/strong claim/lemma=>evidence-derived pass gate, else demote/omit."
            ),
            "execution_label_precision": (
                "Unsupported claimed runs stay reported_but_unverified, with current execution not_run. Do not "
                "create research claim IDs or verdicts for execution status; keep dependent T "
                "plausible_but_unresolved."
            ),
            "future_execution_projection": (
                "A proposed calculation and its empirical test are not executed results. State both not_run, "
                "keep dependent gates unrun and T plausible_but_unresolved, and name the smallest missing inputs, "
                "method, and output. No fixed-row matrix."
            ),
            "citations_must_be_checked": (
                "Snippets/cards=discovery; open+ledger each used page."
            ),
            "response_language_and_canonical_tokens": (
                "Requested language; preserve exact non-hash canonical tokens and URLs; label translations. "
                "Hash-value ban overrides."
            ),
            "compact_no_machine_records": (
                "PUBLIC: no files/downloads/machine records/compiler/stdout/Base64/shards/transport/Section10; "
                "say \"digest supplied\". Export disabled; refer to supervised local engine/Return Desk. Quick/"
                "Intake/Follow-up override Knowledge full-report/ledger templates; nine duties=Deep/Formal only."
            ),
            "execution_ledger": (
                "Compact execution disclosure: mention only activities used, claimed, or decisive; distinguish "
                "reasoning, web, independent checks, Data Analysis, BSC Python, formal tools, empirical tests, "
                "and proposed computations. `ran` needs an inspectable result; unsupported "
                "reports=reported_but_unverified; unexecuted BSC/formal/empirical work=not_run, never "
                "not_applicable. Separate file_read_only from checking. No fixed-row matrix or ledger file."
            ),
            "nonadmissive_receipts": (
                "Receipt-only: sole research T=plausible_but_unresolved; no authorization/tool-run IDs, type/"
                "evidence rows, conclusions, extra verdicts. Authorization only decision/gate; no A claim."
            ),
            "closing_disclosure": (
                "Quick: Bottom line|Why|Weakest point|Best next check; add one short method/omissions note only if "
                "material. Intake stops after question; Follow-up answers delta. Deep/Formal covers nine duties "
                "within budget with compact source/execution disclosures."
            ),
            "public_research_preview": (
                "Verdict first; beginner-first; no boilerplate. Intake<=40 words; Follow-up<=120; Quick<=250 "
                "words and <=4 short blocks; Standard<=650; Adversarial/Formal<=1000. Quick uses <=3 decisive "
                "findings and no tables/internal IDs/gates unless material. Expand only if asked; sources/proofs/"
                "evidence may err."
            ),
        }
        self.assertEqual(all_rules(profile)[0]["id"], "separate_status_axes")
        self.assertEqual({rule_id: rules[rule_id] for rule_id in expected_rules}, expected_rules)
        self.assertEqual(
            next(
                depth["builder_instruction"]
                for depth in profile["audit_depths"]
                if depth["id"] == "formal-mathematical"
            ),
            "Visible: exact objects/quantifiers/hypotheses/conclusion; every proof step/obligation; certificate/"
            "tool limits.",
        )
        instruction_length = len(
            generated_payload()[Path("GPT_INSTRUCTIONS.md")].decode("utf-8")
        )
        self.assertLessEqual(
            instruction_length,
            OPERATING_GPT_INSTRUCTION_CHARACTERS,
        )
        self.assertGreaterEqual(
            MAX_GPT_INSTRUCTION_CHARACTERS - instruction_length,
            MAX_GPT_INSTRUCTION_CHARACTERS // 4,
        )

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
        self.assertEqual(
            {
                case_id: cases[case_id]["expected"]["research_verdict_any_of"]
                for case_id in (
                    "return-envelope-impossible-binding",
                    "ja-return-envelope-impossible-binding",
                    "exact-quotient-without-test",
                )
            },
            {
                "return-envelope-impossible-binding": ["plausible_but_unresolved"],
                "ja-return-envelope-impossible-binding": ["plausible_but_unresolved"],
                "exact-quotient-without-test": ["ill_posed"],
            },
        )

        receipt_only = cases["nonadmissive-adapter-receipt"]["expected"]
        self.assertEqual(
            receipt_only["research_projection_exact"],
            NONADMISSIVE_RECEIPT_RESEARCH_PROJECTION_EXACT,
        )
        generated_cases = {
            case["id"]: case
            for case in (
                json.loads(line)
                for line in generated_payload()[Path("evals/GPT_EVAL_CASES.jsonl")]
                .decode("utf-8")
                .splitlines()
            )
        }
        default_quick_prompt = generated_cases["known-false-continuity"][
            "preview_prompt"
        ]
        self.assertIn("Use the configured default route", default_quick_prompt)
        self.assertIn(
            "select and state the configured default",
            default_quick_prompt,
        )
        self.assertNotIn("Quick", default_quick_prompt)
        self.assertNotIn("`quick`", default_quick_prompt)
        self.assertNotIn("Cover compact audit duties 1-9", default_quick_prompt)
        self.assertNotIn("Run this audit at standard depth", default_quick_prompt)
        self.assertNotIn("Run this audit at quick depth", default_quick_prompt)
        expectations = generated_payload()[
            Path("evals/GPT_EVAL_EXPECTATIONS.md")
        ].decode("utf-8")
        self.assertIn(
            "**Current compact-gate route:** configured default Quick",
            expectations,
        )
        self.assertEqual(
            generated_cases["nonadmissive-adapter-receipt"]["expected"][
                "research_projection_exact"
            ],
            NONADMISSIVE_RECEIPT_RESEARCH_PROJECTION_EXACT,
        )
        mutated_cases = copy.deepcopy(spec["cases"])
        mutated_receipt = next(
            case
            for case in mutated_cases
            if case["id"] == "nonadmissive-adapter-receipt"
        )
        mutated_receipt["expected"]["research_projection_exact"][
            "allow_additional_primary_claims"
        ] = True
        with self.assertRaisesRegex(ValueError, "sole-T unresolved oracle"):
            validate_exact_eval_oracles(mutated_cases)
        self.assertIn(
            "Keeps T as the sole primary research claim and emits exactly one primary verdict, "
            "plausible_but_unresolved; receipt non-admissibility belongs only on evidence, execution, and "
            "gate axes.",
            receipt_only["observable_behaviors"],
        )
        self.assertIn(
            "Creates a receipt-authorization or policy claim as a primary research claim, or emits any extra "
            "refuted or ill_posed research verdict from the receipt defect.",
            receipt_only["forbidden_behaviors"],
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
        self.assertEqual(len(REQUIRED_EVAL_CASE_REQUIREMENTS), 39)
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
            "Keeps request and target source as byte-distinct artifacts; if their bytes are identical, emits no envelope until a distinct exact request artifact exists, and never duplicates one digest across roles.",
            positive_return["observable_behaviors"],
        )
        self.assertIn(
            "Never binds a sources entry directly to a request or report artifact; excludes it or supplies a distinct role-source artifact ID.",
            positive_return["observable_behaviors"],
        )
        self.assertIn(
            "Binds each verified proof-evidence record to a downloadable role-evidence artifact and to an execution activity that declares that evidence artifact as output, never to a role-source artifact alone.",
            positive_return["observable_behaviors"],
        )
        self.assertIn(
            "Records ChatGPT Data Analysis as ran when it writes files, computes hashes, or declares output_artifact_ids; file_read_only declares no outputs.",
            positive_return["observable_behaviors"],
        )
        self.assertIn(
            "Requires every proven or strongly_supported claim, including lemmas, to bind at least one fatal gate that derives pass from complete evidence.",
            positive_return["observable_behaviors"],
        )
        self.assertIn(
            "Projects exactly every declared fatal gate into summary_projection.fatal_gate_ids.",
            positive_return["observable_behaviors"],
        )
        self.assertIn(
            "Omits a lemma claim rather than recording it proven without an evidence-derived passing fatal gate.",
            positive_return["observable_behaviors"],
        )
        self.assertIn(
            "Records any non-model ran activity with hash-matched input and verified output or admissible receipt plus an exact observed nonempty tool and version; otherwise no pass or proven promotion.",
            positive_return["observable_behaviors"],
        )
        self.assertIn(
            "Binds the request and every locally available source for the evidence claims as inputs to each evidence-cited execution.",
            positive_return["observable_behaviors"],
        )
        self.assertIn(
            "Claims schema or semantic validation ran without a bound versioned validator output.",
            positive_return["forbidden_behaviors"],
        )
        self.assertIn(
            "Executes the canonical compiler, which reads its own full sys.version once whenever Data Analysis "
            "writes or hashes files and rejects any model-authored runtime override, then deterministically "
            "creates exactly one chatgpt_data_analysis_output.txt role-execution_output using the v2 header, "
            "one runtime line, one session-reported provenance line, and filename-sorted "
            "`sha256  bytes  filename` rows derived from every earlier-frozen non-request/source output but "
            "never itself or audit_return.json.",
            positive_return["observable_behaviors"],
        )
        self.assertIn(
            "Projects that one captured value into the structured execution.version field, labels it "
            "session-reported rather than independently authenticated, and makes the visible report reference "
            "chatgpt_data_analysis_output.txt or its artifact ID instead of manually reproducing the runtime "
            "literal.",
            positive_return["observable_behaviors"],
        )
        self.assertNotIn(
            "Prints one identical literal full sys.version in chatgpt_data_analysis_output.txt, the visible "
            "execution ledger, and audit_return.json; a file or receipt reference never substitutes.",
            positive_return["observable_behaviors"],
        )
        self.assertIn(
            "Leaves schema and semantic validation unvalidated or not_run unless a bound versioned validator-output artifact records the check.",
            positive_return["observable_behaviors"],
        )
        self.assertIn(
            "Emits prohibited ASCII control bytes in generated text artifacts or interprets a literal LaTeX backslash as a string escape.",
            positive_return["forbidden_behaviors"],
        )
        self.assertIn(
            "After the last write of every artifacts[] file, re-reads the final downloadable bytes, derives every "
            "hash and size from those final bytes, freezes the file, and serializes audit_return.json only after "
            "all referenced artifacts are final.",
            positive_return["observable_behaviors"],
        )
        self.assertIn(
            "Asks model-authored prose to independently reproduce a hash, byte count, Base64 payload, or full "
            "runtime string.",
            positive_return["forbidden_behaviors"],
        )
        self.assertIn(
            "Claims an optional Base64 export proves identity with unavailable download-button bytes or calls "
            "unavailable original bytes corrupt.",
            positive_return["forbidden_behaviors"],
        )
        self.assertIn(
            "Records every unexecuted BSC, external-proof, and empirical activity as not_run, never "
            "not_applicable.",
            positive_return["observable_behaviors"],
        )
        self.assertIn(
            "Binds a pre-final artifact digest, changes an artifacts[] file after hashing, or retains pass or "
            "proven after a byte-hash mismatch.",
            positive_return["forbidden_behaviors"],
        )
        self.assertIn(
            "Marks an unexecuted empirical activity not_applicable.",
            positive_return["forbidden_behaviors"],
        )
        self.assertIn(
            "Records Data Analysis as ran after writes or hashes without binding every generated output except the request and return, including chatgpt_data_analysis_output.txt.",
            positive_return["forbidden_behaviors"],
        )
        self.assertIn(
            "Uses a role-source target or Knowledge file as the verified proof-evidence artifact for a proven claim.",
            positive_return["forbidden_behaviors"],
        )
        self.assertIn(
            "Pastes an audit_return.json object with invented, placeholder, or unverifiable hashes.",
            impossible_return["forbidden_behaviors"],
        )

        self.assertEqual(len(REQUIRED_JAPANESE_CRITICAL_EVAL_CASE_IDS), 8)
        for case_id in REQUIRED_JAPANESE_CRITICAL_EVAL_CASE_IDS:
            case = cases[case_id]
            self.assertRegex(case["user_request"] + case["fixture"]["inline_text"], r"[\u3040-\u30ff\u3400-\u9fff]")
            expected_text = json.dumps(case["expected"], ensure_ascii=False).lower()
            self.assertIn("japanese", expected_text)
            self.assertIn("canonical", expected_text)
        self.assertEqual(
            REQUIRED_STATUS_REPRODUCTION_EVAL_CASE_IDS,
            {"official-service-status-separation", "official-first-reproduction-route"},
        )
        for case_id in REQUIRED_STATUS_REPRODUCTION_EVAL_CASE_IDS:
            case = cases[case_id]
            self.assertRegex(case["user_request"], r"[\u3040-\u30ff\u3400-\u9fff]")
            expected_text = json.dumps(case["expected"], ensure_ascii=False)
            self.assertIn(OFFICIAL_GPT_URL, expected_text)
            self.assertIn("PENDING", expected_text)
            self.assertIn("japanese", expected_text.lower())
            self.assertIn("canonical", expected_text.lower())
            self.assertIn("Answers only in English", expected_text)
            self.assertEqual(
                case["expected"]["research_projection_requirement"],
                STATUS_ONLY_RESEARCH_PROJECTION_EMPTY,
            )
            self.assertNotIn("research_verdict_any_of", case["expected"])
            self.assertNotIn("research_projection_exact", case["expected"])

        generated_cases = {
            case["id"]: case
            for case in (
                json.loads(line)
                for line in generated_payload()[Path("evals/GPT_EVAL_CASES.jsonl")]
                .decode("utf-8")
                .splitlines()
            )
        }
        self.assertEqual(len(generated_cases), 39)
        self.assertEqual(
            {
                case_id
                for case_id, case in generated_cases.items()
                if case["expected"]["research_projection_requirement"]
                == STATUS_ONLY_RESEARCH_PROJECTION_EMPTY
            },
            REQUIRED_STATUS_REPRODUCTION_EVAL_CASE_IDS,
        )
        self.assertTrue(
            all(
                case["expected"]["research_projection_requirement"]
                in {
                    SCIENTIFIC_RESEARCH_PROJECTION_REQUIRED,
                    STATUS_ONLY_RESEARCH_PROJECTION_EMPTY,
                }
                for case in generated_cases.values()
            )
        )
        instructions = generated_payload()[Path("GPT_INSTRUCTIONS.md")].decode("utf-8")
        self.assertLessEqual(
            len(instructions),
            OPERATING_GPT_INSTRUCTION_CHARACTERS,
        )
        self.assertFalse(instructions.endswith("\n"))
        for rule_id, text in expected_rules.items():
            self.assertEqual(instructions.splitlines().count(text), 1)

    def test_instruction_operating_cap_is_fail_closed(self) -> None:
        profile = load_strict_json(PROFILE_PATH)
        mutated = copy.deepcopy(profile)
        route_rule = next(
            rule
            for rule in all_rules(mutated)
            if rule["id"] == "declare_audit_depth"
        )
        route_rule["text"] += " x" * OPERATING_GPT_INSTRUCTION_CHARACTERS
        with self.assertRaisesRegex(
            ValueError,
            "75-percent operating cap",
        ):
            render_instructions(mutated)

    def test_exact_starter_routes_precede_generic_intent_routing(self) -> None:
        profile = load_strict_json(PROFILE_PATH)
        starters = profile["product"]["conversation_starters"]
        route_text = next(
            rule["text"]
            for rule in all_rules(profile)
            if rule["id"] == "declare_audit_depth"
        )
        self.assertEqual(tuple(starters), EXPECTED_CONVERSATION_STARTERS)
        self.assertEqual(validate_starter_routing(starters, route_text), [])
        generated = generated_payload()[Path("GPT_INSTRUCTIONS.md")].decode("utf-8")
        self.assertIn(EXPECTED_STARTER_ROUTE_TEXT, generated)
        for literal, _marker in EXPECTED_STARTER_ROUTE_BINDINGS:
            self.assertEqual(generated.count(literal), 1)

    def test_starter_route_validator_rejects_drift_and_remapping(self) -> None:
        route_text = EXPECTED_STARTER_ROUTE_TEXT
        self.assertEqual(
            validate_starter_routing(list(EXPECTED_CONVERSATION_STARTERS), route_text),
            [],
        )
        for mutated_starters in (
            list(reversed(EXPECTED_CONVERSATION_STARTERS)),
            list(EXPECTED_CONVERSATION_STARTERS[:-1]),
            [
                EXPECTED_CONVERSATION_STARTERS[0],
                EXPECTED_CONVERSATION_STARTERS[0],
                *EXPECTED_CONVERSATION_STARTERS[2:],
            ],
        ):
            with self.subTest(starters=mutated_starters):
                self.assertTrue(
                    validate_starter_routing(mutated_starters, route_text)
                )
        self.assertTrue(
            validate_starter_routing(
                list(EXPECTED_CONVERSATION_STARTERS),
                route_text + ";60秒で主張を点検する=>E",
            )
        )
        self.assertTrue(
            validate_starter_routing(
                list(EXPECTED_CONVERSATION_STARTERS),
                route_text.replace(
                    "Formal=formal-mathematical;both only if asked/Quick misleading.",
                    "Formal=formal-mathematical.",
                ),
            )
        )

    def test_research_projection_oracle_cannot_reclassify_scientific_cases(self) -> None:
        spec = load_strict_json(ROOT / "gpt" / "_source" / "GPT_EVAL_SPEC.json")

        scientific_without_verdict = copy.deepcopy(spec["cases"])
        scientific = next(
            case
            for case in scientific_without_verdict
            if case["id"] == "known-true-induction"
        )
        scientific["expected"].pop("research_verdict_any_of")
        with self.assertRaisesRegex(ValueError, "nonempty unique verdict oracle"):
            validate_exact_eval_oracles(scientific_without_verdict)

        scientific_as_status = copy.deepcopy(spec["cases"])
        scientific = next(
            case for case in scientific_as_status if case["id"] == "known-true-induction"
        )
        scientific["expected"]["research_projection_requirement"] = (
            STATUS_ONLY_RESEARCH_PROJECTION_EMPTY
        )
        scientific["expected"].pop("research_verdict_any_of")
        scientific["expected"]["execution"] = "status_record_read_only"
        with self.assertRaisesRegex(ValueError, "reviewed official-state pair"):
            validate_exact_eval_oracles(scientific_as_status)

        scientific_status_execution = copy.deepcopy(spec["cases"])
        next(
            case
            for case in scientific_status_execution
            if case["id"] == "known-true-induction"
        )["expected"]["execution"] = "status_record_read_only"
        with self.assertRaisesRegex(ValueError, "non-status execution mode"):
            validate_exact_eval_oracles(scientific_status_execution)

    def test_status_only_projection_oracle_rejects_scientific_fields_and_unknown_modes(
        self,
    ) -> None:
        spec = load_strict_json(ROOT / "gpt" / "_source" / "GPT_EVAL_SPEC.json")
        for field, value in (
            ("research_verdict_any_of", ["plausible_but_unresolved"]),
            (
                "research_projection_exact",
                {
                    "primary_claim_ids": ["T"],
                    "verdicts_by_claim": {"T": "plausible_but_unresolved"},
                    "allow_additional_primary_claims": False,
                },
            ),
        ):
            with self.subTest(field=field):
                cases = copy.deepcopy(spec["cases"])
                status_case = next(
                    case
                    for case in cases
                    if case["id"] == "official-service-status-separation"
                )
                status_case["expected"][field] = value
                with self.assertRaisesRegex(
                    ValueError,
                    "must be a status-record read and must not carry",
                ):
                    validate_exact_eval_oracles(cases)

        unknown = copy.deepcopy(spec["cases"])
        next(
            case for case in unknown if case["id"] == "known-true-induction"
        )["expected"]["research_projection_requirement"] = "unknown"
        with self.assertRaisesRegex(ValueError, "unknown research projection requirement"):
            validate_exact_eval_oracles(unknown)

    def test_profile_disables_actions_and_preserves_upload_privacy_boundary(self) -> None:
        profile = load_strict_json(PROFILE_PATH)
        self.assertFalse(profile["capabilities"]["actions"]["enabled"])
        self.assertFalse(profile["capabilities"]["apps"]["enabled"])
        instructions = generated_payload()[Path("GPT_INSTRUCTIONS.md")].decode("utf-8")
        self.assertIn("Packet Builder local-only excludes GPT uploads", instructions)
        self.assertIn("ChatGPT settings/terms apply", instructions)

    def test_compact_profile_disables_public_machine_record_path(self) -> None:
        profile = load_strict_json(PROFILE_PATH)
        payload = generated_payload()
        instructions = payload[Path("GPT_INSTRUCTIONS.md")].decode("utf-8")

        self.assertTrue(
            all(depth["machine_record_required"] is False for depth in profile["audit_depths"])
        )
        self.assertEqual(
            [section["id"] for section in profile["output_sections"]],
            list(REQUIRED_OUTPUT_IDS),
        )
        self.assertEqual(len(REQUIRED_OUTPUT_IDS), 9)
        self.assertNotIn("machine_readable_record", REQUIRED_OUTPUT_IDS)
        self.assertNotIn(Path("knowledge/BSC_EXECUTION_AND_RECEIPTS.md"), payload)
        self.assertIn(
            "PUBLIC: no files/downloads/machine records/compiler/stdout/",
            instructions,
        )
        self.assertIn("visible human audit", instructions)
        self.assertIn(
            "no files/downloads/machine records/compiler/stdout/Base64/shards/"
            "transport/Section10",
            instructions,
        )
        self.assertIn(
            "never compute/emit/copy/quote hash/digest values",
            instructions,
        )
        self.assertNotIn("last2 need machine record", instructions)
        self.assertNotIn("Final=exact v9 stdout", instructions)

        metadata = payload[Path("GPT_PUBLIC_METADATA.md")].decode("utf-8")
        setup = payload[Path("GPT_SETUP_AND_PUBLISHING.md")].decode("utf-8")
        readme = payload[Path("README.md")].decode("utf-8")
        for text in (metadata, setup, readme):
            self.assertIn("compact", text.lower())
            self.assertIn("standalone tooling", text)
        self.assertIn("historical and superseded", setup)
        self.assertIn("These 12 cases, not the historical 39-case suite", setup)
        self.assertIn(
            "do not collapse those states or claim that the compact profile passed",
            setup,
        )

    def test_official_service_candidate_and_bilingual_metadata_are_separate(self) -> None:
        profile = load_strict_json(PROFILE_PATH)
        product = profile["product"]
        self.assertEqual(product["service_availability"], "LIVE")
        self.assertEqual(product["public_url"], OFFICIAL_GPT_URL)
        self.assertEqual(product["package_role"], "REPRODUCIBLE_SOURCE_AND_UPDATE_CANDIDATE")
        self.assertEqual(product["candidate_state"], "PENDING")
        self.assertEqual(product["live_binding_state"], "PENDING_VERIFICATION")
        self.assertEqual(product["preview_validation_state"], "PENDING")
        self.assertEqual(product["preview_gate_case_count"], 12)
        self.assertEqual(
            tuple(product["preview_gate_case_ids"]),
            COMPACT_PREVIEW_CASE_IDS,
        )
        self.assertEqual(
            product["historical_evaluation_suite_status"],
            "SUPERSEDED_ARTIFACT_PROFILE_39_CASES",
        )
        self.assertEqual(product["japanese_interface_status"], "BETA")
        self.assertEqual(product["japanese_native_speaker_terminology_review"], "PENDING")
        starters = product["conversation_starters"]
        self.assertEqual(
            starters,
            [
                "Start a 60-second claim audit",
                "60秒で主張を点検する",
                "Show a simple example first",
                "まず簡単な例を見る",
            ],
        )
        self.assertEqual(
            [
                bool(re.search(r"[\u3040-\u30ff\u3400-\u9fff]", item))
                for item in starters
            ],
            [False, True] * 2,
        )
        self.assertTrue(all(0 < len(item) <= 32 for item in starters))
        self.assertFalse(
            any(
                re.search(
                    r"(?:attachment|attached|upload|file|添付|ファイル)",
                    item,
                    re.IGNORECASE,
                )
                for item in starters
            )
        )
        self.assertRegex(product["description"], r"[A-Za-z]")
        self.assertRegex(product["description"], r"[\u3040-\u30ff\u3400-\u9fff]")
        self.assertLessEqual(len(product["description"]), 200)
        self.assertIn("日本語対応はベータ版", product["description"])
        self.assertEqual(
            product["japanese_native_speaker_terminology_review"],
            "PENDING",
        )

        payload = generated_payload()
        rendered_starters = payload[Path("GPT_CONVERSATION_STARTERS.md")].decode("utf-8")
        self.assertEqual(
            re.findall(r"```text\n([^\n]+)\n```", rendered_starters),
            starters,
        )
        self.assertEqual(rendered_starters.count("## Starter "), 4)
        setup = payload[Path("GPT_SETUP_AND_PUBLISHING.md")].decode("utf-8")
        self.assertIn("Copy the 4 prompts", setup)
        public_text = "\n".join(
            data.decode("utf-8")
            for path, data in payload.items()
            if path.suffix.lower() in {".md", ".txt", ".json", ".jsonl"}
        )
        self.assertNotIn("UNPUBLISHED", public_text)
        self.assertNotIn("first public release", public_text.lower())
        metadata = payload[Path("GPT_PUBLIC_METADATA.md")].decode("utf-8")
        self.assertIn(OFFICIAL_GPT_URL, metadata)
        self.assertIn("candidate state:** `pending`", metadata.lower())
        self.assertIn("**Japanese interface:** `BETA`", metadata)
        self.assertIn("native-speaker terminology review `PENDING`", metadata)
        setup = payload[Path("GPT_SETUP_AND_PUBLISHING.md")].decode("utf-8")
        self.assertIn("**Japanese interface:** `BETA`", setup)
        self.assertIn("Preserve this disclosure in the public Description", setup)
        self.assertIn(
            "Copy the 4 prompts from `GPT_CONVERSATION_STARTERS.md`",
            setup,
        )
        rendered_starters = payload[Path("GPT_CONVERSATION_STARTERS.md")].decode(
            "utf-8"
        )
        self.assertEqual(rendered_starters.count("## Starter "), 4)
        manifest = json.loads(payload[Path("GPT_RELEASE_MANIFEST.json")])
        self.assertEqual(manifest["official_service_and_candidate_state"]["public_url"], OFFICIAL_GPT_URL)
        self.assertEqual(manifest["official_service_and_candidate_state"]["preview_gate_case_count"], 12)
        self.assertEqual(
            tuple(manifest["compact_preview_gate_case_ids"]),
            COMPACT_PREVIEW_CASE_IDS,
        )
        self.assertEqual(manifest["historical_artifact_evaluation_case_count"], 39)
        self.assertEqual(
            manifest["japanese_interface_state"],
            {
                "status": "BETA",
                "native_speaker_terminology_review": "PENDING",
                "canonical_language": "en",
            },
        )


if __name__ == "__main__":
    unittest.main()
