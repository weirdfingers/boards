"""
Unit tests for board mutation functions
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import strawberry

from boards.auth.context import AuthContext
from boards.dbmodels import BoardMembers, Boards, Users
from boards.graphql.mutations.root import (
    AddBoardMemberInput,
    CreateBoardInput,
    UpdateBoardInput,
)
from boards.graphql.resolvers.board import (
    add_board_member,
    create_board,
    delete_board,
    remove_board_member,
    update_board,
    update_board_member_role,
)
from boards.graphql.types.board import BoardRole


@pytest.fixture
def mock_info():
    """Create a mock GraphQL info object with request context."""
    info = MagicMock(spec=strawberry.Info)
    info.context = {
        "request": MagicMock(
            headers=MagicMock(
                get=MagicMock(
                    side_effect=lambda key: {
                        "authorization": "Bearer test-token",
                        "x-tenant": "default",
                    }.get(key)
                )
            )
        )
    }
    return info


@pytest.fixture
def auth_context():
    """Create an authenticated context."""
    return AuthContext(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        principal={"provider": "none", "subject": "test-user"},
        token="test-token",
    )


@pytest.fixture
def sample_board():
    """Create a sample board for testing."""
    board = MagicMock(spec=Boards)
    board.id = uuid.uuid4()
    board.tenant_id = uuid.uuid4()
    board.owner_id = uuid.uuid4()
    board.title = "Test Board"
    board.description = "A test board"
    board.is_public = False
    board.settings = {}
    board.metadata_ = {}
    board.created_at = datetime.now(UTC)
    board.updated_at = datetime.now(UTC)
    board.board_members = []
    return board


class TestCreateBoard:
    """Tests for create_board mutation."""

    @pytest.mark.asyncio
    async def test_create_board_success(self, mock_info, auth_context):
        """Test successful board creation."""
        input_data = CreateBoardInput(
            title="New Board",
            description="Board description",
            is_public=False,
            settings={"theme": "dark"},
        )

        with patch(
            "boards.graphql.resolvers.board.get_auth_context_from_info"
        ) as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch(
                "boards.graphql.resolvers.board.get_async_session"
            ) as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                # Mock the new board creation
                new_board = MagicMock(spec=Boards)
                new_board.id = uuid.uuid4()
                new_board.tenant_id = auth_context.tenant_id
                new_board.owner_id = auth_context.user_id
                new_board.title = input_data.title
                new_board.description = input_data.description
                new_board.is_public = input_data.is_public
                new_board.settings = input_data.settings
                new_board.metadata_ = {}
                new_board.created_at = datetime.now(UTC)
                new_board.updated_at = datetime.now(UTC)

                # Mock refresh and query
                async def mock_refresh(board):
                    board.id = new_board.id

                mock_async_session.refresh = mock_refresh

                mock_result = MagicMock()
                mock_result.scalar_one.return_value = new_board
                mock_async_session.execute.return_value = mock_result

                result = await create_board(mock_info, input_data)

                assert result.title == "New Board"
                assert result.description == "Board description"
                assert result.is_public is False
                assert result.settings == {"theme": "dark"}
                assert result.owner_id == auth_context.user_id

                # Verify session methods were called
                mock_async_session.add.assert_called_once()
                mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_board_unauthenticated(self, mock_info):
        """Test that unauthenticated users cannot create boards."""
        input_data = CreateBoardInput(
            title="New Board", description="Board description"
        )

        with patch(
            "boards.graphql.resolvers.board.get_auth_context_from_info"
        ) as mock_get_auth:
            mock_get_auth.return_value = None

            with pytest.raises(RuntimeError, match="Authentication required"):
                await create_board(mock_info, input_data)

    @pytest.mark.asyncio
    async def test_create_board_minimal_input(self, mock_info, auth_context):
        """Test board creation with minimal input."""
        input_data = CreateBoardInput(title="Minimal Board")

        with patch(
            "boards.graphql.resolvers.board.get_auth_context_from_info"
        ) as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch(
                "boards.graphql.resolvers.board.get_async_session"
            ) as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                new_board = MagicMock(spec=Boards)
                new_board.id = uuid.uuid4()
                new_board.title = input_data.title
                new_board.description = None
                new_board.is_public = False
                new_board.settings = {}
                new_board.metadata_ = {}

                async def mock_refresh(board):
                    board.id = new_board.id

                mock_async_session.refresh = mock_refresh

                mock_result = MagicMock()
                mock_result.scalar_one.return_value = new_board
                mock_async_session.execute.return_value = mock_result

                result = await create_board(mock_info, input_data)

                assert result.title == "Minimal Board"
                assert result.is_public is False
                assert result.settings == {}


class TestUpdateBoard:
    """Tests for update_board mutation."""

    @pytest.mark.asyncio
    async def test_update_board_as_owner(self, mock_info, auth_context, sample_board):
        """Test board update by owner."""
        sample_board.owner_id = auth_context.user_id

        input_data = UpdateBoardInput(
            id=sample_board.id,
            title="Updated Title",
            description="Updated description",
            is_public=True,
        )

        with patch(
            "boards.graphql.resolvers.board.get_auth_context_from_info"
        ) as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch(
                "boards.graphql.resolvers.board.get_async_session"
            ) as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = sample_board
                mock_async_session.execute.return_value = mock_result

                result = await update_board(mock_info, input_data)

                assert result.title == "Updated Title"
                assert result.description == "Updated description"
                assert result.is_public is True

                mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_board_as_admin(self, mock_info, auth_context, sample_board):
        """Test board update by admin member."""
        admin_member = MagicMock(spec=BoardMembers)
        admin_member.user_id = auth_context.user_id
        admin_member.role = "admin"
        sample_board.board_members = [admin_member]

        input_data = UpdateBoardInput(id=sample_board.id, title="Admin Updated")

        with patch(
            "boards.graphql.resolvers.board.get_auth_context_from_info"
        ) as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch(
                "boards.graphql.resolvers.board.get_async_session"
            ) as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = sample_board
                mock_async_session.execute.return_value = mock_result

                result = await update_board(mock_info, input_data)

                assert result.title == "Admin Updated"
                mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_board_permission_denied(
        self, mock_info, auth_context, sample_board
    ):
        """Test that non-owner/non-admin cannot update board."""
        # User is not owner and not a member
        sample_board.owner_id = uuid.uuid4()

        input_data = UpdateBoardInput(id=sample_board.id, title="Should Fail")

        with patch(
            "boards.graphql.resolvers.board.get_auth_context_from_info"
        ) as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch(
                "boards.graphql.resolvers.board.get_async_session"
            ) as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = sample_board
                mock_async_session.execute.return_value = mock_result

                with pytest.raises(RuntimeError, match="Permission denied"):
                    await update_board(mock_info, input_data)

    @pytest.mark.asyncio
    async def test_update_board_not_found(self, mock_info, auth_context):
        """Test updating non-existent board."""
        input_data = UpdateBoardInput(id=uuid.uuid4(), title="Should Fail")

        with patch(
            "boards.graphql.resolvers.board.get_auth_context_from_info"
        ) as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch(
                "boards.graphql.resolvers.board.get_async_session"
            ) as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = None
                mock_async_session.execute.return_value = mock_result

                with pytest.raises(RuntimeError, match="Board not found"):
                    await update_board(mock_info, input_data)


class TestDeleteBoard:
    """Tests for delete_board mutation."""

    @pytest.mark.asyncio
    async def test_delete_board_as_owner(self, mock_info, auth_context, sample_board):
        """Test successful board deletion by owner."""
        sample_board.owner_id = auth_context.user_id

        with patch(
            "boards.graphql.resolvers.board.get_auth_context_from_info"
        ) as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch(
                "boards.graphql.resolvers.board.get_async_session"
            ) as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = sample_board
                mock_async_session.execute.return_value = mock_result

                result = await delete_board(mock_info, sample_board.id)

                assert result is True
                mock_async_session.delete.assert_called_once_with(sample_board)
                mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_board_permission_denied(
        self, mock_info, auth_context, sample_board
    ):
        """Test that non-owner cannot delete board."""
        sample_board.owner_id = uuid.uuid4()  # Different owner

        with patch(
            "boards.graphql.resolvers.board.get_auth_context_from_info"
        ) as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch(
                "boards.graphql.resolvers.board.get_async_session"
            ) as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = sample_board
                mock_async_session.execute.return_value = mock_result

                with pytest.raises(RuntimeError, match="Permission denied"):
                    await delete_board(mock_info, sample_board.id)

    @pytest.mark.asyncio
    async def test_delete_board_not_found(self, mock_info, auth_context):
        """Test deleting non-existent board."""
        with patch(
            "boards.graphql.resolvers.board.get_auth_context_from_info"
        ) as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch(
                "boards.graphql.resolvers.board.get_async_session"
            ) as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = None
                mock_async_session.execute.return_value = mock_result

                with pytest.raises(RuntimeError, match="Board not found"):
                    await delete_board(mock_info, uuid.uuid4())


class TestAddBoardMember:
    """Tests for add_board_member mutation."""

    @pytest.mark.asyncio
    async def test_add_member_as_owner(self, mock_info, auth_context, sample_board):
        """Test adding a member as board owner."""
        sample_board.owner_id = auth_context.user_id
        new_user_id = uuid.uuid4()

        # Mock the user to be added
        new_user = MagicMock(spec=Users)
        new_user.id = new_user_id

        input_data = AddBoardMemberInput(
            board_id=sample_board.id, user_id=new_user_id, role=BoardRole.EDITOR
        )

        with patch(
            "boards.graphql.resolvers.board.get_auth_context_from_info"
        ) as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch(
                "boards.graphql.resolvers.board.get_async_session"
            ) as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                # Mock board query
                mock_board_result = MagicMock()
                mock_board_result.scalar_one_or_none.return_value = sample_board

                # Mock user query
                mock_user_result = MagicMock()
                mock_user_result.scalar_one_or_none.return_value = new_user

                # Mock refreshed board query
                refreshed_board = MagicMock(spec=Boards)
                refreshed_board.id = sample_board.id
                refreshed_board.board_members = [
                    MagicMock(user_id=new_user_id, role="editor")
                ]
                mock_refreshed_result = MagicMock()
                mock_refreshed_result.scalar_one.return_value = refreshed_board

                mock_async_session.execute.side_effect = [
                    mock_board_result,
                    mock_user_result,
                    mock_refreshed_result,
                ]

                result = await add_board_member(mock_info, input_data)

                assert result is not None
                mock_async_session.add.assert_called_once()
                mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_member_user_not_found(
        self, mock_info, auth_context, sample_board
    ):
        """Test adding non-existent user as member."""
        sample_board.owner_id = auth_context.user_id

        input_data = AddBoardMemberInput(
            board_id=sample_board.id, user_id=uuid.uuid4(), role=BoardRole.VIEWER
        )

        with patch(
            "boards.graphql.resolvers.board.get_auth_context_from_info"
        ) as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch(
                "boards.graphql.resolvers.board.get_async_session"
            ) as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_board_result = MagicMock()
                mock_board_result.scalar_one_or_none.return_value = sample_board

                mock_user_result = MagicMock()
                mock_user_result.scalar_one_or_none.return_value = (
                    None  # User not found
                )

                mock_async_session.execute.side_effect = [
                    mock_board_result,
                    mock_user_result,
                ]

                with pytest.raises(RuntimeError, match="User not found"):
                    await add_board_member(mock_info, input_data)

    @pytest.mark.asyncio
    async def test_add_member_already_owner(
        self, mock_info, auth_context, sample_board
    ):
        """Test that owner cannot be added as member."""
        sample_board.owner_id = auth_context.user_id

        input_data = AddBoardMemberInput(
            board_id=sample_board.id,
            user_id=auth_context.user_id,  # Trying to add owner as member
            role=BoardRole.VIEWER,
        )

        with patch(
            "boards.graphql.resolvers.board.get_auth_context_from_info"
        ) as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch(
                "boards.graphql.resolvers.board.get_async_session"
            ) as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_board_result = MagicMock()
                mock_board_result.scalar_one_or_none.return_value = sample_board

                mock_user_result = MagicMock()
                mock_user_result.scalar_one_or_none.return_value = MagicMock(spec=Users)

                mock_async_session.execute.side_effect = [
                    mock_board_result,
                    mock_user_result,
                ]

                with pytest.raises(RuntimeError, match="already the board owner"):
                    await add_board_member(mock_info, input_data)


class TestRemoveBoardMember:
    """Tests for remove_board_member mutation."""

    @pytest.mark.asyncio
    async def test_remove_member_as_owner(self, mock_info, auth_context, sample_board):
        """Test removing a member as board owner."""
        sample_board.owner_id = auth_context.user_id
        member_to_remove_id = uuid.uuid4()

        member = MagicMock(spec=BoardMembers)
        member.user_id = member_to_remove_id
        member.role = "viewer"
        sample_board.board_members = [member]

        with patch(
            "boards.graphql.resolvers.board.get_auth_context_from_info"
        ) as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch(
                "boards.graphql.resolvers.board.get_async_session"
            ) as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = sample_board
                mock_result.scalar_one.return_value = sample_board

                mock_async_session.execute.side_effect = [mock_result, mock_result]

                result = await remove_board_member(
                    mock_info, sample_board.id, member_to_remove_id
                )

                assert result is not None
                mock_async_session.delete.assert_called_once_with(member)
                mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_self_as_member(self, mock_info, auth_context, sample_board):
        """Test that member can remove themselves."""
        sample_board.owner_id = uuid.uuid4()  # Different owner

        member = MagicMock(spec=BoardMembers)
        member.user_id = auth_context.user_id
        member.role = "viewer"
        sample_board.board_members = [member]

        with patch(
            "boards.graphql.resolvers.board.get_auth_context_from_info"
        ) as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch(
                "boards.graphql.resolvers.board.get_async_session"
            ) as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = sample_board
                mock_result.scalar_one.return_value = sample_board

                mock_async_session.execute.side_effect = [mock_result, mock_result]

                result = await remove_board_member(
                    mock_info, sample_board.id, auth_context.user_id  # Removing self
                )

                assert result is not None
                mock_async_session.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_cannot_remove_owner(self, mock_info, auth_context, sample_board):
        """Test that board owner cannot be removed."""
        sample_board.owner_id = auth_context.user_id

        with patch(
            "boards.graphql.resolvers.board.get_auth_context_from_info"
        ) as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch(
                "boards.graphql.resolvers.board.get_async_session"
            ) as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = sample_board
                mock_async_session.execute.return_value = mock_result

                with pytest.raises(RuntimeError, match="Cannot remove the board owner"):
                    await remove_board_member(
                        mock_info,
                        sample_board.id,
                        auth_context.user_id,  # Trying to remove owner
                    )


class TestUpdateBoardMemberRole:
    """Tests for update_board_member_role mutation."""

    @pytest.mark.asyncio
    async def test_update_member_role_as_owner(
        self, mock_info, auth_context, sample_board
    ):
        """Test updating member role as board owner."""
        sample_board.owner_id = auth_context.user_id
        member_id = uuid.uuid4()

        member = MagicMock(spec=BoardMembers)
        member.user_id = member_id
        member.role = "viewer"
        sample_board.board_members = [member]

        with patch(
            "boards.graphql.resolvers.board.get_auth_context_from_info"
        ) as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch(
                "boards.graphql.resolvers.board.get_async_session"
            ) as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = sample_board
                mock_result.scalar_one.return_value = sample_board

                mock_async_session.execute.side_effect = [mock_result, mock_result]

                result = await update_board_member_role(
                    mock_info, sample_board.id, member_id, BoardRole.ADMIN
                )

                assert result is not None
                assert member.role == "admin"
                mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cannot_change_owner_role(
        self, mock_info, auth_context, sample_board
    ):
        """Test that owner's role cannot be changed."""
        sample_board.owner_id = auth_context.user_id

        with patch(
            "boards.graphql.resolvers.board.get_auth_context_from_info"
        ) as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch(
                "boards.graphql.resolvers.board.get_async_session"
            ) as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = sample_board
                mock_async_session.execute.return_value = mock_result

                with pytest.raises(
                    RuntimeError, match="Cannot change the board owner's role"
                ):
                    await update_board_member_role(
                        mock_info,
                        sample_board.id,
                        auth_context.user_id,  # Trying to change owner's role
                        BoardRole.VIEWER,
                    )
