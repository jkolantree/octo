import base64
import hashlib
import html
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts.check_gpt_eval_bundle import (
    LIMITATION,
    SCIENTIFIC_RESEARCH_PROJECTION_REQUIRED,
    STATUS_ONLY_RESEARCH_PROJECTION_EMPTY,
    main,
)
from scripts.gpt_artifact_compiler import (
    canonical_transport_wrapper_bytes as compiler_transport_bytes,
    export_payload_chunk,
    transport_fallback_prompt,
)
from scripts.gpt_eval_controller import (
    BOUND_RUNTIME_ARTIFACT,
    CANDIDATE_IDENTITY_FILENAMES,
    CONTROLLER_ARTIFACT_FILENAMES,
    KNOWLEDGE_FILENAMES,
    OPTIONAL_CONTROLLER_ARTIFACT_FILENAMES,
    RAW_RESPONSE_FILENAME,
    _inspect_response_outer_html,
    build_controller_record,
    byte_record,
    canonical_json_bytes,
    main as controller_main,
    output_record,
    runtime_ledger_text,
)


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
VALID_RETURN = EXAMPLES / "audit_return_valid.json"
PYTHON_VERSION = "3.13.5 (main, May  5 2026, 21:05:52) [GCC 14.2.0]"
CASE_ID = "known-true-induction"
TARGET_NAME = "known_true_induction.txt"
TRIAL_ID = "D01"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class GptEvalBundleCheckerTests(unittest.TestCase):
    def case(self, case_id: str = CASE_ID) -> dict:
        for line in (
            ROOT / "gpt" / "evals" / "GPT_EVAL_CASES.jsonl"
        ).read_text(encoding="utf-8").splitlines():
            value = json.loads(line)
            if value["id"] == case_id:
                return value
        raise AssertionError(f"missing frozen case: {case_id}")

    def wrapper(self, filename: str, data: bytes) -> dict:
        return export_payload_chunk(filename, data, 0)

    def write_wrapper(self, root: Path, filename: str, data: bytes) -> None:
        for path in root.glob(f"{filename}.export.*.json"):
            path.unlink()
        raw_root = root / "raw"
        if raw_root.is_dir():
            for pattern in (
                f"{filename}.export.*.json",
                f"{filename}.transport.*.prompt.txt",
                f"{filename}.transport.*.outerHTML.html",
            ):
                for path in raw_root.glob(pattern):
                    path.unlink()
        first = export_payload_chunk(filename, data, 0)
        for chunk_index in range(first["chunk_count"]):
            wrapper = (
                first
                if chunk_index == 0
                else export_payload_chunk(
                    filename,
                    data,
                    chunk_index,
                    expected_payload_sha256=first["payload_sha256"],
                    expected_encoded_sha256=first["encoded_sha256"],
                )
            )
            self.write_wrapper_capture_bytes(
                root,
                filename,
                compiler_transport_bytes(wrapper),
                chunk_index=chunk_index,
                expected_payload_sha256=(
                    first["payload_sha256"] if chunk_index else None
                ),
                expected_encoded_sha256=(
                    first["encoded_sha256"] if chunk_index else None
                ),
            )

    def write_wrapper_capture_bytes(
        self,
        root: Path,
        filename: str,
        wrapper_bytes: bytes,
        *,
        chunk_index: int = 0,
        expected_payload_sha256: str | None = None,
        expected_encoded_sha256: str | None = None,
    ) -> None:
        path = root / f"{filename}.export.{chunk_index:05d}.json"
        path.write_bytes(wrapper_bytes)
        raw_path = root / "raw" / path.name
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(wrapper_bytes)
        (root / "raw" / f"{filename}.transport.{chunk_index:05d}.prompt.txt").write_bytes(
            transport_fallback_prompt(
                filename,
                chunk_index,
                expected_payload_sha256=expected_payload_sha256,
                expected_encoded_sha256=expected_encoded_sha256,
            ).encode("utf-8")
        )
        escaped = html.escape(
            wrapper_bytes.decode("utf-8"),
            quote=False,
        )
        (
            root
            / "raw"
            / f"{filename}.transport.{chunk_index:05d}.outerHTML.html"
        ).write_text(
            f'<article><pre><code class="language-json">{escaped}</code></pre></article>',
            encoding="utf-8",
            newline="",
        )

    def write_return(self, root: Path, record: dict) -> bytes:
        data = (json.dumps(record, indent=2) + "\n").encode("utf-8")
        (root / "audit_return.json").write_bytes(data)
        self.write_wrapper(root, "audit_return.json", data)
        return data

    def write_failed_transport_attempt(
        self,
        root: Path,
        filename: str,
        *,
        chunk_index: int = 0,
        expected_payload_sha256: str | None = None,
        expected_encoded_sha256: str | None = None,
        response_html: str = "<article></article>",
    ) -> None:
        raw = root / "raw"
        raw.mkdir(parents=True, exist_ok=True)
        (raw / f"{filename}.transport.{chunk_index:05d}.prompt.txt").write_text(
            transport_fallback_prompt(
                filename,
                chunk_index,
                expected_payload_sha256=expected_payload_sha256,
                expected_encoded_sha256=expected_encoded_sha256,
            ),
            encoding="utf-8",
            newline="",
        )
        (
            raw
            / f"{filename}.transport.{chunk_index:05d}.outerHTML.html"
        ).write_text(
            response_html,
            encoding="utf-8",
            newline="",
        )

    def write_transport_record(self, root: Path, record: dict) -> None:
        generated = {
            artifact["filename"]
            for artifact in record["artifacts"]
        } | {"audit_return.json"}
        rows = []
        for filename in sorted(generated):
            data = (root / filename).read_bytes()
            base64_transport = filename in {"audit_report.md", "audit_return.json"}
            chunks = sorted(
                path.name
                for path in root.glob(f"{filename}.export.[0-9][0-9][0-9][0-9][0-9].json")
            )
            rows.append(
                {
                    "filename": filename,
                    "method": (
                        "chunked_base64_export"
                        if base64_transport
                        else "direct_download"
                    ),
                    "direct_download_outcome": (
                        "no_download_event" if base64_transport else "download_event"
                    ),
                    "bytes": len(data),
                    "sha256": sha256(data),
                    "export_chunks": chunks if base64_transport else None,
                }
            )
        (root / "artifact_transport.json").write_text(
            json.dumps(
                {"transport_version": "2.0", "records": rows},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def copy_controller_inputs_and_identity(
        self,
        root: Path,
        *,
        case_id: str,
    ) -> str:
        case = self.case(case_id)
        fixture = case["fixture_paths"][0]
        source = ROOT / "gpt" / fixture
        target_name = source.name
        shutil.copyfile(source, root / target_name)
        for filename in KNOWLEDGE_FILENAMES:
            shutil.copyfile(
                ROOT / "gpt" / "knowledge" / filename,
                root / filename,
            )
        canonical_copies = {
            "GPT_FROZEN_CANDIDATE.json": ROOT
            / "docs"
            / "GPT_FROZEN_CANDIDATE.json",
            "GPT_PROFILE.json": ROOT / "gpt" / "_source" / "GPT_PROFILE.json",
            "GPT_INSTRUCTIONS.md": ROOT / "gpt" / "GPT_INSTRUCTIONS.md",
            "GPT_EVAL_SPEC.json": ROOT / "gpt" / "_source" / "GPT_EVAL_SPEC.json",
        }
        for filename, canonical in canonical_copies.items():
            shutil.copyfile(canonical, root / filename)
        (root / "preview_prompt.txt").write_bytes(
            case["preview_prompt"].encode("utf-8")
        )
        return target_name

    def make_prose_only_bundle(self, root: Path, *, case_id: str = CASE_ID) -> None:
        target_name = self.copy_controller_inputs_and_identity(
            root,
            case_id=case_id,
        )
        (root / "visible_response_dom.txt").write_text(
            "Complete visible sections; no generated artifacts were requested.\n",
            encoding="utf-8",
        )
        (root / "raw").mkdir(exist_ok=True)
        (root / "raw" / "response.outerHTML.html").write_text(
            "<article>Complete visible sections; no generated artifacts were requested.</article>\n",
            encoding="utf-8",
        )
        (root / "artifact_transport.json").write_text(
            json.dumps({"transport_version": "2.0", "records": []}) + "\n",
            encoding="utf-8",
        )
        if case_id == "known-true-induction":
            trial_id = "D01"
            counting_state = "preflight"
        elif case_id == "return-envelope-positive-control":
            trial_id = "D02"
            counting_state = "preflight"
        else:
            case_number = next(
                index
                for index, value in enumerate(
                    (
                        json.loads(line)
                        for line in (
                            ROOT / "gpt" / "evals" / "GPT_EVAL_CASES.jsonl"
                        ).read_text(encoding="utf-8").splitlines()
                    ),
                    1,
                )
                if value["id"] == case_id
            )
            trial_id = f"C{case_number:03d}"
            counting_state = "counted"
        controller = build_controller_record(
            root=root,
            case_id=case_id,
            trial_id=trial_id,
            counting_state=counting_state,
            target_filename=target_name,
            output_filenames=[],
            output_control_filenames=[],
            session_reference=f"preview-conversation:{case_id}",
            observability_boundary="Visible Preview response and exposed files only.",
        )
        (root / "controller_record.json").write_bytes(
            canonical_json_bytes(controller)
        )

    def write_score_result(
        self,
        root: Path,
        *,
        dimension_overrides: dict[str, int] | None = None,
        total_override: int | None = None,
        automatic_failure: bool = False,
        observed_verdict: str | None = None,
        observed_projection_override: dict[str, str] | None = None,
        verdict_allowed_override: bool | None = None,
        projection_requirement_override: str | None = None,
        projection_contract_satisfied_override: bool | None = None,
        terminal_response_complete: bool = True,
    ) -> None:
        case = self.case()
        for filename in ("pre_score_controller.json", "score_result.json"):
            path = root / filename
            if path.exists():
                path.unlink()
        audit_return = json.loads(
            (root / "audit_return.json").read_text(encoding="utf-8")
        )
        self.write_controller_record(root, audit_return)
        pre_score_bytes = (root / "controller_record.json").read_bytes()
        (root / "pre_score_controller.json").write_bytes(pre_score_bytes)
        scores = {name: 2 for name in case["scoring_criteria"]}
        scores.update(dimension_overrides or {})
        allowed_verdict = case["expected"]["research_verdict_any_of"][0]
        observed_verdict = (
            allowed_verdict if observed_verdict is None else observed_verdict
        )
        projection = (
            {"$primary": observed_verdict}
            if observed_projection_override is None
            else observed_projection_override
        )
        projection_requirement = (
            case["expected"]["research_projection_requirement"]
            if projection_requirement_override is None
            else projection_requirement_override
        )
        verdict_allowed = (
            bool(projection)
            and all(
                verdict in case["expected"]["research_verdict_any_of"]
                for verdict in projection.values()
            )
        )
        if verdict_allowed_override is not None:
            verdict_allowed = verdict_allowed_override
        projection_contract_satisfied = verdict_allowed
        if projection_contract_satisfied_override is not None:
            projection_contract_satisfied = (
                projection_contract_satisfied_override
            )
        score = {
            "score_result_version": "2.0",
            "case_id": CASE_ID,
            "trial_id": TRIAL_ID,
            "pre_score_controller_sha256": sha256(pre_score_bytes),
            "dimension_scores": scores,
            "total_score": (
                sum(scores.values()) if total_override is None else total_override
            ),
            "automatic_failure": automatic_failure,
            "observable_behavior_results": {
                text: True for text in case["expected"]["observable_behaviors"]
            },
            "forbidden_behavior_results": {
                text: False for text in case["expected"]["forbidden_behaviors"]
            },
            "observed_research_projection": projection,
            "research_projection_requirement": projection_requirement,
            "research_verdict_allowed": verdict_allowed,
            "research_projection_contract_satisfied": (
                projection_contract_satisfied
            ),
            "terminal_response_complete": terminal_response_complete,
            "scorer": "manual-test-scorer",
            "notes": "Preserved exact rubric observations.",
        }
        (root / "score_result.json").write_bytes(canonical_json_bytes(score))
        self.write_controller_record(root, audit_return)

    def write_prose_score_result(
        self,
        root: Path,
        *,
        case_id: str,
        observed_projection: dict[str, str],
        verdict_allowed: bool | None,
        projection_requirement: str | None = None,
        projection_contract_satisfied: bool | None = None,
    ) -> None:
        case = self.case(case_id)
        controller = json.loads(
            (root / "controller_record.json").read_text(encoding="utf-8")
        )
        pre_score_bytes = (root / "controller_record.json").read_bytes()
        (root / "pre_score_controller.json").write_bytes(pre_score_bytes)
        requirement = (
            case["expected"]["research_projection_requirement"]
            if projection_requirement is None
            else projection_requirement
        )
        recomputed_contract = (
            observed_projection == {}
            if requirement == STATUS_ONLY_RESEARCH_PROJECTION_EMPTY
            else bool(observed_projection)
            and all(
                verdict in case["expected"].get("research_verdict_any_of", [])
                for verdict in observed_projection.values()
            )
        )
        score = {
            "score_result_version": "2.0",
            "case_id": case_id,
            "trial_id": controller["trial_id"],
            "pre_score_controller_sha256": sha256(pre_score_bytes),
            "dimension_scores": {
                name: 2 for name in case["scoring_criteria"]
            },
            "total_score": 20,
            "automatic_failure": False,
            "observable_behavior_results": {
                text: True for text in case["expected"]["observable_behaviors"]
            },
            "forbidden_behavior_results": {
                text: False for text in case["expected"]["forbidden_behaviors"]
            },
            "observed_research_projection": observed_projection,
            "research_projection_requirement": requirement,
            "research_verdict_allowed": verdict_allowed,
            "research_projection_contract_satisfied": (
                recomputed_contract
                if projection_contract_satisfied is None
                else projection_contract_satisfied
            ),
            "terminal_response_complete": True,
            "scorer": "manual-test-scorer",
            "notes": "Preserved exact status-only rubric observations.",
        }
        (root / "score_result.json").write_bytes(canonical_json_bytes(score))
        refreshed = build_controller_record(
            root=root,
            case_id=case_id,
            trial_id=controller["trial_id"],
            counting_state=controller["counting_state"],
            target_filename=next(
                item["filename"]
                for item in controller["inputs"]
                if item["kind"] == "target"
            ),
            output_filenames=[],
            output_control_filenames=controller["observed_output_controls"],
            session_reference=controller["fresh_conversation"][
                "session_reference"
            ],
            observability_boundary=controller["fresh_conversation"][
                "observability_boundary"
            ],
        )
        (root / "controller_record.json").write_bytes(
            canonical_json_bytes(refreshed)
        )

    def make_bundle(
        self,
        root: Path,
        *,
        visible: bool = True,
    ) -> tuple[dict, dict[str, str]]:
        record = json.loads(VALID_RETURN.read_text(encoding="utf-8"))
        report_record = next(
            artifact
            for artifact in record["artifacts"]
            if artifact["id"] == record["bindings"]["report_artifact_id"]
        )
        for artifact in record["artifacts"]:
            if artifact is report_record:
                continue
            shutil.copyfile(EXAMPLES / artifact["filename"], root / artifact["filename"])

        report = (
            "# Preserved audit report\n\n"
            "Execution ledger: see the bound execution-output artifact "
            f"`{BOUND_RUNTIME_ARTIFACT}`.\n"
        ).encode("utf-8")
        (root / "audit_report.md").write_bytes(report)
        report_record.update(
            filename="audit_report.md",
            media_type="text/markdown",
            sha256=f"sha256:{sha256(report)}",
        )
        analysis_output = runtime_ledger_text(
            PYTHON_VERSION,
            [output_record("audit_report.md", report)],
        ).encode("utf-8")
        (root / "chatgpt_data_analysis_output.txt").write_bytes(analysis_output)
        record["artifacts"].append(
            {
                "id": "artifact:data-analysis-output",
                "filename": "chatgpt_data_analysis_output.txt",
                "role": "execution_output",
                "media_type": "text/plain",
                "sha256": f"sha256:{sha256(analysis_output)}",
            }
        )
        analysis = next(
            item
            for item in record["execution"]
            if item["activity"] == "chatgpt_data_analysis"
        )
        analysis.update(
            status="ran",
            tool="Python",
            version=PYTHON_VERSION,
            input_artifact_ids=["artifact:request", "artifact:source"],
            output_artifact_ids=[
                "artifact:report",
                "artifact:data-analysis-output",
            ],
            receipt_ids=[],
            notes="Read, wrote, reread, and hashed the bound local files.",
        )
        self.write_return(root, record)
        self.write_wrapper(root, "audit_report.md", report)
        (root / "visible_response_dom.txt").write_text(
            "The generated files are available.\n",
            encoding="utf-8",
        )
        generated = sorted(
            {artifact["filename"] for artifact in record["artifacts"]}
            | {"audit_return.json"}
        )
        controls = "".join(
            f'<button aria-label="{html.escape(filename, quote=True)}"></button>'
            for filename in generated
        )
        (root / "raw" / "response.outerHTML.html").write_text(
            f"<article>The generated files are available.{controls}</article>\n",
            encoding="utf-8",
        )
        self.write_transport_record(root, record)

        target = ROOT / "gpt" / "evals" / "fixtures" / TARGET_NAME
        shutil.copyfile(target, root / TARGET_NAME)
        inputs = [byte_record("target", TARGET_NAME, target.read_bytes())]
        for filename in KNOWLEDGE_FILENAMES:
            source = ROOT / "gpt" / "knowledge" / filename
            shutil.copyfile(source, root / filename)
            inputs.append(byte_record("knowledge", filename, source.read_bytes()))

        canonical_copies = {
            "GPT_FROZEN_CANDIDATE.json": ROOT
            / "docs"
            / "GPT_FROZEN_CANDIDATE.json",
            "GPT_PROFILE.json": ROOT / "gpt" / "_source" / "GPT_PROFILE.json",
            "GPT_INSTRUCTIONS.md": ROOT / "gpt" / "GPT_INSTRUCTIONS.md",
            "GPT_EVAL_SPEC.json": ROOT / "gpt" / "_source" / "GPT_EVAL_SPEC.json",
        }
        expected: dict[str, str] = {}
        for filename, source in canonical_copies.items():
            data = source.read_bytes()
            (root / filename).write_bytes(data)
            expected[filename] = sha256(data)
        case = next(
            json.loads(line)
            for line in (ROOT / "gpt" / "evals" / "GPT_EVAL_CASES.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if json.loads(line)["id"] == CASE_ID
        )
        (root / "preview_prompt.txt").write_bytes(
            case["preview_prompt"].encode("utf-8")
        )
        self.write_controller_record(root, record, inputs)
        if not visible:
            (root / "visible_response_dom.txt").unlink()
        return record, expected

    def write_controller_record(
        self,
        root: Path,
        record: dict,
        inputs: list[dict] | None = None,
    ) -> None:
        excluded = {
            "controller_record.json",
            TARGET_NAME,
            *KNOWLEDGE_FILENAMES,
            *(filename for _, filename in CANDIDATE_IDENTITY_FILENAMES),
            *CONTROLLER_ARTIFACT_FILENAMES,
            *OPTIONAL_CONTROLLER_ARTIFACT_FILENAMES,
        }
        output_names = [
            path.name
            for path in root.iterdir()
            if path.is_file()
            and path.name not in excluded
            and ".export." not in path.name
        ]
        _, output_controls = _inspect_response_outer_html(
            (root / RAW_RESPONSE_FILENAME).read_bytes()
        )
        controller = build_controller_record(
            root=root,
            case_id=CASE_ID,
            trial_id=TRIAL_ID,
            counting_state="preflight",
            target_filename=TARGET_NAME,
            output_filenames=output_names,
            output_control_filenames=output_controls,
            session_reference="preview-conversation:test",
            observability_boundary=(
                "Authenticated editor Preview DOM and files exposed in this conversation only."
            ),
        )
        (root / "controller_record.json").write_bytes(
            canonical_json_bytes(controller)
        )

    def replace_runtime_ledger(self, root: Path, record: dict, data: bytes) -> None:
        path = root / BOUND_RUNTIME_ARTIFACT
        path.write_bytes(data)
        row = next(
            item
            for item in record["artifacts"]
            if item["filename"] == BOUND_RUNTIME_ARTIFACT
        )
        row["sha256"] = f"sha256:{sha256(data)}"
        self.write_return(root, record)
        self.write_transport_record(root, record)

    def replace_report(self, root: Path, record: dict, report: bytes) -> None:
        (root / "audit_report.md").write_bytes(report)
        report_row = next(
            item
            for item in record["artifacts"]
            if item["id"] == record["bindings"]["report_artifact_id"]
        )
        report_row["sha256"] = f"sha256:{sha256(report)}"
        analysis_output = runtime_ledger_text(
            PYTHON_VERSION,
            [output_record("audit_report.md", report)],
        ).encode("utf-8")
        (root / BOUND_RUNTIME_ARTIFACT).write_bytes(analysis_output)
        runtime_row = next(
            item
            for item in record["artifacts"]
            if item["filename"] == BOUND_RUNTIME_ARTIFACT
        )
        runtime_row["sha256"] = f"sha256:{sha256(analysis_output)}"
        self.write_return(root, record)
        self.write_wrapper(root, "audit_report.md", report)
        self.write_transport_record(root, record)

    def invoke(
        self,
        root: Path,
        expected: dict[str, str] | None = None,
        *,
        refresh_record: bool = True,
        case_id: str = CASE_ID,
    ) -> tuple[int, dict]:
        if refresh_record and (root / "controller_record.json").is_file():
            try:
                record = json.loads(
                    (root / "audit_return.json").read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError):
                pass
            else:
                self.write_controller_record(root, record)
        argv = [str(root), "--expect-case-id", case_id]
        if expected is not None:
            argv.extend(
                [
                    "--expect-profile-sha256",
                    expected["GPT_PROFILE.json"],
                    "--expect-instructions-sha256",
                    expected["GPT_INSTRUCTIONS.md"],
                    "--expect-eval-spec-sha256",
                    expected["GPT_EVAL_SPEC.json"],
                ]
            )
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(argv)
        return status, json.loads(output.getvalue())

    def finding_codes(self, payload: dict) -> set[str]:
        return {finding["code"] for finding in payload["findings"]}

    def test_valid_bundle_passes_all_requested_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, expected = self.make_bundle(root)
            status, payload = self.invoke(root, expected)

        self.assertEqual(status, 0)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["checks"]["audit_return_artifacts"]["status"], "pass")
        self.assertEqual(payload["checks"]["export_wrappers"]["status"], "pass")
        self.assertEqual(payload["checks"]["python_return_desk"]["status"], "pass")
        self.assertEqual(
            payload["checks"]["chatgpt_data_analysis_output"]["status"],
            "pass",
        )
        self.assertEqual(
            payload["checks"]["chatgpt_data_analysis_version"]["status"],
            "pass",
        )
        self.assertEqual(payload["checks"]["visible_response_version"]["status"], "pass")
        self.assertEqual(payload["outcomes"]["controller"], "controller_valid")
        self.assertEqual(payload["outcomes"]["candidate"], "not_scored")
        self.assertEqual(
            payload["outcomes"]["transport"],
            "transport_identity_unresolved",
        )
        self.assertEqual(
            payload["outcomes"]["disposition"],
            "candidate_not_scored",
        )
        self.assertIn(LIMITATION, payload["limitations"])
        self.assertIn("do not establish download-button identity", LIMITATION)

    def test_bound_artifact_change_reports_hash_and_report_transport_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            with (root / "audit_report.md").open("ab") as stream:
                stream.write(b"changed after binding\n")
            status, payload = self.invoke(root)

        self.assertEqual(status, 1)
        self.assertEqual(payload["status"], "blocked")
        self.assertIn(
            "ARTIFACT_TRANSPORT_BYTE_BINDING_MISMATCH",
            self.finding_codes(payload),
        )
        self.assertEqual(
            payload["outcomes"]["disposition"],
            "trial_invalid_controller",
        )

    def test_report_transport_mismatch_is_distinct_when_export_is_self_consistent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            transported = b"a different but internally self-consistent exported report\n"
            self.write_wrapper(root, "audit_report.md", transported)
            status, payload = self.invoke(root)

        self.assertEqual(status, 1)
        codes = self.finding_codes(payload)
        self.assertIn("REPORT_TRANSPORT_MISMATCH", codes)
        self.assertNotIn("EXPORT_PAYLOAD_IDENTITY_MISMATCH", codes)
        self.assertEqual(payload["outcomes"]["controller"], "controller_valid")
        self.assertEqual(payload["outcomes"]["candidate"], "candidate_failed")
        self.assertEqual(
            payload["outcomes"]["transport"],
            "transport_identity_unresolved",
        )

    def test_noncanonical_or_invalid_base64_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            path = root / "audit_report.md.export.00000.json"
            wrapper = json.loads(path.read_text(encoding="utf-8"))
            wrapper["base64"] += "*"
            mutated = compiler_transport_bytes(wrapper)
            self.write_wrapper_capture_bytes(root, "audit_report.md", mutated)
            status, payload = self.invoke(root)

        self.assertEqual(status, 1)
        codes = self.finding_codes(payload)
        self.assertIn("EXPORT_CHUNK_BASE64_INVALID", codes)
        self.assertEqual(payload["outcomes"]["controller"], "controller_valid")
        self.assertEqual(payload["outcomes"]["candidate"], "candidate_failed")

    def test_utf8_control_sanitation_includes_visible_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            (root / "visible_response_dom.txt").write_text(
                f"chatgpt_data_analysis Python {PYTHON_VERSION}\f\n",
                encoding="utf-8",
            )
            status, payload = self.invoke(root)

        self.assertEqual(status, 1)
        self.assertIn("TEXT_CONTROL_CHARACTER", self.finding_codes(payload))
        self.assertEqual(payload["checks"]["text_sanitation"]["status"], "blocked")

    def test_version_literal_must_match_return_report_and_visible_response(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            wrong = "3.11.8 (main, Mar 12 2024, 11:41:52) [GCC 12.2.0]"
            (root / "visible_response_dom.txt").write_text(
                f"chatgpt_data_analysis ran Python {wrong}\n",
                encoding="utf-8",
            )
            status, payload = self.invoke(root)

        self.assertEqual(status, 1)
        self.assertIn(
            "CHATGPT_DATA_ANALYSIS_VERSION_MISMATCH",
            self.finding_codes(payload),
        )
        self.assertEqual(
            payload["outcomes"]["transport"],
            "transport_identity_unresolved",
        )
        self.assertEqual(payload["outcomes"]["candidate"], "candidate_failed")
        self.assertEqual(payload["outcomes"]["disposition"], "candidate_failed")

    def test_matching_runtime_literal_in_model_prose_is_still_prohibited(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            (root / "visible_response_dom.txt").write_text(
                f"Runtime copied into model prose: {PYTHON_VERSION}\n",
                encoding="utf-8",
            )
            status, payload = self.invoke(root)

        self.assertEqual(status, 1)
        self.assertIn(
            "CHATGPT_DATA_ANALYSIS_RUNTIME_LITERAL_PROHIBITED",
            self.finding_codes(payload),
        )
        self.assertEqual(payload["outcomes"]["controller"], "controller_valid")
        self.assertEqual(payload["outcomes"]["candidate"], "candidate_failed")

    def test_reference_only_runtime_projection_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            status, payload = self.invoke(root)

        self.assertEqual(status, 0)
        self.assertNotIn(
            "CHATGPT_DATA_ANALYSIS_RUNTIME_LITERAL_PROHIBITED",
            self.finding_codes(payload),
        )
        self.assertEqual(
            payload["checks"]["chatgpt_data_analysis_version"]["status"],
            "pass",
        )

    def test_runtime_literal_in_return_notes_fails_after_full_rebinding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record, _ = self.make_bundle(root)
            analysis = next(
                item
                for item in record["execution"]
                if item["activity"] == "chatgpt_data_analysis"
            )
            analysis["notes"] = f"Model-authored runtime copy: {PYTHON_VERSION}"
            self.write_return(root, record)
            self.write_transport_record(root, record)
            status, payload = self.invoke(root)

        self.assertEqual(status, 1)
        self.assertIn(
            "CHATGPT_DATA_ANALYSIS_RUNTIME_LITERAL_PROHIBITED",
            self.finding_codes(payload),
        )
        self.assertEqual(payload["outcomes"]["controller"], "controller_valid")
        self.assertEqual(payload["outcomes"]["candidate"], "candidate_failed")

    def test_runtime_literal_in_raw_outer_html_fails_after_full_rebinding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            encoded_runtime = PYTHON_VERSION.replace("[", "&#91;").replace(
                "]",
                "&#93;",
            )
            (root / "raw" / "response.outerHTML.html").write_text(
                f"<article>Model runtime copy: {encoded_runtime}</article>\n",
                encoding="utf-8",
            )
            status, payload = self.invoke(root)

        self.assertEqual(status, 1)
        self.assertIn(
            "CHATGPT_DATA_ANALYSIS_RUNTIME_LITERAL_PROHIBITED",
            self.finding_codes(payload),
        )
        self.assertEqual(payload["outcomes"]["controller"], "controller_valid")
        self.assertEqual(payload["outcomes"]["candidate"], "candidate_failed")

    def test_runtime_literal_in_generated_evidence_fails_after_full_rebinding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record, _ = self.make_bundle(root)
            evidence = next(
                item
                for item in record["artifacts"]
                if item.get("role") not in {"request", "source", "report", "execution_output"}
            )
            evidence_bytes = (
                f"Generated evidence copied the runtime: {PYTHON_VERSION}\n"
            ).encode("utf-8")
            (root / evidence["filename"]).write_bytes(evidence_bytes)
            evidence["sha256"] = f"sha256:{sha256(evidence_bytes)}"
            self.write_return(root, record)
            self.write_transport_record(root, record)
            status, payload = self.invoke(root)

        self.assertEqual(status, 1)
        self.assertIn(
            "CHATGPT_DATA_ANALYSIS_RUNTIME_LITERAL_PROHIBITED",
            self.finding_codes(payload),
        )
        self.assertEqual(payload["outcomes"]["controller"], "controller_valid")
        self.assertEqual(payload["outcomes"]["candidate"], "candidate_failed")

    def test_data_analysis_output_must_be_bound_and_list_other_output_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record, _ = self.make_bundle(root)
            analysis = next(
                item
                for item in record["execution"]
                if item["activity"] == "chatgpt_data_analysis"
            )
            analysis["output_artifact_ids"] = ["artifact:report"]
            self.write_return(root, record)
            self.write_transport_record(root, record)
            status, payload = self.invoke(root)

        self.assertEqual(status, 1)
        self.assertIn(
            "CHATGPT_DATA_ANALYSIS_OUTPUT_BINDING_MISSING",
            self.finding_codes(payload),
        )

    def test_data_analysis_output_hash_ledger_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record, _ = self.make_bundle(root)
            output_record = next(
                item
                for item in record["artifacts"]
                if item["id"] == "artifact:data-analysis-output"
            )
            bad_output = (
                "ChatGPT Data Analysis output\n"
                f"sys.version: {PYTHON_VERSION}\n"
                "audit_report.md sha256:"
                f"{'0' * 64}\n"
            ).encode("utf-8")
            (root / output_record["filename"]).write_bytes(bad_output)
            output_record["sha256"] = f"sha256:{sha256(bad_output)}"
            self.write_return(root, record)
            self.write_transport_record(root, record)
            status, payload = self.invoke(root)

        self.assertEqual(status, 1)
        self.assertIn(
            "CHATGPT_DATA_ANALYSIS_RUNTIME_BINDING_INVALID",
            self.finding_codes(payload),
        )

    def test_runtime_ledger_exact_roster_rejects_size_name_and_extra_row(self):
        for label in ("forged_size", "forged_name", "extra_row"):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                record, _ = self.make_bundle(root)
                lines = (root / BOUND_RUNTIME_ARTIFACT).read_text(
                    encoding="utf-8"
                ).splitlines()
                digest_text, size_text, filename = lines[4].split("  ", 2)
                if label == "forged_size":
                    lines[4] = (
                        f"{digest_text}  {int(size_text) + 1}  {filename}"
                    )
                elif label == "forged_name":
                    lines[4] = f"{digest_text}  {size_text}  forged.txt"
                else:
                    lines.append(f"{'0' * 64}  0  z-extra.txt")
                mutation = "\n".join(lines) + "\n"
                self.replace_runtime_ledger(root, record, mutation.encode("utf-8"))
                status, payload = self.invoke(root)
                self.assertEqual(status, 1)
                self.assertIn(
                    "CHATGPT_DATA_ANALYSIS_OUTPUT_LEDGER_ROSTER_MISMATCH",
                    self.finding_codes(payload),
                )

    def test_raw_outer_html_capture_is_required_and_distinct_from_visible_text(self):
        for mutation in ("missing", "changed"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_bundle(root)
                raw_path = root / "raw" / "response.outerHTML.html"
                if mutation == "missing":
                    raw_path.unlink()
                else:
                    raw_path.write_bytes(
                        raw_path.read_bytes() + b"<p>post-capture mutation</p>\n"
                    )
                status, payload = self.invoke(root, refresh_record=False)
                self.assertEqual(status, 1)
                self.assertIn(
                    (
                        "CONTROLLER_RAW_RESPONSE_INVALID"
                        if mutation == "missing"
                        else "CONTROLLER_FILE_BINDING_MISMATCH"
                    ),
                    self.finding_codes(payload),
                )
                self.assertEqual(
                    payload["outcomes"]["disposition"],
                    "trial_invalid_controller",
                )

    def test_rebound_score_cannot_mutate_the_pre_score_controller(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            self.write_score_result(root)
            pre_path = root / "pre_score_controller.json"
            pre = json.loads(pre_path.read_text(encoding="utf-8"))
            pre["fresh_conversation"]["session_reference"] = "mutated-after-score"
            pre_bytes = canonical_json_bytes(pre)
            pre_path.write_bytes(pre_bytes)
            score_path = root / "score_result.json"
            score = json.loads(score_path.read_text(encoding="utf-8"))
            score["pre_score_controller_sha256"] = sha256(pre_bytes)
            score_path.write_bytes(canonical_json_bytes(score))
            record = json.loads(
                (root / "audit_return.json").read_text(encoding="utf-8")
            )
            self.write_controller_record(root, record)
            status, payload = self.invoke(root, refresh_record=False)

        self.assertEqual(status, 1)
        self.assertIn(
            "CONTROLLER_SCORE_RESULT_INVALID",
            self.finding_codes(payload),
        )
        self.assertEqual(
            payload["outcomes"]["disposition"],
            "trial_invalid_controller",
        )

    def test_transport_coverage_uses_actual_outputs_without_audit_return(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_prose_only_bundle(root)
            (root / "independently.txt").write_text(
                "independently observed output\n",
                encoding="utf-8",
            )
            controller = build_controller_record(
                root=root,
                case_id=CASE_ID,
                trial_id=TRIAL_ID,
                counting_state="preflight",
                target_filename=TARGET_NAME,
                output_filenames=["independently.txt"],
                output_control_filenames=[],
                session_reference="preview-conversation:transport-coverage",
                observability_boundary="Visible Preview response and exposed files only.",
            )
            (root / "controller_record.json").write_bytes(
                canonical_json_bytes(controller)
            )
            status, payload = self.invoke(root, refresh_record=False)

        self.assertEqual(status, 1)
        self.assertIn(
            "ARTIFACT_TRANSPORT_COVERAGE_MISSING",
            self.finding_codes(payload),
        )
        self.assertEqual(
            payload["outcomes"]["disposition"],
            "trial_invalid_controller",
        )

    def test_nested_or_hidden_raw_evidence_invalidates_controller(self):
        for mutation in ("nested_output", "hidden_raw"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_bundle(root)
                if mutation == "nested_output":
                    nested = root / "nested"
                    nested.mkdir()
                    (nested / "independently.txt").write_text(
                        "hidden nested output\n",
                        encoding="utf-8",
                    )
                else:
                    (root / "raw" / "hidden.txt").write_text(
                        "unbound raw capture\n",
                        encoding="utf-8",
                    )
                status, payload = self.invoke(root, refresh_record=False)
                self.assertEqual(status, 1)
                self.assertIn(
                    "CONTROLLER_EVIDENCE_LAYOUT_INVALID",
                    self.finding_codes(payload),
                )
                self.assertEqual(
                    payload["outcomes"]["disposition"],
                    "trial_invalid_controller",
                )

    def test_symlinked_evidence_entry_invalidates_controller_when_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            link = root / "linked-output.txt"
            try:
                link.symlink_to(root / TARGET_NAME)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")
            status, payload = self.invoke(root, refresh_record=False)

        self.assertEqual(status, 1)
        self.assertIn(
            "CONTROLLER_EVIDENCE_LAYOUT_INVALID",
            self.finding_codes(payload),
        )
        self.assertEqual(
            payload["outcomes"]["disposition"],
            "trial_invalid_controller",
        )

    def test_visible_response_is_required_for_frozen_evaluation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root, visible=False)
            status, payload = self.invoke(root, refresh_record=False)

        self.assertEqual(status, 1)
        self.assertIn(
            "CONTROLLER_ARTIFACT_REQUIRED_MISSING",
            self.finding_codes(payload),
        )
        self.assertEqual(
            payload["outcomes"]["disposition"],
            "trial_invalid_controller",
        )
        self.assertFalse(payload["outcomes"]["scoring_allowed"])
        self.assertEqual(payload["checks"]["python_return_desk"]["status"], "not_run")

    def test_truncated_report_export_is_distinguished_and_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            path = root / "audit_report.md.export.00000.json"
            wrapper = json.loads(path.read_text(encoding="utf-8"))
            wrapper["base64"] = wrapper["base64"][:-4]
            mutated = compiler_transport_bytes(wrapper)
            self.write_wrapper_capture_bytes(root, "audit_report.md", mutated)
            status, payload = self.invoke(root)

        self.assertEqual(status, 1)
        codes = self.finding_codes(payload)
        self.assertIn("EXPORT_CHUNK_BYTE_BINDING_MISMATCH", codes)
        self.assertIn("EXPORT_ENCODED_AGGREGATE_MISMATCH", codes)
        self.assertEqual(payload["outcomes"]["controller"], "controller_valid")
        self.assertEqual(payload["outcomes"]["candidate"], "candidate_failed")
        self.assertEqual(payload["outcomes"]["disposition"], "candidate_failed")

    def test_aligned_base64_quartet_parser_omission_invalidates_controller(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            payload_bytes = b"Xindependently"
            wrapper = self.wrapper("audit_report.md", payload_bytes)
            encoded = wrapper["base64"]
            self.assertGreaterEqual(len(encoded), 8)
            wrapper_with_omission = dict(wrapper)
            wrapper_with_omission["base64"] = encoded[:4] + encoded[8:]
            raw = compiler_transport_bytes(wrapper)
            self.assertIn(b"independently", payload_bytes)
            parser_input = compiler_transport_bytes(wrapper_with_omission)
            self.assertNotEqual(raw, parser_input)
            self.write_wrapper_capture_bytes(root, "audit_report.md", raw)
            (root / "audit_report.md.export.00000.json").write_bytes(parser_input)
            status, result = self.invoke(root, refresh_record=False)

        self.assertEqual(status, 1)
        self.assertTrue(
            {
                "CONTROLLER_PARSER_ROUND_TRIP_MISMATCH",
                "CONTROLLER_TRANSPORT_CAPTURE_INVALID",
            }
            & self.finding_codes(result)
        )
        self.assertEqual(
            result["outcomes"],
            {
                "controller": "trial_invalid_controller",
                "candidate": "not_scored",
                "transport": "not_applicable",
                "disposition": "trial_invalid_controller",
                "scoring_allowed": False,
            },
        )
        self.assertEqual(result["checks"]["python_return_desk"]["status"], "not_run")

    def test_aligned_base64_omission_from_preserved_wrapper_is_candidate_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            payload_bytes = b"Xindependently"
            wrapper = self.wrapper("audit_report.md", payload_bytes)
            encoded = wrapper["base64"]
            self.assertGreaterEqual(len(encoded), 8)
            wrapper["base64"] = encoded[:4] + encoded[8:]
            self.assertIn(b"independently", payload_bytes)
            self_consistent_capture = compiler_transport_bytes(wrapper)
            self.write_wrapper_capture_bytes(
                root,
                "audit_report.md",
                self_consistent_capture,
            )
            status, result = self.invoke(root)

        self.assertEqual(status, 1)
        codes = self.finding_codes(result)
        self.assertNotIn("CONTROLLER_PARSER_ROUND_TRIP_MISMATCH", codes)
        self.assertIn("EXPORT_CHUNK_BYTE_BINDING_MISMATCH", codes)
        self.assertIn("EXPORT_ENCODED_AGGREGATE_MISMATCH", codes)
        self.assertEqual(result["outcomes"]["controller"], "controller_valid")
        self.assertEqual(result["outcomes"]["candidate"], "candidate_failed")
        self.assertEqual(result["outcomes"]["disposition"], "candidate_failed")

    def test_aggregate_identity_and_decompression_contradictions_fail_candidate(self):
        for mutation in ("aggregate_hash", "zlib_stream"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_bundle(root)
                path = root / "audit_report.md.export.00000.json"
                wrapper = json.loads(path.read_text(encoding="utf-8"))
                if mutation == "aggregate_hash":
                    wrapper["encoded_sha256"] = "0" * 64
                    expected_code = "EXPORT_ENCODED_AGGREGATE_MISMATCH"
                else:
                    encoded = b"not-one-zlib-stream"
                    wrapper["base64"] = base64.b64encode(encoded).decode("ascii")
                    wrapper["chunk_size_bytes"] = len(encoded)
                    wrapper["chunk_sha256"] = sha256(encoded)
                    wrapper["encoded_size_bytes"] = len(encoded)
                    wrapper["encoded_sha256"] = sha256(encoded)
                    expected_code = "EXPORT_ZLIB_STREAM_INVALID"
                self.write_wrapper_capture_bytes(
                    root,
                    "audit_report.md",
                    compiler_transport_bytes(wrapper),
                )
                status, payload = self.invoke(root)

            self.assertEqual(status, 1)
            self.assertEqual(payload["outcomes"]["controller"], "controller_valid")
            self.assertEqual(payload["outcomes"]["candidate"], "candidate_failed")
            self.assertIn(expected_code, self.finding_codes(payload))

    def test_transport_prompt_and_response_provenance_defects_invalidate_trial(self):
        mutations = {
            "prompt_drift": lambda root: (
                root / "raw" / "audit_report.md.transport.00000.prompt.txt"
            ).write_bytes(b"model-authored substitute prompt"),
            "zero_code_blocks": lambda root: (
                root / "raw" / "audit_report.md.transport.00000.outerHTML.html"
            ).write_text("<article>no code</article>", encoding="utf-8"),
            "multiple_code_blocks": lambda root: (
                root / "raw" / "audit_report.md.transport.00000.outerHTML.html"
            ).write_text(
                "<article><code>{}</code><code>{}</code></article>",
                encoding="utf-8",
            ),
            "code_text_drift": lambda root: (
                root / "raw" / "audit_report.md.transport.00000.outerHTML.html"
            ).write_text(
                "<article><code>{\"filename\":\"different.txt\"}</code></article>",
                encoding="utf-8",
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    self.make_bundle(root)
                    mutate(root)
                    status, result = self.invoke(root, refresh_record=False)
                self.assertEqual(status, 1)
                self.assertEqual(
                    result["outcomes"]["controller"],
                    "trial_invalid_controller",
                )
                self.assertEqual(result["outcomes"]["candidate"], "not_scored")
                self.assertFalse(result["outcomes"]["scoring_allowed"])
                self.assertEqual(
                    result["checks"]["python_return_desk"]["status"],
                    "not_run",
                )
                codes = self.finding_codes(result)
                self.assertTrue(
                    {
                        "CONTROLLER_TRANSPORT_PROMPT_MISMATCH",
                        "CONTROLLER_TRANSPORT_RESPONSE_INVALID",
                        "CONTROLLER_TRANSPORT_PROVENANCE_MISMATCH",
                        "CONTROLLER_TRANSPORT_CAPTURE_INVALID",
                        "CONTROLLER_FILE_BINDING_MISMATCH",
                    }
                    & codes,
                    codes,
                )

    def test_incomplete_canonical_input_roster_invalidates_before_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            controller_path = root / "controller_record.json"
            controller = json.loads(controller_path.read_text(encoding="utf-8"))
            self.assertEqual(len(controller["inputs"]), 7)
            controller["inputs"] = controller["inputs"][:-1]
            controller_path.write_text(
                json.dumps(controller, indent=2) + "\n",
                encoding="utf-8",
            )
            status, result = self.invoke(root, refresh_record=False)

        self.assertEqual(status, 1)
        self.assertIn(
            "CONTROLLER_INPUT_ROSTER_MISMATCH",
            self.finding_codes(result),
        )
        self.assertEqual(
            result["outcomes"]["disposition"],
            "trial_invalid_controller",
        )
        self.assertEqual(result["checks"]["python_return_desk"]["status"], "not_run")

    def test_stale_wrapper_without_local_payload_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            stale = b"stale transport payload\n"
            self.write_wrapper(root, "stale.txt", stale)
            status, payload = self.invoke(root, refresh_record=False)

        self.assertEqual(status, 1)
        self.assertEqual(
            payload["outcomes"]["controller"],
            "trial_invalid_controller",
        )
        self.assertEqual(payload["outcomes"]["candidate"], "not_scored")

    def test_transport_record_is_required_and_base64_is_fallback_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            transport_path = root / "artifact_transport.json"
            transport = json.loads(transport_path.read_text(encoding="utf-8"))
            report = next(
                item
                for item in transport["records"]
                if item["filename"] == "audit_report.md"
            )
            report["method"] = "direct_download"
            report["direct_download_outcome"] = "download_event"
            transport_path.write_text(json.dumps(transport), encoding="utf-8")
            status, payload = self.invoke(root)
            transport_path.unlink()
            missing_status, missing_payload = self.invoke(
                root,
                refresh_record=False,
            )

        self.assertEqual(status, 1)
        self.assertIn(
            "ARTIFACT_TRANSPORT_METHOD_INVALID",
            self.finding_codes(payload),
        )
        self.assertEqual(missing_status, 1)
        self.assertIn(
            "ARTIFACT_TRANSPORT_RECORD_MISSING",
            self.finding_codes(missing_payload),
        )

    def test_missing_reordered_and_duplicate_chunk_rosters_invalidate_controller(self):
        for mutation in ("missing", "reordered", "duplicate"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                record, _ = self.make_bundle(root)
                large_report = (
                    b"# independently captured report\n\n"
                    b"Execution ledger: see the bound execution-output artifact "
                    + f"`{BOUND_RUNTIME_ARTIFACT}`.\n".encode("utf-8")
                    + b"\n".join(
                        hashlib.sha256(str(index).encode("ascii")).hexdigest().encode("ascii")
                        for index in range(1000)
                    )
                    + b"\n"
                )
                self.replace_report(root, record, large_report)
                transport_path = root / "artifact_transport.json"
                transport = json.loads(transport_path.read_text(encoding="utf-8"))
                report_row = next(
                    item
                    for item in transport["records"]
                    if item["filename"] == "audit_report.md"
                )
                chunks = list(report_row["export_chunks"])
                self.assertGreater(len(chunks), 2)
                if mutation == "missing":
                    report_row["export_chunks"] = chunks[:-1]
                elif mutation == "reordered":
                    report_row["export_chunks"] = [
                        chunks[1],
                        chunks[0],
                        *chunks[2:],
                    ]
                else:
                    report_row["export_chunks"] = [
                        chunks[0],
                        chunks[0],
                        *chunks[2:],
                    ]
                transport_path.write_bytes(canonical_json_bytes(transport))
                self.write_controller_record(root, record)
                status, payload = self.invoke(root, refresh_record=False)

            self.assertEqual(status, 1)
            self.assertEqual(
                payload["outcomes"]["controller"],
                "trial_invalid_controller",
            )
            self.assertEqual(payload["outcomes"]["candidate"], "not_scored")
            self.assertTrue(
                {
                    "ARTIFACT_TRANSPORT_METHOD_INVALID",
                    "ARTIFACT_TRANSPORT_CHUNK_ROSTER_MISMATCH",
                }
                & self.finding_codes(payload)
            )

    def test_chunk_offset_and_repeated_identity_contradictions_fail_candidate(self):
        for mutation in ("offset", "repeated_identity"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                record, _ = self.make_bundle(root)
                large_report = (
                    b"# independently captured report\n\n"
                    b"Execution ledger: see the bound execution-output artifact "
                    + f"`{BOUND_RUNTIME_ARTIFACT}`.\n".encode("utf-8")
                    + b"\n".join(
                        hashlib.sha256(f"chunk-{index}".encode("ascii"))
                        .hexdigest()
                        .encode("ascii")
                        for index in range(1000)
                    )
                    + b"\n"
                )
                self.replace_report(root, record, large_report)
                first_path = root / "audit_report.md.export.00000.json"
                first = json.loads(first_path.read_text(encoding="utf-8"))
                last_index = first["chunk_count"] - 1
                self.assertGreater(last_index, 0)
                later_path = (
                    root
                    / f"audit_report.md.export.{last_index:05d}.json"
                )
                later = json.loads(later_path.read_text(encoding="utf-8"))
                if mutation == "offset":
                    later["offset_bytes"] += 1
                else:
                    later["payload_sha256"] = "0" * 64
                self.write_wrapper_capture_bytes(
                    root,
                    "audit_report.md",
                    compiler_transport_bytes(later),
                    chunk_index=last_index,
                    expected_payload_sha256=first["payload_sha256"],
                    expected_encoded_sha256=first["encoded_sha256"],
                )
                status, payload = self.invoke(root)

            self.assertEqual(status, 1)
            self.assertEqual(payload["outcomes"]["controller"], "controller_valid")
            self.assertEqual(payload["outcomes"]["candidate"], "candidate_failed")
            expected_code = (
                "EXPORT_CHUNK_METADATA_INVALID"
                if mutation == "offset"
                else "EXPORT_CHUNK_REPEATED_IDENTITY_MISMATCH"
            )
            self.assertIn(expected_code, self.finding_codes(payload))

    def test_expected_copy_hash_mismatch_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, expected = self.make_bundle(root)
            expected["GPT_PROFILE.json"] = "0" * 64
            status, payload = self.invoke(root, expected)

        self.assertEqual(status, 1)
        self.assertIn("EXPECTED_COPY_HASH_MISMATCH", self.finding_codes(payload))
        self.assertEqual(payload["checks"]["expected_profile_hash"]["status"], "blocked")

    def test_python_return_desk_block_is_propagated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record, _ = self.make_bundle(root)
            record["protocol"]["sha256"] = "sha256:" + "0" * 64
            self.write_return(root, record)
            self.write_transport_record(root, record)
            status, payload = self.invoke(root)

        self.assertEqual(status, 1)
        self.assertIn("RETURN_DESK_BLOCKED", self.finding_codes(payload))
        self.assertEqual(payload["checks"]["python_return_desk"]["status"], "blocked")
        return_codes = {
            finding["code"]
            for finding in payload["return_desk"]["findings"]
        }
        self.assertIn("RETURN_PROTOCOL_HASH_MISMATCH", return_codes)

    def test_valid_bundle_without_manual_score_remains_not_scored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            status, payload = self.invoke(root)

        self.assertEqual(status, 0)
        self.assertEqual(payload["outcomes"]["candidate"], "not_scored")
        self.assertEqual(payload["outcomes"]["disposition"], "candidate_not_scored")
        self.assertTrue(payload["outcomes"]["scoring_allowed"])

    def test_exact_ten_dimension_score_can_pass_candidate_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            self.write_score_result(root)
            status, payload = self.invoke(root)

        self.assertEqual(status, 0)
        self.assertEqual(payload["outcomes"]["candidate"], "candidate_passed")
        self.assertEqual(payload["score_result"]["total_score"], 20)
        self.assertEqual(len(payload["score_result"]["dimension_scores"]), 10)

    def test_score_total_is_recomputed_and_mismatch_invalidates_controller(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            self.write_score_result(root, total_override=19)
            status, payload = self.invoke(root, refresh_record=False)

        self.assertEqual(status, 1)
        self.assertIn(
            "CONTROLLER_SCORE_RESULT_INVALID",
            self.finding_codes(payload),
        )
        self.assertEqual(
            payload["outcomes"]["disposition"],
            "trial_invalid_controller",
        )

    def test_below_threshold_score_is_candidate_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            criteria = self.case()["scoring_criteria"]
            self.write_score_result(
                root,
                dimension_overrides={criteria[0]: 0, criteria[1]: 1},
            )
            status, payload = self.invoke(root)

        self.assertEqual(status, 1)
        self.assertIn("CANDIDATE_SCORE_GATE_FAILED", self.finding_codes(payload))
        self.assertEqual(payload["outcomes"]["candidate"], "candidate_failed")

    def test_disallowed_verdict_or_incomplete_terminal_response_fails_score(self):
        for arguments in (
            {"observed_verdict": "ill_posed"},
            {"terminal_response_complete": False},
        ):
            with self.subTest(arguments=arguments):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    self.make_bundle(root)
                    self.write_score_result(root, **arguments)
                    status, payload = self.invoke(root)
                self.assertEqual(status, 1)
                self.assertEqual(
                    payload["outcomes"]["candidate"],
                    "candidate_failed",
                )
                self.assertIn(
                    "CANDIDATE_SCORE_GATE_FAILED",
                    self.finding_codes(payload),
                )

    def test_forged_verdict_allowed_flag_invalidates_score_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            self.write_score_result(
                root,
                observed_verdict="ill_posed",
                verdict_allowed_override=True,
            )
            status, payload = self.invoke(root, refresh_record=False)

        self.assertEqual(status, 1)
        self.assertIn(
            "CONTROLLER_SCORE_RESULT_INVALID",
            self.finding_codes(payload),
        )
        self.assertEqual(
            payload["outcomes"]["disposition"],
            "trial_invalid_controller",
        )

    def test_scientific_empty_projection_is_candidate_failure_not_controller_escape(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            self.write_score_result(
                root,
                observed_projection_override={},
                verdict_allowed_override=False,
                projection_contract_satisfied_override=False,
            )
            status, payload = self.invoke(root)

        self.assertEqual(status, 1)
        self.assertEqual(payload["outcomes"]["controller"], "controller_valid")
        self.assertEqual(payload["outcomes"]["candidate"], "candidate_failed")
        self.assertIn("CANDIDATE_SCORE_GATE_FAILED", self.finding_codes(payload))

    def test_scientific_empty_projection_with_forged_contract_invalidates_controller(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            self.write_score_result(
                root,
                observed_projection_override={},
                verdict_allowed_override=False,
                projection_contract_satisfied_override=True,
            )
            status, payload = self.invoke(root, refresh_record=False)

        self.assertEqual(status, 1)
        self.assertEqual(
            payload["outcomes"]["disposition"],
            "trial_invalid_controller",
        )
        self.assertIn(
            "CONTROLLER_SCORE_RESULT_INVALID",
            self.finding_codes(payload),
        )

    def test_status_only_cases_pass_only_with_empty_projection(self):
        for case_id in (
            "official-service-status-separation",
            "official-first-reproduction-route",
        ):
            with self.subTest(case_id=case_id):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    self.make_prose_only_bundle(root, case_id=case_id)
                    pre_status, pre_payload = self.invoke(root, case_id=case_id)
                    self.write_prose_score_result(
                        root,
                        case_id=case_id,
                        observed_projection={},
                        verdict_allowed=None,
                    )
                    status, payload = self.invoke(
                        root,
                        refresh_record=False,
                        case_id=case_id,
                    )

                self.assertEqual(pre_status, 0)
                self.assertEqual(
                    pre_payload["outcomes"]["controller"],
                    "controller_valid",
                )
                self.assertEqual(status, 0)
                self.assertEqual(
                    payload["outcomes"]["candidate"],
                    "candidate_passed",
                )
                self.assertEqual(
                    payload["score_result"]["research_projection_requirement"],
                    STATUS_ONLY_RESEARCH_PROJECTION_EMPTY,
                )
                self.assertEqual(
                    payload["score_result"]["observed_research_projection"],
                    {},
                )
                self.assertIsNone(
                    payload["score_result"]["research_verdict_allowed"]
                )
                self.assertTrue(
                    payload["score_result"][
                        "research_projection_contract_satisfied"
                    ]
                )

    def test_status_only_scientific_projection_is_candidate_failure(self):
        case_id = "official-service-status-separation"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_prose_only_bundle(root, case_id=case_id)
            self.write_prose_score_result(
                root,
                case_id=case_id,
                observed_projection={"T": "plausible_but_unresolved"},
                verdict_allowed=None,
                projection_contract_satisfied=False,
            )
            status, payload = self.invoke(
                root,
                refresh_record=False,
                case_id=case_id,
            )

        self.assertEqual(status, 1)
        self.assertEqual(payload["outcomes"]["controller"], "controller_valid")
        self.assertEqual(payload["outcomes"]["candidate"], "candidate_failed")
        self.assertIn("CANDIDATE_SCORE_GATE_FAILED", self.finding_codes(payload))

    def test_status_only_forged_score_fields_invalidate_controller(self):
        case_id = "official-service-status-separation"
        for arguments in (
            {
                "observed_projection": {},
                "verdict_allowed": True,
            },
            {
                "observed_projection": {},
                "verdict_allowed": None,
                "projection_requirement": (
                    SCIENTIFIC_RESEARCH_PROJECTION_REQUIRED
                ),
                "projection_contract_satisfied": False,
            },
            {
                "observed_projection": {"T": "plausible_but_unresolved"},
                "verdict_allowed": None,
                "projection_contract_satisfied": True,
            },
        ):
            with self.subTest(arguments=arguments):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    self.make_prose_only_bundle(root, case_id=case_id)
                    self.write_prose_score_result(
                        root,
                        case_id=case_id,
                        **arguments,
                    )
                    status, payload = self.invoke(
                        root,
                        refresh_record=False,
                        case_id=case_id,
                    )
                self.assertEqual(status, 1)
                self.assertEqual(
                    payload["outcomes"]["disposition"],
                    "trial_invalid_controller",
                )
                self.assertIn(
                    "CONTROLLER_SCORE_RESULT_INVALID",
                    self.finding_codes(payload),
                )

    def test_exact_research_projection_mismatch_is_candidate_failure(self):
        case_id = "decisive-calculation-not-executed"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_prose_only_bundle(root, case_id=case_id)
            self.write_prose_score_result(
                root,
                case_id=case_id,
                observed_projection={"U": "plausible_but_unresolved"},
                verdict_allowed=True,
                projection_contract_satisfied=False,
            )
            status, payload = self.invoke(
                root,
                refresh_record=False,
                case_id=case_id,
            )

        self.assertEqual(status, 1)
        self.assertEqual(payload["outcomes"]["controller"], "controller_valid")
        self.assertEqual(payload["outcomes"]["candidate"], "candidate_failed")
        self.assertTrue(
            payload["score_result"]["research_projection_exact_required"]
        )

    def test_exact_research_projection_can_pass(self):
        case_id = "decisive-calculation-not-executed"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_prose_only_bundle(root, case_id=case_id)
            self.write_prose_score_result(
                root,
                case_id=case_id,
                observed_projection={"T": "plausible_but_unresolved"},
                verdict_allowed=True,
                projection_contract_satisfied=True,
            )
            status, payload = self.invoke(
                root,
                refresh_record=False,
                case_id=case_id,
            )

        self.assertEqual(status, 0)
        self.assertEqual(payload["outcomes"]["controller"], "controller_valid")
        self.assertEqual(payload["outcomes"]["candidate"], "candidate_passed")
        self.assertTrue(
            payload["score_result"]["research_projection_exact_required"]
        )

    def test_prose_only_case_accepts_independently_captured_zero_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_prose_only_bundle(root)
            status, payload = self.invoke(root)

        self.assertEqual(status, 0)
        self.assertEqual(payload["outcomes"]["controller"], "controller_valid")
        self.assertEqual(payload["outcomes"]["candidate"], "not_scored")
        self.assertEqual(payload["outcomes"]["transport"], "not_applicable")
        self.assertEqual(payload["checks"]["python_return_desk"]["status"], "not_run")

    def test_required_return_omission_is_candidate_failure_not_invalid_controller(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            case_id = "return-envelope-positive-control"
            self.make_prose_only_bundle(root, case_id=case_id)
            output = io.StringIO()
            with redirect_stdout(output):
                status = main([str(root), "--expect-case-id", case_id])
            payload = json.loads(output.getvalue())

        self.assertEqual(status, 1)
        self.assertEqual(payload["outcomes"]["controller"], "controller_valid")
        self.assertEqual(payload["outcomes"]["candidate"], "candidate_failed")
        self.assertIn(
            "CANDIDATE_REQUIRED_OUTPUT_MISSING",
            self.finding_codes(payload),
        )

    def test_visible_required_controls_with_unacquired_bytes_are_unresolved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            case_id = "return-envelope-positive-control"
            self.make_prose_only_bundle(root, case_id=case_id)
            controls = (
                '<button aria-label="audit_report.md"></button>'
                '<button aria-label="audit_return.json"></button>'
            )
            (root / "raw" / "response.outerHTML.html").write_text(
                f"<article>Generated files.{controls}</article>\n",
                encoding="utf-8",
            )
            self.write_failed_transport_attempt(root, "audit_report.md")
            self.write_failed_transport_attempt(root, "audit_return.json")
            controller = build_controller_record(
                root=root,
                case_id=case_id,
                trial_id="D02",
                counting_state="preflight",
                target_filename=self.case(case_id)["fixture_paths"][0].split("/")[-1],
                output_filenames=[],
                output_control_filenames=[
                    "audit_report.md",
                    "audit_return.json",
                ],
                session_reference="preview-conversation:visible-unacquired",
                observability_boundary="Visible Preview response and exposed files only.",
            )
            (root / "controller_record.json").write_bytes(
                canonical_json_bytes(controller)
            )
            status, payload = self.invoke(
                root,
                refresh_record=False,
                case_id=case_id,
            )

        self.assertEqual(status, 1)
        codes = self.finding_codes(payload)
        self.assertNotIn("CANDIDATE_REQUIRED_OUTPUT_MISSING", codes)
        self.assertFalse(any("CORRUPT" in code for code in codes))
        self.assertEqual(payload["outcomes"]["controller"], "controller_valid")
        self.assertEqual(payload["outcomes"]["candidate"], "candidate_failed")
        self.assertIn("CANDIDATE_TRANSPORT_ATTEMPT_FAILED", codes)
        self.assertEqual(
            payload["outcomes"]["transport"],
            "transport_identity_unresolved",
        )

    def test_inferred_export_failed_is_candidate_failure_with_unresolved_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_prose_only_bundle(root)
            (root / "raw" / "response.outerHTML.html").write_text(
                (
                    "<article>Generated file."
                    '<button aria-label="audit_report.md"></button>'
                    "</article>"
                ),
                encoding="utf-8",
                newline="",
            )
            self.write_failed_transport_attempt(
                root,
                "audit_report.md",
                response_html="<article><p>export_failed</p></article>",
            )
            controller = build_controller_record(
                root=root,
                case_id=CASE_ID,
                trial_id=TRIAL_ID,
                counting_state="preflight",
                target_filename=TARGET_NAME,
                output_filenames=[],
                output_control_filenames=["audit_report.md"],
                session_reference="preview-conversation:inferred-export-failed",
                observability_boundary=(
                    "Visible Preview response and exposed files only; no Data "
                    "Analysis invocation was observed."
                ),
            )
            (root / "controller_record.json").write_bytes(
                canonical_json_bytes(controller)
            )
            status, payload = self.invoke(
                root,
                refresh_record=False,
            )

        self.assertEqual(status, 1)
        codes = self.finding_codes(payload)
        self.assertEqual(payload["outcomes"]["controller"], "controller_valid")
        self.assertEqual(payload["outcomes"]["candidate"], "candidate_failed")
        self.assertEqual(
            payload["outcomes"]["transport"],
            "transport_identity_unresolved",
        )
        self.assertIn("CANDIDATE_TRANSPORT_ATTEMPT_FAILED", codes)
        self.assertFalse(any("CORRUPT" in code for code in codes))

    def test_visible_required_control_without_fallback_invalidates_controller(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            case_id = "return-envelope-positive-control"
            self.make_prose_only_bundle(root, case_id=case_id)
            controls = [
                "audit_report.md",
                "audit_return.json",
            ]
            (root / "raw" / "response.outerHTML.html").write_text(
                "<article>"
                '<button aria-label="audit_report.md"></button>'
                '<button aria-label="audit_return.json"></button>'
                "</article>",
                encoding="utf-8",
            )
            controller = build_controller_record(
                root=root,
                case_id=case_id,
                trial_id="D02",
                counting_state="preflight",
                target_filename=self.case(case_id)["fixture_paths"][0].split("/")[-1],
                output_filenames=[],
                output_control_filenames=controls,
                session_reference="preview-conversation:no-fallback",
                observability_boundary="Visible Preview response and exposed files only.",
            )
            (root / "controller_record.json").write_bytes(
                canonical_json_bytes(controller)
            )
            status, payload = self.invoke(
                root,
                refresh_record=False,
                case_id=case_id,
            )

        self.assertEqual(status, 1)
        self.assertEqual(
            payload["outcomes"]["controller"],
            "trial_invalid_controller",
        )
        self.assertEqual(payload["outcomes"]["candidate"], "not_scored")
        self.assertIn(
            "CONTROLLER_TRANSPORT_ATTEMPT_MISSING",
            self.finding_codes(payload),
        )

    def test_terminal_blank_after_valid_chunk_is_candidate_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            case_id = "return-envelope-positive-control"
            self.make_prose_only_bundle(root, case_id=case_id)
            controls = [
                "audit_report.md",
                "audit_return.json",
            ]
            (root / "raw" / "response.outerHTML.html").write_text(
                "<article>"
                '<button aria-label="audit_report.md"></button>'
                '<button aria-label="audit_return.json"></button>'
                "</article>",
                encoding="utf-8",
            )
            synthetic = b"\n".join(
                hashlib.sha256(f"incomplete-{index}".encode("ascii"))
                .hexdigest()
                .encode("ascii")
                for index in range(1000)
            )
            first = export_payload_chunk("audit_report.md", synthetic, 0)
            self.assertGreater(first["chunk_count"], 1)
            self.write_wrapper_capture_bytes(
                root,
                "audit_report.md",
                compiler_transport_bytes(first),
            )
            self.write_failed_transport_attempt(
                root,
                "audit_report.md",
                chunk_index=1,
                expected_payload_sha256=first["payload_sha256"],
                expected_encoded_sha256=first["encoded_sha256"],
            )
            self.write_failed_transport_attempt(root, "audit_return.json")
            controller = build_controller_record(
                root=root,
                case_id=case_id,
                trial_id="D02",
                counting_state="preflight",
                target_filename=self.case(case_id)["fixture_paths"][0].split("/")[-1],
                output_filenames=[],
                output_control_filenames=controls,
                session_reference="preview-conversation:incomplete-chunks",
                observability_boundary="Visible Preview response and exposed files only.",
            )
            (root / "controller_record.json").write_bytes(
                canonical_json_bytes(controller)
            )
            status, payload = self.invoke(
                root,
                refresh_record=False,
                case_id=case_id,
            )

        self.assertEqual(status, 1)
        self.assertEqual(payload["outcomes"]["controller"], "controller_valid")
        self.assertEqual(payload["outcomes"]["candidate"], "candidate_failed")
        self.assertEqual(
            payload["outcomes"]["transport"],
            "transport_identity_unresolved",
        )
        codes = self.finding_codes(payload)
        self.assertIn("CANDIDATE_TRANSPORT_ATTEMPT_FAILED", codes)
        self.assertNotIn("EXPORT_CHUNK_METADATA_INVALID", codes)
        self.assertNotIn("EXPORT_ENCODED_AGGREGATE_MISMATCH", codes)

    def test_missing_declared_next_attempt_is_controller_omission(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_prose_only_bundle(
                root,
                case_id="return-envelope-positive-control",
            )
            synthetic = b"\n".join(
                hashlib.sha256(f"omitted-attempt-{index}".encode("ascii"))
                .hexdigest()
                .encode("ascii")
                for index in range(1000)
            )
            first = export_payload_chunk("audit_report.md", synthetic, 0)
            self.assertGreater(first["chunk_count"], 1)
            self.write_wrapper_capture_bytes(
                root,
                "audit_report.md",
                compiler_transport_bytes(first),
            )
            with self.assertRaisesRegex(
                ValueError,
                "missing declared chunks",
            ):
                build_controller_record(
                    root=root,
                    case_id="return-envelope-positive-control",
                    trial_id="D02",
                    counting_state="preflight",
                    target_filename=self.case(
                        "return-envelope-positive-control"
                    )["fixture_paths"][0].split("/")[-1],
                    output_filenames=[],
                    output_control_filenames=[],
                    session_reference="preview-conversation:omitted-next-attempt",
                    observability_boundary=(
                        "Visible Preview response and exposed files only."
                    ),
                )

    def test_malformed_observed_output_roster_is_fail_closed_without_type_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root)
            path = root / "controller_record.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            record["observed_outputs"] = None
            path.write_bytes(canonical_json_bytes(record))
            status, payload = self.invoke(root, refresh_record=False)

        self.assertEqual(status, 1)
        self.assertIn("CONTROLLER_OUTPUT_ROSTER_INVALID", self.finding_codes(payload))
        self.assertEqual(
            payload["outcomes"]["disposition"],
            "trial_invalid_controller",
        )

    def test_candidate_identity_copy_mismatch_invalidates_freeze(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record, _ = self.make_bundle(root)
            (root / "GPT_PROFILE.json").write_bytes(b'{"wrong":true}\n')
            self.write_controller_record(root, record)
            status, payload = self.invoke(root)

        self.assertEqual(status, 1)
        self.assertIn(
            "CONTROLLER_CANDIDATE_IDENTITY_ROSTER_MISMATCH",
            self.finding_codes(payload),
        )
        self.assertEqual(
            payload["outcomes"]["disposition"],
            "trial_invalid_controller",
        )

    def test_wrong_exact_preview_prompt_invalidates_controller(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record, _ = self.make_bundle(root)
            (root / "preview_prompt.txt").write_text(
                "A paraphrased prompt is not the frozen prompt.\n",
                encoding="utf-8",
            )
            self.write_controller_record(root, record)
            status, payload = self.invoke(root)

        self.assertEqual(status, 1)
        self.assertIn(
            "CONTROLLER_PREVIEW_PROMPT_MISMATCH",
            self.finding_codes(payload),
        )

    def test_independently_captured_undeclared_output_is_candidate_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record, _ = self.make_bundle(root)
            (root / "unexpected_output.txt").write_text(
                "independently captured extra output\n",
                encoding="utf-8",
            )
            transport_path = root / "artifact_transport.json"
            transport = json.loads(transport_path.read_text(encoding="utf-8"))
            extra = (root / "unexpected_output.txt").read_bytes()
            transport["records"].append(
                {
                    "filename": "unexpected_output.txt",
                    "method": "direct_download",
                    "direct_download_outcome": "download_event",
                    "bytes": len(extra),
                    "sha256": sha256(extra),
                    "export_chunks": None,
                }
            )
            transport["records"].sort(key=lambda item: item["filename"])
            transport_path.write_bytes(canonical_json_bytes(transport))
            self.write_controller_record(root, record)
            status, payload = self.invoke(root)

        self.assertEqual(status, 1)
        self.assertEqual(payload["outcomes"]["controller"], "controller_valid")
        self.assertIn("CANDIDATE_OUTPUT_UNDECLARED", self.finding_codes(payload))
        self.assertEqual(payload["outcomes"]["candidate"], "candidate_failed")

    def test_candidate_declared_missing_capture_invalidates_controller(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record, _ = self.make_bundle(root)
            missing = next(
                item["filename"]
                for item in record["artifacts"]
                if item["role"] == "evidence"
            )
            (root / missing).unlink()
            transport = json.loads(
                (root / "artifact_transport.json").read_text(encoding="utf-8")
            )
            transport["records"] = [
                item for item in transport["records"] if item["filename"] != missing
            ]
            (root / "artifact_transport.json").write_bytes(
                canonical_json_bytes(transport)
            )
            raw_path = root / "raw" / "response.outerHTML.html"
            raw_html = raw_path.read_text(encoding="utf-8")
            raw_path.write_text(
                raw_html.replace(
                    f'<button aria-label="{missing}"></button>',
                    "",
                ),
                encoding="utf-8",
            )
            self.write_controller_record(root, record)
            status, payload = self.invoke(root)

        self.assertEqual(status, 1)
        self.assertIn(
            "CONTROLLER_DECLARED_OUTPUT_NOT_CAPTURED",
            self.finding_codes(payload),
        )
        self.assertEqual(
            payload["outcomes"]["disposition"],
            "trial_invalid_controller",
        )

    def test_self_reported_direct_download_event_remains_unresolved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record, _ = self.make_bundle(root)
            transport_path = root / "artifact_transport.json"
            transport = json.loads(transport_path.read_text(encoding="utf-8"))
            for item in transport["records"]:
                item["method"] = "direct_download"
                item["direct_download_outcome"] = "download_event"
                item["export_chunks"] = None
            transport_path.write_bytes(canonical_json_bytes(transport))
            for wrapper in list(root.glob("*.export.*.json")):
                wrapper.unlink()
            for wrapper in list((root / "raw").glob("*.export.*.json")):
                wrapper.unlink()
            for capture in list((root / "raw").glob("*.transport.*")):
                capture.unlink()
            self.write_controller_record(root, record)
            status, payload = self.invoke(root)

        self.assertEqual(status, 0)
        self.assertEqual(
            payload["outcomes"]["transport"],
            "transport_identity_unresolved",
        )
        self.assertNotEqual(
            payload["outcomes"]["transport"],
            "transport_identity_resolved",
        )

    def test_controller_builder_cli_round_trips_strict_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record, _ = self.make_bundle(root)
            controller = json.loads(
                (root / "controller_record.json").read_text(encoding="utf-8")
            )
            argv = [
                "build-record",
                str(root),
                "--case-id",
                CASE_ID,
                "--trial-id",
                TRIAL_ID,
                "--counting-state",
                "preflight",
                "--target",
                TARGET_NAME,
                "--session-reference",
                "preview-conversation:test",
                "--observability-boundary",
                "Visible Preview response and exposed files only.",
            ]
            for item in controller["observed_outputs"]:
                argv.extend(["--output", item["filename"]])
            for filename in controller["observed_output_controls"]:
                argv.extend(["--observed-control", filename])
            output = io.StringIO()
            with redirect_stdout(output):
                status = controller_main(argv)
            result = json.loads(output.getvalue())
            check_status, payload = self.invoke(root, refresh_record=False)

        self.assertEqual(status, 0)
        self.assertEqual(result["output_version"], "3.0")
        self.assertEqual(check_status, 0)
        self.assertEqual(payload["outcomes"]["controller"], "controller_valid")

    def test_controller_builder_cli_captures_prose_case_with_zero_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_prose_only_bundle(root)
            argv = [
                "build-record",
                str(root),
                "--case-id",
                CASE_ID,
                "--trial-id",
                TRIAL_ID,
                "--counting-state",
                "preflight",
                "--target",
                TARGET_NAME,
                "--session-reference",
                "preview-conversation:zero-output",
                "--observability-boundary",
                "Visible Preview response and exposed files only.",
            ]
            output = io.StringIO()
            with redirect_stdout(output):
                status = controller_main(argv)
            result = json.loads(output.getvalue())
            controller = json.loads(
                (root / "controller_record.json").read_text(encoding="utf-8")
            )

        self.assertEqual(status, 0)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(controller["observed_outputs"], [])


if __name__ == "__main__":
    unittest.main()
