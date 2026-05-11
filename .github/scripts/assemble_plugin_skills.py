# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
"""Assemble per-host plugin ``SKILL.md`` files from the shared workflow body.

Each plugin host (codex, claude-code, openclaw) keeps a tiny ``_host.md``
overlay next to its assembled ``SKILL.md``. The overlay holds the host-
specific frontmatter, opening section, and any prerequisite / CLI-invocation
text; the canonical workflow body lives in
``packages/semia-plugins/shared/skills/semia-skillscan/SKILL.md``.

This script concatenates the overlay (verbatim) and the shared body (with
its frontmatter and top-level ``# Semia Skillscan`` heading stripped, so the
host's own H1 stays on top). It is byte-deterministic and CI verifies the
committed files match what this script produces — same pattern as
``build_zipapp.py``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "packages" / "semia-plugins" / "shared" / "skills" / "semia-skillscan" / "SKILL.md"
PLUGIN_ROOT = ROOT / "packages" / "semia-plugins"
HOSTS = ("codex", "claude-code", "openclaw")


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    if end == -1:
        return text
    return text[end + len("\n---\n") :]


def _strip_top_h1(text: str) -> str:
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    skipped_h1 = False
    skipping_intro = False
    for line in lines:
        if not skipped_h1 and line.startswith("# "):
            skipped_h1 = True
            skipping_intro = True
            continue
        if skipping_intro:
            # Drop the lines between the H1 and the first H2/H3, including any
            # intro paragraphs the canonical body uses to introduce itself. The
            # per-host overlay supplies its own intro.
            if line.startswith("## ") or line.startswith("### "):
                skipping_intro = False
            else:
                continue
        out.append(line)
    return "".join(out)


def _overlay_path(host: str) -> Path:
    return PLUGIN_ROOT / host / "skills" / "semia-skillscan" / "_host.md"


def _skill_path(host: str) -> Path:
    return PLUGIN_ROOT / host / "skills" / "semia-skillscan" / "SKILL.md"


def _shared_body() -> str:
    raw = SHARED.read_text(encoding="utf-8")
    return _strip_top_h1(_strip_frontmatter(raw))


def _assemble(host: str) -> str:
    overlay = _overlay_path(host).read_text(encoding="utf-8")
    body = _shared_body().lstrip("\n")
    overlay = overlay.rstrip() + "\n\n"
    return overlay + body.rstrip() + "\n"


def _write(host: str) -> Path:
    path = _skill_path(host)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_assemble(host), encoding="utf-8")
    return path


def _check(host: str) -> tuple[bool, str]:
    actual = _skill_path(host).read_text(encoding="utf-8")
    expected = _assemble(host)
    if actual == expected:
        return True, ""
    return (
        False,
        f"{_skill_path(host).relative_to(ROOT)} is stale; run `make assemble-plugin-skills`",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed SKILL.md files match the assembled output without writing.",
    )
    args = parser.parse_args(argv)

    if args.check:
        errors: list[str] = []
        for host in HOSTS:
            ok, msg = _check(host)
            if not ok:
                errors.append(msg)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        print(f"Verified {len(HOSTS)} assembled SKILL.md files.")
        return 0

    for host in HOSTS:
        path = _write(host)
        print(f"Wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
