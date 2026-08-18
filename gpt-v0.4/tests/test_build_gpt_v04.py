from __future__ import annotations

import importlib.util
import hashlib
import json
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
BUILDER_PATH = ROOT / "scripts" / "build_gpt_v04.py"
SPEC = importlib.util.spec_from_file_location("build_gpt_v04", BUILDER_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import machinery guard
    raise RuntimeError("cannot load v0.4 builder")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected object: {path}")
    return value


def synthetic_canaries(lock_sha: str) -> dict[str, object]:
    cases = []
    for order, case_id in enumerate(builder.CASE_IDS, 1):
        cases.append(
            {
                "order": order,
                "id": case_id,
                "title": f"Mechanical schema fixture {order}",
                "language": "ja" if order == 9 else "en",
                "prompt": f"Mechanical prospective schema fixture {order}.",
                "attachments": 0,
                "status": "NOT_RUN_PREVIEW_NOT_AUTHORIZED",
                "outcome_oracle": {
                    "must": [f"mechanical obligation {order}"],
                    "must_not": [f"mechanical prohibition {order}"],
                },
                "applicable_hard_gates": list(builder.CASE_REQUIRED_GATES[case_id]),
                "emergency_stop_on_failure": False,
            }
        )
    return {
        "schema": builder.CANARY_SCHEMA,
        "authority_state": "ACTIVE",
        "protocol_id": builder.PROTOCOL_ID,
        "state": "FROZEN_NOT_RUN",
        "product_lock_sha256": lock_sha,
        "hard_gate_source": "gpt-v0.4/evals/hard-gates.md",
        "controller_contract": {
            "fresh_preview_chat": True,
            "frozen_dated_epoch_configuration_receipt": True,
            "attachments": 0,
            "exact_sends": 1,
            "regenerations": 0,
            "human_semantic_review": True,
            "machine_semantic_grading": False,
        },
        "future_run_rules": [f"mechanical controller rule {index}" for index in range(1, 9)],
        "case_count": 9,
        "cases": cases,
    }


def synthetic_calibration(lock_sha: str) -> dict[str, object]:
    pairs = []
    for index, principle in enumerate(builder.CALIBRATION_PRINCIPLES, 1):
        pass_style = "safe_awkward" if principle == "soft-format-and-identifiers" else "neutral"
        pass_record = {
            "label": f"mechanical-{index}-pass",
            "response": f"Mechanical calibration schema fixture {index} pass.",
            "controller_state": "CAPTURE_VALID",
            "triggered_hard_gates": [],
            "soft_findings": [],
            "expected_result": "HARD_PASS",
            "rationale": "Mechanical schema fixture.",
            "presentation_style": pass_style,
        }
        if principle == "controller":
            contrast_record = {
                "label": f"mechanical-{index}-invalid",
                "response": f"Mechanical calibration schema fixture {index} invalid.",
                "controller_state": "TRIAL_INVALID_CONTROLLER",
                "triggered_hard_gates": [],
                "soft_findings": [],
                "expected_result": "TRIAL_INVALID_CONTROLLER",
                "rationale": "Mechanical schema fixture.",
                "presentation_style": "neutral",
            }
        else:
            fail_style = "unsafe_polished" if principle == "soft-format-and-identifiers" else "neutral"
            contrast_record = {
                "label": f"mechanical-{index}-fail",
                "response": f"Mechanical calibration schema fixture {index} fail.",
                "controller_state": "CAPTURE_VALID",
                "triggered_hard_gates": list(builder.CALIBRATION_REQUIRED_GATES[principle]),
                "soft_findings": [],
                "expected_result": "HARD_FAIL",
                "rationale": "Mechanical schema fixture.",
                "presentation_style": fail_style,
            }
        pairs.append({"id": f"mechanical-pair-{index}", "principle": principle, "records": [pass_record, contrast_record]})
    return {
        "schema": builder.CALIBRATION_SCHEMA,
        "state": "FROZEN",
        "product_lock_sha256": lock_sha,
        "hard_gate_source": "gpt-v0.4/evals/hard-gates.md",
        "classification_invariant": {
            "controller_invalid": "TRIAL_INVALID_CONTROLLER",
            "controller_valid_with_any_triggered_hard_gate": "HARD_FAIL",
            "controller_valid_with_no_triggered_hard_gate": "HARD_PASS",
            "soft_findings_change_hard_result": False,
        },
        "pairs": pairs,
    }


class SourceContractTests(unittest.TestCase):
    def test_source_closure_and_single_active_authorities(self) -> None:
        builder.validate_source_closure()
        builder.validate_active_authorities()

        active_profiles = []
        active_protocols = []
        for path in ROOT.rglob("profile.json"):
            document = load_json(path)
            if document.get("schema") in builder.RECOGNIZED_PROFILE_SCHEMAS and document.get("authority_state") == "ACTIVE":
                active_profiles.append(path)
        for path in ROOT.rglob("prospective-canaries.json"):
            document = load_json(path)
            if document.get("schema") in builder.RECOGNIZED_CANARY_SCHEMAS and document.get("authority_state") == "ACTIVE":
                active_protocols.append(path)

        self.assertEqual(active_profiles, [builder.PROFILE_PATH])
        self.assertEqual(active_protocols, [builder.EVAL_ROOT / "prospective-canaries.json"])

    def test_legacy_active_protocol_cannot_hide_from_v2_authority_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile = root / "current" / "profile.json"
            current = root / "current" / "prospective-canaries.json"
            legacy = root / "legacy" / "prospective-canaries.json"
            for path, document in (
                (profile, {"schema": "bsc-claim-auditor-profile/v2", "authority_state": "ACTIVE"}),
                (current, {"schema": builder.CANARY_SCHEMA, "authority_state": "ACTIVE"}),
                (legacy, {"schema": "bsc-claim-auditor-prospective-canaries/v1", "authority_state": "ACTIVE"}),
            ):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(builder.BuildError):
                builder.validate_active_authorities(
                    root=root,
                    expected_profile=profile,
                    expected_protocol=current,
                )

    def test_instructions_length_headroom_and_removed_ceremony(self) -> None:
        profile = load_json(builder.PROFILE_PATH)
        raw = (builder.SOURCE_ROOT / "instructions.md").read_bytes()
        text = raw.decode("utf-8")
        builder.validate_instructions(text, profile)

        self.assertEqual(len(text), 3997)
        self.assertEqual(len(raw), 3997)
        self.assertEqual(len(text.splitlines()), 27)
        self.assertLessEqual(len(text), 4000)
        self.assertGreaterEqual(4500 - len(text), 503)

        forbidden_phrases = (
            "nine-duty",
            "Base64",
            "Return Desk",
            "audit_request",
            "audit_report",
            "audit_return",
            "shard",
            "compiler",
            "exact response token",
        )
        for phrase in forbidden_phrases:
            self.assertNotIn(phrase.casefold(), text.casefold())
        for identifier in ("T", "T1", "C1"):
            self.assertIsNone(__import__("re").search(rf"\b{identifier}\b", text))

    def test_profile_is_referential_and_capabilities_are_unchanged(self) -> None:
        profile = load_json(builder.PROFILE_PATH)
        builder.validate_profile(profile)
        serialized = json.dumps(profile, ensure_ascii=False)
        metadata = load_json(builder.METADATA_PATH)
        starters = load_json(builder.STARTERS_PATH)

        self.assertEqual(profile["capabilities"], builder.EXPECTED_CAPABILITIES)
        self.assertNotIn(metadata["description"], serialized)
        for starter in starters["starters"]:
            self.assertNotIn(starter, serialized)
        self.assertEqual(
            [item["upload"] for item in profile["source_paths"]["knowledge"]],
            list(builder.KNOWLEDGE_UPLOADS),
        )
        self.assertEqual(profile["product_version"], builder.PRODUCT_VERSION)
        self.assertEqual(profile["candidate_id"], builder.CANDIDATE_ID)

    def test_dependency_local_boundary_is_precise_and_not_a_quick_ledger(self) -> None:
        instructions = (builder.SOURCE_ROOT / "instructions.md").read_text(encoding="utf-8")
        core = (builder.SOURCE_ROOT / "knowledge" / "01-core-guide.md").read_text(encoding="utf-8")
        japanese = (builder.SOURCE_ROOT / "knowledge" / "04-japanese-glossary.md").read_text(encoding="utf-8")
        model_facing = "\n".join((instructions, core, japanese))

        self.assertIn("unestablished decisive premises block only dependent conclusions", instructions)
        self.assertIn("exact certificate actually replayed successfully", core)
        self.assertIn("never asserts that no answer exists globally", core)
        self.assertIn("An independently supported conclusion does not inherit a neighboring gap", core)
        self.assertIn("実際に再実行され、成功している", japanese)
        self.assertIn("世界のどこにも答えがないという意味ではない", japanese)
        self.assertNotIn("support_trace", model_facing)

    def test_four_knowledge_files_are_ordered_and_free_of_mutable_status(self) -> None:
        profile = load_json(builder.PROFILE_PATH)
        knowledge = profile["source_paths"]["knowledge"]
        self.assertEqual(len(knowledge), 4)
        self.assertEqual(
            [item["source"] for item in knowledge],
            [
                "gpt-v0.4/source/knowledge/01-core-guide.md",
                "gpt-v0.4/source/knowledge/02-checks-catalog.md",
                "gpt-v0.4/source/knowledge/03-worked-examples.md",
                "gpt-v0.4/source/knowledge/04-japanese-glossary.md",
            ],
        )
        immutable_text = "\n".join((ROOT / item["source"]).read_text(encoding="utf-8") for item in knowledge)
        for mutable_status in ("Anyone with link", "Research Preview", "UPDATED_LIVE", "PUBLISHED_LIVE"):
            self.assertNotIn(mutable_status, immutable_text)

    def test_catalog_covers_every_real_cli_route_once(self) -> None:
        catalog = load_json(builder.CATALOG_PATH)
        builder.validate_catalog(catalog)
        self.assertEqual([item["command"] for item in catalog["checks"]], list(builder.ENGINE_COMMANDS))
        self.assertEqual(len({item["id"] for item in catalog["checks"]}), len(builder.ENGINE_COMMANDS))

    def test_historical_routing_is_noncontrolling(self) -> None:
        development = load_json(builder.EVAL_ROOT / "development-regressions.json")
        builder.validate_development_regressions(development)
        self.assertEqual(development["authority_state"], "HISTORICAL_NONCONTROLLING")
        self.assertEqual(development["result_transfer"], "FORBIDDEN")
        self.assertTrue(all(route["state"] != "ACTIVE" for route in development["legacy_authority_routes"]))


class DeterministicBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        canaries = load_json(builder.EVAL_ROOT / "prospective-canaries.json")
        cls.frozen = canaries.get("state") == "FROZEN_NOT_RUN"
        cls.payload = builder.build_payload(allow_draft_evaluation=not cls.frozen)

    def test_checked_in_dist_matches_source(self) -> None:
        builder.check_output(builder.DIST_ROOT, self.payload)

    def test_generation_and_archives_are_byte_deterministic(self) -> None:
        again = builder.build_payload(allow_draft_evaluation=not self.frozen)
        self.assertEqual(self.payload, again)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_a = root / "a" / "dist"
            output_b = root / "b" / "dist"
            archive_a = root / "a" / "candidate.zip"
            archive_b = root / "b" / "candidate.zip"
            builder.write_output(output_a, self.payload)
            builder.write_output(output_b, again)
            builder.write_archive(archive_a, self.payload)
            builder.write_archive(archive_b, again)
            self.assertEqual(archive_a.read_bytes(), archive_b.read_bytes())
            self.assertEqual(builder._validate_output_closure(output_a, allow_missing=False), self.payload)
            self.assertEqual(builder._validate_output_closure(output_b, allow_missing=False), self.payload)

    def test_product_lock_has_complete_scope_without_circular_identity(self) -> None:
        lock = json.loads(self.payload["GPT_PRODUCT_LOCK.json"])
        self.assertEqual(lock["model_facing_files"], [builder.file_record(path, self.payload[path]) for path in builder.MODEL_FACING_MEMBERS])
        self.assertEqual(lock["live_binding_state"], "NON_ADMISSIBLE_UNHASHABLE")
        self.assertEqual(lock["builder"]["path"], "scripts/build_gpt_v04.py")
        serialized = self.payload["GPT_PRODUCT_LOCK.json"].decode("utf-8")
        self.assertNotIn("final_git_commit", serialized)
        self.assertNotIn("archive_sha256", serialized)
        self.assertNotIn('"GPT_PRODUCT_LOCK.json"', json.dumps(lock["model_facing_files"]))
        self.assertIn("final Git commit identity", lock["excluded_from_product_identity"])

    def test_checksum_manifest_is_sorted_by_path_and_excludes_itself(self) -> None:
        lines = self.payload["SHA256SUMS"].decode("utf-8").splitlines()
        paths = [line.split("  ", 1)[1] for line in lines]
        self.assertEqual(paths, sorted(paths))
        self.assertEqual(paths, sorted(set(self.payload) - {"SHA256SUMS"}))
        self.assertNotIn("SHA256SUMS", paths)

    def test_dist_and_archive_member_closure(self) -> None:
        self.assertEqual(set(self.payload), set(builder.DIST_MEMBERS))
        archive = builder.CANONICAL_ARCHIVE_PATH
        builder.verify_archive(archive, self.payload)
        self.assertEqual(tuple(builder.V04_ROOT.glob("BSC-Claim-Auditor-v*.zip")), (archive,))
        with zipfile.ZipFile(archive, "r") as handle:
            self.assertEqual(tuple(handle.namelist()), builder.archive_member_names(self.payload))

    def test_check_mode_verifies_archive_without_rewriting_it(self) -> None:
        archive = builder.CANONICAL_ARCHIVE_PATH
        before = (archive.read_bytes(), archive.stat().st_mtime_ns)
        result = builder.main(
            [
                "--check",
                "--output",
                str(builder.DIST_ROOT),
                "--archive",
                str(archive),
                *( [] if self.frozen else ["--allow-draft-evaluation"] ),
            ]
        )
        after = (archive.read_bytes(), archive.stat().st_mtime_ns)
        self.assertEqual(result, 0)
        self.assertEqual(before, after)


class FailureBoundaryTests(unittest.TestCase):
    def test_private_paths_identities_and_secrets_are_rejected(self) -> None:
        probes = (
            "C:" + "\\Users\\" + "alice\\capture.json",
            ".co" + "dex/attachments/receipt.txt",
            "Pirate" + " Dude",
            "gh" + "p_" + "A" * 24,
            "-----BEGIN " + "PRIVATE KEY-----",
        )
        for probe in probes:
            with self.subTest(probe=probe[:12]), self.assertRaises(builder.BuildError):
                builder.scan_private_material("probe", probe.encode("utf-8"))

    def test_unsafe_and_portably_colliding_member_names_are_rejected(self) -> None:
        unsafe = (
            "../escape",
            "/absolute",
            "C:/drive",
            "server\\share",
            "name:stream",
            "trailing. ",
            "CON",
            "control\x00name",
        )
        for value in unsafe:
            with self.subTest(value=value):
                self.assertFalse(builder.safe_member_name(value))
        with self.assertRaises(builder.BuildError):
            builder.validate_path_roster(("A/file.md", "a/FILE.md"), label="collision")
        with self.assertRaises(builder.BuildError):
            builder.validate_path_roster(("é.md", "e\u0301.md"), label="normalization")

    def test_symlink_or_reparse_output_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "dist"
            output.mkdir()
            with mock.patch.object(builder, "_is_reparse_or_symlink", return_value=True):
                with self.assertRaises(builder.BuildError):
                    builder._validate_output_closure(output, allow_missing=False)

    def test_repository_output_and_archive_redirects_are_rejected(self) -> None:
        with self.assertRaises(builder.BuildError):
            builder._assert_safe_output(ROOT / "src" / "generated")
        with self.assertRaises(builder.BuildError):
            builder._assert_safe_archive_destination(builder.PROFILE_PATH, require_existing=False)
        with self.assertRaises(builder.BuildError):
            builder._assert_safe_archive_destination(ROOT / "unrelated.zip", require_existing=False)

    def test_duplicate_archive_members_are_rejected(self) -> None:
        payload = {"README.md": b"ok\n"}
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "duplicate.zip"
            name = f"{builder.ARCHIVE_ROOT}/README.md"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as handle:
                    handle.writestr(name, b"ok\n")
                    handle.writestr(name, b"ok\n")
            with self.assertRaises(builder.BuildError):
                builder.verify_archive(archive, payload)


class EvaluatorContractTests(unittest.TestCase):
    def test_hard_gates_are_the_only_general_semantic_authority(self) -> None:
        text = (builder.EVAL_ROOT / "hard-gates.md").read_text(encoding="utf-8")
        self.assertEqual(builder.hard_gate_ids(text), builder.HARD_GATE_IDS)
        self.assertIn("Unsupported promotion or propagation", text)
        self.assertIn("Japanese-language or evidentiary-parity failure", text)
        self.assertIn("(origin, audit_activity, assurance, authority_scope)", text)

    def test_case_gate_ownership_cannot_be_borrowed(self) -> None:
        lock_sha = "0" * 64
        document = synthetic_canaries(lock_sha)
        builder.validate_canaries(document, product_lock_sha256=lock_sha, allow_draft=False)
        cases = document["cases"]
        execution = next(case for case in cases if case["id"] == "execution-authorization-and-relevance")
        injection = next(case for case in cases if case["id"] == "quoted-prompt-injection")
        execution["applicable_hard_gates"].remove("H04")
        injection["applicable_hard_gates"].append("H04")
        injection["applicable_hard_gates"].sort(key=builder.HARD_GATE_IDS.index)
        with self.assertRaises(builder.BuildError):
            builder.validate_canaries(document, product_lock_sha256=lock_sha, allow_draft=False)

    def test_calibration_rejects_borrowed_gate_and_global_duplicate_label(self) -> None:
        lock_sha = "0" * 64
        document = synthetic_calibration(lock_sha)
        builder.validate_calibration(document, product_lock_sha256=lock_sha, allow_draft=False)

        duplicate = json.loads(json.dumps(document))
        duplicate["pairs"][1]["records"][0]["label"] = duplicate["pairs"][0]["records"][0]["label"]
        with self.assertRaises(builder.BuildError):
            builder.validate_calibration(duplicate, product_lock_sha256=lock_sha, allow_draft=False)

        borrowed = json.loads(json.dumps(document))
        unauthorized = next(pair for pair in borrowed["pairs"] if pair["principle"] == "unauthorized-execution")
        unauthorized["records"][1]["triggered_hard_gates"] = ["H02"]
        relevance = next(pair for pair in borrowed["pairs"] if pair["principle"] == "execution-relevance")
        relevance["records"][1]["triggered_hard_gates"] = ["H02", "H04"]
        with self.assertRaises(builder.BuildError):
            builder.validate_calibration(borrowed, product_lock_sha256=lock_sha, allow_draft=False)

    def test_calibration_and_nine_unique_attachment_free_canaries(self) -> None:
        canaries = load_json(builder.EVAL_ROOT / "prospective-canaries.json")
        calibration = load_json(builder.EVAL_ROOT / "evaluator-calibration.json")
        lock_sha = builder.product_lock_sha256(self.payload_for_state(canaries))
        builder.validate_canaries(canaries, product_lock_sha256=lock_sha, allow_draft=canaries["state"] != "FROZEN_NOT_RUN")
        builder.validate_calibration(calibration, product_lock_sha256=lock_sha, allow_draft=canaries["state"] != "FROZEN_NOT_RUN")

        if canaries["state"] != "FROZEN_NOT_RUN":
            self.skipTest("prospective prompts intentionally withheld until product freeze")
        self.assertEqual(canaries["case_count"], 9)
        self.assertEqual(len(canaries["cases"]), 9)
        prompt_hashes = {hashlib.sha256(case["prompt"].encode("utf-8")).hexdigest() for case in canaries["cases"]}
        self.assertEqual(len(prompt_hashes), 9)
        self.assertTrue(all(case["attachments"] == 0 and case["status"] == "NOT_RUN_PREVIEW_NOT_AUTHORIZED" for case in canaries["cases"]))
        self.assertEqual(len(calibration["pairs"]), len(builder.CALIBRATION_PRINCIPLES))
        covered_case_gates = {gate for case in canaries["cases"] for gate in case["applicable_hard_gates"]}
        covered_calibration_gates = {
            gate
            for pair in calibration["pairs"]
            for record in pair["records"]
            for gate in record["triggered_hard_gates"]
        }
        self.assertEqual(covered_case_gates, set(builder.HARD_GATE_IDS))
        self.assertEqual(covered_calibration_gates, set(builder.HARD_GATE_IDS))
        model_source = "\n".join(
            (builder.SOURCE_ROOT / relative).read_text(encoding="utf-8")
            for relative in builder.SOURCE_MEMBERS
        )
        for case in canaries["cases"]:
            self.assertNotIn(case["prompt"], model_source)

    @staticmethod
    def payload_for_state(canaries: dict[str, object]) -> dict[str, bytes]:
        return builder.build_payload(allow_draft_evaluation=canaries["state"] != "FROZEN_NOT_RUN")


if __name__ == "__main__":
    unittest.main()
