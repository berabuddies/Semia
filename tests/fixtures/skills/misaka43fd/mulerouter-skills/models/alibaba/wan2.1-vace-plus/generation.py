"""Wan2.1 VACE Plus video editing generation endpoint."""

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
    model_id="alibaba/wan2.1-vace-plus",
    action="generation",
    provider="alibaba",
    model_name="wan2.1-vace-plus",
    description="Edit videos using Wan2.1 VACE Plus model with multi-modal inputs (image reference, video repainting, local editing, video extension, video outpainting)",
    input_types=[InputType.VIDEO, InputType.IMAGE, InputType.TEXT],
    output_type=OutputType.VIDEO,
    api_path="/vendors/alibaba/v1/wan2.1-vace-plus/generation",
    result_key="videos",
    available_on=["mulerouter", "mulerun"],
    parameters=[
        ModelParameter(
            name="model",
            type="string",
            description="Model name (only wan2.1-vace-plus is supported)",
            required=True,
            enum=["wan2.1-vace-plus"],
        ),
        ModelParameter(
            name="function",
            type="string",
            description="Feature selector: image_reference, video_repainting, video_edit, video_extension, video_outpainting",
            required=True,
            enum=["image_reference", "video_repainting", "video_edit", "video_extension", "video_outpainting"],
        ),
        ModelParameter(
            name="prompt",
            type="string",
            description="Text description for the video (max 800 characters)",
            required=True,
        ),
        ModelParameter(
            name="negative_prompt",
            type="string",
            description="Negative prompt (max 500 characters)",
            required=False,
        ),
        ModelParameter(
            name="ref_images_url",
            type="array",
            description="Reference image URLs (1-3 images for image_reference, 1 for video_repainting/video_edit)",
            required=False,
        ),
        ModelParameter(
            name="obj_or_bg",
            type="array",
            description="Label each ref image as 'obj' (entity) or 'bg' (background). Required for multiple images",
            required=False,
        ),
        ModelParameter(
            name="video_url",
            type="string",
            description="Source video URL (MP4, ≤50MB, ≥16 FPS, ≤5s). Required for video_repainting, video_edit, video_outpainting",
            required=False,
        ),
        ModelParameter(
            name="control_condition",
            type="string",
            description="Feature extraction method for video_repainting/video_edit/video_extension",
            required=False,
            enum=["posebodyface", "posebody", "depth", "scribble"],
        ),
        ModelParameter(
            name="strength",
            type="number",
            description="Control strength for video_repainting (0.0-1.0, default 1.0)",
            required=False,
        ),
        ModelParameter(
            name="mask_image_url",
            type="string",
            description="Mask image URL for video_edit (white=edit, black=keep)",
            required=False,
        ),
        ModelParameter(
            name="mask_video_url",
            type="string",
            description="Mask video URL for video_edit (MP4)",
            required=False,
        ),
        ModelParameter(
            name="mask_frame_id",
            type="integer",
            description="1-based frame index where mask applies (default: 1)",
            required=False,
        ),
        ModelParameter(
            name="mask_type",
            type="string",
            description="Mask behavior for video_edit: tracking or fixed",
            required=False,
            enum=["tracking", "fixed"],
        ),
        ModelParameter(
            name="expand_ratio",
            type="number",
            description="Expansion ratio for tracking masks (0.0-1.0, default 0.05)",
            required=False,
        ),
        ModelParameter(
            name="expand_mode",
            type="string",
            description="Shape of tracking mask expansion: hull, bbox, or original",
            required=False,
            enum=["hull", "bbox", "original"],
        ),
        ModelParameter(
            name="first_frame_url",
            type="string",
            description="Starting frame image URL for video_extension",
            required=False,
        ),
        ModelParameter(
            name="last_frame_url",
            type="string",
            description="Ending frame image URL for video_extension",
            required=False,
        ),
        ModelParameter(
            name="first_clip_url",
            type="string",
            description="Opening clip URL for video_extension (MP4, ≤3s)",
            required=False,
        ),
        ModelParameter(
            name="last_clip_url",
            type="string",
            description="Ending clip URL for video_extension (MP4, ≤3s)",
            required=False,
        ),
        ModelParameter(
            name="top_scale",
            type="number",
            description="Upward scaling ratio for video_outpainting (1.0-2.0)",
            required=False,
        ),
        ModelParameter(
            name="bottom_scale",
            type="number",
            description="Downward scaling ratio for video_outpainting (1.0-2.0)",
            required=False,
        ),
        ModelParameter(
            name="left_scale",
            type="number",
            description="Leftward scaling ratio for video_outpainting (1.0-2.0)",
            required=False,
        ),
        ModelParameter(
            name="right_scale",
            type="number",
            description="Rightward scaling ratio for video_outpainting (1.0-2.0)",
            required=False,
        ),
        ModelParameter(
            name="size",
            type="string",
            description="Output resolution for image_reference/video_edit",
            required=False,
            default="1280*720",
            enum=["1280*720", "720*1280", "960*960", "832*1088", "1088*832"],
        ),
        ModelParameter(
            name="duration",
            type="integer",
            description="Output duration in seconds (fixed at 5)",
            required=False,
            enum=[5],
        ),
        ModelParameter(
            name="prompt_extend",
            type="boolean",
            description="Enable prompt rewriting",
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


class Wan21VacePlusGeneration(BaseModelEndpoint):
    """Wan2.1 VACE Plus video editing endpoint."""

    @property
    def endpoint_info(self) -> ModelEndpoint:
        return ENDPOINT


def main() -> int:
    """CLI entry point."""
    return Wan21VacePlusGeneration().run()


if __name__ == "__main__":
    raise SystemExit(main())
