"""
User GraphQL type definitions
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

import strawberry

if TYPE_CHECKING:
    from ...dbmodels import Users as UsersDB
    from .board import Board


@strawberry.type
class User:
    """User type for GraphQL API."""

    id: UUID
    tenant_id: UUID
    auth_provider: str
    auth_subject: str
    email: str | None
    display_name: str | None
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    async def boards(
        self, info: strawberry.Info
    ) -> list[Annotated[Board, strawberry.lazy(".board")]]:
        """Get boards owned by this user."""
        # TODO: Implement data loader
        from ..resolvers.user import resolve_user_boards

        return await resolve_user_boards(self, info)

    @strawberry.field
    async def member_boards(
        self, info: strawberry.Info
    ) -> list[Annotated[Board, strawberry.lazy(".board")]]:
        """Get boards where user is a member."""
        # TODO: Implement data loader
        from ..resolvers.user import resolve_user_member_boards

        return await resolve_user_member_boards(self, info)


def user_from_db_model(db_user: UsersDB) -> User:
    """Convert a database User model to GraphQL User type."""
    return User(
        id=db_user.id,
        tenant_id=db_user.tenant_id,
        auth_provider=db_user.auth_provider,
        auth_subject=db_user.auth_subject,
        email=db_user.email,
        display_name=db_user.display_name,
        avatar_url=db_user.avatar_url,
        created_at=db_user.created_at,
        updated_at=db_user.updated_at,
    )
