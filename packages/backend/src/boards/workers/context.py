"""Execution context passed to generators for storage/DB/progress access."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

from ..progress.publisher import ProgressPublisher
from ..progress.models import ProgressUpdate
from ..generators import resolution
from ..database.connection import get_async_session
from ..jobs import repository as jobs_repo

logger = logging.getLogger(__name__)


class GeneratorExecutionContext:
    def __init__(self, generation_id: UUID, publisher: ProgressPublisher) -> None:
        self.generation_id = str(generation_id)
        self.publisher = publisher
        self.provider_correlation_id = uuid4().hex
        logger.info(f"Created execution context for generation {generation_id}")

    async def resolve_artifact(self, artifact) -> str:
        """Resolve an artifact to a file path."""
        logger.debug(f"Resolving artifact for generation {self.generation_id}")
        try:
            result = await resolution.resolve_artifact(artifact)
            logger.debug(f"Artifact resolved successfully: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to resolve artifact: {e}")
            raise

    async def store_image_result(self, *args, **kwargs):
        """Store image generation result."""
        logger.debug(f"Storing image result for generation {self.generation_id}")
        try:
            result = await resolution.store_image_result(*args, **kwargs)
            logger.info(f"Image result stored for generation {self.generation_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to store image result: {e}")
            raise

    async def store_video_result(self, *args, **kwargs):
        """Store video generation result."""
        logger.debug(f"Storing video result for generation {self.generation_id}")
        try:
            result = await resolution.store_video_result(*args, **kwargs)
            logger.info(f"Video result stored for generation {self.generation_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to store video result: {e}")
            raise

    async def store_audio_result(self, *args, **kwargs):
        """Store audio generation result."""
        logger.debug(f"Storing audio result for generation {self.generation_id}")
        try:
            result = await resolution.store_audio_result(*args, **kwargs)
            logger.info(f"Audio result stored for generation {self.generation_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to store audio result: {e}")
            raise

    async def publish_progress(self, update: ProgressUpdate) -> None:
        """Publish progress update for the generation."""
        logger.debug(
            f"Publishing progress for {self.generation_id}: "
            f"status={update.status}, progress={update.progress}"
        )
        try:
            await self.publisher.publish_progress(self.generation_id, update)
        except Exception as e:
            logger.error(f"Failed to publish progress: {e}")
            # Don't raise here - progress updates are non-critical

    async def set_external_job_id(self, external_id: str) -> None:
        """Set the external job ID from the provider."""
        logger.info(f"Setting external job ID {external_id} for {self.generation_id}")
        async with get_async_session() as session:
            try:
                await jobs_repo.set_external_job_id(
                    session, self.generation_id, external_id
                )
                await session.commit()
                logger.debug(f"External job ID {external_id} set successfully")
            except Exception as e:
                logger.error(f"Failed to set external job ID: {e}")
                await session.rollback()
                raise
