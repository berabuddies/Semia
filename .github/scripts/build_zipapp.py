# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
"""Build a byte-reproducible zipapp.

Stdlib-only replacement for ``python -m zipapp``. The standard tool relies on
filesystem walk order and embeds per-file mtimes, so the same source can
produce different bytes across runs — which makes it impossible to gate CI on
a strict ``git diff --exit-code`` against committed ``.pyz`` artifacts.

This builder pins every source of nondeterminism so the same staged source
tree always yields the same archive bytes:

  * file order: sorted alphabetically by archive name
  * mtime: fixed (FIXED_DATE_TIME)
  * permissions: 0o644 for every entry
  * create_system: 3 (Unix), independent of host OS
  * compression: ZIP_STORED (no compression)

We deliberately do NOT use ZIP_DEFLATED. The zlib deflate stream is not
byte-stable across platforms — Linux, macOS, and Windows runners ship
different zlib versions whose encoders may emit different bit sequences
for the same input even at a pinned compresslevel. The ZIP spec only
guarantees inflate output, not deflate output. ZIP_STORED is bit-for-bit
identical everywhere, which is what the CI drift check needs. The size
cost is ~3x per entry; the bundles are small enough that this is fine.

The output is a valid zipapp — same shebang prefix + ZIP layout the cpython
``zipapp`` module produces.
"""

from __future__ import annotations

import argparse
import os
import sys
import zipfile
from pathlib import Path

# ZIP format only supports dates >= 1980-01-01. We pick a stable, obvious
# sentinel value far enough from 1980 to avoid edge cases with two-second
# rounding.
FIXED_DATE_TIME = (2000, 1, 1, 0, 0, 0)
FIXED_PERMISSIONS = 0o644
ZIP_CREATE_SYSTEM_UNIX = 3


# Matches cpython's zipapp main template verbatim so the synthetic
# ``__main__.py`` is identical to what ``python -m zipapp -m`` would emit.
_MAIN_TEMPLATE = """\
# -*- coding: utf-8 -*-
import {module}
{module}.{fn}()
"""


def _build_main_py(entry: str) -> str:
    if ":" not in entry:
        raise SystemExit(f"--main must be in the form 'pkg[.mod]:func', got: {entry!r}")
    module, fn = entry.split(":", 1)
    if not module or not fn:
        raise SystemExit(f"--main must have both a module and a function, got: {entry!r}")
    return _MAIN_TEMPLATE.format(module=module, fn=fn)


def _collect_entries(stage: Path) -> list[tuple[str, bytes]]:
    entries: list[tuple[str, bytes]] = []
    for path in stage.rglob("*"):
        if not path.is_file():
            continue
        # Defensive: zipapp stage should be clean, but guard against stray
        # caches anyway so a forgotten ``__pycache__`` does not poison the
        # output.
        if "__pycache__" in path.parts or path.name.endswith(".pyc"):
            continue
        arcname = path.relative_to(stage).as_posix()
        entries.append((arcname, path.read_bytes()))
    return entries


def write_zipapp(
    *,
    stage: Path,
    out: Path,
    entry: str,
    shebang: str,
) -> None:
    entries = _collect_entries(stage)
    # Drop any pre-existing __main__.py at the stage root — we always
    # synthesize one from --main, mirroring ``python -m zipapp -m``.
    entries = [(name, data) for name, data in entries if name != "__main__.py"]
    entries.append(("__main__.py", _build_main_py(entry).encode("utf-8")))
    entries.sort(key=lambda item: item[0])

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as fh:
        fh.write(f"#!{shebang}\n".encode())
        with zipfile.ZipFile(fh, "w", compression=zipfile.ZIP_STORED) as zf:
            for arcname, data in entries:
                info = zipfile.ZipInfo(arcname, date_time=FIXED_DATE_TIME)
                info.create_system = ZIP_CREATE_SYSTEM_UNIX
                info.external_attr = (FIXED_PERMISSIONS & 0xFFFF) << 16
                info.compress_type = zipfile.ZIP_STORED
                zf.writestr(info, data)

    os.chmod(out, 0o755)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--source", required=True, type=Path, help="staged source directory to bundle"
    )
    parser.add_argument("--main", required=True, help="entry point in pkg[.mod]:func form")
    parser.add_argument(
        "--python",
        default="/usr/bin/env python3",
        help="shebang interpreter (default: %(default)s)",
    )
    parser.add_argument("--out", required=True, type=Path, help="output .pyz path")
    args = parser.parse_args(argv)

    if not args.source.is_dir():
        print(f"source is not a directory: {args.source}", file=sys.stderr)
        return 1

    write_zipapp(
        stage=args.source,
        out=args.out,
        entry=args.main,
        shebang=args.python,
    )
    print(f"built {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
