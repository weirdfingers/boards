"""
Server-Sent Events (SSE) endpoints for real-time generation progress.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import Settings
from ...database.connection import get_db_session
from ...jobs import repository as jobs_repo
from ...logging import get_logger
from ...redis_pool import get_redis_client
from ..auth import AuthenticatedUser, get_current_user

logger = get_logger(__name__)


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

    logger.info(
        "SSE: generation progress stream requested",
        generation_id=generation_id,
        url=request.url,
    )
    # Verify user has access to this generation
    try:
        generation = await jobs_repo.get_generation(db, generation_id)

        # Check if user owns this generation or belongs to the same tenant
        if generation.user_id != current_user.user_id:
            # Allow tenant-level access (users in same tenant can see each other's jobs)
            # You may want to make this more restrictive based on your requirements
            if generation.tenant_id != current_user.tenant_id:
                logger.warning(
                    "User attempted to access generation belonging to different user",
                    user_id=str(current_user.user_id),
                    generation_id=generation_id,
                    owner_user_id=str(generation.user_id),
                )
                raise HTTPException(
                    status_code=403,
                    detail="You don't have permission to access this generation",
                )

        logger.info(
            "User connected to progress stream",
            user_id=str(current_user.user_id),
            generation_id=generation_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to verify access to generation",
            generation_id=generation_id,
            error=str(e),
        )
        raise HTTPException(status_code=404, detail="Generation not found") from e

    channel = f"job:{generation_id}:progress"

    async def event_stream():
        pubsub = _redis.pubsub()
        await pubsub.subscribe(channel)
        logger.info(
            "SSE: Subscribed to Redis channel",
            generation_id=generation_id,
            channel=channel,
        )
        try:
            while True:
                if await request.is_disconnected():
                    logger.info(
                        "Client disconnected from progress stream",
                        generation_id=generation_id,
                    )
                    break
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg:
                    logger.info(
                        "SSE: pubsub message received",
                        message=msg,
                        msg_type=msg.get("type"),
                    )
                if msg and msg.get("type") == "message":
                    data = msg["data"]
                    logger.info(
                        "SSE: sending progress data to client",
                        generation_id=generation_id,
                        data_preview=(data[:100] if isinstance(data, str) else str(data)[:100]),
                    )
                    yield f"data: {data}\n\n"
                else:
                    # Send keep-alive every 15 seconds to prevent timeout
                    await asyncio.sleep(15)
                    logger.debug("SSE: sending keep-alive", generation_id=generation_id)
                    yield ": keep-alive\n\n"
        finally:
            logger.info(
                "SSE: Cleaning up stream",
                generation_id=generation_id,
            )
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
