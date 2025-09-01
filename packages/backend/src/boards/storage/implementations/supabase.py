"""Supabase storage provider with integrated auth and CDN support."""

import tempfile
import logging
from typing import Optional, Dict, Any, Union, AsyncIterator
from datetime import datetime, timedelta, timezone

try:
    from supabase import create_client, Client
except ImportError:
    # Handle case where supabase is not installed
    create_client = None  # type: ignore
    Client = None  # type: ignore

from ..base import StorageProvider, StorageException

logger = logging.getLogger(__name__)


class SupabaseStorageProvider(StorageProvider):
    """Supabase storage with integrated auth, CDN, and proper async patterns."""
    
    def __init__(self, url: str, key: str, bucket: str):
        if create_client is None:
            raise ImportError("supabase-py is required for SupabaseStorageProvider")
            
        # Use sync client for now - async client has typing issues
        self.client = create_client(url, key)
        self.bucket = bucket
        self.url = url
        
    async def upload(
        self, 
        key: str, 
        content: Union[bytes, AsyncIterator[bytes]], 
        content_type: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        try:
            # Handle streaming content for large files
            if isinstance(content, bytes):
                file_content = content
            else:
                # Stream to temp file to avoid memory issues
                with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                    async for chunk in content:
                        tmp_file.write(chunk)
                    tmp_file.flush()
                    
                    # Read the temp file and upload
                    with open(tmp_file.name, 'rb') as f:
                        file_content = f.read()
                    
                    # Clean up temp file
                    import os
                    os.unlink(tmp_file.name)
            
            # Use Supabase client methods (sync for now due to typing issues)
            response = self.client.storage.from_(self.bucket).upload(
                path=key,
                file=file_content,
                file_options={  # type: ignore
                    'content-type': content_type,
                    'upsert': False  # Prevent accidental overwrites
                }
            )
            
            # Check for errors in response
            if hasattr(response, 'error') and response.error:  # type: ignore
                error_msg = str(response.error)  # type: ignore
                logger.error(f"Supabase upload failed for {key}: {error_msg}")
                
                # Handle specific error types
                if 'already exists' in error_msg.lower():
                    raise StorageException(f"File already exists: {key}")
                elif 'storage quota' in error_msg.lower():
                    raise StorageException(f"Storage quota exceeded")
                else:
                    raise StorageException(f"Upload failed: {error_msg}")
            
            # Get public URL
            public_url = self.client.storage.from_(self.bucket).get_public_url(key)
                
            logger.debug(f"Successfully uploaded {key} to Supabase storage")
            return public_url
            
        except Exception as e:
            if isinstance(e, StorageException):
                raise
            logger.error(f"Unexpected error uploading {key} to Supabase: {e}")
            raise StorageException(f"Supabase upload failed: {e}") from e
            
    async def download(self, key: str) -> bytes:
        """Download file content from Supabase storage."""
        try:
            response = self.client.storage.from_(self.bucket).download(key)
            if hasattr(response, 'error') and response.error:  # type: ignore
                raise StorageException(f"Download failed: {response.error}")  # type: ignore
            return response  # type: ignore
        except Exception as e:
            logger.error(f"Failed to download {key} from Supabase: {e}")
            raise StorageException(f"Download failed: {e}") from e
            
    async def get_presigned_upload_url(
        self, 
        key: str, 
        content_type: str, 
        expires_in: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """Generate presigned URL for direct client uploads."""
        if expires_in is None:
            expires_in = timedelta(hours=1)
            
        try:
            response = self.client.storage.from_(self.bucket).create_signed_upload_url(
                path=key,
                expires_in=int(expires_in.total_seconds())  # type: ignore
            )
            
            if hasattr(response, 'error') and response.error:  # type: ignore
                raise StorageException(f"Failed to create signed URL: {response.error}")  # type: ignore
                
            return {
                'url': response.data['signedURL'],  # type: ignore
                'fields': {},  # Supabase doesn't use form fields like S3
                'expires_at': (datetime.now(timezone.utc) + expires_in).isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to create presigned upload URL for {key}: {e}")
            raise StorageException(f"Presigned URL creation failed: {e}") from e
            
    async def get_presigned_download_url(
        self,
        key: str,
        expires_in: Optional[timedelta] = None
    ) -> str:
        """Generate presigned URL for secure downloads."""
        if expires_in is None:
            expires_in = timedelta(hours=1)
            
        try:
            response = self.client.storage.from_(self.bucket).create_signed_url(
                path=key,
                expires_in=int(expires_in.total_seconds())
            )
            
            if hasattr(response, 'error') and response.error:  # type: ignore
                raise StorageException(f"Failed to create signed download URL: {response.error}")  # type: ignore
                
            return response.data['signedURL']  # type: ignore
            
        except Exception as e:
            logger.error(f"Failed to create presigned download URL for {key}: {e}")
            raise StorageException(f"Presigned download URL creation failed: {e}") from e
    
    async def delete(self, key: str) -> bool:
        """Delete file by storage key."""
        try:
            response = self.client.storage.from_(self.bucket).remove([key])
            
            if hasattr(response, 'error') and response.error:  # type: ignore
                logger.error(f"Failed to delete {key} from Supabase: {response.error}")  # type: ignore
                return False
                
            logger.debug(f"Successfully deleted {key} from Supabase storage")
            return True
            
        except Exception as e:
            logger.error(f"Unexpected error deleting {key} from Supabase: {e}")
            raise StorageException(f"Delete failed: {e}") from e
    
    async def exists(self, key: str) -> bool:
        """Check if file exists."""
        try:
            # Try to get file info - if it doesn't exist, this will error
            response = self.client.storage.from_(self.bucket).get_public_url(key)
            # If we get here without error, the file exists
            return True
        except Exception:
            # Any error means the file doesn't exist or we can't access it
            return False
    
    async def get_metadata(self, key: str) -> Dict[str, Any]:
        """Get file metadata (size, modified date, etc.)."""
        try:
            # Supabase doesn't have a direct metadata endpoint
            # We'll need to use the list method with a prefix
            response = self.client.storage.from_(self.bucket).list(
                path="/".join(key.split("/")[:-1]) or "/"
            )
            
            if hasattr(response, 'error') and response.error:  # type: ignore
                raise StorageException(f"Failed to get metadata: {response.error}")  # type: ignore
            
            # Find our file in the results
            file_info = None
            filename = key.split("/")[-1]
            for item in response:  # type: ignore
                if item.get('name') == filename:
                    file_info = item
                    break
            
            if not file_info:
                raise StorageException(f"File not found: {key}")
            
            metadata = file_info.get('metadata', {})
            result = {
                'size': file_info.get('size', 0),
                'last_modified': file_info.get('updated_at'),
                'content_type': file_info.get('mimetype'),
                'etag': file_info.get('id'),
            }
            if isinstance(metadata, dict):
                result.update(metadata)
            return result
            
        except Exception as e:
            if isinstance(e, StorageException):
                raise
            logger.error(f"Failed to get metadata for {key} from Supabase: {e}")
            raise StorageException(f"Get metadata failed: {e}") from e