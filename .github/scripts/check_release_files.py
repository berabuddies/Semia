# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
"""Verify that every file we require in a release is present.

Extracted from the previous inline `python -c` in `make release-check` so the
list of required files is reviewable in version control rather than embedded
in a Makefile recipe.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REQUIRED = (
    "README.md",
    "LICENSE",
    "NOTICE",
    "PRIVACY.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "docs/release.md",
    "docs/supply-chain.md",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
        help="Repository root (defaults to this script's repo).",
    )
    args = parser.parse_args(argv)

    missing = [name for name in REQUIRED if not (args.root / name).exists()]
    if missing:
        print("Missing release files: " + ", ".join(missing), file=sys.stderr)
        return 1

    print(f"release files present ({len(REQUIRED)} checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
