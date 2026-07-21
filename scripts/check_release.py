#!/usr/bin/env python3
"""Fail closed on inexpensive release-integrity invariants."""

from __future__ import annotations

import json
import hashlib
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bsc_audit import __version__  # noqa: E402


def fail(message: str) -> None:
    raise SystemExit(f"release check failed: {message}")


def strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate key {key!r}")
        value[key] = item
    return value


def main() -> int:
    if len((ROOT / "LICENSE").read_text(encoding="utf-8").splitlines()) < 150:
        fail("LICENSE is not the complete Apache-2.0 text")

    for directory in ("examples", "templates", "schemas"):
        for path in sorted((ROOT / directory).glob("*.json")):
            try:
                json.loads(
                    path.read_text(encoding="utf-8"),
                    object_pairs_hook=strict_object,
                    parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
                )
            except (json.JSONDecodeError, ValueError) as exc:
                fail(f"{path.relative_to(ROOT)} is not strict JSON: {exc}")

    for markdown in sorted(path for path in ROOT.rglob("*.md") if not any(part in {"build", "dist", "release"} or part.endswith(".egg-info") for part in path.relative_to(ROOT).parts)):
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", markdown.read_text(encoding="utf-8")):
            target = target.split("#", 1)[0]
            if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE):
                continue
            if not (markdown.parent / target).resolve().exists():
                fail(f"broken local link in {markdown.relative_to(ROOT)}: {target}")

    html = (ROOT / "START_HERE.html").read_text(encoding="utf-8")
    if not re.search(r"<html[^>]+lang=[\"']en(?:-US)?[\"']", html, re.IGNORECASE):
        fail("START_HERE.html must declare an English document language")
    if len(re.findall(r"<h1(?:\s|>)", html, re.IGNORECASE)) != 1:
        fail("START_HERE.html must contain exactly one h1")
    if "focus-visible" not in (ROOT / "docs" / "starter.css").read_text(encoding="utf-8"):
        fail("starter stylesheet lacks visible keyboard focus")

    paper = ROOT / "research" / "Audit_Descent_Calculus.pdf"
    paper_hash = hashlib.sha256(paper.read_bytes()).hexdigest() if paper.is_file() else "missing"
    if paper_hash != "5b6690d4771e5624f79e5e834e485be9c94a2ca12255d4ef7efa1dda59a3203e":
        fail("research-note PDF is missing or differs from its declared release digest")

    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    public_version = __version__.replace("a", "-alpha.", 1)
    if f"version: {public_version}" not in citation:
        fail(f"CITATION.cff does not match package version {__version__}")

    print(f"release checks passed for {__version__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
