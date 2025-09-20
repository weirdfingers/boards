"""
Tests for board GraphQL resolvers
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import strawberry
from sqlalchemy.ext.asyncio import AsyncSession

from boards.auth.context import AuthContext
from boards.auth.adapters.base import Principal
from boards.dbmodels import Boards, BoardMembers, Users
from boards.graphql.resolvers.board import resolve_board_by_id


@pytest.fixture
def mock_info():
    """Create a mock GraphQL info object with request context."""
    info = MagicMock(spec=strawberry.Info)
    info.context = {
        "request": MagicMock(
            headers=MagicMock(
                get=MagicMock(side_effect=lambda key: {
                    "authorization": "Bearer test-token",
                    "x-tenant": "default"
                }.get(key))
            )
        )
    }
    return info


@pytest.fixture
def mock_info_no_auth():
    """Create a mock GraphQL info object without authentication."""
    info = MagicMock(spec=strawberry.Info)
    info.context = {
        "request": MagicMock(
            headers=MagicMock(
                get=MagicMock(return_value=None)
            )
        )
    }
    return info


@pytest.fixture
def sample_board():
    """Create a sample board for testing."""
    board_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    owner_id = uuid.uuid4()

    board = MagicMock(spec=Boards)
    board.id = board_id
    board.tenant_id = tenant_id
    board.owner_id = owner_id
    board.title = "Test Board"
    board.description = "A test board"
    board.is_public = False
    board.settings = {"theme": "dark"}
    board.metadata_ = {"version": "1.0"}
    board.created_at = datetime.now(timezone.utc)
    board.updated_at = datetime.now(timezone.utc)
    board.board_members = []

    return board


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    user = MagicMock(spec=Users)
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.display_name = "Test User"
    return user


class TestResolveBoardById:
    """Tests for resolve_board_by_id function."""

    @pytest.mark.asyncio
    async def test_public_board_access_without_auth(self, mock_info_no_auth, sample_board):
        """Test that public boards can be accessed without authentication."""
        board_id = sample_board.id
        sample_board.is_public = True

        with patch('boards.graphql.resolvers.board.get_auth_context_optional') as mock_get_auth:
            mock_get_auth.return_value = AuthContext(
                user_id=None,
                tenant_id="default",
                principal=None,
                token=None
            )

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                # Mock the async context manager
                mock_async_session = AsyncMock(spec=AsyncSession)
                mock_session.return_value.__aenter__.return_value = mock_async_session

                # Mock the query execution
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = sample_board
                mock_async_session.execute.return_value = mock_result

                result = await resolve_board_by_id(mock_info_no_auth, board_id)

                assert result is not None
                assert result.id == board_id
                assert result.title == "Test Board"
                assert result.is_public is True

    @pytest.mark.asyncio
    async def test_private_board_owner_access(self, mock_info, sample_board):
        """Test that board owners can access their private boards."""
        board_id = sample_board.id
        owner_id = sample_board.owner_id

        with patch('boards.graphql.resolvers.board.get_auth_context_optional') as mock_get_auth:
            mock_get_auth.return_value = AuthContext(
                user_id=owner_id,
                tenant_id="default",
                principal={"provider": "none", "subject": "user123"},
                token="test-token"
            )

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock(spec=AsyncSession)
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = sample_board
                mock_async_session.execute.return_value = mock_result

                result = await resolve_board_by_id(mock_info, board_id)

                assert result is not None
                assert result.id == board_id
                assert result.owner_id == owner_id

    @pytest.mark.asyncio
    async def test_private_board_member_access(self, mock_info, sample_board):
        """Test that board members can access private boards they belong to."""
        board_id = sample_board.id
        member_user_id = uuid.uuid4()

        # Add a member to the board
        member = MagicMock(spec=BoardMembers)
        member.user_id = member_user_id
        member.role = "viewer"
        sample_board.board_members = [member]

        with patch('boards.graphql.resolvers.board.get_auth_context_optional') as mock_get_auth:
            mock_get_auth.return_value = AuthContext(
                user_id=member_user_id,
                tenant_id="default",
                principal={"provider": "none", "subject": "member123"},
                token="test-token"
            )

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock(spec=AsyncSession)
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = sample_board
                mock_async_session.execute.return_value = mock_result

                result = await resolve_board_by_id(mock_info, board_id)

                assert result is not None
                assert result.id == board_id

    @pytest.mark.asyncio
    async def test_private_board_unauthorized_access(self, mock_info, sample_board):
        """Test that unauthorized users cannot access private boards."""
        board_id = sample_board.id
        unauthorized_user_id = uuid.uuid4()  # Different from owner

        with patch('boards.graphql.resolvers.board.get_auth_context_optional') as mock_get_auth:
            mock_get_auth.return_value = AuthContext(
                user_id=unauthorized_user_id,
                tenant_id="default",
                principal={"provider": "none", "subject": "unauthorized"},
                token="test-token"
            )

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock(spec=AsyncSession)
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = sample_board
                mock_async_session.execute.return_value = mock_result

                result = await resolve_board_by_id(mock_info, board_id)

                assert result is None  # Access denied

    @pytest.mark.asyncio
    async def test_private_board_no_auth(self, mock_info_no_auth, sample_board):
        """Test that private boards cannot be accessed without authentication."""
        board_id = sample_board.id

        with patch('boards.graphql.resolvers.board.get_auth_context_optional') as mock_get_auth:
            mock_get_auth.return_value = AuthContext(
                user_id=None,
                tenant_id="default",
                principal=None,
                token=None
            )

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock(spec=AsyncSession)
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = sample_board
                mock_async_session.execute.return_value = mock_result

                result = await resolve_board_by_id(mock_info_no_auth, board_id)

                assert result is None  # Access denied

    @pytest.mark.asyncio
    async def test_board_not_found(self, mock_info):
        """Test that None is returned when board doesn't exist."""
        board_id = uuid.uuid4()

        with patch('boards.graphql.resolvers.board.get_auth_context_optional') as mock_get_auth:
            mock_get_auth.return_value = AuthContext(
                user_id=uuid.uuid4(),
                tenant_id="default",
                principal={"provider": "none", "subject": "user123"},
                token="test-token"
            )

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock(spec=AsyncSession)
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = None  # Board not found
                mock_async_session.execute.return_value = mock_result

                result = await resolve_board_by_id(mock_info, board_id)

                assert result is None

    @pytest.mark.asyncio
    async def test_no_request_in_context(self):
        """Test handling when request is missing from GraphQL context."""
        board_id = uuid.uuid4()

        # Create info without request in context
        info = MagicMock(spec=strawberry.Info)
        info.context = {}

        result = await resolve_board_by_id(info, board_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_board_with_metadata(self, mock_info, sample_board):
        """Test that board metadata and settings are properly returned."""
        board_id = sample_board.id
        owner_id = sample_board.owner_id

        # Set custom metadata and settings
        sample_board.settings = {"theme": "dark", "layout": "grid"}
        sample_board.metadata_ = {"tags": ["important", "project"]}

        with patch('boards.graphql.resolvers.board.get_auth_context_optional') as mock_get_auth:
            mock_get_auth.return_value = AuthContext(
                user_id=owner_id,
                tenant_id="default",
                principal={"provider": "none", "subject": "user123"},
                token="test-token"
            )

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock(spec=AsyncSession)
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = sample_board
                mock_async_session.execute.return_value = mock_result

                result = await resolve_board_by_id(mock_info, board_id)

                assert result is not None
                assert result.settings == {"theme": "dark", "layout": "grid"}
                assert result.metadata == {"tags": ["important", "project"]}