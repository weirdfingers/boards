"""Local filesystem storage provider for development and self-hosted deployments."""

import json
from collections.abc import AsyncIterable
from datetime import timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

import aiofiles

from ...logging import get_logger
from ..base import SecurityException, StorageException, StorageProvider

logger = get_logger(__name__)


class LocalStorageProvider(StorageProvider):
    """Local filesystem storage for development and self-hosted with security."""

    def __init__(self, base_path: Path, public_url_base: str | None = None):
        self.base_path = Path(base_path).resolve()  # Resolve to absolute path
        self.public_url_base = public_url_base
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_safe_file_path(self, key: str) -> Path:
        """Get file path with security validation."""
        # Ensure the resolved path is within base_path
        file_path = (self.base_path / key).resolve()

        # Check that resolved path is within base directory
        try:
            file_path.relative_to(self.base_path)
        except ValueError as e:
            raise SecurityException(f"Path traversal detected: {key}") from e

        return file_path

    async def upload(
        self,
        key: str,
        content: bytes | bytearray | memoryview | AsyncIterable[bytes],
        content_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        logger.info("Uploading file", key=key, content_type=content_type, metadata=metadata)
        try:
            file_path = self._get_safe_file_path(key)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Handle both bytes-like and async iterable content
            if isinstance(content, bytes | bytearray | memoryview):
                # aiofiles accepts bytes-like objects directly
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(content)
            else:  # isinstance(content, AsyncIterable):
                async with aiofiles.open(file_path, "wb") as f:
                    async for chunk in content:
                        # Just write the chunk directly - aiofiles accepts bytes-like objects
                        # It will raise an error if chunk is not bytes-like
                        await f.write(chunk)

            # Store metadata atomically
            if metadata:
                try:
                    metadata_path = file_path.with_suffix(file_path.suffix + ".meta")
                    metadata_json = json.dumps(metadata, indent=2)

                    async with aiofiles.open(metadata_path, "w") as f:
                        await f.write(metadata_json)
                except Exception as e:
                    logger.warning(f"Failed to write metadata for {key}: {e}")
                    # Continue - metadata failure shouldn't fail the upload

            logger.debug(f"Successfully uploaded {key} to local storage")
            return self._get_public_url(key)

        except OSError as e:
            logger.error(f"File system error uploading {key}: {e}")
            raise StorageException(f"Failed to write file: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error uploading {key}: {e}")
            raise StorageException(f"Upload failed: {e}") from e

    def _get_public_url(self, key: str) -> str:
        """Generate public URL for the stored file."""
        if self.public_url_base:
            # URL-encode the key for safety
            encoded_key = quote(key, safe="/")
            return f"{self.public_url_base.rstrip('/')}/{encoded_key}"
        else:
            return f"file://{self.base_path / key}"

    async def download(self, key: str) -> bytes:
        """Download file content from local storage."""
        try:
            file_path = self._get_safe_file_path(key)

            if not file_path.exists():
                raise StorageException(f"File not found: {key}")

            async with aiofiles.open(file_path, "rb") as f:
                return await f.read()

        except OSError as e:
            logger.error(f"File system error downloading {key}: {e}")
            raise StorageException(f"Failed to read file: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error downloading {key}: {e}")
            raise StorageException(f"Download failed: {e}") from e

    async def get_presigned_upload_url(
        self, key: str, content_type: str, expires_in: timedelta | None = None
    ) -> dict[str, Any]:
        """Local storage doesn't support presigned URLs - return direct upload info."""
        # For local storage, we can't really do presigned URLs
        # This would be handled by the web server (e.g., FastAPI endpoint)
        return {
            "url": f"/api/storage/upload/{quote(key, safe='/')}",
            "fields": {"content-type": content_type},
            "method": "PUT",
            "expires_at": None,  # Handled by server session
        }

    async def get_presigned_download_url(
        self, key: str, expires_in: timedelta | None = None
    ) -> str:
        """Return the public URL for local storage."""
        return self._get_public_url(key)

    async def delete(self, key: str) -> bool:
        """Delete file by storage key."""
        try:
            file_path = self._get_safe_file_path(key)

            if not file_path.exists():
                return False

            # Delete the main file
            file_path.unlink()

            # Delete metadata file if it exists
            metadata_path = file_path.with_suffix(file_path.suffix + ".meta")
            if metadata_path.exists():
                metadata_path.unlink()

            logger.debug(f"Successfully deleted {key} from local storage")
            return True

        except OSError as e:
            logger.error(f"File system error deleting {key}: {e}")
            raise StorageException(f"Failed to delete file: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error deleting {key}: {e}")
            raise StorageException(f"Delete failed: {e}") from e

    async def exists(self, key: str) -> bool:
        """Check if file exists."""
        try:
            file_path = self._get_safe_file_path(key)
            return file_path.exists()
        except SecurityException:
            return False
        except Exception as e:
            logger.warning(f"Error checking existence of {key}: {e}")
            return False

    async def get_metadata(self, key: str) -> dict[str, Any]:
        """Get file metadata (size, modified date, etc.)."""
        try:
            file_path = self._get_safe_file_path(key)

            if not file_path.exists():
                raise StorageException(f"File not found: {key}")

            stat = file_path.stat()

            # Try to load stored metadata
            stored_metadata = {}
            metadata_path = file_path.with_suffix(file_path.suffix + ".meta")
            if metadata_path.exists():
                try:
                    async with aiofiles.open(metadata_path) as f:
                        metadata_content = await f.read()
                        stored_metadata = json.loads(metadata_content)
                except Exception as e:
                    logger.warning(f"Failed to load metadata for {key}: {e}")

            return {
                "size": stat.st_size,
                "modified_time": stat.st_mtime,
                "created_time": stat.st_ctime,
                **stored_metadata,
            }

        except OSError as e:
            logger.error(f"File system error getting metadata for {key}: {e}")
            raise StorageException(f"Failed to get metadata: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error getting metadata for {key}: {e}")
            raise StorageException(f"Get metadata failed: {e}") from e
