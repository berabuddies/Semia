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
from pathlib import Path
import shutil
import zipfile


NAME = "semia-skillscan"
DIST = "semia_skillscan"
VERSION = "0.1.0"
TAG = "py3-none-any"
DIST_INFO = f"{DIST}-{VERSION}.dist-info"
ROOT = Path(__file__).resolve().parents[1]
SRC_ROOTS = (
    ROOT / "packages" / "semia-core" / "src",
    ROOT / "packages" / "semia-cli" / "src",
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
    base = f"{DIST}-{VERSION}"
    out_dir = Path(sdist_directory)
    archive_base = out_dir / base
    tmp = out_dir / f"{base}.tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(ROOT, tmp, ignore=shutil.ignore_patterns(".git", ".venv", ".omx", "dist", "__pycache__", "*.pyc"))
    shutil.make_archive(str(archive_base), "gztar", root_dir=out_dir, base_dir=tmp.name)
    shutil.rmtree(tmp)
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
    return (
        "Metadata-Version: 2.3\n"
        f"Name: {NAME}\n"
        f"Version: {VERSION}\n"
        "Summary: Skill Behavior Mapping for AI agent skill auditing.\n"
        "Author: RiemaLabs\n"
        "License-Expression: CC-BY-NC-ND-4.0\n"
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
        "Wheel-Version: 1.0\n"
        "Generator: semia-build 0.1.0\n"
        "Root-Is-Purelib: true\n"
        f"Tag: {TAG}\n"
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
