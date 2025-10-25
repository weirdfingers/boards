"""
Webhook endpoints for external service integrations
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def webhook_status():
    """Webhook status endpoint."""
    return {"status": "Webhook endpoint ready"}
