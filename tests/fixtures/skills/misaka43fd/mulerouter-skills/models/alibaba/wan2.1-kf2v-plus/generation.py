"""Wan2.1 Keyframe-to-Video Plus generation endpoint."""

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
    model_id="alibaba/wan2.1-kf2v-plus",
    action="generation",
    provider="alibaba",
    model_name="wan2.1-kf2v-plus",
    description="Generate videos from first and last frame keyframes using Wan2.1 Keyframe-to-Video Plus model",
    input_types=[InputType.IMAGE, InputType.TEXT],
    output_type=OutputType.VIDEO,
    api_path="/vendors/alibaba/v1/wan2.1-kf2v-plus/generation",
    result_key="videos",
    available_on=["mulerouter", "mulerun"],
    parameters=[
        ModelParameter(
            name="prompt",
            type="string",
            description="Transition and motion description between the first and last frame (max 800 characters)",
            required=True,
        ),
        ModelParameter(
            name="image",
            type="string",
            description="First keyframe image (URL or Base64). Supported formats: JPEG/JPG/PNG/BMP/WEBP, 360-2000px, ≤10MB",
            required=True,
        ),
        ModelParameter(
            name="last_frame",
            type="string",
            description="Last keyframe image (URL or Base64). Same constraints as first frame",
            required=True,
        ),
        ModelParameter(
            name="negative_prompt",
            type="string",
            description="Negative prompt describing unwanted content (max 500 characters)",
            required=False,
        ),
        ModelParameter(
            name="template",
            type="string",
            description="Optional video effect template name",
            required=False,
        ),
        ModelParameter(
            name="resolution",
            type="string",
            description="Output resolution (fixed at 720P)",
            required=False,
            default="720P",
            enum=["720P"],
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


class Wan21KF2VPlusGeneration(BaseModelEndpoint):
    """Wan2.1 Keyframe-to-Video Plus generation endpoint."""

    @property
    def endpoint_info(self) -> ModelEndpoint:
        return ENDPOINT


def main() -> int:
    """CLI entry point."""
    return Wan21KF2VPlusGeneration().run()


if __name__ == "__main__":
    raise SystemExit(main())
