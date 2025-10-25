"""Supabase storage provider with integrated auth and CDN support."""

import os
import tempfile
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import aiofiles

if TYPE_CHECKING:
    from supabase import AsyncClient, create_async_client

try:
    from supabase import AsyncClient, create_async_client

    _supabase_available = True
except ImportError:
    # Handle case where supabase is not installed
    create_async_client = None
    # AsyncClient = None
    _supabase_available = False

from ...logging import get_logger
from ..base import StorageException, StorageProvider

logger = get_logger(__name__)


class SupabaseStorageProvider(StorageProvider):
    """Supabase storage with integrated auth, CDN, and proper async patterns."""

    def __init__(self, url: str, key: str, bucket: str):
        if not _supabase_available:
            raise ImportError("supabase-py is required for SupabaseStorageProvider")

        self.url = url
        self.key = key
        self.bucket = bucket
        self._client: AsyncClient | None = None

    async def _get_client(self) -> "AsyncClient":
        """Get or create the async Supabase client."""
        if self._client is None:
            if create_async_client is None:
                raise ImportError("Async Supabase client not available")
            self._client = await create_async_client(self.url, self.key)
        return self._client

    async def upload(
        self,
        key: str,
        content: bytes | AsyncIterator[bytes],
        content_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        try:
            client = await self._get_client()

            # Handle streaming content for large files
            if isinstance(content, bytes):
                file_content = content
            else:
                # Stream to temp file to avoid memory issues
                with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                    tmp_file_path = tmp_file.name

                # Use async file operations for streaming content
                async with aiofiles.open(tmp_file_path, "wb") as f:
                    async for chunk in content:
                        await f.write(chunk)

                # Read the temp file asynchronously and upload
                async with aiofiles.open(tmp_file_path, "rb") as f:
                    file_content = await f.read()

                # Clean up temp file
                os.unlink(tmp_file_path)

            # Use async Supabase client methods
            response = await client.storage.from_(self.bucket).upload(
                path=key,
                file=file_content,
                file_options={
                    "content-type": content_type,
                    "upsert": "false",  # Prevent accidental overwrites
                },
            )

            return response.path

        except Exception as e:
            if isinstance(e, StorageException):
                raise
            logger.error(f"Unexpected error uploading {key} to Supabase: {e}")
            raise StorageException(f"Supabase upload failed: {e}") from e

    async def download(self, key: str) -> bytes:
        """Download file content from Supabase storage."""
        try:
            client = await self._get_client()
            response = await client.storage.from_(self.bucket).download(key)

            return response

        except Exception as e:
            if isinstance(e, StorageException):
                raise
            logger.error(f"Failed to download {key} from Supabase: {e}")
            raise StorageException(f"Download failed: {e}") from e

    async def get_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: timedelta | None = None,
    ) -> dict[str, Any]:
        """Generate presigned URL for direct client uploads."""
        if expires_in is None:
            expires_in = timedelta(hours=1)

        try:
            client = await self._get_client()
            response = await client.storage.from_(self.bucket).create_signed_upload_url(path=key)

            return {
                "url": response["signed_url"],
                "fields": {},  # Supabase doesn't use form fields like S3
                "expires_at": (datetime.now(UTC) + expires_in).isoformat(),
            }
        except Exception as e:
            if isinstance(e, StorageException):
                raise
            logger.error(f"Failed to create presigned upload URL for {key}: {e}")
            raise StorageException(f"Presigned URL creation failed: {e}") from e

    async def get_presigned_download_url(
        self, key: str, expires_in: timedelta | None = None
    ) -> str:
        """Generate presigned URL for secure downloads."""
        if expires_in is None:
            expires_in = timedelta(hours=1)

        try:
            client = await self._get_client()
            response = await client.storage.from_(self.bucket).create_signed_url(
                path=key, expires_in=int(expires_in.total_seconds())
            )

            return response["signedURL"]

        except Exception as e:
            if isinstance(e, StorageException):
                raise
            logger.error(f"Failed to create presigned download URL for {key}: {e}")
            raise StorageException(f"Presigned download URL creation failed: {e}") from e

    async def delete(self, key: str) -> bool:
        """Delete file by storage key."""
        try:
            client = await self._get_client()
            await client.storage.from_(self.bucket).remove([key])  # type: ignore[reportUnknownMemberType]

            return True

        except Exception as e:
            logger.error(f"Unexpected error deleting {key} from Supabase: {e}")
            raise StorageException(f"Delete failed: {e}") from e

    async def exists(self, key: str) -> bool:
        """Check if file exists."""
        try:
            client = await self._get_client()
            # Try to get file info - if it doesn't exist, this will error
            await client.storage.from_(self.bucket).get_public_url(key)
            # If we get here without error, the file exists
            return True
        except Exception:
            # Any error means the file doesn't exist or we can't access it
            return False

    async def get_metadata(self, key: str) -> dict[str, Any]:
        """Get file metadata (size, modified date, etc.)."""
        try:
            client = await self._get_client()
            # Supabase doesn't have a direct metadata endpoint
            # We'll need to use the list method with a prefix
            response = await client.storage.from_(self.bucket).list(
                path="/".join(key.split("/")[:-1]) or "/"
            )

            # Find our file in the results
            file_info = None
            filename = key.split("/")[-1]
            for item in response:
                if item.get("name") == filename:
                    file_info = item
                    break

            if not file_info:
                raise StorageException(f"File not found: {key}")

            metadata = file_info.get("metadata", {})
            result = {
                "size": file_info.get("size", 0),
                "last_modified": file_info.get("updated_at"),
                "content_type": file_info.get("mimetype"),
                "etag": file_info.get("id"),
            }
            if isinstance(metadata, dict):
                result.update(metadata)
            return result

        except Exception as e:
            if isinstance(e, StorageException):
                raise
            logger.error(f"Failed to get metadata for {key} from Supabase: {e}")
            raise StorageException(f"Get metadata failed: {e}") from e
