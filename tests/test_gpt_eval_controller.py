import base64
import copy
import hashlib
import html
import io
import json
import tempfile
import unittest
import zlib
from contextlib import redirect_stdout
from pathlib import Path

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
    canonical_transport_wrapper_bytes,
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
            "canonical_transport_wrapper_bytes",
            "export_payload_chunk",
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

    def test_transport_request_cli_emits_exact_one_index_prompt_without_newline(self):
        output = io.StringIO()
        with redirect_stdout(output):
            status = controller_main(
                [
                    "transport-request",
                    "--output",
                    "audit_return.json",
                    "--chunk-index",
                    "0",
                ]
            )
        self.assertEqual(status, 0)
        self.assertEqual(
            output.getvalue(),
            transport_fallback_prompt("audit_return.json"),
        )
        self.assertIn(
            "python /mnt/data/gpt_artifact_compiler.py export-chunk "
            "/mnt/data/audit_return.json --chunk-index 0",
            output.getvalue(),
        )
        self.assertIn("complete stdout byte-for-byte", output.getvalue())
        self.assertFalse(output.getvalue().endswith("\n"))

    def transport_wrappers(self, filename: str, payload: bytes) -> list[bytes]:
        first = artifact_compiler.export_payload_chunk(filename, payload, 0)
        documents = [first]
        for chunk_index in range(1, first["chunk_count"]):
            documents.append(
                artifact_compiler.export_payload_chunk(
                    filename,
                    payload,
                    chunk_index,
                    expected_payload_sha256=first["payload_sha256"],
                    expected_encoded_sha256=first["encoded_sha256"],
                )
            )
        return [
            canonical_transport_wrapper_bytes(document) for document in documents
        ]

    def write_captured_wrappers(
        self,
        root: Path,
        filename: str,
        payload: bytes,
    ) -> list[bytes]:
        wrappers = self.transport_wrappers(filename, payload)
        raw = root / "raw"
        raw.mkdir()
        (raw / "response.outerHTML.html").write_text(
            "<article>terminal candidate response</article>",
            encoding="utf-8",
            newline="",
        )
        first = json.loads(wrappers[0])
        for chunk_index, wrapper in enumerate(wrappers):
            parser_name = f"{filename}.export.{chunk_index:05d}.json"
            (root / parser_name).write_bytes(wrapper)
            (raw / parser_name).write_bytes(wrapper)
            if chunk_index == 0:
                prompt = transport_fallback_prompt(filename, 0)
            else:
                prompt = transport_fallback_prompt(
                    filename,
                    chunk_index,
                    expected_payload_sha256=first["payload_sha256"],
                    expected_encoded_sha256=first["encoded_sha256"],
                )
            (
                raw / f"{filename}.transport.{chunk_index:05d}.prompt.txt"
            ).write_bytes(prompt.encode("utf-8"))
            escaped = html.escape(wrapper.decode("utf-8"), quote=False)
            (
                raw
                / f"{filename}.transport.{chunk_index:05d}.outerHTML.html"
            ).write_text(
                f"<article><pre><code>{escaped}</code></pre></article>",
                encoding="utf-8",
                newline="",
            )
        (root / filename).write_bytes(payload)
        return wrappers

    def make_minimal_controller_root(
        self,
        root: Path,
        *,
        output_controls: tuple[str, ...],
        fallback_attempts: tuple[str, ...],
    ) -> None:
        raw = root / "raw"
        raw.mkdir()
        controls = "".join(
            f'<button aria-label="{filename}">{filename}</button>'
            for filename in output_controls
        )
        (raw / "response.outerHTML.html").write_text(
            (
                f"<article>{controls}"
                '<button aria-label="Continue">Continue</button>'
                "terminal response</article>"
            ),
            encoding="utf-8",
            newline="",
        )
        (root / "known_true_induction.txt").write_bytes(b"target\n")
        for filename in eval_controller.KNOWLEDGE_FILENAMES:
            (root / filename).write_bytes(f"{filename}\n".encode("utf-8"))
        for _, filename in eval_controller.CANDIDATE_IDENTITY_FILENAMES:
            (root / filename).write_bytes(f"{filename}\n".encode("utf-8"))
        (root / "artifact_transport.json").write_bytes(b"{}\n")
        (root / "visible_response_dom.txt").write_bytes(b"terminal response\n")
        (root / "preview_prompt.txt").write_bytes(b"prompt")
        for filename in fallback_attempts:
            (
                raw / f"{filename}.transport.00000.prompt.txt"
            ).write_bytes(
                transport_fallback_prompt(filename, 0).encode("utf-8")
            )
            (
                raw / f"{filename}.transport.00000.outerHTML.html"
            ).write_text(
                "<article></article>",
                encoding="utf-8",
                newline="",
            )

    def test_verified_chunk_assembly_round_trips_known_bytes(self):
        payload = b"independently\n" + b"".join(
            hashlib.sha256(index.to_bytes(4, "big")).digest()
            for index in range(400)
        )
        wrappers = self.transport_wrappers("audit_return.json", payload)
        self.assertGreater(len(wrappers), 2)
        filename, assembled = eval_controller.assemble_verified_chunks(wrappers)
        self.assertEqual(filename, "audit_return.json")
        self.assertEqual(assembled, payload)

    def test_transport_wrapper_no_lf_is_strict_for_validation_and_prompt_identity(self):
        payload = b"independently\n"
        wrapper = self.transport_wrappers("audit_return.json", payload)[0]
        document = json.loads(wrapper)
        self.assertEqual(
            wrapper,
            canonical_transport_wrapper_bytes(document),
        )
        self.assertFalse(wrapper.endswith(b"\n"))

        parsed, _ = eval_controller._strict_export_chunk(
            wrapper,
            expected_filename="audit_return.json",
            expected_chunk_index=0,
        )
        self.assertEqual(parsed, document)
        self.assertEqual(
            eval_controller._prompt_identity_from_canonical_wrapper(
                wrapper,
                expected_filename="audit_return.json",
            ),
            (document["payload_sha256"], document["encoded_sha256"]),
        )

        legacy_lf_wrapper = wrapper + b"\n"
        with self.assertRaisesRegex(ValueError, "canonical compiler stdout"):
            eval_controller._strict_export_chunk(legacy_lf_wrapper)
        self.assertIsNone(
            eval_controller._prompt_identity_from_canonical_wrapper(
                legacy_lf_wrapper,
                expected_filename="audit_return.json",
            )
        )

    def test_verified_chunk_assembly_detects_aligned_base64_quartet_omission(self):
        payload = b"independently\n" + b"".join(
            hashlib.sha256(index.to_bytes(4, "big")).digest()
            for index in range(300)
        )
        wrappers = self.transport_wrappers("audit_return.json", payload)
        mutated = json.loads(wrappers[1])
        encoded = mutated["base64"]
        self.assertEqual(len(encoded) % 4, 0)
        mutated["base64"] = encoded[:8] + encoded[12:]
        wrappers[1] = canonical_transport_wrapper_bytes(mutated)
        with self.assertRaisesRegex(ValueError, "Base64 identity"):
            eval_controller.assemble_verified_chunks(wrappers)

    def test_verified_chunk_assembly_rejects_missing_reordered_and_mixed_identity(self):
        payload = b"".join(
            hashlib.sha256(index.to_bytes(4, "big")).digest()
            for index in range(300)
        )
        wrappers = self.transport_wrappers("audit_return.json", payload)
        self.assertGreater(len(wrappers), 2)
        with self.subTest("missing"):
            with self.assertRaisesRegex(ValueError, "complete, contiguous"):
                eval_controller.assemble_verified_chunks(
                    wrappers[:1] + wrappers[2:]
                )
        with self.subTest("reordered"):
            with self.assertRaisesRegex(ValueError, "complete, contiguous"):
                eval_controller.assemble_verified_chunks(
                    [wrappers[1], wrappers[0], *wrappers[2:]]
                )
        with self.subTest("mixed_identity"):
            mixed = list(wrappers)
            document = json.loads(mixed[1])
            document["payload_sha256"] = "f" * 64
            mixed[1] = canonical_transport_wrapper_bytes(document)
            with self.assertRaisesRegex(ValueError, "repeated payload identity"):
                eval_controller.assemble_verified_chunks(mixed)

    def test_assembler_accepts_one_valid_cross_runtime_zlib_stream(self):
        payload = (b"cross-runtime-zlib\n" * 5000) + b"independently\n"
        compressor = zlib.compressobj(level=9, strategy=zlib.Z_HUFFMAN_ONLY)
        encoded = compressor.compress(payload) + compressor.flush()
        chunks = [
            encoded[offset : offset + artifact_compiler.TRANSPORT_CHUNK_BYTES]
            for offset in range(
                0,
                len(encoded),
                artifact_compiler.TRANSPORT_CHUNK_BYTES,
            )
        ]
        wrappers = []
        for chunk_index, chunk in enumerate(chunks):
            wrappers.append(
                canonical_transport_wrapper_bytes(
                    {
                        "transport_version": artifact_compiler.TRANSPORT_CHUNK_VERSION,
                        "filename": "audit_report.md",
                        "encoding": artifact_compiler.TRANSPORT_ENCODING,
                        "payload_size_bytes": len(payload),
                        "payload_sha256": digest(payload),
                        "encoded_size_bytes": len(encoded),
                        "encoded_sha256": digest(encoded),
                        "chunk_index": chunk_index,
                        "chunk_count": len(chunks),
                        "offset_bytes": (
                            chunk_index * artifact_compiler.TRANSPORT_CHUNK_BYTES
                        ),
                        "chunk_size_bytes": len(chunk),
                        "chunk_sha256": digest(chunk),
                        "base64": base64.b64encode(chunk).decode("ascii"),
                    }
                )
            )
        self.assertNotEqual(zlib.compress(payload, level=9), encoded)
        self.assertEqual(
            eval_controller.assemble_verified_chunks(wrappers),
            ("audit_report.md", payload),
        )

    def test_assembler_refuses_to_overwrite_a_different_payload(self):
        payload = b"exact acquired bytes\n"
        wrappers = self.transport_wrappers("audit_return.json", payload)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = []
            for index, wrapper in enumerate(wrappers):
                path = root / f"audit_return.json.export.{index:05d}.json"
                path.write_bytes(wrapper)
                paths.append(path)
            destination = root / "audit_return.json"
            destination.write_bytes(b"different\n")
            with self.assertRaisesRegex(ValueError, "different payload"):
                eval_controller.assemble_verified_chunk_files(paths, destination)
            self.assertEqual(destination.read_bytes(), b"different\n")
            destination.unlink()
            result = eval_controller.assemble_verified_chunk_files(
                paths,
                destination,
            )
            self.assertEqual(result["write_state"], "created")
            self.assertEqual(destination.read_bytes(), payload)
            result = eval_controller.assemble_verified_chunk_files(
                paths,
                destination,
            )
            self.assertEqual(result["write_state"], "verified_unchanged")

    def test_controller_inventory_binds_complete_indexed_transport(self):
        payload = b"independently\n" + b"".join(
            hashlib.sha256(index.to_bytes(4, "big")).digest()
            for index in range(250)
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wrappers = self.write_captured_wrappers(
                root,
                "audit_return.json",
                payload,
            )
            captures, attempts = eval_controller._capture_transport_inventory(root)
            self.assertEqual(len(captures), len(wrappers))
            self.assertEqual(
                [item["chunk_index"] for item in captures],
                list(range(len(wrappers))),
            )
            self.assertTrue(
                all(
                    item["response_outcome"] == "chunk_wrapper_captured"
                    for item in attempts
                )
            )
            self.assertEqual(
                captures[0]["parser_input_filename"],
                "audit_return.json.export.00000.json",
            )

    def test_semantically_bad_exact_wrapper_is_candidate_evidence_not_controller_error(self):
        payload = b"independently\n" + b"x" * 5000
        wrapper = json.loads(
            self.transport_wrappers("audit_return.json", payload)[0]
        )
        wrapper["base64"] = wrapper["base64"][:-4]
        wrapper_bytes = canonical_transport_wrapper_bytes(wrapper)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = root / "raw"
            raw.mkdir()
            (raw / "response.outerHTML.html").write_text(
                "<article>terminal response</article>",
                encoding="utf-8",
                newline="",
            )
            parser_name = "audit_return.json.export.00000.json"
            (root / parser_name).write_bytes(wrapper_bytes)
            (raw / parser_name).write_bytes(wrapper_bytes)
            (
                raw / "audit_return.json.transport.00000.prompt.txt"
            ).write_bytes(
                transport_fallback_prompt("audit_return.json", 0).encode("utf-8")
            )
            escaped = html.escape(wrapper_bytes.decode("utf-8"), quote=False)
            (
                raw / "audit_return.json.transport.00000.outerHTML.html"
            ).write_text(
                f"<article><pre><code>{escaped}</code></pre></article>",
                encoding="utf-8",
                newline="",
            )
            captures, attempts = eval_controller._capture_transport_inventory(root)
            self.assertEqual(len(captures), 1)
            self.assertEqual(
                attempts[0]["response_outcome"],
                "chunk_wrapper_captured",
            )
            with self.assertRaises(ValueError):
                eval_controller.assemble_verified_chunks([wrapper_bytes])

    def test_attempt_after_semantically_bad_wrapper_invalidates_controller(self):
        payload = b"".join(
            hashlib.sha256(index.to_bytes(4, "big")).digest()
            for index in range(300)
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wrappers = self.write_captured_wrappers(
                root,
                "audit_return.json",
                payload,
            )
            self.assertGreater(len(wrappers), 2)
            document = json.loads(wrappers[1])
            document["offset_bytes"] += 1
            mutated = canonical_transport_wrapper_bytes(document)
            parser_name = "audit_return.json.export.00001.json"
            (root / parser_name).write_bytes(mutated)
            (root / "raw" / parser_name).write_bytes(mutated)
            escaped = html.escape(mutated.decode("utf-8"), quote=False)
            (
                root
                / "raw"
                / "audit_return.json.transport.00001.outerHTML.html"
            ).write_text(
                f"<article><pre><code>{escaped}</code></pre></article>",
                encoding="utf-8",
                newline="",
            )
            with self.assertRaisesRegex(ValueError, "must be terminal"):
                eval_controller._capture_transport_inventory(root)

    def test_aggregate_stream_contradiction_does_not_invalidate_exact_capture(self):
        payload = b"".join(
            hashlib.sha256(index.to_bytes(4, "big")).digest()
            for index in range(300)
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wrappers = self.write_captured_wrappers(
                root,
                "audit_return.json",
                payload,
            )
            mutated_wrappers: list[bytes] = []
            payload_sha256 = json.loads(wrappers[0])["payload_sha256"]
            encoded_sha256 = "f" * 64
            for chunk_index, wrapper in enumerate(wrappers):
                document = json.loads(wrapper)
                document["encoded_sha256"] = encoded_sha256
                mutated = canonical_transport_wrapper_bytes(document)
                mutated_wrappers.append(mutated)
                parser_name = (
                    f"audit_return.json.export.{chunk_index:05d}.json"
                )
                (root / parser_name).write_bytes(mutated)
                (root / "raw" / parser_name).write_bytes(mutated)
                if chunk_index > 0:
                    prompt = transport_fallback_prompt(
                        "audit_return.json",
                        chunk_index,
                        expected_payload_sha256=payload_sha256,
                        expected_encoded_sha256=encoded_sha256,
                    )
                    (
                        root
                        / "raw"
                        / (
                            "audit_return.json.transport."
                            f"{chunk_index:05d}.prompt.txt"
                        )
                    ).write_bytes(prompt.encode("utf-8"))
                escaped = html.escape(mutated.decode("utf-8"), quote=False)
                (
                    root
                    / "raw"
                    / (
                        "audit_return.json.transport."
                        f"{chunk_index:05d}.outerHTML.html"
                    )
                ).write_text(
                    f"<article><pre><code>{escaped}</code></pre></article>",
                    encoding="utf-8",
                    newline="",
                )
            captures, attempts = eval_controller._capture_transport_inventory(root)
            self.assertEqual(len(captures), len(mutated_wrappers))
            self.assertTrue(
                all(
                    item["response_outcome"] == "chunk_wrapper_captured"
                    for item in attempts
                )
            )
            with self.assertRaisesRegex(ValueError, "encoded payload identity"):
                eval_controller.assemble_verified_chunks(mutated_wrappers)

    def test_failed_exact_attempts_preserve_blank_and_file_control_outcomes(self):
        variants = {
            "blank_response": "<article></article>",
            "file_control_only": (
                '<article><button aria-label="noncanonical.wrapper.json">'
                "noncanonical.wrapper.json</button></article>"
            ),
        }
        for expected, response in variants.items():
            with self.subTest(expected):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    raw = root / "raw"
                    raw.mkdir()
                    (raw / "response.outerHTML.html").write_text(
                        "<article>terminal response</article>",
                        encoding="utf-8",
                        newline="",
                    )
                    (
                        raw / "audit_return.json.transport.00000.prompt.txt"
                    ).write_bytes(
                        transport_fallback_prompt(
                            "audit_return.json",
                            0,
                        ).encode("utf-8")
                    )
                    (
                        raw
                        / "audit_return.json.transport.00000.outerHTML.html"
                    ).write_text(response, encoding="utf-8", newline="")
                    captures, attempts = (
                        eval_controller._capture_transport_inventory(root)
                    )
                    self.assertEqual(captures, [])
                    self.assertEqual(attempts[0]["response_outcome"], expected)
                    if expected == "file_control_only":
                        self.assertEqual(
                            attempts[0]["response_file_controls"],
                            ["noncanonical.wrapper.json"],
                        )

    def test_single_code_block_without_raw_parser_capture_invalidates_controller(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = root / "raw"
            raw.mkdir()
            (raw / "response.outerHTML.html").write_text(
                "<article>terminal response</article>",
                encoding="utf-8",
                newline="",
            )
            (
                raw / "audit_return.json.transport.00000.prompt.txt"
            ).write_bytes(
                transport_fallback_prompt("audit_return.json", 0).encode("utf-8")
            )
            (
                raw / "audit_return.json.transport.00000.outerHTML.html"
            ).write_text(
                "<article><pre><code>{}</code></pre></article>",
                encoding="utf-8",
                newline="",
            )
            with self.assertRaisesRegex(ValueError, "raw/parser"):
                eval_controller._capture_transport_inventory(root)

    def test_output_controls_are_exact_raw_verified_observations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_minimal_controller_root(
                root,
                output_controls=(
                    "audit_report.md",
                    "proof_reconstruction.md",
                ),
                fallback_attempts=(
                    "audit_report.md",
                    "proof_reconstruction.md",
                ),
            )
            record = eval_controller.build_controller_record(
                root=root,
                case_id="known-true-induction",
                trial_id="D01",
                counting_state="preflight",
                target_filename="known_true_induction.txt",
                output_filenames=[],
                session_reference="preview:test",
                observability_boundary="Visible Preview response only.",
                output_control_filenames=[
                    "audit_report.md",
                    "proof_reconstruction.md",
                ],
            )
            self.assertEqual(
                record["observed_output_controls"],
                ["audit_report.md", "proof_reconstruction.md"],
            )
            issues = eval_controller.validate_controller_record(
                root=root,
                record=record,
                expected_case_id="known-true-induction",
                expected_preview_prompt=b"prompt",
                expected_inputs=record["inputs"],
                expected_candidate_identity=record["candidate_identity"],
                expected_output_filenames=set(),
                required_output_filenames={"audit_report.md"},
                repository_root=Path(__file__).resolve().parents[1],
            )
            self.assertEqual(issues, [])
            omitted = copy.deepcopy(record)
            omitted["observed_output_controls"] = ["audit_report.md"]
            issues = eval_controller.validate_controller_record(
                root=root,
                record=omitted,
                expected_case_id="known-true-induction",
                expected_preview_prompt=b"prompt",
                expected_inputs=record["inputs"],
                expected_candidate_identity=record["candidate_identity"],
                expected_output_filenames=set(),
                required_output_filenames={"audit_report.md"},
                repository_root=Path(__file__).resolve().parents[1],
            )
            self.assertIn(
                "CONTROLLER_OUTPUT_CONTROL_ROSTER_MISMATCH",
                {issue["code"] for issue in issues},
            )

    def test_record_builder_rejects_an_omitted_optional_generated_control(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_minimal_controller_root(
                root,
                output_controls=(
                    "audit_report.md",
                    "proof_reconstruction.md",
                ),
                fallback_attempts=(),
            )
            with self.assertRaisesRegex(
                ValueError,
                "observed output controls must equal",
            ):
                eval_controller.build_controller_record(
                    root=root,
                    case_id="known-true-induction",
                    trial_id="D01",
                    counting_state="preflight",
                    target_filename="known_true_induction.txt",
                    output_filenames=[],
                    session_reference="preview:test",
                    observability_boundary="Visible Preview response only.",
                    output_control_filenames=["audit_report.md"],
                )

    def test_unacquired_visible_control_requires_chunk_zero_attempt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_minimal_controller_root(
                root,
                output_controls=(
                    "audit_report.md",
                    "proof_reconstruction.md",
                ),
                fallback_attempts=("audit_report.md",),
            )
            record = eval_controller.build_controller_record(
                root=root,
                case_id="known-true-induction",
                trial_id="D01",
                counting_state="preflight",
                target_filename="known_true_induction.txt",
                output_filenames=[],
                session_reference="preview:test",
                observability_boundary="Visible Preview response only.",
                output_control_filenames=[
                    "audit_report.md",
                    "proof_reconstruction.md",
                ],
            )
            issues = eval_controller.validate_controller_record(
                root=root,
                record=record,
                expected_case_id="known-true-induction",
                expected_preview_prompt=b"prompt",
                expected_inputs=record["inputs"],
                expected_candidate_identity=record["candidate_identity"],
                expected_output_filenames=set(),
                required_output_filenames={"audit_report.md"},
                repository_root=Path(__file__).resolve().parents[1],
            )
            self.assertIn(
                "CONTROLLER_FALLBACK_ATTEMPT_MISSING",
                {issue["code"] for issue in issues},
            )
            fallback_issue = next(
                issue
                for issue in issues
                if issue["code"] == "CONTROLLER_FALLBACK_ATTEMPT_MISSING"
            )
            self.assertIn("proof_reconstruction.md", fallback_issue["message"])
            self.assertNotIn("'audit_report.md'", fallback_issue["message"])

    def test_acquired_output_bytes_remain_separate_from_visible_controls(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_minimal_controller_root(
                root,
                output_controls=(
                    "audit_report.md",
                    "proof_reconstruction.md",
                ),
                fallback_attempts=("audit_report.md",),
            )
            (root / "proof_reconstruction.md").write_bytes(
                b"independently acquired output bytes\n"
            )
            record = eval_controller.build_controller_record(
                root=root,
                case_id="known-true-induction",
                trial_id="D01",
                counting_state="preflight",
                target_filename="known_true_induction.txt",
                output_filenames=["proof_reconstruction.md"],
                session_reference="preview:test",
                observability_boundary="Visible Preview response only.",
                output_control_filenames=[
                    "audit_report.md",
                    "proof_reconstruction.md",
                ],
            )
            self.assertEqual(
                record["observed_output_controls"],
                ["audit_report.md", "proof_reconstruction.md"],
            )
            self.assertEqual(
                [item["filename"] for item in record["observed_outputs"]],
                ["proof_reconstruction.md"],
            )
            issues = eval_controller.validate_controller_record(
                root=root,
                record=record,
                expected_case_id="known-true-induction",
                expected_preview_prompt=b"prompt",
                expected_inputs=record["inputs"],
                expected_candidate_identity=record["candidate_identity"],
                expected_output_filenames={"proof_reconstruction.md"},
                required_output_filenames={"audit_report.md"},
                repository_root=Path(__file__).resolve().parents[1],
            )
            self.assertEqual(issues, [])

    def test_prefixed_file_control_is_normalized_and_non_file_control_is_ignored(self):
        response = (
            '<article><button aria-label="Download audit_report.md"></button>'
            '<button aria-label="Continue"></button></article>'
        ).encode("utf-8")
        _, controls = eval_controller._inspect_response_outer_html(response)
        self.assertEqual(controls, ("audit_report.md",))

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
