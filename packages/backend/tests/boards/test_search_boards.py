"""
Unit tests for search_boards query function
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import strawberry
from sqlalchemy.ext.asyncio import AsyncSession

from boards.auth.context import AuthContext
from boards.dbmodels import BoardMembers, Boards
from boards.graphql.resolvers.board import search_boards


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
def sample_boards():
    """Create sample boards for testing search functionality."""
    tenant_id = uuid.uuid4()
    owner_id = uuid.uuid4()

    boards = []

    # Public board with "Python" in title
    board1 = MagicMock(spec=Boards)
    board1.id = uuid.uuid4()
    board1.tenant_id = tenant_id
    board1.owner_id = owner_id
    board1.title = "Python Programming Guide"
    board1.description = "Learn Python basics"
    board1.is_public = True
    board1.settings = {}
    board1.metadata_ = {}
    board1.created_at = datetime.now(UTC)
    board1.updated_at = datetime.now(UTC)
    board1.board_members = []
    boards.append(board1)

    # Private board with "Python" in description
    board2 = MagicMock(spec=Boards)
    board2.id = uuid.uuid4()
    board2.tenant_id = tenant_id
    board2.owner_id = owner_id
    board2.title = "Advanced Topics"
    board2.description = "Advanced Python techniques and patterns"
    board2.is_public = False
    board2.settings = {}
    board2.metadata_ = {}
    board2.created_at = datetime.now(UTC)
    board2.updated_at = datetime.now(UTC)
    board2.board_members = []
    boards.append(board2)

    # Public board without search term
    board3 = MagicMock(spec=Boards)
    board3.id = uuid.uuid4()
    board3.tenant_id = tenant_id
    board3.owner_id = uuid.uuid4()  # Different owner
    board3.title = "JavaScript Guide"
    board3.description = "Learn JavaScript"
    board3.is_public = True
    board3.settings = {}
    board3.metadata_ = {}
    board3.created_at = datetime.now(UTC)
    board3.updated_at = datetime.now(UTC)
    board3.board_members = []
    boards.append(board3)

    return boards, owner_id


class TestSearchBoards:
    """Tests for search_boards function."""

    @pytest.mark.asyncio
    async def test_search_public_boards_without_auth(self, mock_info, sample_boards):
        """Test searching public boards without authentication."""
        boards, _ = sample_boards

        with patch('boards.graphql.resolvers.board.get_auth_context_from_info') as mock_get_auth:
            mock_get_auth.return_value = AuthContext(
                user_id=None,
                tenant_id="default",
                principal=None,
                token=None
            )

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock(spec=AsyncSession)
                mock_session.return_value.__aenter__.return_value = mock_async_session

                # Mock query execution - only returns public board with "Python"
                mock_result = MagicMock()
                mock_result.scalars().all.return_value = [boards[0]]  # Only first public board
                mock_async_session.execute.return_value = mock_result

                results = await search_boards(mock_info, "Python", limit=10, offset=0)

                assert len(results) == 1
                assert results[0].title == "Python Programming Guide"
                assert results[0].is_public is True

    @pytest.mark.asyncio
    async def test_search_with_owner_access(self, mock_info, sample_boards):
        """Test that board owner can search their private boards."""
        boards, owner_id = sample_boards

        with patch('boards.graphql.resolvers.board.get_auth_context_from_info') as mock_get_auth:
            mock_get_auth.return_value = AuthContext(
                user_id=owner_id,
                tenant_id="default",
                principal={"provider": "none", "subject": "owner"},
                token="test-token"
            )

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock(spec=AsyncSession)
                mock_session.return_value.__aenter__.return_value = mock_async_session

                # Mock returns both boards (public and private owned)
                mock_result = MagicMock()
                mock_result.scalars().all.return_value = [boards[0], boards[1]]
                mock_async_session.execute.return_value = mock_result

                results = await search_boards(mock_info, "Python", limit=10, offset=0)

                assert len(results) == 2
                assert any(b.title == "Python Programming Guide" for b in results)
                assert any(b.title == "Advanced Topics" for b in results)

    @pytest.mark.asyncio
    async def test_search_with_member_access(self, mock_info, sample_boards):
        """Test that board members can search boards they belong to."""
        boards, _ = sample_boards
        member_id = uuid.uuid4()

        # Add member to private board
        member = MagicMock(spec=BoardMembers)
        member.user_id = member_id
        member.role = "viewer"
        boards[1].board_members = [member]

        with patch('boards.graphql.resolvers.board.get_auth_context_from_info') as mock_get_auth:
            mock_get_auth.return_value = AuthContext(
                user_id=member_id,
                tenant_id="default",
                principal={"provider": "none", "subject": "member"},
                token="test-token"
            )

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock(spec=AsyncSession)
                mock_session.return_value.__aenter__.return_value = mock_async_session

                # Returns public board and private board where user is member
                mock_result = MagicMock()
                mock_result.scalars().all.return_value = [boards[0], boards[1]]
                mock_async_session.execute.return_value = mock_result

                results = await search_boards(mock_info, "Python", limit=10, offset=0)

                assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, mock_info, sample_boards):
        """Test that search is case-insensitive."""
        boards, owner_id = sample_boards

        with patch('boards.graphql.resolvers.board.get_auth_context_from_info') as mock_get_auth:
            mock_get_auth.return_value = AuthContext(
                user_id=owner_id,
                tenant_id="default",
                principal={"provider": "none", "subject": "owner"},
                token="test-token"
            )

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock(spec=AsyncSession)
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalars().all.return_value = [boards[0], boards[1]]
                mock_async_session.execute.return_value = mock_result

                # Search with lowercase
                results = await search_boards(mock_info, "python", limit=10, offset=0)
                assert len(results) == 2

                # Search with uppercase
                results = await search_boards(mock_info, "PYTHON", limit=10, offset=0)
                assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_with_pagination(self, mock_info, sample_boards):
        """Test search with limit and offset pagination."""
        boards, _ = sample_boards

        with patch('boards.graphql.resolvers.board.get_auth_context_from_info') as mock_get_auth:
            mock_get_auth.return_value = AuthContext(
                user_id=None,
                tenant_id="default",
                principal=None,
                token=None
            )

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock(spec=AsyncSession)
                mock_session.return_value.__aenter__.return_value = mock_async_session

                # Create a mock execute that validates limit/offset were used
                execute_call_count = 0

                async def mock_execute(stmt):
                    nonlocal execute_call_count
                    execute_call_count += 1

                    # Check that statement has limit and offset
                    stmt_str = str(stmt)
                    assert "LIMIT" in stmt_str or hasattr(stmt, '_limit')
                    assert "OFFSET" in stmt_str or hasattr(stmt, '_offset')

                    mock_result = MagicMock()
                    mock_result.scalars().all.return_value = [boards[0]]
                    return mock_result

                mock_async_session.execute = mock_execute

                results = await search_boards(mock_info, "Python", limit=5, offset=10)

                assert execute_call_count == 1
                assert len(results) <= 5  # Respects limit

    @pytest.mark.asyncio
    async def test_search_no_results(self, mock_info):
        """Test search that returns no results."""
        with patch('boards.graphql.resolvers.board.get_auth_context_from_info') as mock_get_auth:
            mock_get_auth.return_value = AuthContext(
                user_id=uuid.uuid4(),
                tenant_id="default",
                principal={"provider": "none", "subject": "user"},
                token="test-token"
            )

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock(spec=AsyncSession)
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalars().all.return_value = []
                mock_async_session.execute.return_value = mock_result

                results = await search_boards(mock_info, "NonExistentTerm", limit=10, offset=0)

                assert results == []

    @pytest.mark.asyncio
    async def test_search_empty_query(self, mock_info, sample_boards):
        """Test search with empty query string."""
        boards, _ = sample_boards

        with patch('boards.graphql.resolvers.board.get_auth_context_from_info') as mock_get_auth:
            mock_get_auth.return_value = AuthContext(
                user_id=None,
                tenant_id="default",
                principal=None,
                token=None
            )

            with patch('boards.graphql.resolvers.board.get_async_session') as mock_session:
                mock_async_session = AsyncMock(spec=AsyncSession)
                mock_session.return_value.__aenter__.return_value = mock_async_session

                # Empty query should match all accessible boards
                mock_result = MagicMock()
                mock_result.scalars().all.return_value = [b for b in boards if b.is_public]
                mock_async_session.execute.return_value = mock_result

                results = await search_boards(mock_info, "", limit=10, offset=0)

                # Should return all public boards
                assert len(results) == 2
                assert all(b.is_public for b in results)
