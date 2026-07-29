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

    def test_legacy_hash_only_control_fails_closed(self):
        status, payload = self.invoke("audit", ROOT / "examples" / "claim_valid.json")
        self.assertEqual(status, 1)
        self.assertEqual(payload["decision"], "blocked")
        self.assertTrue(
            {
                "EVIDENCE_MATURITY_UNSUPPORTED",
                "GATE_RESULT_UNVERIFIED",
            }.issubset(
                {finding["code"] for finding in payload["findings"]}
            )
        )

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
            ("holonomy", "schema_holonomy_missing_projection.json"),
            ("observe", "schema_observation_nonstring_state.json"),
        )
        for command, filename in cases:
            with self.subTest(filename=filename):
                status, payload = self.invoke(command, ROOT / "examples" / filename)
                self.assertEqual(status, 2)
                self.assertEqual(payload["decision"], "prohibited")
                self.assertIn("SCHEMA_VALIDATION", {finding["code"] for finding in payload["findings"]})

    def test_exact_holonomy_success_is_explicitly_non_admissive(self):
        status, payload = self.invoke(
            "holonomy",
            ROOT / "examples" / "holonomy_observed_exact_kernel_pass.json",
        )
        self.assertEqual(status, 0)
        self.assertEqual(payload["decision"], "no_blocking_findings_with_warnings")
        boundary = next(
            finding
            for finding in payload["findings"]
            if finding["code"] == "HOLONOMY_EXTERNAL_INTERPRETATION_NON_ADMISSIBLE"
        )
        self.assertEqual(boundary["severity"], "WARNING")
        self.assertEqual(
            boundary["witness"],
            {
                "authority": "non_admissive_declared_input",
                "algebraic_scope": "declared_finite_maps",
                "scientific_truth": "not_established",
                "source_authenticity": "not_established",
            },
        )

    def test_audit_return_controls_and_poisoned_mutations_are_distinguished(self):
        control_status, control = self.invoke("return-desk", ROOT / "examples" / "audit_return_valid.json")
        self.assertEqual(control_status, 0)
        self.assertEqual(control["decision"], "no_blocking_findings")

        cases = (
            ("audit_return_poisoned_summary.json", "RETURN_SUMMARY_VERDICT_MISMATCH"),
            ("audit_return_omitted_bound_failure.json", "RETURN_CONCEALED_GATE_FAILURE"),
            ("audit_return_unreceipted_execution.json", "RETURN_EXECUTION_RECORD_INADEQUATE"),
            ("audit_return_missing_source_promotion.json", "RETURN_PROVEN_WITH_SOURCE_GAP"),
            ("audit_return_deployment_overreach.json", "RETURN_DEPLOYMENT_AUTHORITY_MISSING"),
            ("audit_return_receipt_only_promotion.json", "RETURN_RECEIPT_ONLY_PROMOTION"),
        )
        for filename, required_code in cases:
            with self.subTest(filename=filename):
                status, payload = self.invoke("return-desk", ROOT / "examples" / filename)
                self.assertEqual(status, 1)
                self.assertIn(required_code, {finding["code"] for finding in payload["findings"]})

        review_status, review = self.invoke("return-desk", ROOT / "examples" / "audit_return_missing_artifact.json")
        self.assertEqual(review_status, 0)
        self.assertEqual(review["decision"], "no_blocking_findings_with_warnings")
        self.assertIn("RETURN_ARTIFACT_UNAVAILABLE", {finding["code"] for finding in review["findings"]})

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
