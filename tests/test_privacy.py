from __future__ import annotations

import tempfile
import unittest
import zipfile
import subprocess
from dataclasses import replace
from pathlib import Path
from unittest import mock

from scripts.check_privacy import (
    _noreply_email,
    load_policy,
    scan_docx,
    scan_documentation,
    scan_history,
    scan_pdf_bytes,
    scan_path,
    scan_protected_history,
    scan_text,
    scan_zip,
)


class PrivacyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = load_policy()

    def codes(self, findings):
        return {finding.code for finding in findings}

    def test_registered_project_identity_contract_is_exact(self) -> None:
        self.assertEqual(
            self.policy.project_identities,
            frozenset({"J. Tree", "Tree, J.", "jtree", "jkolantree", "tree"}),
        )

    def test_personal_email_fails_closed_without_echoing_it(self) -> None:
        secret = "person" + "@" + "example.com"
        findings = scan_text("fixture", secret, self.policy)
        self.assertIn("EMAIL_NOT_ALLOWLISTED", self.codes(findings))
        self.assertNotIn(secret, repr(findings))

    def test_github_bot_email_is_permitted(self) -> None:
        findings = scan_text("fixture", "41898282+github-actions[bot]@users.noreply.github.com", self.policy)
        self.assertNotIn("EMAIL_NOT_ALLOWLISTED", self.codes(findings))

    def test_project_commit_email_must_use_a_registered_noreply_handle(self) -> None:
        self.assertTrue(_noreply_email("J. Tree", "307349551+jkolantree@users.noreply.github.com", self.policy))
        self.assertTrue(_noreply_email("tree", "307349551+jkolantree@users.noreply.github.com", self.policy))
        unrelated = "unrelated" + "@" + "users.noreply.github.com"
        self.assertFalse(_noreply_email("J. Tree", unrelated, self.policy))
        self.assertFalse(_noreply_email("tree", unrelated, self.policy))

    def test_local_path_and_private_key_fail_closed(self) -> None:
        payload = "/" + "Users/alice/project\n-----BEGIN " + "PRIVATE KEY-----"
        findings = scan_text("fixture", payload, self.policy)
        self.assertIn("LOCAL_PATH_PRESENT", self.codes(findings))
        self.assertIn("PRIVATE_KEY", self.codes(findings))

    def test_forward_slash_windows_user_path_fails_closed(self) -> None:
        payload = "C:/" + "Us" + "ers/alice/private/record.json"
        findings = scan_text("fixture", payload, self.policy)
        self.assertIn("LOCAL_PATH_PRESENT", self.codes(findings))

    def test_json_escaped_windows_user_path_fails_closed(self) -> None:
        separator = "\\" * 2
        payload = (
            '{"path":"C:'
            + separator
            + "Us"
            + "ers"
            + separator
            + "alice"
            + separator
            + 'private.json"}'
        )
        findings = scan_text("fixture", payload, self.policy)
        self.assertIn("LOCAL_PATH_PRESENT", self.codes(findings))
        self.assertNotIn("alice", repr(findings))

    def test_temporary_path_fails_closed_except_registered_build_paths(self) -> None:
        private_path = "/" + "tmp/private-browser-profile/Default/Cookies"
        findings = scan_text("fixture", private_path, self.policy)
        self.assertIn("LOCAL_PATH_PRESENT", self.codes(findings))
        self.assertNotIn(private_path, repr(findings))

        registered_path = "/" + "tmp/bsc-index.html"
        self.assertEqual(scan_text("fixture", registered_path, self.policy), [])

    def test_requester_perspective_narration_fails_closed_in_markdown(self) -> None:
        findings = scan_documentation(
            "docs/report.md",
            "On 2026-07-24 the user explicitly authorized another repair.\n",
        )
        self.assertIn("REQUESTER_PERSPECTIVE_NARRATION", self.codes(findings))
        self.assertNotIn("2026-07-24", repr(findings))

    def test_machine_identifiers_and_prospective_protocol_language_are_preserved(self) -> None:
        text = (
            "`second_repair_authorization` remains an immutable machine identifier.\n"
            "Stop unless the user explicitly authorizes execution.\n"
        )
        self.assertEqual(scan_documentation("docs/protocol.md", text), [])

    def test_stale_status_wording_is_limited_to_current_public_documents(self) -> None:
        phrase = "The Japanese candidate is pending public deployment."
        current = scan_documentation("README.md", phrase)
        historical = scan_documentation("docs/historical-observation.md", phrase)
        self.assertIn("STALE_CURRENT_PUBLIC_WORDING", self.codes(current))
        self.assertEqual(historical, [])

    def test_stale_release_and_html_status_wording_fails_closed(self) -> None:
        fixtures = (
            (
                "docs/SHARING_GUIDE.md",
                "The v0.3.0-alpha.7 release is a research preview.",
            ),
            (
                "START_HERE.html",
                "<p>The current live controller identifies as alpha.8.dev0.</p>",
            ),
            (
                "START_HERE.html",
                "<a>Japanese Pages candidate</a> is included but remains pending public deployment.",
            ),
        )
        for path, text in fixtures:
            with self.subTest(path=path, text=text):
                self.assertIn(
                    "STALE_CURRENT_PUBLIC_WORDING",
                    self.codes(scan_documentation(path, text)),
                )

    def test_javascript_is_scanned_as_utf8_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for suffix in (".js", ".cjs", ".mjs", ".ts"):
                with self.subTest(suffix=suffix):
                    path = Path(directory) / f"app{suffix}"
                    path.write_text("const contact = 'person" + "@" + "example.com';\n", encoding="utf-8")
                    self.assertIn("EMAIL_NOT_ALLOWLISTED", self.codes(scan_path(path, self.policy)))

    def test_jsonl_is_scanned_as_utf8_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.jsonl"
            path.write_text(
                '{"contact":"person'
                + "@"
                + 'example.com","source":"/'
                + "Users/alice/private.json"
                + '"}\n',
                encoding="utf-8",
            )
            codes = self.codes(scan_path(path, self.policy))
            self.assertIn("EMAIL_NOT_ALLOWLISTED", codes)
            self.assertIn("LOCAL_PATH_PRESENT", codes)

    def test_pdf_requires_generic_metadata_and_no_dates(self) -> None:
        clean = b"/Author (J. Tree) /Creator (BSC publication pipeline) /Producer (BSC publication pipeline)"
        self.assertEqual(scan_pdf_bytes("clean.pdf", clean, self.policy), [])
        dirty = clean + b" /CreationDate (D:20260721134608+09'00')"
        self.assertIn("PDF_TIMESTAMP_PRESENT", self.codes(scan_pdf_bytes("dirty.pdf", dirty, self.policy)))

    def test_docx_structured_metadata_is_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.docx"
            core = b'''<?xml version="1.0" encoding="UTF-8"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:creator>J. Tree</dc:creator></cp:coreProperties>'''
            app = b'''<?xml version="1.0" encoding="UTF-8"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>BSC publication pipeline</Application></Properties>'''
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("docProps/core.xml", core)
                archive.writestr("docProps/app.xml", app)
            self.assertEqual(scan_docx(path, self.policy), [])

    def test_archive_members_are_scanned_and_path_escape_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.zip"
            leak = "person" + "@" + "example.com"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("notes.md", leak)
                archive.writestr("../escape.md", "fixture")
            codes = self.codes(scan_zip(path, self.policy))
            self.assertIn("EMAIL_NOT_ALLOWLISTED", codes)
            self.assertIn("ARCHIVE_UNSAFE_MEMBER", codes)

    def test_complete_reachable_commit_history_is_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "config", "user.name", "jkolantree"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "user.email", "307349551+jkolantree@users.noreply.github.com"],
                cwd=root,
                check=True,
            )
            (root / "fixture.txt").write_text("one\n", encoding="utf-8")
            subprocess.run(["git", "add", "fixture.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "allowed"], cwd=root, check=True)
            base = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
            ).stdout.strip()
            disallowed = "person" + "@" + "example.com"
            subprocess.run(
                ["git", "-c", "user.name=J. Tree", "-c", f"user.email={disallowed}", "commit", "-q", "--allow-empty", "-m", "blocked"],
                cwd=root,
                check=True,
            )
            with mock.patch("scripts.check_privacy.ROOT", root):
                findings, count = scan_history("HEAD", self.policy)
                protected, protected_count = scan_protected_history(
                    "HEAD", replace(self.policy, enforcement_base_commit=base)
                )
            self.assertEqual(count, 2)
            self.assertIn("COMMIT_EMAIL_NOT_NOREPLY", self.codes(findings))
            self.assertEqual(protected_count, 1)
            self.assertIn("COMMIT_EMAIL_NOT_NOREPLY", self.codes(protected))


if __name__ == "__main__":
    unittest.main()
