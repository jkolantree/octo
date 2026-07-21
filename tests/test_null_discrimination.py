import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from bsc_audit.cli import main


ROOT = Path(__file__).resolve().parents[1]


class NullDiscriminationTests(unittest.TestCase):
    def invoke(self, command: str, path: Path) -> tuple[int, dict]:
        output = io.StringIO()
        with redirect_stdout(output):
            status = main([command, str(path)])
        return status, json.loads(output.getvalue())

    def test_valid_control_remains_clear(self):
        status, payload = self.invoke("audit", ROOT / "examples" / "claim_valid.json")
        self.assertEqual(status, 0)
        self.assertEqual(payload["decision"], "no_blocking_findings")

    def test_registered_fatal_mutations_are_distinguished(self):
        cases = (
            ("null_conflicting_referenced.json", {"GATE_RESULT_UNVERIFIED", "GATE_CONFLICT"}),
            ("null_omitted_bound_failure.json", {"GATE_RESULT_UNVERIFIED", "GATE_CONFLICT"}),
            ("null_failed_proof.json", {"THEOREM_CERTIFICATE_MISSING"}),
            ("null_missing_arithmetic_config.json", {"ARITHMETIC_TRACE_CONFIG_MISSING"}),
        )
        for filename, required_codes in cases:
            with self.subTest(filename=filename):
                status, payload = self.invoke("audit", ROOT / "examples" / filename)
                codes = {finding["code"] for finding in payload["findings"]}
                self.assertNotEqual(status, 0)
                self.assertTrue(required_codes & codes, (filename, codes))

    def test_schema_runtime_parity_regressions(self):
        cases = (
            ("atomic", "schema_atomic_missing_name.json"),
            ("complex", "schema_complex_missing_fields.json"),
            ("observe", "schema_observation_nonstring_state.json"),
        )
        for command, filename in cases:
            with self.subTest(filename=filename):
                status, payload = self.invoke(command, ROOT / "examples" / filename)
                self.assertEqual(status, 2)
                self.assertEqual(payload["decision"], "prohibited")
                self.assertIn("SCHEMA_VALIDATION", {finding["code"] for finding in payload["findings"]})

    def test_execution_ledger_records_a_semantic_short_circuit(self):
        raw = json.loads((ROOT / "examples" / "claim_valid.json").read_text(encoding="utf-8"))
        raw["representation"] = {"kind": "exact_quotient"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "short-circuit.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            status, payload = self.invoke("audit", path)
        self.assertEqual(status, 2)
        self.assertIn("claim_manifest_lint", payload["checks"]["run"])
        self.assertIn("gate_product", payload["checks"]["not_run"])
        self.assertNotIn("gate_product", payload["checks"]["run"])


if __name__ == "__main__":
    unittest.main()
