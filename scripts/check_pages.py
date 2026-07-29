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
        self.alternates: list[tuple[str, str]] = []
        self.links: list[tuple[str, str]] = []
        self.duplicate_attributes: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        seen_attributes: set[str] = set()
        for name, _value in attrs:
            normalized_name = name.lower()
            if normalized_name in seen_attributes:
                self.duplicate_attributes.append((tag, normalized_name))
            seen_attributes.add(normalized_name)
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
        elif tag == "link" and values.get("rel") == "alternate":
            self.alternates.append((values.get("hreflang", ""), values.get("href", "")))
        elif tag == "a" and values.get("href"):
            self.links.append((values.get("hreflang", ""), values["href"]))
        elif tag == "meta" and values.get("http-equiv", "").lower() == "content-security-policy":
            self.csp = values.get("content")


def verify_pages() -> list[str]:
    failures = write_site(PAGES, check=True)
    required = {
        ".nojekyll",
        "README.md",
        "app.js",
        "index.html",
        "ja.html",
        "locale-en.js",
        "locale-ja.js",
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
    if workflow.count("python scripts/verify.py pages") != 1:
        failures.append(
            "Pages workflow must pass the complete Pages verification profile before upload"
        )
    post_deploy_tokens = (
        "protocol_meta_sha256: ${{ steps.pages-metadata.outputs.sha256 }}",
        "protocol_version: ${{ steps.pages-metadata.outputs.version }}",
        "EXPECTED_META_SHA256: ${{ needs.build.outputs.protocol_meta_sha256 }}",
        "EXPECTED_VERSION: ${{ needs.build.outputs.protocol_version }}",
        '"${base}" -o /tmp/bsc-index.html',
        '"${base}ja.html" -o /tmp/bsc-ja.html',
        '"${base}protocol/meta.js" -o /tmp/bsc-protocol-meta.js',
        '\\"version\\":\\"${EXPECTED_VERSION}\\"',
        "sha256sum --check --strict",
    )
    if any(workflow.count(token) != 1 for token in post_deploy_tokens):
        failures.append("Pages workflow must smoke-test deployed English, Japanese, and exact protocol metadata")

    page_contracts = {
        "index.html": ("en", "locale-en.js", ("ja", "ja.html")),
        "ja.html": ("ja", "locale-ja.js", ("en", "index.html")),
    }
    parsed_pages: dict[str, PageParser] = {}
    required_csp = {"default-src 'self'", "script-src 'self'", "connect-src 'self'", "object-src 'none'", "form-action 'none'"}
    required_controls = {
        "target-files", "copy-prompt", "download-prompt", "protocol-sha", "toggle-demo",
        "return-json", "return-json-file", "return-artifacts", "inspect-return", "return-result",
    }
    expected_alternates = {("en", "index.html"), ("ja", "ja.html"), ("x-default", "index.html")}
    gpt_url = "https://chatgpt.com/g/g-6a601b1f576881918e659b363ed3063f-bsc-claim-auditor"
    for filename, (language, locale_script, switch_link) in page_contracts.items():
        parser = PageParser()
        html = (PAGES / filename).read_text(encoding="utf-8")
        parser.feed(html)
        parsed_pages[filename] = parser
        label = f"packet builder {filename}"
        if parser.html_lang != language:
            failures.append(f"{label} must declare lang={language}")
        if parser.h1_count != 1:
            failures.append(f"{label} must contain exactly one h1")
        if len(parser.ids) != len(set(parser.ids)):
            failures.append(f"{label} contains duplicate element ids")
        if parser.duplicate_attributes:
            failures.append(f"{label} contains duplicate HTML attributes: {parser.duplicate_attributes}")
        controls_requiring_labels = {
            values["id"]
            for tag, values in parser.controls
            if values.get("id") and not (tag == "input" and values.get("type") == "radio")
        }
        if not controls_requiring_labels <= set(parser.labels):
            failures.append(f"{label} contains an unlabeled form control")
        controls_by_id = {values.get("id"): values for _tag, values in parser.controls if values.get("id")}
        for identifier in ("material", "return-json"):
            control = controls_by_id.get(identifier, {})
            if control.get("spellcheck") != "false" or any(
                control.get(attribute) != "off" for attribute in ("autocomplete", "autocorrect", "autocapitalize")
            ):
                failures.append(f"sensitive textarea must disable browser writing assistance in {filename}: {identifier}")
        expected_scripts = ["protocol/meta.js", "profile.js", locale_script, "return-desk-core.js", "app.js"]
        if parser.scripts != expected_scripts or parser.stylesheets != ["styles.css"]:
            failures.append(f"{label} loads an unexpected script or stylesheet")
        if not parser.csp or not required_csp <= {item.strip() for item in parser.csp.split(";") if item.strip()}:
            failures.append(f"{label} content-security policy is incomplete")
        if not required_controls <= set(parser.ids):
            failures.append(f"{label} is missing accessibility controls: {sorted(required_controls - set(parser.ids))}")
        if set(parser.alternates) != expected_alternates:
            failures.append(f"{label} language alternates differ from the reviewed English/Japanese routes")
        if switch_link not in parser.links:
            failures.append(f"{label} is missing its visible language switch")
        if ("", gpt_url) not in parser.links or html.find(gpt_url) > html.find('class="tabs"'):
            failures.append(f"{label} must present the official BSC Claim Auditor before compatible-model tabs")
        if f'href="{gpt_url}" target="_blank" rel="noopener noreferrer"' not in html:
            failures.append(f"{label} official BSC Claim Auditor link must open safely in a new tab")
        if filename == "ja.html" and not re.search(r"[\u3040-\u30ff\u3400-\u9fff]", html):
            failures.append("Japanese packet builder contains no Japanese text")

    if set(parsed_pages["index.html"].ids) != set(parsed_pages["ja.html"].ids):
        failures.append("English and Japanese packet builders expose different element IDs")
    machine_attributes = {
        "id", "type", "name", "value", "rows", "maxlength", "multiple", "checked", "readonly", "accept",
        "spellcheck", "autocomplete", "autocorrect", "autocapitalize", "aria-describedby",
    }
    def control_contracts(parser: PageParser) -> list[tuple[str, tuple[tuple[str, str], ...]]]:
        return [
            (tag, tuple(sorted((key, value) for key, value in values.items() if key in machine_attributes)))
            for tag, values in parser.controls
        ]
    if control_contracts(parsed_pages["index.html"]) != control_contracts(parsed_pages["ja.html"]):
        failures.append("English and Japanese form controls differ in machine-significant attributes")

    def read_locale(path: Path) -> dict[str, Any]:
        prefix = "\"use strict\";\n\nwindow.BSC_PAGE_LOCALE = Object.freeze("
        source = path.read_text(encoding="utf-8")
        if not source.startswith(prefix) or not source.endswith(");\n"):
            raise ValueError(f"locale catalog wrapper is malformed: {path.name}")
        return json.loads(source[len(prefix) : -3])

    try:
        english_locale = read_locale(PAGES / "locale-en.js")
        japanese_locale = read_locale(PAGES / "locale-ja.js")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(str(exc))
        english_locale = {"strings": {}}
        japanese_locale = {"strings": {}}
    if (english_locale.get("code"), english_locale.get("report_language")) != ("en", "en"):
        failures.append("English locale identity or report language is malformed")
    if (japanese_locale.get("code"), japanese_locale.get("report_language")) != ("ja", "ja-JP"):
        failures.append("Japanese locale identity or report language is malformed")
    english_strings = english_locale.get("strings", {})
    japanese_strings = japanese_locale.get("strings", {})
    if not isinstance(english_strings, dict) or not isinstance(japanese_strings, dict) or set(english_strings) != set(japanese_strings):
        failures.append("English and Japanese runtime locale keys differ")
    else:
        placeholder_pattern = re.compile(r"\{([A-Za-z0-9_]+)\}")
        for key in english_strings:
            if not isinstance(english_strings[key], str) or not isinstance(japanese_strings[key], str):
                failures.append(f"runtime locale value is not text: {key}")
                continue
            if set(placeholder_pattern.findall(english_strings[key])) != set(placeholder_pattern.findall(japanese_strings[key])):
                failures.append(f"runtime locale placeholders differ: {key}")
            if any(marker in english_strings[key] or marker in japanese_strings[key] for marker in ("<script", "</", "javascript:")):
                failures.append(f"runtime locale contains markup or script syntax: {key}")

    runtime_finding_codes = set(re.findall(r'["\'](RETURN_[A-Z0-9_]+)["\']', (PAGES / "return-desk-core.js").read_text(encoding="utf-8")))
    english_explanations = english_locale.get("finding_explanations", {})
    japanese_explanations = japanese_locale.get("finding_explanations", {})
    if english_explanations != {}:
        failures.append("English finding explanations must remain empty so canonical core text is used")
    if not isinstance(japanese_explanations, dict):
        failures.append("Japanese finding explanations must be an object")
    elif set(japanese_explanations) != runtime_finding_codes:
        failures.append(
            "Japanese finding explanations must cover the exact Return Desk finding-code set; "
            f"missing={sorted(runtime_finding_codes - set(japanese_explanations))}; "
            f"extra={sorted(set(japanese_explanations) - runtime_finding_codes)}"
        )
    else:
        for code, explanation in japanese_explanations.items():
            if not isinstance(explanation, str) or not explanation.strip():
                failures.append(f"Japanese finding explanation is empty: {code}")
            elif not re.search(r"[\u3040-\u30ff\u3400-\u9fff]", explanation):
                failures.append(f"Japanese finding explanation contains no Japanese text: {code}")
            elif any(marker in explanation for marker in ("<script", "</", "javascript:")):
                failures.append(f"Japanese finding explanation contains markup or script syntax: {code}")

    javascript = (PAGES / "app.js").read_text(encoding="utf-8")
    return_core = (PAGES / "return-desk-core.js").read_text(encoding="utf-8")
    locale_sources = [
        (PAGES / "locale-en.js").read_text(encoding="utf-8"),
        (PAGES / "locale-ja.js").read_text(encoding="utf-8"),
    ]
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
        if token in javascript or token in return_core or any(token in source for source in locale_sources):
            failures.append(f"packet builder uses forbidden browser capability: {token}")
    if javascript.count("fetch(") != 1 or "fetch(meta.path" not in javascript:
        failures.append("packet builder network access must be limited to its same-origin protocol fetch")
    for token in ("crypto.subtle.digest", "navigator.clipboard", "textContent", "replaceChildren"):
        if token not in javascript:
            failures.append(f"packet builder expected safe browser behavior is missing: {token}")
    literal_locale_keys = set(re.findall(r'\bt\("([A-Za-z0-9_]+)"', javascript))
    dynamic_locale_keys = {
        "target_files_added_one", "target_files_added_many",
        "return_files_hashed_one", "return_files_hashed_many",
        "outcome_blocked", "outcome_needs_review", "outcome_consistent",
        "outcome_blocked_summary", "outcome_needs_review_summary", "outcome_consistent_summary",
        "finding_severity_blocked", "finding_severity_review", "finding_severity_info",
    }
    if isinstance(english_strings, dict) and set(english_strings) != literal_locale_keys | dynamic_locale_keys:
        failures.append(
            "runtime locale catalog differs from app.js references; "
            f"missing={sorted((literal_locale_keys | dynamic_locale_keys) - set(english_strings))}; "
            f"extra={sorted(set(english_strings) - (literal_locale_keys | dynamic_locale_keys))}"
        )
    for token in (
        'new TextDecoder("utf-8", { fatal: true }).decode(bytes)',
        "codePointLength(elements.material.value)",
        "const pasted = elements.material.value;",
        "const pastedHasCodePoints = pasted.length > 0;",
        "const pastedSatisfiesRequiredTarget = pasted.trim().length > 0;",
        "new TextEncoder().encode(pasted)",
        "state.protocol,",
        "Characters (Unicode code points)",
        "Human-readable report language:",
        "activeLocale().report_language",
        'canonicalMessage.lang = "en"',
        "JSON.stringify(state.returnInspection, null, 2)",
        "targetFilenameRecord",
        "validateTargetFilenames(acceptedFiles)",
        "name: file.name,",
        't("target_filename_unsafe"',
        't("target_filename_collision"',
    ):
        if token not in javascript:
            failures.append(f"Japanese locale or byte-preservation behavior is missing: {token}")
    if "file.text(" in javascript:
        failures.append("target text embedding must not use replacement-decoding File.text()")
    for token in ("elements.material.value.trim()", "state.protocol.trimEnd()"):
        if token in javascript:
            failures.append(f"packet-builder exact target or protocol text is transformed: {token}")
    if javascript.count(".normalize(") != 1 or 'const collisionKeySource = name.normalize("NFC");' not in javascript:
        failures.append("packet-builder Unicode normalization must occur exactly once for the filename collision key only")
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
        "return_limit_contract_unavailable",
    ):
        if token not in javascript:
            failures.append(f"browser cancellation or exact input binding is missing: {token}")

    css = (PAGES / "styles.css").read_text(encoding="utf-8")
    for token in (":focus-visible", ":lang(ja)", "prefers-reduced-motion", "forced-colors", "@media (max-width: 560px)"):
        if token not in css:
            failures.append(f"packet builder accessibility stylesheet is missing: {token}")
    if "@import" in css or re.search(r"url\(\s*['\"]?https?://", css, re.IGNORECASE):
        failures.append("packet builder must use local fonts and styles without external requests")

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
            "post_deploy_route_and_metadata_smoke",
            "duplicate_html_attribute_rejection",
            "form_label_and_heading_contract",
            "content_security_policy",
            "browser_capability_allowlist",
            "localized_finding_explanation_coverage",
            "keyboard_motion_contrast_contract",
        ],
        "findings": failures,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
