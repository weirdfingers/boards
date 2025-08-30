from __future__ import annotations

import strawberry
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..types.user import User
    from ..types.board import Board


async def resolve_current_user(info: strawberry.Info) -> User | None:
    raise NotImplementedError


async def resolve_user_by_id(info: strawberry.Info, id) -> User | None:
    raise NotImplementedError


async def resolve_user_boards(user: User, info: strawberry.Info) -> List[Board]:
    raise NotImplementedError


async def resolve_user_member_boards(user: User, info: strawberry.Info) -> List[Board]:
    raise NotImplementedError
