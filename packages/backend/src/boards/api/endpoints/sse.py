"""
Server-Sent Events (SSE) endpoints for real-time generation progress.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import Settings
from ...database.connection import get_db_session
from ...jobs import repository as jobs_repo
from ...redis_pool import get_redis_client
from ..auth import AuthenticatedUser, get_current_user

logger = logging.getLogger(__name__)


router = APIRouter()
_settings = Settings()
# Use the shared Redis connection pool
_redis = get_redis_client()


@router.get("/generations/{generation_id}/progress")
async def generation_progress_stream(
    generation_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Server-sent events for job progress, backed by Redis pub/sub.

    Requires authentication. Users can only monitor progress for their own generations
    or generations within their tenant (depending on access control policy).
    """

    # Verify user has access to this generation
    try:
        generation = await jobs_repo.get_generation(db, generation_id)

        # Check if user owns this generation or belongs to the same tenant
        if generation.user_id != current_user.user_id:
            # Allow tenant-level access (users in same tenant can see each other's jobs)
            # You may want to make this more restrictive based on your requirements
            if generation.tenant_id != current_user.tenant_id:
                logger.warning(
                    f"User {current_user.user_id} attempted to access generation "
                    f"{generation_id} belonging to user {generation.user_id}"
                )
                raise HTTPException(
                    status_code=403, detail="You don't have permission to access this generation"
                )

        logger.info(f"User {current_user.user_id} connected to progress stream for {generation_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify access to generation {generation_id}: {e}")
        raise HTTPException(status_code=404, detail="Generation not found") from e

    channel = f"job:{generation_id}:progress"

    async def event_stream():
        pubsub = _redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            while True:
                if await request.is_disconnected():
                    logger.info(f"Client disconnected from progress stream {generation_id}")
                    break
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg.get("type") == "message":
                    yield f"data: {msg['data']}\n\n"
                else:
                    # Send keep-alive every 15 seconds to prevent timeout
                    await asyncio.sleep(15)
                    yield ": keep-alive\n\n"
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
