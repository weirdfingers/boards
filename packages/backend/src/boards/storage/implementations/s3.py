"""AWS S3 storage provider with IAM auth and CloudFront CDN support."""

import logging
import os
import tempfile
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import aiofiles

if TYPE_CHECKING:
    import boto3

try:
    import aioboto3
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError, NoCredentialsError

    _s3_available = True
except ImportError:
    boto3 = None
    ClientError = None
    NoCredentialsError = None
    Config = None
    aioboto3 = None
    _s3_available = False

from ..base import StorageException, StorageProvider

logger = logging.getLogger(__name__)


class S3StorageProvider(StorageProvider):
    """AWS S3 storage with IAM auth, CloudFront CDN, and proper async patterns."""

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        endpoint_url: str | None = None,
        cloudfront_domain: str | None = None,
        upload_config: dict[str, Any] | None = None,
    ):
        if not _s3_available:
            raise ImportError("boto3 and aioboto3 are required for S3StorageProvider")

        self.bucket = bucket
        self.region = region
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        self.endpoint_url = endpoint_url
        self.cloudfront_domain = cloudfront_domain

        # Default upload configuration
        self.upload_config = {
            "ServerSideEncryption": "AES256",
            "StorageClass": "STANDARD",
            **(upload_config or {}),
        }

        # Configure boto3 with optimized settings
        self.config = Config(  # type: ignore[reportUnknownMemberType]
            region_name=self.region,
            retries={"max_attempts": 3, "mode": "adaptive"},
            max_pool_connections=50,
        )

        self._session: Any | None = None

    def _get_session(self) -> Any:
        """Get or create the aioboto3 session."""
        if self._session is None:
            self._session = aioboto3.Session(  # type: ignore[reportUnknownMemberType]
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                aws_session_token=self.aws_session_token,
                region_name=self.region,
            )
        return self._session

    async def upload(
        self,
        key: str,
        content: bytes | AsyncIterator[bytes],
        content_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Upload content to S3."""
        try:
            session = self._get_session()

            # Prepare upload parameters
            upload_params = {
                "Bucket": self.bucket,
                "Key": key,
                "ContentType": content_type,
                **self.upload_config,
            }

            # Add custom metadata (S3 requires x-amz-meta- prefix)
            if metadata:
                s3_metadata = {}
                for k, v in metadata.items():
                    # Convert values to strings and sanitize keys
                    clean_key = k.replace("-", "_").replace(" ", "_")
                    s3_metadata[clean_key] = str(v)
                upload_params["Metadata"] = s3_metadata

            # Handle streaming content for large files
            if isinstance(content, bytes):
                upload_params["Body"] = content
            else:
                # Stream to temp file to handle large uploads efficiently
                with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                    tmp_file_path = tmp_file.name

                # Use async file operations for streaming content
                async with aiofiles.open(tmp_file_path, "wb") as f:
                    async for chunk in content:
                        await f.write(chunk)

                # Read the temp file asynchronously and upload
                async with aiofiles.open(tmp_file_path, "rb") as f:
                    file_content = await f.read()
                    upload_params["Body"] = file_content

                # Clean up temp file
                os.unlink(tmp_file_path)

            # Upload using aioboto3
            async with session.client(
                "s3", config=self.config, endpoint_url=self.endpoint_url
            ) as s3:
                await s3.put_object(**upload_params)

            # Return the CloudFront URL if configured, otherwise S3 URL
            if self.cloudfront_domain:
                return f"https://{self.cloudfront_domain}/{key}"
            else:
                return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"

        except Exception as e:
            if isinstance(e, StorageException):
                raise
            logger.error(f"Unexpected error uploading {key} to S3: {e}")
            raise StorageException(f"S3 upload failed: {e}") from e

    async def download(self, key: str) -> bytes:
        """Download file content from S3."""
        try:
            session = self._get_session()
            async with session.client(
                "s3", config=self.config, endpoint_url=self.endpoint_url
            ) as s3:
                response = await s3.get_object(Bucket=self.bucket, Key=key)

                # Read the streaming body
                content = await response["Body"].read()
                return content

        except Exception as e:
            if isinstance(e, StorageException):
                raise
            logger.error(f"Failed to download {key} from S3: {e}")
            raise StorageException(f"S3 download failed: {e}") from e

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
            session = self._get_session()
            async with session.client(
                "s3", config=self.config, endpoint_url=self.endpoint_url
            ) as s3:
                # Generate presigned POST for direct uploads with form fields
                response = await s3.generate_presigned_post(
                    Bucket=self.bucket,
                    Key=key,
                    Fields={"Content-Type": content_type, **self.upload_config},
                    Conditions=[
                        {"Content-Type": content_type},
                        [
                            "content-length-range",
                            1,
                            self.upload_config.get("max_file_size", 100 * 1024 * 1024),
                        ],
                    ],
                    ExpiresIn=int(expires_in.total_seconds()),
                )

                return {
                    "url": response["url"],
                    "fields": response["fields"],
                    "expires_at": (datetime.now(UTC) + expires_in).isoformat(),
                }

        except Exception as e:
            if isinstance(e, StorageException):
                raise
            logger.error(f"Failed to create presigned upload URL for {key}: {e}")
            raise StorageException(f"S3 presigned URL creation failed: {e}") from e

    async def get_presigned_download_url(
        self, key: str, expires_in: timedelta | None = None
    ) -> str:
        """Generate presigned URL for secure downloads."""
        if expires_in is None:
            expires_in = timedelta(hours=1)

        try:
            # If using CloudFront, use CloudFront signed URLs for better performance
            if self.cloudfront_domain:
                # For now, return the CloudFront URL (in production, you'd want CloudFront signed URLs)
                return f"https://{self.cloudfront_domain}/{key}"

            session = self._get_session()
            async with session.client(
                "s3", config=self.config, endpoint_url=self.endpoint_url
            ) as s3:
                url = await s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket, "Key": key},
                    ExpiresIn=int(expires_in.total_seconds()),
                )
                return url

        except Exception as e:
            if isinstance(e, StorageException):
                raise
            logger.error(f"Failed to create presigned download URL for {key}: {e}")
            raise StorageException(
                f"S3 presigned download URL creation failed: {e}"
            ) from e

    async def delete(self, key: str) -> bool:
        """Delete file by storage key."""
        try:
            session = self._get_session()
            async with session.client(
                "s3", config=self.config, endpoint_url=self.endpoint_url
            ) as s3:
                await s3.delete_object(Bucket=self.bucket, Key=key)
                return True

        except Exception as e:
            logger.error(f"Unexpected error deleting {key} from S3: {e}")
            raise StorageException(f"S3 delete failed: {e}") from e

    async def exists(self, key: str) -> bool:
        """Check if file exists."""
        try:
            session = self._get_session()
            async with session.client(
                "s3", config=self.config, endpoint_url=self.endpoint_url
            ) as s3:
                await s3.head_object(Bucket=self.bucket, Key=key)
                return True
        except Exception:
            return False

    async def get_metadata(self, key: str) -> dict[str, Any]:
        """Get file metadata (size, modified date, etc.)."""
        try:
            session = self._get_session()
            async with session.client(
                "s3", config=self.config, endpoint_url=self.endpoint_url
            ) as s3:
                response = await s3.head_object(Bucket=self.bucket, Key=key)

                # Extract metadata
                result = {
                    "size": response.get("ContentLength", 0),
                    "last_modified": response.get("LastModified"),
                    "content_type": response.get("ContentType"),
                    "etag": response.get("ETag", "").strip('"'),
                    "version_id": response.get("VersionId"),
                    "storage_class": response.get("StorageClass", "STANDARD"),
                    "server_side_encryption": response.get("ServerSideEncryption"),
                }

                # Add custom metadata (remove x-amz-meta- prefix)
                custom_metadata = response.get("Metadata", {})
                if custom_metadata:
                    result["custom_metadata"] = custom_metadata

                return result

        except Exception as e:
            if isinstance(e, StorageException):
                raise
            logger.error(f"Failed to get metadata for {key} from S3: {e}")
            raise StorageException(f"S3 get metadata failed: {e}") from e
