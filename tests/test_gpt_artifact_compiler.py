import base64
import copy
import hashlib
import io
import json
import sys
import tempfile
import unittest
import zlib
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from bsc_audit.cli import main as bsc_main
from bsc_audit.return_desk import CANONICAL_ACTIVITIES
from scripts.gpt_artifact_compiler import (
    BOUND_REPORT_ARTIFACT,
    BOUND_RETURN_ARTIFACT,
    BOUND_RUNTIME_ARTIFACT,
    CANONICAL_EXECUTION_ACTIVITIES,
    COMPILER_VERSION,
    EXPORT_CHUNK_FIELDS,
    REPORT_PROJECTION_MARKER,
    TRANSPORT_CHUNK_BYTES,
    TRANSPORT_CHUNK_VERSION,
    TRANSPORT_ENCODING,
    _stable_read_payload,
    _transport_chunks,
    canonical_json_bytes,
    canonical_transport_wrapper_bytes,
    export_payload_chunk,
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

    @staticmethod
    def incompressible_payload(blocks: int = 320) -> bytes:
        return b"".join(
            hashlib.sha256(index.to_bytes(4, "big")).digest()
            for index in range(blocks)
        )

    def export_all_chunks(self, filename: str, payload: bytes) -> list[dict]:
        first = export_payload_chunk(filename, payload, 0)
        chunks = [first]
        for index in range(1, first["chunk_count"]):
            chunks.append(
                export_payload_chunk(
                    filename,
                    payload,
                    index,
                    expected_payload_sha256=first["payload_sha256"],
                    expected_encoded_sha256=first["encoded_sha256"],
                )
            )
        return chunks

    def test_export_chunks_reconstruct_exact_payload_and_preserve_terminal_lf(self):
        payload = (
            b"independently::aligned-quartet::ZW5k\n"
            + self.incompressible_payload()
            + b"\n"
        )
        chunks = self.export_all_chunks("audit_report.md", payload)
        encoded_parts = []
        for index, wrapper in enumerate(chunks):
            self.assertEqual(set(wrapper), EXPORT_CHUNK_FIELDS)
            self.assertEqual(wrapper["transport_version"], TRANSPORT_CHUNK_VERSION)
            self.assertEqual(wrapper["encoding"], TRANSPORT_ENCODING)
            self.assertEqual(wrapper["chunk_index"], index)
            self.assertEqual(wrapper["chunk_count"], len(chunks))
            self.assertEqual(
                wrapper["offset_bytes"],
                index * TRANSPORT_CHUNK_BYTES,
            )
            decoded = base64.b64decode(wrapper["base64"], validate=True)
            self.assertEqual(len(decoded), wrapper["chunk_size_bytes"])
            self.assertLessEqual(len(decoded), TRANSPORT_CHUNK_BYTES)
            self.assertEqual(sha256_bytes(decoded), wrapper["chunk_sha256"])
            if index == 0 and len(wrapper["base64"]) >= 12:
                omitted = (
                    wrapper["base64"][:4]
                    + wrapper["base64"][8:]
                )
                omitted_bytes = base64.b64decode(omitted, validate=True)
                self.assertTrue(
                    len(omitted_bytes) != wrapper["chunk_size_bytes"]
                    or sha256_bytes(omitted_bytes) != wrapper["chunk_sha256"]
                )
            encoded_parts.append(decoded)

        encoded = b"".join(encoded_parts)
        self.assertEqual(len(encoded), chunks[0]["encoded_size_bytes"])
        self.assertEqual(sha256_bytes(encoded), chunks[0]["encoded_sha256"])
        reconstructed = zlib.decompress(encoded)
        self.assertEqual(reconstructed, payload)
        self.assertTrue(reconstructed.endswith(b"\n"))
        self.assertIn(b"independently", reconstructed)
        self.assertIn(b"ZW5k", reconstructed)
        self.assertEqual(len(reconstructed), chunks[0]["payload_size_bytes"])
        self.assertEqual(sha256_bytes(reconstructed), chunks[0]["payload_sha256"])

    def test_transport_splitter_handles_empty_exact_boundary_and_final_short_chunk(self):
        self.assertEqual(_transport_chunks(b""), (b"",))
        exact = _transport_chunks(b"x" * TRANSPORT_CHUNK_BYTES)
        self.assertEqual(len(exact), 1)
        self.assertEqual(len(exact[0]), TRANSPORT_CHUNK_BYTES)
        final_short = _transport_chunks(b"x" * (TRANSPORT_CHUNK_BYTES + 1))
        self.assertEqual(
            tuple(len(chunk) for chunk in final_short),
            (TRANSPORT_CHUNK_BYTES, 1),
        )

    def test_empty_payload_export_round_trips_through_one_compressed_chunk(self):
        wrapper = export_payload_chunk("empty.bin", b"", 0)
        self.assertEqual(wrapper["payload_size_bytes"], 0)
        self.assertEqual(wrapper["payload_sha256"], sha256_bytes(b""))
        self.assertEqual(wrapper["chunk_count"], 1)
        encoded = base64.b64decode(wrapper["base64"], validate=True)
        self.assertEqual(len(encoded), wrapper["encoded_size_bytes"])
        self.assertEqual(sha256_bytes(encoded), wrapper["encoded_sha256"])
        self.assertEqual(zlib.decompress(encoded), b"")

    def test_transport_splitter_preserves_zw5k_across_chunk_boundary(self):
        encoded = b"x" * (TRANSPORT_CHUNK_BYTES - 2) + b"ZW5k" + b"tail"
        chunks = _transport_chunks(encoded)
        self.assertEqual(b"".join(chunks), encoded)
        self.assertTrue(chunks[0].endswith(b"ZW"))
        self.assertTrue(chunks[1].startswith(b"5k"))
        omitted = chunks[0][:-2] + chunks[1][2:]
        self.assertNotEqual(sha256_bytes(omitted), sha256_bytes(encoded))

    def test_export_chunk_rejects_invalid_indices_and_missing_later_hashes(self):
        payload = self.incompressible_payload()
        first = export_payload_chunk("audit_report.md", payload, 0)
        self.assertGreater(first["chunk_count"], 1)
        with self.assertRaisesRegex(ValueError, "chunk index"):
            export_payload_chunk("audit_report.md", payload, -1)
        with self.assertRaisesRegex(ValueError, "chunk index"):
            export_payload_chunk(
                "audit_report.md",
                payload,
                first["chunk_count"],
                expected_payload_sha256=first["payload_sha256"],
                expected_encoded_sha256=first["encoded_sha256"],
            )
        with self.assertRaisesRegex(
            ValueError,
            "later transport chunks require",
        ):
            export_payload_chunk("audit_report.md", payload, 1)

    def test_later_chunk_blocks_on_payload_or_encoded_hash_mismatch(self):
        payload = self.incompressible_payload()
        first = export_payload_chunk("audit_report.md", payload, 0)
        self.assertGreater(first["chunk_count"], 1)
        with self.assertRaisesRegex(ValueError, "payload SHA-256 differs"):
            export_payload_chunk(
                "audit_report.md",
                payload + b"changed",
                1,
                expected_payload_sha256=first["payload_sha256"],
                expected_encoded_sha256=first["encoded_sha256"],
            )
        with self.assertRaisesRegex(ValueError, "encoded payload SHA-256 differs"):
            export_payload_chunk(
                "audit_report.md",
                payload,
                1,
                expected_payload_sha256=first["payload_sha256"],
                expected_encoded_sha256="0" * 64,
            )

    def test_stable_read_rejects_mutation_during_payload_read(self):
        stable = SimpleNamespace(
            st_dev=1,
            st_ino=2,
            st_size=4,
            st_mtime_ns=10,
            st_ctime_ns=20,
        )
        changed = SimpleNamespace(
            st_dev=1,
            st_ino=2,
            st_size=4,
            st_mtime_ns=11,
            st_ctime_ns=20,
        )

        class MutatingPayload:
            name = "audit_report.md"

            def __init__(self):
                self.stats = iter((stable, changed))

            def stat(self):
                return next(self.stats)

            def read_bytes(self):
                return b"data"

        with self.assertRaisesRegex(ValueError, "changed during stable read"):
            _stable_read_payload(MutatingPayload())

    def test_export_chunk_enforces_shared_payload_encoded_and_index_bounds(self):
        with patch(
            "scripts.gpt_artifact_compiler.MAX_TRANSPORT_PAYLOAD_BYTES",
            3,
        ):
            with self.assertRaisesRegex(ValueError, "payload exceeds"):
                export_payload_chunk("payload.bin", b"four", 0)
        with patch(
            "scripts.gpt_artifact_compiler.MAX_TRANSPORT_ENCODED_BYTES",
            1,
        ):
            with self.assertRaisesRegex(ValueError, "encoded payload exceeds"):
                export_payload_chunk("payload.bin", b"x", 0)
        with patch(
            "scripts.gpt_artifact_compiler.MAX_TRANSPORT_CHUNKS",
            1,
        ):
            with self.assertRaisesRegex(ValueError, "chunk index exceeds"):
                export_payload_chunk("payload.bin", b"x", 1)

    def test_stable_read_rejects_linked_payload_when_supported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target.bin"
            link = root / "linked.bin"
            target.write_bytes(b"exact")
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable on this platform")
            with self.assertRaisesRegex(ValueError, "regular non-linked file"):
                _stable_read_payload(link)

    def test_export_chunk_cli_uses_no_lf_wrapper_and_preserves_payload_lf(self):
        with tempfile.TemporaryDirectory() as temporary:
            payload_path = Path(temporary) / "audit_report.md"
            original = (
                b"independently::aligned-quartet::ZW5k\n"
                + self.incompressible_payload()
                + b"\n"
            )
            payload_path.write_bytes(original)
            output = io.StringIO()
            with redirect_stdout(output):
                status = compiler_main(
                    [
                        "export-chunk",
                        str(payload_path),
                        "--chunk-index",
                        "0",
                    ]
                )
            self.assertEqual(status, 0)
            wrapper = json.loads(output.getvalue())
            self.assertEqual(COMPILER_VERSION, "bsc-gpt-artifact-compiler-v4")
            self.assertEqual(
                output.getvalue().encode("utf-8"),
                canonical_transport_wrapper_bytes(wrapper),
            )
            self.assertFalse(output.getvalue().endswith("\n"))
            self.assertEqual(
                canonical_json_bytes(wrapper),
                output.getvalue().encode("utf-8") + b"\n",
            )
            self.assertEqual(set(wrapper), EXPORT_CHUNK_FIELDS)
            decoded = base64.b64decode(wrapper["base64"], validate=True)
            self.assertLessEqual(len(decoded), TRANSPORT_CHUNK_BYTES)
            self.assertEqual(
                len(decoded),
                wrapper["chunk_size_bytes"],
            )
            self.assertEqual(sha256_bytes(decoded), wrapper["chunk_sha256"])
            if wrapper["chunk_count"] > 1:
                later_output = io.StringIO()
                with redirect_stdout(later_output):
                    later_status = compiler_main(
                        [
                            "export-chunk",
                            str(payload_path),
                            "--chunk-index",
                            "1",
                            "--expect-payload-sha256",
                            wrapper["payload_sha256"],
                            "--expect-encoded-sha256",
                            wrapper["encoded_sha256"],
                        ]
                    )
                self.assertEqual(later_status, 0)
                later_wrapper = json.loads(later_output.getvalue())
                self.assertEqual(later_wrapper["chunk_index"], 1)
                self.assertEqual(
                    later_wrapper["payload_sha256"],
                    wrapper["payload_sha256"],
                )
                self.assertEqual(
                    later_wrapper["encoded_sha256"],
                    wrapper["encoded_sha256"],
                )
                self.assertEqual(
                    later_output.getvalue().encode("utf-8"),
                    canonical_transport_wrapper_bytes(later_wrapper),
                )
                self.assertFalse(later_output.getvalue().endswith("\n"))

    def test_export_chunk_cli_handled_failure_is_exact_no_lf_json_stdout(self):
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing.bin"
            output = io.StringIO()
            with redirect_stdout(output):
                status = compiler_main(
                    [
                        "export-chunk",
                        str(missing),
                        "--chunk-index",
                        "0",
                    ]
                )
            self.assertEqual(status, 1)
            failure = json.loads(output.getvalue())
            self.assertEqual(
                set(failure),
                {"compiler", "error", "status"},
            )
            self.assertEqual(failure["compiler"], "bsc-gpt-artifact-compiler-v4")
            self.assertEqual(failure["status"], "blocked")
            self.assertTrue(failure["error"])
            self.assertEqual(
                output.getvalue().encode("utf-8"),
                canonical_transport_wrapper_bytes(failure),
            )
            self.assertFalse(output.getvalue().endswith("\n"))

    def test_transport_prompt_contains_exact_indexed_fresh_read_commands(self):
        prompt = transport_fallback_prompt("audit_report.md", 0)
        self.assertIn(
            "python /mnt/data/gpt_artifact_compiler.py export-chunk "
            "/mnt/data/audit_report.md --chunk-index 0",
            prompt,
        )
        self.assertIn("Use the enabled Data Analysis tool now", prompt)
        self.assertIn(
            "A visible Data Analysis invocation of the exact command below is "
            "mandatory before any answer",
            prompt,
        )
        self.assertIn("Do not read, trim, normalize, or encode", prompt)
        self.assertIn("complete stdout byte-for-byte", prompt)
        self.assertIn("compiler-generated blocked record", prompt)
        self.assertIn("no trailing line feed", prompt)
        self.assertIn("Never infer or emit export_failed", prompt)
        self.assertNotIn("state export_failed", prompt)
        self.assertNotIn("export-wrapper", prompt)

        payload_hash = "1" * 64
        encoded_hash = "2" * 64
        later = transport_fallback_prompt(
            "audit_report.md",
            1,
            expected_payload_sha256=payload_hash,
            expected_encoded_sha256=encoded_hash,
        )
        self.assertIn("--chunk-index 1", later)
        self.assertIn(f"--expect-payload-sha256 {payload_hash}", later)
        self.assertIn(f"--expect-encoded-sha256 {encoded_hash}", later)
        with self.assertRaisesRegex(ValueError, "later transport chunks require"):
            transport_fallback_prompt("audit_report.md", 1)

    def test_compile_cli_captures_runtime_once_and_rejects_model_override(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_root = root / "source"
            output_root = root / "output"
            source_root.mkdir()
            output_root.mkdir()
            frozen_paths: dict[str, str] = {}
            for filename, data in self.frozen().items():
                source = source_root / filename
                destination = output_root / filename
                source.write_bytes(data)
                destination.write_bytes(data)
                frozen_paths[filename] = str(source)
            spec = {
                "report_body": (
                    "# BSC audit report\n\n"
                    "The supplied bytes were checked through the deterministic "
                    "compiler transaction."
                ),
                "frozen_artifact_paths": frozen_paths,
                "audit_return_template": self.template(),
            }
            spec_path = root / "compile-spec.json"
            spec_path.write_bytes(canonical_json_bytes(spec))
            output = io.StringIO()
            with redirect_stdout(output):
                status = compiler_main(
                    [
                        "compile",
                        "--spec",
                        str(spec_path),
                        "--output-dir",
                        str(output_root),
                    ]
                )
            self.assertEqual(status, 0, output.getvalue())
            ledger = (output_root / BOUND_RUNTIME_ARTIFACT).read_text(
                encoding="utf-8"
            )
            self.assertEqual(
                ledger.count(f"session_reported_runtime={sys.version}\n"),
                1,
            )
            document = json.loads(
                (output_root / BOUND_RETURN_ARTIFACT).read_text(encoding="utf-8")
            )
            analysis = next(
                row
                for row in document["execution"]
                if row["activity"] == "chatgpt_data_analysis"
            )
            self.assertEqual(analysis["version"], sys.version)

            injected = dict(spec)
            injected["session_reported_runtime"] = RUNTIME
            injected_path = root / "compile-spec-injected.json"
            injected_path.write_bytes(canonical_json_bytes(injected))
            injected_output = io.StringIO()
            with redirect_stdout(injected_output):
                injected_status = compiler_main(
                    [
                        "compile",
                        "--spec",
                        str(injected_path),
                        "--output-dir",
                        str(output_root),
                    ]
                )
            self.assertEqual(injected_status, 1)
            self.assertIn(
                "compiler spec fields differ from the strict contract",
                injected_output.getvalue(),
            )

    def test_compiler_does_not_mutate_the_supplied_template(self):
        template = self.template()
        before = copy.deepcopy(template)
        self.finalize(template)
        self.assertEqual(template, before)


if __name__ == "__main__":
    unittest.main()
