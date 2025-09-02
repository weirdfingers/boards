"""Execution context passed to generators for storage/DB/progress access."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from ..progress.publisher import ProgressPublisher
from ..progress.models import ProgressUpdate
from ..generators import resolution
from ..database.connection import get_async_session
from ..jobs import repository as jobs_repo


class GeneratorExecutionContext:
    def __init__(self, generation_id: UUID, publisher: ProgressPublisher) -> None:
        self.generation_id = str(generation_id)
        self.publisher = publisher
        self.provider_correlation_id = uuid4().hex

    async def resolve_artifact(self, artifact) -> str:
        return await resolution.resolve_artifact(artifact)

    async def store_image_result(self, *args, **kwargs):
        return await resolution.store_image_result(*args, **kwargs)

    async def store_video_result(self, *args, **kwargs):
        return await resolution.store_video_result(*args, **kwargs)

    async def store_audio_result(self, *args, **kwargs):
        return await resolution.store_audio_result(*args, **kwargs)

    async def publish_progress(self, update: ProgressUpdate) -> None:
        await self.publisher.publish_progress(self.generation_id, update)

    async def set_external_job_id(self, external_id: str) -> None:
        async with get_async_session() as session:
            await jobs_repo.set_external_job_id(
                session, self.generation_id, external_id
            )
