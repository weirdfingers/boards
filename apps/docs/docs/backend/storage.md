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

## Generator Integration

The storage system is automatically integrated with the generator execution context. When generators produce artifacts from external providers (Replicate, OpenAI, etc.), the system automatically downloads and re-uploads them to permanent storage.

### How It Works

1. **Generator produces artifact**: Calls `context.store_image_result()` with provider's temporary URL
2. **Download from provider**: System downloads content from the temporary URL
3. **Upload to storage**: Content is uploaded to configured storage backend
4. **Permanent URL returned**: Generator receives an artifact with permanent storage URL
5. **Database persistence**: Storage URL is saved to the `generations` table

### Example: Image Generation Flow

```python
from boards.generators.base import BaseGenerator, GeneratorExecutionContext

class MyImageGenerator(BaseGenerator):
    async def generate(self, inputs, context: GeneratorExecutionContext):
        # Call external provider (e.g., Replicate)
        provider_output_url = await self.call_provider(inputs)

        # Store via context - this downloads and re-uploads automatically
        image_artifact = await context.store_image_result(
            storage_url=provider_output_url,  # Temporary provider URL
            format="png",
            width=1024,
            height=1024,
        )

        # image_artifact.storage_url is now a permanent URL in your storage
        return MyOutput(image=image_artifact)
```

### Why Download and Re-Upload?

Provider URLs (Replicate, OpenAI, etc.) are **temporary** and typically expire within hours or days. The storage integration:

- **Ensures permanence**: Artifacts remain accessible indefinitely
- **Tenant isolation**: Files are organized by tenant and board
- **Cost optimization**: Enables CDN integration and caching strategies
- **Security control**: Applies your storage policies and access controls
- **Backup support**: Integrates with your backup/disaster recovery plans

### Storage Key Structure

Artifacts are stored with hierarchical keys that provide organization and prevent collisions:

```
{tenant_id}/{artifact_type}/{board_id}/{artifact_id}_{timestamp}_{uuid}/original
```

Example:
```
abc123/image/def456/gen_789_20250124120000_a1b2c3d4/original
```

This structure enables:
- Tenant data isolation
- Type-based routing (e.g., videos to high-bandwidth storage)
- Board-level organization
- Collision prevention via timestamp + UUID
- Future variant support (thumbnails, compressed versions)

### Context Methods

The `GeneratorExecutionContext` provides storage methods for all artifact types:

```python
# Store image
image = await context.store_image_result(
    storage_url=url,
    format="png",
    width=1024,
    height=1024
)

# Store video
video = await context.store_video_result(
    storage_url=url,
    format="mp4",
    width=1920,
    height=1080,
    duration=30.5,
    fps=30.0
)

# Store audio
audio = await context.store_audio_result(
    storage_url=url,
    format="mp3",
    duration=120.0,
    sample_rate=44100,
    channels=2
)
```

### Artifact Resolution

When generators need to use previously generated artifacts as inputs, use `resolve_artifact()`:

```python
async def generate(self, inputs, context: GeneratorExecutionContext):
    # Resolve input artifact to local file path
    input_image_path = await context.resolve_artifact(inputs.source_image)

    # Pass to provider SDK
    result = await provider_sdk.process(input_path=input_image_path)

    # Store result
    return await context.store_image_result(...)
```

The `resolve_artifact()` method:
- Downloads the artifact if it's a remote URL
- Returns local file paths as-is
- Caches downloads in temp directory
- Handles cleanup automatically

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
    # Handle security violation (path traversal, forbidden chars)
    pass
except ValidationException as e:
    # Handle content validation error (size limits, content type)
    pass
except StorageException as e:
    # Handle general storage error (upload failure, network issues)
    pass
```

### Generator Error Handling

When using context methods, wrap in try/except to handle storage failures gracefully:

```python
try:
    artifact = await context.store_image_result(
        storage_url=provider_url,
        format="png",
        width=1024,
        height=1024
    )
except httpx.HTTPError as e:
    # Failed to download from provider
    raise ValueError(f"Could not download image from provider: {e}")
except StorageException as e:
    # Failed to upload to storage
    raise ValueError(f"Could not store image: {e}")
```

## Performance Considerations

- **Streaming uploads**: Supports async iterators for large files
- **Retry logic**: Automatic retry with exponential backoff
- **Provider routing**: Route different content types to optimal storage
- **Presigned URLs**: Direct client uploads bypass server bandwidth
