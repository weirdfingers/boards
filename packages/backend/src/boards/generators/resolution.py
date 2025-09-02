"""
Artifact resolution utilities for converting Generation references to actual files.
"""
import os
import tempfile
from typing import Union, Optional
import httpx
from .artifacts import AudioArtifact, VideoArtifact, ImageArtifact, TextArtifact, LoRArtifact


async def resolve_artifact(artifact: Union[AudioArtifact, VideoArtifact, ImageArtifact, LoRArtifact]) -> str:
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
        raise ValueError("TextArtifact cannot be resolved to a file path - use artifact.content directly")
    
    # Check if the storage_url is already a local file
    if os.path.exists(artifact.storage_url):
        return artifact.storage_url
    
    # Download the file to a temporary location
    return await download_artifact_to_temp(artifact)


async def download_artifact_to_temp(artifact: Union[AudioArtifact, VideoArtifact, ImageArtifact, LoRArtifact]) -> str:
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
    
    # Create temporary file with appropriate extension
    temp_fd, temp_path = tempfile.mkstemp(suffix=extension, prefix=f"boards_artifact_{artifact.generation_id}_")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(artifact.storage_url)
            response.raise_for_status()
            
            # Write content to temporary file
            with os.fdopen(temp_fd, 'wb') as temp_file:
                temp_file.write(response.content)
            
        return temp_path
    
    except Exception:
        # Clean up the temporary file if download failed
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
        raise


def _get_file_extension(artifact: Union[AudioArtifact, VideoArtifact, ImageArtifact, LoRArtifact]) -> str:
    """
    Get the appropriate file extension for an artifact based on its format.
    
    Args:
        artifact: Artifact to get extension for
        
    Returns:
        str: File extension including the dot (e.g., '.mp4', '.png')
    """
    format_ext = artifact.format.lower()
    
    # Add dot if not present
    if not format_ext.startswith('.'):
        format_ext = f'.{format_ext}'
    
    return format_ext


# TODO: This function will be implemented when we integrate with the storage system


# Placeholder functions for storing generated results
# These will be implemented when integrating with the storage system

async def store_image_result(storage_url: str, 
                           format: str, 
                           generation_id: str,
                           width: int,
                           height: int) -> ImageArtifact:
    """Create ImageArtifact from stored content."""
    return ImageArtifact(
        generation_id=generation_id,
        storage_url=storage_url,
        width=width,
        height=height,
        format=format
    )


async def store_video_result(storage_url: str, 
                           format: str, 
                           generation_id: str,
                           width: int,
                           height: int,
                           duration: Optional[float] = None,
                           fps: Optional[float] = None) -> VideoArtifact:
    """Create VideoArtifact from stored content."""
    return VideoArtifact(
        generation_id=generation_id,
        storage_url=storage_url,
        width=width,
        height=height,
        format=format,
        duration=duration,
        fps=fps
    )


async def store_audio_result(storage_url: str, 
                           format: str, 
                           generation_id: str,
                           duration: Optional[float] = None,
                           sample_rate: Optional[int] = None,
                           channels: Optional[int] = None) -> AudioArtifact:
    """Create AudioArtifact from stored content."""
    return AudioArtifact(
        generation_id=generation_id,
        storage_url=storage_url,
        format=format,
        duration=duration,
        sample_rate=sample_rate,
        channels=channels
    )