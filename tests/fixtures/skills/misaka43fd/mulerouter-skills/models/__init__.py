"""Model endpoints for MuleRouter/MuleRun API.

This package provides CLI scripts for each model endpoint.
Import this package to register all models with the global registry.

Usage Examples:
    # List all available models
    python scripts/list_models.py

    # Generate video with Wan2.6 T2V
    python models/alibaba/wan2.6-t2v/generation.py --prompt "A cat walking"

    # Generate image with Nano Banana Pro
    python models/google/nano-banana-pro/generation.py --prompt "A sunset"

    # Show parameters for an endpoint
    python models/alibaba/wan2.6-t2v/generation.py --list-params
"""

import sys
from pathlib import Path

# Support both direct execution and package import
_file_dir = Path(__file__).parent
_root_dir = _file_dir.parent

if str(_root_dir) not in sys.path:
    sys.path.insert(0, str(_root_dir))

# Import provider packages to register all endpoints
from models import alibaba, google, midjourney, openai
from models.base import BaseModelEndpoint, create_endpoint_module

__all__ = [
    "alibaba",
    "google",
    "midjourney",
    "openai",
    "BaseModelEndpoint",
    "create_endpoint_module",
]
