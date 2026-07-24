from __future__ import annotations

import ast
import copy
import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts import check_gpt_frozen_candidate as checker


ROOT = Path(__file__).resolve().parents[1]


class FrozenCandidateManifestTests(unittest.TestCase):
    def materialize_registry(self, root: Path) -> None:
        for category, relative in checker.registry_entries():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"{category}\n{relative}\n".encode("utf-8"))

    def invoke(self, root: Path, *argv: str) -> tuple[int, dict]:
        output = io.StringIO()
        with redirect_stdout(output):
            status = checker.main(list(argv), root=root)
        return status, json.loads(output.getvalue())

    def finding_codes(self, payload: dict) -> set[str]:
        return {finding["code"] for finding in payload["findings"]}

    def write_document(self, path: Path, document: dict) -> None:
        path.write_bytes(checker._manifest_bytes(document))

    def test_registry_contract_is_explicit_complete_and_current(self) -> None:
        document, findings = checker.build_manifest(ROOT)
        self.assertEqual(findings, [])
        self.assertEqual(len(checker.registry_entries()), 142)
        self.assertEqual(document["file_count"], 142)
        self.assertEqual(len(document["files"]), 142)
        self.assertEqual(
            [(entry["category"], entry["path"]) for entry in document["files"]],
            list(checker.registry_entries()),
        )

        paths = {path for _, path in checker.registry_entries()}
        self.assertEqual(
            {
                path
                for category, path in checker.registry_entries()
                if category == "evaluation_fixtures"
            },
            {
                f"gpt/evals/fixtures/{filename}"
                for filename in checker.EVAL_FIXTURE_FILENAMES
            },
        )
        self.assertEqual(len(checker.EVAL_FIXTURE_FILENAMES), 39)
        self.assertEqual(
            {
                path
                for category, path in checker.registry_entries()
                if category == "candidate" and path.startswith("gpt/knowledge/")
            },
            {
                f"gpt/knowledge/{filename}"
                for filename in checker.KNOWLEDGE_FILENAMES
            },
        )
        self.assertEqual(len(checker.KNOWLEDGE_FILENAMES), 5)
        self.assertEqual(len(checker.TEST_FILENAMES), 25)
        self.assertEqual(
            {
                path
                for category, path in checker.registry_entries()
                if category == "tests"
            },
            {f"tests/{filename}" for filename in checker.TEST_FILENAMES},
        )
        self.assertEqual(len(checker.SCHEMA_FILENAMES), 9)
        self.assertEqual(
            {
                path
                for category, path in checker.registry_entries()
                if category == "python_return_desk"
                and path.startswith("schemas/")
            },
            {f"schemas/{filename}" for filename in checker.SCHEMA_FILENAMES},
        )
        self.assertEqual(
            {
                path
                for category, path in checker.registry_entries()
                if category == "python_return_desk"
                and path.startswith("src/bsc_audit/schema_data/")
            },
            {
                f"src/bsc_audit/schema_data/{filename}"
                for filename in checker.SCHEMA_FILENAMES
            },
        )

        required = {
            "gpt/GPT_INSTRUCTIONS.md",
            "gpt/_source/GPT_PROFILE.json",
            "gpt/_source/GPT_EVAL_SPEC.json",
            "gpt/evals/GPT_EVAL_CASES.jsonl",
            "gpt/evals/GPT_EVAL_EXPECTATIONS.md",
            "gpt/evals/GPT_MANUAL_SCORECARD.md",
            "gpt/evals/README.md",
            "gpt/_source/GPT_EVAL_PROVENANCE.md",
            "gpt/_source/GPT_INVARIANT_ENFORCEMENT_MATRIX.md",
            "gpt/_source/GPT_FROZEN_EVALUATION_PROTOCOL.json",
            "BSC_AUDIT_LLM_PACKET.md",
            "scripts/build_gpt_package.py",
            "scripts/check_gpt_package.py",
            "scripts/check_gpt_eval_bundle.py",
            "scripts/check_gpt_eval_suite.py",
            "scripts/check_gpt_frozen_candidate.py",
            "scripts/gpt_artifact_compiler.py",
            "scripts/gpt_eval_controller.py",
            "schemas/audit-return-v0.1.schema.json",
            "src/bsc_audit/schema_data/audit-return-v0.1.schema.json",
            "src/bsc_audit/return_desk.py",
            "pages/return-desk-core.js",
            "tests/return_desk_runtime.test.cjs",
            "tests/test_gpt_artifact_compiler.py",
            "tests/test_gpt_eval_bundle.py",
            "tests/test_gpt_eval_controller.py",
            "tests/test_gpt_eval_suite.py",
            "tests/test_gpt_frozen_candidate.py",
            "tests/test_gpt_package.py",
            "tests/test_pages.py",
            "tests/test_return_desk.py",
            "toolchain.lock.json",
        }
        self.assertLessEqual(required, paths)
        self.assertTrue(set(checker.EXCLUDED_CYCLE_PATHS).isdisjoint(paths))

    def test_write_and_check_are_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-frozen-deterministic-") as directory:
            root = Path(directory)
            self.materialize_registry(root)
            first = root / "first.freeze.json"
            second = root / "second.freeze.json"

            first_status, first_payload = self.invoke(root, "--write", str(first))
            second_status, second_payload = self.invoke(root, "--write", str(second))

            self.assertEqual(first_status, 0)
            self.assertEqual(second_status, 0)
            self.assertEqual(first_payload["status"], "pass")
            self.assertEqual(second_payload["status"], "pass")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(
                first_payload["manifest_sha256"],
                hashlib.sha256(first.read_bytes()).hexdigest(),
            )
            document = json.loads(first.read_bytes())
            self.assertEqual(set(document), checker.MANIFEST_KEYS)
            self.assertEqual(document["file_count"], len(checker.registry_entries()))
            self.assertEqual(
                [(entry["category"], entry["path"]) for entry in document["files"]],
                sorted(
                    (entry["category"], entry["path"])
                    for entry in document["files"]
                ),
            )
            for entry in document["files"]:
                self.assertEqual(set(entry), checker.ENTRY_KEYS)
                self.assertIs(type(entry["bytes"]), int)
                self.assertRegex(entry["sha256"], checker.SHA256_RE)
                data = (root / entry["path"]).read_bytes()
                self.assertEqual(entry["bytes"], len(data))
                self.assertEqual(entry["sha256"], hashlib.sha256(data).hexdigest())

            check_status, check_payload = self.invoke(root, "--check", str(first))
            self.assertEqual(check_status, 0)
            self.assertEqual(check_payload["status"], "pass")
            self.assertEqual(check_payload["findings"], [])

    def test_changed_frozen_bytes_block_on_size_and_digest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-frozen-mutation-") as directory:
            root = Path(directory)
            self.materialize_registry(root)
            manifest = root / "candidate.freeze.json"
            self.assertEqual(checker.write_manifest(manifest, root)[0], 0)

            target = root / "gpt" / "GPT_INSTRUCTIONS.md"
            target.write_bytes(target.read_bytes() + b"mutated\n")
            status, payload = checker.check_manifest(manifest, root)

            self.assertNotEqual(status, 0)
            self.assertEqual(payload["status"], "blocked")
            self.assertLessEqual(
                {"MANIFEST_BYTES_MISMATCH", "MANIFEST_SHA256_MISMATCH"},
                self.finding_codes(payload),
            )

    def test_predeclared_manifest_digest_is_checked_before_trials(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-frozen-pinned-") as directory:
            root = Path(directory)
            self.materialize_registry(root)
            manifest = root / "candidate.freeze.json"
            write_status, write_payload = checker.write_manifest(manifest, root)
            self.assertEqual(write_status, 0)
            expected = write_payload["manifest_sha256"]

            pass_status, pass_payload = checker.check_manifest(
                manifest,
                root,
                expected_manifest_sha256=expected,
            )
            fail_status, fail_payload = checker.check_manifest(
                manifest,
                root,
                expected_manifest_sha256="0" * 64,
            )

            self.assertEqual(pass_status, 0)
            self.assertEqual(pass_payload["manifest_sha256"], expected)
            self.assertEqual(pass_payload["findings"], [])
            self.assertNotEqual(fail_status, 0)
            self.assertIn(
                "MANIFEST_EXPECTED_SHA256_MISMATCH",
                self.finding_codes(fail_payload),
            )

    def test_manifest_membership_order_and_path_mutations_fail_closed(self) -> None:
        def remove_entry(document: dict, _: Path) -> None:
            document["files"].pop()
            document["file_count"] -= 1

        def duplicate_entry(document: dict, _: Path) -> None:
            document["files"].append(copy.deepcopy(document["files"][-1]))
            document["file_count"] += 1

        def reverse_order(document: dict, _: Path) -> None:
            document["files"].reverse()

        def unsafe_path(document: dict, _: Path) -> None:
            document["files"][0]["path"] = "../escape"

        def cyclic_path(document: dict, _: Path) -> None:
            document["files"][0]["path"] = checker.EXCLUDED_CYCLE_PATHS[0]

        def self_reference(document: dict, manifest: Path) -> None:
            document["files"][0]["path"] = manifest.name

        cases = (
            ("missing", remove_entry, {"MANIFEST_MEMBERSHIP_MISMATCH"}),
            ("duplicate", duplicate_entry, {"MANIFEST_DUPLICATE_ENTRY"}),
            ("order", reverse_order, {"MANIFEST_ORDER_INVALID"}),
            ("unsafe", unsafe_path, {"MANIFEST_PATH_UNSAFE"}),
            ("cycle", cyclic_path, {"MANIFEST_CYCLE_PATH_INCLUDED"}),
            ("self", self_reference, {"MANIFEST_SELF_REFERENCE"}),
        )
        for name, mutate, expected_codes in cases:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory(prefix=f"bsc-frozen-{name}-") as directory:
                    root = Path(directory)
                    self.materialize_registry(root)
                    manifest = root / "candidate.freeze.json"
                    self.assertEqual(checker.write_manifest(manifest, root)[0], 0)
                    document = json.loads(manifest.read_bytes())
                    mutate(document, manifest)
                    self.write_document(manifest, document)

                    status, payload = checker.check_manifest(manifest, root)
                    self.assertNotEqual(status, 0)
                    self.assertLessEqual(expected_codes, self.finding_codes(payload))

    def test_strict_json_entry_types_and_canonical_bytes_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-frozen-strict-") as directory:
            root = Path(directory)
            self.materialize_registry(root)
            manifest = root / "candidate.freeze.json"
            self.assertEqual(checker.write_manifest(manifest, root)[0], 0)
            baseline = manifest.read_bytes()

            manifest.write_bytes(
                b'{"manifest_schema":"first","manifest_schema":"second"}\n'
            )
            status, payload = checker.check_manifest(manifest, root)
            self.assertNotEqual(status, 0)
            self.assertIn("MANIFEST_JSON_INVALID", self.finding_codes(payload))

            document = json.loads(baseline)
            document["files"][0]["bytes"] = True
            document["files"][1]["sha256"] = document["files"][1]["sha256"].upper()
            document["files"][2]["unexpected"] = "field"
            self.write_document(manifest, document)
            status, payload = checker.check_manifest(manifest, root)
            self.assertNotEqual(status, 0)
            self.assertIn("MANIFEST_ENTRY_INVALID", self.finding_codes(payload))

            manifest.write_bytes(baseline.rstrip(b"\n"))
            status, payload = checker.check_manifest(manifest, root)
            self.assertNotEqual(status, 0)
            self.assertIn(
                "MANIFEST_SERIALIZATION_NONCANONICAL",
                self.finding_codes(payload),
            )

    def test_closed_directory_drift_and_missing_file_block_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-frozen-extra-") as directory:
            root = Path(directory)
            self.materialize_registry(root)
            unexpected = root / "gpt" / "evals" / "fixtures" / "unregistered.txt"
            unexpected.write_bytes(b"not frozen\n")
            manifest = root / "candidate.freeze.json"

            status, payload = checker.write_manifest(manifest, root)

            self.assertNotEqual(status, 0)
            self.assertIn(
                "REGISTRY_DIRECTORY_MEMBERSHIP_MISMATCH",
                self.finding_codes(payload),
            )
            self.assertFalse(manifest.exists())

        with tempfile.TemporaryDirectory(prefix="bsc-frozen-missing-") as directory:
            root = Path(directory)
            self.materialize_registry(root)
            (root / "gpt" / "GPT_INSTRUCTIONS.md").unlink()
            manifest = root / "candidate.freeze.json"

            status, payload = checker.write_manifest(manifest, root)

            self.assertNotEqual(status, 0)
            self.assertIn("REGISTRY_FILE_MISSING", self.finding_codes(payload))
            self.assertFalse(manifest.exists())

    def test_closed_test_and_schema_sets_ignore_cache_but_reject_new_sources(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-frozen-closed-suffix-") as directory:
            root = Path(directory)
            self.materialize_registry(root)
            cache = root / "tests" / "__pycache__"
            cache.mkdir()
            (cache / "test_cache.pyc").write_bytes(b"cache bytes\n")
            (root / "schemas" / "README.md").write_bytes(b"schema notes\n")
            manifest = root / "candidate.freeze.json"

            status, payload = checker.write_manifest(manifest, root)
            self.assertEqual(status, 0)
            self.assertEqual(payload["status"], "pass")

            (root / "tests" / "test_unregistered.py").write_bytes(b"new test\n")
            status, payload = checker.write_manifest(root / "second.json", root)
            self.assertNotEqual(status, 0)
            self.assertIn(
                "REGISTRY_DIRECTORY_MEMBERSHIP_MISMATCH",
                self.finding_codes(payload),
            )

            (root / "tests" / "test_unregistered.py").unlink()
            (root / "schemas" / "unregistered.schema.json").write_bytes(b"{}\n")
            status, payload = checker.write_manifest(root / "third.json", root)
            self.assertNotEqual(status, 0)
            self.assertIn(
                "REGISTRY_DIRECTORY_MEMBERSHIP_MISMATCH",
                self.finding_codes(payload),
            )

    def test_safe_paths_are_portable_and_registry_paths_are_canonical(self) -> None:
        self.assertTrue(
            all(
                checker._safe_relative_path(path)
                for _, path in checker.registry_entries()
            )
        )
        for unsafe in (
            "",
            "/absolute",
            "C:/escape",
            "folder\\file",
            "folder/../file",
            "folder//file",
            "CON/file",
            "folder/trailing.",
            "folder/control\x1f",
            "folder/non-ascii-\N{LATIN SMALL LETTER E WITH ACUTE}",
        ):
            with self.subTest(path=unsafe):
                self.assertFalse(checker._safe_relative_path(unsafe))

    def test_write_targets_cannot_overwrite_frozen_or_cyclic_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-frozen-targets-") as directory:
            root = Path(directory)
            self.materialize_registry(root)

            frozen_target = root / "scripts" / "check_gpt_frozen_candidate.py"
            original = frozen_target.read_bytes()
            status, payload = checker.write_manifest(frozen_target, root)
            self.assertNotEqual(status, 0)
            self.assertIn("MANIFEST_SELF_REFERENCE", self.finding_codes(payload))
            self.assertEqual(frozen_target.read_bytes(), original)

            cyclic_target = root / checker.EXCLUDED_CYCLE_PATHS[0]
            status, payload = checker.write_manifest(cyclic_target, root)
            self.assertNotEqual(status, 0)
            self.assertIn(
                "MANIFEST_WRITE_TARGET_RESERVED",
                self.finding_codes(payload),
            )
            self.assertFalse(cyclic_target.exists())

            closed_target = root / "gpt" / "evals" / "fixtures" / "manifest.json"
            status, payload = checker.write_manifest(closed_target, root)
            self.assertNotEqual(status, 0)
            self.assertIn(
                "MANIFEST_WRITE_TARGET_RESERVED",
                self.finding_codes(payload),
            )
            self.assertFalse(closed_target.exists())

    def test_cli_usage_errors_are_machine_readable_and_nonzero(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bsc-frozen-cli-") as directory:
            root = Path(directory)
            self.materialize_registry(root)
            for argv in (
                (),
                ("--write", "one.json", "--check", "two.json"),
                (
                    "--write",
                    "one.json",
                    "--expect-manifest-sha256",
                    "0" * 64,
                ),
            ):
                with self.subTest(argv=argv):
                    status, payload = self.invoke(root, *argv)
                    self.assertEqual(status, 2)
                    self.assertEqual(payload["status"], "blocked")
                    self.assertEqual(self.finding_codes(payload), {"CLI_USAGE"})

    def test_checker_has_no_git_browser_network_or_process_dependency(self) -> None:
        source = Path(checker.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_roots: set[str] = set()
        forbidden_calls: set[tuple[str, str]] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
            ):
                forbidden_calls.add((node.func.value.id, node.func.attr))

        self.assertTrue(
            {
                "subprocess",
                "socket",
                "urllib",
                "http",
                "requests",
                "webbrowser",
                "git",
            }.isdisjoint(imported_roots)
        )
        self.assertTrue(
            {
                ("os", "system"),
                ("os", "popen"),
                ("os", "spawnl"),
                ("os", "spawnv"),
            }.isdisjoint(forbidden_calls)
        )


if __name__ == "__main__":
    unittest.main()
