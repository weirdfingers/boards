"""
Server-Sent Events (SSE) endpoints for real-time generation progress.
"""

from __future__ import annotations

import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import redis.asyncio as redis

from ...config import Settings


router = APIRouter()
_settings = Settings()
_redis = redis.from_url(_settings.redis_url, decode_responses=True)


@router.get("/generations/{generation_id}/progress")
async def generation_progress_stream(generation_id: str, request: Request):
    """Server-sent events for job progress, backed by Redis pub/sub."""

    channel = f"job:{generation_id}:progress"

    async def event_stream():
        pubsub = _redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            while True:
                if await request.is_disconnected():
                    break
                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if msg and msg.get("type") == "message":
                    yield f"data: {msg['data']}\n\n"
                else:
                    await asyncio.sleep(15)
                    yield ": keep-alive\n\n"
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
