"""Google Cloud Storage provider with IAM auth and CDN support."""

import json
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from google.cloud import storage

try:
    import asyncio

    from google.auth import default
    from google.auth.exceptions import DefaultCredentialsError
    from google.cloud import storage
    from google.cloud.exceptions import GoogleCloudError, NotFound

    _gcs_available = True
except ImportError:
    storage = None
    NotFound = None
    GoogleCloudError = None
    default = None
    DefaultCredentialsError = None
    _gcs_available = False

from ...logging import get_logger
from ..base import StorageException, StorageProvider

logger = get_logger(__name__)


class GCSStorageProvider(StorageProvider):
    """Google Cloud Storage with IAM auth, Cloud CDN, and proper async patterns."""

    def __init__(
        self,
        bucket: str,
        project_id: str | None = None,
        credentials_path: str | None = None,
        credentials_json: str | None = None,
        cdn_domain: str | None = None,
        upload_config: dict[str, Any] | None = None,
    ):
        if not _gcs_available:
            raise ImportError(
                "google-cloud-storage is required for GCSStorageProvider. "
                "Install with: pip install google-cloud-storage"
            )

        self.bucket_name = bucket
        self.project_id = project_id
        self.credentials_path = credentials_path
        self.credentials_json = credentials_json
        self.cdn_domain = cdn_domain

        # Default upload configuration
        self.upload_config = {
            "cache_control": "public, max-age=3600",
            "predefined_acl": None,  # Use bucket's default ACL
            **(upload_config or {}),
        }

        self._client: Any | None = None
        self._bucket: Any | None = None

        # Client will be initialized lazily on first use

    def _get_client(self) -> Any:
        """Get or create the GCS client with proper authentication."""
        if self._client is None:
            if storage is None:
                raise ImportError("google-cloud-storage is required for GCSStorageProvider")

            try:
                if self.credentials_json:
                    # Use JSON credentials string
                    credentials_info = json.loads(self.credentials_json)
                    from google.oauth2 import service_account

                    credentials = service_account.Credentials.from_service_account_info(
                        credentials_info,
                        scopes=["https://www.googleapis.com/auth/cloud-platform"],
                    )
                    self._client = storage.Client(credentials=credentials, project=self.project_id)
                elif self.credentials_path:
                    # Use service account file
                    credentials_path = Path(self.credentials_path)
                    if not credentials_path.exists():
                        raise FileNotFoundError(
                            f"Credentials file not found: {self.credentials_path}"
                        )

                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path)
                    self._client = storage.Client(project=self.project_id)
                else:
                    # Use default credentials (environment variables, gcloud, etc.)
                    self._client = storage.Client(project=self.project_id)

                # Get bucket reference
                self._bucket = self._client.bucket(self.bucket_name)

            except Exception as e:
                logger.error(f"Failed to initialize GCS client: {e}")
                raise StorageException(f"GCS client initialization failed: {e}") from e

        return self._client

    async def _run_sync(self, func, *args, **kwargs) -> Any:
        """Run synchronous GCS operations in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)

    async def upload(
        self,
        key: str,
        content: bytes | AsyncIterator[bytes],
        content_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Upload content to GCS."""
        try:
            # Get client (initializes on first use)
            client = self._get_client()
            bucket = client.bucket(self.bucket_name)

            # Create blob object
            blob = bucket.blob(key)

            # Set content type
            blob.content_type = content_type

            # Set cache control and other configuration
            if self.upload_config.get("cache_control"):
                blob.cache_control = self.upload_config["cache_control"]

            # Add custom metadata
            if metadata:
                # GCS metadata keys must be lowercase and can contain only letters,
                # numbers, and underscores
                gcs_metadata = {}
                for k, v in metadata.items():
                    # Convert key to lowercase and replace invalid characters
                    clean_key = k.lower().replace("-", "_").replace(" ", "_")
                    gcs_metadata[clean_key] = str(v)
                blob.metadata = gcs_metadata

            # Handle streaming content for large files
            if isinstance(content, bytes):
                file_content = content
            else:
                # Collect streaming content into memory for upload
                # For very large files, consider using resumable uploads
                chunks = []
                total_size = 0
                async for chunk in content:
                    chunks.append(chunk)
                    total_size += len(chunk)
                    # For files larger than 100MB, we could implement resumable upload
                    if total_size > 100 * 1024 * 1024:
                        logger.warning(
                            f"Large file upload ({total_size} bytes) - "
                            f"consider implementing resumable upload for key: {key}"
                        )

                file_content = b"".join(chunks)

            # Upload using thread pool to avoid blocking
            await self._run_sync(blob.upload_from_string, file_content, content_type=content_type)

            # Return the CDN URL if configured, otherwise public GCS URL
            if self.cdn_domain:
                return f"https://{self.cdn_domain}/{key}"
            else:
                return f"https://storage.googleapis.com/{self.bucket_name}/{key}"

        except Exception as e:
            if isinstance(e, StorageException):
                raise
            logger.error(f"Unexpected error uploading {key} to GCS: {e}")
            raise StorageException(f"GCS upload failed: {e}") from e

    async def download(self, key: str) -> bytes:
        """Download file content from GCS."""
        try:
            # Get client (initializes on first use)
            client = self._get_client()
            bucket = client.bucket(self.bucket_name)

            blob = bucket.blob(key)

            # Download using thread pool to avoid blocking
            content = await self._run_sync(blob.download_as_bytes)
            return content

        except Exception as e:
            if isinstance(e, StorageException):
                raise
            logger.error(f"Failed to download {key} from GCS: {e}")
            raise StorageException(f"GCS download failed: {e}") from e

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
            # Get client (initializes on first use)
            client = self._get_client()
            bucket = client.bucket(self.bucket_name)

            blob = bucket.blob(key)

            # Generate signed URL for PUT operations
            url = await self._run_sync(
                blob.generate_signed_url,
                version="v4",
                expiration=expires_in,
                method="PUT",
                content_type=content_type,
                headers={"Content-Type": content_type},
            )

            return {
                "url": url,
                "method": "PUT",
                "headers": {"Content-Type": content_type},
                "expires_at": (datetime.now(UTC) + expires_in).isoformat(),
            }

        except Exception as e:
            if isinstance(e, StorageException):
                raise
            logger.error(f"Failed to create presigned upload URL for {key}: {e}")
            raise StorageException(f"GCS presigned URL creation failed: {e}") from e

    async def get_presigned_download_url(
        self, key: str, expires_in: timedelta | None = None
    ) -> str:
        """Generate presigned URL for secure downloads."""
        if expires_in is None:
            expires_in = timedelta(hours=1)

        try:
            # Always use GCS native signed URLs for security
            # Get client (initializes on first use)
            client = self._get_client()
            bucket = client.bucket(self.bucket_name)

            blob = bucket.blob(key)

            # Generate signed URL for GET operations
            url = await self._run_sync(
                blob.generate_signed_url,
                version="v4",
                expiration=expires_in,
                method="GET",
            )

            return url

        except Exception as e:
            if isinstance(e, StorageException):
                raise
            logger.error(f"Failed to create presigned download URL for {key}: {e}")
            raise StorageException(f"GCS presigned download URL creation failed: {e}") from e

    async def delete(self, key: str) -> bool:
        """Delete file by storage key."""
        try:
            # Get client (initializes on first use)
            client = self._get_client()
            bucket = client.bucket(self.bucket_name)

            blob = bucket.blob(key)
            await self._run_sync(blob.delete)
            return True

        except Exception as e:
            logger.error(f"Unexpected error deleting {key} from GCS: {e}")
            raise StorageException(f"GCS delete failed: {e}") from e

    async def exists(self, key: str) -> bool:
        """Check if file exists."""
        try:
            # Get client (initializes on first use)
            client = self._get_client()
            bucket = client.bucket(self.bucket_name)

            blob = bucket.blob(key)
            exists = await self._run_sync(blob.exists)
            return exists

        except Exception:
            return False

    async def get_metadata(self, key: str) -> dict[str, Any]:
        """Get file metadata (size, modified date, etc.)."""
        try:
            # Get client (initializes on first use)
            client = self._get_client()
            bucket = client.bucket(self.bucket_name)

            blob = bucket.blob(key)

            # Reload blob to get latest metadata
            await self._run_sync(blob.reload)

            result = {
                "size": blob.size or 0,
                "last_modified": blob.updated,
                "content_type": blob.content_type,
                "etag": blob.etag,
                "generation": blob.generation,
                "storage_class": blob.storage_class,
                "cache_control": blob.cache_control,
                "content_encoding": blob.content_encoding,
                "content_disposition": blob.content_disposition,
                "content_language": blob.content_language,
            }

            # Add custom metadata
            if blob.metadata:
                result["custom_metadata"] = blob.metadata

            return result

        except Exception as e:
            if isinstance(e, StorageException):
                raise
            logger.error(f"Failed to get metadata for {key} from GCS: {e}")
            raise StorageException(f"GCS get metadata failed: {e}") from e
