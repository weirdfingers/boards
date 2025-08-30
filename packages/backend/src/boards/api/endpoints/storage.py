"""
Storage endpoints for file uploads and management
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def storage_status():
    """Storage status endpoint."""
    return {"status": "Storage endpoint ready"}