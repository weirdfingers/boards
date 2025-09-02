"""
Lipsync generator using Replicate API.

This demonstrates how generators can use multiple artifact inputs
with automatic artifact resolution.
"""
from typing import Type, Optional
from pydantic import BaseModel, Field

from ...base import BaseGenerator
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
    
    async def generate(self, inputs: LipsyncInput) -> LipsyncOutput:
        """Generate lip-synced video."""
        # Import SDK directly
        try:
            import replicate  # type: ignore
        except ImportError:
            raise ValueError("replicate package not installed. Run: pip install replicate")
        
        # System automatically resolves artifacts to file paths
        audio_file = await resolve_artifact(inputs.audio_source)
        video_file = await resolve_artifact(inputs.video_source)
        
        # Use Replicate SDK directly
        result = await replicate.async_run(
            "cjwbw/wav2lip",
            input={
                "audio": open(audio_file, "rb"),
                "video": open(video_file, "rb"),
            }
        )
        
        # Store output and create artifact
        video_artifact = await store_video_result(
            storage_url=result,  # Result is the output URL
            format="mp4",
            generation_id="temp_gen_id",  # TODO: Get from context
            width=inputs.video_source.width,  # Preserve input dimensions
            height=inputs.video_source.height,
            duration=inputs.audio_source.duration,  # Duration matches audio
        )
        
        return LipsyncOutput(video=video_artifact)
    
    async def estimate_cost(self, inputs: LipsyncInput) -> float:
        """Estimate cost for lipsync generation."""
        # Wav2Lip is typically free on Replicate, but let's add a small cost
        return 0.01


# Register the generator
registry.register(LipsyncGenerator())