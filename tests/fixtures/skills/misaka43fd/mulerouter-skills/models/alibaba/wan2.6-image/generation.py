"""Wan2.6 Image editing/generation endpoint (Image-to-Image)."""

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
    model_id="alibaba/wan2.6-image",
    action="generation",
    provider="alibaba",
    model_name="wan2.6-image",
    description="Edit/generate images from input images using Wan2.6 Image model",
    input_types=[InputType.IMAGE, InputType.TEXT],
    output_type=OutputType.IMAGE,
    api_path="/vendors/alibaba/v1/wan2.6-image/generation",
    result_key="images",
    available_on=["mulerouter", "mulerun"],
    parameters=[
        ModelParameter(
            name="prompt",
            type="string",
            description="Text description for the image editing (max 2000 characters)",
            required=True,
        ),
        ModelParameter(
            name="images",
            type="array",
            description="Input images (URLs or Base64). Supported: JPEG/JPG/PNG/BMP/WEBP",
            required=True,
        ),
        ModelParameter(
            name="negative_prompt",
            type="string",
            description="Negative prompt describing unwanted content (max 500 characters)",
            required=False,
        ),
        ModelParameter(
            name="size",
            type="string",
            description="Output resolution (width*height)",
            required=False,
            default="1280*1280",
        ),
        ModelParameter(
            name="n",
            type="integer",
            description="Number of images to generate (1-4)",
            required=False,
            default=1,
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


class Wan26ImageGeneration(BaseModelEndpoint):
    """Wan2.6 Image editing endpoint."""

    @property
    def endpoint_info(self) -> ModelEndpoint:
        return ENDPOINT


def main() -> int:
    """CLI entry point."""
    return Wan26ImageGeneration().run()


if __name__ == "__main__":
    raise SystemExit(main())
