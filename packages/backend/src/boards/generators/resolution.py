"""
Artifact resolution utilities for converting Generation references to actual files.
"""

import os
import tempfile
import uuid
from urllib.parse import urlparse

import aiofiles
import httpx

from ..logging import get_logger
from ..storage.base import StorageManager
from .artifacts import (
    AudioArtifact,
    ImageArtifact,
    LoRArtifact,
    TextArtifact,
    VideoArtifact,
)

logger = get_logger(__name__)


async def resolve_artifact(
    artifact: AudioArtifact | VideoArtifact | ImageArtifact | LoRArtifact,
) -> str:
    """
    Resolve an artifact to a local file path that can be used by provider SDKs.

    This function downloads the artifact from storage if needed and returns
    a local file path that generators can pass to provider SDKs.

    Args:
        artifact: Artifact instance to resolve

    Returns:
        str: Local file path to the artifact content

    Raises:
        ValueError: If the artifact type is not supported for file resolution
        httpx.HTTPError: If downloading the artifact fails
    """
    if isinstance(artifact, TextArtifact):
        # Text artifacts don't need file resolution - they contain content directly
        raise ValueError(
            "TextArtifact cannot be resolved to a file path - use artifact.content directly"
        )

    # Validate that storage_url is actually a URL (not a local file path)
    # This prevents potential security issues with paths like /etc/passwd
    parsed = urlparse(artifact.storage_url)

    # Check if it's a valid URL with a scheme (http, https, s3, etc.)
    if parsed.scheme in ("http", "https", "s3", "gs"):
        # It's a remote URL, download it
        return await download_artifact_to_temp(artifact)

    # If no scheme, it might be a local file path
    # Only allow this if the file actually exists (for backward compatibility)
    if os.path.exists(artifact.storage_url):
        logger.debug(
            "Using local file path for artifact",
            storage_url=artifact.storage_url,
        )
        return artifact.storage_url

    # Download the file to a temporary location
    return await download_artifact_to_temp(artifact)


async def download_artifact_to_temp(
    artifact: AudioArtifact | VideoArtifact | ImageArtifact | LoRArtifact,
) -> str:
    """
    Download an artifact from its storage URL to a temporary file.

    Args:
        artifact: Artifact to download

    Returns:
        str: Path to the temporary file containing the artifact content

    Raises:
        httpx.HTTPError: If downloading fails
    """
    # Determine file extension based on artifact type and format
    extension = _get_file_extension(artifact)

    # Create temporary file with appropriate extension (use random prefix for security)
    random_id = uuid.uuid4().hex[:8]
    temp_fd, temp_path = tempfile.mkstemp(suffix=extension, prefix=f"boards_artifact_{random_id}_")

    # Set restrictive file permissions (owner read/write only: 0o600)
    os.chmod(temp_path, 0o600)

    try:
        # Stream the download to avoid loading large files into memory
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("GET", artifact.storage_url) as response:
                response.raise_for_status()

                # Close the file descriptor returned by mkstemp and use aiofiles
                os.close(temp_fd)

                # Stream content to file using async I/O
                total_bytes = 0
                async with aiofiles.open(temp_path, "wb") as temp_file:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        await temp_file.write(chunk)
                        total_bytes += len(chunk)

                # Validate that we downloaded something
                if total_bytes == 0:
                    raise ValueError("Downloaded file is empty")

                logger.debug(
                    "Successfully downloaded artifact to temp file",
                    temp_path=temp_path,
                    size_bytes=total_bytes,
                )

        return temp_path

    except Exception:
        # Clean up the temporary file if download failed
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
        raise


def _get_file_extension(
    artifact: AudioArtifact | VideoArtifact | ImageArtifact | LoRArtifact,
) -> str:
    """
    Get the appropriate file extension for an artifact based on its format.

    Args:
        artifact: Artifact to get extension for

    Returns:
        str: File extension including the dot (e.g., '.mp4', '.png')
    """
    format_ext = artifact.format.lower()

    # Add dot if not present
    if not format_ext.startswith("."):
        format_ext = f".{format_ext}"

    return format_ext


async def download_from_url(url: str) -> bytes:
    """
    Download content from a URL (typically a provider's temporary URL).

    This is used to download generated content from providers like Replicate, OpenAI, etc.
    before uploading to our permanent storage.

    Note: For very large files, consider using streaming downloads directly to storage
    instead of loading into memory.

    Args:
        url: URL to download from

    Returns:
        bytes: Downloaded content

    Raises:
        httpx.HTTPError: If download fails
        ValueError: If downloaded content is empty
    """
    logger.debug("Downloading content from URL", url=url)

    # Stream download to avoid loading entire file into memory at once
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()

            # Collect chunks
            chunks = []
            total_bytes = 0
            async for chunk in response.aiter_bytes(chunk_size=8192):
                chunks.append(chunk)
                total_bytes += len(chunk)

            # Validate content
            if total_bytes == 0:
                raise ValueError(f"Downloaded file from {url} is empty")

            logger.info(
                "Successfully downloaded content",
                url=url,
                size_bytes=total_bytes,
            )
            return b"".join(chunks)


def _get_content_type_from_format(artifact_type: str, format: str) -> str:
    """
    Get MIME content type from artifact type and format.

    Args:
        artifact_type: Type of artifact ('image', 'video', 'audio')
        format: Format string (e.g., 'png', 'mp4', 'mp3')

    Returns:
        str: MIME content type
    """
    format_lower = format.lower()

    # Map common formats to content types
    content_type_map = {
        "image": {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
            "gif": "image/gif",
        },
        "video": {
            "mp4": "video/mp4",
            "webm": "video/webm",
            "mov": "video/quicktime",
        },
        "audio": {
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "ogg": "audio/ogg",
        },
    }

    type_map = content_type_map.get(artifact_type, {})
    return type_map.get(format_lower, "application/octet-stream")


async def store_image_result(
    storage_manager: StorageManager,
    generation_id: str,
    tenant_id: str,
    board_id: str,
    storage_url: str,
    format: str,
    width: int,
    height: int,
) -> ImageArtifact:
    """
    Store an image result by downloading from provider URL and uploading to storage.

    Args:
        storage_manager: Storage manager instance
        generation_id: ID of the generation
        tenant_id: Tenant ID for storage isolation
        board_id: Board ID for organization
        storage_url: Provider's temporary URL to download from
        format: Image format (png, jpg, etc.)
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        ImageArtifact with permanent storage URL

    Raises:
        StorageException: If storage operation fails
        httpx.HTTPError: If download fails
    """
    logger.info(
        "Storing image result",
        generation_id=generation_id,
        provider_url=storage_url,
        format=format,
    )

    # Download content from provider URL
    content = await download_from_url(storage_url)

    # Determine content type
    content_type = _get_content_type_from_format("image", format)

    # Upload to storage system
    artifact_ref = await storage_manager.store_artifact(
        artifact_id=generation_id,
        content=content,
        artifact_type="image",
        content_type=content_type,
        tenant_id=tenant_id,
        board_id=board_id,
    )

    logger.info(
        "Image stored successfully",
        generation_id=generation_id,
        storage_key=artifact_ref.storage_key,
        storage_url=artifact_ref.storage_url,
    )

    # Return artifact with our permanent storage URL
    return ImageArtifact(
        generation_id=generation_id,
        storage_url=artifact_ref.storage_url,
        width=width,
        height=height,
        format=format,
    )


async def store_video_result(
    storage_manager: StorageManager,
    generation_id: str,
    tenant_id: str,
    board_id: str,
    storage_url: str,
    format: str,
    width: int,
    height: int,
    duration: float | None = None,
    fps: float | None = None,
) -> VideoArtifact:
    """
    Store a video result by downloading from provider URL and uploading to storage.

    Args:
        storage_manager: Storage manager instance
        generation_id: ID of the generation
        tenant_id: Tenant ID for storage isolation
        board_id: Board ID for organization
        storage_url: Provider's temporary URL to download from
        format: Video format (mp4, webm, etc.)
        width: Video width in pixels
        height: Video height in pixels
        duration: Video duration in seconds (optional)
        fps: Frames per second (optional)

    Returns:
        VideoArtifact with permanent storage URL

    Raises:
        StorageException: If storage operation fails
        httpx.HTTPError: If download fails
    """
    logger.info(
        "Storing video result",
        generation_id=generation_id,
        provider_url=storage_url,
        format=format,
    )

    # Download content from provider URL
    content = await download_from_url(storage_url)

    # Determine content type
    content_type = _get_content_type_from_format("video", format)

    # Upload to storage system
    artifact_ref = await storage_manager.store_artifact(
        artifact_id=generation_id,
        content=content,
        artifact_type="video",
        content_type=content_type,
        tenant_id=tenant_id,
        board_id=board_id,
    )

    logger.info(
        "Video stored successfully",
        generation_id=generation_id,
        storage_key=artifact_ref.storage_key,
        storage_url=artifact_ref.storage_url,
    )

    # Return artifact with our permanent storage URL
    return VideoArtifact(
        generation_id=generation_id,
        storage_url=artifact_ref.storage_url,
        width=width,
        height=height,
        format=format,
        duration=duration,
        fps=fps,
    )


async def store_audio_result(
    storage_manager: StorageManager,
    generation_id: str,
    tenant_id: str,
    board_id: str,
    storage_url: str,
    format: str,
    duration: float | None = None,
    sample_rate: int | None = None,
    channels: int | None = None,
) -> AudioArtifact:
    """
    Store an audio result by downloading from provider URL and uploading to storage.

    Args:
        storage_manager: Storage manager instance
        generation_id: ID of the generation
        tenant_id: Tenant ID for storage isolation
        board_id: Board ID for organization
        storage_url: Provider's temporary URL to download from
        format: Audio format (mp3, wav, etc.)
        duration: Audio duration in seconds (optional)
        sample_rate: Sample rate in Hz (optional)
        channels: Number of audio channels (optional)

    Returns:
        AudioArtifact with permanent storage URL

    Raises:
        StorageException: If storage operation fails
        httpx.HTTPError: If download fails
    """
    logger.info(
        "Storing audio result",
        generation_id=generation_id,
        provider_url=storage_url,
        format=format,
    )

    # Download content from provider URL
    content = await download_from_url(storage_url)

    # Determine content type
    content_type = _get_content_type_from_format("audio", format)

    # Upload to storage system
    artifact_ref = await storage_manager.store_artifact(
        artifact_id=generation_id,
        content=content,
        artifact_type="audio",
        content_type=content_type,
        tenant_id=tenant_id,
        board_id=board_id,
    )

    logger.info(
        "Audio stored successfully",
        generation_id=generation_id,
        storage_key=artifact_ref.storage_key,
        storage_url=artifact_ref.storage_url,
    )

    # Return artifact with our permanent storage URL
    return AudioArtifact(
        generation_id=generation_id,
        storage_url=artifact_ref.storage_url,
        format=format,
        duration=duration,
        sample_rate=sample_rate,
        channels=channels,
    )


async def store_text_result(
    storage_manager: StorageManager,
    generation_id: str,
    tenant_id: str,
    board_id: str,
    content: str,
    format: str,
) -> TextArtifact:
    """
    Store a text result by uploading to storage.

    Args:
        storage_manager: Storage manager instance
        generation_id: ID of the generation
        tenant_id: Tenant ID for storage isolation
        board_id: Board ID for organization
        content: Text content to store
        format: Text format (plain, markdown, html, etc.)

    Returns:
        TextArtifact with permanent storage URL

    Raises:
        StorageException: If storage operation fails
        httpx.HTTPError: If upload fails
    """
    logger.info(
        "Storing text result",
        generation_id=generation_id,
        content=content,
        format=format,
    )

    # Upload to storage system
    artifact_ref = await storage_manager.store_artifact(
        artifact_id=generation_id,
        content=content.encode("utf-8"),
        artifact_type="text",
        content_type="text/plain",
        tenant_id=tenant_id,
        board_id=board_id,
    )

    logger.info(
        "Text stored successfully",
        generation_id=generation_id,
        storage_key=artifact_ref.storage_key,
        storage_url=artifact_ref.storage_url,
    )

    # Return artifact with our permanent storage URL
    return TextArtifact(
        generation_id=generation_id,
        storage_url=artifact_ref.storage_url,
        content=content,
        format=format,
    )
