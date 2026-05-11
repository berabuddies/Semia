"""Midjourney models.

This package imports all Midjourney model endpoints to register them with the global registry.
"""

import contextlib
import importlib.util
from pathlib import Path

# Get the directory of this file
_package_dir = Path(__file__).parent

# List of model files to import
_model_files = [
    "diffusion/generation.py",
    "video/generation.py",
]


def _import_model_file(model_file: str) -> None:
    """Import a model file to register its endpoints."""
    file_path = _package_dir / model_file

    if not file_path.exists():
        return

    module_name = model_file.replace("/", "_").replace("-", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(
        f"models.midjourney.{module_name}",
        file_path,
    )
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)


# Import each model file to register endpoints
for _model_file in _model_files:
    with contextlib.suppress(Exception):
        _import_model_file(_model_file)
