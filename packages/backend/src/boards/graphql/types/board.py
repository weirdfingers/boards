"""
Board GraphQL type definitions
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

import strawberry

if TYPE_CHECKING:
    from .generation import Generation
    from .user import User


@strawberry.enum
class BoardRole(Enum):
    """Board member role enumeration."""

    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"


@strawberry.type
class BoardMember:
    """Board member type for GraphQL API."""

    id: UUID
    board_id: UUID
    user_id: UUID
    role: BoardRole
    invited_by: UUID | None
    joined_at: datetime

    @strawberry.field
    async def user(self, info: strawberry.Info) -> Annotated["User", strawberry.lazy(".user")]:
        """Get the user for this board member."""
        from ..resolvers.board import resolve_board_member_user

        return await resolve_board_member_user(self, info)

    @strawberry.field
    async def inviter(
        self, info: strawberry.Info
    ) -> Annotated["User", strawberry.lazy(".user")] | None:  # noqa: E501
        """Get the user who invited this member."""
        if not self.invited_by:
            return None
        from ..resolvers.board import resolve_board_member_inviter

        return await resolve_board_member_inviter(self, info)


@strawberry.type
class Board:
    """Board type for GraphQL API."""

    id: UUID
    tenant_id: UUID
    owner_id: UUID
    title: str
    description: str | None
    is_public: bool
    settings: strawberry.scalars.JSON  # type: ignore[reportInvalidTypeForm]
    metadata: strawberry.scalars.JSON  # type: ignore[reportInvalidTypeForm]
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    async def owner(self, info: strawberry.Info) -> Annotated["User", strawberry.lazy(".user")]:
        """Get the owner of this board."""
        from ..resolvers.board import resolve_board_owner

        return await resolve_board_owner(self, info)

    @strawberry.field
    async def members(self, info: strawberry.Info) -> list[BoardMember]:
        """Get members of this board."""
        from ..resolvers.board import resolve_board_members

        return await resolve_board_members(self, info)

    @strawberry.field
    async def generations(
        self,
        info: strawberry.Info,
        limit: int | None = 50,
        offset: int | None = 0,
    ) -> list[Annotated["Generation", strawberry.lazy(".generation")]]:
        """Get generations in this board."""
        from ..resolvers.board import resolve_board_generations

        return await resolve_board_generations(self, info, limit or 50, offset or 0)

    @strawberry.field
    async def generation_count(self, info: strawberry.Info) -> int:
        """Get total number of generations in this board."""
        from ..resolvers.board import resolve_board_generation_count

        return await resolve_board_generation_count(self, info)
