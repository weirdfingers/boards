from __future__ import annotations

import strawberry
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types.user import User


async def resolve_current_user(info: strawberry.Info) -> User | None:
    raise NotImplementedError
