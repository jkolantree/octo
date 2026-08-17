#!/usr/bin/env python3
"""Validate public Markdown rendering, links, and publication-safe source text."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SKIPPED_DIRECTORY_NAMES = {".git", "build", "dist", "release"}
PRESERVED_PRESENTATION_SHA256 = {
    "docs/standalone/BSC_EXECUTION_AND_RECEIPTS.md": (
        "ef3499a71578e7058a4ba44c8f62439674f4dd3f9200580833f46bb1ef2f43ed"
    ),
    "research/derived-witnessed-descent/"
    "Derived_Witnessed_Descent_and_Atomic_Spectral_Complexity.md": (
        "a2bc92f94d3b53eecc379432c0eab9d7992797078ed1fb408b37ed3768795300"
    ),
    "research/derived-witnessed-descent/"
    "Formal_Verification_and_Prime_Block_Obstruction.md": (
        "ba27ed31bc3c5c2f45a559acd2bbaaacfaf1968e61a63750943dfc1899953211"
    ),
    "research/derived-witnessed-descent/verification/SOURCE_README.md": (
        "c1bb28af8df5a844897dc54f1447d0fc8f2cfb35cffd636965d4965aeb92754b"
    ),
}
NON_NARRATIVE_MARKDOWN = {
    # Compact machine-delivery payload: syntax and privacy checks still apply,
    # but adding presentation headings would change its protocol bytes.
    "gpt/GPT_INSTRUCTIONS.md",
}
PROHIBITED_FORMAT_CODEPOINTS = {
    0x00AD,  # soft hyphen
    0x061C,  # Arabic letter mark
    0x200B,  # zero-width space
    0x200C,  # zero-width non-joiner
    0x200D,  # zero-width joiner
    0x200E,  # left-to-right mark
    0x200F,  # right-to-left mark
    *range(0x202A, 0x202F),  # bidi embeddings and overrides
    *range(0x2060, 0x206A),  # word joiner and bidi isolates
    0xFEFF,  # byte-order mark / zero-width no-break space
}
UNSAFE_HTML = re.compile(
    r"<\s*/?\s*(?:script|iframe|object|embed|form|input|button|textarea|select)\b",
    re.IGNORECASE,
)
UNSAFE_SCHEME = re.compile(
    r"\b(?:data|file|javascript|vbscript)\s*:",
    re.IGNORECASE,
)
WINDOWS_ABSOLUTE_PATH = re.compile(
    r"(?<![A-Za-z0-9_])(?:[A-Za-z]:[\\/]|\\\\[A-Za-z0-9_.-]+[\\/])"
)
UNIX_PRIVATE_PATH = re.compile(
    r"(?<![A-Za-z0-9_:])/"
    r"(?:Users|home|root|tmp|var/tmp|private|etc|opt|srv|mnt|Volumes)"
    r"(?:/|\b)"
)
FENCE = re.compile(r"^( {0,3})(`{3,}|~{3,})([^\r\n]*)$")
ATX_HEADING = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+|$)")
ATX_HEADING_TEXT = re.compile(r"^ {0,3}#{1,6}[ \t]+(.+?)[ \t]*#*[ \t]*$")
SETEXT_EQUALS = re.compile(r"^ {0,3}=+[ \t]*$")
REFERENCE_DEFINITION = re.compile(r"^ {0,3}\[([^\]\r\n]+)\]:[ \t]*(.*)$")
REFERENCE_USAGE = re.compile(r"\[([^\]\r\n]+)\]\[([^\]\r\n]*)\]")
TABLE_SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")
RAW_MATH_DELIMITERS = (
    (r"\[", "unsupported display-math opener"),
    (r"\]", "unsupported display-math closer"),
    (r"\(", "unsupported inline-math opener"),
    (r"\)", "unsupported inline-math closer"),
)
GITHUB_APPROVED_MATH_MACROS = frozenset(
    {
        "Lambda",
        "Longleftrightarrow",
        "Omega",
        "Sigma",
        "Theta",
        "alpha",
        "begin",
        "beta",
        "bigcap",
        "boldsymbol",
        "cdots",
        "circ",
        "delta",
        "dim",
        "downarrow",
        "end",
        "eta",
        "forall",
        "frac",
        "gamma",
        "ge",
        "in",
        "int",
        "kappa",
        "ker",
        "lambda",
        "ldots",
        "le",
        "left",
        "liminf",
        "log",
        "longrightarrow",
        "mathbb",
        "mathbf",
        "mathcal",
        "mathrm",
        "mathsf",
        "mid",
        "min",
        "mu",
        "ne",
        "nsubseteq",
        "omega",
        "partial",
        "pi",
        "qquad",
        "quad",
        "rho",
        "right",
        "setminus",
        "simeq",
        "star",
        "subset",
        "subseteq",
        "sum",
        "sup",
        "tau",
        "theta",
        "times",
        "to",
        "varepsilon",
        "xrightarrow",
    }
)
GITHUB_APPROVED_MATH_CONTROL_SYMBOLS = frozenset({",", "{", "}"})
GITHUB_APPROVED_MATH_ENVIRONMENTS = frozenset({"aligned"})
MATH_MACRO_ARITY = {
    "boldsymbol": 1,
    "frac": 2,
    "left": 1,
    "mathbb": 1,
    "mathbf": 1,
    "mathcal": 1,
    "mathrm": 1,
    "mathsf": 1,
    "right": 1,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def markdown_paths(root: Path = ROOT) -> list[Path]:
    """Return source Markdown candidates, excluding generated build outputs."""

    paths: list[Path] = []
    for path in root.rglob("*.md"):
        relative = path.relative_to(root)
        if any(
            part in SKIPPED_DIRECTORY_NAMES or part.endswith(".egg-info")
            for part in relative.parts
        ):
            continue
        paths.append(path)
    return sorted(
        paths,
        key=lambda item: item.relative_to(root).as_posix().encode("utf-8"),
    )


def is_style_checked(path: Path, *, root: Path = ROOT) -> bool:
    """Grandfather presentation only while one exact preserved digest matches."""

    relative = path.relative_to(root).as_posix()
    if relative in NON_NARRATIVE_MARKDOWN:
        return False
    expected = PRESERVED_PRESENTATION_SHA256.get(relative)
    return expected is None or sha256_bytes(path.read_bytes()) != expected


def mask_inline_code(line: str) -> str:
    """Replace inline-code spans with spaces while preserving line length."""

    return re.sub(
        r"(`+)([^\r\n]*?)\1",
        lambda match: " " * len(match.group(0)),
        line,
    )


def mask_inline_math(line: str) -> str:
    """Mask balanced inline math so table bars are not treated as separators."""

    return re.sub(
        r"(?<!\\)\$.*?(?<!\\)\$",
        lambda match: " " * len(match.group(0)),
        line,
    )


def math_contexts(text: str) -> list[tuple[int, str]]:
    """Return each active inline span or fenced math block with its first line."""

    contexts: list[tuple[int, str]] = []
    fence_marker: str | None = None
    fence_length = 0
    fence_info = ""
    fence_first_content_line = 0
    fence_content: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        match = FENCE.match(line)
        if fence_marker is None:
            if match:
                marker = match.group(2)
                fence_marker = marker[0]
                fence_length = len(marker)
                fence_info = match.group(3).strip()
                fence_first_content_line = number + 1
                fence_content = []
                continue
            visible = mask_inline_code(line)
            contexts.extend(
                (number, inline.group(1))
                for inline in re.finditer(
                    r"(?<!\\)\$(.+?)(?<!\\)\$",
                    visible,
                )
            )
            continue

        close_pattern = (
            rf"^ {{0,3}}{re.escape(fence_marker)}"
            rf"{{{fence_length},}}[ \t]*$"
        )
        if re.match(close_pattern, line):
            if fence_info == "math":
                contexts.append(
                    (fence_first_content_line, "\n".join(fence_content))
                )
            fence_marker = None
            fence_length = 0
            fence_info = ""
            fence_first_content_line = 0
            fence_content = []
        elif fence_info == "math":
            fence_content.append(line)
    return contexts


def github_math_macro_failures(text: str, *, relative: str) -> list[str]:
    """Reject active macros outside the repository's rendered-and-reviewed set."""

    failures: list[str] = []
    for first_line, context in math_contexts(text):
        for match in re.finditer(r"\\([A-Za-z]+|[^A-Za-z\r\n])", context):
            command = match.group(1)
            number = first_line + context[: match.start()].count("\n")
            if command[0].isalpha() and command not in GITHUB_APPROVED_MATH_MACROS:
                guidance = (
                    "observed GitHub renderer rejection"
                    if command == "operatorname"
                    else "not in the reviewed renderer-safe command set"
                )
                failures.append(
                    f"{relative}:{number}: unapproved GitHub math macro "
                    f"\\{command}: {guidance}"
                )
            elif (
                not command[0].isalpha()
                and command not in GITHUB_APPROVED_MATH_CONTROL_SYMBOLS
            ):
                failures.append(
                    f"{relative}:{number}: unapproved GitHub math control symbol "
                    f"\\{command}: not in the reviewed renderer-safe symbol set"
                )

        environment_stack: list[tuple[str, int]] = []
        for match in re.finditer(
            r"\\(begin|end)\{([^{}\r\n]+)\}",
            context,
        ):
            action, environment = match.groups()
            number = first_line + context[: match.start()].count("\n")
            if environment not in GITHUB_APPROVED_MATH_ENVIRONMENTS:
                failures.append(
                    f"{relative}:{number}: unapproved GitHub math environment "
                    f"{environment}: not in the reviewed renderer-safe environment set"
                )
            if action == "begin":
                environment_stack.append((environment, number))
            elif not environment_stack:
                failures.append(
                    f"{relative}:{number}: unmatched math environment end: "
                    f"{environment}"
                )
            elif environment_stack[-1][0] != environment:
                opened, opened_line = environment_stack.pop()
                failures.append(
                    f"{relative}:{number}: math environment {opened} opened at "
                    f"line {opened_line} closes as {environment}"
                )
            else:
                environment_stack.pop()
        for environment, number in environment_stack:
            failures.append(
                f"{relative}:{number}: unclosed math environment: {environment}"
            )
        failures.extend(
            github_math_structure_failures(
                context,
                relative=relative,
                first_line=first_line,
            )
        )
    return failures


def _math_line(first_line: int, context: str, index: int) -> int:
    return first_line + context[:index].count("\n")


def _skip_math_argument(context: str, index: int) -> int | None:
    """Return the first byte after one TeX argument, or None when absent."""

    while index < len(context) and context[index].isspace():
        index += 1
    if index >= len(context) or context[index] == "}":
        return None
    if context[index] == "{":
        depth = 1
        cursor = index + 1
        while cursor < len(context):
            if context[cursor] == "\\":
                cursor += 2
                continue
            if context[cursor] == "{":
                depth += 1
            elif context[cursor] == "}":
                depth -= 1
                if depth == 0:
                    return cursor + 1
            cursor += 1
        return None
    if context[index] == "\\":
        cursor = index + 1
        if cursor >= len(context):
            return None
        if context[cursor].isalpha():
            while cursor < len(context) and context[cursor].isalpha():
                cursor += 1
            return cursor
        return cursor + 1
    return index + 1


def github_math_structure_failures(
    context: str,
    *,
    relative: str,
    first_line: int,
) -> list[str]:
    """Reject malformed active math even when every command name is approved."""

    failures: list[str] = []
    brace_stack: list[int] = []
    cursor = 0
    while cursor < len(context):
        if context[cursor] == "\\":
            cursor += 2
            continue
        if context[cursor] == "{":
            brace_stack.append(cursor)
        elif context[cursor] == "}":
            if brace_stack:
                brace_stack.pop()
            else:
                failures.append(
                    f"{relative}:{_math_line(first_line, context, cursor)}: "
                    "unmatched math closing brace"
                )
        cursor += 1
    for index in brace_stack:
        failures.append(
            f"{relative}:{_math_line(first_line, context, index)}: "
            "unclosed math brace"
        )

    commands = list(re.finditer(r"\\([A-Za-z]+)", context))
    for command_match in commands:
        command = command_match.group(1)
        number = _math_line(first_line, context, command_match.start())
        after = command_match.end()
        if command in {"begin", "end"}:
            environment = re.match(r"\{([^{}\r\n]+)\}", context[after:])
            if environment is None:
                failures.append(
                    f"{relative}:{number}: \\{command} requires an immediate "
                    "braced math environment"
                )
            continue
        arity = MATH_MACRO_ARITY.get(command)
        if arity is None:
            continue
        argument_cursor = after
        for ordinal in range(1, arity + 1):
            argument_cursor = _skip_math_argument(context, argument_cursor)
            if argument_cursor is None:
                failures.append(
                    f"{relative}:{number}: \\{command} requires "
                    f"{arity} math argument{'s' if arity != 1 else ''}; "
                    f"argument {ordinal} is missing or unclosed"
                )
                break

    delimiter_stack: list[int] = []
    for delimiter in re.finditer(r"\\(left|right)\b", context):
        action = delimiter.group(1)
        number = _math_line(first_line, context, delimiter.start())
        if action == "left":
            delimiter_stack.append(number)
        elif delimiter_stack:
            delimiter_stack.pop()
        else:
            failures.append(
                f"{relative}:{number}: unmatched \\right math delimiter"
            )
    for number in delimiter_stack:
        failures.append(f"{relative}:{number}: unclosed \\left math delimiter")

    begin_aligned = re.compile(r"\\begin\{aligned\}")
    end_aligned = re.compile(r"\\end\{aligned\}")
    for ampersand in re.finditer(r"(?<!\\)&", context):
        prefix = context[: ampersand.start()]
        if len(begin_aligned.findall(prefix)) <= len(end_aligned.findall(prefix)):
            number = _math_line(first_line, context, ampersand.start())
            failures.append(
                f"{relative}:{number}: math alignment '&' is allowed only "
                "inside an aligned environment"
            )
    return failures


def mask_security_math(
    visible: list[tuple[int, str]],
) -> list[tuple[int, str]]:
    """Mask current and preserved legacy math before local-path inspection."""

    masked: list[tuple[int, str]] = []
    legacy_display = False
    for number, line in visible:
        stripped = line.strip()
        if legacy_display:
            masked.append((number, " " * len(line)))
            if stripped == r"\]":
                legacy_display = False
            continue
        if stripped == r"\[":
            legacy_display = True
            masked.append((number, " " * len(line)))
            continue
        current = mask_inline_math(line)
        current = re.sub(
            r"\\\(.*?\\\)",
            lambda match: " " * len(match.group(0)),
            current,
        )
        masked.append((number, current))
    return masked


def visible_lines(text: str, *, name: str) -> tuple[list[tuple[int, str]], list[str]]:
    """Return non-fenced Markdown lines with inline code masked."""

    visible: list[tuple[int, str]] = []
    failures: list[str] = []
    fence_marker: str | None = None
    fence_length = 0
    fence_line = 0
    fence_info = ""
    fence_has_content = False

    for number, line in enumerate(text.splitlines(), start=1):
        match = FENCE.match(line)
        if fence_marker is None:
            if match:
                marker = match.group(2)
                fence_marker = marker[0]
                fence_length = len(marker)
                fence_line = number
                fence_info = match.group(3).strip()
                fence_has_content = False
                info_tokens = fence_info.split()
                if (
                    info_tokens
                    and info_tokens[0].casefold() == "math"
                    and fence_info != "math"
                ):
                    failures.append(
                        f"{name}:{number}: math fence language must be exactly 'math'"
                    )
                visible.append((number, " " * len(line)))
                continue
            visible.append((number, mask_inline_code(line)))
            continue

        close_pattern = rf"^ {{0,3}}{re.escape(fence_marker)}{{{fence_length},}}[ \t]*$"
        if re.match(close_pattern, line):
            if fence_info == "math" and not fence_has_content:
                failures.append(f"{name}:{fence_line}: math fence is empty")
            fence_marker = None
            fence_length = 0
            fence_line = 0
            fence_info = ""
            fence_has_content = False
        elif line.strip():
            fence_has_content = True
        visible.append((number, " " * len(line)))

    if fence_marker is not None:
        failures.append(f"{name}:{fence_line}: unclosed fenced block")
    return visible, failures


def _parse_destination(source: str, start: int = 0) -> tuple[str, int]:
    """Parse one Markdown destination with balanced parentheses or angle brackets."""

    index = start
    while index < len(source) and source[index].isspace():
        index += 1
    if index >= len(source):
        return "", index
    if source[index] == "<":
        end = index + 1
        while end < len(source):
            if source[end] == ">" and source[end - 1] != "\\":
                return source[index + 1 : end], end + 1
            end += 1
        return source[index + 1 :], len(source)

    destination: list[str] = []
    depth = 0
    escaped = False
    while index < len(source):
        character = source[index]
        if escaped:
            destination.append(character)
            escaped = False
        elif character == "\\":
            destination.append(character)
            escaped = True
        elif character == "(":
            depth += 1
            destination.append(character)
        elif character == ")":
            if depth == 0:
                break
            depth -= 1
            destination.append(character)
        elif character.isspace() and depth == 0:
            break
        else:
            destination.append(character)
        index += 1
    return "".join(destination), index


def _inline_destination_is_closed(source: str, index: int) -> bool:
    """Accept an outer close after a destination and optional Markdown title."""

    cursor = index
    while cursor < len(source) and source[cursor].isspace():
        cursor += 1
    if cursor < len(source) and source[cursor] == ")":
        return True
    if cursor >= len(source) or source[cursor] not in {'"', "'", "("}:
        return False
    opener = source[cursor]
    closer = ")" if opener == "(" else opener
    cursor += 1
    escaped = False
    while cursor < len(source):
        character = source[cursor]
        if escaped:
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == closer:
            cursor += 1
            break
        cursor += 1
    else:
        return False
    while cursor < len(source) and source[cursor].isspace():
        cursor += 1
    return cursor < len(source) and source[cursor] == ")"


def inline_link_targets(line: str) -> tuple[list[str], bool]:
    """Extract inline destinations and report any missing outer close."""

    targets: list[str] = []
    malformed = False
    start = 0
    while True:
        marker = line.find("](", start)
        if marker < 0:
            return targets, malformed
        backslashes = 0
        cursor = marker - 1
        while cursor >= 0 and line[cursor] == "\\":
            backslashes += 1
            cursor -= 1
        if backslashes % 2 == 0:
            target, end = _parse_destination(line, marker + 2)
            if target:
                targets.append(target)
            if not _inline_destination_is_closed(line, end):
                malformed = True
        start = marker + 2


def reference_links(
    visible: list[tuple[int, str]],
) -> tuple[
    dict[str, tuple[int, str]],
    list[tuple[int, str]],
    list[tuple[int, str]],
]:
    definitions: dict[str, tuple[int, str]] = {}
    usages: list[tuple[int, str]] = []
    issues: list[tuple[int, str]] = []
    for number, line in visible:
        definition = REFERENCE_DEFINITION.match(line)
        if definition:
            label = " ".join(definition.group(1).split()).casefold()
            target, _end = _parse_destination(definition.group(2))
            if label in definitions:
                issues.append((number, f"duplicate reference definition: [{label}]"))
            elif not target:
                issues.append((number, f"empty reference definition: [{label}]"))
            else:
                definitions[label] = (number, target)
            continue
        for usage in REFERENCE_USAGE.finditer(line):
            label = usage.group(2) or usage.group(1)
            usages.append((number, " ".join(label.split()).casefold()))
    return definitions, usages, issues


def split_table_row(line: str) -> list[str]:
    """Split a GFM table row, ignoring escaped pipes and masked inline syntax."""

    source = mask_inline_math(line.strip())
    cells: list[str] = []
    cell: list[str] = []
    escaped = False
    for character in source:
        if escaped:
            cell.append(character)
            escaped = False
        elif character == "\\":
            cell.append(character)
            escaped = True
        elif character == "|":
            cells.append("".join(cell).strip())
            cell = []
        else:
            cell.append(character)
    cells.append("".join(cell).strip())
    if source.startswith("|"):
        cells = cells[1:]
    if source.endswith("|") and cells:
        cells = cells[:-1]
    return cells


def table_failures(
    visible: list[tuple[int, str]],
    *,
    relative: str,
) -> list[str]:
    failures: list[str] = []
    index = 0
    while index + 1 < len(visible):
        header_number, header = visible[index]
        separator_number, separator = visible[index + 1]
        separator_cells = split_table_row(separator)
        is_separator = (
            len(separator_cells) >= 2
            and all(TABLE_SEPARATOR_CELL.fullmatch(cell) for cell in separator_cells)
        )
        if not is_separator:
            index += 1
            continue
        header_cells = split_table_row(header)
        expected = len(separator_cells)
        if len(header_cells) != expected:
            failures.append(
                f"{relative}:{separator_number}: table header has "
                f"{len(header_cells)} columns but separator has {expected}"
            )
        index += 2
        while index < len(visible):
            number, row = visible[index]
            if not row.strip() or "|" not in row:
                break
            cells = split_table_row(row)
            if len(cells) != expected:
                failures.append(
                    f"{relative}:{number}: table row has {len(cells)} columns; "
                    f"expected {expected} from line {separator_number}"
                )
            index += 1
    return failures


def github_heading_anchors(path: Path) -> set[str]:
    """Approximate GitHub's documented heading IDs for local-fragment validation."""

    text = path.read_text(encoding="utf-8")
    visible, _failures = visible_lines(text, name=path.as_posix())
    raw_lines = text.splitlines()
    anchors: set[str] = set(
        re.findall(r"<a\s+(?:name|id)=[\"']([^\"']+)[\"']", text, re.IGNORECASE)
    )
    counts: dict[str, int] = {}
    for number, masked in visible:
        if not ATX_HEADING.match(masked):
            continue
        match = ATX_HEADING_TEXT.match(raw_lines[number - 1])
        if not match:
            continue
        heading = match.group(1)
        heading = re.sub(r"`([^`]*)`", r"\1", heading)
        heading = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", heading)
        heading = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", heading)
        heading = re.sub(r"<[^>]+>", "", heading)
        slug = "".join(
            character
            for character in heading.casefold()
            if character.isalnum() or character in {" ", "-", "_"}
        )
        slug = re.sub(r"\s+", "-", slug.strip())
        suffix = counts.get(slug, 0)
        counts[slug] = suffix + 1
        anchors.add(slug if suffix == 0 else f"{slug}-{suffix}")
    return anchors


def _local_target(target: str) -> tuple[str, str] | None:
    candidate = target.strip()
    if candidate.startswith("<") and candidate.endswith(">"):
        candidate = candidate[1:-1].strip()
    if not candidate:
        return None
    parsed = urlsplit(candidate)
    if parsed.scheme or parsed.netloc:
        return None
    return unquote(parsed.path), unquote(parsed.fragment)


def _within_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def validate_local_link(
    *,
    raw_target: str,
    number: int,
    source: Path,
    root: Path,
    relative: str,
    anchor_cache: dict[Path, set[str]],
) -> list[str]:
    failures: list[str] = []
    local = _local_target(raw_target)
    if local is None:
        return failures
    target, fragment = local
    if target.startswith(("/", "\\")) or WINDOWS_ABSOLUTE_PATH.match(target):
        return [
            f"{relative}:{number}: local link uses an absolute path: {raw_target}"
        ]
    resolved = source if not target else (source.parent / target).resolve()
    root_resolved = root.resolve()
    if not _within_root(resolved, root_resolved):
        return [f"{relative}:{number}: local link escapes the repository: {raw_target}"]
    if not resolved.exists():
        return [f"{relative}:{number}: broken local link: {raw_target}"]
    if fragment and resolved.suffix.casefold() == ".md":
        anchors = anchor_cache.setdefault(resolved, github_heading_anchors(resolved))
        if fragment.casefold() not in anchors:
            failures.append(
                f"{relative}:{number}: missing Markdown anchor "
                f"#{fragment} in {resolved.relative_to(root_resolved).as_posix()}"
            )
    return failures


def check_markdown(
    path: Path,
    *,
    root: Path = ROOT,
    check_style: bool = True,
) -> list[str]:
    """Return documentation failures for one Markdown file."""

    failures: list[str] = []
    relative = path.relative_to(root).as_posix()
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        failures.append(f"{relative}: UTF-8 byte-order mark is prohibited")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        return [f"{relative}: invalid UTF-8 at byte {exc.start}"]

    for index, character in enumerate(text):
        codepoint = ord(character)
        if (codepoint < 0x20 and character not in "\t\n\r") or codepoint == 0x7F:
            failures.append(
                f"{relative}: prohibited control U+{codepoint:04X} at character {index}"
            )
        elif codepoint in PROHIBITED_FORMAT_CODEPOINTS:
            failures.append(
                f"{relative}: prohibited invisible/bidi character U+{codepoint:04X} "
                f"at character {index}"
            )

    visible, fence_failures = visible_lines(text, name=relative)
    failures.extend(fence_failures)
    visible_text = "\n".join(line for _number, line in visible)
    security_visible = mask_security_math(visible)
    security_text = "\n".join(line for _number, line in security_visible)

    # Security, privacy, and link hygiene apply even to presentation-preserved files.
    if UNSAFE_HTML.search(security_text):
        failures.append(f"{relative}: active form or embedded HTML is prohibited")
    if UNSAFE_SCHEME.search(security_text):
        failures.append(f"{relative}: unsafe URI scheme is prohibited")
    if WINDOWS_ABSOLUTE_PATH.search(security_text) or UNIX_PRIVATE_PATH.search(
        security_text
    ):
        failures.append(f"{relative}: local absolute path is prohibited")
    if re.search(r"(?<![A-Za-z0-9+.-])http://", security_text, re.IGNORECASE):
        failures.append(f"{relative}: external links must use HTTPS")
    for number, line in security_visible:
        if re.search(r"!\[\s*\]\(", line):
            failures.append(f"{relative}:{number}: image alt text is empty")

    if check_style:
        headings: list[tuple[int, int]] = []
        for number, line in visible:
            heading = ATX_HEADING.match(line)
            if heading:
                headings.append((number, len(heading.group(1))))
            if SETEXT_EQUALS.match(line):
                failures.append(
                    f"{relative}:{number}: Setext '=' headings are prohibited; "
                    "use ATX headings or a fenced math block"
                )
            for token, label in RAW_MATH_DELIMITERS:
                if token in line:
                    failures.append(f"{relative}:{number}: {label}: {token}")
            if "$$" in line:
                failures.append(
                    f"{relative}:{number}: display math must use a fenced 'math' block"
                )
            unescaped_dollars = re.findall(r"(?<!\\)\$", line)
            if len(unescaped_dollars) % 2:
                failures.append(f"{relative}:{number}: unbalanced inline '$' delimiter")

        h1_lines = [number for number, level in headings if level == 1]
        if len(h1_lines) != 1:
            failures.append(
                f"{relative}: expected exactly one top-level heading; "
                f"found {len(h1_lines)}"
            )
        for (previous_line, previous), (number, level) in zip(headings, headings[1:]):
            if level > previous + 1:
                failures.append(
                    f"{relative}:{number}: heading jumps from h{previous} "
                    f"at line {previous_line} to h{level}"
                )
        failures.extend(table_failures(visible, relative=relative))
        failures.extend(github_math_macro_failures(text, relative=relative))

        if relative == "docs/SHARING_GUIDE.md" and re.search(
            r"\ball\s+\d+\s+(?:assets?|files?)\b",
            visible_text,
            re.IGNORECASE,
        ):
            failures.append(
                f"{relative}: release acceptance must use semantic roles, "
                "not a magic asset count"
            )
        if re.search(
            r"\bthe\s+v0\.2\s+`?atomic`?\s+command\b",
            visible_text,
            re.IGNORECASE,
        ):
            failures.append(f"{relative}: stale atomic-route version wording")

    anchor_cache: dict[Path, set[str]] = {}
    definitions, usages, reference_issues = reference_links(security_visible)
    for number, issue in reference_issues:
        failures.append(f"{relative}:{number}: {issue}")
    for label, (number, target) in definitions.items():
        failures.extend(
            validate_local_link(
                raw_target=target,
                number=number,
                source=path,
                root=root,
                relative=relative,
                anchor_cache=anchor_cache,
            )
        )
    for number, label in usages:
        if label not in definitions:
            failures.append(
                f"{relative}:{number}: undefined reference-style link: [{label}]"
            )
    for number, line in security_visible:
        targets, malformed = inline_link_targets(line)
        if malformed:
            failures.append(
                f"{relative}:{number}: malformed inline link destination"
            )
        for raw_target in targets:
            failures.extend(
                validate_local_link(
                    raw_target=raw_target,
                    number=number,
                    source=path,
                    root=root,
                    relative=relative,
                    anchor_cache=anchor_cache,
                )
            )

    return failures


def documentation_failures(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    for path in markdown_paths(root):
        relative = path.relative_to(root).as_posix()
        expected_preserved = PRESERVED_PRESENTATION_SHA256.get(relative)
        observed = sha256_bytes(path.read_bytes())
        if expected_preserved is not None and observed != expected_preserved:
            failures.append(
                f"{relative}: preserved presentation digest changed; "
                f"expected {expected_preserved}, found {observed}"
            )
        failures.extend(
            check_markdown(
                path,
                root=root,
                check_style=is_style_checked(path, root=root),
            )
        )
    return sorted(set(failures))


def main() -> int:
    failures = documentation_failures()
    payload = {
        "decision": "pass" if not failures else "blocked",
        "scope": {
            "all_markdown": (
                "UTF-8, controls, links, unsafe markup and schemes, local paths, "
                "HTTPS, and image alt text"
            ),
            "current_normative_markdown": (
                "math delimiters plus approved commands, control symbols, and "
                "environments; exact one-h1 structure, heading order, tables, "
                "and authority wording"
            ),
            "presentation_preserved_by_exact_sha256": sorted(
                PRESERVED_PRESENTATION_SHA256
            ),
        },
        "checks_run": [
            "strict_utf8",
            "control_and_bidi_rejection",
            "balanced_fences",
            "github_math_delimiters",
            "approved_github_math_commands_symbols_and_environments",
            "heading_structure",
            "table_structure",
            "inline_and_reference_link_integrity",
            "local_anchor_integrity",
            "unsafe_html_and_uri_rejection",
            "local_path_rejection",
            "https_external_links",
            "image_alt_text",
            "semantic_release_roster_wording",
            "preserved_presentation_digest_binding",
        ],
        "findings": failures,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
