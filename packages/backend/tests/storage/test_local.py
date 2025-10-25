"""Tests for local storage provider."""

import json
from collections.abc import Generator
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import aiofiles
import pytest

from boards.storage.base import SecurityException, StorageException
from boards.storage.implementations.local import LocalStorageProvider


class TestLocalStorageProvider:
    """Test local filesystem storage provider."""

    @pytest.fixture
    def temp_dir(self) -> Generator[Path, None, None]:
        with TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def provider(self, temp_dir: Path) -> LocalStorageProvider:
        return LocalStorageProvider(
            base_path=temp_dir, public_url_base="http://localhost:8088/storage"
        )

    def test_init(self, temp_dir: Path) -> None:
        provider = LocalStorageProvider(temp_dir)

        assert provider.base_path == temp_dir.resolve()
        assert provider.public_url_base is None
        assert temp_dir.exists()

    def test_init_with_public_url(self, temp_dir: Path) -> None:
        provider = LocalStorageProvider(temp_dir, public_url_base="http://example.com/files")

        assert provider.public_url_base == "http://example.com/files"

    def test_get_safe_file_path_valid(self, provider: LocalStorageProvider, temp_dir: Path) -> None:
        path = provider._get_safe_file_path("folder/file.txt")
        expected = temp_dir / "folder" / "file.txt"
        # Compare resolved paths to handle symlinks (e.g. /var vs /private/var on macOS)
        assert path.resolve() == expected.resolve()

    def test_get_safe_file_path_traversal_attack(self, provider: LocalStorageProvider) -> None:
        # Path traversal attempts should fail
        with pytest.raises(SecurityException):
            provider._get_safe_file_path("../../../etc/passwd")

        with pytest.raises(SecurityException):
            provider._get_safe_file_path("folder/../../../etc/passwd")

    def test_get_public_url_with_base(self, provider: LocalStorageProvider) -> None:
        url = provider._get_public_url("folder/file.txt")
        assert url == "http://localhost:8088/storage/folder/file.txt"

    def test_get_public_url_with_special_chars(self, provider: LocalStorageProvider) -> None:
        url = provider._get_public_url("folder/file with spaces.txt")
        assert url == "http://localhost:8088/storage/folder/file%20with%20spaces.txt"

    def test_get_public_url_without_base(self, temp_dir: Path) -> None:
        provider = LocalStorageProvider(temp_dir)
        url = provider._get_public_url("file.txt")
        assert url.startswith("file://")
        assert url.endswith("file.txt")

    @pytest.mark.asyncio
    async def test_upload_bytes(self, provider: LocalStorageProvider, temp_dir: Path):
        content = b"test file content"
        key = "test/file.txt"

        url = await provider.upload(key, content, "text/plain")

        # Check file was written
        file_path = temp_dir / key
        assert file_path.exists()

        # Check content
        async with aiofiles.open(file_path, "rb") as f:
            stored_content = await f.read()
        assert stored_content == content

        # Check return URL
        assert url == "http://localhost:8088/storage/test/file.txt"

    @pytest.mark.asyncio
    async def test_upload_with_metadata(self, provider: LocalStorageProvider, temp_dir: Path):
        content = b"test content"
        key = "test/file.txt"
        metadata = {"user": "test_user", "timestamp": "2024-01-01"}

        await provider.upload(key, content, "text/plain", metadata)

        # Check metadata file was created
        metadata_path = temp_dir / f"{key}.meta"
        assert metadata_path.exists()

        # Check metadata content
        async with aiofiles.open(metadata_path) as f:
            stored_metadata = json.loads(await f.read())
        assert stored_metadata == metadata

    @pytest.mark.asyncio
    async def test_upload_async_iterator(self, provider: LocalStorageProvider, temp_dir: Path):
        # Create async iterator of chunks
        async def content_chunks():
            yield b"chunk1"
            yield b"chunk2"
            yield b"chunk3"

        key = "test/streamed.txt"

        url = await provider.upload(key, content_chunks(), "text/plain")

        # Check file content
        file_path = temp_dir / key
        async with aiofiles.open(file_path, "rb") as f:
            content = await f.read()

        assert content == b"chunk1chunk2chunk3"
        assert url == "http://localhost:8088/storage/test/streamed.txt"

    @pytest.mark.asyncio
    async def test_upload_creates_directories(self, provider: LocalStorageProvider, temp_dir: Path):
        key = "deep/nested/path/file.txt"
        content = b"test"

        await provider.upload(key, content, "text/plain")

        # Check directory structure was created
        file_path = temp_dir / key
        assert file_path.exists()
        assert file_path.parent.exists()

    @pytest.mark.asyncio
    async def test_download_success(self, provider: LocalStorageProvider, temp_dir: Path):
        # Create test file
        key = "test/file.txt"
        content = b"test file content"
        file_path = temp_dir / key
        file_path.parent.mkdir(parents=True)

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        # Download and verify
        downloaded = await provider.download(key)
        assert downloaded == content

    @pytest.mark.asyncio
    async def test_download_not_found(self, provider: LocalStorageProvider, temp_dir: Path):
        with pytest.raises(StorageException, match="File not found"):
            await provider.download("nonexistent/file.txt")

    @pytest.mark.asyncio
    async def test_get_presigned_upload_url(self, provider: LocalStorageProvider):
        result = await provider.get_presigned_upload_url(
            "test/file.txt", "text/plain", timedelta(hours=1)
        )

        assert result["url"] == "/api/storage/upload/test/file.txt"
        assert result["fields"]["content-type"] == "text/plain"
        assert result["method"] == "PUT"
        assert result["expires_at"] is None

    @pytest.mark.asyncio
    async def test_get_presigned_download_url(self, provider: LocalStorageProvider):
        url = await provider.get_presigned_download_url("test/file.txt")
        assert url == "http://localhost:8088/storage/test/file.txt"

    @pytest.mark.asyncio
    async def test_delete_success(self, provider: LocalStorageProvider, temp_dir: Path):
        # Create test file
        key = "test/file.txt"
        file_path = temp_dir / key
        file_path.parent.mkdir(parents=True)

        async with aiofiles.open(file_path, "w") as f:
            await f.write("test content")

        # Delete and verify
        result = await provider.delete(key)
        assert result is True
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_delete_with_metadata(self, provider: LocalStorageProvider, temp_dir: Path):
        # Create test file and metadata
        key = "test/file.txt"
        file_path = temp_dir / key
        metadata_path = temp_dir / f"{key}.meta"

        file_path.parent.mkdir(parents=True)

        async with aiofiles.open(file_path, "w") as f:
            await f.write("test")
        async with aiofiles.open(metadata_path, "w") as f:
            await f.write('{"test": true}')

        # Delete and verify both files removed
        result = await provider.delete(key)
        assert result is True
        assert not file_path.exists()
        assert not metadata_path.exists()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, provider: LocalStorageProvider):
        result = await provider.delete("nonexistent/file.txt")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_true(self, provider: LocalStorageProvider, temp_dir: Path):
        # Create test file
        key = "test/file.txt"
        file_path = temp_dir / key
        file_path.parent.mkdir(parents=True)
        file_path.touch()

        assert await provider.exists(key) is True

    @pytest.mark.asyncio
    async def test_exists_false(self, provider: LocalStorageProvider):
        assert await provider.exists("nonexistent/file.txt") is False

    @pytest.mark.asyncio
    async def test_exists_path_traversal(self, provider: LocalStorageProvider):
        # Security violation should return False, not raise
        assert await provider.exists("../../../etc/passwd") is False

    @pytest.mark.asyncio
    async def test_get_metadata_success(self, provider: LocalStorageProvider, temp_dir: Path):
        # Create test file with metadata
        key = "test/file.txt"
        file_path = temp_dir / key
        metadata_path = temp_dir / f"{key}.meta"

        file_path.parent.mkdir(parents=True)

        # Write file
        async with aiofiles.open(file_path, "w") as f:
            await f.write("test content")

        # Write metadata
        stored_metadata = {"user": "testuser", "version": 1}
        async with aiofiles.open(metadata_path, "w") as f:
            await f.write(json.dumps(stored_metadata))

        # Get metadata
        metadata = await provider.get_metadata(key)

        # Check filesystem metadata
        assert "size" in metadata
        assert "modified_time" in metadata
        assert "created_time" in metadata

        # Check stored metadata
        assert metadata["user"] == "testuser"
        assert metadata["version"] == 1

    @pytest.mark.asyncio
    async def test_get_metadata_no_stored_metadata(
        self, provider: LocalStorageProvider, temp_dir: Path
    ):
        # Create file without metadata
        key = "test/file.txt"
        file_path = temp_dir / key
        file_path.parent.mkdir(parents=True)
        file_path.touch()

        metadata = await provider.get_metadata(key)

        # Should still have filesystem metadata
        assert "size" in metadata
        assert "modified_time" in metadata
        assert "created_time" in metadata

    @pytest.mark.asyncio
    async def test_get_metadata_not_found(self, provider: LocalStorageProvider):
        with pytest.raises(StorageException, match="File not found"):
            await provider.get_metadata("nonexistent/file.txt")
