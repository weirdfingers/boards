"""Publisher for progress updates via Redis pub/sub with DB persistence."""

from __future__ import annotations

from ..config import Settings
from ..database.connection import get_async_session
from ..jobs import repository as jobs_repo
from ..logging import get_logger
from ..redis_pool import get_redis_client
from .models import ProgressUpdate

logger = get_logger(__name__)


class ProgressPublisher:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        # Use the shared Redis connection pool
        self._redis = get_redis_client()

    async def publish_progress(self, job_id: str, update: ProgressUpdate) -> None:
        """Publish progress update to Redis and persist to database."""
        channel = f"job:{job_id}:progress"
        await self._persist_update(job_id, update)
        json_data = update.model_dump_json()
        logger.info(
            "Publishing progress update to Redis",
            job_id=job_id,
            channel=channel,
            status=update.status,
            progress=update.progress,
            data_length=len(json_data),
        )
        await self._redis.publish(channel, json_data)
        logger.debug("Progress update published successfully", job_id=job_id)

    async def publish_only(self, job_id: str, update: ProgressUpdate) -> None:
        """Publish progress update to Redis without persisting to database.

        Use this when the database has already been updated separately,
        e.g., after calling finalize_success in the repository.
        """
        channel = f"job:{job_id}:progress"
        json_data = update.model_dump_json()
        logger.info(
            "Publishing progress update to Redis (no DB persist)",
            job_id=job_id,
            channel=channel,
            status=update.status,
            progress=update.progress,
            data_length=len(json_data),
        )
        await self._redis.publish(channel, json_data)
        logger.debug("Progress update published successfully", job_id=job_id)

    async def _persist_update(self, job_id: str, update: ProgressUpdate) -> None:
        async with get_async_session() as session:
            await jobs_repo.update_progress(
                session,
                generation_id=job_id,
                status=update.status,
                progress=(update.progress * 100 if update.progress <= 1.0 else update.progress),
                error_message=update.message if update.status == "failed" else None,
            )
