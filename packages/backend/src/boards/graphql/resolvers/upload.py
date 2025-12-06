"""Resolvers for artifact upload operations."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
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

if TYPE_CHECKING:
    from ..types.generation import Generation as GenerationType
    from ..types.generation import UploadArtifactInput

logger = get_logger(__name__)


async def upload_artifact_from_url(
    info: strawberry.Info,
    input: UploadArtifactInput,
) -> GenerationType:
    """Upload artifact from URL (synchronous)."""
    auth_context = await get_auth_context_from_info(info)
    if not auth_context or not auth_context.is_authenticated:
        raise RuntimeError("Authentication required")

    if not input.file_url:
        raise RuntimeError("file_url is required")

    # Download file from URL
    async with aiohttp.ClientSession() as http_session:
        try:
            async with http_session.get(
                input.file_url, timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Failed to download from URL: HTTP {resp.status}")

                content = await resp.read()
                content_type = resp.headers.get("Content-Type", "application/octet-stream")

                # Extract filename from URL if not provided
                filename = input.original_filename
                if not filename:
                    from urllib.parse import urlparse

                    path = urlparse(input.file_url).path
                    filename = path.split("/")[-1] if path else "uploaded_file"

        except aiohttp.ClientError as e:
            logger.error("URL download failed", url=input.file_url, error=str(e))
            raise RuntimeError(f"Failed to download file from URL: {e}") from e

    # Process upload
    return await _process_upload(
        auth_context=auth_context,
        board_id=input.board_id,
        artifact_type=input.artifact_type.value,
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
        artifact_type=artifact_type,
        file_content=file_content,
        filename=filename or "uploaded_file",
        content_type=content_type or "application/octet-stream",
        user_description=user_description,
        parent_generation_id=parent_generation_id,
        upload_source="file",
        source_url=None,
    )


async def _process_upload(
    auth_context: AuthContext,
    board_id: UUID,
    artifact_type: str,
    file_content: bytes,
    filename: str,
    content_type: str,
    user_description: str | None,
    parent_generation_id: UUID | None,
    upload_source: str,
    source_url: str | None,
) -> GenerationType:
    """Common upload processing logic."""
    from ..types.generation import ArtifactType, GenerationStatus
    from ..types.generation import Generation as GenerationType

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
        gen.generator_name = f"user-upload-{artifact_type}"
        gen.artifact_type = artifact_type
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
        gen.parent_generation_id = parent_generation_id
        gen.started_at = datetime.now(UTC)

        session.add(gen)
        await session.flush()  # Get ID

        try:
            # Upload to storage
            storage_manager = create_storage_manager()
            artifact_ref = await storage_manager.store_artifact(
                artifact_id=str(gen.id),
                content=file_content,
                artifact_type=artifact_type,
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
                parent_generation_id=gen.parent_generation_id,
                input_generation_ids=gen.input_generation_ids or [],
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
