"""Alibaba (Wan) models.

This package imports all Alibaba model endpoints to register them with the global registry.
Since directory names contain hyphens (e.g., wan2.6-t2v), we use importlib to import them.
"""

import contextlib
import importlib.util
from pathlib import Path

# Get the directory of this file
_package_dir = Path(__file__).parent

# List of model directories and their scripts to import
_model_files = [
    # Wan 2.6 series
    "wan2.6-t2v/generation.py",
    "wan2.6-i2v/generation.py",
    "wan2.6-t2i/generation.py",
    "wan2.6-image/generation.py",
    # Wan 2.5 preview series
    "wan2.5-t2v-preview/generation.py",
    "wan2.5-i2v-preview/generation.py",
    "wan2.5-t2i-preview/generation.py",
    "wan2.5-i2i-preview/generation.py",
    # Wan 2.2 plus/flash series
    "wan2.2-t2v-plus/generation.py",
    "wan2.2-i2v-plus/generation.py",
    "wan2.2-i2v-flash/generation.py",
    # Wan 2.1 plus series
    "wan2.1-vace-plus/generation.py",
    "wan2.1-kf2v-plus/generation.py",
]


def _import_model_file(model_file: str) -> None:
    """Import a model file to register its endpoints."""
    file_path = _package_dir / model_file

    if not file_path.exists():
        return

    module_name = model_file.replace("/", "_").replace("-", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(
        f"models.alibaba.{module_name}",
        file_path,
    )
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)


# Import each model file to register endpoints
for _model_file in _model_files:
    with contextlib.suppress(Exception):
        _import_model_file(_model_file)
