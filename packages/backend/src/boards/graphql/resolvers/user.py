from __future__ import annotations

from typing import TYPE_CHECKING

import strawberry

if TYPE_CHECKING:
    from ..types.board import Board
    from ..types.user import User


async def resolve_current_user(info: strawberry.Info) -> User | None:
    raise NotImplementedError


async def resolve_user_by_id(info: strawberry.Info, id: str) -> User | None:
    raise NotImplementedError


async def resolve_user_boards(user: User, info: strawberry.Info) -> list[Board]:
    raise NotImplementedError


async def resolve_user_member_boards(user: User, info: strawberry.Info) -> list[Board]:
    raise NotImplementedError
