"""Wan2.6 Image-to-Video generation endpoint."""

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
    model_id="alibaba/wan2.6-i2v",
    action="generation",
    provider="alibaba",
    model_name="wan2.6-i2v",
    description="Generate videos from images using Wan2.6 Image-to-Video model",
    input_types=[InputType.IMAGE, InputType.TEXT],
    output_type=OutputType.VIDEO,
    api_path="/vendors/alibaba/v1/wan2.6-i2v/generation",
    result_key="videos",
    available_on=["mulerouter", "mulerun"],
    parameters=[
        ModelParameter(
            name="prompt",
            type="string",
            description="Motion/story description for the video (max 2000 characters)",
            required=True,
        ),
        ModelParameter(
            name="image",
            type="string",
            description="First-frame image (URL or Base64). Supported: JPEG/JPG/PNG/BMP/WEBP, 360-2000px, ≤10MB",
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
            default="720P",
            enum=["480P", "720P", "1080P"],
        ),
        ModelParameter(
            name="duration",
            type="integer",
            description="Video duration in seconds (5, 10, or 15)",
            required=False,
            default=5,
            enum=[5, 10, 15],
        ),
        ModelParameter(
            name="prompt_extend",
            type="boolean",
            description="Enable intelligent prompt rewriting",
            required=False,
            default="true",
        ),
        ModelParameter(
            name="multi_shots",
            type="string",
            description="Shot type: single or multi",
            required=False,
            default="single",
            enum=["single", "multi"],
        ),
        ModelParameter(
            name="audio",
            type="boolean",
            description="Enable automatic audio generation",
            required=False,
            default="true",
        ),
        ModelParameter(
            name="audio_url",
            type="string",
            description="Custom audio file URL (wav/mp3, 3-30s, ≤15MB)",
            required=False,
        ),
        ModelParameter(
            name="seed",
            type="integer",
            description="Random seed for reproducibility (0-2147483647)",
            required=False,
        ),
    ],
)

register_endpoint(ENDPOINT)


class Wan26I2VGeneration(BaseModelEndpoint):
    """Wan2.6 Image-to-Video generation endpoint."""

    @property
    def endpoint_info(self) -> ModelEndpoint:
        return ENDPOINT


def main() -> int:
    """CLI entry point."""
    return Wan26I2VGeneration().run()


if __name__ == "__main__":
    raise SystemExit(main())
