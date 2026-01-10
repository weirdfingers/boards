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


def _get_extension_from_content_type(content_type: str) -> str:
    """Get file extension from content type.

    Args:
        content_type: MIME type (e.g., 'video/mp4', 'image/png', 'audio/mpeg')

    Returns:
        File extension with dot (e.g., '.mp4', '.png', '.mp3')
    """
    # Map common content types to extensions
    content_type_map = {
        # Video
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/quicktime": ".mov",
        "video/x-msvideo": ".avi",
        # Image
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/webp": ".webp",
        "image/gif": ".gif",
        # Audio
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/wav": ".wav",
        "audio/ogg": ".ogg",
        "audio/aac": ".aac",
        # Text
        "text/plain": ".txt",
        "text/html": ".html",
    }

    return content_type_map.get(content_type.lower(), "")


@router.get("/{full_path:path}")
async def serve_file(full_path: str, download: bool = False, filename: str | None = None):
    """Serve a file from local storage.

    This endpoint serves files that were uploaded to local storage.
    The full_path includes the tenant_id/artifact_type/board_id/artifact_id/variant structure.

    Args:
        full_path: Path to the file in storage
        download: If True, force download with Content-Disposition: attachment
        filename: Optional custom filename (without extension) to use for download
    """
    try:
        logger.info("Serving file", full_path=full_path, download=download, filename=filename)

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

        # Determine the proper filename with extension
        base_filename = filename if filename else file_path.stem
        final_filename = file_path.name
        has_extension = False

        # Try to get metadata from storage to determine content type and proper extension
        try:
            metadata = await local_provider.get_metadata(full_path)
            content_type = metadata.get("content_type")

            if content_type:
                extension = _get_extension_from_content_type(content_type)
                if extension:
                    # Use custom filename if provided, otherwise use file stem
                    final_filename = f"{base_filename}{extension}"
                    has_extension = True
                    logger.info(
                        "Determined filename from storage metadata",
                        original=file_path.name,
                        new_filename=final_filename,
                        content_type=content_type,
                        custom_filename=filename,
                    )
        except Exception as e:
            # Log but don't fail if we can't get metadata
            logger.warning("Failed to get storage metadata", path=full_path, error=str(e))

        # Serve the file with proper filename
        # Only set Content-Disposition if:
        # 1. Download is explicitly requested, OR
        # 2. We have a proper extension from metadata
        headers = {}
        if download:
            # Force download with attachment
            headers["Content-Disposition"] = f'attachment; filename="{final_filename}"'
        elif has_extension:
            # We have proper metadata, suggest filename but allow inline preview
            headers["Content-Disposition"] = f'inline; filename="{final_filename}"'
        # else: No Content-Disposition header - let browser decide based on content-type

        return FileResponse(file_path, filename=final_filename, headers=headers)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error serving file", path=full_path, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e
