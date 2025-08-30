"""
Root GraphQL mutation definitions
"""

import strawberry
from typing import Optional, List
from uuid import UUID

from ..types.board import Board, BoardRole
from ..types.generation import Generation, ArtifactType

# Input types for mutations
@strawberry.input
class CreateBoardInput:
    """Input for creating a new board."""
    title: str
    description: Optional[str] = None
    is_public: bool = False
    settings: Optional[strawberry.scalars.JSON] = None

@strawberry.input
class UpdateBoardInput:
    """Input for updating a board."""
    id: UUID
    title: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    settings: Optional[strawberry.scalars.JSON] = None

@strawberry.input
class AddBoardMemberInput:
    """Input for adding a board member."""
    board_id: UUID
    user_id: UUID
    role: BoardRole = BoardRole.VIEWER

@strawberry.input
class CreateGenerationInput:
    """Input for creating a new generation."""
    board_id: UUID
    generator_name: str
    provider_name: str
    artifact_type: ArtifactType
    input_params: strawberry.scalars.JSON
    parent_generation_id: Optional[UUID] = None
    input_generation_ids: Optional[List[UUID]] = None

@strawberry.type
class Mutation:
    """Root GraphQL mutation type."""
    
    # Board mutations
    @strawberry.mutation
    async def create_board(self, info: strawberry.Info, input: CreateBoardInput) -> Board:
        """Create a new board."""
        from ..resolvers.board import create_board
        return await create_board(info, input)
    
    @strawberry.mutation
    async def update_board(self, info: strawberry.Info, input: UpdateBoardInput) -> Board:
        """Update an existing board."""
        from ..resolvers.board import update_board
        return await update_board(info, input)
    
    @strawberry.mutation
    async def delete_board(self, info: strawberry.Info, id: UUID) -> bool:
        """Delete a board."""
        from ..resolvers.board import delete_board
        return await delete_board(info, id)
    
    @strawberry.mutation
    async def add_board_member(self, info: strawberry.Info, input: AddBoardMemberInput) -> Board:
        """Add a member to a board."""
        from ..resolvers.board import add_board_member
        return await add_board_member(info, input)
    
    @strawberry.mutation
    async def remove_board_member(self, info: strawberry.Info, board_id: UUID, user_id: UUID) -> Board:
        """Remove a member from a board."""
        from ..resolvers.board import remove_board_member
        return await remove_board_member(info, board_id, user_id)
    
    @strawberry.mutation
    async def update_board_member_role(
        self,
        info: strawberry.Info,
        board_id: UUID,
        user_id: UUID,
        role: BoardRole
    ) -> Board:
        """Update a board member's role."""
        from ..resolvers.board import update_board_member_role
        return await update_board_member_role(info, board_id, user_id, role)
    
    # Generation mutations
    @strawberry.mutation
    async def create_generation(self, info: strawberry.Info, input: CreateGenerationInput) -> Generation:
        """Create a new generation (start a job)."""
        from ..resolvers.generation import create_generation
        return await create_generation(info, input)
    
    @strawberry.mutation
    async def cancel_generation(self, info: strawberry.Info, id: UUID) -> Generation:
        """Cancel a pending or processing generation."""
        from ..resolvers.generation import cancel_generation
        return await cancel_generation(info, id)
    
    @strawberry.mutation
    async def delete_generation(self, info: strawberry.Info, id: UUID) -> bool:
        """Delete a generation."""
        from ..resolvers.generation import delete_generation
        return await delete_generation(info, id)
    
    @strawberry.mutation
    async def regenerate(self, info: strawberry.Info, id: UUID) -> Generation:
        """Regenerate from an existing generation."""
        from ..resolvers.generation import regenerate
        return await regenerate(info, id)