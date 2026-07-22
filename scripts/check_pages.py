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
    "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020",
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
        "profile.js",
        "protocol/BSC_AUDIT_LLM_PACKET.md",
        "protocol/meta.js",
        "return-desk-core.js",
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
    if workflow.count('node-version: "22.23.1"') != 1 or workflow.count("package-manager-cache: false") != 1:
        failures.append("Pages workflow Return Desk Node configuration differs from the toolchain lock")
    if workflow.count("node --test tests/return_desk_runtime.test.cjs") != 1:
        failures.append("Pages workflow must pass the Return Desk runtime suite before upload")

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
    controls_by_id = {values.get("id"): values for _tag, values in parser.controls if values.get("id")}
    for identifier in ("material", "return-json"):
        control = controls_by_id.get(identifier, {})
        if control.get("spellcheck") != "false" or any(
            control.get(attribute) != "off" for attribute in ("autocomplete", "autocorrect", "autocapitalize")
        ):
            failures.append(f"sensitive textarea must disable browser writing assistance: {identifier}")
    if parser.scripts != ["protocol/meta.js", "profile.js", "return-desk-core.js", "app.js"] or parser.stylesheets != ["styles.css"]:
        failures.append("packet builder loads an unexpected script or stylesheet")
    required_csp = {"default-src 'self'", "script-src 'self'", "connect-src 'self'", "object-src 'none'", "form-action 'none'"}
    if not parser.csp or not required_csp <= {item.strip() for item in parser.csp.split(";") if item.strip()}:
        failures.append("packet builder content-security policy is incomplete")
    for token in (
        "target-files",
        "copy-prompt",
        "download-prompt",
        "protocol-sha",
        "toggle-demo",
        "return-json",
        "return-json-file",
        "return-artifacts",
        "inspect-return",
        "return-result",
    ):
        if token not in parser.ids:
            failures.append(f"packet builder accessibility control is missing: {token}")

    javascript = (PAGES / "app.js").read_text(encoding="utf-8")
    return_core = (PAGES / "return-desk-core.js").read_text(encoding="utf-8")
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
        if token in javascript or token in return_core:
            failures.append(f"packet builder uses forbidden browser capability: {token}")
    if javascript.count("fetch(") != 1 or "fetch(meta.path" not in javascript:
        failures.append("packet builder network access must be limited to its same-origin protocol fetch")
    for token in ("crypto.subtle.digest", "navigator.clipboard", "textContent", "replaceChildren"):
        if token not in javascript:
            failures.append(f"packet builder expected safe browser behavior is missing: {token}")
    for token in (r"\p{Cc}", r"\p{Cf}", r"\p{Cs}", r"\p{Zl}", r"\p{Zp}"):
        if token not in javascript or token not in return_core:
            failures.append(f"filename control-category hardening is missing: {token}")
    if "window.BSC_AUDIT_PROFILE.audit_depths" not in javascript or "window.BSC_AUDIT_PROFILE.output_sections" not in javascript:
        failures.append("packet builder depth and output order must come from the canonical GPT profile")
    for token in (
        "parseStrictJson",
        "inspectReturn",
        "non_admissive_return_inspection",
        "needs_review",
        "consistent",
        "blocked",
        "MAX_RETURN_JSON_BYTES = 8 * 1024 * 1024",
        "utf8ByteLengthBounded",
        "RETURN_JSON_TOO_LARGE",
    ):
        if token not in return_core:
            failures.append(f"Audit Return Desk core contract is missing: {token}")
    if "verifyReturnContract(profile)" not in javascript or "contract: state.returnContract" not in javascript:
        failures.append("Audit Return Desk must verify and use the generated return contract")
    for token in (
        "fileEpoch",
        "packetInputEpoch",
        "packetGenerationEpoch",
        "processingPacket",
        "invalidatePacketPreview",
        'input[name="depth"]',
        "returnInspectionEpoch",
        'elements.returnJson.addEventListener("input"',
        "return_text_sha256",
        "artifact_descriptor_sha256",
        "canonicalReturnArtifactDescriptors",
        "returnTextBytes",
        "source-limit contract",
    ):
        if token not in javascript:
            failures.append(f"browser cancellation or exact input binding is missing: {token}")

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
    profile_text = expected[Path("profile.js")].decode("utf-8")
    profile_match = re.search(r'"profile_sha256":"([0-9a-f]{64})"', profile_text)
    profile_source = ROOT / "gpt" / "_source" / "GPT_PROFILE.json"
    if not profile_match or profile_match.group(1) != sha256_bytes(profile_source.read_bytes()):
        failures.append("packet builder metadata does not bind the exact GPT profile bytes")
    return_schema = ROOT / "schemas" / "audit-return-v0.1.schema.json"
    return_match = re.search(r'"schema_sha256":"([0-9a-f]{64})"', profile_text)
    if not return_schema.is_file() or not return_match or return_match.group(1) != sha256_bytes(return_schema.read_bytes()):
        failures.append("Audit Return Desk metadata does not bind the exact return schema bytes")
    core_schema_match = re.search(r'EXPECTED_SCHEMA_SHA256 = "([0-9a-f]{64})"', return_core)
    if not return_schema.is_file() or not core_schema_match or core_schema_match.group(1) != sha256_bytes(return_schema.read_bytes()):
        failures.append("Audit Return Desk runtime does not bind the exact return schema bytes")
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
