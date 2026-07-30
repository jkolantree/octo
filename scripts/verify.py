#!/usr/bin/env python3
"""Run the repository's existing verification gates through one fail-fast entry point."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Stage:
    description: str
    command: tuple[str, ...]


STAGES: dict[str, Stage] = {
    "diff-check": Stage(
        "reject whitespace errors in workspace, index, and committed candidate bytes",
        (
            "{python}",
            "scripts/verify.py",
            "--check-diff",
            "--git-executable",
            "{git}",
        ),
    ),
    "privacy-history": Stage(
        "scan the candidate and protected history for publication hazards",
        (
            "{python}",
            "scripts/check_privacy.py",
            "--protected-history",
            "HEAD",
        ),
    ),
    "source-tests": Stage(
        "run the complete Python source suite",
        ("{python}", "scripts/run_tests.py"),
    ),
    "null-discrimination": Stage(
        "run deterministic null-discrimination checks",
        ("{python}", "scripts/run_null_discrimination.py"),
    ),
    "browser-runtime": Stage(
        "run the Return Desk browser-runtime suite",
        ("{node}", "--test", "tests/return_desk_runtime.test.cjs"),
    ),
    "publication-assets": Stage(
        "verify generated browser publication assets",
        ("{python}", "scripts/build_publication_assets.py", "--check"),
    ),
    "pages-integrity": Stage(
        "verify Pages integrity and accessibility",
        ("{python}", "scripts/check_pages.py"),
    ),
    "frozen-candidate": Stage(
        "verify the frozen Custom GPT candidate registry",
        (
            "{python}",
            "scripts/check_gpt_frozen_candidate.py",
            "--check",
            "docs/GPT_FROZEN_CANDIDATE.json",
        ),
    ),
    "localization": Stage(
        "verify localization projections",
        ("{python}", "scripts/check_localization.py"),
    ),
    "release-integrity": Stage(
        "verify documentation, package, Pages, publication, and release invariants",
        ("{python}", "scripts/check_release.py"),
    ),
}

PROFILES: dict[str, tuple[str, ...]] = {
    "core": (
        "source-tests",
        "null-discrimination",
    ),
    "pages": (
        "browser-runtime",
        "publication-assets",
        "pages-integrity",
        "localization",
    ),
    "candidate": (
        "diff-check",
        "privacy-history",
        "source-tests",
        "null-discrimination",
        "browser-runtime",
        "frozen-candidate",
        "localization",
        "release-integrity",
    ),
}


Runner = Callable[..., subprocess.CompletedProcess[object]]


def _git_output(
    git_executable: str,
    arguments: Sequence[str],
    *,
    root: Path,
) -> tuple[int, str]:
    result = subprocess.run(
        (git_executable, *arguments),
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return int(result.returncode), result.stdout.strip()


def check_candidate_diff(
    *,
    root: Path = ROOT,
    git_executable: str | None = None,
) -> int:
    """Check dirty bytes and a committed range, including on clean CI/tag trees."""

    resolved_git = git_executable or shutil.which("git")
    if resolved_git is None:
        print("[blocked] diff-check: Git is not available on PATH", file=sys.stderr)
        return 2

    for arguments in (
        ("diff", "--check"),
        ("diff", "--cached", "--check"),
    ):
        result = subprocess.run(
            (resolved_git, *arguments),
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            sys.stdout.write(result.stdout)
            sys.stderr.write(result.stderr)
            return int(result.returncode)

    status, head = _git_output(resolved_git, ("rev-parse", "HEAD"), root=root)
    if status != 0:
        print("[failed] diff-check: HEAD cannot be resolved", file=sys.stderr)
        return status

    candidates: list[str] = []
    github_base = os.environ.get("GITHUB_BASE_REF", "").strip()
    if github_base:
        candidates.extend((f"refs/remotes/origin/{github_base}", github_base))
    candidates.append("refs/remotes/origin/main")

    base: str | None = None
    for candidate in candidates:
        status, resolved = _git_output(
            resolved_git,
            ("rev-parse", "--verify", "--quiet", candidate),
            root=root,
        )
        if status != 0:
            continue
        status, merge_base = _git_output(
            resolved_git,
            ("merge-base", head, resolved),
            root=root,
        )
        if status == 0 and merge_base and merge_base != head:
            base = merge_base
            break

    if base is None:
        status, parent = _git_output(
            resolved_git,
            ("rev-parse", "--verify", "--quiet", f"{head}^1"),
            root=root,
        )
        if status == 0 and parent and parent != head:
            base = parent

    if base is None:
        print("[passed] diff-check: initial commit plus workspace and index")
        return 0

    result = subprocess.run(
        (resolved_git, "diff", "--check", base, head),
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        return int(result.returncode)
    print(f"[passed] diff-check: committed range {base}..{head}")
    return 0


def stage_names(profile: str) -> tuple[str, ...]:
    try:
        names = PROFILES[profile]
    except KeyError as exc:
        raise ValueError(f"unknown verification profile: {profile}") from exc
    if len(names) != len(set(names)):
        raise ValueError(f"verification profile contains duplicate stages: {profile}")
    unknown = [name for name in names if name not in STAGES]
    if unknown:
        raise ValueError(f"verification profile references unknown stages: {unknown}")
    return names


def resolve_command(
    stage: Stage,
    *,
    python_executable: str,
    node_executable: str,
    git_executable: str,
) -> tuple[str, ...]:
    replacements = {
        "{python}": python_executable,
        "{node}": node_executable,
        "{git}": git_executable,
    }
    return tuple(replacements.get(part, part) for part in stage.command)


def run_stages(
    names: Sequence[str],
    *,
    root: Path = ROOT,
    runner: Runner = subprocess.run,
    python_executable: str = sys.executable,
    node_executable: str | None = None,
    git_executable: str | None = None,
) -> int:
    resolved_node = node_executable or shutil.which("node")
    resolved_git = git_executable or shutil.which("git")
    for name in names:
        if name not in STAGES:
            raise ValueError(f"unknown verification stage: {name}")
        stage = STAGES[name]
        if "{node}" in stage.command and resolved_node is None:
            print(f"[blocked] {name}: Node.js is not available on PATH", file=sys.stderr)
            return 2
        if "{git}" in stage.command and resolved_git is None:
            print(f"[blocked] {name}: Git is not available on PATH", file=sys.stderr)
            return 2
        command = resolve_command(
            stage,
            python_executable=python_executable,
            node_executable=resolved_node or "node",
            git_executable=resolved_git or "git",
        )
        print(f"[run] {name}: {stage.description}", flush=True)
        result = runner(command, cwd=root, check=False)
        if result.returncode != 0:
            print(
                f"[failed] {name}: exit {result.returncode}",
                file=sys.stderr,
                flush=True,
            )
            return int(result.returncode)
        print(f"[passed] {name}", flush=True)
    print(f"[passed] verification spine ({len(names)} stages)", flush=True)
    return 0


def run_profile(profile: str, **kwargs: object) -> int:
    return run_stages(stage_names(profile), **kwargs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "profile",
        nargs="?",
        choices=tuple(PROFILES),
        default="candidate",
        help="verification profile (default: candidate)",
    )
    parser.add_argument(
        "--stage",
        choices=tuple(STAGES),
        help="run exactly one named stage instead of a profile",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list profiles and stages without running them",
    )
    parser.add_argument(
        "--node-executable",
        help="explicit Node executable for isolated toolchains",
    )
    parser.add_argument(
        "--git-executable",
        help="explicit Git executable for isolated toolchains",
    )
    parser.add_argument(
        "--check-diff",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)
    if args.check_diff:
        if args.stage is not None or args.list:
            parser.error("--check-diff cannot be combined with --stage or --list")
        return check_candidate_diff(git_executable=args.git_executable)
    if args.list:
        for profile, names in PROFILES.items():
            print(f"{profile}: {', '.join(names)}")
        for name, stage in STAGES.items():
            print(f"{name}: {stage.description}")
        return 0
    if args.stage is not None:
        return run_stages(
            (args.stage,),
            node_executable=args.node_executable,
            git_executable=args.git_executable,
        )
    return run_profile(
        args.profile,
        node_executable=args.node_executable,
        git_executable=args.git_executable,
    )


if __name__ == "__main__":
    raise SystemExit(main())
