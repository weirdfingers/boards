"""
Shared access control logic for GraphQL resolvers
"""

from enum import Enum
from typing import TYPE_CHECKING

import strawberry

from ..auth.middleware import get_auth_context_optional
from ..logging import get_logger

if TYPE_CHECKING:
    from ..auth.context import AuthContext
    from ..dbmodels import Boards

logger = get_logger(__name__)


@strawberry.enum
class BoardQueryRole(Enum):
    """Role filter for board queries"""

    ANY = "any"
    OWNER = "owner"
    MEMBER = "member"


@strawberry.enum
class SortOrder(Enum):
    """Sort order for queries"""

    CREATED_ASC = "created_asc"
    CREATED_DESC = "created_desc"
    UPDATED_ASC = "updated_asc"
    UPDATED_DESC = "updated_desc"


async def get_auth_context_from_info(info: strawberry.Info) -> "AuthContext | None":
    """
    Extract auth context from GraphQL info object.

    Returns None if request is not available or auth fails.
    """
    request = info.context.get("request")
    if not request:
        logger.error("Request not found in GraphQL context")
        return None

    return await get_auth_context_optional(
        authorization=request.headers.get("authorization"),
        x_tenant=request.headers.get("x-tenant"),
    )


def can_access_board(board: "Boards", auth_context: "AuthContext | None") -> bool:
    """
    Check if a user can access a board based on authorization rules.

    Board is accessible if:
    1. It's public
    2. User is the owner
    3. User is a member

    Args:
        board: The board to check access for
        auth_context: The authentication context (can be None)

    Returns:
        True if access is allowed, False otherwise
    """
    # Public boards are accessible to everyone
    if board.is_public:
        return True

    # Private boards require authentication
    if not auth_context or not auth_context.is_authenticated:
        return False

    # Owner has access
    if board.owner_id == auth_context.user_id:
        return True

    # Check if user is a member
    return any(member.user_id == auth_context.user_id for member in board.board_members)


def can_access_board_details(board: "Boards", auth_context: "AuthContext | None") -> bool:
    """
    Check if a user can access detailed board information (members, owner, etc).

    Currently same as can_access_board, but separated for future customization.
    """
    return can_access_board(board, auth_context)


def is_board_owner_or_member(board: "Boards", auth_context: "AuthContext | None") -> bool:
    """
    Check if the authenticated user is the owner or a member of the board.

    This is stricter than can_access_board - public access is not sufficient.
    """
    if not auth_context or not auth_context.is_authenticated:
        return False

    # Owner has access
    if board.owner_id == auth_context.user_id:
        return True

    # Check if user is a member
    return any(member.user_id == auth_context.user_id for member in board.board_members)


def ensure_preloaded(obj, attr_name: str, error_msg: str | None = None) -> None:
    """
    Ensure that a relationship attribute has been preloaded.

    Args:
        obj: The SQLAlchemy object
        attr_name: Name of the relationship attribute
        error_msg: Custom error message (optional)

    Raises:
        RuntimeError: If the attribute was not preloaded
    """
    try:
        # Try to access the attribute
        getattr(obj, attr_name)
    except Exception as e:
        if "was not loaded" in str(e) or "lazy loading" in str(e):
            msg = error_msg or (
                f"Relationship '{attr_name}' was not preloaded. " "Use selectinload() in the query."
            )
            raise RuntimeError(msg) from e
        # Re-raise other exceptions
        raise
