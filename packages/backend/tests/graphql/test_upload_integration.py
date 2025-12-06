"""Integration tests for artifact upload functionality."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from boards.auth.context import DEFAULT_TENANT_UUID, AuthContext


@pytest.fixture
def auth_context():
    """Create a test auth context."""
    return AuthContext(
        user_id=uuid4(),
        tenant_id=DEFAULT_TENANT_UUID,
        principal={"provider": "none", "subject": "test-user"},
        token="test-token",
    )


@pytest.mark.asyncio
class TestUploadArtifactFromFile:
    """Test file upload via REST endpoint."""

    async def test_upload_image_file_success(self, auth_context):
        """Successfully upload an image file."""
        from boards.dbmodels import Boards
        from boards.graphql.resolvers.upload import upload_artifact_from_file

        # Create test data
        file_content = b"fake-image-data"
        filename = "test.jpg"
        board_id = uuid4()

        # Mock board object
        mock_board = MagicMock(spec=Boards)
        mock_board.id = board_id
        mock_board.tenant_id = auth_context.tenant_id
        mock_board.owner_id = auth_context.user_id
        mock_board.board_members = []

        # Mock storage manager
        with patch("boards.graphql.resolvers.upload.create_storage_manager") as mock_storage:
            mock_manager = AsyncMock()
            mock_manager.store_artifact = AsyncMock(
                return_value=MagicMock(
                    storage_url="http://example.com/test.jpg",
                    storage_key="test-key",
                    storage_provider="local",
                )
            )
            mock_storage.return_value = mock_manager

            # Mock database session
            with patch("boards.graphql.resolvers.upload.get_async_session") as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                # Mock board query
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = mock_board
                mock_async_session.execute.return_value = mock_result

                # Mock generation creation
                mock_async_session.add = MagicMock()
                mock_async_session.flush = AsyncMock()
                mock_async_session.commit = AsyncMock()
                mock_async_session.refresh = AsyncMock()

                # Upload file
                result = await upload_artifact_from_file(
                    auth_context=auth_context,
                    board_id=board_id,
                    artifact_type="image",
                    file_content=file_content,
                    filename=filename,
                    content_type="image/jpeg",
                    user_description="Test upload",
                    parent_generation_id=None,
                )

                # Verify result
                assert result.generator_name == "user-upload-image"
                assert result.artifact_type.value == "image"
                assert result.status.value == "completed"
                assert result.storage_url == "http://example.com/test.jpg"

    async def test_upload_rejects_invalid_mime_type(self, auth_context):
        """Upload should fail with mismatched MIME type."""
        from boards.graphql.resolvers.upload import upload_artifact_from_file

        file_content = b"fake-video-data"
        board_id = uuid4()

        with pytest.raises(RuntimeError) as exc_info:
            await upload_artifact_from_file(
                auth_context=auth_context,
                board_id=board_id,
                artifact_type="image",  # Wrong type
                file_content=file_content,
                filename="test.mp4",
                content_type="video/mp4",  # Video MIME type
                user_description=None,
                parent_generation_id=None,
            )

        assert "invalid file type" in str(exc_info.value).lower()

    async def test_upload_rejects_oversized_file(self, auth_context):
        """Upload should fail with oversized file."""
        from boards.graphql.resolvers.upload import upload_artifact_from_file

        # Create a file larger than max_upload_size (100MB)
        file_content = b"x" * (101 * 1024 * 1024)
        board_id = uuid4()

        with pytest.raises(RuntimeError) as exc_info:
            await upload_artifact_from_file(
                auth_context=auth_context,
                board_id=board_id,
                artifact_type="image",
                file_content=file_content,
                filename="large.jpg",
                content_type="image/jpeg",
                user_description=None,
                parent_generation_id=None,
            )

        assert "file size" in str(exc_info.value).lower()
        assert "exceeds" in str(exc_info.value).lower()

    async def test_upload_sanitizes_filename(self, auth_context):
        """Upload should sanitize malicious filenames."""
        from boards.dbmodels import Boards
        from boards.graphql.resolvers.upload import upload_artifact_from_file

        file_content = b"fake-image-data"
        malicious_filename = "../../../etc/passwd"
        board_id = uuid4()

        # Mock board object
        mock_board = MagicMock(spec=Boards)
        mock_board.id = board_id
        mock_board.tenant_id = auth_context.tenant_id
        mock_board.owner_id = auth_context.user_id
        mock_board.board_members = []

        with patch("boards.graphql.resolvers.upload.create_storage_manager") as mock_storage:
            mock_manager = AsyncMock()
            mock_manager.store_artifact = AsyncMock(
                return_value=MagicMock(
                    storage_url="http://example.com/test.jpg",
                    storage_key="test-key",
                    storage_provider="local",
                )
            )
            mock_storage.return_value = mock_manager

            with patch("boards.graphql.resolvers.upload.get_async_session") as mock_session:
                mock_async_session = AsyncMock()
                mock_session.return_value.__aenter__.return_value = mock_async_session

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = mock_board
                mock_async_session.execute.return_value = mock_result

                mock_async_session.add = MagicMock()
                mock_async_session.flush = AsyncMock()
                mock_async_session.commit = AsyncMock()
                mock_async_session.refresh = AsyncMock()

                result = await upload_artifact_from_file(
                    auth_context=auth_context,
                    board_id=board_id,
                    artifact_type="image",
                    file_content=file_content,
                    filename=malicious_filename,
                    content_type="image/jpeg",
                    user_description=None,
                    parent_generation_id=None,
                )

                # Verify filename was sanitized
                assert result.input_params["original_filename"] == "passwd"
                assert ".." not in result.input_params["original_filename"]


@pytest.mark.asyncio
class TestUploadArtifactFromURL:
    """Test URL upload via GraphQL mutation."""

    async def test_upload_from_url_success(self, auth_context):
        """Successfully upload from a valid URL."""
        from boards.dbmodels import Boards
        from boards.graphql.resolvers.upload import upload_artifact_from_url
        from boards.graphql.types.generation import ArtifactType, UploadArtifactInput

        board_id = uuid4()

        input_data = UploadArtifactInput(
            board_id=board_id,
            artifact_type=ArtifactType.IMAGE,
            file_url="https://example.com/test.jpg",
            original_filename="test.jpg",
            user_description="Test upload",
            parent_generation_id=None,
        )

        # Mock board object
        mock_board = MagicMock(spec=Boards)
        mock_board.id = board_id
        mock_board.tenant_id = auth_context.tenant_id
        mock_board.owner_id = auth_context.user_id
        mock_board.board_members = []

        # Mock the HTTP request and storage
        with patch("boards.graphql.resolvers.upload.aiohttp.ClientSession") as mock_session_cls:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.headers = {
                "Content-Type": "image/jpeg",
                "Content-Length": "1024",
            }
            mock_resp.read = AsyncMock(return_value=b"fake-image-data")

            # Set up mock session context manager chain
            mock_get_ctx = AsyncMock()
            mock_get_ctx.__aenter__.return_value = mock_resp

            mock_session = MagicMock()
            mock_session.get.return_value = mock_get_ctx
            mock_session_cls.return_value.__aenter__.return_value = mock_session

            with patch("boards.graphql.resolvers.upload.create_storage_manager") as mock_storage:
                mock_manager = AsyncMock()
                mock_manager.store_artifact = AsyncMock(
                    return_value=MagicMock(
                        storage_url="http://example.com/test.jpg",
                        storage_key="test-key",
                        storage_provider="local",
                    )
                )
                mock_storage.return_value = mock_manager

                with patch("boards.graphql.resolvers.upload.get_async_session") as mock_db_session:
                    mock_async_session = AsyncMock()
                    mock_db_session.return_value.__aenter__.return_value = mock_async_session

                    mock_result = MagicMock()
                    mock_result.scalar_one_or_none.return_value = mock_board
                    mock_async_session.execute.return_value = mock_result

                    mock_async_session.add = MagicMock()
                    mock_async_session.flush = AsyncMock()
                    mock_async_session.commit = AsyncMock()
                    mock_async_session.refresh = AsyncMock()

                    # Create mock info with auth context
                    mock_info = MagicMock()
                    mock_info.context = {"auth_context": auth_context}

                    with patch(
                        "boards.graphql.resolvers.upload.get_auth_context_from_info",
                        return_value=auth_context,
                    ):
                        result = await upload_artifact_from_url(mock_info, input_data)

                        assert result.generator_name == "user-upload-image"
                        assert result.status.value == "completed"

    async def test_upload_blocks_localhost_url(self, auth_context):
        """Upload should block localhost URLs (SSRF prevention)."""
        from boards.graphql.resolvers.upload import upload_artifact_from_url
        from boards.graphql.types.generation import ArtifactType, UploadArtifactInput

        board_id = uuid4()

        input_data = UploadArtifactInput(
            board_id=board_id,
            artifact_type=ArtifactType.IMAGE,
            file_url="http://localhost/test.jpg",
            original_filename=None,
            user_description=None,
            parent_generation_id=None,
        )

        mock_info = MagicMock()
        mock_info.context = {"auth_context": auth_context}

        with patch(
            "boards.graphql.resolvers.upload.get_auth_context_from_info",
            return_value=auth_context,
        ):
            with pytest.raises(RuntimeError) as exc_info:
                await upload_artifact_from_url(mock_info, input_data)

            assert "url not allowed" in str(exc_info.value).lower()

    async def test_upload_blocks_private_ip_url(self, auth_context):
        """Upload should block private IP URLs (SSRF prevention)."""
        from boards.graphql.resolvers.upload import upload_artifact_from_url
        from boards.graphql.types.generation import ArtifactType, UploadArtifactInput

        board_id = uuid4()

        input_data = UploadArtifactInput(
            board_id=board_id,
            artifact_type=ArtifactType.IMAGE,
            file_url="http://192.168.1.1/test.jpg",
            original_filename=None,
            user_description=None,
            parent_generation_id=None,
        )

        mock_info = MagicMock()
        mock_info.context = {"auth_context": auth_context}

        with patch(
            "boards.graphql.resolvers.upload.get_auth_context_from_info",
            return_value=auth_context,
        ):
            with pytest.raises(RuntimeError) as exc_info:
                await upload_artifact_from_url(mock_info, input_data)

            assert "url not allowed" in str(exc_info.value).lower()

    async def test_upload_checks_content_length(self, auth_context):
        """Upload should reject oversized files before downloading."""
        from boards.graphql.resolvers.upload import upload_artifact_from_url
        from boards.graphql.types.generation import ArtifactType, UploadArtifactInput

        board_id = uuid4()

        input_data = UploadArtifactInput(
            board_id=board_id,
            artifact_type=ArtifactType.IMAGE,
            file_url="https://example.com/large.jpg",
            original_filename=None,
            user_description=None,
            parent_generation_id=None,
        )

        with patch("boards.graphql.resolvers.upload.aiohttp.ClientSession") as mock_session_cls:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.headers = {
                "Content-Type": "image/jpeg",
                "Content-Length": str(101 * 1024 * 1024),  # 101 MB
            }

            # Set up mock session context manager chain
            mock_get_ctx = AsyncMock()
            mock_get_ctx.__aenter__.return_value = mock_resp

            mock_session = MagicMock()
            mock_session.get.return_value = mock_get_ctx
            mock_session_cls.return_value.__aenter__.return_value = mock_session

            mock_info = MagicMock()
            mock_info.context = {"auth_context": auth_context}

            with patch(
                "boards.graphql.resolvers.upload.get_auth_context_from_info",
                return_value=auth_context,
            ):
                with pytest.raises(RuntimeError) as exc_info:
                    await upload_artifact_from_url(mock_info, input_data)

                assert "file size" in str(exc_info.value).lower()
                assert "exceeds" in str(exc_info.value).lower()
