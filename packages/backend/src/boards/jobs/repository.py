"""Repository helpers for Generations job lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..dbmodels import Generations


async def get_generation(
    session: AsyncSession, generation_id: str | UUID
) -> Generations:
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
    error_message: Optional[str] = None,
) -> None:
    now = datetime.now(timezone.utc)
    stmt = (
        update(Generations)
        .where(Generations.id == str(generation_id))
        .values(
            status=status,
            progress=progress,
            error_message=error_message,
            updated_at=now,
            started_at=now if status == "processing" else Generations.started_at,
            completed_at=(
                now if status in {"completed", "failed", "cancelled"} else None
            ),
        )
    )
    await session.execute(stmt)


async def create_generation(
    session: AsyncSession,
    *,
    tenant_id: str,
    board_id: str,
    user_id: str,
    generator_name: str,
    provider_name: str,
    artifact_type: str,
    input_params: dict,
) -> Generations:
    gen = Generations(
        tenant_id=tenant_id,
        board_id=board_id,
        user_id=user_id,
        generator_name=generator_name,
        provider_name=provider_name,
        artifact_type=artifact_type,
        input_params=input_params,
        status="pending",
        progress=0.0,
    )
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
    storage_url: Optional[str] = None,
    thumbnail_url: Optional[str] = None,
    output_metadata: Optional[dict[str, Any]] = None,
) -> None:
    now = datetime.now(timezone.utc)
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
