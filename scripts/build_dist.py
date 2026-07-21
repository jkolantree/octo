#!/usr/bin/env python3
"""Build wheel and sdist with the already-installed setuptools backend."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import tarfile
import tempfile
from pathlib import Path

import setuptools
from setuptools import build_meta


ROOT = Path(__file__).resolve().parents[1]


def normalize_sdist(path: Path) -> None:
    """Repack the backend sdist with stable gzip and tar metadata."""

    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "1784505600"))
    with tempfile.TemporaryDirectory(prefix="bsc-sdist-") as temporary:
        staging = Path(temporary) / "tree"
        staging.mkdir()
        with tarfile.open(path, "r:gz") as archive:
            archive.extractall(staging, filter="data")
        replacement = Path(temporary) / path.name
        with replacement.open("wb") as raw_stream:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw_stream, compresslevel=9, mtime=epoch) as gzip_stream:
                with tarfile.open(fileobj=gzip_stream, mode="w", format=tarfile.GNU_FORMAT) as output:
                    for item in sorted(staging.rglob("*"), key=lambda value: value.relative_to(staging).as_posix()):
                        relative = item.relative_to(staging).as_posix()
                        info = output.gettarinfo(str(item), arcname=relative)
                        info.mtime = epoch
                        info.uid = 0
                        info.gid = 0
                        info.uname = ""
                        info.gname = ""
                        if item.is_file():
                            with item.open("rb") as source:
                                output.addfile(info, source)
                        else:
                            output.addfile(info)
        shutil.copyfile(replacement, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    lock = json.loads((ROOT / "toolchain.lock.json").read_text(encoding="utf-8"))
    if setuptools.__version__ != lock.get("setuptools"):
        raise SystemExit(f"setuptools {setuptools.__version__} does not match toolchain lock {lock.get('setuptools')}")
    output = args.outdir.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"distribution output directory must be empty: {output}")
    for target in (ROOT / "build", ROOT / "src" / "bsc_audit_engine.egg-info"):
        if target.exists():
            shutil.rmtree(target)
    output.mkdir(parents=True, exist_ok=True)
    os.chdir(ROOT)
    wheel = build_meta.build_wheel(str(output))
    sdist = build_meta.build_sdist(str(output))
    normalize_sdist(output / sdist)
    print(f"setuptools {setuptools.__version__}")
    print(output / wheel)
    print(output / sdist)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
