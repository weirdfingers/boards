"""
Simple unit tests for board access control logic
"""

import uuid
from unittest.mock import MagicMock

import pytest

from boards.auth.context import AuthContext
from boards.dbmodels import Boards, BoardMembers
from boards.graphql.access_control import (
    can_access_board,
    can_access_board_details,
    is_board_owner_or_member,
    ensure_preloaded,
)


@pytest.fixture
def sample_board():
    """Create a sample board for testing."""
    board = MagicMock(spec=Boards)
    board.id = uuid.uuid4()
    board.owner_id = uuid.uuid4()
    board.is_public = False
    board.board_members = []
    return board


@pytest.fixture
def authenticated_context():
    """Create an authenticated user context."""
    return AuthContext(
        user_id=uuid.uuid4(),
        tenant_id="test-tenant",
        principal={"provider": "none", "subject": "test-user"},
        token="test-token"
    )


@pytest.fixture
def unauthenticated_context():
    """Create an unauthenticated context."""
    return AuthContext(
        user_id=None,
        tenant_id="test-tenant",
        principal=None,
        token=None
    )


class TestCanAccessBoard:
    """Tests for can_access_board function."""

    def test_public_board_unauthenticated(self, sample_board, unauthenticated_context):
        """Public boards should be accessible without authentication."""
        sample_board.is_public = True
        assert can_access_board(sample_board, unauthenticated_context) is True

    def test_public_board_authenticated(self, sample_board, authenticated_context):
        """Public boards should be accessible with authentication."""
        sample_board.is_public = True
        assert can_access_board(sample_board, authenticated_context) is True

    def test_private_board_unauthenticated(self, sample_board, unauthenticated_context):
        """Private boards should not be accessible without authentication."""
        sample_board.is_public = False
        assert can_access_board(sample_board, unauthenticated_context) is False

    def test_private_board_owner(self, sample_board, authenticated_context):
        """Board owners should be able to access their private boards."""
        sample_board.is_public = False
        sample_board.owner_id = authenticated_context.user_id
        assert can_access_board(sample_board, authenticated_context) is True

    def test_private_board_member(self, sample_board, authenticated_context):
        """Board members should be able to access private boards they belong to."""
        sample_board.is_public = False

        # Create a member relationship
        member = MagicMock(spec=BoardMembers)
        member.user_id = authenticated_context.user_id
        sample_board.board_members = [member]

        assert can_access_board(sample_board, authenticated_context) is True

    def test_private_board_unauthorized(self, sample_board, authenticated_context):
        """Unauthorized users should not be able to access private boards."""
        sample_board.is_public = False
        sample_board.owner_id = uuid.uuid4()  # Different from authenticated user
        sample_board.board_members = []  # Not a member

        assert can_access_board(sample_board, authenticated_context) is False

    def test_none_auth_context(self, sample_board):
        """Test behavior with None auth context."""
        sample_board.is_public = True
        assert can_access_board(sample_board, None) is True

        sample_board.is_public = False
        assert can_access_board(sample_board, None) is False


class TestCanAccessBoardDetails:
    """Tests for can_access_board_details function."""

    def test_same_as_can_access_board(self, sample_board, authenticated_context):
        """can_access_board_details should behave the same as can_access_board."""
        # Test public board
        sample_board.is_public = True
        assert can_access_board_details(sample_board, authenticated_context) == \
               can_access_board(sample_board, authenticated_context)

        # Test private board as owner
        sample_board.is_public = False
        sample_board.owner_id = authenticated_context.user_id
        assert can_access_board_details(sample_board, authenticated_context) == \
               can_access_board(sample_board, authenticated_context)


class TestIsBoardOwnerOrMember:
    """Tests for is_board_owner_or_member function."""

    def test_unauthenticated(self, sample_board, unauthenticated_context):
        """Unauthenticated users are not owners or members."""
        assert is_board_owner_or_member(sample_board, unauthenticated_context) is False

    def test_none_context(self, sample_board):
        """None context should return False."""
        assert is_board_owner_or_member(sample_board, None) is False

    def test_owner(self, sample_board, authenticated_context):
        """Board owners should be recognized as such."""
        sample_board.owner_id = authenticated_context.user_id
        assert is_board_owner_or_member(sample_board, authenticated_context) is True

    def test_member(self, sample_board, authenticated_context):
        """Board members should be recognized as such."""
        member = MagicMock(spec=BoardMembers)
        member.user_id = authenticated_context.user_id
        sample_board.board_members = [member]

        assert is_board_owner_or_member(sample_board, authenticated_context) is True

    def test_neither_owner_nor_member(self, sample_board, authenticated_context):
        """Users who are neither owners nor members should return False."""
        sample_board.owner_id = uuid.uuid4()  # Different user
        sample_board.board_members = []

        assert is_board_owner_or_member(sample_board, authenticated_context) is False

    def test_public_board_not_sufficient(self, sample_board, authenticated_context):
        """Public access is not sufficient for is_board_owner_or_member."""
        sample_board.is_public = True
        sample_board.owner_id = uuid.uuid4()  # Different user
        sample_board.board_members = []

        assert is_board_owner_or_member(sample_board, authenticated_context) is False


class TestEnsurePreloaded:
    """Tests for ensure_preloaded function."""

    def test_preloaded_attribute(self):
        """Should not raise when attribute is preloaded."""
        obj = MagicMock()
        obj.preloaded_attr = "value"

        # Should not raise
        ensure_preloaded(obj, "preloaded_attr")

    def test_not_preloaded_attribute(self):
        """Should raise when attribute was not preloaded."""
        obj = MagicMock()

        # Mock the behavior of accessing a non-preloaded relationship
        def side_effect(self):
            raise Exception("Object was not loaded")

        type(obj).not_loaded_attr = property(side_effect)

        with pytest.raises(RuntimeError, match="was not preloaded"):
            ensure_preloaded(obj, "not_loaded_attr")

    def test_custom_error_message(self):
        """Should use custom error message when provided."""
        obj = MagicMock()

        def side_effect(self):
            raise Exception("lazy loading is not allowed")

        type(obj).attr = property(side_effect)

        custom_msg = "Custom error message"
        with pytest.raises(RuntimeError, match=custom_msg):
            ensure_preloaded(obj, "attr", custom_msg)

    def test_other_exception_propagated(self):
        """Should propagate exceptions that are not related to lazy loading."""
        obj = MagicMock()

        def side_effect(self):
            raise ValueError("Some other error")

        type(obj).attr = property(side_effect)

        with pytest.raises(ValueError, match="Some other error"):
            ensure_preloaded(obj, "attr")