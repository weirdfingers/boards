"""
Lipsync generator using Replicate API.

This demonstrates how generators can use multiple artifact inputs
with automatic artifact resolution.
"""

from typing import Type, Optional
from pydantic import BaseModel, Field

from ...base import BaseGenerator, GeneratorExecutionContext
from ...artifacts import AudioArtifact, VideoArtifact
from ...resolution import resolve_artifact, store_video_result
from ...registry import registry


class LipsyncInput(BaseModel):
    """Input schema for lipsync generation."""

    audio_source: AudioArtifact = Field(description="Audio track for lip sync")
    video_source: VideoArtifact = Field(description="Video to sync lips in")
    prompt: Optional[str] = Field(None, description="Optional prompt for generation")


class LipsyncOutput(BaseModel):
    """Output schema for lipsync generation."""

    video: VideoArtifact


class LipsyncGenerator(BaseGenerator):
    """Lipsync generator that syncs lips in video to audio."""

    name = "lipsync"
    artifact_type = "video"
    description = "Sync lips in video to match audio track"

    def get_input_schema(self) -> Type[LipsyncInput]:
        return LipsyncInput

    def get_output_schema(self) -> Type[LipsyncOutput]:
        return LipsyncOutput

    async def generate(
        self, inputs: LipsyncInput, context: GeneratorExecutionContext
    ) -> LipsyncOutput:
        """Generate lip-synced video."""
        # Import SDK directly
        try:
            import replicate  # type: ignore
        except ImportError:
            raise ValueError("Required dependencies not available")

        # Resolve artifacts via context
        audio_file = await context.resolve_artifact(inputs.audio_source)
        video_file = await context.resolve_artifact(inputs.video_source)

        # Use Replicate SDK directly with proper file handling
        with open(audio_file, "rb") as audio_f, open(video_file, "rb") as video_f:
            result = await replicate.async_run(
                "cjwbw/wav2lip",
                input={
                    "audio": audio_f,
                    "video": video_f,
                },
            )

        # Store output and create artifact via context
        video_artifact = await context.store_video_result(
            storage_url=result,
            format="mp4",
            generation_id=context.generation_id,
            width=inputs.video_source.width,
            height=inputs.video_source.height,
            duration=inputs.audio_source.duration,
        )

        return LipsyncOutput(video=video_artifact)

    async def estimate_cost(self, inputs: LipsyncInput) -> float:
        """Estimate cost for lipsync generation."""
        # Wav2Lip is typically free on Replicate, but let's add a small cost
        return 0.01


# Register the generator
registry.register(LipsyncGenerator())
