"""Rename SpliceGAIP -> EpitopeRank across a working tree.

Mirrors what the remote repository already did (package ``epitoperank``,
env prefix ``EPITOPERANK_``, exe ``EpitopeRank.exe``), so the local branch and
``origin/master`` can be merged without ending up with two packages.

Run from the repository root. Text files only; binaries are skipped by suffix.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SKIP_DIRS = {".git", "venv", ".venv", "node_modules", "dist", "out", "results",
             "__pycache__", "build-temp", "tutorial_shots", "legacy"}
SKIP_FILES = {"rename_to_epitoperank.py"}
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".zip",
                   ".exe", ".pdf", ".sqlite3", ".db", ".woff", ".woff2",
                   ".ttf", ".eot", ".mp4", ".webm", ".gz", ".tar", ".whl"}

REPLACEMENTS = (
    ("SPLICEGAIP", "EPITOPERANK"),
    ("SpliceGAIP", "EpitopeRank"),
    ("splicegaip", "epitoperank"),
)


def iter_files() -> "list[Path]":
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name in SKIP_FILES:
                continue
            path = Path(dirpath) / name
            if path.suffix.lower() in BINARY_SUFFIXES:
                continue
            try:
                if path.stat().st_size > 4 * 1024 * 1024:
                    continue
            except OSError:
                continue
            found.append(path)
    return found


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    changed = 0
    for path in iter_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        original = text
        for old, new in REPLACEMENTS:
            if old in text:
                text = text.replace(old, new)
        if text != original:
            changed += 1
            print("rewrite", path.relative_to(ROOT))
            if not dry_run:
                path.write_text(text, encoding="utf-8", newline="")
    print(f"{changed} files rewritten (dry_run={dry_run})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
