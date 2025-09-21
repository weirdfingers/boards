from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import strawberry
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ...auth.middleware import get_auth_context_optional
from ...database.connection import get_async_session
from ...dbmodels import BoardMembers, Boards
from ...logging import get_logger

if TYPE_CHECKING:
    from ..mutations.root import AddBoardMemberInput, CreateBoardInput, UpdateBoardInput
    from ..types.board import Board, BoardMember, BoardRole
    from ..types.generation import Generation
    from ..types.user import User

logger = get_logger(__name__)


# Query resolvers
async def resolve_board_by_id(info: strawberry.Info, id: UUID) -> Board | None:
    """
    Resolve a board by its ID.

    Checks authorization: board must be public or user must be owner/member.
    """
    # Get the request from context
    request = info.context.get("request")
    if not request:
        logger.error("Request not found in GraphQL context")
        return None

    # Get auth context from request headers
    auth_context = await get_auth_context_optional(
        authorization=request.headers.get("authorization"),
        x_tenant=request.headers.get("x-tenant"),
    )

    # Get database session
    async with get_async_session() as session:
        # Query board with owner and members eagerly loaded
        stmt = (
            select(Boards)
            .where(Boards.id == id)
            .options(
                selectinload(Boards.owner),
                selectinload(Boards.board_members).selectinload(BoardMembers.user),
            )
        )

        result = await session.execute(stmt)
        board = result.scalar_one_or_none()

        if not board:
            logger.info("Board not found", board_id=str(id))
            return None

        # Check authorization
        # Board is accessible if:
        # 1. It's public
        # 2. User is the owner
        # 3. User is a member
        if board.is_public:
            pass  # Public board, allow access
        elif not auth_context.is_authenticated:
            logger.info("Unauthenticated access denied to private board", board_id=str(id))
            return None
        elif board.owner_id == auth_context.user_id:
            pass  # User is owner
        else:
            # Check if user is a member
            is_member = any(
                member.user_id == auth_context.user_id
                for member in board.board_members
            )
            if not is_member:
                logger.info(
                    "Access denied to board",
                    board_id=str(id),
                    user_id=str(auth_context.user_id) if auth_context.user_id else None,
                )
                return None

        # Convert SQLAlchemy model to GraphQL type
        # This is a simple conversion - the actual Board type will handle
        # field resolvers for nested objects
        from ..types.board import Board as BoardType

        return BoardType(
            id=board.id,
            tenant_id=board.tenant_id,
            owner_id=board.owner_id,
            title=board.title,
            description=board.description,
            is_public=board.is_public,
            settings=board.settings or {},
            metadata=board.metadata_ or {},
            created_at=board.created_at,
            updated_at=board.updated_at,
        )


async def resolve_my_boards(info: strawberry.Info, limit: int, offset: int) -> list[Board]:
    raise NotImplementedError


async def resolve_public_boards(info: strawberry.Info, limit: int, offset: int) -> list[Board]:
    raise NotImplementedError


async def search_boards(info: strawberry.Info, query: str, limit: int, offset: int) -> list[Board]:
    raise NotImplementedError


# Board field resolvers
async def resolve_board_owner(board: Board, info: strawberry.Info) -> User:
    raise NotImplementedError


async def resolve_board_members(board: Board, info: strawberry.Info) -> list[BoardMember]:
    raise NotImplementedError


async def resolve_board_generations(
    board: Board, info: strawberry.Info, limit: int, offset: int
) -> list[Generation]:
    raise NotImplementedError


async def resolve_board_generation_count(board: Board, info: strawberry.Info) -> int:
    raise NotImplementedError


# BoardMember field resolvers
async def resolve_board_member_user(member: BoardMember, info: strawberry.Info) -> User:
    raise NotImplementedError


async def resolve_board_member_inviter(member: BoardMember, info: strawberry.Info) -> User | None:
    raise NotImplementedError


# Mutation resolvers
async def create_board(info: strawberry.Info, input: CreateBoardInput) -> Board:
    raise NotImplementedError


async def update_board(info: strawberry.Info, input: UpdateBoardInput) -> Board:
    raise NotImplementedError


async def delete_board(info: strawberry.Info, id: UUID) -> bool:
    raise NotImplementedError


async def add_board_member(info: strawberry.Info, input: AddBoardMemberInput) -> Board:
    raise NotImplementedError


async def remove_board_member(info: strawberry.Info, board_id: UUID, user_id: UUID) -> Board:
    raise NotImplementedError


async def update_board_member_role(
    info: strawberry.Info, board_id: UUID, user_id: UUID, role: BoardRole
) -> Board:
    raise NotImplementedError
