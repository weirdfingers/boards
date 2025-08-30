"""
User GraphQL type definitions
"""

import strawberry
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from uuid import UUID

if TYPE_CHECKING:
    from .board import Board

@strawberry.type
class User:
    """User type for GraphQL API."""
    
    id: UUID
    tenant_id: UUID
    auth_provider: str
    auth_subject: str
    email: Optional[str]
    display_name: Optional[str]
    avatar_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    @strawberry.field
    async def boards(self, info: strawberry.Info) -> List["Board"]:
        """Get boards owned by this user."""
        # TODO: Implement data loader
        from ..resolvers.user import resolve_user_boards
        return await resolve_user_boards(self, info)
    
    @strawberry.field
    async def member_boards(self, info: strawberry.Info) -> List["Board"]:
        """Get boards where user is a member."""
        # TODO: Implement data loader
        from ..resolvers.user import resolve_user_member_boards
        return await resolve_user_member_boards(self, info)