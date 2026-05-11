# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 berabuddies
"""Assert that CHANGELOG.md contains a section for the given version.

Invoked from the release workflow once a `v*` tag has been pushed. The check
is intentionally strict — a tag without a matching `## [X.Y.Z]` entry means
the changelog was forgotten, which would result in a released artifact whose
public notes do not match its contents.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Release version (no leading 'v').")
    parser.add_argument("--changelog", default="CHANGELOG.md", type=Path)
    args = parser.parse_args(argv)

    if not args.changelog.exists():
        print(f"{args.changelog} does not exist", file=sys.stderr)
        return 1

    text = args.changelog.read_text(encoding="utf-8")
    pattern = re.compile(rf"^##\s+\[{re.escape(args.version)}\]", re.MULTILINE)
    if not pattern.search(text):
        print(
            f"{args.changelog} does not contain a section header for "
            f"version [{args.version}]. Add a `## [{args.version}] - YYYY-MM-DD` "
            "section before tagging the release.",
            file=sys.stderr,
        )
        return 1

    print(f"Found CHANGELOG.md section for [{args.version}].")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
