"""Job submission endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ...database.connection import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from ...jobs import repository as jobs_repo
from ...workers.actors import process_generation


router = APIRouter()


class SubmitGenerationRequest(BaseModel):
    tenant_id: str
    board_id: str
    user_id: str
    generator_name: str
    provider_name: str
    artifact_type: str
    input_params: dict


class SubmitGenerationResponse(BaseModel):
    generation_id: str


@router.post("/generations", response_model=SubmitGenerationResponse)
async def submit_generation(
    body: SubmitGenerationRequest,
    db: AsyncSession = Depends(get_db_session),
) -> SubmitGenerationResponse:
    gen = await jobs_repo.create_generation(
        db,
        tenant_id=body.tenant_id,
        board_id=body.board_id,
        user_id=body.user_id,
        generator_name=body.generator_name,
        provider_name=body.provider_name,
        artifact_type=body.artifact_type,
        input_params=body.input_params,
    )
    # Enqueue job
    process_generation.send(str(gen.id))
    return SubmitGenerationResponse(generation_id=str(gen.id))
