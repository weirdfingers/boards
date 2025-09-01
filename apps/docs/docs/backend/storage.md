# Storage System

The Boards storage system provides a pluggable architecture for handling artifact storage across multiple backends. It supports local development, cloud deployment, and custom storage providers.

## Overview

The storage system handles diverse content types:
- **Images**: PNG, JPG, WebP, GIF
- **Videos**: MP4, WebM, MOV  
- **Audio**: MP3, WAV, OGG
- **Models**: LoRA weights, checkpoints
- **Metadata**: JSON, text files

## Quick Start

### Basic Usage

```python
from boards.storage import create_development_storage

# Create storage manager for development
storage = create_development_storage()

# Store an artifact
artifact_ref = await storage.store_artifact(
    artifact_id="my_image",
    content=image_bytes,
    artifact_type="image", 
    content_type="image/png",
    tenant_id="user123",
    board_id="board456"
)

# Get download URL
download_url = await storage.get_download_url(
    artifact_ref.storage_key,
    artifact_ref.storage_provider
)
```

### Production Configuration

```python
from boards.storage import create_storage_manager

# Load from configuration file
storage = create_storage_manager("config/storage.yaml")

# Or create with direct config
from boards.storage import StorageConfig

config = StorageConfig(
    default_provider="supabase",
    providers={
        "supabase": {
            "type": "supabase",
            "config": {
                "url": "https://your-project.supabase.co",
                "key": "your-anon-key",
                "bucket": "artifacts"
            }
        }
    },
    routing_rules=[{"provider": "supabase"}]
)

storage = create_storage_manager(storage_config=config)
```

## Storage Providers

### Local Storage
For development and self-hosted deployments:

```python
from boards.storage.implementations import LocalStorageProvider

provider = LocalStorageProvider(
    base_path="/var/boards/storage",
    public_url_base="https://your-domain.com/storage"
)
```

### Supabase Storage  
Integrated with Supabase auth and CDN:

```python
from boards.storage.implementations import SupabaseStorageProvider

provider = SupabaseStorageProvider(
    url="https://your-project.supabase.co",
    key="your-anon-key", 
    bucket="artifacts"
)
```

## Configuration

### Environment Variables

```bash
# Default provider
BOARDS_STORAGE_DEFAULT_PROVIDER=supabase

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
BOARDS_STORAGE_SUPABASE_BUCKET=artifacts

# Local storage
BOARDS_STORAGE_LOCAL_BASE_PATH=/var/boards/storage
BOARDS_STORAGE_LOCAL_PUBLIC_URL_BASE=https://your-domain.com/storage

# File limits
BOARDS_STORAGE_MAX_FILE_SIZE=104857600  # 100MB
```

### YAML Configuration

```yaml
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
        
  routing_rules:
    # Large files go to specialized storage
    - condition: 
        artifact_type: "video"
        size_gt: "100MB"
      provider: "s3"
      
    # Default to Supabase
    - provider: "supabase"
    
  max_file_size: 1073741824  # 1GB
```

## Storage Key Structure

Files are organized hierarchically:
```
{tenant_id}/{artifact_type}/{board_id}/{artifact_id}_{timestamp}_{uuid}/{variant}
```

Examples:
```
# User image in board
user123/image/board456/avatar_20241230143000_a1b2c3d4/original.png
user123/image/board456/avatar_20241230143000_a1b2c3d4/thumbnail.webp

# LoRA model  
user123/model/lora_789_20241230143001_e5f6g7h8/weights.safetensors
user123/model/lora_789_20241230143001_e5f6g7h8/config.json
```

## Security Features

- **Path traversal protection**: Keys are validated and sanitized
- **Content type validation**: Only allowed MIME types accepted
- **File size limits**: Configurable maximum file sizes
- **Presigned URLs**: Time-limited access without exposing credentials

## Integration with Jobs

Temporary files are managed through the job system:

```python
class GenerationJob:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.temp_files = []
    
    async def cleanup(self):
        """Clean up temp files when job completes/fails."""
        for temp_key in self.temp_files:
            await storage_manager.delete_temp_file(temp_key)
```

## Error Handling

The storage system provides specific exception types:

```python
from boards.storage import (
    StorageException,      # Base storage error
    SecurityException,     # Security/validation error  
    ValidationException    # Content validation error
)

try:
    await storage.store_artifact(...)
except SecurityException as e:
    # Handle security violation
    pass
except ValidationException as e:
    # Handle content validation error
    pass  
except StorageException as e:
    # Handle general storage error
    pass
```

## Performance Considerations

- **Streaming uploads**: Supports async iterators for large files
- **Retry logic**: Automatic retry with exponential backoff
- **Provider routing**: Route different content types to optimal storage
- **Presigned URLs**: Direct client uploads bypass server bandwidth