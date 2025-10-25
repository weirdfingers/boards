"""Job submission endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.connection import get_db_session
from ...jobs import repository as jobs_repo
from ...logging import get_logger
from ...workers.actors import process_generation
from ..auth import AuthenticatedUser, get_current_user

logger = get_logger(__name__)


router = APIRouter()


class SubmitGenerationRequest(BaseModel):
    tenant_id: UUID
    board_id: UUID
    user_id: UUID
    generator_name: str
    artifact_type: str
    input_params: dict


class SubmitGenerationResponse(BaseModel):
    generation_id: UUID


@router.post("/generations", response_model=SubmitGenerationResponse)
async def submit_generation(
    body: SubmitGenerationRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> SubmitGenerationResponse:
    """Submit a new generation job.

    Requires authentication. The authenticated user's ID and tenant will be used
    for the generation, overriding any values provided in the request body.
    """
    try:
        # Validate that user has access to the specified board
        # TODO: Add board access validation logic here

        # Override user_id and tenant_id with authenticated values for security
        # This prevents users from submitting jobs on behalf of others
        gen = await jobs_repo.create_generation(
            db,
            tenant_id=current_user.tenant_id,  # Use authenticated tenant
            board_id=body.board_id,
            user_id=current_user.user_id,  # Use authenticated user
            generator_name=body.generator_name,
            artifact_type=body.artifact_type,
            input_params=body.input_params,
        )

        # Commit the transaction to ensure job is persisted before enqueueing
        await db.commit()
        logger.info(f"Created generation job {gen.id} for user {current_user.user_id}")

        # Enqueue job for processing
        process_generation.send(str(gen.id))
        logger.info(f"Enqueued generation job {gen.id}")

        return SubmitGenerationResponse(generation_id=gen.id)

    except Exception as e:
        logger.error(f"Failed to submit generation: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to submit generation: {str(e)}") from e
