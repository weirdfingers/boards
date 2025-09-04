from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import strawberry

if TYPE_CHECKING:
    from ..mutations.root import CreateGenerationInput
    from ..types.board import Board
    from ..types.generation import ArtifactType, Generation, GenerationStatus
    from ..types.user import User


# Query resolvers
async def resolve_generation_by_id(info: strawberry.Info, id: UUID) -> Generation | None:
    raise NotImplementedError


async def resolve_recent_generations(
    info: strawberry.Info,
    board_id: UUID | None,
    status: GenerationStatus | None,
    artifact_type: ArtifactType | None,
    limit: int,
    offset: int,
) -> list[Generation]:
    raise NotImplementedError


# Field resolvers
async def resolve_generation_board(generation: Generation, info: strawberry.Info) -> Board:
    raise NotImplementedError


async def resolve_generation_user(generation: Generation, info: strawberry.Info) -> User:
    raise NotImplementedError


async def resolve_generation_parent(
    generation: Generation, info: strawberry.Info
) -> Generation | None:
    raise NotImplementedError


async def resolve_generation_inputs(generation: Generation, info: strawberry.Info) -> list[Generation]:
    raise NotImplementedError


async def resolve_generation_children(generation: Generation, info: strawberry.Info) -> list[Generation]:
    raise NotImplementedError


# Mutation resolvers
async def create_generation(info: strawberry.Info, input: CreateGenerationInput) -> Generation:
    raise NotImplementedError


async def cancel_generation(info: strawberry.Info, id: UUID) -> Generation:
    raise NotImplementedError


async def delete_generation(info: strawberry.Info, id: UUID) -> bool:
    raise NotImplementedError


async def regenerate(info: strawberry.Info, id: UUID) -> Generation:
    raise NotImplementedError
