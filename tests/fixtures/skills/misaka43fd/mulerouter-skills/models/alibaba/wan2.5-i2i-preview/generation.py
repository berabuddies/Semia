"""Wan2.5 Image-to-Image Preview generation endpoint."""

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
    model_id="alibaba/wan2.5-i2i-preview",
    action="generation",
    provider="alibaba",
    model_name="wan2.5-i2i-preview",
    description="Edit images using Wan2.5 Image-to-Image Preview model with reference images",
    input_types=[InputType.IMAGE, InputType.TEXT],
    output_type=OutputType.IMAGE,
    api_path="/vendors/alibaba/v1/wan2.5-i2i-preview/generation",
    result_key="images",
    available_on=["mulerouter", "mulerun"],
    parameters=[
        ModelParameter(
            name="prompt",
            type="string",
            description="Text description for the desired edit (max 2000 characters)",
            required=True,
        ),
        ModelParameter(
            name="images",
            type="array",
            description="Array of image URLs or Base64 encoded data (max 2 images). Supported formats: JPEG, JPG, PNG, BMP, WEBP. Dimensions: [384, 5000] pixels, Max: 10MB per image",
            required=True,
        ),
        ModelParameter(
            name="negative_prompt",
            type="string",
            description="Negative prompt (max 500 characters)",
            required=False,
        ),
        ModelParameter(
            name="size",
            type="string",
            description="Output image resolution (width*height). Total pixels: [768*768, 1440*1440], aspect ratio: [1:4, 4:1]",
            required=False,
            default="1280*1280",
        ),
        ModelParameter(
            name="n",
            type="integer",
            description="Number of images to generate (1-4)",
            required=False,
            default=4,
        ),
        ModelParameter(
            name="prompt_extend",
            type="boolean",
            description="Enable intelligent prompt rewriting (improves short prompts but increases processing time)",
            required=False,
            default="false",
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


class Wan25I2IPreviewGeneration(BaseModelEndpoint):
    """Wan2.5 Image-to-Image Preview generation endpoint."""

    @property
    def endpoint_info(self) -> ModelEndpoint:
        return ENDPOINT


def main() -> int:
    """CLI entry point."""
    return Wan25I2IPreviewGeneration().run()


if __name__ == "__main__":
    raise SystemExit(main())
