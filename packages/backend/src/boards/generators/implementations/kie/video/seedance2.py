"""
Kie.ai Seedance 2.0 text-to-video and multimodal video generator.

Generate high-quality videos from text prompts with optional image, video, and audio
inputs using ByteDance's Seedance 2.0 model via Kie.ai's Market API.

Features flawless real human generation, identity consistency, cinematic coherence,
multimodal inputs (text/image/video/audio), and native audio output.

Based on Kie.ai's Seedance 2.0 API.
See: https://docs.kie.ai/market/bytedance/seedance-2
"""

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from ....artifacts import AudioArtifact, ImageArtifact, VideoArtifact
from ....base import GeneratorExecutionContext, GeneratorResult
from ..base import KieMarketAPIGenerator


class KieSeedance2Input(BaseModel):
    """Input schema for Kie.ai Seedance 2.0 video generation.

    Supports text-to-video, image-to-video, video-to-video, and audio-driven modes.
    Artifact fields are automatically detected via type introspection and resolved
    from generation IDs to artifact objects.
    """

    prompt: str = Field(
        description="Text prompt describing the video to generate (3-2500 characters)",
        min_length=3,
        max_length=2500,
    )
    reference_image_sources: list[ImageArtifact] | None = Field(
        default=None,
        description="Optional reference images for guidance (max 9, max 10MB each)",
        min_length=1,
        max_length=9,
    )
    reference_video_sources: list[VideoArtifact] | None = Field(
        default=None,
        description="Optional reference videos (max 3, total duration <= 15s, max 10MB each)",
        min_length=1,
        max_length=3,
    )
    reference_audio_sources: list[AudioArtifact] | None = Field(
        default=None,
        description="Optional reference audio files (max 3, total duration <= 15s, max 10MB each)",
        min_length=1,
        max_length=3,
    )
    first_frame_image: list[ImageArtifact] | None = Field(
        default=None,
        description="Optional first frame image for the video",
        min_length=1,
        max_length=1,
    )
    last_frame_image: list[ImageArtifact] | None = Field(
        default=None,
        description="Optional last frame image for the video",
        min_length=1,
        max_length=1,
    )
    resolution: Literal["480p", "720p"] = Field(
        default="720p",
        description="Output video resolution",
    )
    aspect_ratio: Literal["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"] = Field(
        default="16:9",
        description="Aspect ratio of the generated video",
    )
    duration: Literal[4, 8, 12] = Field(
        default=8,
        description="Duration of the generated video in seconds",
    )
    generate_audio: bool = Field(
        default=True,
        description="Whether to generate AI audio synced with the video",
    )


class KieSeedance2Generator(KieMarketAPIGenerator):
    """Seedance 2.0 video generator using Kie.ai Market API."""

    name = "kie-seedance-2"
    artifact_type = "video"
    description = "Kie.ai: ByteDance Seedance 2.0 - High-quality AI video generation"

    # Market API configuration
    model_id = "bytedance/seedance-2"

    def get_input_schema(self) -> type[KieSeedance2Input]:
        return KieSeedance2Input

    async def generate(
        self, inputs: KieSeedance2Input, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using Kie.ai Seedance 2.0 model."""
        api_key = self._get_api_key()

        # Build the input parameters
        input_params: dict[str, Any] = {
            "prompt": inputs.prompt,
            "resolution": inputs.resolution,
            "aspect_ratio": inputs.aspect_ratio,
            "duration": inputs.duration,
            "generate_audio": inputs.generate_audio,
        }

        # Upload artifact inputs if provided
        from ..utils import upload_artifacts_to_kie

        if inputs.reference_image_sources:
            image_urls = await upload_artifacts_to_kie(inputs.reference_image_sources, context)
            input_params["reference_image_urls"] = image_urls

        if inputs.reference_video_sources:
            video_urls = await upload_artifacts_to_kie(inputs.reference_video_sources, context)
            input_params["reference_video_urls"] = video_urls

        if inputs.reference_audio_sources:
            audio_urls = await upload_artifacts_to_kie(inputs.reference_audio_sources, context)
            input_params["reference_audio_urls"] = audio_urls

        if inputs.first_frame_image:
            first_frame_urls = await upload_artifacts_to_kie(inputs.first_frame_image, context)
            input_params["first_frame_url"] = first_frame_urls[0]

        if inputs.last_frame_image:
            last_frame_urls = await upload_artifacts_to_kie(inputs.last_frame_image, context)
            input_params["last_frame_url"] = last_frame_urls[0]

        # Prepare request body for Market API
        body = {
            "model": self.model_id,
            "input": input_params,
        }

        # Submit task using Market API endpoint
        submit_url = "https://api.kie.ai/api/v1/jobs/createTask"
        result = await self._make_request(submit_url, "POST", api_key, json=body)

        # Extract task ID
        data = result.get("data", {})
        task_id = data.get("taskId")

        if not task_id:
            raise ValueError(f"No taskId returned from Kie.ai API. Response: {result}")

        await context.set_external_job_id(task_id)

        # Poll for completion using Market API base class method
        task_data = await self._poll_for_completion(task_id, api_key, context)

        # Extract video URLs from result
        result_json = task_data.get("resultJson")
        if result_json:
            result_data = json.loads(result_json)
        else:
            result_data = task_data.get("result")

        if not result_data:
            raise ValueError("No result data returned from Kie.ai API")

        # Extract video URLs from response
        video_urls = _extract_video_urls(result_data)

        # Determine video dimensions based on resolution and aspect ratio
        width, height = _calculate_dimensions(inputs.resolution, inputs.aspect_ratio)

        # Store each video using output_index
        artifacts = []
        for idx, video_url in enumerate(video_urls):
            if not video_url:
                raise ValueError(f"Video {idx} missing URL in Kie.ai response")

            artifact = await context.store_video_result(
                storage_url=video_url,
                format="mp4",
                width=width,
                height=height,
                duration=float(inputs.duration),
                output_index=idx,
            )
            artifacts.append(artifact)

        return GeneratorResult(outputs=artifacts)

    async def estimate_cost(self, inputs: KieSeedance2Input) -> float:
        """Estimate cost for Seedance 2.0 video generation.

        Pricing per second varies by resolution and whether video input is used:
        - 480p: $0.095/sec (text) | $0.0575/sec (with video input)
        - 720p: $0.205/sec (text) | $0.125/sec (with video input)
        """
        has_video_input = inputs.reference_video_sources is not None

        if inputs.resolution == "480p":
            rate = 0.0575 if has_video_input else 0.095
        else:  # 720p
            rate = 0.125 if has_video_input else 0.205

        return rate * inputs.duration


def _extract_video_urls(result_data: dict[str, Any] | Any) -> list[str]:
    """Extract video URLs from Market API result data."""
    if not isinstance(result_data, dict):
        raise ValueError(f"Unexpected result data format: {type(result_data)}")

    # Try common response patterns
    if "resultUrls" in result_data:
        return result_data["resultUrls"]
    if "video_urls" in result_data:
        return result_data["video_urls"]
    if "videos" in result_data:
        videos = result_data["videos"]
        if videos and isinstance(videos[0], str):
            return [str(v) for v in videos]
        return [str(v["url"]) for v in videos if isinstance(v, dict) and "url" in v]
    if "url" in result_data:
        return [result_data["url"]]

    raise ValueError(f"No video URLs found in result: {result_data}")


def _calculate_dimensions(resolution: str, aspect_ratio: str) -> tuple[int, int]:
    """Calculate pixel dimensions from resolution and aspect ratio."""
    # Base heights for each resolution
    if resolution == "480p":
        base_height = 480
    else:  # 720p
        base_height = 720

    aspect_ratios: dict[str, tuple[int, int]] = {
        "16:9": (16, 9),
        "9:16": (9, 16),
        "1:1": (1, 1),
        "4:3": (4, 3),
        "3:4": (3, 4),
        "21:9": (21, 9),
    }

    w_ratio, h_ratio = aspect_ratios.get(aspect_ratio, (16, 9))

    # Calculate width from height and aspect ratio, round to nearest even number
    if h_ratio >= w_ratio:
        # Portrait or square: height is the larger dimension
        height = base_height
        width = int(height * w_ratio / h_ratio)
    else:
        # Landscape: width is the larger dimension based on height
        height = base_height
        width = int(height * w_ratio / h_ratio)

    # Ensure dimensions are even (required for video encoding)
    width = width + (width % 2)
    height = height + (height % 2)

    return width, height
