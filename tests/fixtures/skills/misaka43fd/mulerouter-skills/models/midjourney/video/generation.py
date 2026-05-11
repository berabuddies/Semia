"""Midjourney Text/Image-to-Video generation endpoint."""

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
    model_id="midjourney/video",
    action="generation",
    provider="midjourney",
    model_name="video",
    description="Generate videos from image with text description using Midjourney. Prompt must contain both text description and image URL (e.g., 'a cat running https://example.com/image.jpg')",
    input_types=[InputType.TEXT, InputType.IMAGE],
    output_type=OutputType.VIDEO,
    api_path="/vendors/midjourney/v1/tob/video-diffusion",
    result_key="videos",
    available_on=["mulerouter", "mulerun"],
    parameters=[
        ModelParameter(
            name="prompt",
            type="string",
            description="Text description with image URL (required). Format: 'description text https://example.com/image.jpg'. Max 8192 characters",
            required=True,
        ),
        ModelParameter(
            name="video_type",
            type="integer",
            description="Video quality: 0=480p, 1=720p",
            required=False,
            default=0,
            enum=[0, 1],
        ),
    ],
)

register_endpoint(ENDPOINT)


class MidjourneyVideo(BaseModelEndpoint):
    """Midjourney video generation endpoint."""

    @property
    def endpoint_info(self) -> ModelEndpoint:
        return ENDPOINT


def main() -> int:
    """CLI entry point."""
    return MidjourneyVideo().run()


if __name__ == "__main__":
    raise SystemExit(main())
