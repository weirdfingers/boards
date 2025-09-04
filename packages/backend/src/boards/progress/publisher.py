"""Publisher for progress updates via Redis pub/sub with DB persistence."""

from __future__ import annotations

import logging

from ..config import Settings
from ..database.connection import get_async_session
from ..jobs import repository as jobs_repo
from ..redis_pool import get_redis_client
from .models import ProgressUpdate

logger = logging.getLogger(__name__)


class ProgressPublisher:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        # Use the shared Redis connection pool
        self._redis = get_redis_client()

    async def publish_progress(self, job_id: str, update: ProgressUpdate) -> None:
        channel = f"job:{job_id}:progress"
        await self._persist_update(job_id, update)
        await self._redis.publish(channel, update.model_dump_json())

    async def _persist_update(self, job_id: str, update: ProgressUpdate) -> None:
        async with get_async_session() as session:
            await jobs_repo.update_progress(
                session,
                generation_id=job_id,
                status=update.status,
                progress=(
                    update.progress * 100 if update.progress <= 1.0 else update.progress
                ),
                error_message=update.message if update.status == "failed" else None,
            )
