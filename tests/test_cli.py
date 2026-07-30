import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from bsc_audit import __version__
from bsc_audit.census import (
    MAX_CERTIFICATE_BYTES as MAX_CENSUS_INPUT_BYTES,
    MAX_CERTIFICATE_CONTAINER_ITEMS as MAX_CENSUS_CONTAINER_ITEMS,
)
from bsc_audit.cli import (
    MAX_CONTAINER_ITEMS,
    InputError,
    _enforce_resource_limits,
    _read_stream_bounded,
    command,
    main,
)
from bsc_audit.findings import Finding, Severity
from bsc_audit.theorem import MAX_CERTIFICATE_BYTES as MAX_THEOREM_INPUT_BYTES


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def invoke(self, argv: list[str]) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            try:
                result = main(argv)
            except SystemExit as exc:
                result = int(exc.code)
        return result, output.getvalue()

    def test_duplicate_keys_are_rejected_as_prohibited_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"draft": false, "draft": true}', encoding="utf-8")
            status, text = self.invoke(["lint", str(path)])
        payload = json.loads(text)
        self.assertEqual(status, 2)
        self.assertEqual(payload["decision"], "prohibited")
        self.assertEqual(payload["findings"][0]["code"], "INPUT_MALFORMED")
        self.assertEqual(payload["input"], "duplicate.json")
        self.assertNotIn(directory, text)

    def test_nonfinite_json_numbers_are_rejected(self):
        for token in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(token=token), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "nonfinite.json"
                path.write_text('{"value": ' + token + "}", encoding="utf-8")
                status, text = self.invoke(["lint", str(path)])
            self.assertEqual(status, 2)
            self.assertEqual(json.loads(text)["decision"], "prohibited")

    def test_top_level_json_must_be_an_object(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "list.json"
            path.write_text("[]", encoding="utf-8")
            status, text = self.invoke(["lint", str(path)])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(text)["findings"][0]["code"], "INPUT_MALFORMED")

    def test_version_uses_the_package_version(self):
        status, text = self.invoke(["--version"])
        self.assertEqual(status, 0)
        self.assertEqual(text.strip(), f"bsc-audit {__version__}")

    def test_success_output_contains_safe_input_and_two_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.json"
            path.write_text('{"a": 1}\n', encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                status = command(
                    str(path),
                    lambda _raw, _root: [Finding(Severity.INFO, "CHECKED", "$", "fixture checked")],
                )
        payload = json.loads(output.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(payload["input"], "document.json")
        self.assertEqual(payload["decision"], "no_blocking_findings")
        self.assertEqual(payload["checks"]["run"], ["strict_json_parse", "custom_auditor"])
        self.assertRegex(payload["input_hashes"]["raw"], r"^sha256:[0-9a-f]{64}$")
        self.assertRegex(payload["input_hashes"]["semantic"], r"^sha256:[0-9a-f]{64}$")

    def test_internal_checker_failure_has_unique_decision_and_exit(self):
        def fail(_raw, _root):
            raise RuntimeError("sensitive implementation detail")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.json"
            path.write_text("{}", encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                status = command(str(path), fail)
        payload = json.loads(output.getvalue())
        self.assertEqual(status, 70)
        self.assertEqual(payload["decision"], "internal_error")
        self.assertEqual(payload["findings"][0]["code"], "INTERNAL_ERROR")
        self.assertNotIn("sensitive implementation detail", output.getvalue())

    def test_finding_precedence_and_exit_contract(self):
        cases = (
            (Severity.ERROR, "prohibited", 2),
            (Severity.BLOCKED, "blocked", 1),
            (Severity.DEMOTION, "demoted", 1),
            (Severity.WARNING, "no_blocking_findings_with_warnings", 0),
            (Severity.INFO, "no_blocking_findings", 0),
        )
        for severity, expected_decision, expected_exit in cases:
            with self.subTest(severity=severity), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "document.json"
                path.write_text("{}", encoding="utf-8")
                output = io.StringIO()
                with redirect_stdout(output):
                    status = command(
                        str(path),
                        lambda _raw, _root: [Finding(severity, "FIXTURE", "$", "fixture")],
                    )
            self.assertEqual(status, expected_exit)
            self.assertEqual(json.loads(output.getvalue())["decision"], expected_decision)

    def test_usage_error_is_machine_readable(self):
        status, text = self.invoke([])
        payload = json.loads(text)
        self.assertEqual(status, 2)
        self.assertEqual(payload["decision"], "prohibited")
        self.assertEqual(payload["findings"][0]["code"], "CLI_USAGE")
        self.assertIn("semantic_audit", payload["checks"]["not_run"])

    def test_nesting_limit_is_enforced(self):
        value = {}
        cursor = value
        for _ in range(65):
            cursor["nested"] = {}
            cursor = cursor["nested"]
        with self.assertRaises(InputError):
            _enforce_resource_limits(value)

    def test_input_stream_read_is_bounded_even_if_the_file_grows_after_stat(self):
        class GuardedBytesIO(io.BytesIO):
            def read(self, size=-1):
                self.assert_bounded(size)
                return super().read(size)

            @staticmethod
            def assert_bounded(size):
                if size < 0:
                    raise AssertionError("unbounded read")

        with self.assertRaises(InputError):
            _read_stream_bounded(GuardedBytesIO(b"1234"), 3)
        self.assertEqual(_read_stream_bounded(GuardedBytesIO(b"1234"), 4), b"1234")

    def test_closed_certificate_routes_enforce_kernel_byte_limits(self):
        cases = (
            (
                "theorem",
                ROOT / "examples" / "theorem_binomial_identity.json",
                MAX_THEOREM_INPUT_BYTES,
            ),
            (
                "census",
                ROOT / "examples" / "census_affine_bound.json",
                MAX_CENSUS_INPUT_BYTES,
            ),
        )
        for command_name, fixture, byte_limit in cases:
            with self.subTest(command=command_name), tempfile.TemporaryDirectory() as directory:
                payload = fixture.read_bytes()
                path = Path(directory) / f"{command_name}.json"
                path.write_bytes(payload + b" " * (byte_limit + 1 - len(payload)))
                status, text = self.invoke([command_name, str(path)])
            finding = json.loads(text)["findings"][0]
            self.assertEqual(status, 2)
            self.assertEqual(finding["code"], "INPUT_MALFORMED")
            self.assertIn(f"{byte_limit}-byte limit", finding["message"])

    def test_census_route_uses_a_headroom_container_limit(self):
        schema = json.loads(
            (
                ROOT / "schemas" / "finite-census-certificate-v0.1.schema.json"
            ).read_text(encoding="utf-8")
        )
        units = schema["properties"]["observations"]["maxItems"]
        observables = schema["$defs"]["formalStatement"]["properties"][
            "observables"
        ]["maxItems"]
        schema_maximum_entries = (
            23
            + 2 * observables
            + 4 * units
            + 3 * units * observables
        )
        self.assertLessEqual(
            4 * schema_maximum_entries,
            3 * MAX_CENSUS_CONTAINER_ITEMS,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            above_generic = root / "above-generic.json"
            above_generic.write_text(
                json.dumps({"items": [None] * (MAX_CONTAINER_ITEMS + 1)}),
                encoding="utf-8",
            )
            status, text = self.invoke(["census", str(above_generic)])
            self.assertEqual(status, 2)
            self.assertEqual(
                json.loads(text)["findings"][0]["code"],
                "SCHEMA_VALIDATION",
            )

            above_census = root / "above-census.json"
            above_census.write_text(
                json.dumps(
                    {"items": [None] * (MAX_CENSUS_CONTAINER_ITEMS + 1)}
                ),
                encoding="utf-8",
            )
            status, text = self.invoke(["census", str(above_census)])
            finding = json.loads(text)["findings"][0]
            self.assertEqual(status, 2)
            self.assertEqual(finding["code"], "INPUT_MALFORMED")
            self.assertIn(
                f"container entries exceed {MAX_CENSUS_CONTAINER_ITEMS}",
                finding["message"],
            )


if __name__ == "__main__":
    unittest.main()
