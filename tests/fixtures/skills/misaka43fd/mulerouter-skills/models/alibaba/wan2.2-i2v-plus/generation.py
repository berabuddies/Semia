"""Wan2.2 Image-to-Video Plus generation endpoint."""

import sys
from pathlib import Path

# Support both direct execution and package import
_file_dir = Path(__file__).parent
_models_dir = _file_dir.parent.parent
_root_dir = _models_dir.parent

if str(_root_dir) not in sys.path:
    sys.path.insert(0, str(_root_dir))

from core import InputType, ModelEndpoint, ModelParameter, OutputType, register_endpoint
from models.base import BaseModelEndpoint

# Define the endpoint
ENDPOINT = ModelEndpoint(
    model_id="alibaba/wan2.2-i2v-plus",
    action="generation",
    provider="alibaba",
    model_name="wan2.2-i2v-plus",
    description="Generate videos from images using Wan2.2 Image-to-Video Plus model",
    input_types=[InputType.IMAGE, InputType.TEXT],
    output_type=OutputType.VIDEO,
    api_path="/vendors/alibaba/v1/wan2.2-i2v-plus/generation",
    result_key="videos",
    available_on=["mulerouter", "mulerun"],
    parameters=[
        ModelParameter(
            name="prompt",
            type="string",
            description="Motion/story description (max 800 characters)",
            required=True,
        ),
        ModelParameter(
            name="image",
            type="string",
            description="First-frame image (URL or Base64). Supported formats: JPEG/JPG/PNG/BMP/WEBP, 360-2000px, ≤10MB",
            required=True,
        ),
        ModelParameter(
            name="negative_prompt",
            type="string",
            description="Negative prompt describing unwanted content (max 500 characters)",
            required=False,
        ),
        ModelParameter(
            name="resolution",
            type="string",
            description="Output resolution tier",
            required=False,
            default="1080P",
            enum=["480P", "1080P"],
        ),
        ModelParameter(
            name="duration",
            type="integer",
            description="Video duration in seconds (fixed at 5)",
            required=False,
            enum=[5],
        ),
        ModelParameter(
            name="prompt_extend",
            type="boolean",
            description="Enable intelligent prompt rewriting",
            required=False,
            default="true",
        ),
        ModelParameter(
            name="seed",
            type="integer",
            description="Random seed for reproducibility (0-2147483647)",
            required=False,
        ),
    ],
)

# Register with global registry
register_endpoint(ENDPOINT)


class Wan22I2VPlusGeneration(BaseModelEndpoint):
    """Wan2.2 Image-to-Video Plus generation endpoint."""

    @property
    def endpoint_info(self) -> ModelEndpoint:
        return ENDPOINT


def main() -> int:
    """CLI entry point."""
    return Wan22I2VPlusGeneration().run()


if __name__ == "__main__":
    raise SystemExit(main())
