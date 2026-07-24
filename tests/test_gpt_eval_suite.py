import copy
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.check_gpt_eval_suite import (
    SuiteLedgerError,
    _validate_candidate_snapshot,
    _validate_score_for_pass,
    check_suite_ledger,
)
from scripts.check_gpt_eval_bundle import (
    SCIENTIFIC_RESEARCH_PROJECTION_REQUIRED,
    STATUS_ONLY_RESEARCH_PROJECTION_EMPTY,
)
from scripts.check_gpt_frozen_candidate import (
    EXCLUDED_CYCLE_PATHS,
    MANIFEST_SCHEMA,
    REGISTRY_VERSION,
    registry_entries,
)
from scripts.gpt_eval_controller import (
    CANDIDATE_FAILED,
    CANDIDATE_NOT_SCORED,
    CANDIDATE_PASSED,
    CONTROLLER_RECORD_VERSION,
    CONTROLLER_VALID,
    RAW_RESPONSE_FILENAME,
    TRANSPORT_IDENTITY_UNRESOLVED,
    TRIAL_INVALID_CONTROLLER,
    canonical_json_bytes,
    derive_disposition,
    frozen_trial_bindings,
)


ROOT = Path(__file__).resolve().parents[1]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class GptEvalSuiteTests(unittest.TestCase):
    def setUp(self):
        self.snapshot_patch = patch(
            "scripts.check_gpt_eval_suite._validate_candidate_snapshot",
            side_effect=self.fake_candidate_snapshot,
        )
        self.snapshot_patch.start()
        self.addCleanup(self.snapshot_patch.stop)
        self.bundle_patch = patch(
            "scripts.check_gpt_eval_suite.check_bundle",
            side_effect=self.recompute_archived_checker,
        )
        self.bundle_mock = self.bundle_patch.start()
        self.addCleanup(self.bundle_patch.stop)

    def fake_candidate_snapshot(
        self,
        *,
        freeze_bytes: bytes,
        **_: object,
    ) -> tuple[Path, tuple[tuple[str, int, str], ...]]:
        label = json.loads(freeze_bytes.decode("utf-8"))["freeze"]
        registered_label = (
            "freeze-one"
            if label == "freeze-two-metadata-only"
            else label
        )
        data = registered_label.encode("utf-8")
        return ROOT, (("gpt/GPT_INSTRUCTIONS.md", len(data), digest(data)),)

    def recompute_archived_checker(
        self,
        evidence_directory: Path,
        **_: object,
    ) -> tuple[int, dict]:
        checker = json.loads(
            (evidence_directory.parent / "checker.json").read_text(encoding="utf-8")
        )
        return (0 if checker.get("status") == "pass" else 1), checker

    def write_file(self, root: Path, relative: str, data: bytes) -> dict:
        path = root / Path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return {
            "filename": Path(relative).as_posix(),
            "bytes": len(data),
            "sha256": digest(data),
        }

    def candidate_identity(
        self,
        freeze_bytes: bytes,
        *,
        candidate_source_root: Path | None = None,
    ) -> list[dict]:
        if candidate_source_root is None:
            source_rows = [
                ("profile", "GPT_PROFILE.json", b"profile\n"),
                ("instructions", "GPT_INSTRUCTIONS.md", b"instructions\n"),
                ("eval_spec", "GPT_EVAL_SPEC.json", b"eval spec\n"),
            ]
        else:
            source_rows = [
                (
                    "profile",
                    "GPT_PROFILE.json",
                    (
                        candidate_source_root
                        / "gpt"
                        / "_source"
                        / "GPT_PROFILE.json"
                    ).read_bytes(),
                ),
                (
                    "instructions",
                    "GPT_INSTRUCTIONS.md",
                    (
                        candidate_source_root
                        / "gpt"
                        / "GPT_INSTRUCTIONS.md"
                    ).read_bytes(),
                ),
                (
                    "eval_spec",
                    "GPT_EVAL_SPEC.json",
                    (
                        candidate_source_root
                        / "gpt"
                        / "_source"
                        / "GPT_EVAL_SPEC.json"
                    ).read_bytes(),
                ),
            ]
        rows = [
            ("freeze_manifest", "GPT_FROZEN_CANDIDATE.json", freeze_bytes),
            *source_rows,
        ]
        return [
            {
                "kind": kind,
                "filename": filename,
                "bytes": len(data),
                "sha256": digest(data),
            }
            for kind, filename, data in rows
        ]

    def controller(
        self,
        *,
        trial_id: str,
        case_id: str,
        counting_state: str,
        identity: list[dict],
        raw_bytes: bytes,
        session_reference: str,
    ) -> dict:
        placeholder = digest(b"controller artifact\n")
        return {
            "controller_record_version": CONTROLLER_RECORD_VERSION,
            "case_id": case_id,
            "trial_id": trial_id,
            "counting_state": counting_state,
            "preview_prompt": {
                "filename": "preview_prompt.txt",
                "bytes": 7,
                "sha256": digest(b"prompt\n"),
            },
            "raw_response": {
                "filename": RAW_RESPONSE_FILENAME,
                "bytes": len(raw_bytes),
                "sha256": digest(raw_bytes),
            },
            "fresh_conversation": {
                "required": True,
                "observed": True,
                "session_reference": session_reference,
                "observability_boundary": "Preserved Preview response and exposed files.",
            },
            "candidate_identity": copy.deepcopy(identity),
            "controller_artifacts": [
                {
                    "kind": "controller",
                    "filename": filename,
                    "bytes": 20,
                    "sha256": placeholder,
                }
                for filename in (
                    "artifact_transport.json",
                    "visible_response_dom.txt",
                    "preview_prompt.txt",
                )
            ],
            "inputs": [],
            "observed_output_controls": [],
            "observed_outputs": [],
            "direct_acquisition_attempts": [],
            "compiler_transport_capture": {
                "status": "missing",
                "candidate_evidence": True,
                "detail": (
                    "no compiler-v6 stdout block was present in the completed response"
                ),
                "compiler_blocks": [],
                "compiler": None,
                "transport_version": None,
            },
            "reconstructed_outputs": [],
        }

    def score(
        self,
        *,
        trial_id: str,
        case_id: str,
        pre_digest: str,
        candidate: str,
    ) -> dict:
        automatic_failure = candidate == CANDIDATE_FAILED
        status_only = case_id in {
            "official-service-status-separation",
            "official-first-reproduction-route",
        }
        return {
            "score_result_version": "2.0",
            "case_id": case_id,
            "trial_id": trial_id,
            "pre_score_controller_sha256": pre_digest,
            "dimension_scores": {f"dimension_{number:02d}": 2 for number in range(1, 11)},
            "total_score": 20,
            "automatic_failure": automatic_failure,
            "observable_behavior_results": {"required behavior": True},
            "forbidden_behavior_results": {"forbidden behavior": False},
            "observed_research_projection": {} if status_only else {"T": "proven"},
            "research_projection_requirement": (
                STATUS_ONLY_RESEARCH_PROJECTION_EMPTY
                if status_only
                else SCIENTIFIC_RESEARCH_PROJECTION_REQUIRED
            ),
            "research_verdict_allowed": None if status_only else True,
            "research_projection_contract_satisfied": True,
            "terminal_response_complete": True,
            "scorer": "preserved-manual-scorer",
            "notes": "Exact manual rubric record.",
        }

    def make_attempt(
        self,
        root: Path,
        *,
        suite_id: str,
        trial_id: str,
        case_id: str,
        attempt_number: int,
        identity: list[dict],
        controller_outcome: str = CONTROLLER_VALID,
        candidate_outcome: str = CANDIDATE_PASSED,
        session_reference: str | None = None,
    ) -> dict:
        attempt_id = f"{trial_id}-A{attempt_number:02d}"
        prefix = f"records/{suite_id}/{attempt_id}"
        raw_bytes = f"<article>{suite_id} {attempt_id} complete response</article>\n".encode()
        raw_ref = self.write_file(
            root,
            f"{prefix}/response.outerHTML.html",
            raw_bytes,
        )
        evidence_relative = f"{prefix}/evidence"
        self.write_file(
            root,
            f"{evidence_relative}/{RAW_RESPONSE_FILENAME}",
            raw_bytes,
        )
        counting_state = "counted" if attempt_number == 1 else "invalid_retry"
        pre = self.controller(
            trial_id=trial_id,
            case_id=case_id,
            counting_state=counting_state,
            identity=identity,
            raw_bytes=raw_bytes,
            session_reference=(
                session_reference or f"preview:{suite_id}:{attempt_id}"
            ),
        )
        pre_bytes = canonical_json_bytes(pre)
        pre_ref = self.write_file(root, f"{prefix}/pre.json", pre_bytes)

        score_ref = None
        score_bytes = None
        if controller_outcome == CONTROLLER_VALID:
            score = self.score(
                trial_id=trial_id,
                case_id=case_id,
                pre_digest=digest(pre_bytes),
                candidate=candidate_outcome,
            )
            score_bytes = canonical_json_bytes(score)
            score_ref = self.write_file(root, f"{prefix}/score.json", score_bytes)
            self.write_file(
                root,
                f"{evidence_relative}/pre_score_controller.json",
                pre_bytes,
            )
            self.write_file(
                root,
                f"{evidence_relative}/score_result.json",
                score_bytes,
            )
            post = copy.deepcopy(pre)
            post["controller_artifacts"].extend(
                [
                    {
                        "kind": "controller",
                        "filename": "pre_score_controller.json",
                        "bytes": len(pre_bytes),
                        "sha256": digest(pre_bytes),
                    },
                    {
                        "kind": "controller",
                        "filename": "score_result.json",
                        "bytes": len(score_bytes),
                        "sha256": digest(score_bytes),
                    },
                ]
            )
        else:
            post = copy.deepcopy(pre)
            candidate_outcome = CANDIDATE_NOT_SCORED
        post_bytes = canonical_json_bytes(post)
        post_ref = self.write_file(root, f"{prefix}/post.json", post_bytes)
        self.write_file(
            root,
            f"{evidence_relative}/controller_record.json",
            post_bytes,
        )
        identity_digest = digest(canonical_json_bytes(identity))
        bindings = {
            "controller_record_sha256": digest(post_bytes),
            "pre_score_controller_sha256": (
                digest(pre_bytes) if score_bytes is not None else None
            ),
            "score_result_sha256": (
                digest(score_bytes) if score_bytes is not None else None
            ),
            "candidate_identity_sha256": identity_digest,
        }
        checker = {
            "checker": "gpt_eval_bundle",
            "output_version": "2.0",
            "evidence_directory": str(
                (root / Path(evidence_relative)).resolve()
            ),
            "status": (
                "pass"
                if controller_outcome == CONTROLLER_VALID
                and candidate_outcome == CANDIDATE_PASSED
                else "blocked"
            ),
            "outcomes": {
                "controller": controller_outcome,
                "candidate": candidate_outcome,
                "transport": TRANSPORT_IDENTITY_UNRESOLVED,
                "disposition": derive_disposition(
                    controller=controller_outcome,
                    candidate=candidate_outcome,
                    transport=TRANSPORT_IDENTITY_UNRESOLVED,
                ),
                "scoring_allowed": controller_outcome == CONTROLLER_VALID,
            },
            "bindings": bindings,
            "checks": {},
            "findings": [],
            "score_result": None,
            "return_desk": None,
            "limitations": [],
        }
        checker_ref = self.write_file(
            root,
            f"{prefix}/checker.json",
            canonical_json_bytes(checker),
        )
        return {
            "attempt_id": attempt_id,
            "parent_attempt_id": (
                None
                if attempt_number == 1
                else f"{trial_id}-A{attempt_number - 1:02d}"
            ),
            "pre_score_controller": pre_ref,
            "post_score_controller": post_ref,
            "checker_result": checker_ref,
            "score_result": score_ref,
            "raw_response": raw_ref,
            "evidence_directory": evidence_relative,
            "controller": controller_outcome,
            "candidate": candidate_outcome,
            "transport": TRANSPORT_IDENTITY_UNRESOLVED,
        }

    def make_suite(
        self,
        root: Path,
        *,
        suite_number: int,
        freeze_label: str,
        fail_at: int | None = None,
        retry_at: int | None = None,
        reuse_first_session_at: int | None = None,
        freeze_bytes_override: bytes | None = None,
        candidate_source_relative: str | None = None,
        candidate_source_path: Path | None = None,
    ) -> dict:
        suite_id = f"S{suite_number:02d}"
        freeze_bytes = (
            canonical_json_bytes({"freeze": freeze_label})
            if freeze_bytes_override is None
            else freeze_bytes_override
        )
        freeze_ref = self.write_file(
            root,
            f"freezes/{suite_id}/GPT_FROZEN_CANDIDATE.json",
            freeze_bytes,
        )
        identity = self.candidate_identity(
            freeze_bytes,
            candidate_source_root=candidate_source_path,
        )
        bindings = frozen_trial_bindings(ROOT)
        final_number = fail_at or 39
        trials = []
        for number in range(1, final_number + 1):
            trial_id = f"C{number:03d}"
            case_id = bindings[trial_id][1]
            attempts = []
            if retry_at == number:
                attempts.append(
                    self.make_attempt(
                        root,
                        suite_id=suite_id,
                        trial_id=trial_id,
                        case_id=case_id,
                        attempt_number=1,
                        identity=identity,
                        controller_outcome=TRIAL_INVALID_CONTROLLER,
                        session_reference=(
                            f"preview:{suite_id}:C001-A01"
                            if reuse_first_session_at == number
                            else None
                        ),
                    )
                )
                attempt_number = 2
            else:
                attempt_number = 1
            attempts.append(
                self.make_attempt(
                    root,
                    suite_id=suite_id,
                    trial_id=trial_id,
                    case_id=case_id,
                    attempt_number=attempt_number,
                    identity=identity,
                    candidate_outcome=(
                        CANDIDATE_FAILED
                        if fail_at == number
                        else CANDIDATE_PASSED
                    ),
                    session_reference=(
                        f"preview:{suite_id}:C001-A01"
                        if reuse_first_session_at == number
                        else None
                    ),
                )
            )
            trials.append(
                {"trial_id": trial_id, "case_id": case_id, "attempts": attempts}
            )
        return {
            "suite_id": suite_id,
            "repair_number": suite_number - 1,
            "restart_of": None if suite_number == 1 else "S01",
            "status": (
                "stopped_candidate_failed"
                if fail_at is not None
                else "complete_pass"
            ),
            "freeze_manifest": freeze_ref,
            "candidate_source_root": (
                candidate_source_relative
                if candidate_source_relative is not None
                else f"freezes/{suite_id}/source"
            ),
            "candidate_identity_sha256": digest(canonical_json_bytes(identity)),
            "trials": trials,
        }

    def make_ledger(
        self,
        root: Path,
        *,
        first_fail_at: int | None = None,
        second_fail_at: int | None = None,
        include_second: bool = False,
        same_second_freeze: bool = False,
        metadata_only_second_freeze: bool = False,
        reuse_first_session_at: int | None = None,
    ) -> tuple[Path, dict]:
        protocol_ref = self.write_file(
            root,
            "GPT_FROZEN_EVALUATION_PROTOCOL.json",
            (ROOT / "gpt" / "_source" / "GPT_FROZEN_EVALUATION_PROTOCOL.json").read_bytes(),
        )
        first = self.make_suite(
            root,
            suite_number=1,
            freeze_label="freeze-one",
            fail_at=first_fail_at,
            reuse_first_session_at=reuse_first_session_at,
        )
        suites = [first]
        if include_second:
            second = self.make_suite(
                root,
                suite_number=2,
                freeze_label=(
                    "freeze-one"
                    if same_second_freeze
                    else (
                        "freeze-two-metadata-only"
                        if metadata_only_second_freeze
                        else "freeze-two"
                    )
                ),
                fail_at=second_fail_at,
            )
            suites.append(second)
        overall_status = (
            "passed"
            if (not include_second and first_fail_at is None)
            or (include_second and second_fail_at is None)
            else ("failed_closed" if include_second else "repair_pending")
        )
        ledger = {
            "suite_ledger_version": "1.0",
            "frozen_protocol": protocol_ref,
            "overall_status": overall_status,
            "suites": suites,
        }
        path = root / "suite_ledger.json"
        path.write_bytes(canonical_json_bytes(ledger))
        return path, ledger

    def rewrite_ledger(self, path: Path, ledger: dict) -> None:
        path.write_bytes(canonical_json_bytes(ledger))

    def finding_codes(self, payload: dict) -> set[str]:
        return {item["code"] for item in payload["findings"]}

    def make_candidate_snapshot(
        self,
        root: Path,
        *,
        source_relative: str = "candidate-source",
        changed_path: str | None = None,
    ) -> tuple[dict, bytes, bytes]:
        source_root = root / source_relative
        protocol_bytes = (
            ROOT / "gpt" / "_source" / "GPT_FROZEN_EVALUATION_PROTOCOL.json"
        ).read_bytes()
        rows = []
        for category, relative in registry_entries():
            data = (ROOT / Path(relative)).read_bytes()
            if relative == changed_path:
                data += b"\nS02 registered-file repair bytes.\n"
            path = source_root / Path(relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            rows.append(
                {
                    "bytes": len(data),
                    "category": category,
                    "path": relative,
                    "sha256": digest(data),
                }
            )
        manifest = {
            "excluded_paths": list(EXCLUDED_CYCLE_PATHS),
            "file_count": len(rows),
            "files": rows,
            "manifest_schema": MANIFEST_SCHEMA,
            "registry_version": REGISTRY_VERSION,
        }
        freeze_bytes = canonical_json_bytes(manifest)
        freeze_path = source_root / "docs" / "GPT_FROZEN_CANDIDATE.json"
        freeze_path.parent.mkdir(parents=True, exist_ok=True)
        freeze_path.write_bytes(freeze_bytes)
        return {"candidate_source_root": source_relative}, freeze_bytes, protocol_bytes

    def test_all_39_cases_pass_exactly_once_in_order_on_one_freeze(self):
        with tempfile.TemporaryDirectory() as directory:
            path, ledger = self.make_ledger(Path(directory))
            status, payload = check_suite_ledger(path)

        self.assertEqual(len(ledger["suites"][0]["trials"]), 39)
        self.assertEqual(status, 0)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["checks"]["promotion_gate"]["status"], "pass")

    def test_aggregate_score_contract_separates_status_only_and_scientific_cases(
        self,
    ):
        for case_id in (
            "official-service-status-separation",
            "official-first-reproduction-route",
        ):
            with self.subTest(case_id=case_id):
                score = self.score(
                    trial_id="C038",
                    case_id=case_id,
                    pre_digest=digest(b"pre"),
                    candidate=CANDIDATE_PASSED,
                )
                self.assertTrue(
                    _validate_score_for_pass(
                        score,
                        expected_case_id=case_id,
                    )
                )

        scientific = self.score(
            trial_id="C001",
            case_id="known-true-induction",
            pre_digest=digest(b"pre"),
            candidate=CANDIDATE_PASSED,
        )
        self.assertTrue(
            _validate_score_for_pass(
                scientific,
                expected_case_id="known-true-induction",
            )
        )
        scientific["observed_research_projection"] = {}
        scientific["research_projection_requirement"] = (
            STATUS_ONLY_RESEARCH_PROJECTION_EMPTY
        )
        scientific["research_verdict_allowed"] = None
        self.assertFalse(
            _validate_score_for_pass(
                scientific,
                expected_case_id="known-true-induction",
            )
        )

    def test_syntactically_valid_counted_case_mismap_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            path, ledger = self.make_ledger(Path(directory))
            ledger["suites"][0]["trials"][4]["case_id"] = "known-true-induction"
            self.rewrite_ledger(path, ledger)
            status, payload = check_suite_ledger(path)

        self.assertEqual(status, 1)
        self.assertIn(
            "SUITE_TRIAL_ORDER_OR_MAPPING_INVALID",
            self.finding_codes(payload),
        )

    def test_duplicate_or_out_of_order_counted_case_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            path, ledger = self.make_ledger(Path(directory))
            trials = ledger["suites"][0]["trials"]
            trials[9], trials[10] = trials[10], trials[9]
            self.rewrite_ledger(path, ledger)
            status, payload = check_suite_ledger(path)

        self.assertEqual(status, 1)
        self.assertIn(
            "SUITE_TRIAL_ORDER_OR_MAPPING_INVALID",
            self.finding_codes(payload),
        )

    def test_invalid_controller_retry_has_explicit_same_freeze_ancestry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol_ref = self.write_file(
                root,
                "GPT_FROZEN_EVALUATION_PROTOCOL.json",
                (
                    ROOT / "gpt" / "_source" / "GPT_FROZEN_EVALUATION_PROTOCOL.json"
                ).read_bytes(),
            )
            suite = self.make_suite(
                root,
                suite_number=1,
                freeze_label="freeze-retry",
                retry_at=7,
            )
            ledger = {
                "suite_ledger_version": "1.0",
                "frozen_protocol": protocol_ref,
                "overall_status": "passed",
                "suites": [suite],
            }
            path = root / "suite_ledger.json"
            self.rewrite_ledger(path, ledger)
            status, payload = check_suite_ledger(path)

        self.assertEqual(status, 0)
        self.assertEqual(payload["checks"]["retry_ancestry"]["status"], "pass")

    def test_candidate_failure_cannot_be_retried_as_controller_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            path, ledger = self.make_ledger(Path(directory), first_fail_at=5)
            trial = ledger["suites"][0]["trials"][-1]
            retry = copy.deepcopy(trial["attempts"][0])
            retry["attempt_id"] = "C005-A02"
            retry["parent_attempt_id"] = "C005-A01"
            trial["attempts"].append(retry)
            self.rewrite_ledger(path, ledger)
            status, payload = check_suite_ledger(path)

        self.assertEqual(status, 1)
        self.assertIn(
            "SUITE_RETRY_AFTER_NONCONTROLLER_FAILURE",
            self.finding_codes(payload),
        )

    def test_pre_post_score_hash_chain_rejects_fully_rebound_pre_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, ledger = self.make_ledger(root)
            attempt = ledger["suites"][0]["trials"][0]["attempts"][0]
            pre_path = root / Path(attempt["pre_score_controller"]["filename"])
            pre = json.loads(pre_path.read_text(encoding="utf-8"))
            pre["fresh_conversation"]["session_reference"] = "mutated-after-score"
            pre_bytes = canonical_json_bytes(pre)
            pre_path.write_bytes(pre_bytes)
            attempt["pre_score_controller"]["bytes"] = len(pre_bytes)
            attempt["pre_score_controller"]["sha256"] = digest(pre_bytes)
            checker_path = root / Path(attempt["checker_result"]["filename"])
            checker = json.loads(checker_path.read_text(encoding="utf-8"))
            checker["bindings"]["pre_score_controller_sha256"] = digest(pre_bytes)
            checker_bytes = canonical_json_bytes(checker)
            checker_path.write_bytes(checker_bytes)
            attempt["checker_result"]["bytes"] = len(checker_bytes)
            attempt["checker_result"]["sha256"] = digest(checker_bytes)
            self.rewrite_ledger(path, ledger)
            status, payload = check_suite_ledger(path)

        self.assertEqual(status, 1)
        self.assertIn(
            "SUITE_TRIAL_FREEZE_OR_MAPPING_MISMATCH",
            self.finding_codes(payload),
        )

    def test_raw_response_mutation_cannot_be_rebound_only_in_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, ledger = self.make_ledger(root)
            attempt = ledger["suites"][0]["trials"][0]["attempts"][0]
            raw_path = root / Path(attempt["raw_response"]["filename"])
            raw_bytes = raw_path.read_bytes() + b"<p>mutated</p>\n"
            raw_path.write_bytes(raw_bytes)
            attempt["raw_response"]["bytes"] = len(raw_bytes)
            attempt["raw_response"]["sha256"] = digest(raw_bytes)
            self.rewrite_ledger(path, ledger)
            status, payload = check_suite_ledger(path)

        self.assertEqual(status, 1)
        self.assertIn(
            "SUITE_TRIAL_FREEZE_OR_MAPPING_MISMATCH",
            self.finding_codes(payload),
        )

    def test_one_repair_requires_new_freeze_and_full_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path, _ = self.make_ledger(
                Path(directory),
                first_fail_at=4,
                include_second=True,
            )
            status, payload = check_suite_ledger(path)

        self.assertEqual(status, 0)
        self.assertEqual(payload["checks"]["repair_and_stopping_rule"]["status"], "pass")

    def test_real_registered_file_change_allows_s02_repair_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_source, first_freeze, first_protocol = self.make_candidate_snapshot(
                root,
                source_relative="candidate-source-s01",
            )
            second_source, second_freeze, second_protocol = self.make_candidate_snapshot(
                root,
                source_relative="candidate-source-s02",
                changed_path="gpt/GPT_INSTRUCTIONS.md",
            )
            self.assertEqual(first_protocol, second_protocol)
            protocol_ref = self.write_file(
                root,
                "GPT_FROZEN_EVALUATION_PROTOCOL.json",
                first_protocol,
            )
            first_suite = self.make_suite(
                root,
                suite_number=1,
                freeze_label="unused-real-s01",
                fail_at=4,
                freeze_bytes_override=first_freeze,
                candidate_source_relative=first_source["candidate_source_root"],
                candidate_source_path=(
                    root / first_source["candidate_source_root"]
                ),
            )
            second_suite = self.make_suite(
                root,
                suite_number=2,
                freeze_label="unused-real-s02",
                freeze_bytes_override=second_freeze,
                candidate_source_relative=second_source["candidate_source_root"],
                candidate_source_path=(
                    root / second_source["candidate_source_root"]
                ),
            )
            ledger = {
                "suite_ledger_version": "1.0",
                "frozen_protocol": protocol_ref,
                "overall_status": "passed",
                "suites": [first_suite, second_suite],
            }
            path = root / "suite_ledger.json"
            self.rewrite_ledger(path, ledger)
            with patch(
                "scripts.check_gpt_eval_suite._validate_candidate_snapshot",
                new=_validate_candidate_snapshot,
            ):
                status, payload = check_suite_ledger(path)

        self.assertEqual(status, 0)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(
            payload["checks"]["repair_and_stopping_rule"]["status"],
            "pass",
        )

    def test_second_suite_cannot_reuse_failed_freeze(self):
        with tempfile.TemporaryDirectory() as directory:
            path, _ = self.make_ledger(
                Path(directory),
                first_fail_at=4,
                include_second=True,
                same_second_freeze=True,
            )
            status, payload = check_suite_ledger(path)

        self.assertEqual(status, 1)
        self.assertIn("SUITE_REPAIR_RESTART_INVALID", self.finding_codes(payload))

    def test_suite_stops_at_first_candidate_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, ledger = self.make_ledger(root, first_fail_at=3)
            suite = ledger["suites"][0]
            identity = self.candidate_identity(
                (root / Path(suite["freeze_manifest"]["filename"])).read_bytes()
            )
            case_id = frozen_trial_bindings(ROOT)["C004"][1]
            suite["trials"].append(
                {
                    "trial_id": "C004",
                    "case_id": case_id,
                    "attempts": [
                        self.make_attempt(
                            root,
                            suite_id="S01",
                            trial_id="C004",
                            case_id=case_id,
                            attempt_number=1,
                            identity=identity,
                        )
                    ],
                }
            )
            self.rewrite_ledger(path, ledger)
            status, payload = check_suite_ledger(path)

        self.assertEqual(status, 1)
        self.assertIn("SUITE_STOPPING_RULE_VIOLATION", self.finding_codes(payload))

    def test_more_than_two_suite_runs_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path, ledger = self.make_ledger(Path(directory))
            third = copy.deepcopy(ledger["suites"][0])
            third["suite_id"] = "S03"
            third["repair_number"] = 2
            third["restart_of"] = "S02"
            ledger["suites"].extend([copy.deepcopy(third), third])
            self.rewrite_ledger(path, ledger)
            status, payload = check_suite_ledger(path)

        self.assertEqual(status, 1)
        self.assertIn("SUITE_LEDGER_HEADER_INVALID", self.finding_codes(payload))

    def test_globally_reused_preview_session_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path, _ = self.make_ledger(
                Path(directory),
                reuse_first_session_at=2,
            )
            status, payload = check_suite_ledger(path)

        self.assertEqual(status, 1)
        self.assertIn("SUITE_FRESH_CONVERSATION_REUSED", self.finding_codes(payload))

    def test_evidence_snapshot_cannot_diverge_from_bound_raw_response(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, ledger = self.make_ledger(root)
            attempt = ledger["suites"][0]["trials"][0]["attempts"][0]
            evidence_raw = (
                root
                / Path(attempt["evidence_directory"])
                / Path(RAW_RESPONSE_FILENAME)
            )
            evidence_raw.write_bytes(evidence_raw.read_bytes() + b"<p>mutation</p>\n")
            status, payload = check_suite_ledger(path)

        self.assertEqual(status, 1)
        self.assertIn("SUITE_EVIDENCE_BINDING_MISMATCH", self.finding_codes(payload))

    def test_archived_checker_json_is_recomputed_not_trusted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, ledger = self.make_ledger(root)
            attempt = ledger["suites"][0]["trials"][0]["attempts"][0]
            checker_path = root / Path(attempt["checker_result"]["filename"])
            recomputed = json.loads(checker_path.read_text(encoding="utf-8"))
            forged = copy.deepcopy(recomputed)
            forged["limitations"] = ["forged archived conclusion"]
            forged_bytes = canonical_json_bytes(forged)
            checker_path.write_bytes(forged_bytes)
            attempt["checker_result"]["bytes"] = len(forged_bytes)
            attempt["checker_result"]["sha256"] = digest(forged_bytes)
            self.rewrite_ledger(path, ledger)

            def recompute(
                evidence_directory: Path,
                **_: object,
            ) -> tuple[int, dict]:
                if "C001-A01" in evidence_directory.as_posix():
                    return 0, recomputed
                return self.recompute_archived_checker(evidence_directory)

            self.bundle_mock.side_effect = recompute
            status, payload = check_suite_ledger(path)

        self.assertEqual(status, 1)
        self.assertIn(
            "SUITE_CHECKER_RECOMPUTATION_MISMATCH",
            self.finding_codes(payload),
        )

    def test_candidate_source_snapshot_manifest_is_reverified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            suite, freeze_bytes, protocol_bytes = self.make_candidate_snapshot(root)
            source_root, registered_files = _validate_candidate_snapshot(
                ledger_root=root,
                suite=suite,
                freeze_bytes=freeze_bytes,
                protocol_bytes=protocol_bytes,
                label="$.suites[0]",
            )
            registered_paths = {item[0] for item in registered_files}
            self.assertEqual(len(registered_files), len(registry_entries()))
            self.assertIn("scripts/check_gpt_eval_suite.py", registered_paths)
            self.assertIn("scripts/gpt_artifact_compiler.py", registered_paths)
            self.assertIn("tests/test_gpt_artifact_compiler.py", registered_paths)
            self.assertIn("tests/test_gpt_eval_controller.py", registered_paths)
            self.assertIn("tests/test_gpt_eval_bundle.py", registered_paths)
            self.assertIn("tests/test_gpt_eval_suite.py", registered_paths)
            self.assertIn("gpt/evals/GPT_MANUAL_SCORECARD.md", registered_paths)
            target = (
                source_root
                / "scripts"
                / "check_gpt_eval_bundle.py"
            )
            target.write_bytes(target.read_bytes() + b"mutation\n")
            with self.assertRaises(SuiteLedgerError) as captured:
                _validate_candidate_snapshot(
                    ledger_root=root,
                    suite=suite,
                    freeze_bytes=freeze_bytes,
                    protocol_bytes=protocol_bytes,
                    label="$.suites[0]",
                )

        self.assertEqual(
            captured.exception.code,
            "SUITE_SNAPSHOT_FILE_BINDING_MISMATCH",
        )

    def test_incomplete_candidate_snapshot_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "candidate-source"
            source.mkdir()
            manifest = {
                "excluded_paths": list(EXCLUDED_CYCLE_PATHS),
                "file_count": 0,
                "files": [],
                "manifest_schema": MANIFEST_SCHEMA,
                "registry_version": REGISTRY_VERSION,
            }
            freeze_bytes = canonical_json_bytes(manifest)
            freeze_path = source / "docs" / "GPT_FROZEN_CANDIDATE.json"
            freeze_path.parent.mkdir()
            freeze_path.write_bytes(freeze_bytes)
            protocol_bytes = (
                ROOT
                / "gpt"
                / "_source"
                / "GPT_FROZEN_EVALUATION_PROTOCOL.json"
            ).read_bytes()
            with self.assertRaises(SuiteLedgerError) as captured:
                _validate_candidate_snapshot(
                    ledger_root=root,
                    suite={"candidate_source_root": "candidate-source"},
                    freeze_bytes=freeze_bytes,
                    protocol_bytes=protocol_bytes,
                    label="$.suites[0]",
                )

        self.assertEqual(captured.exception.code, "SUITE_FREEZE_MANIFEST_INVALID")

    @unittest.skipUnless(os.name == "nt", "Windows junction regression")
    def test_windows_junction_candidate_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "junction-target"
            target.mkdir()
            junction = root / "junction-source"
            command_processor = os.environ.get(
                "COMSPEC",
                r"C:\Windows\System32\cmd.exe",
            )
            result = subprocess.run(
                [
                    command_processor,
                    "/d",
                    "/c",
                    "mklink",
                    "/J",
                    str(junction),
                    str(target),
                ],
                capture_output=True,
                check=False,
                text=True,
                timeout=10,
            )
            if result.returncode != 0 or not junction.exists():
                self.skipTest(
                    "junction creation unavailable without elevation: "
                    f"{result.stderr.strip() or result.stdout.strip()}"
                )
            try:
                with self.assertRaises(SuiteLedgerError) as captured:
                    _validate_candidate_snapshot(
                        ledger_root=root,
                        suite={"candidate_source_root": "junction-source"},
                        freeze_bytes=b"{}\n",
                        protocol_bytes=b"",
                        label="$.suites[0]",
                    )
            finally:
                if junction.exists():
                    os.rmdir(junction)

        self.assertEqual(
            captured.exception.code,
            "SUITE_DIRECTORY_MISSING_OR_UNSAFE",
        )

    def test_manifest_only_second_freeze_cannot_masquerade_as_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            path, _ = self.make_ledger(
                Path(directory),
                first_fail_at=4,
                include_second=True,
                metadata_only_second_freeze=True,
            )
            status, payload = check_suite_ledger(path)

        self.assertEqual(status, 1)
        self.assertIn(
            "SUITE_REPAIR_REGISTERED_FILES_UNCHANGED",
            self.finding_codes(payload),
        )


if __name__ == "__main__":
    unittest.main()
