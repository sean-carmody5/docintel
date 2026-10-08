"""Prove the committed synthetic set is what the generator produces.

    uv run python -m evals.synth.verify

Rebuilds into a temporary folder and compares against data/synthetic. Text files
must match byte for byte. Images are compared pixel for pixel and Office packages
member by member, because zlib emits different bytes on different platforms for
the same content, which is not a difference in the data.
"""

from __future__ import annotations

import filecmp
import hashlib
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

from evals.synth.build import build

COMMITTED = Path("data/synthetic")
SEED = 2026


def _pixels(path: Path) -> bytes:
    with Image.open(path) as im:
        return hashlib.sha256(np.asarray(im.convert("RGB")).tobytes()).hexdigest().encode()


def _zip_members(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as zf:
        return {n: zf.read(n) for n in sorted(zf.namelist())}


def same(a: Path, b: Path) -> bool:
    suffix = a.suffix.lower()
    if suffix in (".png", ".jpg", ".jpeg"):
        return _pixels(a) == _pixels(b)
    if suffix in (".xlsx", ".docx"):
        return _zip_members(a) == _zip_members(b)
    return filecmp.cmp(a, b, shallow=False)


def verify(committed: Path = COMMITTED, seed: int = SEED) -> list[str]:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / "synthetic"
        build(fresh, seed)
        fresh_files = {p.relative_to(fresh).as_posix() for p in fresh.rglob("*") if p.is_file()}
        committed_files = {
            p.relative_to(committed).as_posix() for p in committed.rglob("*") if p.is_file()
        }
        for missing in sorted(fresh_files - committed_files):
            problems.append(f"not committed: {missing}")
        for extra in sorted(committed_files - fresh_files):
            problems.append(f"committed but not generated: {extra}")
        for rel in sorted(fresh_files & committed_files):
            if not same(committed / rel, fresh / rel):
                problems.append(f"differs: {rel}")
    return problems


def main() -> None:
    problems = verify()
    if problems:
        print("\n".join(problems))
        print(f"{len(problems)} problem(s): committed synthetic set does not match the generator")
        sys.exit(1)
    print("committed synthetic set matches a fresh build")


if __name__ == "__main__":
    main()
