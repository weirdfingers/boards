"""Core storage interfaces and manager implementation."""

import asyncio
import re
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from ..logging import get_logger

logger = get_logger(__name__)


@dataclass
class StorageConfig:
    """Configuration for storage system."""

    default_provider: str
    providers: dict[str, dict[str, Any]]
    routing_rules: list[dict[str, Any]]
    max_file_size: int = 100 * 1024 * 1024  # 100MB default
    allowed_content_types: set[str] = field(default_factory=set)

    def __post_init__(self):
        if not self.allowed_content_types:
            self.allowed_content_types = {
                "image/jpeg",
                "image/png",
                "image/webp",
                "image/gif",
                "video/mp4",
                "video/webm",
                "video/quicktime",
                "audio/mpeg",
                "audio/wav",
                "audio/ogg",
                "text/plain",
                "application/json",
                "text/markdown",
                "application/octet-stream",  # For model files
            }


@dataclass
class ArtifactReference:
    """Reference to a stored artifact."""

    artifact_id: str
    storage_key: str
    storage_provider: str
    storage_url: str
    content_type: str
    size: int = 0
    created_at: datetime | None = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(UTC)


class StorageException(Exception):
    """Base exception for storage operations."""

    pass


class SecurityException(StorageException):
    """Security-related storage exception."""

    pass


class ValidationException(StorageException):
    """Content validation exception."""

    pass


class StorageProvider(ABC):
    """Abstract base class for all storage providers."""

    @abstractmethod
    async def upload(
        self,
        key: str,
        content: bytes | AsyncIterator[bytes],
        content_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Upload content and return storage reference.

        Args:
            key: Storage key (must be validated before calling)
            content: File content as bytes or async iterator
            content_type: MIME type (must be validated)
            metadata: Optional metadata dictionary

        Returns:
            storage reference

        Raises:
            StorageException: On upload failure
            SecurityException: On security validation failure
        """
        pass

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Download content by storage key."""
        pass

    @abstractmethod
    async def get_presigned_upload_url(
        self, key: str, content_type: str, expires_in: timedelta | None = None
    ) -> dict[str, Any]:
        """Generate presigned URL for direct client uploads."""
        pass

    @abstractmethod
    async def get_presigned_download_url(
        self, key: str, expires_in: timedelta | None = None
    ) -> str:
        """Generate presigned URL for secure downloads."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete file by storage key."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if file exists."""
        pass

    @abstractmethod
    async def get_metadata(self, key: str) -> dict[str, Any]:
        """Get file metadata (size, modified date, etc.)."""
        pass


class StorageManager:
    """Central storage coordinator handling provider selection and routing."""

    def __init__(self, config: StorageConfig):
        self.providers: dict[str, StorageProvider] = {}
        self.default_provider = config.default_provider
        self.routing_rules = config.routing_rules
        self.config = config

    def _validate_storage_key(self, key: str) -> str:
        """Validate and sanitize storage key to prevent path traversal."""
        # Remove any path traversal attempts
        if ".." in key or key.startswith("/") or "\\" in key:
            raise SecurityException(f"Invalid storage key: {key}")

        # Sanitize key components
        key_parts = key.split("/")
        sanitized_parts: list[str] = []

        for part in key_parts:
            # Remove dangerous characters, keep alphanumeric, hyphens, underscores, dots
            sanitized = re.sub(r"[^a-zA-Z0-9._-]", "", part)
            if not sanitized:
                raise SecurityException(f"Invalid key component: {part}")
            sanitized_parts.append(sanitized)

        return "/".join(sanitized_parts)

    def _validate_content_type(self, content_type: str) -> None:
        """Validate content type against allowed types."""
        if content_type not in self.config.allowed_content_types:
            raise ValidationException(f"Content type not allowed: {content_type}")

    def _validate_file_size(self, content_size: int) -> None:
        """Validate file size against limits."""
        if content_size > self.config.max_file_size:
            raise ValidationException(
                f"File size {content_size} exceeds limit {self.config.max_file_size}"
            )

    def register_provider(self, name: str, provider: StorageProvider):
        """Register a storage provider."""
        self.providers[name] = provider

    async def store_artifact(
        self,
        artifact_id: str,
        content: bytes | AsyncIterator[bytes],
        artifact_type: str,
        content_type: str,
        tenant_id: str | None = None,
        board_id: str | None = None,
    ) -> ArtifactReference:
        """Store artifact with comprehensive validation and error handling."""

        try:
            # Validate content type
            self._validate_content_type(content_type)

            # Validate content size if it's bytes
            if isinstance(content, bytes):
                self._validate_file_size(len(content))

            # Generate and validate storage key
            key = self._generate_storage_key(artifact_id, artifact_type, tenant_id, board_id)
            validated_key = self._validate_storage_key(key)

            # Select provider based on routing rules
            provider_name = self._select_provider(artifact_type, content)
            if provider_name not in self.providers:
                raise StorageException(f"Provider not found: {provider_name}")

            provider = self.providers[provider_name]

            # Prepare metadata
            metadata = {
                "artifact_id": artifact_id,
                "artifact_type": artifact_type,
                "tenant_id": tenant_id,
                "board_id": board_id,
                "uploaded_at": datetime.now(UTC).isoformat(),
                "content_type": content_type,
            }

            # Store the content with retry logic
            storage_url = await self._upload_with_retry(
                provider, validated_key, content, content_type, metadata
            )

            logger.info(f"Successfully stored artifact {artifact_id} at {validated_key}")

            return ArtifactReference(
                artifact_id=artifact_id,
                storage_key=validated_key,
                storage_provider=provider_name,
                storage_url=storage_url,
                content_type=content_type,
                size=len(content) if isinstance(content, bytes) else 0,
                created_at=datetime.now(UTC),
            )

        except (SecurityException, ValidationException) as e:
            logger.error(f"Validation failed for artifact {artifact_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to store artifact {artifact_id}: {e}")
            raise StorageException(f"Storage operation failed: {e}") from e

    async def _upload_with_retry(
        self,
        provider: StorageProvider,
        key: str,
        content: bytes | AsyncIterator[bytes],
        content_type: str,
        metadata: dict[str, Any],
        max_retries: int = 3,
    ) -> str:
        """Upload with exponential backoff retry logic."""

        if max_retries <= 0:
            max_retries = 1

        for attempt in range(max_retries):
            try:
                return await provider.upload(key, content, content_type, metadata)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise

                wait_time = 2**attempt  # Exponential backoff
                logger.warning(
                    f"Upload attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s"
                )
                await asyncio.sleep(wait_time)

        # This should never be reached due to the exception handling above
        raise StorageException("Upload failed after all retries")

    def _generate_storage_key(
        self,
        artifact_id: str,
        artifact_type: str,
        tenant_id: str | None = None,
        board_id: str | None = None,
        variant: str = "original",
    ) -> str:
        """Generate hierarchical storage key with collision prevention."""

        # Use tenant_id or default
        tenant = tenant_id or "default"

        # Add timestamp and UUID for uniqueness
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        unique_suffix = str(uuid.uuid4())[:8]

        if board_id:
            # Board-scoped artifact
            return f"{tenant}/{artifact_type}/{board_id}/{artifact_id}_{timestamp}_{unique_suffix}/{variant}"  # noqa: E501
        else:
            # Global artifact (like LoRA models)
            return f"{tenant}/{artifact_type}/{artifact_id}_{timestamp}_{unique_suffix}/{variant}"

    def _select_provider(self, artifact_type: str, content: bytes | AsyncIterator[bytes]) -> str:
        """Select storage provider based on routing rules."""
        content_size = len(content) if isinstance(content, bytes) else 0

        for rule in self.routing_rules:
            condition = rule.get("condition", {})

            # Check artifact type condition
            if "artifact_type" in condition:
                if condition["artifact_type"] != artifact_type:
                    continue

            # Check size condition
            if "size_gt" in condition:
                size_limit = self._parse_size(condition["size_gt"])
                if content_size <= size_limit:
                    continue
                elif not isinstance(content, bytes):
                    logger.warning(
                        f"Size-based routing rule ignored for {artifact_type} - "
                        f"content size unknown for async iterator"
                    )
                    continue

            # If all conditions match, return this provider
            return rule["provider"]

        # Return default if no rules match
        return self.default_provider

    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '100MB' to bytes."""
        size_str = size_str.upper()
        if size_str.endswith("KB"):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith("MB"):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith("GB"):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)

    async def get_download_url(self, storage_key: str, provider_name: str) -> str:
        """Get download URL for a stored artifact."""
        if provider_name not in self.providers:
            raise StorageException(f"Provider not found: {provider_name}")

        provider = self.providers[provider_name]
        return await provider.get_presigned_download_url(storage_key)

    async def delete_artifact(self, storage_key: str, provider_name: str) -> bool:
        """Delete a stored artifact."""
        if provider_name not in self.providers:
            raise StorageException(f"Provider not found: {provider_name}")

        provider = self.providers[provider_name]
        return await provider.delete(storage_key)
