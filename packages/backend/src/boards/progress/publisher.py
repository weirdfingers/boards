"""Publisher for progress updates via Redis pub/sub with DB persistence."""

from __future__ import annotations

import json
import redis.asyncio as redis
from typing import Any

from ..config import Settings
from .models import ProgressUpdate
from ..database.connection import get_async_session
from ..jobs import repository as jobs_repo


class ProgressPublisher:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self._redis = redis.from_url(self.settings.redis_url, decode_responses=True)

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
