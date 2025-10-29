"""
Tests for artifact resolution utilities.
"""

import os
import tempfile
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from boards.generators.artifacts import (
    AudioArtifact,
    ImageArtifact,
    TextArtifact,
    VideoArtifact,
)
from boards.generators.resolution import (
    download_artifact_to_temp,
    resolve_artifact,
    store_image_result,
)


class TestResolveArtifact:
    """Tests for resolve_artifact function."""

    @pytest.mark.asyncio
    async def test_resolve_local_file(self):
        """Test resolving artifact that points to existing local file."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            temp_file.write(b"fake audio content")
            temp_path = temp_file.name

        try:
            artifact = AudioArtifact(  # type: ignore
                generation_id="test", storage_url=temp_path, format="mp3"
            )

            result = await resolve_artifact(artifact)

            # Should return the same path since file exists locally
            assert result == temp_path
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_resolve_remote_file(self):
        """Test resolving artifact that needs to be downloaded."""
        artifact = AudioArtifact(  # type: ignore
            generation_id="test",
            storage_url="https://example.com/audio.mp3",
            format="mp3",
        )

        # Mock the download function
        with patch("boards.generators.resolution.download_artifact_to_temp") as mock_download:
            mock_download.return_value = "/tmp/downloaded_audio.mp3"

            result = await resolve_artifact(artifact)

            assert result == "/tmp/downloaded_audio.mp3"
            mock_download.assert_called_once_with(artifact)

    @pytest.mark.asyncio
    async def test_resolve_text_artifact_fails(self):
        """Test that resolving TextArtifact raises an error."""
        artifact = TextArtifact(
            generation_id="test",
            content="Some text content",
            storage_url="",
            format="plain",
        )

        with pytest.raises(ValueError, match="TextArtifact cannot be resolved to a file path"):
            await resolve_artifact(artifact)  # type: ignore


class TestDownloadArtifactToTemp:
    """Tests for download_artifact_to_temp function."""

    @pytest.mark.asyncio
    async def test_successful_download(self):
        """Test successful artifact download."""
        artifact = ImageArtifact(
            generation_id="test",
            storage_url="https://example.com/image.png",
            width=512,
            height=512,
            format="png",
        )

        fake_content = b"fake image content"

        # Mock httpx client
        from unittest.mock import MagicMock

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = AsyncMock()
            mock_response.content = fake_content
            # raise_for_status is not async in httpx
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response

            result_path = await download_artifact_to_temp(artifact)

            # Check that file was created and contains expected content
            assert os.path.exists(result_path)
            assert result_path.endswith(".png")

            with open(result_path, "rb") as f:
                content = f.read()
                assert content == fake_content

            # Verify the HTTP call was made correctly
            mock_client.get.assert_called_once_with("https://example.com/image.png")
            mock_response.raise_for_status.assert_called_once()

            # Clean up
            os.unlink(result_path)

    @pytest.mark.asyncio
    async def test_download_http_error(self):
        """Test download failure with HTTP error."""
        artifact = ImageArtifact(
            generation_id="test",
            storage_url="https://example.com/nonexistent.png",
            width=512,
            height=512,
            format="png",
        )

        # Mock httpx client to raise an error on get
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Make the get call itself raise the error
            mock_client.get.side_effect = httpx.HTTPStatusError(
                "404 Not Found", request=AsyncMock(), response=AsyncMock()
            )

            with pytest.raises(httpx.HTTPStatusError):
                await download_artifact_to_temp(artifact)


class TestFileExtensionDetection:
    """Tests for file extension detection."""

    @pytest.mark.asyncio
    async def test_extension_with_dot(self):
        """Test extension detection when format includes dot."""
        artifact = AudioArtifact(  # type: ignore
            generation_id="test", storage_url="https://example.com/audio", format=".mp3"
        )

        with patch("boards.generators.resolution.download_artifact_to_temp") as mock_download:
            mock_download.return_value = "/tmp/test.mp3"

            await resolve_artifact(artifact)

            # Check that the artifact was passed correctly
            mock_download.assert_called_once_with(artifact)

    @pytest.mark.asyncio
    async def test_extension_without_dot(self):
        """Test extension detection when format doesn't include dot."""
        artifact = VideoArtifact(  # type: ignore
            generation_id="test",
            storage_url="https://example.com/video",
            width=640,
            height=480,
            format="mp4",
        )

        with patch("boards.generators.resolution.download_artifact_to_temp") as mock_download:
            mock_download.return_value = "/tmp/test.mp4"

            await resolve_artifact(artifact)

            mock_download.assert_called_once_with(artifact)


class TestStoreResults:
    """Tests for store result functions."""

    @pytest.mark.asyncio
    async def test_store_image_result(self, tmp_path):
        """Test storing image result."""
        from unittest.mock import AsyncMock, patch

        from boards.storage.factory import create_development_storage
        from boards.storage.implementations.local import LocalStorageProvider

        # Create mock storage manager
        storage_manager = create_development_storage()
        local_provider = storage_manager.providers["local"]
        assert isinstance(local_provider, LocalStorageProvider)
        local_provider.base_path = tmp_path / "storage"
        local_provider.base_path.mkdir(parents=True, exist_ok=True)

        # Mock HTTP download
        from unittest.mock import MagicMock

        mock_response = AsyncMock()
        mock_response.content = b"fake image data"
        # raise_for_status is not async in httpx
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await store_image_result(
                storage_manager=storage_manager,
                generation_id="gen_123",
                tenant_id="tenant_123",
                board_id="board_123",
                storage_url="https://example.com/generated.png",
                format="png",
                width=1024,
                height=1024,
            )

        assert isinstance(result, ImageArtifact)
        assert result.generation_id == "gen_123"
        assert result.format == "png"
        assert result.width == 1024
        assert result.height == 1024
        # Storage URL should be different from input URL
        assert "storage" in result.storage_url or result.storage_url.startswith("file://")

    @pytest.mark.skip(reason="Replaced by test_storage_integration.py tests")
    @pytest.mark.asyncio
    async def test_store_video_result(self):
        """Test storing video result."""
        pass

    @pytest.mark.skip(reason="Replaced by test_storage_integration.py tests")
    @pytest.mark.asyncio
    async def test_store_audio_result(self):
        """Test storing audio result."""
        pass

    @pytest.mark.skip(reason="Replaced by test_storage_integration.py tests")
    @pytest.mark.asyncio
    async def test_store_video_result_optional_params(self):
        """Test storing video result with optional parameters as None."""
        pass
