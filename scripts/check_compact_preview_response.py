#!/usr/bin/env python3
"""Fail-closed semantic checks for one compact Custom GPT Preview response."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Sequence


CHECKER_VERSION = "1.0"
MAX_RESPONSE_CHARACTERS = 12_000
MAX_RESPONSE_UTF8_BYTES = MAX_RESPONSE_CHARACTERS * 4
OFFICIAL_GPT_URL = (
    "https://chatgpt.com/g/"
    "g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor"
)
COMPACT_PREVIEW_CASE_IDS = frozenset(
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
    }
)
STATUS_ONLY_CASE_IDS = frozenset(
    {
        "official-first-reproduction-route",
        "official-service-status-separation",
    }
)
SUPPORTED_CASE_IDS = COMPACT_PREVIEW_CASE_IDS | STATUS_ONLY_CASE_IDS
COMMON_STATUS_LITERALS = (
    ("public_url", f"public_url={OFFICIAL_GPT_URL}"),
    ("service_availability", "service_availability=LIVE"),
    (
        "package_role",
        "package_role=REPRODUCIBLE_SOURCE_AND_UPDATE_CANDIDATE",
    ),
    ("candidate_state", "candidate_state=PENDING"),
    ("preview_validation_state", "preview_validation_state=PENDING"),
    ("execution_mode", "status_record_read_only"),
)
REQUIRED_STATUS_LITERALS_BY_CASE = {
    "official-first-reproduction-route": COMMON_STATUS_LITERALS,
    "official-service-status-separation": COMMON_STATUS_LITERALS
    + (
        (
            "live_binding_state",
            "live_binding_state=PENDING_VERIFICATION",
        ),
    ),
}
RESEARCH_VERDICT_TOKENS = (
    "proven",
    "strongly_supported",
    "plausible_but_unresolved",
    "refuted",
    "ill_posed",
    "outside_current_knowledge",
)

STANDALONE_DIGEST_RE = re.compile(
    r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{64}(?![0-9A-Fa-f])"
)
RESEARCH_CLAIM_ID_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:C|T)[0-9]+(?![A-Za-z0-9_])"
)
RESEARCH_CLAIM_LABEL_RE = re.compile(
    r"(?:research[_ -]+claim|claim[_ -]+id|研究主張|主張ID)",
    re.IGNORECASE,
)
RESEARCH_VERDICT_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    + "|".join(re.escape(token) for token in RESEARCH_VERDICT_TOKENS)
    + r")(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
RESEARCH_VERDICT_LABEL_RE = re.compile(
    r"(?:research[_ -]+verdict|研究上の判定)",
    re.IGNORECASE,
)
SCIENTIFIC_GATE_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    r"G[0-9]+|(?:fatal|scientific|research)[_ -]+gates?|"
    r"(?:科学(?:的(?:な)?)?|研究(?:上の)?|致命的(?:な)?)[_ -]*ゲート"
    r")(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
GATE_OUTCOME_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"gate[ _-]*(?:pass|fail|conflict|unrun)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
PREVIEW_GATE_PREFIX_RE = re.compile(
    r"(?<![A-Za-z0-9_])preview[ _-]+$",
    re.IGNORECASE,
)
JAPANESE_GATE_OUTCOME_RE = re.compile(
    r"ゲート(?:の)?(?:判定|状態|結果)?"
    r"[ \t\u3000:：はをが=,，_-]{0,12}"
    r"(?:pass|fail|conflict|unrun)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
PRODUCT_PREVIEW_PREFIX_RE = re.compile(
    r"(?:^|[\s(\[（【「『])"
    r"(?:preview|プレビュー)[ \t\u3000_-]*$",
    re.IGNORECASE,
)
STATUS_ASSIGNMENT_START_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(service_availability|public_url|package_role|candidate_state|"
    r"live_binding_state|preview_validation_state|release_state|"
    r"github_release_state|pages_deployment_state)"
    r"="
)
STATUS_LITERAL_TERMINATOR_RE = re.compile(
    r"(?:$|\s|[)\]}*`'\"“”‘’]|"
    r"[，。、；！？：（）【】『』「」〈〉《》〔〕…—–]|"
    r"[.,;:!?](?=$|[\s)\]}*`]))"
)


def _finding(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _contains_required_status_literal(
    response: str,
    literal: str,
) -> bool:
    pattern = re.compile(
        r"(?<![A-Za-z0-9_])" + re.escape(literal)
    )
    return any(
        STATUS_LITERAL_TERMINATOR_RE.match(response, match.end())
        for match in pattern.finditer(response)
    )


def _status_assignment_matches_expected(
    response: str,
    match: re.Match[str],
    expected_value: str | None,
) -> bool:
    if expected_value is None:
        return False
    expected_literal = f"{match.group(1)}={expected_value}"
    if not response.startswith(expected_literal, match.start()):
        return False
    return (
        STATUS_LITERAL_TERMINATOR_RE.match(
            response,
            match.start() + len(expected_literal),
        )
        is not None
    )


def _contains_scientific_gate(response: str) -> bool:
    if SCIENTIFIC_GATE_RE.search(response):
        return True
    for match in GATE_OUTCOME_RE.finditer(response):
        if PREVIEW_GATE_PREFIX_RE.search(response[: match.start()]) is None:
            return True
    for match in JAPANESE_GATE_OUTCOME_RE.finditer(response):
        if PRODUCT_PREVIEW_PREFIX_RE.search(response[: match.start()]) is None:
            return True
    return False


def validate_compact_preview_response(
    case_id: str,
    response: str,
) -> list[dict[str, str]]:
    """Return deterministic findings without repeating prohibited response data."""

    findings: list[dict[str, str]] = []
    if not response.strip():
        findings.append(
            _finding(
                "COMPACT_RESPONSE_EMPTY",
                "the compact Preview response is empty",
            )
        )
    if len(response) > MAX_RESPONSE_CHARACTERS:
        findings.append(
            _finding(
                "COMPACT_RESPONSE_TOO_LARGE",
                (
                    "the compact Preview response exceeds the hard "
                    f"{MAX_RESPONSE_CHARACTERS}-character ceiling"
                ),
            )
        )

    digest_count = len(STANDALONE_DIGEST_RE.findall(response))
    if digest_count:
        findings.append(
            _finding(
                "COMPACT_DIGEST_VALUE_FORBIDDEN",
                (
                    "the compact Preview response contains "
                    f"{digest_count} standalone 64-hex digest value(s)"
                ),
            )
        )

    if case_id not in SUPPORTED_CASE_IDS:
        findings.append(
            _finding(
                "COMPACT_CASE_ID_UNKNOWN",
                "the case ID is not in the exact compact Preview roster",
            )
        )
        return findings

    required_status_literals = REQUIRED_STATUS_LITERALS_BY_CASE.get(case_id)
    if required_status_literals is None:
        return findings

    missing = [
        label
        for label, required_literal in required_status_literals
        if not _contains_required_status_literal(
            response,
            required_literal,
        )
    ]
    if missing:
        findings.append(
            _finding(
                "STATUS_REQUIRED_LITERAL_MISSING",
                "missing exact status-only literals: " + ", ".join(missing),
            )
        )
    expected_assignments = {
        literal.split("=", 1)[0]: literal.split("=", 1)[1]
        for _, literal in required_status_literals
        if "=" in literal
    }
    contradictory_keys = sorted(
        {
            match.group(1)
            for match in STATUS_ASSIGNMENT_START_RE.finditer(response)
            if not _status_assignment_matches_expected(
                response,
                match,
                expected_assignments.get(match.group(1)),
            )
        }
    )
    if contradictory_keys:
        findings.append(
            _finding(
                "STATUS_CONTRADICTORY_LITERAL_FORBIDDEN",
                (
                    "status-only response contains absent or contradictory "
                    "canonical fields: "
                    + ", ".join(contradictory_keys)
                ),
            )
        )
    if (
        RESEARCH_CLAIM_ID_RE.search(response)
        or RESEARCH_CLAIM_LABEL_RE.search(response)
    ):
        findings.append(
            _finding(
                "STATUS_RESEARCH_CLAIM_ID_FORBIDDEN",
                "a status-only response must not create a research claim ID",
            )
        )
    if (
        RESEARCH_VERDICT_RE.search(response)
        or RESEARCH_VERDICT_LABEL_RE.search(response)
    ):
        findings.append(
            _finding(
                "STATUS_RESEARCH_VERDICT_FORBIDDEN",
                "a status-only response must not contain research-verdict vocabulary",
            )
        )
    if _contains_scientific_gate(response):
        findings.append(
            _finding(
                "STATUS_SCIENTIFIC_GATE_FORBIDDEN",
                "a status-only response must not create or report a scientific gate",
            )
        )
    return findings


def result_payload(
    case_id: str,
    findings: list[dict[str, str]],
) -> dict[str, object]:
    return {
        "case_id": case_id,
        "checker": "compact_preview_response",
        "checker_version": CHECKER_VERSION,
        "findings": findings,
        "status": "pass" if not findings else "blocked",
    }


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail closed on compact Preview response-policy violations."
    )
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--response-file", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        with args.response_file.open("rb") as response_stream:
            response_bytes = response_stream.read(
                MAX_RESPONSE_UTF8_BYTES + 1
            )
    except OSError:
        findings = [
            _finding(
                "COMPACT_RESPONSE_UNREADABLE",
                "the response file could not be read",
            )
        ]
        _emit(result_payload(args.case_id, findings))
        return 2
    if len(response_bytes) > MAX_RESPONSE_UTF8_BYTES:
        findings = [
            _finding(
                "COMPACT_RESPONSE_TOO_LARGE",
                (
                    "the compact Preview response exceeds the hard "
                    f"{MAX_RESPONSE_CHARACTERS}-character ceiling"
                ),
            )
        ]
        _emit(result_payload(args.case_id, findings))
        return 1
    try:
        response = response_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        findings = [
            _finding(
                "COMPACT_RESPONSE_NOT_UTF8",
                "the response file is not strict UTF-8",
            )
        ]
        _emit(result_payload(args.case_id, findings))
        return 2

    findings = validate_compact_preview_response(args.case_id, response)
    _emit(result_payload(args.case_id, findings))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
