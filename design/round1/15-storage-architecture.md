# Storage Architecture

## Overview

The Boards storage system needs to handle diverse artifact types (images, videos, audio, LoRAs, etc.) across multiple storage backends while providing a unified interface. This document outlines the pluggable storage architecture that supports local development, cloud deployment, and custom storage providers.

## Core Requirements

### Artifact Types
- **Images**: PNG, JPG, WebP, GIF (generated outputs, input references)
- **Videos**: MP4, WebM, MOV (generated content, training data)
- **Audio**: MP3, WAV, OGG (voice synthesis, music generation)
- **Text**: JSON, TXT, MD (prompts, metadata, configurations)
- **Models**: Binary files (LoRA weights, checkpoints)
- **Intermediate Assets**: Temporary files during multi-step generation

### Storage Backends
1. **Local Filesystem** - Development and self-hosted deployments
2. **Supabase Storage** - Default cloud option with auth integration
3. **AWS S3** - Enterprise cloud storage
4. **Google Cloud Storage** - Alternative cloud provider
5. **Custom Providers** - Plugin system for specialized storage

## Architecture Components

Storage components are implemented in the backend package at:
- `packages/backend/src/boards/storage/base.py` - Core interfaces and manager
- `packages/backend/src/boards/storage/implementations/` - Provider implementations

### 1. Storage Abstraction Layer

```python
# packages/backend/src/boards/storage/base.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, AsyncIterator, Union
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import re
import logging
from urllib.parse import quote
import aiofiles

logger = logging.getLogger(__name__)

@dataclass
class StorageConfig:
    """Configuration for storage system."""
    default_provider: str
    providers: Dict[str, Dict[str, Any]]
    routing_rules: list[Dict[str, Any]]
    max_file_size: int = 100 * 1024 * 1024  # 100MB default
    allowed_content_types: set[str] = None
    
    def __post_init__(self):
        if self.allowed_content_types is None:
            self.allowed_content_types = {
                'image/jpeg', 'image/png', 'image/webp', 'image/gif',
                'video/mp4', 'video/webm', 'video/quicktime',
                'audio/mpeg', 'audio/wav', 'audio/ogg',
                'text/plain', 'application/json', 'text/markdown',
                'application/octet-stream'  # For model files
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
    created_at: datetime = None
    
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
        content: Union[bytes, AsyncIterator[bytes]],
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Upload content and return public URL or storage reference.
        
        Args:
            key: Storage key (must be validated before calling)
            content: File content as bytes or async iterator
            content_type: MIME type (must be validated)
            metadata: Optional metadata dictionary
            
        Returns:
            Public URL or storage reference
            
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
        self,
        key: str,
        content_type: str,
        expires_in: timedelta = timedelta(hours=1)
    ) -> Dict[str, Any]:
        """Generate presigned URL for direct client uploads."""
        pass
    
    @abstractmethod
    async def get_presigned_download_url(
        self,
        key: str,
        expires_in: timedelta = timedelta(hours=1)
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
    async def get_metadata(self, key: str) -> Dict[str, Any]:
        """Get file metadata (size, modified date, etc.)."""
        pass
```

### 2. Storage Manager

```python
class StorageManager:
    """Central storage coordinator handling provider selection and routing."""
    
    def __init__(self, config: StorageConfig):
        self.providers: Dict[str, StorageProvider] = {}
        self.default_provider = config.default_provider
        self.routing_rules = config.routing_rules
        self.config = config
        
    def _validate_storage_key(self, key: str) -> str:
        """Validate and sanitize storage key to prevent path traversal."""
        # Remove any path traversal attempts
        if '..' in key or key.startswith('/') or '\\' in key:
            raise SecurityException(f"Invalid storage key: {key}")
            
        # Sanitize key components
        key_parts = key.split('/')
        sanitized_parts = []
        
        for part in key_parts:
            # Remove dangerous characters, keep alphanumeric, hyphens, underscores
            sanitized = re.sub(r'[^a-zA-Z0-9._-]', '', part)
            if not sanitized:
                raise SecurityException(f"Invalid key component: {part}")
            sanitized_parts.append(sanitized)
            
        return '/'.join(sanitized_parts)
        
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
        content: Union[bytes, AsyncIterator[bytes]],
        artifact_type: str,
        content_type: str,
        tenant_id: Optional[str] = None,
        board_id: Optional[str] = None
    ) -> ArtifactReference:
        """Store artifact with comprehensive validation and error handling."""
        
        try:
            # Validate content type
            self._validate_content_type(content_type)
            
            # Validate content size if it's bytes
            if isinstance(content, bytes):
                self._validate_file_size(len(content))
            
            # Generate and validate storage key
            key = self._generate_storage_key(
                artifact_id, artifact_type, tenant_id, board_id
            )
            validated_key = self._validate_storage_key(key)
            
            # Select provider based on routing rules
            provider_name = self._select_provider(artifact_type, content)
            if provider_name not in self.providers:
                raise StorageException(f"Provider not found: {provider_name}")
                
            provider = self.providers[provider_name]
            
            # Prepare metadata
            metadata = {
                'artifact_id': artifact_id,
                'artifact_type': artifact_type,
                'tenant_id': tenant_id,
                'board_id': board_id,
                'uploaded_at': datetime.utcnow().isoformat(),
                'content_type': content_type
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
                created_at=datetime.utcnow()
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
        content: Union[bytes, AsyncIterator[bytes]], 
        content_type: str, 
        metadata: Dict[str, Any],
        max_retries: int = 3
    ) -> str:
        """Upload with exponential backoff retry logic."""
        import asyncio
        
        for attempt in range(max_retries):
            try:
                return await provider.upload(key, content, content_type, metadata)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                    
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Upload attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s")
                await asyncio.sleep(wait_time)
```

### 3. Provider Implementations

#### Local Filesystem Provider
```python
# packages/backend/src/boards/storage/implementations/local.py
class LocalStorageProvider(StorageProvider):
    """Local filesystem storage for development and self-hosted with security."""
    
    def __init__(self, base_path: Path, public_url_base: Optional[str] = None):
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
        except ValueError:
            raise SecurityException(f"Path traversal detected: {key}")
            
        return file_path
        
    async def upload(self, key: str, content: Union[bytes, AsyncIterator[bytes]], 
                    content_type: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        try:
            file_path = self._get_safe_file_path(key)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle both bytes and async iterator content
            if isinstance(content, bytes):
                # Use async file I/O for better performance
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(content)
            else:
                # Stream async iterator content
                async with aiofiles.open(file_path, 'wb') as f:
                    async for chunk in content:
                        await f.write(chunk)
            
            # Store metadata atomically
            if metadata:
                try:
                    metadata_path = file_path.with_suffix(file_path.suffix + '.meta')
                    metadata_json = json.dumps(metadata, indent=2)
                    
                    async with aiofiles.open(metadata_path, 'w') as f:
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
            encoded_key = quote(key, safe='/')
            return f"{self.public_url_base.rstrip('/')}/{encoded_key}"
        else:
            return f"file://{self.base_path / key}"
```

#### Supabase Storage Provider
```python
# packages/backend/src/boards/storage/implementations/supabase.py
from supabase import create_client, AsyncClient
import asyncio

class SupabaseStorageProvider(StorageProvider):
    """Supabase storage with integrated auth, CDN, and proper async patterns."""
    
    def __init__(self, url: str, key: str, bucket: str):
        # Use async client for proper async operations
        self.client: AsyncClient = create_client(url, key)
        self.bucket = bucket
        self.url = url
        
    async def upload(self, key: str, content: Union[bytes, AsyncIterator[bytes]], 
                    content_type: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        try:
            # Handle streaming content for large files
            if isinstance(content, bytes):
                file_content = content
            else:
                # Collect async iterator into bytes (consider streaming for very large files)
                chunks = []
                async for chunk in content:
                    chunks.append(chunk)
                file_content = b''.join(chunks)
            
            # Use async Supabase client methods
            response = await self.client.storage.from_(self.bucket).upload(
                path=key,
                file=file_content,
                file_options={
                    'content-type': content_type,
                    'metadata': metadata or {},
                    'upsert': False  # Prevent accidental overwrites
                }
            )
            
            if response.error:
                error_msg = str(response.error)
                logger.error(f"Supabase upload failed for {key}: {error_msg}")
                
                # Handle specific error types
                if 'already exists' in error_msg.lower():
                    raise StorageException(f"File already exists: {key}")
                elif 'storage quota' in error_msg.lower():
                    raise StorageException(f"Storage quota exceeded")
                else:
                    raise StorageException(f"Upload failed: {error_msg}")
            
            # Get public URL - use async method if available
            try:
                public_url = await self.client.storage.from_(self.bucket).get_public_url(key)
            except AttributeError:
                # Fallback to sync method if async not available
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
            response = await self.client.storage.from_(self.bucket).download(key)
            if response.error:
                raise StorageException(f"Download failed: {response.error}")
            return response.data
        except Exception as e:
            logger.error(f"Failed to download {key} from Supabase: {e}")
            raise StorageException(f"Download failed: {e}") from e
            
    async def get_presigned_upload_url(
        self, 
        key: str, 
        content_type: str, 
        expires_in: timedelta = timedelta(hours=1)
    ) -> Dict[str, Any]:
        """Generate presigned URL for direct client uploads."""
        try:
            response = await self.client.storage.from_(self.bucket).create_signed_upload_url(
                path=key,
                expires_in=int(expires_in.total_seconds())
            )
            
            if response.error:
                raise StorageException(f"Failed to create signed URL: {response.error}")
                
            return {
                'url': response.data['signedURL'],
                'fields': {},  # Supabase doesn't use form fields like S3
                'expires_at': (datetime.utcnow() + expires_in).isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to create presigned upload URL for {key}: {e}")
            raise StorageException(f"Presigned URL creation failed: {e}") from e
```

## Storage Key Hierarchy

### Key Structure
```
{tenant_id}/{artifact_type}/{board_id}/{artifact_id}_{timestamp}_{uuid}/{variant}
```

### Key Generation with Collision Prevention
```python
import uuid
from datetime import datetime

class StorageManager:
    # ... other methods ...
    
    def _generate_storage_key(
        self, 
        artifact_id: str, 
        artifact_type: str, 
        tenant_id: Optional[str] = None, 
        board_id: Optional[str] = None,
        variant: str = "original"
    ) -> str:
        """Generate hierarchical storage key with collision prevention."""
        
        # Use tenant_id or default
        tenant = tenant_id or "default"
        
        # Add timestamp and UUID for uniqueness
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        unique_suffix = str(uuid.uuid4())[:8]
        
        if board_id:
            # Board-scoped artifact
            return f"{tenant}/{artifact_type}/{board_id}/{artifact_id}_{timestamp}_{unique_suffix}/{variant}"
        else:
            # Global artifact (like LoRA models)
            return f"{tenant}/{artifact_type}/{artifact_id}_{timestamp}_{unique_suffix}/{variant}"
            
    def _select_provider(self, artifact_type: str, content: Union[bytes, AsyncIterator[bytes]]) -> str:
        """Select storage provider based on routing rules."""
        content_size = len(content) if isinstance(content, bytes) else 0
        
        for rule in self.routing_rules:
            condition = rule.get('condition', {})
            
            # Check artifact type condition
            if 'artifact_type' in condition:
                if condition['artifact_type'] != artifact_type:
                    continue
                    
            # Check size condition  
            if 'size_gt' in condition:
                size_limit = self._parse_size(condition['size_gt'])
                if content_size <= size_limit:
                    continue
                    
            # If all conditions match, return this provider
            return rule['provider']
            
        # Return default if no rules match
        return self.default_provider
        
    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '100MB' to bytes."""
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
```

### Examples
```
# User-generated image in board (with collision prevention)
default/image/board_123/artifact_456_20241230143000_a1b2c3d4/original.png
default/image/board_123/artifact_456_20241230143000_a1b2c3d4/thumbnail.webp

# LoRA model files  
default/model/lora_789_20241230143001_e5f6g7h8/weights.safetensors
default/model/lora_789_20241230143001_e5f6g7h8/config.json

# Training data
tenant_abc/dataset/training_001_20241230143002_i9j0k1l2/img_001.jpg

# Temporary generation assets (auto-cleanup after 24h)
temp/generation_xyz/input_mask.png
```

### Temporary File Cleanup
```python
class TempFileCleanup:
    """Background service for cleaning up temporary files."""
    
    def __init__(self, storage_manager: StorageManager, ttl_hours: int = 24):
        self.storage_manager = storage_manager
        self.ttl = timedelta(hours=ttl_hours)
        self.cleanup_interval = timedelta(hours=1)
        
    async def start_cleanup_service(self):
        """Start background cleanup task."""
        while True:
            try:
                await self.cleanup_expired_files()
            except Exception as e:
                logger.error(f"Cleanup service error: {e}")
            await asyncio.sleep(self.cleanup_interval.total_seconds())
            
    async def cleanup_expired_files(self):
        """Remove temporary files older than TTL."""
        cutoff_time = datetime.utcnow() - self.ttl
        
        for provider_name, provider in self.storage_manager.providers.items():
            try:
                # List files in temp/ hierarchy
                temp_files = await self._list_temp_files(provider)
                
                for file_info in temp_files:
                    if file_info['modified'] < cutoff_time:
                        await provider.delete(file_info['key'])
                        logger.debug(f"Cleaned up temp file: {file_info['key']}")
                        
            except Exception as e:
                logger.warning(f"Cleanup failed for provider {provider_name}: {e}")
                
    async def _list_temp_files(self, provider: StorageProvider) -> list[Dict[str, Any]]:
        """List files in temp/ hierarchy with metadata."""
        # Implementation would depend on provider capabilities
        # This is a simplified version
        return []
```

## Configuration System

### Storage Configuration
```yaml
# storage.yaml
storage:
  default_provider: "supabase"
  
  providers:
    local:
      type: "local"
      config:
        base_path: "/var/boards/storage"
        public_url_base: "http://localhost:8000/storage"
        
    supabase:
      type: "supabase"  
      config:
        url: "${SUPABASE_URL}"
        key: "${SUPABASE_ANON_KEY}"
        bucket: "boards-artifacts"
        
    s3:
      type: "s3"
      config:
        bucket: "boards-prod-artifacts"
        region: "us-west-2"
        access_key_id: "${AWS_ACCESS_KEY_ID}"
        secret_access_key: "${AWS_SECRET_ACCESS_KEY}"
        
  routing_rules:
    # Large video files go to S3 for cost efficiency
    - condition: 
        artifact_type: "video"
        size_gt: "100MB"
      provider: "s3"
      
    # LoRA models use dedicated storage
    - condition:
        artifact_type: "model"
      provider: "supabase"
      
    # Default rule
    - provider: "supabase"
    
  # Cleanup configuration
  cleanup:
    temp_file_ttl_hours: 24
    cleanup_interval_hours: 1
    max_cleanup_batch_size: 1000
```

## Security and Access Control

### Access Patterns
1. **Public Assets**: Thumbnails, public board artifacts
2. **Private Assets**: User-generated content with access control  
3. **Temporary Assets**: Short-lived generation intermediates
4. **Authenticated Assets**: Require valid session/token

### Security Features
- **Presigned URLs**: Time-limited access without exposing credentials
- **Content Validation**: MIME type checking and malware scanning hooks
- **Access Logging**: Audit trail for all storage operations
- **Encryption**: At-rest encryption for sensitive content
- **CORS Configuration**: Proper cross-origin policies

### Authorization Integration
```python
class AuthorizedStorageManager(StorageManager):
    """Storage manager with built-in authorization checks."""
    
    async def get_download_url(
        self,
        artifact_id: str,
        user_id: str,
        session_token: str
    ) -> str:
        # Check user permissions for the artifact's board
        if not await self.auth_service.can_access_artifact(
            user_id, artifact_id, session_token
        ):
            raise UnauthorizedException("Access denied")
            
        artifact_ref = await self.get_artifact_reference(artifact_id)
        provider = self.providers[artifact_ref.storage_provider]
        
        return await provider.get_presigned_download_url(
            artifact_ref.storage_key,
            expires_in=timedelta(hours=1)
        )
```

## Performance Considerations

### Caching Strategy
- **CDN Integration**: CloudFlare/CloudFront for public assets
- **Local Cache**: Redis-backed cache for frequently accessed metadata
- **Thumbnail Generation**: Async background processing with cache warming
- **Compression**: WebP/AVIF for images, optimized codecs for video

### Scalability Features
- **Multipart Uploads**: For large files (videos, models)
- **Background Processing**: Async thumbnail/preview generation
- **Batch Operations**: Efficient bulk uploads/downloads
- **Connection Pooling**: Reuse connections to cloud providers

### Monitoring and Metrics
```python
@dataclass
class StorageMetrics:
    """Storage operation metrics for monitoring."""
    
    operations_count: Dict[str, int]
    bytes_transferred: Dict[str, int] 
    error_rates: Dict[str, float]
    latency_percentiles: Dict[str, Dict[str, float]]
    storage_utilization: Dict[str, int]
```

## Migration and Backup

### Data Migration
- **Provider Migration**: Move artifacts between storage backends
- **Schema Evolution**: Handle changes to storage key structure  
- **Batch Processing**: Efficient migration of large datasets
- **Rollback Support**: Safe migration with rollback capabilities

### Backup Strategy
- **Automatic Backups**: Scheduled full and incremental backups
- **Cross-Provider Replication**: Mirror critical data across providers
- **Point-in-Time Recovery**: Restore to specific timestamps
- **Disaster Recovery**: Multi-region backup distribution

## Plugin Development

### Custom Provider Interface
```python
class CustomStorageProvider(StorageProvider):
    """Example custom provider implementation."""
    
    def __init__(self, **config):
        # Initialize with custom configuration
        self.config = config
        self.client = self._create_client()
        
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'CustomStorageProvider':
        """Factory method for configuration-based initialization."""
        return cls(**config)
        
    def _create_client(self):
        # Custom client initialization logic
        pass
```

### Registration System
```python
# Custom provider registration
storage_manager.register_provider("custom", CustomStorageProvider.from_config({
    'endpoint': 'https://api.custom-storage.com',
    'api_key': os.getenv('CUSTOM_STORAGE_KEY')
}))
```

## Error Handling and Resilience

### Error Types
- **StorageException**: Base exception for all storage errors
- **ProviderUnavailableException**: Provider service issues
- **InsufficientStorageException**: Quota/space limitations
- **AccessDeniedException**: Authorization failures
- **CorruptionException**: Data integrity issues

### Resilience Features
- **Retry Logic**: Exponential backoff for transient failures
- **Circuit Breaker**: Prevent cascade failures across providers
- **Fallback Providers**: Automatic failover to backup storage
- **Health Checks**: Monitor provider availability and performance

## Implementation Roadmap

### Phase 1: Core Infrastructure ✅
- [x] Implement base StorageProvider interface
- [x] Create LocalStorageProvider for development
- [x] Build StorageManager with basic routing
- [x] Add configuration system

### Phase 2: Cloud Integration  
- [x] Implement SupabaseStorageProvider
- [ ] Add S3StorageProvider
- [ ] Add GCSStorageProvider (moved from Phase 2)
- [x] Implement presigned URL generation
- [x] Add security and access control

### Phase 3: Advanced Features
- [ ] Add caching and performance optimizations
- [ ] Implement migration and backup tools
- [ ] Create monitoring and metrics system
- [ ] Add plugin registration system

### Phase 4: Production Ready
- [ ] Add comprehensive error handling
- [ ] Implement resilience features
- [ ] Performance testing and optimization
- [ ] Documentation and examples

## Job Integration

The storage system integrates with the job system for temporary file management:

```python
# packages/backend/src/boards/jobs/tasks.py
class GenerationJob:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.temp_files = []
    
    async def cleanup(self):
        """Clean up temp files when job completes/fails."""
        for temp_key in self.temp_files:
            await storage_manager.delete_temp_file(temp_key)
```

This approach provides better control over temporary file lifecycle compared to time-based cleanup.

This storage architecture provides a robust, scalable, and extensible foundation for handling all artifact storage needs in the Boards system while maintaining simplicity for basic use cases and power for advanced deployments.
