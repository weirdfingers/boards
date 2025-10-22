"""
Whisper audio transcription using OpenAI API.

Demonstrates audio processing generator that outputs text.
"""

from pydantic import BaseModel, Field

from ...artifacts import AudioArtifact, TextArtifact
from ...base import BaseGenerator, GeneratorExecutionContext


class WhisperInput(BaseModel):
    """Input schema for Whisper transcription."""

    audio_source: AudioArtifact = Field(description="Audio file to transcribe")
    language: str = Field(
        default="en", description="Language code (e.g., 'en', 'es', 'fr')"
    )
    prompt: str = Field(
        default="", description="Optional prompt to guide transcription"
    )


class WhisperOutput(BaseModel):
    """Output schema for Whisper transcription."""

    text: TextArtifact


class WhisperGenerator(BaseGenerator):
    """Whisper speech-to-text transcription using OpenAI API."""

    name = "whisper"
    artifact_type = "text"
    description = "OpenAI Whisper - speech-to-text transcription"

    def get_input_schema(self) -> type[WhisperInput]:
        return WhisperInput

    def get_output_schema(self) -> type[WhisperOutput]:
        return WhisperOutput

    async def generate(
        self, inputs: WhisperInput, context: GeneratorExecutionContext
    ) -> WhisperOutput:
        """Transcribe audio using OpenAI Whisper."""
        try:
            from openai import AsyncOpenAI  # type: ignore
        except ImportError as e:
            raise ValueError("Required dependencies not available") from e

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
        text_artifact = TextArtifact(
            generation_id=context.generation_id, content=transcript.text, format="plain"
        )

        return WhisperOutput(text=text_artifact)

    async def estimate_cost(self, inputs: WhisperInput) -> float:
        """Estimate cost for Whisper transcription."""
        # Whisper pricing is $0.006 per minute
        duration_minutes = (inputs.audio_source.duration or 60) / 60
        return duration_minutes * 0.006
