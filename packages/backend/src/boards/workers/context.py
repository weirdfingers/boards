"""Execution context passed to generators for storage/DB/progress access."""

from __future__ import annotations

from uuid import UUID, uuid4

from ..database.connection import get_async_session
from ..generators import resolution
from ..jobs import repository as jobs_repo
from ..logging import get_logger
from ..progress.models import ProgressUpdate
from ..progress.publisher import ProgressPublisher

logger = get_logger(__name__)


class GeneratorExecutionContext:
    def __init__(self, generation_id: UUID, publisher: ProgressPublisher) -> None:
        self.generation_id = str(generation_id)
        self.publisher = publisher
        self.provider_correlation_id = uuid4().hex
        logger.info("Created execution context", generation_id=str(generation_id))

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

    async def store_image_result(self, *args, **kwargs):
        """Store image generation result."""
        logger.debug("Storing image result", generation_id=self.generation_id)
        try:
            result = await resolution.store_image_result(*args, **kwargs)
            logger.info("Image result stored", generation_id=self.generation_id)
            return result
        except Exception as e:
            logger.error("Failed to store image result", error=str(e))
            raise

    async def store_video_result(self, *args, **kwargs):
        """Store video generation result."""
        logger.debug("Storing video result", generation_id=self.generation_id)
        try:
            result = await resolution.store_video_result(*args, **kwargs)
            logger.info("Video result stored", generation_id=self.generation_id)
            return result
        except Exception as e:
            logger.error("Failed to store video result", error=str(e))
            raise

    async def store_audio_result(self, *args, **kwargs):
        """Store audio generation result."""
        logger.debug("Storing audio result", generation_id=self.generation_id)
        try:
            result = await resolution.store_audio_result(*args, **kwargs)
            logger.info("Audio result stored", generation_id=self.generation_id)
            return result
        except Exception as e:
            logger.error("Failed to store audio result", error=str(e))
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
            logger.error("Failed to publish progress", error=str(e))
            # Don't raise here - progress updates are non-critical

    async def set_external_job_id(self, external_id: str) -> None:
        """Set the external job ID from the provider."""
        logger.info(
            "Setting external job ID",
            external_job_id=external_id,
            generation_id=self.generation_id,
        )
        async with get_async_session() as session:
            await jobs_repo.set_external_job_id(session, self.generation_id, external_id)
