from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path, PureWindowsPath


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_release import (  # noqa: E402
    git_source_entries,
    ordered_artifact_paths,
    require_tracked_tree_clean,
    zip_git_source,
)
from release_contract import expected_artifact_names  # noqa: E402


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
    def test_release_artifact_order_is_utf8_bytewise_on_windows_paths(self) -> None:
        names = list(
            expected_artifact_names(
                engine_version="0.3.0a16",
                public_version="0.3.0-alpha.16",
            ).values()
        )
        names.append("RELEASE_MANIFEST.json")
        expected = sorted(names, key=lambda name: name.encode("utf-8"))
        for creation_order in (names, list(reversed(names))):
            with self.subTest(first_created=creation_order[0]):
                paths = [PureWindowsPath(name) for name in creation_order]
                observed = [
                    path.name
                    for path in ordered_artifact_paths(paths)
                ]
                self.assertEqual(observed, expected)
        self.assertLess(
            expected.index("RELEASE_MANIFEST.json"),
            expected.index("SBOM.spdx.json"),
        )

    def test_release_roster_is_semantic_and_has_no_duplicate_source_alias(self) -> None:
        builder = (ROOT / "scripts" / "build_release.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("bsc-audit-complete.zip", builder)
        self.assertIn("role_for_artifact_name(", builder)
        self.assertIn("REQUIRED_ARTIFACT_ROLES", builder)

        workflow = (
            ROOT / ".github" / "workflows" / "release.yml"
        ).read_text(encoding="utf-8")
        self.assertEqual(
            workflow.count("python scripts/check_release_directory.py"),
            3,
        )
        self.assertNotIn("--expected-count", workflow)
        self.assertNotIn(".assets | length", workflow)

        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(ci.count("python scripts/build_dist.py"), 2)

    def test_source_archive_reads_immutable_git_objects_and_detects_later_drift(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            git(root, "init", "-b", "main")
            git(root, "config", "core.autocrlf", "false")
            git(root, "config", "user.name", "Release Test")
            git(
                root,
                "config",
                "user.email",
                "307349551+jkolantree@users.noreply.github.com",
            )
            payload = root / "payload.txt"
            payload.write_bytes(b"committed\n")
            git(root, "add", "payload.txt")
            git(root, "commit", "-m", "candidate")
            commit = git(root, "rev-parse", "HEAD")
            tree = git(root, "rev-parse", "HEAD^{tree}")

            entries = git_source_entries(commit, root=root)
            self.assertEqual(dict(entries), {"payload.txt": b"committed\n"})
            archive = Path(directory) / "source.zip"
            zip_git_source(archive, entries)
            with zipfile.ZipFile(archive) as bundle:
                self.assertEqual(bundle.namelist(), ["payload.txt"])
                self.assertEqual(bundle.read("payload.txt"), b"committed\n")

            output = root / "release-output"
            output.mkdir()
            (output / "artifact.bin").write_bytes(b"release artifact\n")
            require_tracked_tree_clean(
                commit,
                tree,
                root=root,
                allowed_untracked_root=output,
            )
            extra = root / "untracked-source.py"
            extra.write_text("unexpected = True\n", encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "untracked source"):
                require_tracked_tree_clean(
                    commit,
                    tree,
                    root=root,
                    allowed_untracked_root=output,
                )
            extra.unlink()

            payload.write_bytes(b"mutated after gates\n")
            self.assertEqual(
                dict(git_source_entries(commit, root=root))["payload.txt"],
                b"committed\n",
            )
            with self.assertRaisesRegex(SystemExit, "changed tracked source"):
                require_tracked_tree_clean(commit, tree, root=root)

    def test_source_archive_rejects_a_tracked_symlink_without_dereferencing_it(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            git(root, "init", "-b", "main")
            git(root, "config", "core.autocrlf", "false")
            git(root, "config", "user.name", "Release Test")
            git(
                root,
                "config",
                "user.email",
                "307349551+jkolantree@users.noreply.github.com",
            )
            target = root / "link-target.txt"
            target.write_text("outside.txt", encoding="utf-8")
            blob = git(root, "hash-object", "-w", "link-target.txt")
            git(
                root,
                "update-index",
                "--add",
                "--cacheinfo",
                f"120000,{blob},unsafe-link",
            )
            git(root, "commit", "-m", "tracked symlink")

            with self.assertRaisesRegex(SystemExit, "rejects symlinks"):
                git_source_entries(git(root, "rev-parse", "HEAD"), root=root)

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
