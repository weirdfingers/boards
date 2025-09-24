from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import strawberry
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import selectinload

from ...database.connection import get_async_session
from ...dbmodels import BoardMembers, Boards, Generations, Users
from ...logging import get_logger
from ..access_control import (
    BoardQueryRole,
    SortOrder,
    can_access_board,
    can_access_board_details,
    ensure_preloaded,
    get_auth_context_from_info,
)

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
    auth_context = await get_auth_context_from_info(info)
    if auth_context is None:
        return None

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

        # Check authorization using shared logic
        if not can_access_board(board, auth_context):
            logger.info(
                "Access denied to board",
                board_id=str(id),
                user_id=(
                    str(auth_context.user_id) if auth_context and auth_context.user_id else None
                ),
            )
            return None

        # Convert SQLAlchemy model to GraphQL type
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


async def resolve_my_boards(
    info: strawberry.Info,
    limit: int,
    offset: int,
    role: BoardQueryRole = BoardQueryRole.ANY,
    sort: SortOrder = SortOrder.UPDATED_DESC
) -> list[Board]:
    """
    Resolve boards where the authenticated user is owner or member.

    Args:
        role: Filter by role (ANY, OWNER, MEMBER)
        sort: Sort order for results
    """
    auth_context = await get_auth_context_from_info(info)
    if not auth_context or not auth_context.is_authenticated:
        logger.info("Unauthenticated access to my_boards")
        return []

    async with get_async_session() as session:
        # Build the query based on role filter
        if role == BoardQueryRole.OWNER:
            # Only boards owned by user
            boards_condition = Boards.owner_id == auth_context.user_id
        elif role == BoardQueryRole.MEMBER:
            # Only boards where user is a member (not owner)
            member_board_ids = select(BoardMembers.board_id).where(
                BoardMembers.user_id == auth_context.user_id
            )
            boards_condition = and_(
                Boards.id.in_(member_board_ids),
                Boards.owner_id != auth_context.user_id
            )
        else:  # BoardQueryRole.ANY
            # Boards where user is owner OR member
            member_board_ids = select(BoardMembers.board_id).where(
                BoardMembers.user_id == auth_context.user_id
            )
            boards_condition = or_(
                Boards.owner_id == auth_context.user_id,
                Boards.id.in_(member_board_ids)
            )

        # Add sorting
        if sort == SortOrder.CREATED_ASC:
            order_by = Boards.created_at.asc()
        elif sort == SortOrder.CREATED_DESC:
            order_by = Boards.created_at.desc()
        elif sort == SortOrder.UPDATED_ASC:
            order_by = Boards.updated_at.asc()
        else:  # UPDATED_DESC (default)
            order_by = Boards.updated_at.desc()

        stmt = (
            select(Boards)
            .where(boards_condition)
            .options(
                selectinload(Boards.owner),
                selectinload(Boards.board_members).selectinload(BoardMembers.user),
            )
            .order_by(order_by)
            .limit(limit)
            .offset(offset)
        )

        result = await session.execute(stmt)
        boards = result.scalars().all()

        # Convert to GraphQL types
        from ..types.board import Board as BoardType

        return [
            BoardType(
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
            for board in boards
        ]


async def resolve_public_boards(
    info: strawberry.Info,
    limit: int,
    offset: int,
    sort: SortOrder = SortOrder.UPDATED_DESC
) -> list[Board]:
    """
    Resolve public boards (no authentication required).

    Args:
        sort: Sort order for results
    """
    async with get_async_session() as session:
        # Add sorting
        if sort == SortOrder.CREATED_ASC:
            order_by = Boards.created_at.asc()
        elif sort == SortOrder.CREATED_DESC:
            order_by = Boards.created_at.desc()
        elif sort == SortOrder.UPDATED_ASC:
            order_by = Boards.updated_at.asc()
        else:  # UPDATED_DESC (default)
            order_by = Boards.updated_at.desc()

        stmt = (
            select(Boards)
            .where(Boards.is_public)
            .options(
                selectinload(Boards.owner),
                selectinload(Boards.board_members).selectinload(BoardMembers.user),
            )
            .order_by(order_by)
            .limit(limit)
            .offset(offset)
        )

        result = await session.execute(stmt)
        boards = result.scalars().all()

        # Convert to GraphQL types
        from ..types.board import Board as BoardType

        return [
            BoardType(
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
            for board in boards
        ]


async def search_boards(info: strawberry.Info, query: str, limit: int, offset: int) -> list[Board]:
    raise NotImplementedError


# Board field resolvers
async def resolve_board_owner(board: Board, info: strawberry.Info) -> User:
    """
    Resolve the owner of a board. Requires user to have access to board details.
    """
    auth_context = await get_auth_context_from_info(info)

    # Check if user can access board details
    # We need to get the actual board from database to check access
    async with get_async_session() as session:
        stmt = (
            select(Boards)
            .where(Boards.id == board.id)
            .options(
                selectinload(Boards.owner),
                selectinload(Boards.board_members),
            )
        )
        result = await session.execute(stmt)
        db_board = result.scalar_one_or_none()

        if not db_board or not can_access_board_details(db_board, auth_context):
            raise RuntimeError("Access denied to board owner information")

        # Ensure owner is preloaded
        ensure_preloaded(db_board, "owner", "Board owner relationship was not preloaded")

        if not db_board.owner:
            raise RuntimeError("Board owner not found")

        from ..types.user import User as UserType

        return UserType(
            id=db_board.owner.id,
            tenant_id=db_board.owner.tenant_id,
            auth_provider=db_board.owner.auth_provider,
            auth_subject=db_board.owner.auth_subject,
            email=db_board.owner.email,
            display_name=db_board.owner.display_name,
            avatar_url=db_board.owner.avatar_url,
            created_at=db_board.owner.created_at,
            updated_at=db_board.owner.updated_at,
        )


async def resolve_board_members(board: Board, info: strawberry.Info) -> list[BoardMember]:
    """
    Resolve the members of a board. Requires user to have access to board details.
    """
    auth_context = await get_auth_context_from_info(info)

    # Check if user can access board details
    async with get_async_session() as session:
        stmt = (
            select(Boards)
            .where(Boards.id == board.id)
            .options(
                selectinload(Boards.board_members).selectinload(BoardMembers.user),
                selectinload(Boards.owner),
            )
        )
        result = await session.execute(stmt)
        db_board = result.scalar_one_or_none()

        if not db_board or not can_access_board_details(db_board, auth_context):
            raise RuntimeError("Access denied to board member information")

        # Ensure members are preloaded
        ensure_preloaded(db_board, "board_members", "Board members relationship was not preloaded")

        from ..types.board import BoardMember as BoardMemberType
        from ..types.board import BoardRole

        members = []
        for member in db_board.board_members:
            # Ensure user relationship is preloaded
            ensure_preloaded(member, "user", "BoardMember user relationship was not preloaded")

            members.append(BoardMemberType(
                id=member.id,
                board_id=member.board_id,
                user_id=member.user_id,
                role=BoardRole(member.role),
                invited_by=member.invited_by,
                joined_at=member.joined_at,
            ))

        return members


async def resolve_board_generations(
    board: Board, info: strawberry.Info, limit: int, offset: int
) -> list[Generation]:
    """
    Resolve generations for a board. Requires user to have access to the board.
    """
    auth_context = await get_auth_context_from_info(info)

    # Check if user can access board
    async with get_async_session() as session:
        # First check board access
        stmt = (
            select(Boards)
            .where(Boards.id == board.id)
            .options(
                selectinload(Boards.board_members),
            )
        )
        result = await session.execute(stmt)
        db_board = result.scalar_one_or_none()

        if not db_board or not can_access_board(db_board, auth_context):
            logger.info("Access denied to board generations", board_id=str(board.id))
            return []

        # Query generations for this board
        generations_stmt = (
            select(Generations)
            .where(Generations.board_id == board.id)
            .order_by(Generations.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        generations_result = await session.execute(generations_stmt)
        generations = generations_result.scalars().all()

        from ..types.generation import ArtifactType, GenerationStatus
        from ..types.generation import Generation as GenerationType

        return [
            GenerationType(
                id=gen.id,
                tenant_id=gen.tenant_id,
                board_id=gen.board_id,
                user_id=gen.user_id,
                generator_name=gen.generator_name,
                provider_name=gen.provider_name,
                artifact_type=ArtifactType(gen.artifact_type),
                storage_url=gen.storage_url,
                thumbnail_url=gen.thumbnail_url,
                additional_files=gen.additional_files or [],
                input_params=gen.input_params or {},
                output_metadata=gen.output_metadata or {},
                parent_generation_id=gen.parent_generation_id,
                input_generation_ids=gen.input_generation_ids or [],
                external_job_id=gen.external_job_id,
                status=GenerationStatus(gen.status),
                progress=gen.progress or 0.0,
                error_message=gen.error_message,
                started_at=gen.started_at,
                completed_at=gen.completed_at,
                created_at=gen.created_at,
                updated_at=gen.updated_at,
            )
            for gen in generations
        ]


async def resolve_board_generation_count(board: Board, info: strawberry.Info) -> int:
    raise NotImplementedError


# BoardMember field resolvers
async def resolve_board_member_user(member: BoardMember, info: strawberry.Info) -> User:
    """
    Resolve the user for a board member. Requires access to board details.
    """
    auth_context = await get_auth_context_from_info(info)

    async with get_async_session() as session:
        # First verify access to the board that this member belongs to
        board_stmt = (
            select(Boards)
            .where(Boards.id == member.board_id)
            .options(
                selectinload(Boards.board_members),
            )
        )
        board_result = await session.execute(board_stmt)
        board = board_result.scalar_one_or_none()

        if not board or not can_access_board_details(board, auth_context):
            raise RuntimeError("Access denied to board member information")

        # Query the user
        user_stmt = select(Users).where(Users.id == member.user_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user:
            raise RuntimeError("Board member user not found")

        from ..types.user import User as UserType

        return UserType(
            id=user.id,
            tenant_id=user.tenant_id,
            auth_provider=user.auth_provider,
            auth_subject=user.auth_subject,
            email=user.email,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


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
