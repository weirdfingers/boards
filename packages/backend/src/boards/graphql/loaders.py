from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from strawberry.dataloader import DataLoader

from ..database.connection import get_async_session
from ..dbmodels import BoardMembers, Boards, Users


async def load_boards(keys: list[UUID]) -> list[Boards | None]:
    """Batch load boards by ID."""
    async with get_async_session() as session:
        stmt = (
            select(Boards)
            .where(Boards.id.in_(keys))
            .options(
                selectinload(Boards.owner),
                selectinload(Boards.board_members).selectinload(BoardMembers.user),
            )
        )
        result = await session.execute(stmt)
        boards = result.scalars().all()
        boards_map = {board.id: board for board in boards}
        return [boards_map.get(key) for key in keys]


async def load_users(keys: list[UUID]) -> list[Users | None]:
    """Batch load users by ID."""
    async with get_async_session() as session:
        stmt = select(Users).where(Users.id.in_(keys))
        result = await session.execute(stmt)
        users = result.scalars().all()
        users_map = {user.id: user for user in users}
        return [users_map.get(key) for key in keys]


class Loaders:
    def __init__(self):
        self.board_loader = DataLoader(load_fn=load_boards)
        self.user_loader = DataLoader(load_fn=load_users)
