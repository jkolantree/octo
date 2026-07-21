#!/usr/bin/env python3
"""Remove only known, repository-local build products."""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS = (ROOT / "build", ROOT / "dist", ROOT / "src" / "bsc_audit_engine.egg-info")


def main() -> int:
    for target in TARGETS:
        if target.exists():
            shutil.rmtree(target)
            print(f"removed {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

