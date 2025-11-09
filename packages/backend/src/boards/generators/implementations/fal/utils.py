"""
Shared utilities for Fal.ai generators.

Provides helper functions for common operations across Fal generators.
"""

import asyncio

from ...artifacts import AudioArtifact, DigitalArtifact, ImageArtifact, VideoArtifact
from ...base import GeneratorExecutionContext


async def upload_artifacts_to_fal[T: DigitalArtifact](
    artifacts: list[ImageArtifact] | list[VideoArtifact] | list[AudioArtifact] | list[T],
    context: GeneratorExecutionContext,
) -> list[str]:
    """
    Upload artifacts to Fal's temporary storage for use in API requests.

    Fal API endpoints require publicly accessible URLs for file inputs. Since our
    storage URLs might be local or private (localhost, private S3 buckets, etc.),
    we need to:
    1. Resolve each artifact to a local file path
    2. Upload to Fal's public temporary storage
    3. Get back publicly accessible URLs

    Args:
        artifacts: List of artifacts (image, video, or audio) to upload
        context: Generator execution context for artifact resolution

    Returns:
        List of publicly accessible URLs from Fal storage

    Raises:
        ImportError: If fal_client is not installed
        Any exceptions from file resolution or upload are propagated
    """
    # Import fal_client
    try:
        import fal_client
    except ImportError as e:
        raise ImportError(
            "fal.ai SDK is required for Fal generators. "
            "Install with: pip install weirdfingers-boards[generators-fal]"
        ) from e

    async def upload_single_artifact(artifact: DigitalArtifact) -> str:
        """Upload a single artifact and return its public URL."""
        # Resolve artifact to local file path (downloads if needed)
        file_path_str = await context.resolve_artifact(artifact)

        # Upload to Fal's temporary storage and get public URL
        # fal_client.upload_file_async expects a file path
        url = await fal_client.upload_file_async(file_path_str)  # type: ignore[arg-type]

        return url

    # Upload all artifacts in parallel for performance
    urls = await asyncio.gather(*[upload_single_artifact(artifact) for artifact in artifacts])

    return list(urls)
