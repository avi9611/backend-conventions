#!/usr/bin/env python3
"""Documentation checker — relative links resolve, and stamps stay fresh.

Two failure modes this catches, both of which happen in every repo eventually:

  1. A moved or deleted file leaves dangling links behind.
  2. A doc quietly ages past the point where anyone should trust it. Every file under
     the stamp root carries ``Last verified against the code: <DD Month YYYY>``, and
     past ``--max-age`` days it is reported as stale.

Wire it into a pre-commit hook so a stale doc costs a commit, not an afternoon.

Usage
-----
    python3 tools/check_docs.py                 # links + stamps, repo-wide
    python3 tools/check_docs.py --links-only
    python3 tools/check_docs.py --max-age 60
    python3 tools/check_docs.py --strict        # stale stamps become errors
    python3 tools/check_docs.py --quiet         # only failures

Exit code is 1 if any *error* was found. Stale stamps are warnings by default.

Configure the four constants below for your repo, then leave it alone.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

# --- configure these four for your repo ---------------------------------------

#: Repo root, relative to this file.
REPO = Path(__file__).resolve().parent.parent

#: Only this subtree is stamp-checked. Module guides and dated records are excluded
#: deliberately: a session handoff is a record of one day, not a living document.
STAMP_ROOT = "concerns"

#: Files that carry no stamp on purpose.
STAMP_EXEMPT = {
    "README.md",
    "CHECKLIST.md",
    "RECOMMENDATIONS.md",
}

#: Subtrees that are historical, or written for somebody outside the team, and so must
#: not carry an internal "verified against the code" claim.
STAMP_EXEMPT_DIRS = ("templates/", "archive/", "session-handoff/")

# ------------------------------------------------------------------------------

SKIP_DIRS = {
    ".git", "node_modules", ".next", "__pycache__", ".pytest_cache",
    ".venv", "venv", ".ruff_cache", ".mypy_cache", "dist", "build",
    # Agent worktrees are whole copies of the repo nested deeper, so every doc would
    # be checked twice and each relative link would resolve outside the checkout and
    # read as dead. Scanning a scratch copy of the tree tells you nothing about it.
    ".claude",
}

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+?)(?:\s+\"[^\"]*\")?\)")
STAMP_RE = re.compile(r"Last verified against the code:\s*\**\s*(\d{1,2}\s+\w+\s+\d{4})")
EXTERNAL = ("http://", "https://", "mailto:", "tel:", "#")


def markdown_files() -> list[Path]:
    return sorted(
        p for p in REPO.rglob("*.md")
        if not any(part in SKIP_DIRS for part in p.parts)
    )


def check_links(files: list[Path]) -> tuple[list[str], int]:
    errors, checked = [], 0
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in LINK_RE.finditer(text):
            target = m.group(1)
            if target.startswith(EXTERNAL):
                continue
            path = target.split("#")[0]
            if not path:
                continue
            checked += 1
            if not (f.parent / path).resolve().exists():
                line = text[: m.start()].count("\n") + 1
                errors.append(f"{f.relative_to(REPO)}:{line}  dead link -> {target}")
    return errors, checked


def check_stamps(files: list[Path], max_age: int) -> tuple[list[str], list[str], int]:
    today = dt.date.today()
    missing, stale, checked = [], [], 0
    for f in files:
        rel = f.relative_to(REPO).as_posix()
        if not rel.startswith(f"{STAMP_ROOT}/") or rel in STAMP_EXEMPT:
            continue
        if rel.startswith(STAMP_EXEMPT_DIRS):
            continue
        checked += 1
        text = f.read_text(encoding="utf-8", errors="replace")
        m = STAMP_RE.search(text)
        if not m:
            missing.append(f"{rel}  no 'Last verified against the code' stamp")
            continue
        try:
            stamped = dt.datetime.strptime(m.group(1).strip(), "%d %B %Y").date()
        except ValueError:
            missing.append(f"{rel}  unparseable stamp date: {m.group(1)!r}")
            continue
        age = (today - stamped).days
        if age > max_age:
            stale.append(f"{rel}  stamp is {age} days old ({m.group(1)})")
    return missing, stale, checked


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--max-age", type=int, default=30,
                    help="days before a stamp is called stale (default: 30)")
    ap.add_argument("--links-only", action="store_true", help="skip the stamp check")
    ap.add_argument("--strict", action="store_true", help="treat stale stamps as errors")
    ap.add_argument("--quiet", action="store_true", help="print only problems")
    args = ap.parse_args()

    files = markdown_files()
    errors: list[str] = []

    link_errors, n_links = check_links(files)
    errors += link_errors
    if not args.quiet:
        print(f"links   : {n_links} checked, {len(link_errors)} dead")

    if not args.links_only:
        missing, stale, n_stamped = check_stamps(files, args.max_age)
        errors += missing
        if args.strict:
            errors += stale
        if not args.quiet:
            print(f"stamps  : {n_stamped} checked, {len(missing)} missing, "
                  f"{len(stale)} older than {args.max_age}d")
        for s in stale:
            print(f"  warn  {s}")

    for e in errors:
        print(f"  ERROR {e}")

    if errors:
        print(f"\n{len(errors)} problem(s). Fix the doc, or the link it points at.")
        return 1
    if not args.quiet:
        print("\nDocs OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
