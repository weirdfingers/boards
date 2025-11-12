"""
Base generator classes and interfaces for the Boards generators system.
"""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from ..progress.models import ProgressUpdate
from .artifacts import (
    AudioArtifact,
    DigitalArtifact,
    ImageArtifact,
    TextArtifact,
    VideoArtifact,
)


class GeneratorResult(BaseModel):
    """All generators return a list of urls to the artifacts they produce."""

    outputs: list[DigitalArtifact]


class BaseGenerator(ABC):
    """
    Abstract base class for all generators in the Boards system.

    Generators define input/output schemas using Pydantic models and implement
    the generation logic using provider SDKs directly.
    """

    # Class attributes that subclasses must define
    name: str
    artifact_type: str  # 'image', 'video', 'audio', 'text', 'lora'
    description: str

    @abstractmethod
    def get_input_schema(self) -> type[BaseModel]:
        """
        Return the Pydantic model class that defines the input schema for this generator.

        Returns:
            Type[BaseModel]: Pydantic model class for input validation
        """
        pass

    @abstractmethod
    async def generate(
        self, inputs: BaseModel, context: "GeneratorExecutionContext"
    ) -> GeneratorResult:
        """
        Execute the generation process using the provided inputs.

        Args:
            inputs: Validated input data matching the input schema

        Returns:
            BaseModel: Generated output matching the output schema
        """
        pass

    @abstractmethod
    async def estimate_cost(self, inputs: BaseModel) -> float:
        """
        Estimate the cost of running this generation in USD.

        Args:
            inputs: Input data for cost estimation

        Returns:
            float: Estimated cost in USD
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', type='{self.artifact_type}')>"


@runtime_checkable
class GeneratorExecutionContext(Protocol):
    """Typed protocol for the execution context passed to generators.

    This protocol defines the interface that generators can use to interact
    with storage, database, and progress tracking systems.
    """

    async def resolve_artifact(self, artifact: DigitalArtifact) -> str:
        """Resolve an artifact to a local file path for use with provider SDKs."""
        ...

    async def store_image_result(
        self,
        storage_url: str,
        format: str,
        width: int | None = None,
        height: int | None = None,
        output_index: int = 0,
    ) -> ImageArtifact:
        """Store an image result to permanent storage."""
        ...

    async def store_video_result(
        self,
        storage_url: str,
        format: str,
        width: int | None = None,
        height: int | None = None,
        duration: float | None = None,
        fps: float | None = None,
        output_index: int = 0,
    ) -> VideoArtifact:
        """Store a video result to permanent storage."""
        ...

    async def store_audio_result(
        self,
        storage_url: str,
        format: str,
        duration: float | None = None,
        sample_rate: int | None = None,
        channels: int | None = None,
        output_index: int = 0,
    ) -> AudioArtifact:
        """Store an audio result to permanent storage."""
        ...

    async def store_text_result(
        self,
        content: str,
        format: str,
        output_index: int = 0,
    ) -> TextArtifact:
        """Store a text result to permanent storage."""
        ...

    async def publish_progress(self, update: ProgressUpdate) -> None:
        """Publish a progress update for this generation."""
        ...

    async def set_external_job_id(self, external_id: str) -> None:
        """Set the external job ID from the provider (e.g., Replicate prediction ID)."""
        ...
