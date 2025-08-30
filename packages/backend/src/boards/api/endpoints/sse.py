"""
Server-Sent Events (SSE) endpoints for real-time updates
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def sse_status():
    """SSE status endpoint."""
    return {"status": "SSE endpoint ready"}