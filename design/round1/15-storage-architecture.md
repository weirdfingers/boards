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

### 1. Storage Abstraction Layer

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, AsyncIterator
from pathlib import Path
from datetime import datetime, timedelta

class StorageProvider(ABC):
    """Abstract base class for all storage providers."""
    
    @abstractmethod
    async def upload(
        self, 
        key: str, 
        content: bytes | AsyncIterator[bytes],
        content_type: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Upload content and return public URL or storage reference."""
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
        
    def register_provider(self, name: str, provider: StorageProvider):
        """Register a storage provider."""
        self.providers[name] = provider
        
    async def store_artifact(
        self,
        artifact_id: str,
        content: bytes,
        artifact_type: str,
        tenant_id: Optional[str] = None,
        board_id: Optional[str] = None
    ) -> ArtifactReference:
        """Store artifact with appropriate provider selection."""
        
        # Generate storage key with hierarchy
        key = self._generate_storage_key(
            artifact_id, artifact_type, tenant_id, board_id
        )
        
        # Select provider based on routing rules
        provider_name = self._select_provider(artifact_type, content)
        provider = self.providers[provider_name]
        
        # Store the content
        storage_url = await provider.upload(
            key=key,
            content=content,
            content_type=self._get_content_type(artifact_type),
            metadata={
                'artifact_id': artifact_id,
                'artifact_type': artifact_type,
                'tenant_id': tenant_id,
                'board_id': board_id,
                'uploaded_at': datetime.utcnow().isoformat()
            }
        )
        
        return ArtifactReference(
            artifact_id=artifact_id,
            storage_key=key,
            storage_provider=provider_name,
            storage_url=storage_url,
            content_type=self._get_content_type(artifact_type)
        )
```

### 3. Provider Implementations

#### Local Filesystem Provider
```python
class LocalStorageProvider(StorageProvider):
    """Local filesystem storage for development and self-hosted."""
    
    def __init__(self, base_path: Path, public_url_base: str = None):
        self.base_path = Path(base_path)
        self.public_url_base = public_url_base
        self.base_path.mkdir(parents=True, exist_ok=True)
        
    async def upload(self, key: str, content: bytes, content_type: str, metadata=None):
        file_path = self.base_path / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_path.write_bytes(content)
        
        # Store metadata as sidecar file
        if metadata:
            metadata_path = file_path.with_suffix(file_path.suffix + '.meta')
            metadata_path.write_text(json.dumps(metadata))
            
        return self._get_public_url(key)
```

#### Supabase Storage Provider
```python
class SupabaseStorageProvider(StorageProvider):
    """Supabase storage with integrated auth and CDN."""
    
    def __init__(self, url: str, key: str, bucket: str):
        self.client = create_client(url, key)
        self.bucket = bucket
        
    async def upload(self, key: str, content: bytes, content_type: str, metadata=None):
        response = self.client.storage.from_(self.bucket).upload(
            path=key,
            file=content,
            file_options={
                'content-type': content_type,
                'metadata': metadata or {}
            }
        )
        
        if response.error:
            raise StorageException(f"Upload failed: {response.error}")
            
        return self.client.storage.from_(self.bucket).get_public_url(key)
```

## Storage Key Hierarchy

### Key Structure
```
{tenant_id}/{artifact_type}/{board_id}/{artifact_id}/{variant}
```

### Examples
```
# User-generated image in board
default/image/board_123/artifact_456/original.png
default/image/board_123/artifact_456/thumbnail.webp

# LoRA model files  
default/model/lora_789/weights.safetensors
default/model/lora_789/config.json

# Training data
tenant_abc/dataset/training_001/img_001.jpg

# Temporary generation assets
temp/generation_xyz/input_mask.png
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

### Phase 1: Core Infrastructure
- [ ] Implement base StorageProvider interface
- [ ] Create LocalStorageProvider for development
- [ ] Build StorageManager with basic routing
- [ ] Add configuration system

### Phase 2: Cloud Integration  
- [ ] Implement SupabaseStorageProvider
- [ ] Add S3StorageProvider
- [ ] Implement presigned URL generation
- [ ] Add security and access control

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

This storage architecture provides a robust, scalable, and extensible foundation for handling all artifact storage needs in the Boards system while maintaining simplicity for basic use cases and power for advanced deployments.