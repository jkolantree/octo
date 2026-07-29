from __future__ import annotations

import contextlib
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import verify


ROOT = Path(__file__).resolve().parents[1]


class VerifySpineTests(unittest.TestCase):
    def test_candidate_profile_has_one_ordered_instance_of_every_gate(self) -> None:
        names = verify.stage_names("candidate")
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(
            set(names),
            {
                "diff-check",
                "privacy-history",
                "source-tests",
                "null-discrimination",
                "browser-runtime",
                "frozen-candidate",
                "localization",
                "release-integrity",
            },
        )
        self.assertLess(names.index("source-tests"), names.index("release-integrity"))
        self.assertLess(names.index("frozen-candidate"), names.index("release-integrity"))
        self.assertNotIn("publication-assets", names)
        self.assertNotIn("pages-integrity", names)

    def test_core_profile_is_python_only(self) -> None:
        self.assertEqual(
            verify.stage_names("core"),
            ("source-tests", "null-discrimination"),
        )

    def test_pages_profile_is_complete_and_bounded(self) -> None:
        self.assertEqual(
            verify.stage_names("pages"),
            (
                "browser-runtime",
                "publication-assets",
                "pages-integrity",
                "localization",
            ),
        )

    def test_run_profile_resolves_tools_and_preserves_repository_root(self) -> None:
        calls: list[tuple[tuple[str, ...], Path, bool]] = []

        def runner(
            command: tuple[str, ...], *, cwd: Path, check: bool
        ) -> subprocess.CompletedProcess[object]:
            calls.append((command, cwd, check))
            return subprocess.CompletedProcess(command, 0)

        with contextlib.redirect_stdout(io.StringIO()):
            status = verify.run_profile(
                "candidate",
                root=Path("C:/candidate"),
                runner=runner,
                python_executable="PYTHON",
                node_executable="NODE",
                git_executable="GIT",
            )
        self.assertEqual(status, 0)
        self.assertEqual(len(calls), len(verify.PROFILES["candidate"]))
        self.assertEqual(
            calls[0],
            (
                (
                    "PYTHON",
                    "scripts/verify.py",
                    "--check-diff",
                    "--git-executable",
                    "GIT",
                ),
                Path("C:/candidate"),
                False,
            ),
        )
        self.assertIn(
            (
                ("NODE", "--test", "tests/return_desk_runtime.test.cjs"),
                Path("C:/candidate"),
                False,
            ),
            calls,
        )
        self.assertTrue(
            all(
                command[0] in {"PYTHON", "NODE", "GIT"}
                for command, _, _ in calls
            )
        )

    def test_diff_check_reads_committed_bytes_on_a_clean_checkout(self) -> None:
        git = shutil.which("git")
        if git is None:
            self.skipTest("git is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def run(*arguments: str) -> None:
                subprocess.run(
                    (git, *arguments),
                    cwd=root,
                    check=True,
                    capture_output=True,
                    text=True,
                )

            run("init", "-b", "main")
            run("config", "core.autocrlf", "false")
            run("config", "user.name", "Verification Test")
            run(
                "config",
                "user.email",
                "307349551+jkolantree@users.noreply.github.com",
            )
            path = root / "candidate.txt"
            path.write_text("clean\n", encoding="utf-8", newline="\n")
            run("add", "candidate.txt")
            run("commit", "-m", "base")
            path.write_text("trailing whitespace  \n", encoding="utf-8", newline="\n")
            run("add", "candidate.txt")
            run("commit", "-m", "candidate")

            self.assertNotEqual(
                verify.check_candidate_diff(root=root, git_executable=git),
                0,
            )

    def test_failure_is_returned_without_running_later_stages(self) -> None:
        calls: list[tuple[str, ...]] = []

        def runner(
            command: tuple[str, ...], *, cwd: Path, check: bool
        ) -> subprocess.CompletedProcess[object]:
            calls.append(command)
            return subprocess.CompletedProcess(command, 7 if len(calls) == 2 else 0)

        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            status = verify.run_stages(
                ("source-tests", "null-discrimination", "release-integrity"),
                runner=runner,
                python_executable="PYTHON",
                node_executable="NODE",
                git_executable="GIT",
            )
        self.assertEqual(status, 7)
        self.assertEqual(len(calls), 2)

    def test_list_mode_is_read_only(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(verify.main(["--list"]), 0)
        self.assertIn("candidate:", output.getvalue())
        self.assertIn("release-integrity:", output.getvalue())

    def test_cli_accepts_explicit_tool_paths_for_isolated_runtimes(self) -> None:
        with mock.patch.object(verify, "run_profile", return_value=0) as run_profile:
            self.assertEqual(
                verify.main(
                    [
                        "pages",
                        "--node-executable",
                        "NODE",
                        "--git-executable",
                        "GIT",
                    ]
                ),
                0,
            )
        run_profile.assert_called_once_with(
            "pages",
            node_executable="NODE",
            git_executable="GIT",
        )

    def test_release_and_ci_delegate_to_the_profiles_once(self) -> None:
        release_builder = (ROOT / "scripts" / "build_release.py").read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            release_builder.count('"scripts/verify.py", "candidate"'),
            1,
        )
        for duplicate in (
            '"scripts/run_tests.py"',
            '"scripts/run_null_discrimination.py"',
            '"scripts/check_gpt_frozen_candidate.py"',
            '"scripts/check_localization.py"',
            '"scripts/check_release.py"',
        ):
            self.assertNotIn(duplicate, release_builder)

        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(ci.count("python scripts/verify.py core"), 1)
        self.assertEqual(ci.count("python scripts/verify.py candidate"), 1)
        pages = (ROOT / ".github" / "workflows" / "pages.yml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(pages.count("python scripts/verify.py pages"), 1)
        source_manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
        self.assertEqual(
            source_manifest.count("include .github/workflows/ci.yml"),
            1,
        )


if __name__ == "__main__":
    unittest.main()
