"""Nano Banana Image-to-Image edit endpoint."""

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
    model_id="google/nano-banana",
    action="edit",
    provider="google",
    model_name="nano-banana",
    description="Edit images based on text prompts using Gemini Nano-Banana model",
    input_types=[InputType.IMAGE, InputType.TEXT],
    output_type=OutputType.IMAGE,
    api_path="/vendors/google/v1/nano-banana/edit",
    result_key="images",
    available_on=["mulerun"],
    parameters=[
        ModelParameter(
            name="prompt",
            type="string",
            description="Text prompt for image editing",
            required=True,
        ),
        ModelParameter(
            name="images",
            type="array",
            description="List of images to edit (URLs or base64). Min 1, max 10 images",
            required=True,
        ),
        ModelParameter(
            name="aspect_ratio",
            type="string",
            description="Aspect ratio of the edited image",
            required=False,
            default="1:1",
            enum=[
                "1:1",
                "2:3",
                "3:2",
                "3:4",
                "4:3",
                "4:5",
                "5:4",
                "9:16",
                "16:9",
            ],
        ),
    ],
)

register_endpoint(ENDPOINT)


class NanoBananaEdit(BaseModelEndpoint):
    """Nano Banana image editing endpoint."""

    @property
    def endpoint_info(self) -> ModelEndpoint:
        return ENDPOINT


def main() -> int:
    """CLI entry point."""
    return NanoBananaEdit().run()


if __name__ == "__main__":
    raise SystemExit(main())
