#!/usr/bin/env python3
"""Fail closed on the static packet builder's integrity and accessibility contract."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from build_publication_assets import ROOT, sha256_bytes, site_outputs, write_site


PAGES = ROOT / "pages"
EXPECTED_ACTION_PINS = [
    "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683",
    "actions/setup-python@42375524e23c412d93fb67b49958b491fce71c38",
    "actions/configure-pages@983d7736d9b0ae728b81ab479565c72886d7745b",
    "actions/upload-pages-artifact@7b1f4a764d45c48632c6b24a0339c27f5614fb0b",
    "actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e",
]


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.labels: list[str] = []
        self.controls: list[tuple[str, dict[str, str]]] = []
        self.h1_count = 0
        self.html_lang: str | None = None
        self.scripts: list[str] = []
        self.stylesheets: list[str] = []
        self.csp: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        if "id" in values:
            self.ids.append(values["id"])
        if tag == "html":
            self.html_lang = values.get("lang")
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "label" and values.get("for"):
            self.labels.append(values["for"])
        elif tag in {"input", "textarea", "select"}:
            self.controls.append((tag, values))
        elif tag == "script" and values.get("src"):
            self.scripts.append(values["src"])
        elif tag == "link" and values.get("rel") == "stylesheet":
            self.stylesheets.append(values.get("href", ""))
        elif tag == "meta" and values.get("http-equiv", "").lower() == "content-security-policy":
            self.csp = values.get("content")


def verify_pages() -> list[str]:
    failures = write_site(PAGES, check=True)
    required = {
        ".nojekyll",
        "README.md",
        "app.js",
        "index.html",
        "protocol/BSC_AUDIT_LLM_PACKET.md",
        "protocol/meta.js",
        "styles.css",
    }
    actual = {path.relative_to(PAGES).as_posix() for path in PAGES.rglob("*") if path.is_file()}
    if actual != required:
        failures.append("Pages directory contents do not exactly match the reviewed static surface")
    if any(path.is_symlink() for path in PAGES.rglob("*")):
        failures.append("Pages surface contains a symbolic link")

    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    observed_pins = re.findall(r"^\s*uses:\s*([^\s#]+)", workflow, re.MULTILINE)
    if observed_pins != EXPECTED_ACTION_PINS:
        failures.append("Pages workflow actions differ from the reviewed immutable pins")

    parser = PageParser()
    html = (PAGES / "index.html").read_text(encoding="utf-8")
    parser.feed(html)
    if parser.html_lang != "en":
        failures.append("packet builder must declare lang=en")
    if parser.h1_count != 1:
        failures.append("packet builder must contain exactly one h1")
    if len(parser.ids) != len(set(parser.ids)):
        failures.append("packet builder contains duplicate element ids")
    controls_requiring_labels = {
        values["id"]
        for tag, values in parser.controls
        if values.get("id") and not (tag == "input" and values.get("type") == "radio")
    }
    if not controls_requiring_labels <= set(parser.labels):
        failures.append("packet builder contains an unlabeled form control")
    if parser.scripts != ["protocol/meta.js", "app.js"] or parser.stylesheets != ["styles.css"]:
        failures.append("packet builder loads an unexpected script or stylesheet")
    required_csp = {"default-src 'self'", "script-src 'self'", "connect-src 'self'", "object-src 'none'", "form-action 'none'"}
    if not parser.csp or not required_csp <= {item.strip() for item in parser.csp.split(";") if item.strip()}:
        failures.append("packet builder content-security policy is incomplete")
    for token in ("target-files", "copy-prompt", "download-prompt", "protocol-sha", "toggle-demo"):
        if token not in parser.ids:
            failures.append(f"packet builder accessibility control is missing: {token}")

    javascript = (PAGES / "app.js").read_text(encoding="utf-8")
    forbidden = (
        "innerHTML",
        "outerHTML",
        "insertAdjacentHTML",
        "document.cookie",
        "localStorage",
        "sessionStorage",
        "sendBeacon",
        "WebSocket",
        "XMLHttpRequest",
    )
    for token in forbidden:
        if token in javascript:
            failures.append(f"packet builder uses forbidden browser capability: {token}")
    if javascript.count("fetch(") != 1 or "fetch(meta.path" not in javascript:
        failures.append("packet builder network access must be limited to its same-origin protocol fetch")
    for token in ("crypto.subtle.digest", "navigator.clipboard", "textContent", "replaceChildren"):
        if token not in javascript:
            failures.append(f"packet builder expected safe browser behavior is missing: {token}")

    css = (PAGES / "styles.css").read_text(encoding="utf-8")
    for token in (":focus-visible", "prefers-reduced-motion", "forced-colors", "@media (max-width: 560px)"):
        if token not in css:
            failures.append(f"packet builder accessibility stylesheet is missing: {token}")

    expected = site_outputs()
    protocol = expected[Path("protocol/BSC_AUDIT_LLM_PACKET.md")]
    metadata_text = expected[Path("protocol/meta.js")].decode("utf-8")
    match = re.search(r'"sha256":"([0-9a-f]{64})"', metadata_text)
    if not match or match.group(1) != sha256_bytes(protocol):
        failures.append("packet builder metadata does not bind the exact protocol bytes")
    return sorted(set(failures))


def main() -> int:
    failures = verify_pages()
    payload: dict[str, Any] = {
        "decision": "pass" if not failures else "blocked",
        "checks_run": [
            "generated_protocol_drift",
            "protocol_sha256_binding",
            "static_surface_allowlist",
            "workflow_action_pins",
            "form_label_and_heading_contract",
            "content_security_policy",
            "browser_capability_allowlist",
            "keyboard_motion_contrast_contract",
        ],
        "findings": failures,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
