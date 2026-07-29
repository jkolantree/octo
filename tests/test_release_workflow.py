from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


TAG = "v0.3.0-alpha.test"


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        [shutil.which("git") or "git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class ReleaseWorkflowTests(unittest.TestCase):
    def test_remote_refetch_restores_annotated_tag_after_checkout_dereference(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            remote = root / "remote.git"
            runner = root / "runner"

            source.mkdir()
            git(source, "init", "-b", "main")
            git(source, "config", "user.name", "Release Test")
            git(
                source,
                "config",
                "user.email",
                "307349551+jkolantree@users.noreply.github.com",
            )
            (source / "payload.txt").write_text("candidate\n", encoding="utf-8")
            git(source, "add", "payload.txt")
            git(source, "commit", "-m", "candidate")
            git(source, "tag", "-a", TAG, "-m", "annotated candidate")
            commit = git(source, "rev-parse", "HEAD")

            git(root, "init", "--bare", str(remote))
            git(source, "remote", "add", "origin", str(remote))
            git(source, "push", "origin", "main", f"refs/tags/{TAG}")

            runner.mkdir()
            git(runner, "init")
            git(runner, "remote", "add", "origin", str(remote))
            git(runner, "fetch", "origin", f"refs/tags/{TAG}:refs/tags/{TAG}")
            self.assertEqual(git(runner, "cat-file", "-t", TAG), "tag")

            # Reproduce actions/checkout's event-SHA refspec, which dereferences
            # the annotated tag into a lightweight local tag.
            git(runner, "fetch", "--force", "--no-tags", "origin", f"+{commit}:refs/tags/{TAG}")
            self.assertEqual(git(runner, "cat-file", "-t", TAG), "commit")

            git(
                runner,
                "fetch",
                "--force",
                "--no-tags",
                "origin",
                f"refs/tags/{TAG}:refs/tags/{TAG}",
            )
            self.assertEqual(git(runner, "cat-file", "-t", TAG), "tag")
            self.assertEqual(git(runner, "rev-list", "-n", "1", TAG), commit)


if __name__ == "__main__":
    unittest.main()
