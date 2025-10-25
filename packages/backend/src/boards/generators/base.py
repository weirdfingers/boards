"""
Base generator classes and interfaces for the Boards generators system.
"""

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from ..progress.models import ProgressUpdate
from .artifacts import AudioArtifact, ImageArtifact, VideoArtifact


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
    async def generate(self, inputs: BaseModel, context: "GeneratorExecutionContext") -> BaseModel:
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

    def get_output_schema(self) -> type[BaseModel]:
        """
        Return the Pydantic model class that defines the output schema for this generator.

        By default, this assumes the generate method returns the output directly.
        Override this method if you need custom output schema definition.

        Returns:
            Type[BaseModel]: Pydantic model class for output validation
        """
        # This is a simple default implementation
        # Generators can override this if they need custom output schemas
        return BaseModel

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', type='{self.artifact_type}')>"


@runtime_checkable
class GeneratorExecutionContext(Protocol):
    """Typed protocol for the execution context passed to generators."""

    generation_id: str
    provider_correlation_id: str

    async def resolve_artifact(self, artifact: BaseModel) -> str: ...

    async def store_image_result(self, *args: Any, **kwargs: Any) -> ImageArtifact: ...

    async def store_video_result(self, *args: Any, **kwargs: Any) -> VideoArtifact: ...

    async def store_audio_result(self, *args: Any, **kwargs: Any) -> AudioArtifact: ...

    async def publish_progress(self, update: ProgressUpdate) -> None: ...

    async def set_external_job_id(self, external_id: str) -> None: ...
