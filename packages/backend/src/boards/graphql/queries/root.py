"""
Root GraphQL query definitions
"""

from uuid import UUID

import strawberry

from ..access_control import BoardQueryRole, SortOrder
from ..types.board import Board
from ..types.generation import ArtifactType, Generation, GenerationStatus
from ..types.generator import GeneratorInfo
from ..types.user import User


@strawberry.type
class Query:
    """Root GraphQL query type."""

    @strawberry.field
    async def me(self, info: strawberry.Info) -> User | None:
        """Get the current authenticated user."""
        from ..resolvers.auth import resolve_current_user

        return await resolve_current_user(info)

    @strawberry.field
    async def user(self, info: strawberry.Info, id: UUID) -> User | None:
        """Get a user by ID."""
        from ..resolvers.user import resolve_user_by_id

        return await resolve_user_by_id(info, str(id))

    @strawberry.field
    async def board(self, info: strawberry.Info, id: UUID) -> Board | None:
        """Get a board by ID."""
        from ..resolvers.board import resolve_board_by_id

        return await resolve_board_by_id(info, id)

    @strawberry.field
    async def my_boards(
        self,
        info: strawberry.Info,
        limit: int | None = 50,
        offset: int | None = 0,
        role: BoardQueryRole | None = None,
        sort: SortOrder | None = None,
    ) -> list[Board]:
        """Get boards owned by or shared with the current user."""
        from ..resolvers.board import resolve_my_boards

        return await resolve_my_boards(
            info,
            limit or 50,
            offset or 0,
            role or BoardQueryRole.ANY,
            sort or SortOrder.UPDATED_DESC,
        )

    @strawberry.field
    async def public_boards(
        self,
        info: strawberry.Info,
        limit: int | None = 50,
        offset: int | None = 0,
        sort: SortOrder | None = None,
    ) -> list[Board]:
        """Get public boards."""
        from ..resolvers.board import resolve_public_boards

        return await resolve_public_boards(
            info, limit or 50, offset or 0, sort or SortOrder.UPDATED_DESC
        )

    @strawberry.field
    async def generation(self, info: strawberry.Info, id: UUID) -> Generation | None:
        """Get a generation by ID."""
        from ..resolvers.generation import resolve_generation_by_id

        return await resolve_generation_by_id(info, id)

    @strawberry.field
    async def recent_generations(
        self,
        info: strawberry.Info,
        board_id: UUID | None = None,
        status: GenerationStatus | None = None,
        artifact_type: ArtifactType | None = None,
        limit: int | None = 50,
        offset: int | None = 0,
    ) -> list[Generation]:
        """Get recent generations with optional filters."""
        from ..resolvers.generation import resolve_recent_generations

        return await resolve_recent_generations(
            info, board_id, status, artifact_type, limit or 50, offset or 0
        )

    @strawberry.field
    async def search_boards(
        self, info: strawberry.Info, query: str, limit: int | None = 50, offset: int | None = 0
    ) -> list[Board]:
        """Search for boards by title or description."""
        from ..resolvers.board import search_boards

        return await search_boards(info, query, limit or 50, offset or 0)

    @strawberry.field
    async def generators(
        self, info: strawberry.Info, artifact_type: str | None = None
    ) -> list[GeneratorInfo]:
        """Get all available generators, optionally filtered by artifact type."""
        from ..resolvers.generator import resolve_generators

        return await resolve_generators(info, artifact_type)
