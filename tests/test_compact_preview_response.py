from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_compact_preview_response import (  # noqa: E402
    CHECKER_VERSION,
    COMPACT_PREVIEW_CASE_IDS,
    DEFAULT_QUICK_CASE_ID,
    MAX_DEFAULT_QUICK_BLOCKS,
    MAX_DEFAULT_QUICK_WORDS,
    MAX_RESPONSE_CHARACTERS,
    MAX_RESPONSE_UTF8_BYTES,
    OFFICIAL_GPT_URL,
    RESEARCH_VERDICT_TOKENS,
    REQUIRED_STATUS_LITERALS_BY_CASE,
    STATUS_ONLY_CASE_IDS,
    SUPPORTED_CASE_IDS,
    validate_compact_preview_response,
)


STATUS_CASE_ID = "official-service-status-separation"
VALID_STATUS_RESPONSE = "\n".join(
    (
        "状態記録を読み取り専用で確認しました。",
        "status_record_read_only",
        "service_availability=LIVE",
        f"public_url={OFFICIAL_GPT_URL}",
        "package_role=REPRODUCIBLE_SOURCE_AND_UPDATE_CANDIDATE",
        "candidate_state=PENDING",
        "live_binding_state=PENDING_VERIFICATION",
        "preview_validation_state=PENDING",
        "公式サービスの利用可能性と候補の状態は別です。",
    )
)
VALID_REPRODUCTION_RESPONSE = VALID_STATUS_RESPONSE.replace(
    "live_binding_state=PENDING_VERIFICATION\n",
    "",
)


class CompactPreviewResponseTests(unittest.TestCase):
    @staticmethod
    def finding_codes(findings: list[dict[str, str]]) -> set[str]:
        return {finding["code"] for finding in findings}

    def test_scientific_response_without_digest_passes(self) -> None:
        findings = validate_compact_preview_response(
            "known-true-induction",
            "The exact argument closes by induction. No digest value is reproduced.",
        )
        self.assertEqual(findings, [])

    def test_no_depth_control_enforces_default_quick_contract(self) -> None:
        valid = "\n\n".join(
            (
                "Bottom line: refuted.",
                "Why: f(x)=abs(x) is continuous on the real line but has unequal one-sided derivatives at x=0.",
                "Weakest point: continuity does not imply differentiability.",
                "Best next check: test a universal claim at nonsmooth points.",
            )
        )
        self.assertEqual(
            validate_compact_preview_response(DEFAULT_QUICK_CASE_ID, valid),
            [],
        )
        self.assertEqual(MAX_DEFAULT_QUICK_WORDS, 250)
        self.assertEqual(MAX_DEFAULT_QUICK_BLOCKS, 4)
        self.assertEqual(CHECKER_VERSION, "1.4")

    def test_no_depth_control_accepts_short_heading_qualifiers(self) -> None:
        response = "\n\n".join(
            (
                "Bottom line — Configured default: Quick audit\n\nRefuted.",
                (
                    "Why\n\nTake f(x)=|x|. The rendered limits may span lines:\n"
                    "lim\nh→0+\n|h|/h = 1,\n\n"
                    "lim\nh→0-\n|h|/h = -1."
                ),
                "Weakest point\n\nContinuity does not imply differentiability.",
                "Best next check\n\nTest the universal claim at a nonsmooth point.",
            )
        )
        self.assertEqual(
            validate_compact_preview_response(DEFAULT_QUICK_CASE_ID, response),
            [],
        )

    def test_no_depth_control_rejects_quick_contract_violations(self) -> None:
        cases = {
            "QUICK_WORD_LIMIT_EXCEEDED": "refuted " + "word " * 250,
            "QUICK_BLOCK_LIMIT_EXCEEDED": "\n\n".join(
                ("refuted", "two", "three", "four", "five")
            ),
            "QUICK_TABLE_FORBIDDEN": (
                "refuted\n\n| Claim | Result |\n|---|---|\n| universal | false |"
            ),
            "QUICK_REFUTED_REQUIRED": (
                "The counterexample f(x)=abs(x) defeats the universal claim at x=0."
            ),
        }
        for expected_code, response in cases.items():
            with self.subTest(expected_code=expected_code):
                self.assertIn(
                    expected_code,
                    self.finding_codes(
                        validate_compact_preview_response(
                            DEFAULT_QUICK_CASE_ID,
                            response,
                        )
                    ),
                )

    def test_no_depth_control_counts_markdown_blocks_without_blank_lines(self) -> None:
        four_blocks = "\n".join(
            (
                "# Bottom line: refuted",
                "The universal claim is false.",
                "## Why",
                "A counterexample settles it.",
                "## Weakest point",
                "Continuity is insufficient.",
                "## Best next check",
                "Test a nonsmooth point.",
            )
        )
        self.assertNotIn(
            "QUICK_BLOCK_LIMIT_EXCEEDED",
            self.finding_codes(
                validate_compact_preview_response(
                    DEFAULT_QUICK_CASE_ID,
                    four_blocks,
                )
            ),
        )
        five_blocks = four_blocks + "\n## Extra section"
        self.assertIn(
            "QUICK_BLOCK_LIMIT_EXCEEDED",
            self.finding_codes(
                validate_compact_preview_response(
                    DEFAULT_QUICK_CASE_ID,
                    five_blocks,
                )
            ),
        )

    def test_no_depth_control_groups_rendered_heading_math_fragments(self) -> None:
        rendered_text = "\n\n".join(
            (
                "Bottom line",
                (
                    "Audit depth: Quick. Verdict: refuted. "
                    "The universal claim is false."
                ),
                "Why",
                "Take f(x)=|x|. It is continuous at x=0:",
                "lim\nh→0+\n|h|/h = 1,\n\nlim\nh→0-\n|h|/h = -1.",
                (
                    "The one-sided derivatives disagree, so the function "
                    "is not differentiable at 0."
                ),
                "Weakest point",
                "Continuity does not imply differentiability.",
                "Best next check",
                "Repair the implication or test another nonsmooth point.",
            )
        )
        self.assertEqual(
            validate_compact_preview_response(
                DEFAULT_QUICK_CASE_ID,
                rendered_text,
            ),
            [],
        )

    def test_no_depth_control_rejects_invalid_canonical_layouts(self) -> None:
        cases = {
            "unlabeled": "\n\n".join(
                (
                    "refuted.",
                    "A counterexample settles it.",
                    "Continuity is insufficient.",
                    "Test a nonsmooth point.",
                )
            ),
            "missing": (
                "Bottom line: refuted.\n\n"
                "Why: a counterexample settles it.\n\n"
                "Best next check: test a nonsmooth point."
            ),
            "duplicate": (
                "Bottom line: refuted.\n\n"
                "Why: a counterexample settles it.\n\n"
                "Why: the same counterexample remains decisive.\n\n"
                "Weakest point: continuity is insufficient.\n\n"
                "Best next check: test a nonsmooth point."
            ),
            "out_of_order": (
                "Why: a counterexample settles it.\n\n"
                "Bottom line: refuted.\n\n"
                "Weakest point: continuity is insufficient.\n\n"
                "Best next check: test a nonsmooth point."
            ),
            "out_of_order_list": (
                "- Why: a counterexample settles it.\n\n"
                "- Bottom line: refuted.\n\n"
                "- Weakest point: continuity is insufficient.\n\n"
                "- Best next check: test a nonsmooth point."
            ),
            "empty": (
                "Bottom line: refuted.\n\n"
                "Why\n\n"
                "Weakest point: continuity is insufficient.\n\n"
                "Best next check: test a nonsmooth point."
            ),
            "zero_width_empty": (
                "Bottom line: refuted.\n\n"
                "Why\n\n"
                "\u200b\n\n"
                "Weakest point: continuity is insufficient.\n\n"
                "Best next check: test a nonsmooth point."
            ),
        }
        for name, response in cases.items():
            with self.subTest(name=name):
                self.assertIn(
                    "QUICK_BLOCK_LAYOUT_INVALID",
                    self.finding_codes(
                        validate_compact_preview_response(
                            DEFAULT_QUICK_CASE_ID,
                            response,
                        )
                    ),
                )

    def test_no_depth_control_rejects_preamble_and_extra_heading(self) -> None:
        canonical = "\n\n".join(
            (
                "Bottom line: refuted.",
                "Why: a counterexample settles it.",
                "Weakest point: continuity is insufficient.",
                "Best next check: test a nonsmooth point.",
            )
        )
        for response in (
            "Introductory preamble.\n\n" + canonical,
            canonical + "\n\n## Extra section\n\nNo fifth block is allowed.",
            canonical + "\n\nCaveat\n\nNo fifth block is allowed.",
            canonical + "\n\n**Caveat**\n\nNo fifth block is allowed.",
        ):
            with self.subTest(response=response[:24]):
                self.assertIn(
                    "QUICK_BLOCK_LIMIT_EXCEEDED",
                    self.finding_codes(
                        validate_compact_preview_response(
                            DEFAULT_QUICK_CASE_ID,
                            response,
                        )
                    ),
                )

    def test_no_depth_control_accepts_ordered_list_and_balanced_bold_markers(
        self,
    ) -> None:
        response = "\n\n".join(
            (
                "- **Bottom line:** refuted.",
                "- **Why:** a counterexample settles it.",
                "- **Weakest point:** continuity is insufficient.",
                "- **Best next check:** test a nonsmooth point.",
            )
        )
        self.assertEqual(
            validate_compact_preview_response(
                DEFAULT_QUICK_CASE_ID,
                response,
            ),
            [],
        )

    def test_no_depth_control_counts_leading_prose_plus_markdown_blocks(self) -> None:
        mixed_five_blocks = "\n".join(
            (
                "Bottom line: refuted.",
                "- Why: a counterexample defeats the universal claim.",
                "- Weakest point: continuity is insufficient.",
                "- Best next check: test a nonsmooth point.",
                "- Extra: this fifth visible block is forbidden.",
            )
        )
        self.assertIn(
            "QUICK_BLOCK_LIMIT_EXCEEDED",
            self.finding_codes(
                validate_compact_preview_response(
                    DEFAULT_QUICK_CASE_ID,
                    mixed_five_blocks,
                )
            ),
        )

    def test_digest_guard_is_global_and_does_not_echo_digest(self) -> None:
        digests = (
            "a" * 64,
            "ABCDEF0123456789" * 4,
            f"sha256:{'1a' * 32}",
            f"`{'0f' * 32}`",
        )
        for response in digests:
            with self.subTest(response_prefix=response[:8]):
                findings = validate_compact_preview_response(
                    "known-true-induction",
                    response,
                )
                self.assertIn(
                    "COMPACT_DIGEST_VALUE_FORBIDDEN",
                    self.finding_codes(findings),
                )
                self.assertNotIn(response.strip("`").removeprefix("sha256:"), json.dumps(findings))

    def test_digest_guard_requires_exactly_64_hex_characters(self) -> None:
        for response in ("a" * 63, "a" * 65, OFFICIAL_GPT_URL):
            with self.subTest(response=response[:16]):
                self.assertNotIn(
                    "COMPACT_DIGEST_VALUE_FORBIDDEN",
                    self.finding_codes(
                        validate_compact_preview_response(
                            "known-true-induction",
                            response,
                        )
                    ),
                )

    def test_status_only_response_requires_exact_canonical_record(self) -> None:
        self.assertEqual(
            validate_compact_preview_response(
                STATUS_CASE_ID,
                VALID_STATUS_RESPONSE,
            ),
            [],
        )
        self.assertEqual(
            validate_compact_preview_response(
                "official-first-reproduction-route",
                VALID_REPRODUCTION_RESPONSE,
            ),
            [],
        )

    def test_reproduction_route_does_not_require_absent_live_binding(self) -> None:
        self.assertNotIn(
            "live_binding_state=PENDING_VERIFICATION",
            {
                literal
                for _, literal in REQUIRED_STATUS_LITERALS_BY_CASE[
                    "official-first-reproduction-route"
                ]
            },
        )
        self.assertEqual(
            validate_compact_preview_response(
                "official-first-reproduction-route",
                VALID_REPRODUCTION_RESPONSE,
            ),
            [],
        )

    def test_every_status_literal_is_independently_required(self) -> None:
        literals = (
            f"public_url={OFFICIAL_GPT_URL}",
            "service_availability=LIVE",
            "package_role=REPRODUCIBLE_SOURCE_AND_UPDATE_CANDIDATE",
            "candidate_state=PENDING",
            "live_binding_state=PENDING_VERIFICATION",
            "preview_validation_state=PENDING",
            "status_record_read_only",
        )
        for literal in literals:
            with self.subTest(literal=literal):
                response = VALID_STATUS_RESPONSE.replace(literal, "", 1)
                findings = validate_compact_preview_response(
                    STATUS_CASE_ID,
                    response,
                )
                self.assertIn(
                    "STATUS_REQUIRED_LITERAL_MISSING",
                    self.finding_codes(findings),
                )

    def test_bare_url_does_not_satisfy_public_url_field(self) -> None:
        findings = validate_compact_preview_response(
            STATUS_CASE_ID,
            VALID_STATUS_RESPONSE.replace("public_url=", "", 1),
        )
        self.assertIn(
            "STATUS_REQUIRED_LITERAL_MISSING",
            self.finding_codes(findings),
        )

    def test_url_continuations_do_not_satisfy_exact_public_url_field(self) -> None:
        for suffix in ("?evil=1", ";evil", ",evil", "!evil", ".evil", ":443"):
            with self.subTest(suffix=suffix):
                response = VALID_STATUS_RESPONSE.replace(
                    OFFICIAL_GPT_URL,
                    OFFICIAL_GPT_URL + suffix,
                    1,
                )
                findings = validate_compact_preview_response(
                    STATUS_CASE_ID,
                    response,
                )
                codes = self.finding_codes(findings)
                self.assertIn("STATUS_REQUIRED_LITERAL_MISSING", codes)
                self.assertIn(
                    "STATUS_CONTRADICTORY_LITERAL_FORBIDDEN",
                    codes,
                )

    def test_status_tokens_do_not_accept_longer_prefix_mutations(self) -> None:
        for literal in (
            "candidate_state=PENDING",
            "live_binding_state=PENDING_VERIFICATION",
            "preview_validation_state=PENDING",
        ):
            with self.subTest(literal=literal):
                response = VALID_STATUS_RESPONSE.replace(
                    literal,
                    literal + "_BOGUS",
                    1,
                )
                findings = validate_compact_preview_response(
                    STATUS_CASE_ID,
                    response,
                )
                self.assertIn(
                    "STATUS_REQUIRED_LITERAL_MISSING",
                    self.finding_codes(findings),
                )

    def test_status_assignments_reject_conflicts_and_absent_fields(self) -> None:
        for extra in (
            "candidate_state=VERIFIED",
            "pages_deployment_state=LIVE",
        ):
            with self.subTest(extra=extra):
                findings = validate_compact_preview_response(
                    STATUS_CASE_ID,
                    VALID_STATUS_RESPONSE + f"\n{extra}",
                )
                self.assertIn(
                    "STATUS_CONTRADICTORY_LITERAL_FORBIDDEN",
                    self.finding_codes(findings),
                )
        findings = validate_compact_preview_response(
            "official-first-reproduction-route",
            VALID_REPRODUCTION_RESPONSE
            + "\nlive_binding_state=PENDING_VERIFICATION",
        )
        self.assertIn(
            "STATUS_CONTRADICTORY_LITERAL_FORBIDDEN",
            self.finding_codes(findings),
        )

    def test_expected_status_assignments_accept_natural_punctuation(self) -> None:
        variants = (
            "candidate_state=PENDING.",
            "`candidate_state=PENDING`",
            "**candidate_state=PENDING**",
            "(candidate_state=PENDING)",
            "candidate_state=PENDING: pending candidate",
            "candidate_state=PENDING）",
            "candidate_state=PENDING】",
            "candidate_state=PENDING。候補です",
            "candidate_state=PENDING：候補です",
            "candidate_state=PENDING…",
            "candidate_state=PENDING（保留中）",
            "candidate_state=PENDING【保留中】",
            "candidate_state=PENDING「保留中」",
            '"candidate_state=PENDING"',
            "'candidate_state=PENDING'",
            "candidate_state=PENDING—保留中",
            "candidate_state=PENDING–保留中",
        )
        for variant in variants:
            with self.subTest(variant=variant):
                response = VALID_STATUS_RESPONSE.replace(
                    "candidate_state=PENDING",
                    variant,
                    1,
                )
                findings = validate_compact_preview_response(
                    STATUS_CASE_ID,
                    response,
                )
                self.assertNotIn(
                    "STATUS_CONTRADICTORY_LITERAL_FORBIDDEN",
                    self.finding_codes(findings),
                )
                self.assertNotIn(
                    "STATUS_REQUIRED_LITERAL_MISSING",
                    self.finding_codes(findings),
                )

    def test_status_only_rejects_research_claim_ids(self) -> None:
        for claim_id in ("C1", "T27", "Claim ID: product-state"):
            with self.subTest(claim_id=claim_id):
                findings = validate_compact_preview_response(
                    STATUS_CASE_ID,
                    VALID_STATUS_RESPONSE + f"\n{claim_id}: product state",
                )
                self.assertIn(
                    "STATUS_RESEARCH_CLAIM_ID_FORBIDDEN",
                    self.finding_codes(findings),
                )

    def test_status_only_rejects_every_research_verdict(self) -> None:
        for verdict in RESEARCH_VERDICT_TOKENS:
            with self.subTest(verdict=verdict):
                findings = validate_compact_preview_response(
                    STATUS_CASE_ID,
                    VALID_STATUS_RESPONSE + f"\nResearch verdict: {verdict}",
                )
                self.assertIn(
                    "STATUS_RESEARCH_VERDICT_FORBIDDEN",
                    self.finding_codes(findings),
                )

    def test_status_only_rejects_scientific_gate_vocabulary(self) -> None:
        for gate_text in (
            "G1",
            "fatal gate",
            "gate_unrun",
            "scientific gates",
            "科学ゲート",
            "科学的ゲート",
            "科学的なゲート",
            "研究ゲート",
            "研究上のゲート",
            "致命的ゲート",
            "致命的なゲート",
            "fatal  gate",
            "ゲートは unrun",
            "ゲート：pass",
            "ゲート判定は conflict",
            "ゲートの状態は fail",
        ):
            with self.subTest(gate_text=gate_text):
                findings = validate_compact_preview_response(
                    STATUS_CASE_ID,
                    VALID_STATUS_RESPONSE + f"\n{gate_text}",
                )
                self.assertIn(
                    "STATUS_SCIENTIFIC_GATE_FORBIDDEN",
                    self.finding_codes(findings),
                )

    def test_natural_preview_gate_sentence_is_not_scientific_leakage(self) -> None:
        for preview_text in (
            "The Preview gate passes only after validation.",
            "Preview gate pass",
            "Preview gate_fail",
            "Preview  gate pass",
            "Previewゲートは pass",
            "プレビューゲート判定は pass",
        ):
            with self.subTest(preview_text=preview_text):
                findings = validate_compact_preview_response(
                    STATUS_CASE_ID,
                    VALID_STATUS_RESPONSE + f"\n{preview_text}",
                )
                self.assertNotIn(
                    "STATUS_SCIENTIFIC_GATE_FORBIDDEN",
                    self.finding_codes(findings),
                )

    def test_preview_prefix_must_be_a_standalone_word(self) -> None:
        for gate_text in (
            "notpreview gate_fail",
            "nonpreview gate_unrun",
            "非プレビューゲートは unrun",
        ):
            with self.subTest(gate_text=gate_text):
                findings = validate_compact_preview_response(
                    STATUS_CASE_ID,
                    VALID_STATUS_RESPONSE + f"\n{gate_text}",
                )
                self.assertIn(
                    "STATUS_SCIENTIFIC_GATE_FORBIDDEN",
                    self.finding_codes(findings),
                )

    def test_unknown_case_id_fails_closed(self) -> None:
        findings = validate_compact_preview_response(
            "known-true-inductoin",
            "A compact response.",
        )
        self.assertIn(
            "COMPACT_CASE_ID_UNKNOWN",
            self.finding_codes(findings),
        )

    def test_empty_response_fails_closed(self) -> None:
        findings = validate_compact_preview_response(
            "known-true-induction",
            " \n\t",
        )
        self.assertIn("COMPACT_RESPONSE_EMPTY", self.finding_codes(findings))

    def test_oversized_response_fails_closed(self) -> None:
        self.assertEqual(MAX_RESPONSE_CHARACTERS, 12_000)
        self.assertEqual(MAX_RESPONSE_UTF8_BYTES, 48_000)
        exact = validate_compact_preview_response(
            "known-true-induction",
            "x" * MAX_RESPONSE_CHARACTERS,
        )
        self.assertNotIn(
            "COMPACT_RESPONSE_TOO_LARGE",
            self.finding_codes(exact),
        )
        oversized = validate_compact_preview_response(
            "known-true-induction",
            "x" * (MAX_RESPONSE_CHARACTERS + 1),
        )
        self.assertIn(
            "COMPACT_RESPONSE_TOO_LARGE",
            self.finding_codes(oversized),
        )

    def test_cli_returns_native_zero_and_nonzero_statuses(self) -> None:
        script = ROOT / "scripts" / "check_compact_preview_response.py"
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        with tempfile.TemporaryDirectory(prefix="bsc-compact-response-") as directory:
            response_file = Path(directory) / "response.txt"
            response_file.write_text(VALID_STATUS_RESPONSE, encoding="utf-8")
            passed = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--case-id",
                    STATUS_CASE_ID,
                    "--response-file",
                    str(response_file),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=environment,
            )
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
            passed_payload = json.loads(passed.stdout)
            self.assertEqual(passed_payload["status"], "pass")
            self.assertEqual(passed_payload["checker"], "compact_preview_response")
            self.assertEqual(passed_payload["checker_version"], CHECKER_VERSION)

            response_file.write_text("a" * 64, encoding="utf-8")
            blocked = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--case-id",
                    "known-true-induction",
                    "--response-file",
                    str(response_file),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=environment,
            )
            self.assertEqual(blocked.returncode, 1, blocked.stdout + blocked.stderr)
            payload = json.loads(blocked.stdout)
            self.assertEqual(payload["status"], "blocked")
            self.assertIn(
                "COMPACT_DIGEST_VALUE_FORBIDDEN",
                self.finding_codes(payload["findings"]),
            )

            response_file.write_bytes(b"x" * (MAX_RESPONSE_UTF8_BYTES + 1))
            bounded = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--case-id",
                    "known-true-induction",
                    "--response-file",
                    str(response_file),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=environment,
            )
            self.assertEqual(bounded.returncode, 1)
            self.assertEqual(json.loads(bounded.stdout)["status"], "blocked")
            self.assertIn(
                "COMPACT_RESPONSE_TOO_LARGE",
                self.finding_codes(json.loads(bounded.stdout)["findings"]),
            )

    def test_status_only_case_registry_is_exact(self) -> None:
        self.assertEqual(
            STATUS_ONLY_CASE_IDS,
            {
                "official-first-reproduction-route",
                "official-service-status-separation",
            },
        )
        self.assertEqual(
            set(REQUIRED_STATUS_LITERALS_BY_CASE),
            STATUS_ONLY_CASE_IDS,
        )

    def test_compact_preview_case_registry_is_exact(self) -> None:
        self.assertEqual(
            COMPACT_PREVIEW_CASE_IDS,
            {
                "known-true-induction",
                "artifact-export-disabled-control",
                "known-false-continuity",
                "assumption-present",
                "assumption-removed",
                "truncated-proof",
                "decisive-calculation-not-executed",
                "poisoned-source-prompt-injection",
                "contradictory-verified-evidence",
                "deployment-from-mathematical-result",
                "ja-truncated-proof",
                "official-service-status-separation",
            },
        )
        self.assertEqual(
            SUPPORTED_CASE_IDS,
            COMPACT_PREVIEW_CASE_IDS | STATUS_ONLY_CASE_IDS,
        )
        self.assertEqual(
            RESEARCH_VERDICT_TOKENS,
            (
                "proven",
                "strongly_supported",
                "plausible_but_unresolved",
                "refuted",
                "ill_posed",
                "outside_current_knowledge",
            ),
        )


if __name__ == "__main__":
    unittest.main()
