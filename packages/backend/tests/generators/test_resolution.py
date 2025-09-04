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
    store_audio_result,
    store_image_result,
    store_video_result,
)


class TestResolveArtifact:
    """Tests for resolve_artifact function."""

    @pytest.mark.asyncio
    async def test_resolve_local_file(self):
        """Test resolving artifact that points to existing local file."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_file.write(b"fake audio content")
            temp_path = temp_file.name

        try:
            artifact = AudioArtifact(  # type: ignore
                generation_id="test",
                storage_url=temp_path,
                format="mp3"
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
            format="mp3"
        )

        # Mock the download function
        with patch('boards.generators.resolution.download_artifact_to_temp') as mock_download:
            mock_download.return_value = "/tmp/downloaded_audio.mp3"

            result = await resolve_artifact(artifact)

            assert result == "/tmp/downloaded_audio.mp3"
            mock_download.assert_called_once_with(artifact)

    @pytest.mark.asyncio
    async def test_resolve_text_artifact_fails(self):
        """Test that resolving TextArtifact raises an error."""
        artifact = TextArtifact(
            generation_id="test",
            content="Some text content"
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
            format="png"
        )

        fake_content = b"fake image content"

        # Mock httpx client
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = AsyncMock()
            mock_response.content = fake_content
            mock_client.get.return_value = mock_response

            result_path = await download_artifact_to_temp(artifact)

            # Check that file was created and contains expected content
            assert os.path.exists(result_path)
            assert result_path.endswith('.png')

            with open(result_path, 'rb') as f:
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
            format="png"
        )

        # Mock httpx client to raise an error on get
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Make the get call itself raise the error
            mock_client.get.side_effect = httpx.HTTPStatusError(
                "404 Not Found",
                request=AsyncMock(),
                response=AsyncMock()
            )

            with pytest.raises(httpx.HTTPStatusError):
                await download_artifact_to_temp(artifact)


class TestFileExtensionDetection:
    """Tests for file extension detection."""

    @pytest.mark.asyncio
    async def test_extension_with_dot(self):
        """Test extension detection when format includes dot."""
        artifact = AudioArtifact(  # type: ignore
            generation_id="test",
            storage_url="https://example.com/audio",
            format=".mp3"
        )

        with patch('boards.generators.resolution.download_artifact_to_temp') as mock_download:
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
            format="mp4"
        )

        with patch('boards.generators.resolution.download_artifact_to_temp') as mock_download:
            mock_download.return_value = "/tmp/test.mp4"

            await resolve_artifact(artifact)

            mock_download.assert_called_once_with(artifact)


class TestStoreResults:
    """Tests for store result functions."""

    @pytest.mark.asyncio
    async def test_store_image_result(self):
        """Test storing image result."""
        result = await store_image_result(
            storage_url="https://example.com/generated.png",
            format="png",
            generation_id="gen_123",
            width=1024,
            height=1024
        )

        assert isinstance(result, ImageArtifact)
        assert result.generation_id == "gen_123"
        assert result.storage_url == "https://example.com/generated.png"
        assert result.format == "png"
        assert result.width == 1024
        assert result.height == 1024

    @pytest.mark.asyncio
    async def test_store_video_result(self):
        """Test storing video result."""
        result = await store_video_result(
            storage_url="https://example.com/generated.mp4",
            format="mp4",
            generation_id="gen_456",
            width=1920,
            height=1080,
            duration=60.0,
            fps=30.0
        )

        assert isinstance(result, VideoArtifact)
        assert result.generation_id == "gen_456"
        assert result.storage_url == "https://example.com/generated.mp4"
        assert result.format == "mp4"
        assert result.width == 1920
        assert result.height == 1080
        assert result.duration == 60.0
        assert result.fps == 30.0

    @pytest.mark.asyncio
    async def test_store_audio_result(self):
        """Test storing audio result."""
        result = await store_audio_result(
            storage_url="https://example.com/generated.mp3",
            format="mp3",
            generation_id="gen_789",
            duration=120.0,
            sample_rate=44100,
            channels=2
        )

        assert isinstance(result, AudioArtifact)
        assert result.generation_id == "gen_789"
        assert result.storage_url == "https://example.com/generated.mp3"
        assert result.format == "mp3"
        assert result.duration == 120.0
        assert result.sample_rate == 44100
        assert result.channels == 2

    @pytest.mark.asyncio
    async def test_store_video_result_optional_params(self):
        """Test storing video result with optional parameters as None."""
        result = await store_video_result(
            storage_url="https://example.com/generated.mp4",
            format="mp4",
            generation_id="gen_456",
            width=640,
            height=480
            # duration and fps not provided
        )

        assert result.duration is None
        assert result.fps is None
        assert result.width == 640
        assert result.height == 480
