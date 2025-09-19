from __future__ import annotations

from typing import TYPE_CHECKING

import strawberry

if TYPE_CHECKING:
    from ..types.user import User


async def resolve_current_user(info: strawberry.Info) -> User | None:
    raise NotImplementedError
