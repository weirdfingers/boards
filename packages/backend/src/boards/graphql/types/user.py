"""
User GraphQL type definitions
"""

from datetime import datetime
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

import strawberry

if TYPE_CHECKING:
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
    ) -> list[Annotated["Board", strawberry.lazy(".board")]]:  # noqa: E501
        """Get boards owned by this user."""
        # TODO: Implement data loader
        from ..resolvers.user import resolve_user_boards

        return await resolve_user_boards(self, info)

    @strawberry.field
    async def member_boards(
        self, info: strawberry.Info
    ) -> list[Annotated["Board", strawberry.lazy(".board")]]:  # noqa: E501
        """Get boards where user is a member."""
        # TODO: Implement data loader
        from ..resolvers.user import resolve_user_member_boards

        return await resolve_user_member_boards(self, info)
