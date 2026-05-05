"""Validate Semia plugin manifests without third-party dependencies."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = ROOT / "packages" / "semia-plugins"
IDENTITY_KEYS = ("id", "name", "display_name", "displayName")


def is_manifest(path: Path) -> bool:
    if path.name.endswith(".plugin.json"):
        return True
    return path.name == "plugin.json" and any(
        part in {".codex-plugin", ".claude-plugin"} for part in path.parts
    )


def discover_manifests() -> list[Path]:
    if not PLUGIN_ROOT.exists():
        return []
    return sorted(path for path in PLUGIN_ROOT.rglob("*.json") if is_manifest(path))


def non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_manifest(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON: {exc}"]

    if not isinstance(data, dict):
        return [f"{path}: manifest root must be a JSON object"]

    if not any(non_empty_string(data.get(key)) for key in IDENTITY_KEYS):
        errors.append(
            f"{path}: manifest should include a non-empty identity field "
            f"({', '.join(IDENTITY_KEYS)})"
        )
    if data.get("license") != "CC-BY-NC-ND-4.0":
        errors.append(f"{path}: license must be CC-BY-NC-ND-4.0")

    return errors


def main() -> int:
    manifests = discover_manifests()
    if not manifests:
        print("No plugin manifests found yet.")
        return 0

    errors: list[str] = []
    for manifest in manifests:
        errors.extend(validate_manifest(manifest))

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    print(f"Validated {len(manifests)} plugin manifest(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
