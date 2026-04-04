"""
Kie.ai Seedance 2.0 Fast text-to-video and multimodal video generator.

Generate videos quickly from text prompts with optional image, video, and audio
inputs using ByteDance's Seedance 2.0 Fast model via Kie.ai's Market API.

Optimized for speed and cost efficiency compared to standard Seedance 2.0,
with the same multimodal input support and native audio output.

Based on Kie.ai's Seedance 2.0 Fast API.
See: https://docs.kie.ai/market/bytedance/seedance-2-fast
"""

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from ....artifacts import AudioArtifact, ImageArtifact, VideoArtifact
from ....base import GeneratorExecutionContext, GeneratorResult
from ..base import KieMarketAPIGenerator
from .seedance2 import _calculate_dimensions, _extract_video_urls


class KieSeedance2FastInput(BaseModel):
    """Input schema for Kie.ai Seedance 2.0 Fast video generation.

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


class KieSeedance2FastGenerator(KieMarketAPIGenerator):
    """Seedance 2.0 Fast video generator using Kie.ai Market API."""

    name = "kie-seedance-2-fast"
    artifact_type = "video"
    description = "Kie.ai: ByteDance Seedance 2.0 Fast - Fast AI video generation with native audio"

    # Market API configuration
    model_id = "bytedance/seedance-2-fast"

    def get_input_schema(self) -> type[KieSeedance2FastInput]:
        return KieSeedance2FastInput

    async def generate(
        self, inputs: KieSeedance2FastInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate video using Kie.ai Seedance 2.0 Fast model."""
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

    async def estimate_cost(self, inputs: KieSeedance2FastInput) -> float:
        """Estimate cost for Seedance 2.0 Fast video generation.

        Pricing per second varies by resolution and whether video input is used:
        - 480p: $0.0775/sec (text) | $0.045/sec (with video input)
        - 720p: $0.165/sec (text) | $0.10/sec (with video input)
        """
        has_video_input = inputs.reference_video_sources is not None

        if inputs.resolution == "480p":
            rate = 0.045 if has_video_input else 0.0775
        else:  # 720p
            rate = 0.10 if has_video_input else 0.165

        return rate * inputs.duration
