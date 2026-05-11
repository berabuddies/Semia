"""Image utilities for handling local file paths and base64 conversion."""

import base64
import mimetypes
from pathlib import Path
from typing import Any

# Parameter names that accept image input (local path, URL, or base64)
IMAGE_PARAM_NAMES = {
    "image",
    "images",
    "first_frame",
    "last_frame",
    "first_frame_url",
    "last_frame_url",
    "ref_images_url",
    "reference_images",
}

# Hint to add to image parameter descriptions
IMAGE_PARAM_HINT = " **Prefer local file path** (e.g., /tmp/img.png) - auto-converted to base64."


def is_image_param(name: str) -> bool:
    """Check if a parameter name is an image parameter."""
    return name in IMAGE_PARAM_NAMES


def enhance_image_param_description(name: str, description: str) -> str:
    """Enhance image parameter description with local file path hint.

    Args:
        name: Parameter name
        description: Original description

    Returns:
        Enhanced description if it's an image param, otherwise original
    """
    if is_image_param(name):
        return description + IMAGE_PARAM_HINT
    return description


def is_local_file(value: str) -> bool:
    """Check if a string value is a local file path."""
    if not isinstance(value, str):
        return False
    if value.startswith(("http://", "https://", "data:")):
        return False
    path = Path(value)
    return path.exists() and path.is_file()


def file_to_base64(file_path: str) -> str:
    """Convert a local file to base64 data URI.

    Args:
        file_path: Path to the local file

    Returns:
        Base64 data URI string (e.g., "data:image/png;base64,...")
    """
    path = Path(file_path)
    mime_type, _ = mimetypes.guess_type(str(path))
    if mime_type is None:
        mime_type = "image/png"

    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")

    return f"data:{mime_type};base64,{data}"


def convert_image_value(value: Any) -> Any:
    """Convert image parameter value, handling local file paths.

    Args:
        value: Parameter value (string or list of strings)

    Returns:
        Converted value with local files as base64 data URIs
    """
    if isinstance(value, str):
        if is_local_file(value):
            return file_to_base64(value)
        return value
    elif isinstance(value, list):
        return [convert_image_value(v) for v in value]
    return value


def process_image_params(body: dict[str, Any]) -> dict[str, Any]:
    """Process request body, converting local file paths to base64.

    Args:
        body: Request body dictionary

    Returns:
        Processed body with image params converted
    """
    result = body.copy()
    for key in IMAGE_PARAM_NAMES:
        if key in result:
            result[key] = convert_image_value(result[key])
    return result
