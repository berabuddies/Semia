"""OpenAI Sora 2 Text/Image-to-Video generation endpoint."""

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
    model_id="openai/sora2",
    action="generation",
    provider="openai",
    model_name="sora2",
    description="Generate videos from text prompts or images using OpenAI Sora 2 model",
    input_types=[InputType.TEXT, InputType.IMAGE],
    output_type=OutputType.VIDEO,
    api_path="/vendors/openai/v1/sora/generation",
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
            name="image",
            type="string",
            description="Initial frame image (URL or local path). Size must match the size parameter (1280x720 or 720x1280). Optional for text-to-video",
            required=False,
        ),
        ModelParameter(
            name="model",
            type="string",
            description="Model version to use",
            required=False,
            default="sora-2",
            enum=["sora-2"],
        ),
        ModelParameter(
            name="seconds",
            type="string",
            description="Video duration in seconds",
            required=False,
            default="8",
            enum=["4", "8", "12"],
        ),
        ModelParameter(
            name="size",
            type="string",
            description="Video size (1280x720=landscape, 720x1280=portrait)",
            required=False,
            default="1280x720",
            enum=["1280x720", "720x1280"],
        ),
    ],
)

register_endpoint(ENDPOINT)


class Sora2Generation(BaseModelEndpoint):
    """OpenAI Sora 2 video generation endpoint."""

    @property
    def endpoint_info(self) -> ModelEndpoint:
        return ENDPOINT


def main() -> int:
    """CLI entry point."""
    return Sora2Generation().run()


if __name__ == "__main__":
    raise SystemExit(main())
