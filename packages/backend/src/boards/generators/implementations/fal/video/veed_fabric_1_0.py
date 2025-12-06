"""
VEED Fabric 1.0 image-to-video generator.

Generate talking videos from any image using VEED Fabric 1.0.
This generator turns a static image into a talking video with synchronized
lip movements based on provided audio.

Based on Fal AI's veed/fabric-1.0 model.
See: https://fal.ai/models/veed/fabric-1.0
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import AudioArtifact, ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult
from ..utils import upload_artifacts_to_fal


class VeedFabric10Input(BaseModel):
    """Input schema for VEED Fabric 1.0.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    image_url: ImageArtifact = Field(description="Image to turn into a talking video")
    audio_url: AudioArtifact = Field(description="Audio to synchronize with the image")
    resolution: Literal["720p", "480p"] = Field(
        default="720p", description="Output video resolution"
    )


class FalVeedFabric10Generator(BaseGenerator):
    """Generator for turning images into talking videos using VEED Fabric 1.0."""

    name = "veed-fabric-1.0"
    description = "VEED: Fabric 1.0 - Turn any image into a talking video"
    artifact_type = "video"

    def get_input_schema(self) -> type[VeedFabric10Input]:
        """Return the input schema for this generator."""
        return VeedFabric10Input

    async def generate(
        self, inputs: VeedFabric10Input, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate talking video using VEED Fabric 1.0."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for FalVeedFabric10Generator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # Upload image and audio artifacts to Fal's public storage
        # Fal API requires publicly accessible URLs
        image_urls = await upload_artifacts_to_fal([inputs.image_url], context)
        audio_urls = await upload_artifacts_to_fal([inputs.audio_url], context)

        # Prepare arguments for fal.ai API
        arguments = {
            "image_url": image_urls[0],
            "audio_url": audio_urls[0],
            "resolution": inputs.resolution,
        }

        # Submit async job
        handler = await fal_client.submit_async(
            "veed/fabric-1.0",
            arguments=arguments,
        )

        # Store external job ID
        await context.set_external_job_id(handler.request_id)

        # Stream progress updates
        from .....progress.models import ProgressUpdate

        event_count = 0
        async for event in handler.iter_events(with_logs=True):
            event_count += 1
            # Sample every 3rd event to avoid spamming progress updates
            if event_count % 3 == 0:
                logs = getattr(event, "logs", None)
                if logs:
                    if isinstance(logs, list):
                        message = " | ".join(str(log) for log in logs if log)
                    else:
                        message = str(logs)

                    if message:
                        await context.publish_progress(
                            ProgressUpdate(
                                job_id=handler.request_id,
                                status="processing",
                                progress=50.0,
                                phase="processing",
                                message=message,
                            )
                        )

        # Get final result
        result = await handler.get()

        # Extract video from result
        # Fabric 1.0 API returns: {"video": {"url": "...", "content_type": "video/mp4", ...}}
        video_data = result.get("video")

        if not video_data:
            raise ValueError(
                "No video returned from VEED Fabric 1.0 API. "
                f"Response structure: {list(result.keys())}"
            )

        video_url = video_data.get("url")
        if not video_url:
            raise ValueError(
                f"Video missing URL in VEED response. Video data keys: {list(video_data.keys())}"
            )

        # Determine video format with fallback strategy:
        # 1. Try to extract from URL extension
        # 2. Parse content_type only if it's a video/* MIME type
        # 3. Default to mp4
        video_format = "mp4"  # Default

        if video_url:
            url_parts = video_url.split(".")
            if len(url_parts) > 1:
                ext = url_parts[-1].split("?")[0].lower()
                if ext in ["mp4", "webm", "mov", "avi"]:
                    video_format = ext

        if video_format == "mp4":
            content_type = video_data.get("content_type", "")
            if content_type.startswith("video/"):
                video_format = content_type.split("/")[-1]

        # Determine output dimensions based on resolution
        # 720p = 1280x720, 480p = 854x480 (16:9 aspect ratio)
        if inputs.resolution == "720p":
            output_width = 1280
            output_height = 720
        else:
            output_width = 854
            output_height = 480

        # Store the video result
        artifact = await context.store_video_result(
            storage_url=video_url,
            format=video_format,
            width=output_width,
            height=output_height,
            duration=inputs.audio_url.duration,
            fps=30.0,  # Standard frame rate for talking videos
            output_index=0,
        )

        return GeneratorResult(outputs=[artifact])

    async def estimate_cost(self, inputs: VeedFabric10Input) -> float:
        """Estimate cost for VEED Fabric 1.0 generation in USD.

        Pricing not specified in documentation, using estimate based on
        typical video lipsync processing costs.
        """
        # Fixed cost estimate of $0.08 per generation
        # Based on typical AI video processing costs
        # This is a conservative estimate and should be updated when official
        # pricing information becomes available
        return 0.08
