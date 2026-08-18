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


class SourceContractTests(unittest.TestCase):
    def test_source_closure_and_single_active_authorities(self) -> None:
        builder.validate_source_closure()
        builder.validate_active_authorities()

        active_profiles = []
        active_protocols = []
        for path in ROOT.rglob("profile.json"):
            document = load_json(path)
            if document.get("schema") == "bsc-claim-auditor-profile/v2" and document.get("authority_state") == "ACTIVE":
                active_profiles.append(path)
        for path in ROOT.rglob("prospective-canaries.json"):
            document = load_json(path)
            if document.get("schema") == "bsc-claim-auditor-prospective-canaries/v1" and document.get("authority_state") == "ACTIVE":
                active_protocols.append(path)

        self.assertEqual(active_profiles, [builder.PROFILE_PATH])
        self.assertEqual(active_protocols, [builder.EVAL_ROOT / "prospective-canaries.json"])

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
        archive = builder.V04_ROOT / "BSC-Claim-Auditor-v0.4.0-preview.1.zip"
        builder.verify_archive(archive, self.payload)
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
        self.assertEqual(len(calibration["pairs"]), 10)
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
