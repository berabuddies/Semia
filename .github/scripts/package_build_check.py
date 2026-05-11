# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
"""Run a stdlib package metadata build check for the scaffold."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"
REQUIRED_PROJECT_FIELDS = (
    "name",
    "version",
    "description",
    "readme",
    "requires-python",
    "license",
)
EXPECTED_LICENSE = "Apache-2.0"
EXPECTED_LICENSE_SPDX_HEADER = f"SPDX-License-Identifier: {EXPECTED_LICENSE}"


def load_pyproject() -> dict[str, Any]:
    try:
        return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit("pyproject.toml is missing") from exc
    except tomllib.TOMLDecodeError as exc:
        raise SystemExit(f"pyproject.toml is invalid: {exc}") from exc


def validate_project(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    project = data.get("project")
    if not isinstance(project, dict):
        return ["pyproject.toml must contain a [project] table"]

    for field in REQUIRED_PROJECT_FIELDS:
        if field not in project:
            errors.append(f"[project].{field} is required")

    readme = project.get("readme")
    if isinstance(readme, str) and not (ROOT / readme).exists():
        errors.append(f"readme file does not exist: {readme}")

    license_value = project.get("license")
    if isinstance(license_value, str):
        if license_value != EXPECTED_LICENSE:
            errors.append(
                f"[project].license must be the SPDX expression {EXPECTED_LICENSE!r}, "
                f"got {license_value!r}"
            )
    elif isinstance(license_value, dict):
        # Legacy PEP 621 license = { file = "..." } form. Still accepted.
        license_file = license_value.get("file")
        if isinstance(license_file, str) and not (ROOT / license_file).exists():
            errors.append(f"license file does not exist: {license_file}")
    else:
        errors.append(
            "[project].license must be a SPDX license expression string "
            "(PEP 639) or a legacy { file = ... } table"
        )

    license_files = project.get("license-files")
    if license_files is not None and not (
        isinstance(license_files, list) and all(isinstance(p, str) for p in license_files)
    ):
        errors.append("[project].license-files must be a list of strings if set")
    elif isinstance(license_files, list):
        for entry in license_files:
            if not (ROOT / entry).exists():
                errors.append(f"license file referenced by license-files is missing: {entry}")

    license_path = ROOT / "LICENSE"
    if license_path.exists():
        license_text = license_path.read_text(encoding="utf-8")
        if EXPECTED_LICENSE_SPDX_HEADER not in license_text:
            errors.append(f"LICENSE must declare {EXPECTED_LICENSE_SPDX_HEADER}")
    else:
        errors.append("LICENSE file is missing at the repository root")

    dependencies = project.get("dependencies", [])
    if not isinstance(dependencies, list):
        errors.append("[project].dependencies must be a list")

    build_system = data.get("build-system")
    if not isinstance(build_system, dict):
        errors.append("pyproject.toml must contain a [build-system] table")
    elif "build-backend" not in build_system:
        errors.append("[build-system].build-backend is required")
    elif build_system.get("build-backend") != "semia_build":
        errors.append(
            "[build-system].build-backend must be semia_build for offline editable installs"
        )
    if build_system.get("requires") != []:
        errors.append("[build-system].requires must stay empty for offline editable installs")
    if build_system.get("backend-path") != ["build_backend"]:
        errors.append("[build-system].backend-path must be ['build_backend']")

    package_rules = ROOT / "packages" / "semia-core" / "src" / "semia_core" / "rules" / "sdl"
    for name in ("skill_description_lang.dl", "skill_dl_static_analysis.dl"):
        if not (package_rules / name).exists():
            errors.append(f"packaged detector rule is missing: {package_rules / name}")

    scripts = project.get("scripts", {})
    if not isinstance(scripts, dict) or scripts.get("semia") != "semia_cli.main:main":
        errors.append("[project.scripts].semia must point to semia_cli.main:main")

    return errors


def write_artifact(path: Path, data: dict[str, Any]) -> None:
    project = data["project"]
    artifact = {
        "checked_at": datetime.now(UTC).isoformat(),
        "project": {
            "name": project["name"],
            "version": project["version"],
            "requires_python": project["requires-python"],
            "runtime_dependency_count": len(project.get("dependencies", [])),
            "scripts": project.get("scripts", {}),
        },
        "status": "package metadata dry-run passed",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="dist/build-check.json")
    args = parser.parse_args(argv)

    data = load_pyproject()
    errors = validate_project(data)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    write_artifact(ROOT / args.out, data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
