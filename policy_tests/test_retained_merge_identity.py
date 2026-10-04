from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.check_privacy import (
    _noreply_email,
    _retained_commit_author_exception_matches,
    load_policy,
    scan_commit,
    scan_protected_history,
)


RETAINED_MERGE = "4135c705a14ea6628481798da123dc62bee40885"
FIRST_PARENT = "f41b47bf0021648e6a389cb4feb6847b383a0ec9"
SECOND_PARENT = "3b0300d07062a57f8d4d132071471699904d67b3"
SUBJECT = (
    "Merge pull request #35 from "
    "jkolantree/codex/gpt-v0.4.0-preview.2-minimal-integration"
)
AUTHOR_EMAIL = "307349551+jkolantree@users.noreply.github.com"


class RetainedMergeIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = load_policy()

    def matches(self, **overrides: object) -> bool:
        values: dict[str, object] = {
            "commit": RETAINED_MERGE,
            "parents": (FIRST_PARENT, SECOND_PARENT),
            "subject": SUBJECT,
            "author_identity": "jack",
            "author_email": AUTHOR_EMAIL,
            "committer_identity": "GitHub",
            "committer_email": "noreply@github.com",
            "policy": self.policy,
        }
        values.update(overrides)
        return _retained_commit_author_exception_matches(**values)  # type: ignore[arg-type]

    def test_exact_retained_merge_object_passes(self) -> None:
        self.assertEqual(scan_commit(RETAINED_MERGE, self.policy), [])

    def test_descendant_protected_history_passes(self) -> None:
        findings, count = scan_protected_history("HEAD", self.policy)
        self.assertGreater(count, 0)
        self.assertEqual(findings, [])

    def test_project_identity_allowlist_does_not_expand(self) -> None:
        self.assertNotIn("jack", self.policy.project_identities)
        self.assertFalse(_noreply_email("jack", AUTHOR_EMAIL, self.policy))

    def test_exception_is_bound_to_exact_object_and_transport_metadata(self) -> None:
        self.assertTrue(self.matches())
        variants = (
            {"commit": SECOND_PARENT},
            {"parents": (SECOND_PARENT, FIRST_PARENT)},
            {"parents": (FIRST_PARENT,)},
            {"parents": (FIRST_PARENT, SECOND_PARENT, RETAINED_MERGE)},
            {"subject": SUBJECT + " altered"},
            {"author_identity": "tree"},
            {"author_email": "jkolantree@users.noreply.github.com"},
            {"committer_identity": "web-flow"},
            {"committer_email": "github-actions[bot]@users.noreply.github.com"},
        )
        for variant in variants:
            with self.subTest(variant=variant):
                self.assertFalse(self.matches(**variant))

    def test_transport_policy_rejects_duplicate_keys(self) -> None:
        payload = (
            '{"policy_version":"1.0.0","policy_version":"1.0.0",'
            '"retained_commit_author_exceptions":[]}\n'
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transport.json"
            path.write_text(payload, encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(ValueError, "duplicate key"):
                load_policy(transport_path=path)

    def test_transport_policy_rejects_wrong_container_types(self) -> None:
        valid = json.loads(
            (Path(__file__).resolve().parents[1] / "privacy-commit-transport-policy.json").read_text(
                encoding="utf-8"
            )
        )
        malformed_values = (
            None,
            1,
            {**valid, "retained_commit_author_exceptions": None},
            {**valid, "retained_commit_author_exceptions": {}},
            {**valid, "retained_commit_author_exceptions": [None]},
            {
                **valid,
                "retained_commit_author_exceptions": [
                    {**valid["retained_commit_author_exceptions"][0], "parents": FIRST_PARENT}
                ],
            },
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transport.json"
            for index, value in enumerate(malformed_values):
                with self.subTest(index=index):
                    path.write_text(json.dumps(value) + "\n", encoding="utf-8", newline="\n")
                    with self.assertRaises(ValueError):
                        load_policy(transport_path=path)

    def test_original_enforcement_base_is_rejected(self) -> None:
        root = Path(__file__).resolve().parents[1]
        raw = json.loads((root / "privacy-policy.json").read_text(encoding="utf-8"))
        raw["enforcement_base_commit"] = "2c611ab693f09bc2f3b5304f972d9a3b8a8f1969"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "enforcement base commit has drifted"):
                load_policy(path=path)

    def test_original_retained_merge_is_rejected(self) -> None:
        root = Path(__file__).resolve().parents[1]
        raw = json.loads((root / "privacy-commit-transport-policy.json").read_text(encoding="utf-8"))
        raw["retained_commit_author_exceptions"][0]["commit"] = "fdfda14d1a0c90ec03b4cf844c91596e9a19dced"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transport.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "retained commit author exceptions have drifted"):
                load_policy(transport_path=path)

    def test_same_author_pair_on_an_ordinary_commit_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            environment = os.environ.copy()
            environment.update(
                {
                    "GIT_AUTHOR_NAME": "jack",
                    "GIT_AUTHOR_EMAIL": AUTHOR_EMAIL,
                    "GIT_COMMITTER_NAME": "tree",
                    "GIT_COMMITTER_EMAIL": AUTHOR_EMAIL,
                }
            )
            subprocess.run(
                ["git", "commit", "-q", "--allow-empty", "-m", "ordinary"],
                cwd=root,
                env=environment,
                check=True,
            )
            with mock.patch("scripts.check_privacy.ROOT", root):
                findings = scan_commit("HEAD", self.policy)
            codes = {finding.code for finding in findings}
            self.assertIn("COMMIT_IDENTITY_NOT_ALLOWLISTED", codes)
            self.assertIn("COMMIT_EMAIL_NOT_NOREPLY", codes)


if __name__ == "__main__":
    unittest.main()
