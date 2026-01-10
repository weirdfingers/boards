"""File upload endpoints for artifact uploads."""

import os
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ...auth import get_auth_context
from ...auth.context import AuthContext
from ...config import settings
from ...logging import get_logger

router = APIRouter(prefix="/uploads", tags=["uploads"])
logger = get_logger(__name__)


@router.post("/artifact")
async def upload_artifact_file(
    board_id: Annotated[str, Form()],
    artifact_type: Annotated[str, Form()],  # image, video, audio, text
    file: UploadFile = File(...),
    user_description: Annotated[str | None, Form()] = None,
    parent_generation_id: Annotated[str | None, Form()] = None,
    auth_context: AuthContext = Depends(get_auth_context),
) -> dict:
    """
    Upload artifact file (synchronous).

    Args:
        board_id: UUID of the board to upload to
        artifact_type: Type of artifact (image, video, audio, text)
        file: The file to upload
        user_description: Optional description provided by user
        parent_generation_id: Optional parent generation UUID
        auth_context: Authentication context

    Returns:
        Generation object as JSON

    Raises:
        HTTPException: If validation fails or upload errors occur
    """
    from ...graphql.resolvers.upload import upload_artifact_from_file

    # Validate authentication
    if not auth_context.is_authenticated or not auth_context.user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate artifact type
    valid_types = {"image", "video", "audio", "text"}
    if artifact_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid artifact_type. Must be one of: {', '.join(valid_types)}",
        )

    # Read file content
    try:
        content = await file.read()
    except Exception as e:
        logger.error("Failed to read uploaded file", error=str(e), filename=file.filename)
        raise HTTPException(
            status_code=400,
            detail="Failed to read uploaded file",
        ) from e

    # Validate file size
    if len(content) > settings.max_upload_size:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File size {len(content)} bytes exceeds maximum allowed size "
                f"of {settings.max_upload_size} bytes"
            ),
        )

    # Validate extension
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext and file_ext not in settings.allowed_upload_extensions:
        allowed_exts = ", ".join(settings.allowed_upload_extensions)
        raise HTTPException(
            status_code=400,
            detail=(
                f"File extension '{file_ext}' is not allowed. Allowed extensions: {allowed_exts}"
            ),
        )

    # Parse UUIDs
    try:
        board_uuid = UUID(board_id)
        parent_uuid = UUID(parent_generation_id) if parent_generation_id else None
    except ValueError as e:
        logger.warning("Invalid UUID provided", board_id=board_id, error=str(e))
        raise HTTPException(
            status_code=400,
            detail="Invalid board_id or parent_generation_id format",
        ) from e

    # Call resolver
    try:
        generation = await upload_artifact_from_file(
            auth_context=auth_context,
            board_id=board_uuid,
            artifact_type=artifact_type,
            file_content=content,
            filename=file.filename,
            content_type=file.content_type,
            user_description=user_description,
            parent_generation_id=parent_uuid,
        )

        logger.info(
            "File upload successful",
            generation_id=str(generation.id),
            artifact_type=artifact_type,
            file_size=len(content),
        )

        return {
            "id": str(generation.id),
            "status": generation.status.value,
            "storageUrl": generation.storage_url,
            "thumbnailUrl": generation.thumbnail_url,
            "artifactType": generation.artifact_type.value,
            "generatorName": generation.generator_name,
        }

    except RuntimeError as e:
        # These are expected errors (permission denied, board not found, etc.)
        # Pass through the message since these are safe, user-facing errors
        logger.warning("Upload failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        # Unexpected errors - don't expose internal details
        logger.error(
            "Unexpected error during upload",
            error=str(e),
            board_id=board_id,
            artifact_type=artifact_type,
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during upload",
        ) from e
