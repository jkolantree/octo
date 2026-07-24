import base64
import copy
import hashlib
import io
import json
import sys
import tempfile
import unittest
import unicodedata
import zlib
from contextlib import redirect_stderr, redirect_stdout
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
    COMPILE_RESULT_FIELDS,
    COMPILER_VERSION,
    EXPORT_CHUNK_FIELDS,
    MAX_COMPILE_STDOUT_BYTES,
    RECOVERY_STATE_DATA_SHARD_RECOVERED,
    RECOVERY_STATE_NOT_NEEDED,
    RECOVERY_STATE_PARITY_DEGRADED_NOT_USED,
    REPORT_PROJECTION_MARKER,
    SAME_RESPONSE_CHUNK_FIELDS,
    SAME_RESPONSE_PARITY_FIELDS,
    SAME_RESPONSE_RECOVERY_RECEIPT_FIELDS,
    SAME_RESPONSE_RECOVERY_STATES,
    SAME_RESPONSE_TRANSPORT_FIELDS,
    SAME_RESPONSE_TRANSPORT_VERSION,
    TRANSPORT_CHUNK_BYTES,
    TRANSPORT_CHUNK_VERSION,
    TRANSPORT_CONTAINER_MAGIC,
    TRANSPORT_CONTAINER_VERSION,
    TRANSPORT_ENCODING,
    XOR_PARITY_SCHEME,
    _stable_read_payload,
    _transport_chunks,
    _xor_parity_shard,
    build_same_response_transport,
    build_transport_container,
    canonical_json_bytes,
    canonical_transport_wrapper_bytes,
    export_payload_chunk,
    finalize_candidate_artifacts,
    main as compiler_main,
    output_record,
    parse_compile_transport_stdout,
    parse_compile_transport_stdout_with_receipt,
    parse_same_response_transport,
    parse_same_response_transport_with_receipt,
    parse_transport_container,
    sha256_bytes,
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
        self.assertEqual(
            set(finalized.transport_files),
            {
                "claim_valid.json",
                "defect_composition_valid.json",
                BOUND_REPORT_ARTIFACT,
                BOUND_RUNTIME_ARTIFACT,
                BOUND_RETURN_ARTIFACT,
            },
        )
        self.assertNotIn("atomic_modulus_valid.json", finalized.transport_files)
        for filename, data in finalized.transport_files.items():
            self.assertIs(data, finalized.files[filename])

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

    def test_report_preserves_unicode_math_and_literal_latex_backslashes(self):
        report_body = (
            "# BSC audit report\n\n"
            "∀ n ∈ ℤ, n ≥ 1 ⇒ ∑_{k=1}^{n}(2k−1)=n².\n\n"
            r"A literal LaTeX fallback remains byte-exact: \forall."
        )
        finalized = finalize_candidate_artifacts(
            session_reported_runtime=RUNTIME,
            report_body=report_body,
            frozen_artifacts=self.frozen(),
            audit_return_template=self.template(),
        )
        report = finalized.files[BOUND_REPORT_ARTIFACT].decode("utf-8")
        self.assertIn("∀ n ∈ ℤ, n ≥ 1 ⇒ ∑_{k=1}^{n}(2k−1)=n²", report)
        self.assertIn(r"\forall", report)
        self.assertFalse(
            any(
                unicodedata.category(character) == "Cc"
                and character != "\n"
                for character in report
            )
        )

    def test_report_body_rejects_interpreted_latex_control_escapes(self):
        damaged_fragments = {
            "alpha": "\a" + "lpha",
            "beta": "\b" + "eta",
            "forall": "\f" + "orall",
            "theta": "\t" + "heta",
            "rho": "\r" + "ho",
            "varphi": "\v" + "arphi",
            "unicode-c1": "\u0085",
        }
        for name, fragment in damaged_fragments.items():
            with self.subTest(name=name):
                with self.assertRaisesRegex(
                    ValueError,
                    "report body contains prohibited Unicode controls",
                ):
                    finalize_candidate_artifacts(
                        session_reported_runtime=RUNTIME,
                        report_body=f"# Report\n\nDamaged {fragment}.",
                        frozen_artifacts=self.frozen(),
                        audit_return_template=self.template(),
                    )

    def test_return_template_and_generated_json_reject_controls(self):
        template = self.template()
        template["claims"][0]["statement"] = "Damaged " + "\n" + "abla."
        with self.assertRaisesRegex(
            ValueError,
            "audit return template.*contains prohibited Unicode controls",
        ):
            finalize_candidate_artifacts(
                session_reported_runtime=RUNTIME,
                report_body="# Report\n\nControl-free body.",
                frozen_artifacts=self.frozen(),
                audit_return_template=template,
            )

        frozen = self.frozen()
        frozen["defect_composition_valid.json"] = canonical_json_bytes(
            {"statement": "Damaged " + "\f" + "orall."}
        )
        with self.assertRaisesRegex(
            ValueError,
            "generated JSON artifact.*contains prohibited Unicode controls",
        ):
            finalize_candidate_artifacts(
                session_reported_runtime=RUNTIME,
                report_body="# Report\n\nControl-free body.",
                frozen_artifacts=frozen,
                audit_return_template=self.template(),
            )

    def test_all_textual_media_and_input_roles_reject_controls_before_hashing(self):
        cases = (
            ("request", "artifact:request", "application/json"),
            ("source", "artifact:source", "application/json"),
            ("problem-json", "artifact:evidence", "application/problem+json"),
            ("yaml", "artifact:evidence", "application/yaml"),
            ("javascript", "artifact:evidence", "application/javascript"),
            ("mixed-case", "artifact:evidence", "TEXT/PLAIN; charset=UTF-8"),
        )
        for name, artifact_id, media_type in cases:
            with self.subTest(name=name):
                template = self.template()
                artifact = next(
                    row for row in template["artifacts"] if row["id"] == artifact_id
                )
                artifact["media_type"] = media_type
                frozen = self.frozen()
                frozen[artifact["filename"]] = b"damaged\x0cbytes"
                with patch(
                    "scripts.gpt_artifact_compiler.sha256_bytes"
                ) as digest:
                    with self.assertRaisesRegex(
                        ValueError,
                        "text artifact.*contains prohibited Unicode controls",
                    ):
                        finalize_candidate_artifacts(
                            session_reported_runtime=RUNTIME,
                            report_body="# Report\n\nControl-free body.",
                            frozen_artifacts=frozen,
                            audit_return_template=template,
                        )
                digest.assert_not_called()

    def test_suffixed_generated_json_rejects_escaped_controls_before_hashing(self):
        payloads = {
            "value-form-feed": {"statement": "Damaged " + "\f" + "orall."},
            "key-line-feed": {"Damaged " + "\n" + "abla": "value"},
        }
        for name, payload in payloads.items():
            with self.subTest(name=name):
                template = self.template()
                artifact = next(
                    row
                    for row in template["artifacts"]
                    if row["id"] == "artifact:evidence"
                )
                artifact["media_type"] = "application/problem+json; charset=utf-8"
                frozen = self.frozen()
                frozen[artifact["filename"]] = canonical_json_bytes(payload)
                with patch(
                    "scripts.gpt_artifact_compiler.sha256_bytes"
                ) as digest:
                    with self.assertRaisesRegex(
                        ValueError,
                        "generated JSON artifact.*contains prohibited Unicode controls",
                    ):
                        finalize_candidate_artifacts(
                            session_reported_runtime=RUNTIME,
                            report_body="# Report\n\nControl-free body.",
                            frozen_artifacts=frozen,
                            audit_return_template=template,
                        )
                digest.assert_not_called()

    def test_textual_input_must_be_strict_utf8_before_hashing(self):
        template = self.template()
        artifact = next(
            row
            for row in template["artifacts"]
            if row["id"] == "artifact:source"
        )
        artifact["media_type"] = "application/yaml"
        frozen = self.frozen()
        frozen[artifact["filename"]] = b"\xff"
        with patch("scripts.gpt_artifact_compiler.sha256_bytes") as digest:
            with self.assertRaisesRegex(
                ValueError,
                "text artifact must be strict UTF-8",
            ):
                finalize_candidate_artifacts(
                    session_reported_runtime=RUNTIME,
                    report_body="# Report\n\nControl-free body.",
                    frozen_artifacts=frozen,
                    audit_return_template=template,
                )
        digest.assert_not_called()

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

    def same_response_document(self):
        finalized = self.finalize()
        document = {
            "compiler": COMPILER_VERSION,
            "status": "pass",
            "outputs": list(finalized.identities),
            "return_serialized_last": True,
            "transport": build_same_response_transport(
                finalized.transport_files,
            ),
        }
        return finalized, document

    @staticmethod
    def parse_same_response_document_with_receipt(
        finalized,
        document: dict,
    ):
        return parse_compile_transport_stdout_with_receipt(
            canonical_transport_wrapper_bytes(document),
            expected_untransported_files=finalized.files,
            required_untransported_filenames=(
                set(finalized.files) - set(finalized.transport_files)
            ),
        )

    @staticmethod
    def mutate_valid_base64_payload(encoded_text: str) -> str:
        data = bytearray(base64.b64decode(encoded_text, validate=True))
        if not data:
            raise AssertionError("synthetic Base64 payload must not be empty")
        data[len(data) // 2] ^= 0x01
        mutated = base64.b64encode(data).decode("ascii")
        if len(mutated) != len(encoded_text) or mutated == encoded_text:
            raise AssertionError("synthetic Base64 mutation changed text length")
        return mutated

    @staticmethod
    def mutate_invalid_base64_payload(encoded_text: str) -> str:
        if not encoded_text or encoded_text[0] == "!":
            raise AssertionError("synthetic Base64 text cannot be mutated")
        return "!" + encoded_text[1:]

    def prepare_compile_fixture(
        self,
        root: Path,
    ) -> tuple[Path, Path, dict]:
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
            "report_body_lines": [
                "# BSC audit report",
                "",
                "The supplied bytes were checked through the deterministic "
                "compiler transaction.",
            ],
            "frozen_artifact_paths": frozen_paths,
            "audit_return_template": self.template(),
        }
        spec_path = root / "compile-spec.json"
        spec_path.write_bytes(canonical_json_bytes(spec))
        return spec_path, output_root, spec

    @staticmethod
    def replace_same_response_encoded(
        document: dict,
        encoded: bytes,
    ) -> None:
        transport = document["transport"]
        chunks = _transport_chunks(encoded)
        transport["encoded_size_bytes"] = len(encoded)
        transport["encoded_sha256"] = sha256_bytes(encoded)
        transport["chunk_count"] = len(chunks)
        transport["chunks"] = [
            {
                "chunk_index": index,
                "chunk_count": len(chunks),
                "offset_bytes": index * TRANSPORT_CHUNK_BYTES,
                "chunk_size_bytes": len(chunk),
                "chunk_sha256": sha256_bytes(chunk),
                "base64": base64.b64encode(chunk).decode("ascii"),
            }
            for index, chunk in enumerate(chunks)
        ]
        shard_size = (
            TRANSPORT_CHUNK_BYTES if len(chunks) > 1 else len(encoded)
        )
        parity = _xor_parity_shard(chunks, shard_size)
        transport["parity"] = {
            "scheme": XOR_PARITY_SCHEME,
            "shard_size_bytes": shard_size,
            "parity_sha256": sha256_bytes(parity),
            "base64": base64.b64encode(parity).decode("ascii"),
        }

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
                        "--offline-historical-v3",
                        str(payload_path),
                        "--chunk-index",
                        "0",
                    ]
                )
            self.assertEqual(status, 0)
            wrapper = json.loads(output.getvalue())
            self.assertEqual(COMPILER_VERSION, "bsc-gpt-artifact-compiler-v8")
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
                            "--offline-historical-v3",
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
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    compiler_main(
                        [
                            "export-chunk",
                            str(missing),
                            "--chunk-index",
                            "0",
                        ]
                    )
            output = io.StringIO()
            with redirect_stdout(output):
                status = compiler_main(
                    [
                        "export-chunk",
                        "--offline-historical-v3",
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
            self.assertEqual(failure["compiler"], "bsc-gpt-artifact-compiler-v8")
            self.assertEqual(failure["status"], "blocked")
            self.assertTrue(failure["error"])
            self.assertEqual(
                output.getvalue().encode("utf-8"),
                canonical_transport_wrapper_bytes(failure),
            )
            self.assertFalse(output.getvalue().endswith("\n"))

    def test_transport_container_is_deterministic_and_preserves_exact_bytes(self):
        forward = {
            "zeta.txt": b"aligned quartet ZW5k",
            "alpha.txt": b"independently\x00exact\n",
        }
        reverse = dict(reversed(list(forward.items())))
        first = build_transport_container(forward)
        second = build_transport_container(reverse)
        self.assertEqual(first, second)
        self.assertTrue(first.startswith(TRANSPORT_CONTAINER_MAGIC))
        reconstructed = parse_transport_container(first)
        self.assertEqual(
            reconstructed,
            {
                "alpha.txt": b"independently\x00exact\n",
                "zeta.txt": b"aligned quartet ZW5k",
            },
        )
        self.assertIn(b"independently", reconstructed["alpha.txt"])
        self.assertIn(b"ZW5k", reconstructed["zeta.txt"])

    def test_finalizer_is_independent_of_frozen_mapping_order(self):
        forward = self.frozen()
        reverse = dict(reversed(list(forward.items())))
        first = finalize_candidate_artifacts(
            session_reported_runtime=RUNTIME,
            report_body="# BSC audit report\n\nChecked from exact supplied bytes.",
            frozen_artifacts=forward,
            audit_return_template=self.template(),
        )
        second = finalize_candidate_artifacts(
            session_reported_runtime=RUNTIME,
            report_body="# BSC audit report\n\nChecked from exact supplied bytes.",
            frozen_artifacts=reverse,
            audit_return_template=self.template(),
        )
        self.assertEqual(first.files, second.files)
        self.assertEqual(first.identities, second.identities)
        self.assertEqual(first.transport_files, second.transport_files)
        self.assertEqual(first.audit_return, second.audit_return)

    def test_same_response_container_enforces_tight_member_and_aggregate_bounds(self):
        with patch(
            "scripts.gpt_artifact_compiler.MAX_SAME_RESPONSE_MEMBER_BYTES",
            3,
        ):
            with self.assertRaisesRegex(ValueError, "payload exceeds"):
                build_transport_container({"artifact.bin": b"four"})
        with patch(
            "scripts.gpt_artifact_compiler.MAX_TRANSPORT_CONTAINER_BYTES",
            len(TRANSPORT_CONTAINER_MAGIC) + 4,
        ):
            with self.assertRaisesRegex(ValueError, "aggregate"):
                build_transport_container({"artifact.bin": b"x"})

    def test_same_response_transport_has_strict_schema_and_exact_public_roster(self):
        finalized, document = self.same_response_document()
        raw = canonical_transport_wrapper_bytes(document)
        parsed, reconstructed = parse_compile_transport_stdout(
            raw,
            expected_untransported_files=finalized.files,
            required_untransported_filenames=(
                set(finalized.files) - set(finalized.transport_files)
            ),
        )
        expected = [
            "audit_report.md",
            "audit_return.json",
            "chatgpt_data_analysis_output.txt",
            "claim_valid.json",
            "defect_composition_valid.json",
        ]
        self.assertEqual(set(parsed), COMPILE_RESULT_FIELDS)
        self.assertEqual(parsed["compiler"], "bsc-gpt-artifact-compiler-v8")
        self.assertEqual(
            set(parsed["transport"]),
            SAME_RESPONSE_TRANSPORT_FIELDS,
        )
        self.assertEqual(
            parsed["transport"]["transport_version"],
            SAME_RESPONSE_TRANSPORT_VERSION,
        )
        self.assertEqual(
            parsed["transport"]["container_version"],
            TRANSPORT_CONTAINER_VERSION,
        )
        self.assertEqual(parsed["transport"]["encoding"], TRANSPORT_ENCODING)
        self.assertEqual(
            [row["filename"] for row in parsed["transport"]["files"]],
            expected,
        )
        self.assertEqual(list(reconstructed), expected)
        self.assertEqual(reconstructed, finalized.transport_files)
        self.assertLessEqual(len(raw), MAX_COMPILE_STDOUT_BYTES)
        self.assertFalse(raw.endswith(b"\n"))
        for chunk in parsed["transport"]["chunks"]:
            self.assertEqual(set(chunk), SAME_RESPONSE_CHUNK_FIELDS)
        self.assertEqual(
            set(parsed["transport"]["parity"]),
            SAME_RESPONSE_PARITY_FIELDS,
        )
        self.assertEqual(
            parsed["transport"]["parity"]["scheme"],
            XOR_PARITY_SCHEME,
        )

    def test_same_response_xor_parity_is_deterministic_for_known_bytes(self):
        parts = (
            bytes([0x01, 0x02, 0x03]),
            bytes([0x04]),
            bytes([0x08, 0x10, 0x20, 0x40]),
        )
        expected = bytes([0x0D, 0x12, 0x23, 0x40])
        self.assertEqual(_xor_parity_shard(parts, 4), expected)
        self.assertEqual(_xor_parity_shard(parts, 4), expected)

        finalized = self.finalize()
        first = build_same_response_transport(finalized.transport_files)
        second = build_same_response_transport(finalized.transport_files)
        self.assertEqual(first, second)
        parity = first["parity"]
        self.assertEqual(set(parity), SAME_RESPONSE_PARITY_FIELDS)
        self.assertEqual(parity["scheme"], XOR_PARITY_SCHEME)
        parity_bytes = base64.b64decode(parity["base64"], validate=True)
        self.assertEqual(len(parity_bytes), parity["shard_size_bytes"])
        self.assertEqual(
            sha256_bytes(parity_bytes),
            parity["parity_sha256"],
        )

    def test_same_response_pristine_roundtrip_returns_exact_no_recovery_receipt(
        self,
    ):
        finalized, document = self.same_response_document()
        parsed, reconstructed, receipt = (
            self.parse_same_response_document_with_receipt(
                finalized,
                document,
            )
        )
        self.assertEqual(parsed, document)
        self.assertEqual(reconstructed, finalized.transport_files)
        self.assertEqual(set(receipt), SAME_RESPONSE_RECOVERY_RECEIPT_FIELDS)
        self.assertEqual(
            set(SAME_RESPONSE_RECOVERY_STATES),
            {
                RECOVERY_STATE_NOT_NEEDED,
                RECOVERY_STATE_DATA_SHARD_RECOVERED,
                RECOVERY_STATE_PARITY_DEGRADED_NOT_USED,
            },
        )
        self.assertEqual(
            receipt,
            {
                "scheme": XOR_PARITY_SCHEME,
                "state": RECOVERY_STATE_NOT_NEEDED,
                "recovered_chunk_index": None,
                "received_base64_sha256": None,
                "reconstructed_chunk_sha256": None,
            },
        )
        self.assertEqual(
            parse_same_response_transport(
                document["transport"],
                expected_transport_filenames=finalized.transport_files,
            ),
            finalized.transport_files,
        )

    def test_same_response_recovers_one_same_length_valid_base64_data_shard(
        self,
    ):
        finalized, document = self.same_response_document()
        mutated = copy.deepcopy(document)
        chunk = mutated["transport"]["chunks"][0]
        received = self.mutate_valid_base64_payload(chunk["base64"])
        chunk["base64"] = received

        _, reconstructed, receipt = (
            self.parse_same_response_document_with_receipt(
                finalized,
                mutated,
            )
        )
        self.assertEqual(reconstructed, finalized.transport_files)
        self.assertEqual(
            receipt,
            {
                "scheme": XOR_PARITY_SCHEME,
                "state": RECOVERY_STATE_DATA_SHARD_RECOVERED,
                "recovered_chunk_index": 0,
                "received_base64_sha256": sha256_bytes(
                    received.encode("ascii")
                ),
                "reconstructed_chunk_sha256": chunk["chunk_sha256"],
            },
        )

    def test_same_response_recovers_one_exact_length_invalid_base64_data_shard(
        self,
    ):
        finalized, document = self.same_response_document()
        mutated = copy.deepcopy(document)
        chunk = mutated["transport"]["chunks"][0]
        received = self.mutate_invalid_base64_payload(chunk["base64"])
        chunk["base64"] = received

        _, reconstructed, receipt = (
            self.parse_same_response_document_with_receipt(
                finalized,
                mutated,
            )
        )
        self.assertEqual(reconstructed, finalized.transport_files)
        self.assertEqual(
            receipt["state"],
            RECOVERY_STATE_DATA_SHARD_RECOVERED,
        )
        self.assertEqual(receipt["recovered_chunk_index"], 0)
        self.assertEqual(
            receipt["received_base64_sha256"],
            sha256_bytes(received.encode("ascii")),
        )
        self.assertEqual(
            receipt["reconstructed_chunk_sha256"],
            chunk["chunk_sha256"],
        )

    def test_same_response_accepts_parity_only_payload_degradation_with_receipt(
        self,
    ):
        finalized, document = self.same_response_document()
        mutated = copy.deepcopy(document)
        parity = mutated["transport"]["parity"]
        received = self.mutate_valid_base64_payload(parity["base64"])
        parity["base64"] = received

        _, reconstructed, receipt = (
            self.parse_same_response_document_with_receipt(
                finalized,
                mutated,
            )
        )
        self.assertEqual(reconstructed, finalized.transport_files)
        self.assertEqual(
            receipt,
            {
                "scheme": XOR_PARITY_SCHEME,
                "state": RECOVERY_STATE_PARITY_DEGRADED_NOT_USED,
                "recovered_chunk_index": None,
                "received_base64_sha256": sha256_bytes(
                    received.encode("ascii")
                ),
                "reconstructed_chunk_sha256": None,
            },
        )

    def test_same_response_recovery_rejects_data_and_parity_failure_combinations(
        self,
    ):
        finalized, document = self.same_response_document()
        self.assertGreaterEqual(len(document["transport"]["chunks"]), 2)

        two_bad_data = copy.deepcopy(document)
        for chunk in two_bad_data["transport"]["chunks"][:2]:
            chunk["base64"] = self.mutate_invalid_base64_payload(
                chunk["base64"]
            )

        bad_data_and_parity = copy.deepcopy(document)
        bad_data_and_parity["transport"]["chunks"][0]["base64"] = (
            self.mutate_invalid_base64_payload(
                bad_data_and_parity["transport"]["chunks"][0]["base64"]
            )
        )
        bad_data_and_parity["transport"]["parity"]["base64"] = (
            self.mutate_invalid_base64_payload(
                bad_data_and_parity["transport"]["parity"]["base64"]
            )
        )

        wrong_declared_data_hash = copy.deepcopy(document)
        wrong_declared_data_hash["transport"]["chunks"][0]["base64"] = (
            self.mutate_valid_base64_payload(
                wrong_declared_data_hash["transport"]["chunks"][0]["base64"]
            )
        )
        wrong_declared_data_hash["transport"]["chunks"][0][
            "chunk_sha256"
        ] = "0" * 64

        cases = {
            "two_bad_data": (
                two_bad_data,
                "more than one invalid data shard",
            ),
            "bad_data_and_parity": (
                bad_data_and_parity,
                "data and parity shards are both invalid",
            ),
            "wrong_declared_data_hash": (
                wrong_declared_data_hash,
                "reconstructed data shard identity",
            ),
        }
        for label, (mutated, message) in cases.items():
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, message):
                    self.parse_same_response_document_with_receipt(
                        finalized,
                        mutated,
                    )

    def test_same_response_recovery_rejects_chunk_and_parity_metadata_mutation(
        self,
    ):
        finalized, document = self.same_response_document()

        chunk_size = copy.deepcopy(document)
        chunk_size["transport"]["chunks"][0]["chunk_size_bytes"] -= 1

        chunk_hash = copy.deepcopy(document)
        chunk_hash["transport"]["chunks"][0]["chunk_sha256"] = "0" * 64

        parity_missing_field = copy.deepcopy(document)
        parity_missing_field["transport"]["parity"].pop("base64")

        parity_scheme = copy.deepcopy(document)
        parity_scheme["transport"]["parity"]["scheme"] = "wrong"

        parity_size = copy.deepcopy(document)
        parity_size["transport"]["parity"]["shard_size_bytes"] -= 1

        parity_hash = copy.deepcopy(document)
        parity_hash["transport"]["parity"]["parity_sha256"] = "0" * 64

        cases = {
            "chunk_size": chunk_size,
            "chunk_hash": chunk_hash,
            "parity_missing_field": parity_missing_field,
            "parity_scheme": parity_scheme,
            "parity_size": parity_size,
            "parity_hash": parity_hash,
        }
        for label, mutated in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    self.parse_same_response_document_with_receipt(
                        finalized,
                        mutated,
                    )

    def test_same_response_recovery_rejects_non_ascii_and_identity_mutations(
        self,
    ):
        finalized, document = self.same_response_document()

        non_ascii_data = copy.deepcopy(document)
        original = non_ascii_data["transport"]["chunks"][0]["base64"]
        non_ascii_data["transport"]["chunks"][0]["base64"] = "é" + original[1:]

        encoded_hash = copy.deepcopy(document)
        encoded_hash["transport"]["encoded_sha256"] = "0" * 64

        container_hash = copy.deepcopy(document)
        container_hash["transport"]["container_sha256"] = "0" * 64

        member_hash = copy.deepcopy(document)
        member_hash["transport"]["files"][0]["sha256"] = "0" * 64

        cases = {
            "non_ascii_data": non_ascii_data,
            "encoded_hash": encoded_hash,
            "container_hash": container_hash,
            "member_hash": member_hash,
        }
        for label, mutated in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    self.parse_same_response_document_with_receipt(
                        finalized,
                        mutated,
                    )

    def test_aligned_base64_quartet_omission_is_detected(self):
        finalized, document = self.same_response_document()
        mutated = copy.deepcopy(document)
        encoded_text = mutated["transport"]["chunks"][0]["base64"]
        self.assertGreaterEqual(len(encoded_text), 12)
        mutated["transport"]["chunks"][0]["base64"] = (
            encoded_text[:4] + encoded_text[8:]
        )
        omitted = base64.b64decode(
            mutated["transport"]["chunks"][0]["base64"],
            validate=True,
        )
        self.assertNotEqual(
            len(omitted),
            mutated["transport"]["chunks"][0]["chunk_size_bytes"],
        )
        with self.assertRaisesRegex(ValueError, "chunk metadata"):
            parse_compile_transport_stdout(
                canonical_transport_wrapper_bytes(mutated),
                expected_untransported_files=finalized.files,
                required_untransported_filenames=(
                    set(finalized.files) - set(finalized.transport_files)
                ),
            )

    def test_same_response_parser_rejects_roster_order_path_hash_and_size_mutations(self):
        finalized, document = self.same_response_document()

        missing_files = dict(finalized.transport_files)
        missing_files.pop("claim_valid.json")
        missing = copy.deepcopy(document)
        missing["transport"] = build_same_response_transport(missing_files)

        missing_return_files = dict(finalized.transport_files)
        missing_return_files.pop(BOUND_RETURN_ARTIFACT)
        missing_return = copy.deepcopy(document)
        missing_return_container = build_transport_container(
            missing_return_files
        )
        missing_return_transport = missing_return["transport"]
        missing_return_transport["container_size_bytes"] = len(
            missing_return_container
        )
        missing_return_transport["container_sha256"] = sha256_bytes(
            missing_return_container
        )
        missing_return_transport["file_count"] = len(missing_return_files)
        missing_return_transport["files"] = [
            output_record(filename, data)
            for filename, data in sorted(missing_return_files.items())
        ]
        self.replace_same_response_encoded(
            missing_return,
            zlib.compress(missing_return_container, level=9),
        )

        reversed_roster = copy.deepcopy(document)
        reversed_roster["transport"]["files"].reverse()

        unsafe_path = copy.deepcopy(document)
        unsafe_path["transport"]["files"][0]["filename"] = "../audit_report.md"

        file_hash = copy.deepcopy(document)
        file_hash["transport"]["files"][0]["sha256"] = "0" * 64

        file_size = copy.deepcopy(document)
        file_size["transport"]["files"][0]["bytes"] += 1

        container_hash = copy.deepcopy(document)
        container_hash["transport"]["container_sha256"] = "0" * 64

        container_size = copy.deepcopy(document)
        container_size["transport"]["container_size_bytes"] += 1

        phantom_output = copy.deepcopy(document)
        phantom_output["outputs"].append(
            {
                "filename": "phantom.txt",
                "bytes": 0,
                "sha256": hashlib.sha256(b"").hexdigest(),
            }
        )
        phantom_output["outputs"].sort(key=lambda item: item["filename"])

        omitted_source_output = copy.deepcopy(document)
        omitted_source_output["outputs"] = [
            item
            for item in omitted_source_output["outputs"]
            if item["filename"] != "atomic_modulus_valid.json"
        ]

        source_output_hash = copy.deepcopy(document)
        source_record = next(
            item
            for item in source_output_hash["outputs"]
            if item["filename"] == "atomic_modulus_valid.json"
        )
        source_record["sha256"] = "0" * 64

        source_output_size = copy.deepcopy(document)
        source_size_record = next(
            item
            for item in source_output_size["outputs"]
            if item["filename"] == "atomic_modulus_valid.json"
        )
        source_size_record["bytes"] += 1

        mutations = {
            "roster": missing,
            "required_return": missing_return,
            "order": reversed_roster,
            "path": unsafe_path,
            "file_hash": file_hash,
            "file_size": file_size,
            "container_hash": container_hash,
            "container_size": container_size,
            "phantom_output": phantom_output,
            "omitted_source_output": omitted_source_output,
            "source_output_hash": source_output_hash,
            "source_output_size": source_output_size,
        }
        for label, mutated in mutations.items():
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    parse_compile_transport_stdout(
                        canonical_transport_wrapper_bytes(mutated),
                        expected_untransported_files=finalized.files,
                        required_untransported_filenames=(
                            set(finalized.files) - set(finalized.transport_files)
                        ),
                    )

    def test_same_response_parser_rejects_rehashed_invalid_zlib_stream(self):
        finalized, document = self.same_response_document()
        mutated = copy.deepcopy(document)
        encoded = b"".join(
            base64.b64decode(chunk["base64"], validate=True)
            for chunk in mutated["transport"]["chunks"]
        )
        corrupted = bytes([encoded[0] ^ 0xFF]) + encoded[1:]
        self.replace_same_response_encoded(mutated, corrupted)
        with self.assertRaisesRegex(ValueError, "zlib stream"):
            parse_compile_transport_stdout(
                canonical_transport_wrapper_bytes(mutated),
                expected_untransported_files=finalized.files,
                required_untransported_filenames=(
                    set(finalized.files) - set(finalized.transport_files)
                ),
            )

    def test_same_response_parser_rejects_source_omitted_from_execution_inputs(self):
        finalized, document = self.same_response_document()
        return_document = json.loads(
            finalized.files[BOUND_RETURN_ARTIFACT].decode("utf-8")
        )
        for row in return_document["execution"]:
            if row["activity"] in {
                "model_reasoning",
                "chatgpt_data_analysis",
            }:
                row["input_artifact_ids"].remove("artifact:source")
        mutated_return = canonical_json_bytes(return_document)
        mutated_files = dict(finalized.transport_files)
        mutated_files[BOUND_RETURN_ARTIFACT] = mutated_return
        mutated = copy.deepcopy(document)
        mutated["transport"] = build_same_response_transport(mutated_files)
        return_identity = next(
            item
            for item in mutated["outputs"]
            if item["filename"] == BOUND_RETURN_ARTIFACT
        )
        return_identity.update(
            bytes=len(mutated_return),
            sha256=sha256_bytes(mutated_return),
        )

        with self.assertRaisesRegex(
            ValueError,
            "model_reasoning must bind exactly request and sources",
        ):
            parse_compile_transport_stdout(
                canonical_transport_wrapper_bytes(mutated),
                expected_untransported_files=finalized.files,
                required_untransported_filenames=(
                    set(finalized.files) - set(finalized.transport_files)
                ),
            )

    def test_compile_cli_emits_same_response_bytes_without_output_tree_dependence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec_path, output_root, spec = self.prepare_compile_fixture(root)
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
            raw = output.getvalue().encode("utf-8")
            self.assertFalse(raw.endswith(b"\n"))
            self.assertLessEqual(len(raw), MAX_COMPILE_STDOUT_BYTES)
            exact_inputs = {
                filename: Path(path).read_bytes()
                for filename, path in spec["frozen_artifact_paths"].items()
            }
            compile_result, reconstructed = parse_compile_transport_stdout(
                raw,
                expected_untransported_files=exact_inputs,
                required_untransported_filenames={
                    "atomic_modulus_valid.json"
                },
            )
            self.assertTrue(compile_result["return_serialized_last"])
            self.assertEqual(
                compile_result["compiler"],
                "bsc-gpt-artifact-compiler-v8",
            )

            ledger = (output_root / BOUND_RUNTIME_ARTIFACT).read_text(
                encoding="utf-8"
            )
            self.assertEqual(
                ledger.count(f"session_reported_runtime={sys.version}\n"),
                1,
            )
            return_document = json.loads(
                (output_root / BOUND_RETURN_ARTIFACT).read_text(encoding="utf-8")
            )
            analysis = next(
                row
                for row in return_document["execution"]
                if row["activity"] == "chatgpt_data_analysis"
            )
            self.assertEqual(analysis["version"], sys.version)
            self.assertEqual(
                reconstructed[BOUND_RETURN_ARTIFACT],
                (output_root / BOUND_RETURN_ARTIFACT).read_bytes(),
            )
            self.assertNotIn(".bsc-transport-v1", output.getvalue())
            self.assertFalse(
                any(
                    path.name.startswith(".bsc-transport")
                    for path in output_root.iterdir()
                )
            )

            captured = dict(reconstructed)
            for filename in captured:
                (output_root / filename).unlink()
            _, replayed = parse_compile_transport_stdout(
                raw,
                expected_untransported_files=exact_inputs,
                required_untransported_filenames={
                    "atomic_modulus_valid.json"
                },
            )
            self.assertEqual(replayed, captured)
            self.assertIn(
                b"compiler transaction",
                replayed[BOUND_REPORT_ARTIFACT],
            )

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
            self.assertFalse(injected_output.getvalue().endswith("\n"))

    def test_compile_stdout_bound_blocks_without_partial_transport_or_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec_path, output_root, _ = self.prepare_compile_fixture(root)
            output = io.StringIO()
            with patch(
                "scripts.gpt_artifact_compiler.MAX_COMPILE_STDOUT_BYTES",
                256,
            ):
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
            self.assertEqual(status, 1)
            failure = json.loads(output.getvalue())
            self.assertEqual(set(failure), {"compiler", "error", "status"})
            self.assertEqual(failure["compiler"], COMPILER_VERSION)
            self.assertEqual(failure["status"], "blocked")
            self.assertNotIn("transport", failure)
            self.assertFalse(output.getvalue().endswith("\n"))
            for filename in (
                BOUND_REPORT_ARTIFACT,
                BOUND_RUNTIME_ARTIFACT,
                BOUND_RETURN_ARTIFACT,
            ):
                self.assertFalse((output_root / filename).exists())

    def test_compile_report_line_contract_blocks_every_latex_escape_collision(self):
        damaged_fragments = {
            "alpha": "\a" + "lpha",
            "beta": "\b" + "eta",
            "forall": "\f" + "orall",
            "nabla": "\n" + "abla",
            "theta": "\t" + "heta",
            "rho": "\r" + "ho",
            "varphi": "\v" + "arphi",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, output_root, spec = self.prepare_compile_fixture(root)
            for name, fragment in damaged_fragments.items():
                with self.subTest(name=name):
                    bad_spec = copy.deepcopy(spec)
                    bad_spec["report_body_lines"] = [
                        "# BSC audit report",
                        "",
                        f"Damaged {fragment}.",
                    ]
                    bad_path = root / f"compile-spec-{name}.json"
                    bad_path.write_bytes(canonical_json_bytes(bad_spec))
                    output = io.StringIO()
                    with redirect_stdout(output):
                        status = compiler_main(
                            [
                                "compile",
                                "--spec",
                                str(bad_path),
                                "--output-dir",
                                str(output_root),
                            ]
                        )
                    self.assertEqual(status, 1)
                    failure = json.loads(output.getvalue())
                    self.assertEqual(failure["status"], "blocked")
                    self.assertIn(
                        "report_body_lines[2] contains prohibited controls",
                        failure["error"],
                    )
                    for filename in (
                        BOUND_REPORT_ARTIFACT,
                        BOUND_RUNTIME_ARTIFACT,
                        BOUND_RETURN_ARTIFACT,
                    ):
                        self.assertFalse((output_root / filename).exists())

    def test_compile_textual_input_control_blocks_before_hash_transport_or_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, output_root, spec = self.prepare_compile_fixture(root)
            request = next(
                row
                for row in spec["audit_return_template"]["artifacts"]
                if row["id"] == "artifact:request"
            )
            request["media_type"] = "application/problem+json; charset=UTF-8"
            Path(spec["frozen_artifact_paths"][request["filename"]]).write_bytes(
                b"damaged\x0cbytes"
            )
            bad_path = root / "compile-spec-text-control.json"
            bad_path.write_bytes(canonical_json_bytes(spec))
            output = io.StringIO()
            with (
                patch(
                    "scripts.gpt_artifact_compiler.sha256_bytes"
                ) as digest,
                patch(
                    "scripts.gpt_artifact_compiler.build_same_response_transport"
                ) as transport,
                redirect_stdout(output),
            ):
                status = compiler_main(
                    [
                        "compile",
                        "--spec",
                        str(bad_path),
                        "--output-dir",
                        str(output_root),
                    ]
                )
            self.assertEqual(status, 1)
            failure = json.loads(output.getvalue())
            self.assertEqual(failure["status"], "blocked")
            self.assertIn(
                "text artifact claim_valid.json contains prohibited Unicode controls",
                failure["error"],
            )
            digest.assert_not_called()
            transport.assert_not_called()
            for filename in (
                BOUND_REPORT_ARTIFACT,
                BOUND_RUNTIME_ARTIFACT,
                BOUND_RETURN_ARTIFACT,
            ):
                self.assertFalse((output_root / filename).exists())

    def test_compiler_does_not_mutate_the_supplied_template(self):
        template = self.template()
        before = copy.deepcopy(template)
        self.finalize(template)
        self.assertEqual(template, before)


if __name__ == "__main__":
    unittest.main()
