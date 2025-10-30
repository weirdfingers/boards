"""Execution context passed to generators for storage/DB/progress access."""

from __future__ import annotations

from uuid import UUID

from ..database.connection import get_async_session
from ..generators import resolution
from ..generators.artifacts import AudioArtifact, ImageArtifact, TextArtifact, VideoArtifact
from ..jobs import repository as jobs_repo
from ..logging import get_logger
from ..progress.models import ProgressUpdate
from ..progress.publisher import ProgressPublisher
from ..storage.base import StorageManager

logger = get_logger(__name__)


class GeneratorExecutionContext:
    def __init__(
        self,
        generation_id: UUID,
        publisher: ProgressPublisher,
        storage_manager: StorageManager,
        tenant_id: UUID,
        board_id: UUID,
    ) -> None:
        self.generation_id = str(generation_id)
        self.publisher = publisher
        self.storage_manager = storage_manager
        self.tenant_id = str(tenant_id)
        self.board_id = str(board_id)
        logger.info(
            "Created execution context",
            generation_id=str(generation_id),
            tenant_id=str(tenant_id),
            board_id=str(board_id),
        )

    async def resolve_artifact(self, artifact) -> str:
        """Resolve an artifact to a file path."""
        logger.debug("Resolving artifact", generation_id=self.generation_id)
        try:
            result = await resolution.resolve_artifact(artifact)
            logger.debug("Artifact resolved successfully", result=result)
            return result
        except Exception as e:
            logger.error("Failed to resolve artifact", error=str(e))
            raise

    async def store_image_result(
        self,
        storage_url: str,
        format: str,
        width: int,
        height: int,
    ) -> ImageArtifact:
        """Store image generation result."""
        logger.debug("Storing image result", generation_id=self.generation_id)
        try:
            result = await resolution.store_image_result(
                storage_manager=self.storage_manager,
                generation_id=self.generation_id,
                tenant_id=self.tenant_id,
                board_id=self.board_id,
                storage_url=storage_url,
                format=format,
                width=width,
                height=height,
            )
            logger.info("Image result stored", generation_id=self.generation_id)
            return result
        except Exception as e:
            logger.error("Failed to store image result", error=str(e))
            raise

    async def store_video_result(
        self,
        storage_url: str,
        format: str,
        width: int,
        height: int,
        duration: float | None = None,
        fps: float | None = None,
    ) -> VideoArtifact:
        """Store video generation result."""
        logger.debug("Storing video result", generation_id=self.generation_id)
        try:
            result = await resolution.store_video_result(
                storage_manager=self.storage_manager,
                generation_id=self.generation_id,
                tenant_id=self.tenant_id,
                board_id=self.board_id,
                storage_url=storage_url,
                format=format,
                width=width,
                height=height,
                duration=duration,
                fps=fps,
            )
            logger.info("Video result stored", generation_id=self.generation_id)
            return result
        except Exception as e:
            logger.error("Failed to store video result", error=str(e))
            raise

    async def store_audio_result(
        self,
        storage_url: str,
        format: str,
        duration: float | None = None,
        sample_rate: int | None = None,
        channels: int | None = None,
    ) -> AudioArtifact:
        """Store audio generation result."""
        logger.debug("Storing audio result", generation_id=self.generation_id)
        try:
            result = await resolution.store_audio_result(
                storage_manager=self.storage_manager,
                generation_id=self.generation_id,
                tenant_id=self.tenant_id,
                board_id=self.board_id,
                storage_url=storage_url,
                format=format,
                duration=duration,
                sample_rate=sample_rate,
                channels=channels,
            )
            logger.info("Audio result stored", generation_id=self.generation_id)
            return result
        except Exception as e:
            logger.error("Failed to store audio result", error=str(e))
            raise

    async def store_text_result(
        self,
        content: str,
        format: str,
    ) -> TextArtifact:
        """Store text generation result."""
        logger.debug("Storing text result", generation_id=self.generation_id)
        try:
            result = await resolution.store_text_result(
                storage_manager=self.storage_manager,
                generation_id=self.generation_id,
                tenant_id=self.tenant_id,
                board_id=self.board_id,
                content=content,
                format=format,
            )
            logger.info("Text result stored", generation_id=self.generation_id)
            return result
        except Exception as e:
            logger.error("Failed to store text result", error=str(e))
            raise

    async def publish_progress(self, update: ProgressUpdate) -> None:
        """Publish progress update for the generation."""
        logger.debug(
            "Publishing progress",
            generation_id=self.generation_id,
            status=update.status,
            progress=update.progress,
        )
        try:
            await self.publisher.publish_progress(self.generation_id, update)
        except Exception as e:
            logger.error(
                "Failed to publish progress update - "
                "generation will continue but progress may not be visible",
                generation_id=self.generation_id,
                status=update.status,
                progress=update.progress,
                error=str(e),
                error_type=type(e).__name__,
            )
            # Don't raise here - progress updates are non-critical
            # The generation should continue even if progress updates fail

    async def set_external_job_id(self, external_id: str) -> None:
        """Set the external job ID from the provider."""
        logger.info(
            "Setting external job ID",
            external_job_id=external_id,
            generation_id=self.generation_id,
        )
        async with get_async_session() as session:
            await jobs_repo.set_external_job_id(session, self.generation_id, external_id)
