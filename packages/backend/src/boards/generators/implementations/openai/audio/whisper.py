"""
Whisper audio transcription using OpenAI API.

Demonstrates audio processing generator that outputs text.
"""

from pydantic import BaseModel, Field

from ....artifacts import AudioArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class WhisperInput(BaseModel):
    """Input schema for Whisper transcription."""

    audio_source: AudioArtifact = Field(description="Audio file to transcribe")
    language: str = Field(default="en", description="Language code (e.g., 'en', 'es', 'fr')")
    prompt: str = Field(default="", description="Optional prompt to guide transcription")


class OpenAIWhisperGenerator(BaseGenerator):
    """Whisper speech-to-text transcription using OpenAI API."""

    name = "openai-whisper"
    artifact_type = "text"
    description = "OpenAI: Whisper - speech-to-text transcription"

    def get_input_schema(self) -> type[WhisperInput]:
        return WhisperInput

    async def generate(
        self, inputs: WhisperInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Transcribe audio using OpenAI Whisper."""
        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            raise ImportError(
                "OpenAI SDK is required for WhisperGenerator. "
                "Install with: pip install weirdfingers-boards[generators-openai]"
            ) from e

        client = AsyncOpenAI()

        # Resolve audio artifact to file path via context
        audio_file_path = await context.resolve_artifact(inputs.audio_source)

        # Use OpenAI SDK for transcription
        with open(audio_file_path, "rb") as audio_file:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=inputs.language,
                prompt=inputs.prompt,
            )

        # Create text artifact
        text_artifact = await context.store_text_result(
            content=transcript.text,
            format="plain",
        )

        return GeneratorResult(outputs=[text_artifact])

    async def estimate_cost(self, inputs: WhisperInput) -> float:
        """Estimate cost for Whisper transcription."""
        # Whisper pricing is $0.006 per minute
        duration_minutes = (inputs.audio_source.duration or 60) / 60
        return duration_minutes * 0.006
