"""Google Veo 3 Text/Image-to-Video generation endpoint."""

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
    model_id="google/veo3",
    action="generation",
    provider="google",
    model_name="veo3",
    description="Generate videos from text prompts or images using Google Veo 3 model",
    input_types=[InputType.TEXT, InputType.IMAGE],
    output_type=OutputType.VIDEO,
    api_path="/vendors/google/v1/veo/generation",
    result_key="videos",
    available_on=["mulerun"],
    parameters=[
        ModelParameter(
            name="prompt",
            type="string",
            description="Video description prompt (max 2000 characters)",
            required=True,
        ),
        ModelParameter(
            name="negative_prompt",
            type="string",
            description="Content to avoid in generation (max 500 characters)",
            required=False,
        ),
        ModelParameter(
            name="image",
            type="string",
            description="Initial frame image (URL or local path) for image-to-video generation",
            required=False,
        ),
        ModelParameter(
            name="last_frame",
            type="string",
            description="Last frame image (URL or local path) for keyframe interpolation",
            required=False,
        ),
        ModelParameter(
            name="reference_images",
            type="array",
            description="Reference images (URLs or local paths, max 3). Only supported by Veo 3.1",
            required=False,
        ),
        ModelParameter(
            name="model",
            type="string",
            description="Model version to use",
            required=False,
            default="veo-3.1",
            enum=["veo-3.1", "veo-3.1-fast", "veo-3"],
        ),
        ModelParameter(
            name="aspect_ratio",
            type="string",
            description="Video aspect ratio",
            required=False,
            default="16:9",
            enum=["16:9", "9:16"],
        ),
        ModelParameter(
            name="resolution",
            type="string",
            description="Video resolution",
            required=False,
            default="720p",
            enum=["720p", "1080p"],
        ),
        ModelParameter(
            name="duration",
            type="integer",
            description="Video duration in seconds (must be 8 when using reference_images)",
            required=False,
            default=8,
            enum=[4, 6, 8],
        ),
    ],
)

register_endpoint(ENDPOINT)


class Veo3Generation(BaseModelEndpoint):
    """Google Veo 3 video generation endpoint."""

    @property
    def endpoint_info(self) -> ModelEndpoint:
        return ENDPOINT


def main() -> int:
    """CLI entry point."""
    return Veo3Generation().run()


if __name__ == "__main__":
    raise SystemExit(main())
