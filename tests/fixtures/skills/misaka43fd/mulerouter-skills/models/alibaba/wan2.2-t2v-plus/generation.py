"""Wan2.2 Text-to-Video Plus generation endpoint."""

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
    model_id="alibaba/wan2.2-t2v-plus",
    action="generation",
    provider="alibaba",
    model_name="wan2.2-t2v-plus",
    description="Generate videos from text prompts using Wan2.2 Text-to-Video Plus model",
    input_types=[InputType.TEXT],
    output_type=OutputType.VIDEO,
    api_path="/vendors/alibaba/v1/wan2.2-t2v-plus/generation",
    result_key="videos",
    available_on=["mulerouter", "mulerun"],
    parameters=[
        ModelParameter(
            name="prompt",
            type="string",
            description="Text prompt for the video (max 800 characters)",
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
            default="1920*1080",
            enum=[
                "832*480",
                "480*832",
                "624*624",
                "1920*1080",
                "1080*1920",
                "1440*1440",
                "1632*1248",
                "1248*1632",
            ],
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


class Wan22T2VPlusGeneration(BaseModelEndpoint):
    """Wan2.2 Text-to-Video Plus generation endpoint."""

    @property
    def endpoint_info(self) -> ModelEndpoint:
        return ENDPOINT


def main() -> int:
    """CLI entry point."""
    return Wan22T2VPlusGeneration().run()


if __name__ == "__main__":
    raise SystemExit(main())
