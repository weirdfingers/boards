"""Resolvers for artifact upload operations."""

from __future__ import annotations

import ipaddress
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from uuid import UUID

import aiohttp
import strawberry
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ...auth.context import AuthContext
from ...database.connection import get_async_session
from ...dbmodels import Boards, Generations
from ...logging import get_logger
from ...storage.factory import create_storage_manager
from ..access_control import get_auth_context_from_info
from ..types.generation import ArtifactType

if TYPE_CHECKING:
    from ..types.generation import Generation as GenerationType
    from ..types.generation import UploadArtifactInput

logger = get_logger(__name__)


def _validate_mime_type(
    content_type: str, artifact_type: ArtifactType, filename: str | None
) -> tuple[bool, str | None]:
    """
    Validate that MIME type matches the expected artifact type.

    Args:
        content_type: The MIME type to validate (e.g., "image/jpeg")
        artifact_type: The expected artifact type enum
        filename: Optional filename for additional context

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Define allowed MIME types for each artifact type
    allowed_mime_types = {
        ArtifactType.IMAGE: [
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/gif",
            "image/webp",
            "image/bmp",
            "image/svg+xml",
        ],
        ArtifactType.VIDEO: [
            "video/mp4",
            "video/quicktime",
            "video/x-msvideo",
            "video/webm",
            "video/mpeg",
            "video/x-matroska",
        ],
        ArtifactType.AUDIO: [
            "audio/mpeg",
            "audio/mp3",
            "audio/wav",
            "audio/ogg",
            "audio/webm",
            "audio/x-m4a",
            "audio/mp4",
        ],
        ArtifactType.TEXT: [
            "text/plain",
            "text/markdown",
            "application/json",
            "text/html",
            "text/csv",
        ],
    }

    # Normalize MIME type (remove charset, etc.)
    mime_type = content_type.split(";")[0].strip().lower()

    # Check if artifact type is supported
    if artifact_type not in allowed_mime_types:
        return False, f"Unsupported artifact type: {artifact_type.value}"

    # Check if MIME type is allowed for this artifact type
    if mime_type not in allowed_mime_types[artifact_type]:
        # Also check for generic types
        mime_category = mime_type.split("/")[0]
        if mime_category != artifact_type.value:
            return (
                False,
                f"MIME type '{mime_type}' does not match artifact type '{artifact_type.value}'",
            )

    return True, None


def _is_safe_url(url: str) -> tuple[bool, str | None]:
    """
    Validate URL to prevent SSRF attacks.

    Returns:
        Tuple of (is_safe, error_message)
    """
    try:
        parsed = urlparse(url)

        # Only allow http and https
        if parsed.scheme not in ("http", "https"):
            return (
                False,
                f"URL scheme '{parsed.scheme}' not allowed. Only http and https are supported.",
            )

        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid URL: no hostname found"

        # Block localhost
        if hostname.lower() in ("localhost", "127.0.0.1", "::1"):
            return False, "Access to localhost is not allowed"

        # Try to resolve hostname to IP
        try:
            # Check if it's already an IP address
            ip = ipaddress.ip_address(hostname)

            # Block private IP ranges
            if ip.is_private:
                return False, f"Access to private IP address {ip} is not allowed"

            # Block link-local addresses (including AWS metadata endpoint)
            if ip.is_link_local:
                return False, f"Access to link-local address {ip} is not allowed"

            # Block loopback
            if ip.is_loopback:
                return False, f"Access to loopback address {ip} is not allowed"

        except ValueError:
            # Not an IP address, it's a hostname - this is OK
            # In production, you might want to resolve the hostname and check the IP
            # but that adds complexity and potential DNS rebinding issues
            pass

        return True, None

    except Exception as e:
        return False, f"Invalid URL: {e}"


async def upload_artifact_from_url(
    info: strawberry.Info,
    input: UploadArtifactInput,
) -> GenerationType:
    """Upload artifact from URL (synchronous)."""
    from ...config import settings

    auth_context = await get_auth_context_from_info(info)
    if not auth_context or not auth_context.is_authenticated:
        raise RuntimeError("Authentication required")

    if not input.file_url:
        raise RuntimeError("file_url is required")

    # Validate URL to prevent SSRF attacks
    is_safe, error_msg = _is_safe_url(input.file_url)
    if not is_safe:
        logger.warning("Unsafe URL blocked", url=input.file_url, reason=error_msg)
        raise RuntimeError(f"URL not allowed: {error_msg}")

    # Download file from URL
    async with aiohttp.ClientSession() as http_session:
        try:
            async with http_session.get(
                input.file_url, timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Failed to download from URL: HTTP {resp.status}")

                # Check Content-Length before downloading to prevent memory exhaustion
                content_length = resp.headers.get("Content-Length")
                if content_length:
                    file_size = int(content_length)
                    if file_size > settings.max_upload_size:
                        raise RuntimeError(
                            f"File size ({file_size} bytes) exceeds maximum allowed "
                            f"size ({settings.max_upload_size} bytes)"
                        )

                content = await resp.read()
                content_type = resp.headers.get("Content-Type", "application/octet-stream")

                # Extract filename from URL if not provided
                filename = input.original_filename
                if not filename:
                    path = urlparse(input.file_url).path
                    filename = path.split("/")[-1] if path else "uploaded_file"

        except aiohttp.ClientError as e:
            logger.error("URL download failed", url=input.file_url, error=str(e))
            raise RuntimeError("Failed to download file from URL") from e

    # Process upload
    return await _process_upload(
        auth_context=auth_context,
        board_id=input.board_id,
        artifact_type=input.artifact_type,
        file_content=content,
        filename=filename,
        content_type=content_type,
        user_description=input.user_description,
        parent_generation_id=input.parent_generation_id,
        upload_source="url",
        source_url=input.file_url,
    )


async def upload_artifact_from_file(
    auth_context: AuthContext,
    board_id: UUID,
    artifact_type: str,
    file_content: bytes,
    filename: str | None,
    content_type: str | None,
    user_description: str | None,
    parent_generation_id: UUID | None,
) -> GenerationType:
    """Upload artifact from file (synchronous)."""
    return await _process_upload(
        auth_context=auth_context,
        board_id=board_id,
        artifact_type=ArtifactType(artifact_type),
        file_content=file_content,
        filename=filename or "uploaded_file",
        content_type=content_type or "application/octet-stream",
        user_description=user_description,
        parent_generation_id=parent_generation_id,
        upload_source="file",
        source_url=None,
    )


def _sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and other security issues.

    Returns:
        Sanitized filename (basename only, no path components)
    """
    import os
    import re

    # Get basename only (remove any path components)
    filename = os.path.basename(filename)

    # Remove any null bytes
    filename = filename.replace("\x00", "")

    # Replace potentially dangerous characters (including backslash for Windows paths)
    filename = re.sub(r'[<>:"|?*\\]', "_", filename)

    # Remove leading/trailing whitespace and dots
    filename = filename.strip(". ")

    # If filename is empty after sanitization, use a default
    if not filename:
        filename = "uploaded_file"

    return filename


async def _process_upload(
    auth_context: AuthContext,
    board_id: UUID,
    artifact_type: ArtifactType,
    file_content: bytes,
    filename: str,
    content_type: str,
    user_description: str | None,
    parent_generation_id: UUID | None,
    upload_source: str,
    source_url: str | None,
) -> GenerationType:
    """Common upload processing logic.

    Args:
        auth_context: Authentication context for the request
        board_id: UUID of the board to upload to
        artifact_type: Type of artifact being uploaded (enum)
        file_content: Binary content of the file
        filename: Original filename
        content_type: MIME type of the file
        user_description: Optional user-provided description
        parent_generation_id: Optional parent generation UUID
        upload_source: Source of upload ("file" or "url")
        source_url: URL if uploaded from URL, None otherwise

    Returns:
        GenerationType object representing the uploaded artifact
    """
    from ...config import settings
    from ..types.generation import Generation as GenerationType
    from ..types.generation import GenerationStatus

    # Sanitize filename to prevent path traversal
    filename = _sanitize_filename(filename)

    # Validate MIME type matches artifact type
    is_valid, error_msg = _validate_mime_type(content_type, artifact_type, filename)
    if not is_valid:
        logger.warning(
            "Invalid MIME type for artifact",
            mime_type=content_type,
            artifact_type=artifact_type.value,
            reason=error_msg,
        )
        raise RuntimeError(f"Invalid file type: {error_msg}")

    # Validate file size (double-check even after Content-Length check)
    if len(file_content) > settings.max_upload_size:
        raise RuntimeError(
            f"File size ({len(file_content)} bytes) exceeds maximum allowed "
            f"size ({settings.max_upload_size} bytes)"
        )

    async with get_async_session() as session:
        # Validate board access
        board_stmt = (
            select(Boards).where(Boards.id == board_id).options(selectinload(Boards.board_members))
        )
        board = (await session.execute(board_stmt)).scalar_one_or_none()

        if not board:
            raise RuntimeError("Board not found")

        # Check permissions (same as create_generation)
        if not auth_context.user_id:
            raise RuntimeError("User ID is required")

        is_owner = board.owner_id == auth_context.user_id
        is_editor = any(
            m.user_id == auth_context.user_id and m.role in {"editor", "admin"}
            for m in board.board_members
        )

        if not is_owner and not is_editor:
            raise RuntimeError(
                "Permission denied: You don't have permission to upload to this board"
            )

        # Create generation record (status=pending temporarily)
        gen = Generations()
        gen.tenant_id = auth_context.tenant_id
        gen.board_id = board_id
        gen.user_id = auth_context.user_id
        gen.generator_name = f"user-upload-{artifact_type.value}"
        gen.artifact_type = artifact_type.value
        gen.status = "pending"
        gen.progress = Decimal(0.0)
        gen.input_params = {
            "upload_source": upload_source,
            "original_filename": filename,
            "source_url": source_url,
            "user_description": user_description,
        }
        gen.output_metadata = {
            "file_size": len(file_content),
            "mime_type": content_type,
            "upload_timestamp": datetime.now(UTC).isoformat(),
        }
        # If parent_generation_id is provided, add it to input_artifacts
        if parent_generation_id:
            gen.input_artifacts = [
                {
                    "generation_id": str(parent_generation_id),
                    "role": "parent",
                    "artifact_type": artifact_type.value,
                }
            ]
        else:
            gen.input_artifacts = []
        gen.started_at = datetime.now(UTC)

        session.add(gen)
        await session.flush()  # Get ID

        try:
            # Upload to storage
            storage_manager = create_storage_manager()
            artifact_ref = await storage_manager.store_artifact(
                artifact_id=str(gen.id),
                content=file_content,
                artifact_type=artifact_type.value,
                content_type=content_type,
                tenant_id=str(auth_context.tenant_id),
                board_id=str(board_id),
            )

            # Update generation with storage info
            gen.storage_url = artifact_ref.storage_url
            gen.status = "completed"
            gen.progress = Decimal(100.0)
            gen.completed_at = datetime.now(UTC)

            # Update metadata with storage details
            if gen.output_metadata is None:
                gen.output_metadata = {}
            gen.output_metadata["storage_key"] = artifact_ref.storage_key
            gen.output_metadata["storage_provider"] = artifact_ref.storage_provider

            await session.commit()
            await session.refresh(gen)

            logger.info(
                "Artifact uploaded",
                generation_id=str(gen.id),
                artifact_type=artifact_type,
                file_size=len(file_content),
                upload_source=upload_source,
            )

            # Convert to GraphQL type
            return GenerationType(
                id=gen.id,
                tenant_id=gen.tenant_id,
                board_id=gen.board_id,
                user_id=gen.user_id,
                generator_name=gen.generator_name,
                artifact_type=ArtifactType(gen.artifact_type),
                storage_url=gen.storage_url,
                thumbnail_url=gen.thumbnail_url,
                additional_files=gen.additional_files or [],
                input_params=gen.input_params or {},
                output_metadata=gen.output_metadata or {},
                external_job_id=gen.external_job_id,
                status=GenerationStatus(gen.status),
                progress=float(gen.progress),
                error_message=gen.error_message,
                started_at=gen.started_at,
                completed_at=gen.completed_at,
                created_at=gen.created_at,
                updated_at=gen.updated_at,
            )

        except Exception as e:
            # Mark as failed
            gen.status = "failed"
            gen.error_message = str(e)
            gen.completed_at = datetime.now(UTC)
            await session.commit()

            logger.error(
                "Upload failed",
                generation_id=str(gen.id),
                error=str(e),
            )
            raise RuntimeError(f"Upload failed: {e}") from e
