"""
Shared utilities for Kie.ai generators.

Provides helper functions for common operations across Kie generators.
"""

import asyncio
import os

import httpx

from ...artifacts import AudioArtifact, DigitalArtifact, ImageArtifact, VideoArtifact
from ...base import GeneratorExecutionContext


async def upload_artifacts_to_kie[T: DigitalArtifact](
    artifacts: list[ImageArtifact] | list[VideoArtifact] | list[AudioArtifact] | list[T],
    context: GeneratorExecutionContext,
) -> list[str]:
    """
    Upload artifacts to Kie.ai's temporary storage for use in API requests.

    Kie.ai API endpoints require publicly accessible URLs for file inputs. Since our
    storage URLs might be local or private (localhost, private S3 buckets, etc.),
    we need to:
    1. Resolve each artifact to a local file path
    2. Upload to Kie.ai's public temporary storage
    3. Get back publicly accessible URLs

    Note: Files uploaded to Kie.ai storage expire after 3 days.

    Args:
        artifacts: List of artifacts (image, video, or audio) to upload
        context: Generator execution context for artifact resolution

    Returns:
        List of publicly accessible URLs from Kie.ai storage

    Raises:
        ValueError: If KIE_API_KEY is not set
        Any exceptions from file resolution or upload are propagated
    """
    api_key = os.getenv("KIE_API_KEY")
    if not api_key:
        raise ValueError("KIE_API_KEY environment variable is required for file uploads")

    async def upload_single_artifact(artifact: DigitalArtifact) -> str:
        """Upload a single artifact and return its public URL."""
        # Resolve artifact to local file path (downloads if needed)
        file_path_str = await context.resolve_artifact(artifact)

        # Upload to Kie.ai's temporary storage
        # Using file stream upload API
        async with httpx.AsyncClient() as client:
            with open(file_path_str, "rb") as f:
                files = {"file": f}
                # uploadPath is required by Kie.ai API - specifies the storage path
                data = {"uploadPath": "boards/temp"}
                response = await client.post(
                    "https://kieai.redpandaai.co/api/file-stream-upload",
                    files=files,
                    data=data,
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=120.0,  # 2 minute timeout for uploads
                )

            if response.status_code != 200:
                raise ValueError(f"File upload failed: {response.status_code} {response.text}")

            result = response.json()

            if not result.get("success"):
                raise ValueError(f"File upload failed: {result.get('msg')}")

            # Extract the public URL from response data
            data = result.get("data", {})

            # The actual field name is 'downloadUrl' based on API response
            file_url = data.get("downloadUrl")

            if not file_url:
                # Fallback to other possible field names
                file_url = data.get("fileUrl") or data.get("file_url") or data.get("url")

            if not file_url:
                # If we still can't find the URL, provide detailed error message
                raise ValueError(
                    f"File upload succeeded but couldn't find URL in response. "
                    f"Response data keys: {list(data.keys())}, "
                    f"Full response: {result}"
                )

            return file_url

    # Upload all artifacts in parallel for performance
    urls = await asyncio.gather(*[upload_single_artifact(artifact) for artifact in artifacts])

    return list(urls)
