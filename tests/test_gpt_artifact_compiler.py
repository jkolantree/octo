import base64
import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from bsc_audit.cli import main as bsc_main
from bsc_audit.return_desk import CANONICAL_ACTIVITIES
from scripts.gpt_artifact_compiler import (
    BOUND_REPORT_ARTIFACT,
    BOUND_RETURN_ARTIFACT,
    BOUND_RUNTIME_ARTIFACT,
    CANONICAL_EXECUTION_ACTIVITIES,
    REPORT_PROJECTION_MARKER,
    export_payload_wrapper,
    finalize_candidate_artifacts,
    main as compiler_main,
    sha256_bytes,
    transport_fallback_prompt,
)


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = "3.12.13 (main, Jun  3 2026, 10:00:00) [MSC v.1944 64 bit (AMD64)]"


class GptArtifactCompilerTests(unittest.TestCase):
    def template(self) -> dict:
        value = json.loads(
            (ROOT / "examples" / "audit_return_valid.json").read_text(
                encoding="utf-8"
            )
        )
        report = next(
            artifact
            for artifact in value["artifacts"]
            if artifact["id"] == "artifact:report"
        )
        report.update(
            filename=BOUND_REPORT_ARTIFACT,
            media_type="text/markdown",
            sha256="sha256:" + "0" * 64,
        )
        value["artifacts"].append(
            {
                "id": "artifact:data-analysis-output",
                "filename": BOUND_RUNTIME_ARTIFACT,
                "role": "execution_output",
                "media_type": "text/plain",
                "sha256": "sha256:" + "0" * 64,
            }
        )
        return value

    def frozen(self) -> dict[str, bytes]:
        return {
            name: (ROOT / "examples" / name).read_bytes()
            for name in (
                "claim_valid.json",
                "atomic_modulus_valid.json",
                "defect_composition_valid.json",
            )
        }

    def finalize(self, template: dict | None = None):
        return finalize_candidate_artifacts(
            session_reported_runtime=RUNTIME,
            report_body=(
                "# BSC audit report\n\n"
                "The finite control was reconstructed and checked from the supplied "
                "bytes. Canonical claims, dependencies, gates, and summary follow."
            ),
            frozen_artifacts=self.frozen(),
            audit_return_template=self.template() if template is None else template,
        )

    def replay(self, files: dict[str, bytes]) -> tuple[int, dict]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for filename, data in files.items():
                (root / filename).write_bytes(data)
            output = io.StringIO()
            with redirect_stdout(output):
                status = bsc_main(
                    ["return-desk", str(root / BOUND_RETURN_ARTIFACT)]
                )
            return status, json.loads(output.getvalue())

    def test_schema_complete_transaction_passes_return_desk_end_to_end(self):
        finalized = self.finalize()
        status, result = self.replay(finalized.files)
        self.assertEqual(status, 0, result)
        self.assertEqual(result["decision"], "no_blocking_findings")
        self.assertEqual(list(finalized.files)[-1], BOUND_RETURN_ARTIFACT)

        execution = {
            row["activity"]: row for row in finalized.audit_return["execution"]
        }
        request_and_sources = {
            row["id"]
            for row in finalized.audit_return["artifacts"]
            if row["role"] in {"request", "source"}
        }
        generated = {
            row["id"]
            for row in finalized.audit_return["artifacts"]
            if row["role"] not in {"request", "source"}
        }
        evidence_and_report = {
            row["id"]
            for row in finalized.audit_return["artifacts"]
            if row["role"] in {"evidence", "report"}
        }
        self.assertEqual(
            set(execution["model_reasoning"]["input_artifact_ids"]),
            request_and_sources,
        )
        self.assertEqual(
            set(execution["model_reasoning"]["output_artifact_ids"]),
            evidence_and_report,
        )
        self.assertEqual(execution["model_reasoning"]["receipt_ids"], [])
        self.assertEqual(
            set(execution["chatgpt_data_analysis"]["input_artifact_ids"]),
            request_and_sources,
        )
        self.assertEqual(
            set(execution["chatgpt_data_analysis"]["output_artifact_ids"]),
            generated,
        )
        self.assertEqual(execution["chatgpt_data_analysis"]["receipt_ids"], [])

    def test_report_projection_comes_from_the_return_semantic_object(self):
        template = self.template()
        template["claims"][0]["depends_on"] = []
        finalized = self.finalize(template)
        report = finalized.files[BOUND_REPORT_ARTIFACT].decode("utf-8")
        self.assertEqual(report.count(REPORT_PROJECTION_MARKER), 1)
        projection_text = report.split("```json\n", 1)[1].split("```\n", 1)[0]
        projection = json.loads(projection_text)
        self.assertEqual(
            projection["claims"][0]["depends_on"],
            finalized.audit_return["claims"][0]["depends_on"],
        )
        self.assertEqual(
            projection["summary_projection"],
            finalized.audit_return["summary_projection"],
        )
        projected_execution = {
            row["activity"]: row for row in projection["execution"]
        }
        return_execution = {
            row["activity"]: row for row in finalized.audit_return["execution"]
        }
        self.assertEqual(
            {
                activity: row["status"]
                for activity, row in projected_execution.items()
            },
            {
                activity: row["status"]
                for activity, row in return_execution.items()
            },
        )
        self.assertIsNone(
            projected_execution["chatgpt_data_analysis"]["version"]
        )
        self.assertEqual(
            projected_execution["chatgpt_data_analysis"]["version_reference"],
            BOUND_RUNTIME_ARTIFACT,
        )

    def test_compiler_repairs_missing_request_and_incomplete_output_rosters(self):
        template = self.template()
        execution = {row["activity"]: row for row in template["execution"]}
        execution["model_reasoning"]["input_artifact_ids"] = []
        execution["model_reasoning"]["output_artifact_ids"] = []
        execution["chatgpt_data_analysis"]["input_artifact_ids"] = []
        execution["chatgpt_data_analysis"]["output_artifact_ids"] = []
        finalized = self.finalize(template)
        repaired = {
            row["activity"]: row for row in finalized.audit_return["execution"]
        }
        self.assertIn(
            "artifact:request",
            repaired["model_reasoning"]["input_artifact_ids"],
        )
        self.assertIn(
            "artifact:request",
            repaired["chatgpt_data_analysis"]["input_artifact_ids"],
        )
        self.assertIn(
            "artifact:report",
            repaired["chatgpt_data_analysis"]["output_artifact_ids"],
        )
        self.assertIn(
            "artifact:evidence",
            repaired["chatgpt_data_analysis"]["output_artifact_ids"],
        )
        self.assertIn(
            "artifact:data-analysis-output",
            repaired["chatgpt_data_analysis"]["output_artifact_ids"],
        )

    def test_execution_output_cannot_be_misrepresented_as_a_receipt(self):
        template = self.template()
        template["receipts"].append(
            {
                "id": "receipt:da",
                "artifact_id": "artifact:data-analysis-output",
                "claim_ids": ["claim:fixture"],
                "gate_ids": ["gate:structural-consistency"],
            }
        )
        with self.assertRaisesRegex(ValueError, "role-receipt"):
            self.finalize(template)

    def test_complete_execution_roster_is_compiler_owned_and_canonical(self):
        template = self.template()
        execution = {row["activity"]: row for row in template["execution"]}
        execution["empirical_test"].update(
            status="not_applicable",
            notes="The target is a pure mathematical theorem.",
        )
        execution["proposed_computation"].update(
            status="not_run",
            tool="Lean 4 or equivalent",
            notes="A proof-assistant replay is proposed only.",
        )
        template["execution"] = list(reversed(template["execution"]))

        finalized = self.finalize(template)
        rows = finalized.audit_return["execution"]
        self.assertEqual(
            tuple(row["activity"] for row in rows),
            CANONICAL_EXECUTION_ACTIVITIES,
        )
        self.assertEqual(CANONICAL_EXECUTION_ACTIVITIES, CANONICAL_ACTIVITIES)
        normalized = {row["activity"]: row for row in rows}
        for activity in ("empirical_test", "proposed_computation"):
            self.assertEqual(normalized[activity]["status"], "not_run")
            self.assertIsNone(normalized[activity]["tool"])
            self.assertIsNone(normalized[activity]["version"])
            self.assertEqual(normalized[activity]["input_artifact_ids"], [])
            self.assertEqual(normalized[activity]["output_artifact_ids"], [])
            self.assertEqual(normalized[activity]["receipt_ids"], [])
        status, result = self.replay(finalized.files)
        self.assertEqual(status, 0, result)

    def test_incomplete_or_unknown_execution_roster_blocks_before_serialization(self):
        missing = self.template()
        missing["execution"] = missing["execution"][:-1]
        with self.assertRaisesRegex(ValueError, "canonical activity"):
            self.finalize(missing)

        unknown = self.template()
        unknown["execution"][-1]["activity"] = "invented_activity"
        with self.assertRaisesRegex(ValueError, "roster"):
            self.finalize(unknown)

        duplicate = self.template()
        duplicate["execution"][-1]["activity"] = "empirical_test"
        with self.assertRaisesRegex(ValueError, "roster"):
            self.finalize(duplicate)

    def test_unexecuted_status_cannot_hide_bound_output(self):
        template = self.template()
        empirical = next(
            row
            for row in template["execution"]
            if row["activity"] == "empirical_test"
        )
        empirical["status"] = "not_run"
        empirical["output_artifact_ids"] = ["artifact:evidence"]
        with self.assertRaisesRegex(ValueError, "contradicts outputs"):
            self.finalize(template)

    def test_same_length_post_freeze_report_mutation_is_not_rescued(self):
        finalized = self.finalize()
        mutated = dict(finalized.files)
        original = mutated[BOUND_REPORT_ARTIFACT]
        marker = b"finite control"
        replacement = b"FINITE CONTROL"
        self.assertEqual(len(marker), len(replacement))
        self.assertIn(marker, original)
        mutated[BOUND_REPORT_ARTIFACT] = original.replace(
            marker,
            replacement,
            1,
        )
        status, result = self.replay(mutated)
        self.assertNotEqual(status, 0)
        self.assertEqual(result["decision"], "blocked")
        self.assertTrue(
            any(
                finding["code"] == "RETURN_ARTIFACT_BINDING_INVALID"
                for finding in result["findings"]
            )
        )

    def test_export_wrapper_fields_derive_from_one_payload_and_detect_omission(self):
        payload = b"independently::aligned-quartet::end"
        wrapper = export_payload_wrapper("audit_report.md", payload)
        decoded = base64.b64decode(wrapper["base64"], validate=True)
        self.assertEqual(decoded, payload)
        self.assertEqual(wrapper["size_bytes"], len(decoded))
        self.assertEqual(wrapper["sha256"], sha256_bytes(decoded))

        quartet = wrapper["base64"][4:8]
        omitted = wrapper["base64"].replace(quartet, "", 1)
        mutated = base64.b64decode(omitted, validate=True)
        self.assertNotEqual(mutated, payload)
        self.assertTrue(
            len(mutated) != wrapper["size_bytes"]
            or sha256_bytes(mutated) != wrapper["sha256"]
        )

    def test_export_wrapper_cli_fresh_reads_and_preserves_terminal_lf(self):
        with tempfile.TemporaryDirectory() as temporary:
            payload_path = Path(temporary) / "audit_report.md"
            original = b"independently::aligned-quartet::ZW5k\n\n"
            payload_path.write_bytes(original)
            output = io.StringIO()
            with redirect_stdout(output):
                status = compiler_main(["export-wrapper", str(payload_path)])
            self.assertEqual(status, 0)
            wrapper = json.loads(output.getvalue())
            self.assertEqual(
                base64.b64decode(wrapper["base64"], validate=True),
                original,
            )
            self.assertEqual(wrapper["size_bytes"], len(original))
            self.assertEqual(wrapper["sha256"], sha256_bytes(original))

            changed = original[:-1]
            payload_path.write_bytes(changed)
            output = io.StringIO()
            with redirect_stdout(output):
                status = compiler_main(["export-wrapper", str(payload_path)])
            self.assertEqual(status, 0)
            changed_wrapper = json.loads(output.getvalue())
            self.assertEqual(
                base64.b64decode(changed_wrapper["base64"], validate=True),
                changed,
            )
            self.assertNotEqual(changed_wrapper["sha256"], wrapper["sha256"])
            self.assertEqual(changed_wrapper["size_bytes"], len(changed))

    def test_transport_prompt_contains_literal_fresh_read_command(self):
        prompt = transport_fallback_prompt("audit_report.md")
        self.assertIn(
            "python /mnt/data/gpt_artifact_compiler.py export-wrapper "
            "/mnt/data/audit_report.md",
            prompt,
        )
        self.assertIn("Do not read, trim, normalize, or encode", prompt)
        self.assertIn("complete stdout byte-for-byte", prompt)

    def test_compiler_does_not_mutate_the_supplied_template(self):
        template = self.template()
        before = copy.deepcopy(template)
        self.finalize(template)
        self.assertEqual(template, before)


if __name__ == "__main__":
    unittest.main()
