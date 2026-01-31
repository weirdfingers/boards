"""
Board GraphQL type definitions
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

import strawberry

if TYPE_CHECKING:
    from ...dbmodels import BoardMembers as BoardMembersDB
    from ...dbmodels import Boards as BoardsDB
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

    # Private field for pre-loaded user (not exposed in GraphQL)
    _user: strawberry.Private[User | None] = None

    @strawberry.field
    async def user(self, info: strawberry.Info) -> Annotated[User, strawberry.lazy(".user")]:
        """Get the user for this board member."""
        # Use pre-loaded data if available
        if self._user is not None:
            return self._user

        # Fall back to resolver (which should use DataLoader)
        from ..resolvers.board import resolve_board_member_user

        return await resolve_board_member_user(self, info)

    @strawberry.field
    async def inviter(
        self, info: strawberry.Info
    ) -> Annotated[User, strawberry.lazy(".user")] | None:
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

    # Private fields for pre-loaded data (not exposed in GraphQL)
    _owner: strawberry.Private[User | None] = None
    _members: strawberry.Private[list[BoardMember] | None] = None

    @strawberry.field
    async def owner(self, info: strawberry.Info) -> Annotated[User, strawberry.lazy(".user")]:
        """Get the owner of this board."""
        # Use pre-loaded data if available
        if self._owner is not None:
            return self._owner

        # Fall back to resolver (which should use DataLoader)
        from ..resolvers.board import resolve_board_owner

        return await resolve_board_owner(self, info)

    @strawberry.field
    async def members(self, info: strawberry.Info) -> list[BoardMember]:
        """Get members of this board."""
        # Use pre-loaded data if available
        if self._members is not None:
            return self._members

        # Fall back to resolver
        from ..resolvers.board import resolve_board_members

        return await resolve_board_members(self, info)

    @strawberry.field
    async def generations(
        self,
        info: strawberry.Info,
        limit: int | None = 50,
        offset: int | None = 0,
    ) -> list[Annotated[Generation, strawberry.lazy(".generation")]]:
        """Get generations in this board."""
        from ..resolvers.board import resolve_board_generations

        return await resolve_board_generations(self, info, limit or 50, offset or 0)

    @strawberry.field
    async def generation_count(self, info: strawberry.Info) -> int:
        """Get total number of generations in this board."""
        from ..resolvers.board import resolve_board_generation_count

        return await resolve_board_generation_count(self, info)


def board_member_from_db_model(
    db_member: BoardMembersDB,
    preloaded_user: User | None = None,
) -> BoardMember:
    """Convert a database BoardMember model to GraphQL BoardMember type."""
    return BoardMember(
        id=db_member.id,
        board_id=db_member.board_id,
        user_id=db_member.user_id,
        role=BoardRole(db_member.role),
        invited_by=db_member.invited_by,
        joined_at=db_member.joined_at,
        _user=preloaded_user,
    )


def board_from_db_model(
    db_board: BoardsDB,
    preloaded_owner: User | None = None,
    preloaded_members: list[BoardMember] | None = None,
) -> Board:
    """Convert a database Board model to GraphQL Board type."""
    return Board(
        id=db_board.id,
        tenant_id=db_board.tenant_id,
        owner_id=db_board.owner_id,
        title=db_board.title,
        description=db_board.description,
        is_public=db_board.is_public,
        settings=db_board.settings or {},
        metadata=db_board.metadata_ or {},
        created_at=db_board.created_at,
        updated_at=db_board.updated_at,
        _owner=preloaded_owner,
        _members=preloaded_members,
    )
