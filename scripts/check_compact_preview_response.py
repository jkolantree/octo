#!/usr/bin/env python3
"""Fail-closed semantic checks for one compact Custom GPT Preview response."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Sequence


CHECKER_VERSION = "1.4"
MAX_RESPONSE_CHARACTERS = 12_000
MAX_RESPONSE_UTF8_BYTES = MAX_RESPONSE_CHARACTERS * 4
DEFAULT_QUICK_CASE_ID = "known-false-continuity"
MAX_DEFAULT_QUICK_WORDS = 250
MAX_DEFAULT_QUICK_BLOCKS = 4
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
WORD_RE = re.compile(r"\b[\w'-]+\b", re.UNICODE)
CANONICAL_REFUTED_RE = re.compile(
    r"(?<![A-Za-z0-9_])refuted(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
MARKDOWN_TABLE_DELIMITER_RE = re.compile(
    r"(?m)^[ \t]*\|?[ \t]*:?-{3,}:?[ \t]*"
    r"(?:\|[ \t]*:?-{3,}:?[ \t]*)+\|?[ \t]*$"
)
HTML_TABLE_RE = re.compile(r"<[ \t]*/?[ \t]*(?:table|thead|tbody|tr|th|td)\b", re.IGNORECASE)
GRID_TABLE_RE = re.compile(r"(?m)^[ \t]*\+-{3,}\+(?:-{3,}\+)+[ \t]*$")
MARKDOWN_VISIBLE_BLOCK_START_RE = re.compile(
    r"(?m)^[ \t]{0,3}(?:"
    r"#{1,6}[ \t]+\S|"
    r"(?:[-+*]|\d+[.)])[ \t]+\S|"
    r">[ \t]*\S|"
    r"(?:```|~~~)"
    r")"
)
MARKDOWN_PREFIX_RE = re.compile(
    r"^[ \t]{0,3}(?:"
    r"#{1,6}[ \t]+|"
    r"(?:[-+*]|\d+[.)])[ \t]+"
    r")"
)
INVISIBLE_FORMAT_RE = re.compile("[\ufeff\u200b\u200c\u200d\u2060]")
QUICK_BLOCK_LABELS = (
    "Bottom line",
    "Why",
    "Weakest point",
    "Best next check",
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


def _quick_block_marker(line: str) -> tuple[str, str] | None:
    candidate = line.strip()
    candidate = MARKDOWN_PREFIX_RE.sub("", candidate, count=1)
    for label in QUICK_BLOCK_LABELS:
        if candidate == label:
            return label, ""
        for separator in (" — ", " – ", " - ", ":", "：", "—", "–"):
            prefix = label + separator
            if candidate.startswith(prefix):
                return label, candidate[len(prefix) :].strip()
        for wrapper in ("**", "__"):
            for inside_separator in ("", ":", "："):
                wrapped = (
                    wrapper
                    + label
                    + inside_separator
                    + wrapper
                )
                if candidate == wrapped:
                    return label, ""
                if not candidate.startswith(wrapped):
                    continue
                remainder = candidate[len(wrapped) :]
                if not remainder or not (
                    remainder[0].isspace()
                    or remainder[0] in (":", "：")
                ):
                    continue
                remainder = remainder.strip()
                if (
                    not inside_separator
                    and remainder.startswith((":", "："))
                ):
                    remainder = remainder[1:].strip()
                return label, remainder
    return None


def _fallback_default_quick_blocks(response: str) -> list[str]:
    paragraph_blocks = [
        block
        for block in re.split(r"(?:\r?\n)[ \t]*(?:\r?\n)+", response.strip())
        if block.strip()
    ]
    visible_blocks: list[str] = []
    for paragraph in paragraph_blocks:
        structural_starts = list(
            MARKDOWN_VISIBLE_BLOCK_START_RE.finditer(paragraph)
        )
        if not structural_starts:
            visible_blocks.append(paragraph)
            continue
        leading_prose = paragraph[: structural_starts[0].start()]
        if leading_prose.strip():
            visible_blocks.append(leading_prose)
        visible_blocks.extend(match.group(0) for match in structural_starts)
    return visible_blocks


def _has_visible_content(value: str) -> bool:
    return bool(INVISIBLE_FORMAT_RE.sub("", value).strip())


def _is_bold_only_heading(value: str) -> bool:
    candidate = value.strip()
    for wrapper in ("**", "__"):
        if (
            candidate.startswith(wrapper)
            and candidate.endswith(wrapper)
            and len(candidate) > len(wrapper) * 2
            and _has_visible_content(
                candidate[len(wrapper) : -len(wrapper)]
            )
        ):
            return True
    return False


def _is_plain_title_heading(value: str) -> bool:
    candidate = INVISIBLE_FORMAT_RE.sub("", value).strip()
    if "\n" in candidate or len(candidate) > 60:
        return False
    if not any(character.isalpha() for character in candidate):
        return False
    if any(character in candidate for character in ".?!。！？:：;,=<>/\\|{}[]()"):
        return False
    words = candidate.split()
    return 1 <= len(words) <= 6 and (
        candidate.istitle() or candidate.isupper()
    )


def _extra_quick_blocks(body: str) -> list[str]:
    extras = [
        line.strip()
        for line in body.splitlines()
        if MARKDOWN_VISIBLE_BLOCK_START_RE.match(line)
    ]
    paragraphs = [
        paragraph
        for paragraph in re.split(
            r"(?:\r?\n)[ \t]*(?:\r?\n)+",
            body.strip(),
        )
        if _has_visible_content(paragraph)
    ]
    for paragraph in paragraphs:
        if (
            MARKDOWN_VISIBLE_BLOCK_START_RE.match(paragraph)
            or _is_bold_only_heading(paragraph)
            or _is_plain_title_heading(paragraph)
        ):
            if paragraph.strip() not in extras:
                extras.append(paragraph.strip())
    return extras


def _default_quick_blocks(
    response: str,
) -> tuple[list[str], bool]:
    """Return semantic Quick blocks and whether a detected layout is valid.

    Preview can render one semantic section as a heading, prose paragraphs, and
    display-math elements. A rendered-text capture then contains blank-line
    fragments that are not additional top-level blocks. When canonical Quick
    markers are present, group all following content under the current marker.
    Fall back to the generic Markdown counter only when no marker is present.
    """

    lines = response.splitlines()
    markers: list[tuple[int, str, str]] = []
    for line_index, line in enumerate(lines):
        marker = _quick_block_marker(line)
        if marker is not None:
            label, inline_content = marker
            markers.append((line_index, label, inline_content))

    if not markers:
        return _fallback_default_quick_blocks(response), False

    labels = [label for _, label, _ in markers]
    if labels != list(QUICK_BLOCK_LABELS):
        return _fallback_default_quick_blocks(response), False

    visible_blocks: list[str] = []
    first_marker_index = markers[0][0]
    preamble = "\n".join(lines[:first_marker_index]).strip()
    if preamble:
        visible_blocks.append(preamble)

    layout_valid = True
    for marker_index, (line_index, _, inline_content) in enumerate(markers):
        next_line_index = (
            markers[marker_index + 1][0]
            if marker_index + 1 < len(markers)
            else len(lines)
        )
        body_lines = lines[line_index + 1 : next_line_index]
        body = "\n".join(body_lines).strip()
        if not _has_visible_content(inline_content) and not _has_visible_content(
            body
        ):
            layout_valid = False
        visible_blocks.append(
            "\n".join(lines[line_index:next_line_index]).strip()
        )
        visible_blocks.extend(_extra_quick_blocks(body))

    return visible_blocks, layout_valid


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

    if case_id == DEFAULT_QUICK_CASE_ID:
        word_count = len(WORD_RE.findall(response))
        if word_count > MAX_DEFAULT_QUICK_WORDS:
            findings.append(
                _finding(
                    "QUICK_WORD_LIMIT_EXCEEDED",
                    (
                        "the default-Quick response exceeds the "
                        f"{MAX_DEFAULT_QUICK_WORDS}-word ceiling"
                    ),
                )
            )
        quick_blocks, quick_layout_valid = _default_quick_blocks(response)
        if not quick_layout_valid:
            findings.append(
                _finding(
                    "QUICK_BLOCK_LAYOUT_INVALID",
                    (
                        "canonical Quick blocks are missing, "
                        "duplicated, empty, or out of order"
                    ),
                )
            )
        block_count = len(quick_blocks)
        if block_count > MAX_DEFAULT_QUICK_BLOCKS:
            findings.append(
                _finding(
                    "QUICK_BLOCK_LIMIT_EXCEEDED",
                    (
                        "the default-Quick response exceeds the "
                        f"{MAX_DEFAULT_QUICK_BLOCKS}-block ceiling"
                    ),
                )
            )
        if (
            MARKDOWN_TABLE_DELIMITER_RE.search(response)
            or HTML_TABLE_RE.search(response)
            or GRID_TABLE_RE.search(response)
        ):
            findings.append(
                _finding(
                    "QUICK_TABLE_FORBIDDEN",
                    "the default-Quick control case must not use a table",
                )
            )
        if CANONICAL_REFUTED_RE.search(response) is None:
            findings.append(
                _finding(
                    "QUICK_REFUTED_REQUIRED",
                    "the default-Quick control case must contain canonical refuted",
                )
            )

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
