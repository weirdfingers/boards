"""Repository helpers for Generations job lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..dbmodels import Generations


async def get_generation(session: AsyncSession, generation_id: str | UUID) -> Generations:
    stmt = select(Generations).where(Generations.id == str(generation_id))
    res = await session.execute(stmt)
    row = res.scalar_one()
    return row


async def update_progress(
    session: AsyncSession,
    generation_id: str | UUID,
    *,
    status: str,
    progress: float,
    error_message: str | None = None,
) -> None:
    now = datetime.now(UTC)
    stmt = (
        update(Generations)
        .where(Generations.id == str(generation_id))
        .values(
            status=status,
            progress=progress,
            error_message=error_message,
            updated_at=now,
            started_at=now if status == "processing" else Generations.started_at,
            completed_at=(now if status in {"completed", "failed", "cancelled"} else None),
        )
    )
    await session.execute(stmt)


async def create_generation(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    board_id: UUID,
    user_id: UUID,
    generator_name: str,
    artifact_type: str,
    input_params: dict,
) -> Generations:
    gen = Generations()
    gen.tenant_id = tenant_id
    gen.board_id = board_id
    gen.user_id = user_id
    gen.generator_name = generator_name
    gen.artifact_type = artifact_type
    gen.input_params = input_params
    gen.status = "pending"
    gen.progress = Decimal(0.0)
    session.add(gen)
    await session.flush()
    return gen


async def set_external_job_id(
    session: AsyncSession, generation_id: str | UUID, external_job_id: str
) -> None:
    stmt = (
        update(Generations)
        .where(Generations.id == str(generation_id))
        .values(external_job_id=external_job_id)
    )
    await session.execute(stmt)


async def finalize_success(
    session: AsyncSession,
    generation_id: str | UUID,
    *,
    storage_url: str | None = None,
    thumbnail_url: str | None = None,
    output_metadata: dict[str, Any] | None = None,
) -> None:
    now = datetime.now(UTC)
    stmt = (
        update(Generations)
        .where(Generations.id == str(generation_id))
        .values(
            status="completed",
            progress=100.0,
            storage_url=storage_url,
            thumbnail_url=thumbnail_url,
            output_metadata=output_metadata or {},
            updated_at=now,
            completed_at=now,
        )
    )
    await session.execute(stmt)


async def create_batch_generation(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    board_id: UUID,
    user_id: UUID,
    generator_name: str,
    artifact_type: str,
    input_params: dict,
    batch_id: str,
    batch_index: int,
) -> Generations:
    """Create a batch generation record for multi-output generators.

    This creates a new generation record that is part of a batch, with
    batch metadata stored in output_metadata.

    Args:
        session: Database session
        tenant_id: Tenant ID
        board_id: Board ID
        user_id: User ID
        generator_name: Name of the generator
        artifact_type: Type of artifact (image, video, etc.)
        input_params: Input parameters (same as primary generation)
        batch_id: Unique ID for this batch
        batch_index: Index of this output in the batch

    Returns:
        Created generation record
    """
    gen = Generations()
    gen.tenant_id = tenant_id
    gen.board_id = board_id
    gen.user_id = user_id
    gen.generator_name = generator_name
    gen.artifact_type = artifact_type
    gen.input_params = input_params
    gen.status = "processing"
    gen.progress = Decimal(0.0)
    gen.output_metadata = {
        "batch_id": batch_id,
        "batch_index": batch_index,
    }
    session.add(gen)
    await session.flush()
    return gen
