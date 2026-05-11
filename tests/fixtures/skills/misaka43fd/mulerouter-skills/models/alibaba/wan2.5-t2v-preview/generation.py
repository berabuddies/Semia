"""Wan2.5 Text-to-Video Preview generation endpoint."""

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
    model_id="alibaba/wan2.5-t2v-preview",
    action="generation",
    provider="alibaba",
    model_name="wan2.5-t2v-preview",
    description="Generate videos from text prompts using Wan2.5 Text-to-Video Preview model",
    input_types=[InputType.TEXT],
    output_type=OutputType.VIDEO,
    api_path="/vendors/alibaba/v1/wan2.5-t2v-preview/generation",
    result_key="videos",
    available_on=["mulerouter", "mulerun"],
    parameters=[
        ModelParameter(
            name="prompt",
            type="string",
            description="Text description for video content (max 2000 characters)",
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
            default="1280*720",
            enum=[
                "832*480",
                "480*832",
                "624*624",
                "1280*720",
                "720*1280",
                "960*960",
                "1088*832",
                "832*1088",
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
            description="Video duration in seconds (5 or 10)",
            required=False,
            enum=[5, 10],
        ),
        ModelParameter(
            name="prompt_extend",
            type="boolean",
            description="Enable intelligent prompt rewriting for better detail",
            required=False,
            default="true",
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

# Register with global registry
register_endpoint(ENDPOINT)


class Wan25T2VPreviewGeneration(BaseModelEndpoint):
    """Wan2.5 Text-to-Video Preview generation endpoint."""

    @property
    def endpoint_info(self) -> ModelEndpoint:
        return ENDPOINT


def main() -> int:
    """CLI entry point."""
    return Wan25T2VPreviewGeneration().run()


if __name__ == "__main__":
    raise SystemExit(main())
