"""
Root GraphQL query definitions
"""

import strawberry
from typing import Optional, List
from uuid import UUID

from ..types.user import User
from ..types.board import Board
from ..types.generation import Generation, GenerationStatus, ArtifactType


@strawberry.type
class Query:
    """Root GraphQL query type."""

    @strawberry.field
    async def me(self, info: strawberry.Info) -> Optional[User]:
        """Get the current authenticated user."""
        from ..resolvers.auth import resolve_current_user

        return await resolve_current_user(info)

    @strawberry.field
    async def user(self, info: strawberry.Info, id: UUID) -> Optional[User]:
        """Get a user by ID."""
        from ..resolvers.user import resolve_user_by_id

        return await resolve_user_by_id(info, str(id))

    @strawberry.field
    async def board(self, info: strawberry.Info, id: UUID) -> Optional[Board]:
        """Get a board by ID."""
        from ..resolvers.board import resolve_board_by_id

        return await resolve_board_by_id(info, id)

    @strawberry.field
    async def my_boards(
        self, info: strawberry.Info, limit: Optional[int] = 50, offset: Optional[int] = 0
    ) -> List[Board]:
        """Get boards owned by or shared with the current user."""
        from ..resolvers.board import resolve_my_boards

        return await resolve_my_boards(info, limit or 50, offset or 0)

    @strawberry.field
    async def public_boards(
        self, info: strawberry.Info, limit: Optional[int] = 50, offset: Optional[int] = 0
    ) -> List[Board]:
        """Get public boards."""
        from ..resolvers.board import resolve_public_boards

        return await resolve_public_boards(info, limit or 50, offset or 0)

    @strawberry.field
    async def generation(self, info: strawberry.Info, id: UUID) -> Optional[Generation]:
        """Get a generation by ID."""
        from ..resolvers.generation import resolve_generation_by_id

        return await resolve_generation_by_id(info, id)

    @strawberry.field
    async def recent_generations(
        self,
        info: strawberry.Info,
        board_id: Optional[UUID] = None,
        status: Optional[GenerationStatus] = None,
        artifact_type: Optional[ArtifactType] = None,
        limit: Optional[int] = 50,
        offset: Optional[int] = 0,
    ) -> List[Generation]:
        """Get recent generations with optional filters."""
        from ..resolvers.generation import resolve_recent_generations

        return await resolve_recent_generations(
            info, board_id, status, artifact_type, limit or 50, offset or 0
        )

    @strawberry.field
    async def search_boards(
        self, info: strawberry.Info, query: str, limit: Optional[int] = 50, offset: Optional[int] = 0
    ) -> List[Board]:
        """Search for boards by title or description."""
        from ..resolvers.board import search_boards

        return await search_boards(info, query, limit or 50, offset or 0)
