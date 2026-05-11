# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
"""Small stdlib-only build backend for Semia's editable CLI installs.

The repository intentionally has no runtime dependencies. This backend lets
`python -m pip install -e .` work in offline environments where setuptools is
not already installed in the virtual environment.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import shutil
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
_PROJECT = _PYPROJECT["project"]

NAME = _PROJECT["name"]
DIST = NAME.replace("-", "_")
VERSION = _PROJECT["version"]
LICENSE_EXPRESSION = _PROJECT.get("license", "Apache-2.0")
SUMMARY = _PROJECT.get("description", "")
TAG = "py3-none-any"
DIST_INFO = f"{DIST}-{VERSION}.dist-info"
SRC_ROOTS = (
    ROOT / "packages" / "semia-core" / "src",
    ROOT / "packages" / "semia-cli" / "src",
)

# Explicit allowlist of top-level files that belong in the sdist. A whitelist
# is intentional: a blacklist of "things to skip" repeatedly leaked dev state
# (.coverage / coverage.xml — which embed absolute build-host paths! — plus
# .agents/, .github/, tests/, etc.).
SDIST_FILES = (
    "pyproject.toml",
    "README.md",
    "LICENSE",
    "NOTICE",
    "CHANGELOG.md",
    "SECURITY.md",
    "PRIVACY.md",
)

# Directories included recursively. Caches and bytecode inside them are
# filtered by `_SDIST_DIR_IGNORE`. Everything else in the repo (tests, CI
# scaffolding, Makefile, dev tooling configs) is deliberately excluded.
SDIST_DIRS = (
    "build_backend",
    "packages/semia-cli/src",
    "packages/semia-core/src",
    # Ship the per-host plugin assets (zipapps, SKILL.md, manifests) so users
    # who install from the sdist still get a complete plugin bundle.
    "packages/semia-plugins",
    # Architecture / release / supply-chain docs are referenced from the
    # README and from check_release_files.py — keep them shippable.
    "docs",
)

_SDIST_DIR_IGNORE = shutil.ignore_patterns(
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".DS_Store",
)


def get_requires_for_build_wheel(config_settings=None):
    return []


def get_requires_for_build_editable(config_settings=None):
    return []


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    return _write_metadata_dir(Path(metadata_directory))


def prepare_metadata_for_build_editable(metadata_directory, config_settings=None):
    return _write_metadata_dir(Path(metadata_directory))


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    wheel = Path(wheel_directory) / f"{DIST}-{VERSION}-0.editable-{TAG}.whl"
    entries = {
        f"{DIST}.pth": "\n".join(str(path) for path in SRC_ROOTS) + "\n",
        f"{DIST_INFO}/METADATA": _metadata(),
        f"{DIST_INFO}/WHEEL": _wheel_file(),
        f"{DIST_INFO}/entry_points.txt": _entry_points(),
    }
    _write_wheel(wheel, entries)
    return wheel.name


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    wheel = Path(wheel_directory) / f"{DIST}-{VERSION}-{TAG}.whl"
    entries = {
        f"{DIST_INFO}/METADATA": _metadata(),
        f"{DIST_INFO}/WHEEL": _wheel_file(),
        f"{DIST_INFO}/entry_points.txt": _entry_points(),
    }
    for src_root in SRC_ROOTS:
        for path in src_root.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                entries[path.relative_to(src_root).as_posix()] = path.read_bytes()
    _write_wheel(wheel, entries)
    return wheel.name


def build_sdist(sdist_directory, config_settings=None):
    # PEP 517 requires the sdist tarball to contain a single top-level
    # directory named `{name}-{version}` and a `PKG-INFO` file inside it.
    #
    # We populate that directory from explicit allowlists (SDIST_FILES,
    # SDIST_DIRS). Tests, CI scaffolding, dev tooling configs, and any
    # development state (.coverage / coverage.xml / .agents/) stay out.
    base = f"{DIST}-{VERSION}"
    out_dir = Path(sdist_directory)
    out_dir.mkdir(parents=True, exist_ok=True)

    staging = out_dir / f".{base}.staging"
    if staging.exists():
        shutil.rmtree(staging)
    pkg_root = staging / base
    pkg_root.mkdir(parents=True)

    for rel in SDIST_FILES:
        src = ROOT / rel
        if not src.is_file():
            raise FileNotFoundError(f"sdist allowlisted file is missing: {rel}")
        dst = pkg_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    for rel in SDIST_DIRS:
        src = ROOT / rel
        if not src.is_dir():
            raise FileNotFoundError(f"sdist allowlisted directory is missing: {rel}")
        dst = pkg_root / rel
        shutil.copytree(src, dst, ignore=_SDIST_DIR_IGNORE)

    (pkg_root / "PKG-INFO").write_text(_metadata(), encoding="utf-8")

    archive_base = out_dir / base
    shutil.make_archive(str(archive_base), "gztar", root_dir=staging, base_dir=base)
    shutil.rmtree(staging)
    return f"{base}.tar.gz"


def _write_metadata_dir(metadata_directory: Path) -> str:
    dist_info = metadata_directory / DIST_INFO
    dist_info.mkdir(parents=True, exist_ok=True)
    (dist_info / "METADATA").write_text(_metadata(), encoding="utf-8")
    (dist_info / "WHEEL").write_text(_wheel_file(), encoding="utf-8")
    (dist_info / "entry_points.txt").write_text(_entry_points(), encoding="utf-8")
    return DIST_INFO


def _metadata() -> str:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    license_files = _PROJECT.get("license-files") or []
    license_file_lines = "".join(
        f"License-File: {path}\n" for path in license_files if (ROOT / path).is_file()
    )
    return (
        # Metadata 2.4 is required for PEP 639 License-Expression / License-File.
        "Metadata-Version: 2.4\n"
        f"Name: {NAME}\n"
        f"Version: {VERSION}\n"
        f"Summary: {SUMMARY}\n"
        "Author: RiemaLabs\n"
        f"License-Expression: {LICENSE_EXPRESSION}\n"
        f"{license_file_lines}"
        "Requires-Python: >=3.11\n"
        "Provides-Extra: anthropic\n"
        "Requires-Dist: anthropic>=0.40; extra == 'anthropic'\n"
        "Description-Content-Type: text/markdown\n"
        "Project-URL: Homepage, https://github.com/RiemaLabs/semia-skillscan\n"
        "\n"
        f"{readme}\n"
    )


def _wheel_file() -> str:
    return (
        f"Wheel-Version: 1.0\nGenerator: semia-build {VERSION}\nRoot-Is-Purelib: true\nTag: {TAG}\n"
    )


def _entry_points() -> str:
    return "[console_scripts]\nsemia = semia_cli.main:main\n"


def _write_wheel(path: Path, entries: dict[str, str | bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record_rows: list[list[str]] = []
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as wheel:
        for name, value in sorted(entries.items()):
            data = value.encode("utf-8") if isinstance(value, str) else value
            wheel.writestr(name, data)
            record_rows.append([name, _hash(data), str(len(data))])
        record_name = f"{DIST_INFO}/RECORD"
        record_rows.append([record_name, "", ""])
        record_data = _csv(record_rows).encode("utf-8")
        wheel.writestr(record_name, record_data)


def _hash(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    encoded = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return f"sha256={encoded}"


def _csv(rows: list[list[str]]) -> str:
    handle = io.StringIO()
    writer = csv.writer(handle, lineterminator="\n")
    writer.writerows(rows)
    return handle.getvalue()
