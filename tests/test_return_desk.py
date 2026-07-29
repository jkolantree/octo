import copy
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from bsc_audit.cli import main
from bsc_audit.return_desk import (
    EXPECTED_PROTOCOL_SHA256,
    EXPECTED_PROTOCOL_VERSION,
    MAX_RETURN_TOTAL_ARTIFACT_BYTES,
    _portable_filename,
)


ROOT = Path(__file__).resolve().parents[1]
VALID_PATH = ROOT / "examples" / "audit_return_valid.json"
VERSIONED_REPORT_NAME = "versioned-audit-report.txt"
VERSIONED_OUTPUT_NAME = "versioned-bsc-output.txt"
VERSIONED_REPORT_BYTES = (
    b"Execution details: see the bound versioned-bsc-output.txt artifact.\n"
)
VERSIONED_OUTPUT_BYTES = b"tool=bsc-audit\nversion=0.3.0a10\n"
SESSION_RUNTIME = "3.12.13 (session-reported test runtime)"
DA_REPORT_BYTES = b"Execution details: see chatgpt_data_analysis_output.txt.\n"
DA_OUTPUT_BYTES = (
    "bsc_chatgpt_data_analysis_output_version: 2\n"
    f"session_reported_runtime={SESSION_RUNTIME}\n"
    "runtime_provenance=session_reported\n"
    "finalized_artifacts:\n"
).encode("utf-8")


class AuditReturnDeskTests(unittest.TestCase):
    def invoke(self, path: Path) -> tuple[int, dict]:
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["return-desk", str(path)])
        return status, json.loads(output.getvalue())

    def valid(self) -> dict:
        return json.loads(VALID_PATH.read_text(encoding="utf-8"))

    def write_with_artifacts(self, directory: str, raw: dict) -> Path:
        root = Path(directory)
        for artifact in raw.get("artifacts", []):
            source = ROOT / "examples" / artifact["filename"]
            if source.is_file():
                shutil.copyfile(source, root / artifact["filename"])
            elif artifact["filename"] == VERSIONED_REPORT_NAME:
                (root / VERSIONED_REPORT_NAME).write_bytes(VERSIONED_REPORT_BYTES)
            elif artifact["filename"] == VERSIONED_OUTPUT_NAME:
                (root / VERSIONED_OUTPUT_NAME).write_bytes(VERSIONED_OUTPUT_BYTES)
        path = root / "return.json"
        path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        return path

    def add_artifact(self, raw: dict, identifier: str, filename: str, role: str) -> None:
        data = (ROOT / "examples" / filename).read_bytes()
        raw["artifacts"].append(
            {
                "id": identifier,
                "filename": filename,
                "role": role,
                "media_type": "application/json",
                "sha256": f"sha256:{hashlib.sha256(data).hexdigest()}",
            }
        )

    def replace_artifact_bytes(
        self,
        raw: dict,
        identifier: str,
        filename: str,
        media_type: str,
        data: bytes,
    ) -> None:
        artifact = next(item for item in raw["artifacts"] if item["id"] == identifier)
        artifact.update(
            filename=filename,
            media_type=media_type,
            sha256=f"sha256:{hashlib.sha256(data).hexdigest()}",
        )

    def bind_effective_bsc_run(self, raw: dict) -> None:
        report = next(item for item in raw["artifacts"] if item["id"] == raw["bindings"]["report_artifact_id"])
        report.update(
            filename=VERSIONED_REPORT_NAME,
            media_type="text/plain; charset=utf-8",
            sha256=f"sha256:{hashlib.sha256(VERSIONED_REPORT_BYTES).hexdigest()}",
        )
        raw["artifacts"].append(
            {
                "id": "artifact:bsc-output",
                "filename": VERSIONED_OUTPUT_NAME,
                "role": "execution_output",
                "media_type": "text/plain; charset=utf-8",
                "sha256": f"sha256:{hashlib.sha256(VERSIONED_OUTPUT_BYTES).hexdigest()}",
            }
        )
        self.add_artifact(raw, "artifact:bsc-receipt", "atomic_modulus_evasion.json", "receipt")
        raw["receipts"].append(
            {
                "id": "receipt:bsc",
                "authority": "execution_record",
                "kind": "bsc_cli_output",
                "artifact_id": "artifact:bsc-receipt",
                "claim_ids": ["claim:fixture"],
                "gate_ids": ["gate:structural-consistency"],
                "status": "verified",
            }
        )
        run = next(item for item in raw["execution"] if item["activity"] == "bsc_python_checker")
        run.update(
            status="ran",
            tool="bsc-audit",
            version="0.3.0a10",
            input_artifact_ids=["artifact:request", "artifact:source"],
            output_artifact_ids=["artifact:bsc-output"],
            receipt_ids=["receipt:bsc"],
            notes="Bound positive control for execution-to-evidence linkage.",
        )
        raw["evidence"][0].update(
            artifact_ids=["artifact:bsc-output", "artifact:bsc-receipt"],
            execution_activities=["bsc_python_checker"],
            receipt_ids=["receipt:bsc"],
        )

    def test_schema_mirror_is_exact(self):
        canonical = (ROOT / "schemas" / "audit-return-v0.1.schema.json").read_bytes()
        packaged = (ROOT / "src" / "bsc_audit" / "schema_data" / "audit-return-v0.1.schema.json").read_bytes()
        self.assertEqual(canonical, packaged)

    def test_return_fixtures_bind_the_exact_current_protocol(self):
        protocol = (ROOT / "BSC_AUDIT_LLM_PACKET.md").read_bytes()
        self.assertEqual(EXPECTED_PROTOCOL_SHA256, f"sha256:{hashlib.sha256(protocol).hexdigest()}")
        self.assertEqual(EXPECTED_PROTOCOL_VERSION, "0.3.0-alpha.10")
        for path in sorted((ROOT / "examples").glob("audit_return_*.json")):
            with self.subTest(path=path.name):
                record = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(record["protocol"]["version"], EXPECTED_PROTOCOL_VERSION)
                self.assertEqual(record["protocol"]["sha256"], EXPECTED_PROTOCOL_SHA256)

    def test_protocol_version_and_hash_drift_block(self):
        version_drift = self.valid()
        version_drift["protocol"]["version"] = "0.3.0-alpha.7"
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, version_drift))
        self.assertEqual(status, 1)
        self.assertIn("RETURN_PROTOCOL_VERSION_MISMATCH", {finding["code"] for finding in payload["findings"]})

        hash_drift = self.valid()
        hash_drift["protocol"]["sha256"] = "sha256:" + "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, hash_drift))
        self.assertEqual(status, 1)
        self.assertIn("RETURN_PROTOCOL_HASH_MISMATCH", {finding["code"] for finding in payload["findings"]})

    def test_valid_control_is_internally_consistent_but_explicitly_nonadmissive(self):
        status, payload = self.invoke(VALID_PATH)
        codes = {finding["code"] for finding in payload["findings"]}
        self.assertEqual(status, 0)
        self.assertEqual(payload["decision"], "no_blocking_findings")
        self.assertIn("RETURN_INTERNALLY_CONSISTENT", codes)
        self.assertIn("RETURN_DESK_NON_ADMISSIVE", codes)
        self.assertIn("schema_validation:return-desk", payload["checks"]["run"])
        self.assertIn("non_admissive_audit_return_inspection", payload["checks"]["run"])

    def test_verified_evidence_requires_a_bound_checking_activity(self):
        raw = self.valid()
        raw["evidence"][0]["execution_activities"] = []
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, raw))
        codes = {finding["code"] for finding in payload["findings"]}
        self.assertEqual(status, 1)
        self.assertIn("RETURN_GATE_STATE_MISMATCH", codes)
        self.assertIn("RETURN_EVIDENCE_UNVERIFIED_LOCALLY", codes)

    def test_ineffective_receipt_only_nonpassing_evidence_needs_review(self):
        for evidence_result in ("fail", "inconclusive"):
            with self.subTest(evidence_result=evidence_result):
                raw = self.valid()
                next(item for item in raw["artifacts"] if item["id"] == "artifact:evidence")["role"] = "receipt"
                raw["evidence"][0]["result"] = evidence_result
                raw["fatal_gates"][0].update(state="unrun", obligation_ids=["obligation:review"])
                raw["summary_projection"].update(admission="unrun", unresolved_obligation_ids=["obligation:review"])
                raw["unresolved_obligations"] = [{
                    "id": "obligation:review",
                    "statement": "Verify the evidence with a substantive, locally bound artifact.",
                    "claim_ids": ["claim:fixture"],
                    "gate_ids": ["gate:structural-consistency"],
                    "evidence_ids": ["evidence:structural-check"],
                }]
                with tempfile.TemporaryDirectory() as directory:
                    status, payload = self.invoke(self.write_with_artifacts(directory, raw))
                self.assertEqual(status, 0)
                self.assertEqual(payload["decision"], "no_blocking_findings_with_warnings")
                self.assertIn("RETURN_EVIDENCE_UNVERIFIED_LOCALLY", {finding["code"] for finding in payload["findings"]})

    def test_schema_equality_and_unicode_lengths_match_json_schema(self):
        bool_as_number = self.valid()
        bool_as_number["draft"] = 1
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, bool_as_number))
        self.assertEqual(status, 2)
        self.assertEqual(payload["decision"], "prohibited")
        self.assertIn("SCHEMA_VALIDATION", {finding["code"] for finding in payload["findings"]})

        trailing_newline = self.valid()
        trailing_newline["claims"][0]["id"] = "claim:fixture\n"
        trailing_newline["primary_claim_id"] = "claim:fixture\n"
        trailing_newline["summary_projection"]["primary_claim_id"] = "claim:fixture\n"
        trailing_newline["evidence"][0]["claim_ids"] = ["claim:fixture\n"]
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, trailing_newline))
        self.assertEqual(status, 2)
        self.assertEqual(payload["decision"], "prohibited")
        self.assertIn("SCHEMA_VALIDATION", {finding["code"] for finding in payload["findings"]})

        at_limit = self.valid()
        at_limit["claims"][0]["statement"] = "\U0001f600" * 16384
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, at_limit))
        self.assertEqual(status, 0)
        self.assertEqual(payload["decision"], "no_blocking_findings")

        over_limit = self.valid()
        over_limit["claims"][0]["statement"] = "\U0001f600" * 16385
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, over_limit))
        self.assertEqual(status, 2)
        self.assertEqual(payload["decision"], "prohibited")
        self.assertIn("SCHEMA_VALIDATION", {finding["code"] for finding in payload["findings"]})

    def test_registered_poisoned_returns_are_blocked_by_the_expected_gate(self):
        cases = (
            ("audit_return_poisoned_summary.json", "RETURN_SUMMARY_VERDICT_MISMATCH"),
            ("audit_return_omitted_bound_failure.json", "RETURN_CONCEALED_GATE_FAILURE"),
            ("audit_return_unreceipted_execution.json", "RETURN_EXECUTION_RECORD_INADEQUATE"),
            ("audit_return_missing_source_promotion.json", "RETURN_PROVEN_WITH_SOURCE_GAP"),
            ("audit_return_deployment_overreach.json", "RETURN_DEPLOYMENT_AUTHORITY_MISSING"),
            ("audit_return_receipt_only_promotion.json", "RETURN_RECEIPT_ONLY_PROMOTION"),
        )
        for filename, expected_code in cases:
            with self.subTest(filename=filename):
                status, payload = self.invoke(ROOT / "examples" / filename)
                self.assertEqual(status, 1)
                self.assertEqual(payload["decision"], "blocked")
                self.assertIn(expected_code, {finding["code"] for finding in payload["findings"]})

    def test_missing_local_artifact_needs_review_without_becoming_a_false_failure(self):
        status, payload = self.invoke(ROOT / "examples" / "audit_return_missing_artifact.json")
        codes = {finding["code"] for finding in payload["findings"]}
        self.assertEqual(status, 0)
        self.assertEqual(payload["decision"], "no_blocking_findings_with_warnings")
        self.assertIn("RETURN_ARTIFACT_UNAVAILABLE", codes)
        self.assertIn("RETURN_INTERNALLY_CONSISTENT", codes)

    def test_hash_mismatch_blocks_instead_of_degrading_to_a_warning(self):
        raw = self.valid()
        raw["artifacts"][0]["sha256"] = "sha256:" + "f" * 64
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, raw))
        self.assertEqual(status, 1)
        self.assertIn("RETURN_ARTIFACT_BINDING_INVALID", {finding["code"] for finding in payload["findings"]})

    def test_verified_text_artifacts_require_strict_utf8_and_safe_controls(self):
        allowed_bytes = b"proof line\tvalue\r\nliteral \\\\forall x\n"
        allowed = self.valid()
        self.replace_artifact_bytes(
            allowed,
            "artifact:evidence",
            "verified-evidence.txt",
            "text/plain; charset=utf-8",
            allowed_bytes,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_with_artifacts(directory, allowed)
            (Path(directory) / "verified-evidence.txt").write_bytes(allowed_bytes)
            status, payload = self.invoke(path)
        self.assertEqual(status, 0, payload)
        self.assertNotIn(
            "RETURN_ARTIFACT_TEXT_CONTROL_INVALID",
            {item["code"] for item in payload["findings"]},
        )

        invalid_utf8_bytes = b"proof:\xff"
        invalid_utf8 = self.valid()
        self.replace_artifact_bytes(
            invalid_utf8,
            "artifact:evidence",
            "invalid-utf8.txt",
            "text/plain",
            invalid_utf8_bytes,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_with_artifacts(directory, invalid_utf8)
            (Path(directory) / "invalid-utf8.txt").write_bytes(invalid_utf8_bytes)
            status, payload = self.invoke(path)
        self.assertEqual(status, 1)
        self.assertIn(
            "RETURN_ARTIFACT_TEXT_ENCODING_INVALID",
            {item["code"] for item in payload["findings"]},
        )

        for control in (0x00, 0x0B, 0x0C, 0x1B, 0x7F):
            with self.subTest(control=f"0x{control:02X}"):
                controlled_bytes = b"proof:" + bytes([control])
                controlled = self.valid()
                self.replace_artifact_bytes(
                    controlled,
                    "artifact:evidence",
                    "controlled-evidence.txt",
                    "text/plain",
                    controlled_bytes,
                )
                with tempfile.TemporaryDirectory() as directory:
                    path = self.write_with_artifacts(directory, controlled)
                    (Path(directory) / "controlled-evidence.txt").write_bytes(controlled_bytes)
                    status, payload = self.invoke(path)
                self.assertEqual(status, 1)
                self.assertIn(
                    "RETURN_ARTIFACT_TEXT_CONTROL_INVALID",
                    {item["code"] for item in payload["findings"]},
                )

    def test_browser_ambiguous_filename_and_path_are_fail_closed(self):
        duplicate = self.valid()
        duplicate["artifacts"][1]["filename"] = duplicate["artifacts"][0]["filename"]
        duplicate["artifacts"][1]["sha256"] = duplicate["artifacts"][0]["sha256"]
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, duplicate))
        self.assertEqual(status, 1)
        self.assertIn("RETURN_DUPLICATE_FILENAME", {finding["code"] for finding in payload["findings"]})

        unsafe = self.valid()
        unsafe["artifacts"][0]["filename"] = "evidence/claim_valid.json"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "return.json"
            path.write_text(json.dumps(unsafe), encoding="utf-8")
            status, payload = self.invoke(path)
        self.assertEqual(status, 2)
        self.assertEqual(payload["decision"], "prohibited")
        self.assertIn("SCHEMA_VALIDATION", {finding["code"] for finding in payload["findings"]})

    def test_execution_ledger_requires_each_activity_exactly_once(self):
        raw = self.valid()
        raw["execution"][-1]["activity"] = "model_reasoning"
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, raw))
        self.assertEqual(status, 1)
        self.assertIn("RETURN_EXECUTION_LEDGER_INCOMPLETE", {finding["code"] for finding in payload["findings"]})

    def test_unrun_critical_activities_use_not_run_not_not_applicable(self):
        canonical = self.valid()
        for activity in ("bsc_python_checker", "external_proof_tool", "empirical_test"):
            self.assertEqual(
                next(item for item in canonical["execution"] if item["activity"] == activity)["status"],
                "not_run",
            )

        for activity in ("bsc_python_checker", "external_proof_tool", "empirical_test"):
            with self.subTest(activity=activity):
                raw = self.valid()
                next(item for item in raw["execution"] if item["activity"] == activity)["status"] = "not_applicable"
                with tempfile.TemporaryDirectory() as directory:
                    status, payload = self.invoke(self.write_with_artifacts(directory, raw))
                self.assertEqual(status, 1)
                self.assertIn(
                    "RETURN_EXECUTION_NOT_APPLICABLE_MISUSED",
                    {item["code"] for item in payload["findings"]},
                )

    def test_file_read_only_is_precise_and_cannot_support_evidence(self):
        raw = self.valid()
        data_analysis = next(item for item in raw["execution"] if item["activity"] == "chatgpt_data_analysis")
        data_analysis.update(
            status="file_read_only",
            tool="ChatGPT Data Analysis",
            version="unreported",
            input_artifact_ids=["artifact:request"],
        )
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, raw))
        self.assertEqual(status, 0)
        self.assertEqual(payload["decision"], "no_blocking_findings")

        relied_upon = copy.deepcopy(raw)
        relied_upon["evidence"][0]["execution_activities"] = ["chatgpt_data_analysis"]
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, relied_upon))
        codes = {finding["code"] for finding in payload["findings"]}
        self.assertEqual(status, 1)
        self.assertIn("RETURN_FILE_READ_PROMOTION", codes)
        self.assertIn("RETURN_UNSUPPORTED_EXECUTION_EVIDENCE", codes)

    def test_execution_evidence_receipt_and_input_bindings_are_exact(self):
        positive = self.valid()
        self.bind_effective_bsc_run(positive)
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, positive))
        self.assertEqual(status, 0, payload)
        self.assertEqual(payload["decision"], "no_blocking_findings")

        unrelated = self.valid()
        model_reasoning = next(item for item in unrelated["execution"] if item["activity"] == "model_reasoning")
        model_reasoning["output_artifact_ids"] = ["artifact:report"]
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, unrelated))
        self.assertEqual(status, 1)
        self.assertIn("RETURN_EVIDENCE_EXECUTION_BINDING_MISMATCH", {item["code"] for item in payload["findings"]})

        wrong_input = copy.deepcopy(positive)
        run = next(item for item in wrong_input["execution"] if item["activity"] == "bsc_python_checker")
        run["input_artifact_ids"] = ["artifact:request"]
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, wrong_input))
        self.assertEqual(status, 1)
        self.assertIn("RETURN_EVIDENCE_EXECUTION_INPUT_UNBOUND", {item["code"] for item in payload["findings"]})

        wrong_scope = copy.deepcopy(positive)
        wrong_scope["receipts"][0]["claim_ids"] = []
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, wrong_scope))
        self.assertEqual(status, 1)
        self.assertIn("RETURN_RECEIPT_SCOPE_MISMATCH", {item["code"] for item in payload["findings"]})

        duplicate_receipt = copy.deepcopy(positive)
        duplicate_receipt["receipts"].append({**duplicate_receipt["receipts"][0], "id": "receipt:copy"})
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, duplicate_receipt))
        self.assertEqual(status, 1)
        self.assertIn("RETURN_RECEIPT_ARTIFACT_REUSED", {item["code"] for item in payload["findings"]})

    def test_every_verified_role_evidence_artifact_is_a_cited_execution_output(self):
        positive = self.valid()
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, positive))
        self.assertEqual(status, 0, payload)
        self.assertNotIn(
            "RETURN_EVIDENCE_SUPPORT_OUTPUT_MISMATCH",
            {item["code"] for item in payload["findings"]},
        )

        decoy = self.valid()
        self.add_artifact(decoy, "artifact:decoy-output", "observation_failure.json", "execution_output")
        decoy["evidence"][0]["artifact_ids"] = ["artifact:evidence", "artifact:decoy-output"]
        model_reasoning = next(item for item in decoy["execution"] if item["activity"] == "model_reasoning")
        model_reasoning["output_artifact_ids"] = ["artifact:report", "artifact:decoy-output"]
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, decoy))
        self.assertEqual(status, 1)
        self.assertIn(
            "RETURN_EVIDENCE_SUPPORT_OUTPUT_MISMATCH",
            {item["code"] for item in payload["findings"]},
        )

    def test_ran_nonmodel_version_binds_output_and_report_references_it(self):
        positive = self.valid()
        self.bind_effective_bsc_run(positive)
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, positive))
        self.assertEqual(status, 0, payload)
        self.assertNotIn(
            "RETURN_EXECUTION_VERSION_UNBOUND",
            {item["code"] for item in payload["findings"]},
        )
        self.assertNotIn(
            "0.3.0a10",
            VERSIONED_REPORT_BYTES.decode("utf-8"),
        )

        absent = copy.deepcopy(positive)
        run = next(item for item in absent["execution"] if item["activity"] == "bsc_python_checker")
        run["version"] = "0.3.0a10-not-in-output"
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, absent))
        self.assertEqual(status, 1)
        self.assertIn(
            "RETURN_EXECUTION_VERSION_UNBOUND",
            {item["code"] for item in payload["findings"]},
        )

    def test_data_analysis_runtime_is_one_session_reported_binding(self):
        positive = self.valid()
        report = next(
            item
            for item in positive["artifacts"]
            if item["id"] == positive["bindings"]["report_artifact_id"]
        )
        report.update(
            filename="da-report.txt",
            media_type="text/plain; charset=utf-8",
            sha256=f"sha256:{hashlib.sha256(DA_REPORT_BYTES).hexdigest()}",
        )
        positive["artifacts"].append(
            {
                "id": "artifact:da-output",
                "filename": "chatgpt_data_analysis_output.txt",
                "role": "execution_output",
                "media_type": "text/plain; charset=utf-8",
                "sha256": f"sha256:{hashlib.sha256(DA_OUTPUT_BYTES).hexdigest()}",
            }
        )
        run = next(
            item
            for item in positive["execution"]
            if item["activity"] == "chatgpt_data_analysis"
        )
        run.update(
            status="ran",
            tool="Python",
            version=SESSION_RUNTIME,
            input_artifact_ids=["artifact:request", "artifact:source"],
            output_artifact_ids=["artifact:da-output"],
            receipt_ids=[],
            notes="The runtime is session-reported, not independently authenticated.",
        )

        with tempfile.TemporaryDirectory() as directory:
            path = self.write_with_artifacts(directory, positive)
            Path(directory, "da-report.txt").write_bytes(DA_REPORT_BYTES)
            Path(directory, "chatgpt_data_analysis_output.txt").write_bytes(
                DA_OUTPUT_BYTES
            )
            status, payload = self.invoke(path)
        self.assertEqual(status, 0, payload)
        self.assertNotIn(SESSION_RUNTIME, DA_REPORT_BYTES.decode("utf-8"))

        row_bound = copy.deepcopy(positive)
        row_bound_run = next(
            item
            for item in row_bound["execution"]
            if item["activity"] == "chatgpt_data_analysis"
        )
        row_bound_run["output_artifact_ids"] = [
            "artifact:report",
            "artifact:da-output",
        ]
        row_bound_bytes = (
            "bsc_chatgpt_data_analysis_output_version: 2\n"
            f"session_reported_runtime={SESSION_RUNTIME}\n"
            "runtime_provenance=session_reported\n"
            "finalized_artifacts:\n"
            f"{hashlib.sha256(DA_REPORT_BYTES).hexdigest()}  "
            f"{len(DA_REPORT_BYTES)}  da-report.txt\n"
        ).encode("utf-8")
        row_bound_output = next(
            item
            for item in row_bound["artifacts"]
            if item["id"] == "artifact:da-output"
        )
        row_bound_output["sha256"] = (
            f"sha256:{hashlib.sha256(row_bound_bytes).hexdigest()}"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_with_artifacts(directory, row_bound)
            Path(directory, "da-report.txt").write_bytes(DA_REPORT_BYTES)
            Path(directory, "chatgpt_data_analysis_output.txt").write_bytes(
                row_bound_bytes
            )
            status, payload = self.invoke(path)
        self.assertEqual(status, 0, payload)

        for original, replacement in (
            (f"  {len(DA_REPORT_BYTES)}  ", "  999999  "),
            ("  da-report.txt\n", "  forged-name.md\n"),
        ):
            with self.subTest(replacement=replacement):
                malformed = copy.deepcopy(row_bound)
                bad_bytes = row_bound_bytes.replace(
                    original.encode("utf-8"),
                    replacement.encode("utf-8"),
                )
                output = next(
                    item
                    for item in malformed["artifacts"]
                    if item["id"] == "artifact:da-output"
                )
                output["sha256"] = (
                    f"sha256:{hashlib.sha256(bad_bytes).hexdigest()}"
                )
                with tempfile.TemporaryDirectory() as directory:
                    path = self.write_with_artifacts(directory, malformed)
                    Path(directory, "da-report.txt").write_bytes(DA_REPORT_BYTES)
                    Path(
                        directory, "chatgpt_data_analysis_output.txt"
                    ).write_bytes(bad_bytes)
                    status, payload = self.invoke(path)
                self.assertEqual(status, 1)
                self.assertIn(
                    "RETURN_DATA_ANALYSIS_RUNTIME_BINDING_INVALID",
                    {item["code"] for item in payload["findings"]},
                )

        wrong_provenance = copy.deepcopy(positive)
        bad_bytes = (
            f"session_reported_runtime={SESSION_RUNTIME}\n"
            "runtime_provenance=independently_authenticated\n"
        ).encode("utf-8")
        output = next(
            item
            for item in wrong_provenance["artifacts"]
            if item["id"] == "artifact:da-output"
        )
        output["sha256"] = f"sha256:{hashlib.sha256(bad_bytes).hexdigest()}"
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_with_artifacts(directory, wrong_provenance)
            Path(directory, "da-report.txt").write_bytes(DA_REPORT_BYTES)
            Path(directory, "chatgpt_data_analysis_output.txt").write_bytes(
                bad_bytes
            )
            status, payload = self.invoke(path)
        self.assertEqual(status, 1)
        self.assertIn(
            "RETURN_DATA_ANALYSIS_RUNTIME_BINDING_INVALID",
            {item["code"] for item in payload["findings"]},
        )

        malformed_bindings = (
            DA_OUTPUT_BYTES
            + f"session_reported_runtime={SESSION_RUNTIME}\n".encode("utf-8"),
            (
                f"session_reported_runtime={SESSION_RUNTIME} suffix\n"
                "runtime_provenance=session_reported\n"
            ).encode("utf-8"),
            DA_OUTPUT_BYTES + b"runtime_provenance=independently_authenticated\n",
            DA_OUTPUT_BYTES
            + b"0f4b6688f8f47f050bad1a1205a3adf1eb19f99841981a03f1f0bfe1ad1f3831  999999  forged-name.md\n",
        )
        for bad_bytes in malformed_bindings:
            with self.subTest(bad_bytes=bad_bytes):
                malformed = copy.deepcopy(positive)
                output = next(
                    item
                    for item in malformed["artifacts"]
                    if item["id"] == "artifact:da-output"
                )
                output["sha256"] = (
                    f"sha256:{hashlib.sha256(bad_bytes).hexdigest()}"
                )
                with tempfile.TemporaryDirectory() as directory:
                    path = self.write_with_artifacts(directory, malformed)
                    Path(directory, "da-report.txt").write_bytes(DA_REPORT_BYTES)
                    Path(
                        directory, "chatgpt_data_analysis_output.txt"
                    ).write_bytes(bad_bytes)
                    status, payload = self.invoke(path)
                self.assertEqual(status, 1)
                self.assertIn(
                    "RETURN_DATA_ANALYSIS_RUNTIME_BINDING_INVALID",
                    {item["code"] for item in payload["findings"]},
                )

    def test_evidence_cannot_relabel_request_report_or_other_artifacts(self):
        cases = (("artifact:request", None), ("artifact:report", None), ("artifact:evidence", "other"))
        for artifact_id, replacement_role in cases:
            with self.subTest(artifact_id=artifact_id, role=replacement_role):
                raw = self.valid()
                if replacement_role is not None:
                    next(item for item in raw["artifacts"] if item["id"] == artifact_id)["role"] = replacement_role
                raw["evidence"][0]["artifact_ids"] = [artifact_id]
                with tempfile.TemporaryDirectory() as directory:
                    status, payload = self.invoke(self.write_with_artifacts(directory, raw))
                self.assertEqual(status, 1)
                self.assertIn("RETURN_EVIDENCE_ARTIFACT_ROLE_INVALID", {item["code"] for item in payload["findings"]})

    def test_artifact_bytes_cannot_be_redeclared_to_launder_roles(self):
        raw = self.valid()
        raw["claims"][0]["research_verdict"] = "proven"
        raw["summary_projection"]["research_verdict"] = "proven"
        request = next(item for item in raw["artifacts"] if item["role"] == "request")
        evidence = next(item for item in raw["artifacts"] if item["role"] == "evidence")
        evidence["sha256"] = request["sha256"]
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_with_artifacts(directory, raw)
            shutil.copyfile(Path(directory) / request["filename"], Path(directory) / evidence["filename"])
            status, payload = self.invoke(path)
        self.assertEqual(status, 1)
        self.assertIn("RETURN_ARTIFACT_HASH_ALIAS", {item["code"] for item in payload["findings"]})

    def test_high_verdicts_require_locally_bound_sources_and_direct_evidence(self):
        missing_source = json.loads((ROOT / "examples" / "audit_return_missing_artifact.json").read_text(encoding="utf-8"))
        missing_source["claims"][0]["research_verdict"] = "proven"
        missing_source["summary_projection"]["research_verdict"] = "proven"
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, missing_source))
        self.assertEqual(status, 1)
        self.assertIn("RETURN_PROVEN_SOURCE_BYTES_UNVERIFIED", {item["code"] for item in payload["findings"]})

        unsupported = self.valid()
        unsupported["claims"][0].update(research_verdict="strongly_supported", source_ids=[], evidence_ids=[])
        unsupported["evidence"][0]["claim_ids"] = []
        unsupported["summary_projection"]["research_verdict"] = "strongly_supported"
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, unsupported))
        codes = {item["code"] for item in payload["findings"]}
        self.assertEqual(status, 1)
        self.assertIn("RETURN_STRONGLY_SUPPORTED_WITH_SOURCE_GAP", codes)
        self.assertIn("RETURN_STRONGLY_SUPPORTED_WITHOUT_EVIDENCE", codes)

        dependency = self.valid()
        dependency["claims"][0].update(
            research_verdict="strongly_supported",
            depends_on=["claim:unsupported-dependency"],
        )
        dependency["claims"].append(
            {
                "id": "claim:unsupported-dependency",
                "statement": "A required dependency remains unresolved.",
                "research_verdict": "plausible_but_unresolved",
                "depends_on": [],
                "source_ids": [],
                "evidence_ids": [],
                "fatal_gate_ids": [],
            }
        )
        dependency["summary_projection"]["research_verdict"] = "strongly_supported"
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, dependency))
        self.assertEqual(status, 1)
        self.assertIn("RETURN_STRONGLY_SUPPORTED_DEPENDENCY_UNCLOSED", {item["code"] for item in payload["findings"]})

    def test_gate_evidence_scope_cannot_float_free_of_its_claim(self):
        raw = self.valid()
        raw["claims"][0]["evidence_ids"] = []
        raw["evidence"][0]["claim_ids"] = []
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, raw))
        self.assertEqual(status, 1)
        self.assertIn("RETURN_GATE_CLAIM_SCOPE_MISMATCH", {item["code"] for item in payload["findings"]})

    def test_primary_claim_and_every_gate_require_explicit_ownership(self):
        raw = self.valid()
        raw["claims"][0]["fatal_gate_ids"] = []
        raw["evidence"][0]["claim_ids"] = []
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, raw))
        self.assertEqual(status, 1)
        codes = {item["code"] for item in payload["findings"]}
        self.assertIn("RETURN_PRIMARY_CLAIM_GATE_MISSING", codes)
        self.assertIn("RETURN_GATE_OWNER_MISSING", codes)

    def test_portable_filenames_and_nonblank_tool_identity_are_enforced(self):
        collision = self.valid()
        collision["artifacts"][0]["filename"] = "A.txt"
        collision["artifacts"][1]["filename"] = "a.txt"
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, collision))
        self.assertEqual(status, 1)
        self.assertIn("RETURN_DUPLICATE_FILENAME", {item["code"] for item in payload["findings"]})

        unsafe = self.valid()
        unsafe["artifacts"][0]["filename"] = "CON .txt"
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, unsafe))
        self.assertEqual(status, 1)
        self.assertIn("RETURN_ARTIFACT_FILENAME_UNSAFE", {item["code"] for item in payload["findings"]})

        superscript_device = self.valid()
        superscript_device["artifacts"][0]["filename"] = "COM¹.txt"
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, superscript_device))
        self.assertEqual(status, 1)
        self.assertIn("RETURN_ARTIFACT_FILENAME_UNSAFE", {item["code"] for item in payload["findings"]})

        for format_control in (
            "\u0085", "\u009f", "\u061c", "\u200e", "\u200f", "\u2028", "\u2029", "\u202a", "\u202e", "\u2066", "\u2069", "\ufeff",
        ):
            bidi = self.valid()
            bidi["artifacts"][0]["filename"] = f"report{format_control}fdp.exe"
            with self.subTest(format_control=f"U+{ord(format_control):04X}"), tempfile.TemporaryDirectory() as directory:
                status, payload = self.invoke(self.write_with_artifacts(directory, bidi))
            self.assertEqual(status, 1)
            self.assertIn("RETURN_ARTIFACT_FILENAME_UNSAFE", {item["code"] for item in payload["findings"]})

        self.assertTrue(_portable_filename("report\ud800fdp.exe")[1])
        surrogate = self.valid()
        surrogate["artifacts"][0]["filename"] = "report\ud800fdp.exe"
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, surrogate))
        self.assertEqual(status, 2)
        self.assertIn("INPUT_MALFORMED", {item["code"] for item in payload["findings"]})

        for non_ascii_cased in ("Å.txt", "å.txt", "Δ.txt", "δ.txt"):
            cased = self.valid()
            cased["artifacts"][0]["filename"] = non_ascii_cased
            with self.subTest(non_ascii_cased=non_ascii_cased), tempfile.TemporaryDirectory() as directory:
                status, payload = self.invoke(self.write_with_artifacts(directory, cased))
            self.assertEqual(status, 1)
            self.assertIn("RETURN_ARTIFACT_FILENAME_UNSAFE", {item["code"] for item in payload["findings"]})

        whitespace = self.valid()
        whitespace["execution"][0]["tool"] = " "
        whitespace["execution"][0]["version"] = "\t"
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, whitespace))
        self.assertEqual(status, 2)
        self.assertIn("SCHEMA_VALIDATION", {item["code"] for item in payload["findings"]})

    def test_receipt_bytes_cannot_be_redeclared_as_substantive_evidence(self):
        raw = self.valid()
        evidence = next(item for item in raw["artifacts"] if item["role"] == "evidence")
        alias_filename = "receipt-alias.json"
        raw["artifacts"].append(
            {
                "id": "artifact:receipt-alias",
                "filename": alias_filename,
                "role": "receipt",
                "media_type": evidence["media_type"],
                "sha256": evidence["sha256"],
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_with_artifacts(directory, raw)
            source = ROOT / "examples" / evidence["filename"]
            shutil.copyfile(source, Path(directory) / alias_filename)
            status, payload = self.invoke(path)
        self.assertEqual(status, 1)
        self.assertIn("RETURN_ARTIFACT_HASH_ALIAS", {item["code"] for item in payload["findings"]})

    def test_honest_unrun_gate_can_remain_internally_consistent(self):
        raw = self.valid()
        raw["evidence"][0].update(status="unverified", result="inconclusive")
        raw["fatal_gates"][0].update(state="unrun", obligation_ids=["obligation:replay"])
        raw["unresolved_obligations"] = [
            {
                "id": "obligation:replay",
                "statement": "Independently replay the structural check against the bound source.",
                "claim_ids": ["claim:fixture"],
                "gate_ids": ["gate:structural-consistency"],
                "evidence_ids": ["evidence:structural-check"],
            }
        ]
        raw["summary_projection"].update(admission="unrun", unresolved_obligation_ids=["obligation:replay"])
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, raw))
        self.assertEqual(status, 0)
        self.assertEqual(payload["decision"], "no_blocking_findings_with_warnings")
        codes = {finding["code"] for finding in payload["findings"]}
        self.assertIn("RETURN_EVIDENCE_UNVERIFIED", codes)
        self.assertIn("RETURN_INTERNALLY_CONSISTENT", codes)
        self.assertNotIn("RETURN_OBLIGATION_SCOPE_MISMATCH", codes)

    def test_gate_obligation_cardinality_is_fail_closed(self):
        nonpassing = self.valid()
        nonpassing["claims"][0]["research_verdict"] = "refuted"
        nonpassing["evidence"][0]["result"] = "fail"
        nonpassing["fatal_gates"][0]["state"] = "fail"
        nonpassing["summary_projection"].update(
            research_verdict="refuted",
            admission="fail",
        )
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(
                self.write_with_artifacts(directory, nonpassing)
            )
        self.assertEqual(status, 1)
        self.assertIn(
            "RETURN_UNRESOLVED_GATE_OBLIGATION_OMITTED",
            {item["code"] for item in payload["findings"]},
        )

        passing = self.valid()
        passing["fatal_gates"][0]["obligation_ids"] = [
            "obligation:unnecessarily-open"
        ]
        passing["unresolved_obligations"] = [
            {
                "id": "obligation:unnecessarily-open",
                "statement": "This obligation cannot remain behind a passing gate.",
                "claim_ids": ["claim:fixture"],
                "gate_ids": ["gate:structural-consistency"],
                "evidence_ids": ["evidence:structural-check"],
            }
        ]
        passing["summary_projection"]["unresolved_obligation_ids"] = [
            "obligation:unnecessarily-open"
        ]
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(
                self.write_with_artifacts(directory, passing)
            )
        self.assertEqual(status, 1)
        self.assertIn(
            "RETURN_PASSED_GATE_HAS_OPEN_OBLIGATION",
            {item["code"] for item in payload["findings"]},
        )

    def test_obligation_claim_gate_and_evidence_scopes_are_closed(self):
        def scoped_unrun() -> dict:
            raw = self.valid()
            raw["evidence"][0].update(status="unverified", result="inconclusive")
            raw["fatal_gates"][0].update(state="unrun", obligation_ids=["obligation:replay"])
            raw["unresolved_obligations"] = [
                {
                    "id": "obligation:replay",
                    "statement": "Independently replay the structural check against the bound source.",
                    "claim_ids": ["claim:fixture"],
                    "gate_ids": ["gate:structural-consistency"],
                    "evidence_ids": ["evidence:structural-check"],
                }
            ]
            raw["summary_projection"].update(
                admission="unrun",
                unresolved_obligation_ids=["obligation:replay"],
            )
            return raw

        for field in ("claim_ids", "gate_ids"):
            with self.subTest(field=field):
                mismatch = scoped_unrun()
                mismatch["unresolved_obligations"][0][field] = []
                with tempfile.TemporaryDirectory() as directory:
                    status, payload = self.invoke(self.write_with_artifacts(directory, mismatch))
                self.assertEqual(status, 1)
                self.assertIn(
                    "RETURN_OBLIGATION_SCOPE_MISMATCH",
                    {item["code"] for item in payload["findings"]},
                )

        evidence_mismatch = scoped_unrun()
        unrelated = copy.deepcopy(evidence_mismatch["evidence"][0])
        unrelated.update(id="evidence:unrelated", claim_ids=[], gate_ids=[])
        evidence_mismatch["evidence"].append(unrelated)
        evidence_mismatch["unresolved_obligations"][0]["evidence_ids"] = ["evidence:unrelated"]
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, evidence_mismatch))
        self.assertEqual(status, 1)
        self.assertIn(
            "RETURN_OBLIGATION_SCOPE_MISMATCH",
            {item["code"] for item in payload["findings"]},
        )

    def test_effective_decisive_and_inconclusive_evidence_preserve_conflict(self):
        raw = self.valid()
        mixed = copy.deepcopy(raw["evidence"][0])
        mixed["id"] = "evidence:inconclusive"
        mixed["result"] = "inconclusive"
        raw["evidence"].append(mixed)
        raw["claims"][0]["evidence_ids"].append(mixed["id"])
        raw["fatal_gates"][0].update(
            state="conflict",
            evidence_ids=["evidence:structural-check", mixed["id"]],
            obligation_ids=["obligation:resolve-conflict"],
        )
        raw["unresolved_obligations"] = [
            {
                "id": "obligation:resolve-conflict",
                "statement": "Resolve the incompatible decisive and inconclusive bound records.",
                "claim_ids": ["claim:fixture"],
                "gate_ids": ["gate:structural-consistency"],
                "evidence_ids": ["evidence:structural-check", mixed["id"]],
            }
        ]
        raw["summary_projection"].update(
            admission="conflict",
            unresolved_obligation_ids=["obligation:resolve-conflict"],
        )
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, raw))
        self.assertEqual(status, 0)
        codes = {finding["code"] for finding in payload["findings"]}
        self.assertNotIn("RETURN_GATE_STATE_MISMATCH", codes)
        self.assertIn("RETURN_INTERNALLY_CONSISTENT", codes)

    def test_locally_bound_proven_record_is_only_consistency_checked(self):
        raw = self.valid()
        raw["claims"][0]["research_verdict"] = "proven"
        raw["summary_projection"]["research_verdict"] = "proven"
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, raw))
        self.assertEqual(status, 0)
        nonadmissive = next(finding for finding in payload["findings"] if finding["code"] == "RETURN_DESK_NON_ADMISSIVE")
        self.assertIn("does not establish truth", nonadmissive["message"])

    def test_unknown_properties_are_rejected_by_the_closed_schema(self):
        raw = self.valid()
        raw["summary_projection"]["confidence"] = 0.99
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, raw))
        self.assertEqual(status, 2)
        self.assertEqual(payload["decision"], "prohibited")
        self.assertIn("SCHEMA_VALIDATION", {finding["code"] for finding in payload["findings"]})

    def test_required_human_semantic_strings_cannot_be_blank(self):
        claim = self.valid()
        claim["claims"][0]["statement"] = " \t"
        label = self.valid()
        label["sources"][0]["label"] = " \t"
        scope = self.valid()
        scope["sources"][0]["inspected_scope"] = [" \t"]
        omissions = self.valid()
        omissions["sources"][0].update(coverage_state="partially_inspected", omissions=[" \t"])
        media_type = self.valid()
        media_type["artifacts"][0]["media_type"] = " \t"
        notes = self.valid()
        notes["execution"][0]["notes"] = " \t"
        for label_name, raw in (
            ("claim statement", claim),
            ("source label", label),
            ("inspected scope", scope),
            ("omission", omissions),
            ("media type", media_type),
            ("execution notes", notes),
        ):
            with self.subTest(field=label_name), tempfile.TemporaryDirectory() as directory:
                status, payload = self.invoke(self.write_with_artifacts(directory, raw))
            self.assertEqual(status, 2)
            self.assertIn("SCHEMA_VALIDATION", {finding["code"] for finding in payload["findings"]})

        for invisible in ("\u200b", "\ufeff"):
            raw = self.valid()
            raw["claims"][0]["statement"] = invisible
            with self.subTest(invisible=f"U+{ord(invisible):04X}"), tempfile.TemporaryDirectory() as directory:
                status, payload = self.invoke(self.write_with_artifacts(directory, raw))
            self.assertEqual(status, 1)
            self.assertIn("RETURN_SEMANTIC_TEXT_INVISIBLE", {finding["code"] for finding in payload["findings"]})

    def test_high_verdicts_cannot_ignore_direct_effective_nonpassing_evidence(self):
        for verdict in ("proven", "strongly_supported"):
            for result in ("fail", "inconclusive"):
                raw = self.valid()
                raw["claims"][0]["research_verdict"] = verdict
                raw["summary_projection"]["research_verdict"] = verdict
                contrary = copy.deepcopy(raw["evidence"][0])
                contrary.update(id=f"evidence:{result}", result=result, gate_ids=[])
                raw["evidence"].append(contrary)
                raw["claims"][0]["evidence_ids"].append(contrary["id"])
                with self.subTest(verdict=verdict, result=result), tempfile.TemporaryDirectory() as directory:
                    status, payload = self.invoke(self.write_with_artifacts(directory, raw))
                self.assertEqual(status, 1)
                self.assertIn("RETURN_HIGH_VERDICT_EVIDENCE_CONFLICT", {finding["code"] for finding in payload["findings"]})

    def test_python_artifact_budgets_abort_before_hashing(self):
        too_many = self.valid()
        for index in range(len(too_many["artifacts"]), 33):
            too_many["artifacts"].append(
                {
                    "id": f"artifact:extra:{index}",
                    "filename": f"extra-{index}.bin",
                    "role": "other",
                    "media_type": "application/octet-stream",
                    "sha256": f"sha256:{index:064x}",
                }
            )
        with patch("bsc_audit.return_desk.verify_local_artifact") as verifier, tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, too_many))
        self.assertEqual(status, 1)
        self.assertIn("RETURN_ARTIFACT_COUNT_LIMIT", {finding["code"] for finding in payload["findings"]})
        verifier.assert_not_called()

        aggregate = self.valid()
        with (
            patch(
                "bsc_audit.return_desk._preflight_return_artifacts",
                return_value=({}, MAX_RETURN_TOTAL_ARTIFACT_BYTES + 1),
            ),
            patch("bsc_audit.return_desk.verify_local_artifact") as verifier,
            tempfile.TemporaryDirectory() as directory,
        ):
            status, payload = self.invoke(self.write_with_artifacts(directory, aggregate))
        self.assertEqual(status, 1)
        self.assertIn("RETURN_ARTIFACT_TOTAL_LIMIT", {finding["code"] for finding in payload["findings"]})
        verifier.assert_not_called()

    def test_maximum_claim_chain_and_tail_cycle_return_structured_results(self):
        raw = self.valid()
        identifiers = [f"claim:chain:{index}" for index in range(4095)]
        raw["claims"][0]["depends_on"] = [identifiers[0]]
        raw["claims"].extend(
            {
                "id": identifier,
                "statement": f"Acyclic dependency {index}.",
                "research_verdict": "plausible_but_unresolved",
                "depends_on": ([identifiers[index + 1]] if index + 1 < len(identifiers) else []),
                "source_ids": [],
                "evidence_ids": [],
                "fatal_gate_ids": [],
            }
            for index, identifier in enumerate(identifiers)
        )
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, raw))
        self.assertEqual(status, 0, payload)
        self.assertIn("RETURN_INTERNALLY_CONSISTENT", {finding["code"] for finding in payload["findings"]})

        raw["claims"][-1]["depends_on"] = [identifiers[-100]]
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, raw))
        self.assertEqual(status, 1)
        self.assertIn("RETURN_CLAIM_DEPENDENCY_CYCLE", {finding["code"] for finding in payload["findings"]})

    def test_identifiers_are_globally_unambiguous(self):
        raw = self.valid()
        raw["sources"][0]["id"] = "claim:fixture"
        raw["claims"][0]["source_ids"] = ["claim:fixture"]
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, raw))
        self.assertEqual(status, 1)
        self.assertIn("RETURN_GLOBAL_ID_COLLISION", {finding["code"] for finding in payload["findings"]})

    def test_absence_is_not_allowed_to_become_refutation(self):
        raw = self.valid()
        raw["claims"][0]["research_verdict"] = "refuted"
        raw["summary_projection"]["research_verdict"] = "refuted"
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, raw))
        self.assertEqual(status, 1)
        self.assertIn("RETURN_REFUTED_WITHOUT_COUNTEREVIDENCE", {finding["code"] for finding in payload["findings"]})

    def test_summary_must_project_secondary_gates_and_obligations(self):
        raw = self.valid()
        raw["fatal_gates"].append(
            {
                "id": "gate:secondary",
                "state": "unrun",
                "evidence_ids": [],
                "obligation_ids": ["obligation:secondary"],
            }
        )
        raw["unresolved_obligations"].append(
            {
                "id": "obligation:secondary",
                "statement": "Resolve the independently declared secondary gate.",
                "claim_ids": [],
                "gate_ids": ["gate:secondary"],
                "evidence_ids": [],
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            status, payload = self.invoke(self.write_with_artifacts(directory, raw))
        codes = {finding["code"] for finding in payload["findings"]}
        self.assertEqual(status, 1)
        self.assertIn("RETURN_SUMMARY_GATE_OMISSION", codes)
        self.assertIn("RETURN_SUMMARY_OBLIGATION_OMISSION", codes)
        self.assertIn("RETURN_SUMMARY_ADMISSION_MISMATCH", codes)


if __name__ == "__main__":
    unittest.main()
