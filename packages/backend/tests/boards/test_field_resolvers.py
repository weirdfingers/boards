"""
Unit tests for board field resolver functions
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import strawberry

from boards.auth.context import AuthContext
from boards.dbmodels import Boards, Users
from boards.graphql.resolvers.board import (
    resolve_board_generation_count,
    resolve_board_member_inviter,
)
from boards.graphql.types.board import Board, BoardMember, BoardRole


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
def auth_context():
    """Create an authenticated context."""
    return AuthContext(
        user_id=uuid.uuid4(),
        tenant_id=str(uuid.uuid4()),
        principal={"provider": "none", "subject": "test-user"},
        token="test-token"
    )


@pytest.fixture
def sample_board():
    """Create a sample Board GraphQL type."""
    return Board(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        title="Test Board",
        description="Test Description",
        is_public=False,
        settings={},
        metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


@pytest.fixture
def sample_board_member():
    """Create a sample BoardMember GraphQL type."""
    return BoardMember(
        id=uuid.uuid4(),
        board_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=BoardRole.VIEWER,
        invited_by=uuid.uuid4(),
        joined_at=datetime.now(UTC)
    )


class TestBoardGenerationCount:
    """Tests for resolve_board_generation_count field resolver."""

    @pytest.mark.asyncio
    async def test_generation_count_with_access(self, mock_info, auth_context, sample_board):
        """Test getting generation count for accessible board."""
        sample_board.owner_id = auth_context.user_id

        # Create mock database board
        db_board = MagicMock(spec=Boards)
        db_board.id = sample_board.id
        db_board.owner_id = sample_board.owner_id
        db_board.is_public = False
        db_board.board_members = []

        with patch('boards.graphql.resolvers.board.get_auth_context_from_info') as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                # Mock board query
                mock_board_result = MagicMock()
                mock_board_result.scalar_one_or_none.return_value = db_board

                # Mock count query
                mock_count_result = MagicMock()
                mock_count_result.scalar.return_value = 42

                mock_async_session.execute.side_effect = [
                    mock_board_result,
                    mock_count_result
                ]

                result = await resolve_board_generation_count(sample_board, mock_info)

                assert result == 42

    @pytest.mark.asyncio
    async def test_generation_count_no_access(self, mock_info, auth_context, sample_board):
        """Test that generation count returns 0 when access is denied."""
        # Different owner, private board
        sample_board.owner_id = uuid.uuid4()

        db_board = MagicMock(spec=Boards)
        db_board.id = sample_board.id
        db_board.owner_id = sample_board.owner_id
        db_board.is_public = False
        db_board.board_members = []

        with patch('boards.graphql.resolvers.board.get_auth_context_from_info') as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_board_result = MagicMock()
                mock_board_result.scalar_one_or_none.return_value = db_board

                mock_async_session.execute.return_value = mock_board_result

                result = await resolve_board_generation_count(sample_board, mock_info)

                assert result == 0

    @pytest.mark.asyncio
    async def test_generation_count_board_not_found(self, mock_info, auth_context, sample_board):
        """Test generation count when board doesn't exist."""
        with patch('boards.graphql.resolvers.board.get_auth_context_from_info') as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = None

                mock_async_session.execute.return_value = mock_result

                result = await resolve_board_generation_count(sample_board, mock_info)

                assert result == 0

    @pytest.mark.asyncio
    async def test_generation_count_empty_board(self, mock_info, auth_context, sample_board):
        """Test generation count for board with no generations."""
        sample_board.owner_id = auth_context.user_id

        db_board = MagicMock(spec=Boards)
        db_board.id = sample_board.id
        db_board.owner_id = sample_board.owner_id
        db_board.is_public = False
        db_board.board_members = []

        with patch('boards.graphql.resolvers.board.get_auth_context_from_info') as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_board_result = MagicMock()
                mock_board_result.scalar_one_or_none.return_value = db_board

                mock_count_result = MagicMock()
                mock_count_result.scalar.return_value = 0

                mock_async_session.execute.side_effect = [
                    mock_board_result,
                    mock_count_result
                ]

                result = await resolve_board_generation_count(sample_board, mock_info)

                assert result == 0

    @pytest.mark.asyncio
    async def test_generation_count_public_board(self, mock_info, sample_board):
        """Test generation count for public board without authentication."""
        db_board = MagicMock(spec=Boards)
        db_board.id = sample_board.id
        db_board.owner_id = uuid.uuid4()
        db_board.is_public = True
        db_board.board_members = []

        with patch('boards.graphql.resolvers.board.get_auth_context_from_info') as mock_get_auth:
            mock_get_auth.return_value = None  # No authentication

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_board_result = MagicMock()
                mock_board_result.scalar_one_or_none.return_value = db_board

                mock_count_result = MagicMock()
                mock_count_result.scalar.return_value = 15

                mock_async_session.execute.side_effect = [
                    mock_board_result,
                    mock_count_result
                ]

                result = await resolve_board_generation_count(sample_board, mock_info)

                assert result == 15


class TestBoardMemberInviter:
    """Tests for resolve_board_member_inviter field resolver."""

    @pytest.mark.asyncio
    async def test_inviter_resolution(self, mock_info, auth_context, sample_board_member):
        """Test resolving the user who invited a board member."""
        inviter_id = sample_board_member.invited_by

        # Mock board with access
        db_board = MagicMock(spec=Boards)
        db_board.id = sample_board_member.board_id
        db_board.owner_id = auth_context.user_id
        db_board.is_public = False
        db_board.board_members = []

        # Mock inviter user
        inviter = MagicMock(spec=Users)
        inviter.id = inviter_id
        inviter.tenant_id = uuid.uuid4()
        inviter.auth_provider = "none"
        inviter.auth_subject = "inviter"
        inviter.email = "inviter@example.com"
        inviter.display_name = "Inviter User"
        inviter.avatar_url = None
        inviter.created_at = datetime.now(UTC)
        inviter.updated_at = datetime.now(UTC)

        with patch('boards.graphql.resolvers.board.get_auth_context_from_info') as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_board_result = MagicMock()
                mock_board_result.scalar_one_or_none.return_value = db_board

                mock_inviter_result = MagicMock()
                mock_inviter_result.scalar_one_or_none.return_value = inviter

                mock_async_session.execute.side_effect = [
                    mock_board_result,
                    mock_inviter_result
                ]

                result = await resolve_board_member_inviter(sample_board_member, mock_info)

                assert result is not None
                assert result.id == inviter_id
                assert result.email == "inviter@example.com"
                assert result.display_name == "Inviter User"

    @pytest.mark.asyncio
    async def test_inviter_none_when_no_inviter(self, mock_info):
        """Test that None is returned when member has no inviter."""
        member = BoardMember(
            id=uuid.uuid4(),
            board_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            role=BoardRole.VIEWER,
            invited_by=None,  # No inviter
            joined_at=datetime.now(UTC)
        )

        result = await resolve_board_member_inviter(member, mock_info)

        assert result is None

    @pytest.mark.asyncio
    async def test_inviter_access_denied(self, mock_info, auth_context, sample_board_member):
        """Test that error is raised when access to board is denied."""
        # Mock board without access
        db_board = MagicMock(spec=Boards)
        db_board.id = sample_board_member.board_id
        db_board.owner_id = uuid.uuid4()  # Different owner
        db_board.is_public = False
        db_board.board_members = []  # User is not a member

        with patch('boards.graphql.resolvers.board.get_auth_context_from_info') as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_board_result = MagicMock()
                mock_board_result.scalar_one_or_none.return_value = db_board

                mock_async_session.execute.return_value = mock_board_result

                with pytest.raises(RuntimeError, match="Access denied"):
                    await resolve_board_member_inviter(sample_board_member, mock_info)

    @pytest.mark.asyncio
    async def test_inviter_not_found(self, mock_info, auth_context, sample_board_member):
        """Test that None is returned when inviter user doesn't exist."""
        # Mock board with access
        db_board = MagicMock(spec=Boards)
        db_board.id = sample_board_member.board_id
        db_board.owner_id = auth_context.user_id
        db_board.is_public = False
        db_board.board_members = []

        with patch('boards.graphql.resolvers.board.get_auth_context_from_info') as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_board_result = MagicMock()
                mock_board_result.scalar_one_or_none.return_value = db_board

                mock_inviter_result = MagicMock()
                mock_inviter_result.scalar_one_or_none.return_value = None  # Inviter not found

                mock_async_session.execute.side_effect = [
                    mock_board_result,
                    mock_inviter_result
                ]

                result = await resolve_board_member_inviter(sample_board_member, mock_info)

                assert result is None

    @pytest.mark.asyncio
    async def test_inviter_board_not_found(self, mock_info, auth_context, sample_board_member):
        """Test error when board doesn't exist."""
        with patch('boards.graphql.resolvers.board.get_auth_context_from_info') as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = None  # Board not found

                mock_async_session.execute.return_value = mock_result

                with pytest.raises(RuntimeError, match="Access denied"):
                    await resolve_board_member_inviter(sample_board_member, mock_info)
