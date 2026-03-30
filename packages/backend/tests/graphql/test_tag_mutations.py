"""
Unit tests for tag mutation functions
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import strawberry

from boards.auth.context import AuthContext
from boards.dbmodels import BoardMembers, Boards, Generations, GenerationTags, Tags
from boards.graphql.mutations.root import CreateTagInput, UpdateTagInput
from boards.graphql.resolvers.tag import (
    add_tag_to_generation,
    create_tag,
    delete_tag,
    remove_tag_from_generation,
    resolve_generation_tags,
    resolve_tag_by_id,
    resolve_tag_by_slug,
    resolve_tags,
    slugify,
    update_tag,
)


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
def sample_tag():
    """Create a sample tag for testing."""
    tag = MagicMock(spec=Tags)
    tag.id = uuid.uuid4()
    tag.tenant_id = uuid.uuid4()
    tag.name = "Test Tag"
    tag.slug = "test-tag"
    tag.description = "A test tag"
    tag.metadata_ = {}
    tag.created_at = datetime.now(UTC)
    tag.updated_at = datetime.now(UTC)
    return tag


@pytest.fixture
def sample_board():
    """Create a sample board for testing."""
    board = MagicMock(spec=Boards)
    board.id = uuid.uuid4()
    board.tenant_id = uuid.uuid4()
    board.owner_id = uuid.uuid4()
    board.title = "Test Board"
    board.is_public = False
    board.board_members = []
    return board


@pytest.fixture
def sample_generation():
    """Create a sample generation for testing."""
    gen = MagicMock(spec=Generations)
    gen.id = uuid.uuid4()
    gen.tenant_id = uuid.uuid4()
    gen.board_id = uuid.uuid4()
    gen.user_id = uuid.uuid4()
    return gen


class TestSlugify:
    """Tests for the slugify helper function."""

    def test_slugify_basic(self):
        """Test basic slugification."""
        assert slugify("Hello World") == "hello-world"

    def test_slugify_uppercase(self):
        """Test that uppercase is converted to lowercase."""
        assert slugify("UPPERCASE") == "uppercase"

    def test_slugify_special_chars(self):
        """Test that special characters are removed."""
        assert slugify("Hello! @World#") == "hello-world"

    def test_slugify_underscores(self):
        """Test that underscores become hyphens."""
        assert slugify("hello_world") == "hello-world"

    def test_slugify_multiple_spaces(self):
        """Test that multiple spaces become single hyphen."""
        assert slugify("hello   world") == "hello-world"

    def test_slugify_leading_trailing(self):
        """Test that leading/trailing hyphens are stripped."""
        assert slugify("  hello world  ") == "hello-world"


class TestCreateTag:
    """Tests for create_tag mutation."""

    @pytest.mark.asyncio
    async def test_create_tag_success(self, mock_info, auth_context):
        """Test successful tag creation."""
        input_data = CreateTagInput(
            name="New Tag",
            description="Tag description",
            metadata={"color": "blue"},
        )

        with patch("boards.graphql.resolvers.tag.get_auth_context_from_info") as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch("boards.graphql.resolvers.tag.get_async_session") as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                # Mock no existing tag with same slug
                mock_existing_result = MagicMock()
                mock_existing_result.scalar_one_or_none.return_value = None
                mock_async_session.execute.return_value = mock_existing_result

                # Mock the new tag after refresh
                new_tag = MagicMock(spec=Tags)
                new_tag.id = uuid.uuid4()
                new_tag.tenant_id = auth_context.tenant_id
                new_tag.name = input_data.name
                new_tag.slug = "new-tag"
                new_tag.description = input_data.description
                new_tag.metadata_ = input_data.metadata
                new_tag.created_at = datetime.now(UTC)
                new_tag.updated_at = datetime.now(UTC)

                async def mock_refresh(tag):
                    tag.id = new_tag.id
                    tag.tenant_id = new_tag.tenant_id
                    tag.name = new_tag.name
                    tag.slug = new_tag.slug
                    tag.description = new_tag.description
                    tag.metadata_ = new_tag.metadata_
                    tag.created_at = new_tag.created_at
                    tag.updated_at = new_tag.updated_at

                mock_async_session.refresh = mock_refresh

                result = await create_tag(mock_info, input_data)

                assert result.name == "New Tag"
                assert result.slug == "new-tag"
                assert result.description == "Tag description"

                mock_async_session.add.assert_called_once()
                mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_tag_with_custom_slug(self, mock_info, auth_context):
        """Test tag creation with custom slug."""
        input_data = CreateTagInput(
            name="New Tag",
            slug="custom-slug",
        )

        with patch("boards.graphql.resolvers.tag.get_auth_context_from_info") as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch("boards.graphql.resolvers.tag.get_async_session") as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_existing_result = MagicMock()
                mock_existing_result.scalar_one_or_none.return_value = None
                mock_async_session.execute.return_value = mock_existing_result

                new_tag = MagicMock(spec=Tags)
                new_tag.id = uuid.uuid4()
                new_tag.tenant_id = auth_context.tenant_id
                new_tag.name = input_data.name
                new_tag.slug = "custom-slug"
                new_tag.description = None
                new_tag.metadata_ = {}
                new_tag.created_at = datetime.now(UTC)
                new_tag.updated_at = datetime.now(UTC)

                async def mock_refresh(tag):
                    tag.id = new_tag.id
                    tag.slug = new_tag.slug

                mock_async_session.refresh = mock_refresh

                result = await create_tag(mock_info, input_data)

                assert result.slug == "custom-slug"

    @pytest.mark.asyncio
    async def test_create_tag_duplicate_slug(self, mock_info, auth_context, sample_tag):
        """Test that duplicate slug raises error."""
        input_data = CreateTagInput(name="Test Tag")

        with patch("boards.graphql.resolvers.tag.get_auth_context_from_info") as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch("boards.graphql.resolvers.tag.get_async_session") as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                # Mock existing tag with same slug
                mock_existing_result = MagicMock()
                mock_existing_result.scalar_one_or_none.return_value = sample_tag
                mock_async_session.execute.return_value = mock_existing_result

                with pytest.raises(RuntimeError, match="already exists"):
                    await create_tag(mock_info, input_data)

    @pytest.mark.asyncio
    async def test_create_tag_unauthenticated(self, mock_info):
        """Test that unauthenticated users cannot create tags."""
        input_data = CreateTagInput(name="New Tag")

        with patch("boards.graphql.resolvers.tag.get_auth_context_from_info") as mock_get_auth:
            mock_get_auth.return_value = None

            with pytest.raises(RuntimeError, match="Authentication required"):
                await create_tag(mock_info, input_data)


class TestUpdateTag:
    """Tests for update_tag mutation."""

    @pytest.mark.asyncio
    async def test_update_tag_success(self, mock_info, auth_context, sample_tag):
        """Test successful tag update."""
        sample_tag.tenant_id = auth_context.tenant_id

        input_data = UpdateTagInput(
            id=sample_tag.id,
            name="Updated Tag",
            description="Updated description",
        )

        with patch("boards.graphql.resolvers.tag.get_auth_context_from_info") as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch("boards.graphql.resolvers.tag.get_async_session") as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                # First call: get tag, second call: check for duplicate slug
                mock_tag_result = MagicMock()
                mock_tag_result.scalar_one_or_none.return_value = sample_tag

                mock_slug_result = MagicMock()
                mock_slug_result.scalar_one_or_none.return_value = None

                mock_async_session.execute.side_effect = [mock_tag_result, mock_slug_result]

                result = await update_tag(mock_info, input_data)

                assert result is not None
                mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_tag_not_found(self, mock_info, auth_context):
        """Test updating non-existent tag."""
        input_data = UpdateTagInput(id=uuid.uuid4(), name="Updated")

        with patch("boards.graphql.resolvers.tag.get_auth_context_from_info") as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch("boards.graphql.resolvers.tag.get_async_session") as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = None
                mock_async_session.execute.return_value = mock_result

                with pytest.raises(RuntimeError, match="Tag not found"):
                    await update_tag(mock_info, input_data)


class TestDeleteTag:
    """Tests for delete_tag mutation."""

    @pytest.mark.asyncio
    async def test_delete_tag_success(self, mock_info, auth_context, sample_tag):
        """Test successful tag deletion."""
        sample_tag.tenant_id = auth_context.tenant_id

        with patch("boards.graphql.resolvers.tag.get_auth_context_from_info") as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch("boards.graphql.resolvers.tag.get_async_session") as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = sample_tag
                mock_async_session.execute.return_value = mock_result

                result = await delete_tag(mock_info, sample_tag.id)

                assert result is True
                mock_async_session.delete.assert_called_once_with(sample_tag)
                mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_tag_not_found(self, mock_info, auth_context):
        """Test deleting non-existent tag."""
        with patch("boards.graphql.resolvers.tag.get_auth_context_from_info") as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch("boards.graphql.resolvers.tag.get_async_session") as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = None
                mock_async_session.execute.return_value = mock_result

                with pytest.raises(RuntimeError, match="Tag not found"):
                    await delete_tag(mock_info, uuid.uuid4())


class TestResolveTags:
    """Tests for resolve_tags query."""

    @pytest.mark.asyncio
    async def test_resolve_tags_success(self, mock_info, auth_context, sample_tag):
        """Test successful tag listing."""
        with patch("boards.graphql.resolvers.tag.get_auth_context_from_info") as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch("boards.graphql.resolvers.tag.get_async_session") as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalars.return_value.all.return_value = [sample_tag]
                mock_async_session.execute.return_value = mock_result

                result = await resolve_tags(mock_info)

                assert len(result) == 1
                assert result[0].name == sample_tag.name

    @pytest.mark.asyncio
    async def test_resolve_tags_unauthenticated(self, mock_info):
        """Test that unauthenticated users get empty list."""
        with patch("boards.graphql.resolvers.tag.get_auth_context_from_info") as mock_get_auth:
            mock_get_auth.return_value = None

            result = await resolve_tags(mock_info)

            assert result == []


class TestResolveTagById:
    """Tests for resolve_tag_by_id query."""

    @pytest.mark.asyncio
    async def test_resolve_tag_by_id_success(self, mock_info, auth_context, sample_tag):
        """Test successful tag lookup by ID."""
        sample_tag.tenant_id = auth_context.tenant_id

        with patch("boards.graphql.resolvers.tag.get_auth_context_from_info") as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch("boards.graphql.resolvers.tag.get_async_session") as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = sample_tag
                mock_async_session.execute.return_value = mock_result

                result = await resolve_tag_by_id(mock_info, sample_tag.id)

                assert result is not None
                assert result.id == sample_tag.id

    @pytest.mark.asyncio
    async def test_resolve_tag_by_id_not_found(self, mock_info, auth_context):
        """Test tag lookup by ID when not found."""
        with patch("boards.graphql.resolvers.tag.get_auth_context_from_info") as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch("boards.graphql.resolvers.tag.get_async_session") as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = None
                mock_async_session.execute.return_value = mock_result

                result = await resolve_tag_by_id(mock_info, uuid.uuid4())

                assert result is None


class TestResolveTagBySlug:
    """Tests for resolve_tag_by_slug query."""

    @pytest.mark.asyncio
    async def test_resolve_tag_by_slug_success(self, mock_info, auth_context, sample_tag):
        """Test successful tag lookup by slug."""
        sample_tag.tenant_id = auth_context.tenant_id

        with patch("boards.graphql.resolvers.tag.get_auth_context_from_info") as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch("boards.graphql.resolvers.tag.get_async_session") as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = sample_tag
                mock_async_session.execute.return_value = mock_result

                result = await resolve_tag_by_slug(mock_info, "test-tag")

                assert result is not None
                assert result.slug == sample_tag.slug


class TestAddTagToGeneration:
    """Tests for add_tag_to_generation mutation."""

    @pytest.mark.asyncio
    async def test_add_tag_to_generation_as_owner(
        self, mock_info, auth_context, sample_tag, sample_board, sample_generation
    ):
        """Test adding a tag to a generation as board owner."""
        sample_board.owner_id = auth_context.user_id
        sample_tag.tenant_id = auth_context.tenant_id
        sample_generation.board_id = sample_board.id

        with patch("boards.graphql.resolvers.tag.get_auth_context_from_info") as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch("boards.graphql.resolvers.tag.get_async_session") as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                # Mock generation query
                mock_gen_result = MagicMock()
                mock_gen_result.scalar_one_or_none.return_value = sample_generation

                # Mock board query
                mock_board_result = MagicMock()
                mock_board_result.scalar_one_or_none.return_value = sample_board

                # Mock tag query
                mock_tag_result = MagicMock()
                mock_tag_result.scalar_one_or_none.return_value = sample_tag

                # Mock existing association check (not found)
                mock_existing_result = MagicMock()
                mock_existing_result.scalar_one_or_none.return_value = None

                mock_async_session.execute.side_effect = [
                    mock_gen_result,
                    mock_board_result,
                    mock_tag_result,
                    mock_existing_result,
                ]

                result = await add_tag_to_generation(mock_info, sample_generation.id, sample_tag.id)

                assert result is not None
                mock_async_session.add.assert_called_once()
                mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_tag_to_generation_as_editor(
        self, mock_info, auth_context, sample_tag, sample_board, sample_generation
    ):
        """Test adding a tag to a generation as board editor."""
        sample_tag.tenant_id = auth_context.tenant_id
        sample_generation.board_id = sample_board.id

        # Add user as editor
        editor_member = MagicMock(spec=BoardMembers)
        editor_member.user_id = auth_context.user_id
        editor_member.role = "editor"
        sample_board.board_members = [editor_member]

        with patch("boards.graphql.resolvers.tag.get_auth_context_from_info") as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch("boards.graphql.resolvers.tag.get_async_session") as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_gen_result = MagicMock()
                mock_gen_result.scalar_one_or_none.return_value = sample_generation

                mock_board_result = MagicMock()
                mock_board_result.scalar_one_or_none.return_value = sample_board

                mock_tag_result = MagicMock()
                mock_tag_result.scalar_one_or_none.return_value = sample_tag

                mock_existing_result = MagicMock()
                mock_existing_result.scalar_one_or_none.return_value = None

                mock_async_session.execute.side_effect = [
                    mock_gen_result,
                    mock_board_result,
                    mock_tag_result,
                    mock_existing_result,
                ]

                result = await add_tag_to_generation(mock_info, sample_generation.id, sample_tag.id)

                assert result is not None

    @pytest.mark.asyncio
    async def test_add_tag_to_generation_permission_denied(
        self, mock_info, auth_context, sample_tag, sample_board, sample_generation
    ):
        """Test that non-editor cannot add tags."""
        sample_tag.tenant_id = auth_context.tenant_id
        sample_generation.board_id = sample_board.id

        # User is just a viewer
        viewer_member = MagicMock(spec=BoardMembers)
        viewer_member.user_id = auth_context.user_id
        viewer_member.role = "viewer"
        sample_board.board_members = [viewer_member]

        with patch("boards.graphql.resolvers.tag.get_auth_context_from_info") as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch("boards.graphql.resolvers.tag.get_async_session") as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_gen_result = MagicMock()
                mock_gen_result.scalar_one_or_none.return_value = sample_generation

                mock_board_result = MagicMock()
                mock_board_result.scalar_one_or_none.return_value = sample_board

                mock_async_session.execute.side_effect = [
                    mock_gen_result,
                    mock_board_result,
                ]

                with pytest.raises(RuntimeError, match="Permission denied"):
                    await add_tag_to_generation(mock_info, sample_generation.id, sample_tag.id)

    @pytest.mark.asyncio
    async def test_add_tag_already_exists(
        self, mock_info, auth_context, sample_tag, sample_board, sample_generation
    ):
        """Test that adding existing tag returns the tag without error."""
        sample_board.owner_id = auth_context.user_id
        sample_tag.tenant_id = auth_context.tenant_id
        sample_generation.board_id = sample_board.id

        existing_assoc = MagicMock(spec=GenerationTags)

        with patch("boards.graphql.resolvers.tag.get_auth_context_from_info") as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch("boards.graphql.resolvers.tag.get_async_session") as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_gen_result = MagicMock()
                mock_gen_result.scalar_one_or_none.return_value = sample_generation

                mock_board_result = MagicMock()
                mock_board_result.scalar_one_or_none.return_value = sample_board

                mock_tag_result = MagicMock()
                mock_tag_result.scalar_one_or_none.return_value = sample_tag

                # Existing association found
                mock_existing_result = MagicMock()
                mock_existing_result.scalar_one_or_none.return_value = existing_assoc

                mock_async_session.execute.side_effect = [
                    mock_gen_result,
                    mock_board_result,
                    mock_tag_result,
                    mock_existing_result,
                ]

                result = await add_tag_to_generation(mock_info, sample_generation.id, sample_tag.id)

                # Should return tag without adding again
                assert result is not None
                mock_async_session.add.assert_not_called()


class TestRemoveTagFromGeneration:
    """Tests for remove_tag_from_generation mutation."""

    @pytest.mark.asyncio
    async def test_remove_tag_from_generation_success(
        self, mock_info, auth_context, sample_board, sample_generation
    ):
        """Test successful tag removal from generation."""
        sample_board.owner_id = auth_context.user_id
        sample_generation.board_id = sample_board.id

        assoc = MagicMock(spec=GenerationTags)

        with patch("boards.graphql.resolvers.tag.get_auth_context_from_info") as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch("boards.graphql.resolvers.tag.get_async_session") as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_gen_result = MagicMock()
                mock_gen_result.scalar_one_or_none.return_value = sample_generation

                mock_board_result = MagicMock()
                mock_board_result.scalar_one_or_none.return_value = sample_board

                mock_assoc_result = MagicMock()
                mock_assoc_result.scalar_one_or_none.return_value = assoc

                mock_async_session.execute.side_effect = [
                    mock_gen_result,
                    mock_board_result,
                    mock_assoc_result,
                ]

                result = await remove_tag_from_generation(
                    mock_info, sample_generation.id, uuid.uuid4()
                )

                assert result is True
                mock_async_session.delete.assert_called_once_with(assoc)
                mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_tag_not_associated(
        self, mock_info, auth_context, sample_board, sample_generation
    ):
        """Test removing tag that isn't associated."""
        sample_board.owner_id = auth_context.user_id
        sample_generation.board_id = sample_board.id

        with patch("boards.graphql.resolvers.tag.get_auth_context_from_info") as mock_get_auth:
            mock_get_auth.return_value = auth_context

            with patch("boards.graphql.resolvers.tag.get_async_session") as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_gen_result = MagicMock()
                mock_gen_result.scalar_one_or_none.return_value = sample_generation

                mock_board_result = MagicMock()
                mock_board_result.scalar_one_or_none.return_value = sample_board

                mock_assoc_result = MagicMock()
                mock_assoc_result.scalar_one_or_none.return_value = None

                mock_async_session.execute.side_effect = [
                    mock_gen_result,
                    mock_board_result,
                    mock_assoc_result,
                ]

                with pytest.raises(RuntimeError, match="not associated"):
                    await remove_tag_from_generation(mock_info, sample_generation.id, uuid.uuid4())


class TestResolveGenerationTags:
    """Tests for resolve_generation_tags field resolver."""

    @pytest.mark.asyncio
    async def test_resolve_generation_tags_success(self, mock_info, sample_tag):
        """Test successful generation tags resolution."""
        generation_id = uuid.uuid4()

        with patch("boards.graphql.resolvers.tag.get_async_session") as mock_session:
            mock_async_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_async_session

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [sample_tag]
            mock_async_session.execute.return_value = mock_result

            result = await resolve_generation_tags(generation_id, mock_info)

            assert len(result) == 1
            assert result[0].name == sample_tag.name

    @pytest.mark.asyncio
    async def test_resolve_generation_tags_empty(self, mock_info):
        """Test generation with no tags."""
        generation_id = uuid.uuid4()

        with patch("boards.graphql.resolvers.tag.get_async_session") as mock_session:
            mock_async_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_async_session

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_async_session.execute.return_value = mock_result

            result = await resolve_generation_tags(generation_id, mock_info)

            assert result == []
