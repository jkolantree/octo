import copy
import hashlib
import io
import json
import unittest
from contextlib import redirect_stdout

import scripts.gpt_artifact_compiler as artifact_compiler
import scripts.gpt_eval_controller as eval_controller
from scripts.gpt_eval_controller import (
    BOUND_REPORT_ARTIFACT,
    BOUND_RETURN_ARTIFACT,
    BOUND_RUNTIME_ARTIFACT,
    CANDIDATE_FAILED,
    CANDIDATE_NOT_SCORED,
    CANDIDATE_PASSED,
    CANDIDATE_PENDING_DISPOSITION,
    CONTROLLER_VALID,
    REPORT_RUNTIME_REFERENCE,
    RUNTIME_BASIS_LINE,
    RUNTIME_PREFIX,
    TRANSPORT_IDENTITY_RESOLVED,
    TRANSPORT_IDENTITY_UNRESOLVED,
    TRIAL_INVALID_CONTROLLER,
    _parser,
    canonical_json_bytes,
    derive_disposition,
    extract_session_reported_runtime,
    finalize_candidate_artifacts,
    frozen_trial_bindings,
    main as controller_main,
    output_record,
    parse_runtime_ledger,
    runtime_ledger_text,
    transport_fallback_prompt,
    validate_frozen_trial_binding,
)


RUNTIME = "3.13.5 (main, May  5 2026, 21:05:52) [GCC 14.2.0]"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def template() -> dict:
    artifacts = [
        {
            "id": "artifact:request",
            "filename": "audit_request.txt",
            "role": "request",
            "media_type": "text/plain",
            "sha256": "sha256:" + "0" * 64,
        },
        {
            "id": "artifact:source",
            "filename": "target.txt",
            "role": "source",
            "media_type": "text/plain",
            "sha256": "sha256:" + "0" * 64,
        },
        {
            "id": "artifact:evidence",
            "filename": "proof_evidence.md",
            "role": "evidence",
            "media_type": "text/markdown",
            "sha256": "sha256:" + "0" * 64,
        },
        {
            "id": "artifact:report",
            "filename": BOUND_REPORT_ARTIFACT,
            "role": "report",
            "media_type": "text/markdown",
            "sha256": "sha256:" + "0" * 64,
        },
        {
            "id": "artifact:data-analysis-output",
            "filename": BOUND_RUNTIME_ARTIFACT,
            "role": "execution_output",
            "media_type": "text/plain",
            "sha256": "sha256:" + "0" * 64,
        },
    ]
    return {
        "protocol": {"version": "0.3.0-alpha.8"},
        "artifacts": artifacts,
        "execution": [
            {
                "activity": activity,
                "status": "not_run",
                "tool": None,
                "version": None,
                "input_artifact_ids": [],
                "output_artifact_ids": [],
                "receipt_ids": [],
                "notes": "pending",
            }
            for activity in artifact_compiler.CANONICAL_EXECUTION_ACTIVITIES
        ],
        "receipts": [],
        "evidence": [],
    }


class GptEvalControllerTests(unittest.TestCase):
    def test_controller_reexports_the_single_compiler_implementation(self):
        for name in (
            "canonical_json_bytes",
            "export_payload_wrapper",
            "extract_session_reported_runtime",
            "finalize_candidate_artifacts",
            "output_record",
            "parse_runtime_ledger",
            "runtime_ledger_text",
            "sha256_bytes",
            "transport_fallback_prompt",
        ):
            self.assertIs(
                getattr(eval_controller, name),
                getattr(artifact_compiler, name),
                name,
            )

    def test_transport_request_cli_emits_exact_one_file_prompt_without_newline(self):
        output = io.StringIO()
        with redirect_stdout(output):
            status = controller_main(
                ["transport-request", "--output", "audit_return.json"]
            )
        self.assertEqual(status, 0)
        self.assertEqual(
            output.getvalue(),
            transport_fallback_prompt("audit_return.json"),
        )
        self.assertIn(
            "python /mnt/data/gpt_artifact_compiler.py export-wrapper "
            "/mnt/data/audit_return.json",
            output.getvalue(),
        )
        self.assertIn("complete stdout byte-for-byte", output.getvalue())
        self.assertFalse(output.getvalue().endswith("\n"))

    def test_finalizer_uses_one_runtime_and_serializes_return_last(self):
        original = template()
        frozen = {
            "audit_request.txt": b"Audit the exact target.\n",
            "target.txt": b"Target bytes.\n",
            "proof_evidence.md": b"# Exact proof\n\nInduction closes.\n",
        }
        finalized = finalize_candidate_artifacts(
            session_reported_runtime=RUNTIME,
            report_body="# Audit report\n\nThe supplied induction is valid.",
            frozen_artifacts=frozen,
            audit_return_template=original,
        )

        self.assertEqual(list(finalized.files)[-1], BOUND_RETURN_ARTIFACT)
        report = finalized.files[BOUND_REPORT_ARTIFACT].decode("utf-8")
        self.assertIn(REPORT_RUNTIME_REFERENCE, report)
        self.assertNotIn(RUNTIME, report)
        ledger = finalized.files[BOUND_RUNTIME_ARTIFACT].decode("utf-8")
        self.assertEqual(extract_session_reported_runtime(ledger), RUNTIME)
        self.assertEqual(ledger.count(RUNTIME), 1)
        self.assertNotIn(BOUND_RUNTIME_ARTIFACT, ledger)
        self.assertNotIn(BOUND_RETURN_ARTIFACT, ledger)
        self.assertIn(digest(finalized.files[BOUND_REPORT_ARTIFACT]), ledger)
        self.assertIn(digest(finalized.files["proof_evidence.md"]), ledger)

        analysis = next(
            row
            for row in finalized.audit_return["execution"]
            if row["activity"] == "chatgpt_data_analysis"
        )
        self.assertEqual(analysis["version"], RUNTIME)
        self.assertIn("session-reported", analysis["notes"])
        self.assertIn("not independently authenticated", analysis["notes"])
        rows = {
            row["filename"]: row for row in finalized.audit_return["artifacts"]
        }
        for filename, data in finalized.files.items():
            if filename == BOUND_RETURN_ARTIFACT:
                continue
            self.assertEqual(rows[filename]["sha256"], f"sha256:{digest(data)}")
        return_document = json.loads(
            finalized.files[BOUND_RETURN_ARTIFACT].decode("utf-8")
        )
        self.assertEqual(return_document, finalized.audit_return)
        self.assertNotIn(
            '"base64"',
            finalized.files[BOUND_RETURN_ARTIFACT].decode("utf-8"),
        )
        self.assertEqual(original, template(), "finalizer mutated its template")

    def test_finalizer_is_byte_deterministic(self):
        arguments = {
            "session_reported_runtime": RUNTIME,
            "report_body": "# Result\n\nA deterministic projection.",
            "frozen_artifacts": {
                "audit_request.txt": b"request\n",
                "target.txt": b"target\n",
                "proof_evidence.md": b"proof\n",
            },
            "audit_return_template": template(),
        }
        first = finalize_candidate_artifacts(**copy.deepcopy(arguments))
        second = finalize_candidate_artifacts(**copy.deepcopy(arguments))
        self.assertEqual(first.files, second.files)
        self.assertEqual(first.identities, second.identities)
        identity_by_name = {
            item["filename"]: item for item in first.identities
        }
        for filename, data in first.files.items():
            self.assertEqual(identity_by_name[filename], output_record(filename, data))

    def test_finalizer_rejects_manual_runtime_replication_in_report(self):
        with self.assertRaisesRegex(ValueError, "reference"):
            finalize_candidate_artifacts(
                session_reported_runtime=RUNTIME,
                report_body=f"Model prose copied {RUNTIME}",
                frozen_artifacts={
                    "audit_request.txt": b"request\n",
                    "target.txt": b"target\n",
                    "proof_evidence.md": b"proof\n",
                },
                audit_return_template=template(),
            )

    def test_finalizer_rejects_runtime_copy_in_generated_evidence(self):
        with self.assertRaisesRegex(ValueError, "generated text artifact"):
            finalize_candidate_artifacts(
                session_reported_runtime=RUNTIME,
                report_body="The report references the bound execution output.",
                frozen_artifacts={
                    "audit_request.txt": b"request\n",
                    "target.txt": b"target\n",
                    "proof_evidence.md": (
                        f"Copied runtime in generated evidence: {RUNTIME}\n"
                    ).encode("utf-8"),
                },
                audit_return_template=template(),
            )

    def test_runtime_ledger_rejects_self_and_return_identity(self):
        for filename in (BOUND_RUNTIME_ARTIFACT, BOUND_RETURN_ARTIFACT):
            with self.subTest(filename=filename):
                with self.assertRaisesRegex(ValueError, "own or return"):
                    runtime_ledger_text(
                        RUNTIME,
                        [output_record(filename, b"bytes")],
                    )

    def test_runtime_ledger_requires_exact_full_runtime_projection_lines(self):
        ledger = runtime_ledger_text(RUNTIME, [])
        self.assertEqual(ledger.splitlines().count(RUNTIME_PREFIX + RUNTIME), 1)
        self.assertEqual(ledger.splitlines().count(RUNTIME_BASIS_LINE), 1)
        with self.assertRaisesRegex(ValueError, "complete sys.version"):
            runtime_ledger_text("3.13.5", [])
        with self.assertRaisesRegex(ValueError, "complete sys.version"):
            extract_session_reported_runtime(
                "bsc_chatgpt_data_analysis_output_version: 2\n"
                "session_reported_runtime=3.13.5\n"
                "runtime_provenance=session_reported\n"
                "finalized_artifacts:\n"
            )

    def test_canonical_json_rejects_nonfinite_numbers(self):
        with self.assertRaises(ValueError):
            canonical_json_bytes({"not_json": float("nan")})

    def test_runtime_ledger_rejects_casefold_filename_collision(self):
        with self.assertRaisesRegex(ValueError, "collision"):
            runtime_ledger_text(
                RUNTIME,
                [
                    output_record("Evidence.txt", b"one"),
                    output_record("evidence.txt", b"two"),
                ],
            )

    def test_runtime_ledger_rejects_hidden_second_runtime(self):
        ledger = runtime_ledger_text(RUNTIME, [])
        mutated = ledger.replace(
            RUNTIME_BASIS_LINE,
            f"{RUNTIME_PREFIX}{RUNTIME}\n{RUNTIME_BASIS_LINE}",
        )
        with self.assertRaises(ValueError):
            parse_runtime_ledger(mutated)

    def test_frozen_protocol_maps_preflights_and_all_counted_trials_exactly(self):
        bindings = frozen_trial_bindings()
        self.assertEqual(bindings["D01"], (1, "known-true-induction", "preflight"))
        self.assertEqual(
            bindings["D02"],
            (27, "return-envelope-positive-control", "preflight"),
        )
        counted = [bindings[f"C{number:03d}"] for number in range(1, 40)]
        self.assertEqual([item[0] for item in counted], list(range(1, 40)))
        self.assertTrue(all(item[2] == "counted" for item in counted))
        self.assertEqual(counted[0][1], "known-true-induction")
        self.assertEqual(counted[-1][1], "official-first-reproduction-route")

    def test_syntactically_valid_trial_mismap_is_invalid_controller_state(self):
        with self.assertRaisesRegex(ValueError, "different frozen case"):
            validate_frozen_trial_binding(
                trial_id="D01",
                case_id="return-envelope-positive-control",
                counting_state="preflight",
            )
        with self.assertRaisesRegex(ValueError, "different frozen case"):
            validate_frozen_trial_binding(
                trial_id="C001",
                case_id="known-false-continuity",
                counting_state="counted",
            )

    def test_build_record_cli_accepts_zero_output_arguments(self):
        args = _parser().parse_args(
            [
                "build-record",
                "evidence",
                "--case-id",
                "known-true-induction",
                "--trial-id",
                "D01",
                "--counting-state",
                "preflight",
                "--target",
                "known_true_induction.txt",
                "--session-reference",
                "preview:test",
                "--observability-boundary",
                "Visible Preview response and exposed files only.",
            ]
        )
        self.assertEqual(args.output_filenames, [])

    def test_finalizer_rejects_model_invented_conflicting_runtime_literal(self):
        other_runtime = "3.11.8 (main, Mar 12 2024, 11:41:52) [GCC 12.2.0]"
        with self.assertRaisesRegex(ValueError, "copy a runtime"):
            finalize_candidate_artifacts(
                session_reported_runtime=RUNTIME,
                report_body=f"Model prose invented {other_runtime}",
                frozen_artifacts={
                    "audit_request.txt": b"request\n",
                    "target.txt": b"target\n",
                    "proof_evidence.md": b"proof\n",
                },
                audit_return_template=template(),
            )

    def test_disposition_axes_cannot_rescue_candidate_failure(self):
        self.assertEqual(
            derive_disposition(
                controller=CONTROLLER_VALID,
                candidate=CANDIDATE_FAILED,
                transport=TRANSPORT_IDENTITY_UNRESOLVED,
            ),
            CANDIDATE_FAILED,
        )
        self.assertEqual(
            derive_disposition(
                controller=CONTROLLER_VALID,
                candidate=CANDIDATE_PASSED,
                transport=TRANSPORT_IDENTITY_UNRESOLVED,
            ),
            TRANSPORT_IDENTITY_UNRESOLVED,
        )
        self.assertEqual(
            derive_disposition(
                controller=CONTROLLER_VALID,
                candidate=CANDIDATE_PASSED,
                transport=TRANSPORT_IDENTITY_RESOLVED,
            ),
            CANDIDATE_PASSED,
        )
        self.assertEqual(
            derive_disposition(
                controller=TRIAL_INVALID_CONTROLLER,
                candidate=CANDIDATE_NOT_SCORED,
                transport=TRANSPORT_IDENTITY_UNRESOLVED,
            ),
            TRIAL_INVALID_CONTROLLER,
        )
        self.assertEqual(
            derive_disposition(
                controller=CONTROLLER_VALID,
                candidate=CANDIDATE_NOT_SCORED,
                transport=TRANSPORT_IDENTITY_UNRESOLVED,
            ),
            CANDIDATE_PENDING_DISPOSITION,
        )
        with self.assertRaisesRegex(ValueError, "cannot be scored"):
            derive_disposition(
                controller=TRIAL_INVALID_CONTROLLER,
                candidate=CANDIDATE_FAILED,
                transport=TRANSPORT_IDENTITY_UNRESOLVED,
            )


if __name__ == "__main__":
    unittest.main()
