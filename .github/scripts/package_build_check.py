"""Run a stdlib package metadata build check for the scaffold."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from datetime import datetime, timezone
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


def load_pyproject() -> dict[str, Any]:
    try:
        return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit("pyproject.toml is missing")
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
    if isinstance(license_value, dict):
        license_file = license_value.get("file")
        if isinstance(license_file, str) and not (ROOT / license_file).exists():
            errors.append(f"license file does not exist: {license_file}")
        elif isinstance(license_file, str):
            license_text = (ROOT / license_file).read_text(encoding="utf-8")
            if "SPDX-License-Identifier: CC-BY-NC-ND-4.0" not in license_text:
                errors.append("license file must declare SPDX-License-Identifier: CC-BY-NC-ND-4.0")

    dependencies = project.get("dependencies", [])
    if not isinstance(dependencies, list):
        errors.append("[project].dependencies must be a list")

    build_system = data.get("build-system")
    if not isinstance(build_system, dict):
        errors.append("pyproject.toml must contain a [build-system] table")
    elif "build-backend" not in build_system:
        errors.append("[build-system].build-backend is required")
    elif build_system.get("build-backend") != "semia_build":
        errors.append("[build-system].build-backend must be semia_build for offline editable installs")
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
        "checked_at": datetime.now(timezone.utc).isoformat(),
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
