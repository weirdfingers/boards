"""
Storage endpoints for file uploads and management
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ...logging import get_logger
from ...storage.factory import create_storage_manager
from ...storage.implementations.local import LocalStorageProvider

logger = get_logger(__name__)
router = APIRouter()


@router.get("/status")
async def storage_status():
    """Storage status endpoint."""
    return {"status": "Storage endpoint ready"}


@router.get("/{full_path:path}")
async def serve_file(full_path: str):
    """Serve a file from local storage.

    This endpoint serves files that were uploaded to local storage.
    The full_path includes the tenant_id/artifact_type/board_id/artifact_id/variant structure.
    """
    try:
        logger.info("Serving file", full_path=full_path)
        # Create storage manager to get the configured local storage path
        storage_manager = create_storage_manager()

        # Get the local provider (assumes 'local' is the provider name)
        local_provider = storage_manager.providers.get("local")
        if not local_provider:
            raise HTTPException(status_code=500, detail="Local storage provider not configured")

        # Type check: ensure it's a LocalStorageProvider
        # This endpoint only serves local files; cloud providers return direct URLs
        if not isinstance(local_provider, LocalStorageProvider):
            raise HTTPException(
                status_code=500,
                detail="Storage provider does not support local file serving",
            )

        base_path = local_provider.base_path
        file_path = Path(base_path) / full_path

        # Security check: ensure the resolved path is within base_path
        try:
            file_path.resolve().relative_to(Path(base_path).resolve())
        except ValueError as e:
            logger.warning("Path traversal attempt detected", requested_path=full_path)
            raise HTTPException(status_code=403, detail="Access denied") from e

        # Check if file exists
        if not file_path.exists():
            logger.warning("File not found", path=str(file_path))
            raise HTTPException(status_code=404, detail="File not found")

        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")

        # Serve the file
        return FileResponse(file_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error serving file", path=full_path, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e
