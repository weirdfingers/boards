"""
Board GraphQL type definitions
"""

import strawberry
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from uuid import UUID
from enum import Enum

if TYPE_CHECKING:
    from .user import User
    from .generation import Generation


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
    invited_by: Optional[UUID]
    joined_at: datetime

    @strawberry.field
    async def user(self, info: strawberry.Info) -> "User":
        """Get the user for this board member."""
        from ..resolvers.board import resolve_board_member_user

        return await resolve_board_member_user(self, info)

    @strawberry.field
    async def inviter(self, info: strawberry.Info) -> Optional["User"]:
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
    description: Optional[str]
    is_public: bool
    settings: strawberry.scalars.JSON
    metadata: strawberry.scalars.JSON
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    async def owner(self, info: strawberry.Info) -> "User":
        """Get the owner of this board."""
        from ..resolvers.board import resolve_board_owner

        return await resolve_board_owner(self, info)

    @strawberry.field
    async def members(self, info: strawberry.Info) -> List[BoardMember]:
        """Get members of this board."""
        from ..resolvers.board import resolve_board_members

        return await resolve_board_members(self, info)

    @strawberry.field
    async def generations(
        self, info: strawberry.Info, limit: Optional[int] = 50, offset: Optional[int] = 0
    ) -> List["Generation"]:
        """Get generations in this board."""
        from ..resolvers.board import resolve_board_generations

        return await resolve_board_generations(self, info, limit or 50, offset or 0)

    @strawberry.field
    async def generation_count(self, info: strawberry.Info) -> int:
        """Get total number of generations in this board."""
        from ..resolvers.board import resolve_board_generation_count

        return await resolve_board_generation_count(self, info)
