"""Midjourney Text-to-Image generation endpoint."""

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
    model_id="midjourney/diffusion",
    action="generation",
    provider="midjourney",
    model_name="diffusion",
    description="Generate images from text prompts using Midjourney",
    input_types=[InputType.TEXT],
    output_type=OutputType.IMAGE,
    api_path="/vendors/midjourney/v1/tob/diffusion",
    result_key="images",
    available_on=["mulerouter", "mulerun"],
    parameters=[
        ModelParameter(
            name="prompt",
            type="string",
            description="Image description prompt in Midjourney format (max 8192 characters)",
            required=True,
        ),
    ],
)

register_endpoint(ENDPOINT)


class MidjourneyDiffusion(BaseModelEndpoint):
    """Midjourney image generation endpoint."""

    @property
    def endpoint_info(self) -> ModelEndpoint:
        return ENDPOINT


def main() -> int:
    """CLI entry point."""
    return MidjourneyDiffusion().run()


if __name__ == "__main__":
    raise SystemExit(main())
