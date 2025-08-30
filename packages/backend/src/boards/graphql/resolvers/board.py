from __future__ import annotations

import strawberry
from typing import List, Optional, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from ..types.board import Board, BoardMember, BoardRole
    from ..types.user import User
    from ..types.generation import Generation
    from ..mutations.root import CreateBoardInput, UpdateBoardInput, AddBoardMemberInput


# Query resolvers
async def resolve_board_by_id(info: strawberry.Info, id: UUID) -> Optional[Board]:
    raise NotImplementedError


async def resolve_my_boards(info: strawberry.Info, limit: int, offset: int) -> List[Board]:
    raise NotImplementedError


async def resolve_public_boards(info: strawberry.Info, limit: int, offset: int) -> List[Board]:
    raise NotImplementedError


async def search_boards(info: strawberry.Info, query: str, limit: int, offset: int) -> List[Board]:
    raise NotImplementedError


# Board field resolvers
async def resolve_board_owner(board: Board, info: strawberry.Info) -> User:
    raise NotImplementedError


async def resolve_board_members(board: Board, info: strawberry.Info) -> List[BoardMember]:
    raise NotImplementedError


async def resolve_board_generations(
    board: Board, info: strawberry.Info, limit: int, offset: int
) -> List[Generation]:
    raise NotImplementedError


async def resolve_board_generation_count(board: Board, info: strawberry.Info) -> int:
    raise NotImplementedError


# BoardMember field resolvers
async def resolve_board_member_user(member: BoardMember, info: strawberry.Info) -> User:
    raise NotImplementedError


async def resolve_board_member_inviter(member: BoardMember, info: strawberry.Info) -> Optional[User]:
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
