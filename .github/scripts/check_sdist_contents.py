# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
"""Assert the built sdist does not contain dev state or test scaffolding.

Regression guard for build_backend/semia_build.py. The previous blacklist
approach repeatedly leaked .coverage, coverage.xml (which both embed
absolute paths from the build host), .agents/, .github/, tests/, etc. We
now build the sdist from an explicit allowlist; this script enforces the
inverse — fails CI if any forbidden path slips back in.
"""

from __future__ import annotations

import argparse
import sys
import tarfile
from pathlib import Path

FORBIDDEN_PREFIXES = (
    "tests/",
    ".github/",
    ".agents/",
    ".claude/",
    ".codex/",
    ".semia/",
    ".venv/",
    ".cache/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    "build/",
    "dist/",
    "output/",
)

FORBIDDEN_NAMES = (
    ".coverage",
    "coverage.xml",
    ".gitleaks.toml",
    ".pre-commit-config.yaml",
    ".gitattributes",
    ".gitignore",
    "Makefile",
    ".DS_Store",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "sdist",
        type=Path,
        help="Path to the sdist tarball (e.g. dist/semia_skillscan-0.1.0.tar.gz).",
    )
    args = parser.parse_args(argv)

    if not args.sdist.is_file():
        print(f"sdist not found: {args.sdist}", file=sys.stderr)
        return 1

    leaks: list[str] = []
    with tarfile.open(args.sdist, "r:gz") as tar:
        for member in tar.getmembers():
            # Strip the leading "<distname>-<version>/" prefix that every
            # PEP 517 sdist member starts with.
            parts = member.name.split("/", 1)
            if len(parts) < 2 or not parts[1]:
                continue
            inside = parts[1]
            if any(inside.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
                leaks.append(inside)
                continue
            basename = inside.rsplit("/", 1)[-1]
            if basename in FORBIDDEN_NAMES:
                leaks.append(inside)

    if leaks:
        print(f"{args.sdist} contains forbidden paths:", file=sys.stderr)
        for path in sorted(set(leaks)):
            print(f"  {path}", file=sys.stderr)
        return 1

    print(f"sdist contents OK ({args.sdist.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
