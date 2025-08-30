from __future__ import annotations

import strawberry
from typing import List, Optional, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from ..types.generation import Generation, GenerationStatus, ArtifactType
    from ..types.board import Board
    from ..types.user import User
    from ..mutations.root import CreateGenerationInput


# Query resolvers
async def resolve_generation_by_id(info: strawberry.Info, id: UUID) -> Optional[Generation]:
    raise NotImplementedError


async def resolve_recent_generations(
    info: strawberry.Info,
    board_id: Optional[UUID],
    status: Optional[GenerationStatus],
    artifact_type: Optional[ArtifactType],
    limit: int,
    offset: int,
) -> List[Generation]:
    raise NotImplementedError


# Field resolvers
async def resolve_generation_board(generation: Generation, info: strawberry.Info) -> Board:
    raise NotImplementedError


async def resolve_generation_user(generation: Generation, info: strawberry.Info) -> User:
    raise NotImplementedError


async def resolve_generation_parent(
    generation: Generation, info: strawberry.Info
) -> Optional[Generation]:
    raise NotImplementedError


async def resolve_generation_inputs(generation: Generation, info: strawberry.Info) -> List[Generation]:
    raise NotImplementedError


async def resolve_generation_children(generation: Generation, info: strawberry.Info) -> List[Generation]:
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
