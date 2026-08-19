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


RETAINED_MERGE = "fdfda14d1a0c90ec03b4cf844c91596e9a19dced"
FIRST_PARENT = "bcdd04575c88757241182f991c2877fb480369d2"
SECOND_PARENT = "287a02c7b576f3a052c70deb17a5f6a01add1e1c"
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
