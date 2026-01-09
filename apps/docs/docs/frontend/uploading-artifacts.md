---
title: Uploading Artifacts
description: Guide to uploading images, videos, audio, and text files to boards
sidebar_position: 4
---

# Uploading Artifacts

Boards supports direct artifact uploads, allowing users to bring their own content into boards alongside AI-generated artifacts. This feature enables workflows like:

- Uploading reference images for image-to-image generation
- Adding source videos for video editing
- Importing audio files for processing
- Uploading text files as prompts or inputs

## Supported Artifact Types

The upload system supports the following artifact types:

- **Images**: JPEG, PNG, GIF, WebP, BMP, SVG
- **Videos**: MP4, QuickTime (MOV), AVI, WebM, MPEG, MKV
- **Audio**: MP3, WAV, OGG, WebM, M4A
- **Text**: Plain text, Markdown, JSON, HTML, CSV

## Upload Methods

Boards provides two upload methods:

### 1. File Upload (Multipart)

Direct file upload from the user's device via REST API endpoint.

**Endpoint**: `POST /api/uploads/artifact`

**Advantages**:
- Progress tracking support
- Large file handling
- Works with all file types

### 2. URL Download

Download artifacts from external URLs via GraphQL mutation.

**Mutation**: `uploadArtifact`

**Advantages**:
- No local file needed
- Works with web-hosted content
- Useful for automation

## Using the Multi-Upload Hook

The `@weirdfingers/boards` package provides a `useMultiUpload` hook for React applications that supports uploading multiple files concurrently:

```typescript
import { useMultiUpload, ArtifactType } from '@weirdfingers/boards';

function MyComponent() {
  const { uploadMultiple, uploads, isUploading, overallProgress } = useMultiUpload();

  const handleFilesUpload = async (files: File[]) => {
    try {
      const requests = files.map(file => ({
        boardId: 'your-board-id',
        artifactType: ArtifactType.IMAGE,
        source: file, // Can be File or URL string
        userDescription: 'My uploaded image',
      }));

      const results = await uploadMultiple(requests);
      console.log('Uploads complete:', results);
    } catch (err) {
      console.error('Upload failed:', err);
    }
  };

  return (
    <div>
      <input
        type="file"
        multiple
        onChange={(e) => {
          const files = Array.from(e.target.files || []);
          handleFilesUpload(files);
        }}
        disabled={isUploading}
      />
      {isUploading && <progress value={overallProgress} max={100} />}

      {/* Show individual upload progress */}
      {uploads.map(upload => (
        <div key={upload.id}>
          {upload.fileName}: {upload.status} ({upload.progress}%)
        </div>
      ))}
    </div>
  );
}
```

### Hook API

#### Parameters

```typescript
interface MultiUploadRequest {
  boardId: string;               // UUID of the target board
  artifactType: ArtifactType;    // Type of artifact (IMAGE, VIDEO, AUDIO, TEXT)
  source: File | string;         // File object or URL string
  userDescription?: string;      // Optional description
  parentGenerationId?: string;   // Optional parent generation UUID
}
```

#### Return Value

```typescript
interface MultiUploadHook {
  uploadMultiple: (requests: MultiUploadRequest[]) => Promise<MultiUploadResult[]>;
  uploads: UploadItem[];           // Array of upload items with progress
  isUploading: boolean;            // True while any upload in progress
  overallProgress: number;         // Overall progress (0-100)
  clearUploads: () => void;        // Clear upload history
  cancelUpload: (uploadId: string) => void;  // Cancel a specific upload
}

interface MultiUploadResult {
  id: string;           // UUID of created generation
  status: string;       // 'completed' or 'failed'
  storageUrl: string;   // URL to access the artifact
  artifactType: ArtifactType;
  generatorName: string;
}

interface UploadItem {
  id: string;
  file: File | string;
  fileName: string;
  status: 'pending' | 'uploading' | 'completed' | 'failed';
  progress: number;
  result?: MultiUploadResult;
  error?: Error;
}
```

## Upload UI Component

The Baseboards example app includes a full-featured upload component with:

- Drag-and-drop support
- File picker
- URL input
- Clipboard paste (for images)
- Progress indication
- Error handling

See [apps/baseboards/src/components/boards/UploadArtifact.tsx](https://github.com/weirdfingers/boards/blob/main/apps/baseboards/src/components/boards/UploadArtifact.tsx) for the complete implementation.

## Security Features

The upload system includes multiple security measures:

### SSRF Protection

URL uploads are validated to prevent Server-Side Request Forgery (SSRF) attacks:

- ✅ Allowed: `http://` and `https://` public URLs
- ❌ Blocked: `localhost`, `127.0.0.1`, private IP ranges (10.x.x.x, 192.168.x.x, 172.16-31.x.x)
- ❌ Blocked: Link-local addresses (169.254.x.x, AWS metadata endpoint)
- ❌ Blocked: Non-HTTP schemes (`file://`, `ftp://`, etc.)

### File Type Validation

- MIME type validation ensures uploaded content matches the declared artifact type
- File extensions are checked against an allowlist
- Content-Type headers are verified

### File Size Limits

Default maximum file size is 100MB (configurable via `BOARDS_MAX_UPLOAD_SIZE`).

### Filename Sanitization

All filenames are sanitized to prevent:
- Path traversal attacks (`../`, absolute paths)
- Null byte injection
- Dangerous characters (`<>:"|?*`)

## File Size Configuration

Configure the maximum upload size in your backend `.env`:

```bash
# Allow uploads up to 500MB
BOARDS_MAX_UPLOAD_SIZE=524288000
```

Allowed extensions are configured in [packages/backend/src/boards/config.py](https://github.com/weirdfingers/boards/blob/main/packages/backend/src/boards/config.py).

## GraphQL Mutation

For URL-based uploads via GraphQL:

```graphql
mutation UploadArtifactFromUrl($input: UploadArtifactInput!) {
  uploadArtifact(input: $input) {
    id
    status
    storageUrl
    artifactType
    generatorName
  }
}
```

**Variables**:
```json
{
  "input": {
    "boardId": "550e8400-e29b-41d4-a716-446655440000",
    "artifactType": "IMAGE",
    "fileUrl": "https://example.com/image.jpg",
    "userDescription": "Reference image",
    "parentGenerationId": null
  }
}
```

## REST API

For file uploads via REST:

```bash
curl -X POST http://localhost:8088/api/uploads/artifact \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "board_id=550e8400-e29b-41d4-a716-446655440000" \
  -F "artifact_type=image" \
  -F "file=@/path/to/image.jpg" \
  -F "user_description=My upload"
```

**Response**:
```json
{
  "id": "650e8400-e29b-41d4-a716-446655440001",
  "status": "completed",
  "storageUrl": "http://localhost:8088/api/storage/...",
  "artifactType": "image",
  "generatorName": "user-upload-image"
}
```

## Generator Naming Convention

Uploaded artifacts are stored as Generation records with a special `generator_name` pattern:

- `user-upload-image` - Uploaded images
- `user-upload-video` - Uploaded videos
- `user-upload-audio` - Uploaded audio files
- `user-upload-text` - Uploaded text files

This allows uploads to integrate seamlessly with the generation lineage system.

## Storage

Uploaded artifacts are stored using the configured storage provider:

- **Local**: Files stored in `BOARDS_STORAGE_LOCAL_BASE_PATH`
- **S3**: Uploaded to configured S3 bucket
- **Supabase Storage**: Uploaded to Supabase bucket
- **Google Cloud Storage**: Uploaded to GCS bucket

See the [Storage documentation](../backend/storage.md) for configuration details.

## Error Handling

The upload system provides detailed error messages for common issues:

| Error | Cause | Solution |
|-------|-------|----------|
| "URL not allowed" | SSRF protection blocked the URL | Use a public HTTP/HTTPS URL |
| "Invalid file type" | MIME type doesn't match artifact type | Ensure file type matches declared type |
| "File size exceeds maximum" | File too large | Reduce file size or increase limit |
| "Permission denied" | User can't upload to board | User must be board owner or editor |
| "Board not found" | Invalid board ID | Check board ID is correct |

## Best Practices

1. **Client-side validation**: Validate file size and type before upload to improve UX
2. **Progress feedback**: Always show upload progress for files >1MB
3. **Error recovery**: Allow users to retry failed uploads
4. **Cancellation**: Implement upload cancellation for large files
5. **Chunked uploads**: For very large files (>100MB), consider implementing chunked uploads

## Example: Drag-and-Drop Upload

```typescript
import { useMultiUpload, ArtifactType } from '@weirdfingers/boards';
import { useCallback, useState } from 'react';

function DragDropUpload({ boardId }: { boardId: string }) {
  const { uploadMultiple, isUploading, overallProgress } = useMultiUpload();
  const [dragActive, setDragActive] = useState(false);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      // Determine artifact type from file MIME type
      const requests = files.map(file => {
        let artifactType = ArtifactType.IMAGE;
        if (file.type.startsWith('video/')) {
          artifactType = ArtifactType.VIDEO;
        } else if (file.type.startsWith('audio/')) {
          artifactType = ArtifactType.AUDIO;
        }

        return { boardId, artifactType, source: file };
      });

      await uploadMultiple(requests);
    }
  }, [uploadMultiple, boardId]);

  return (
    <div
      onDrop={handleDrop}
      onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
      onDragLeave={() => setDragActive(false)}
      className={dragActive ? 'border-blue-500' : 'border-gray-300'}
      style={{ border: '2px dashed', padding: '2rem', textAlign: 'center' }}
    >
      {isUploading ? (
        <div>Uploading... {Math.round(overallProgress)}%</div>
      ) : (
        <div>Drag and drop files here</div>
      )}
    </div>
  );
}
```

## Related Documentation

- [Storage Configuration](../backend/storage.md) - Configure storage backends
- [Generator UI](./generator-ui.md) - Use uploaded artifacts as generator inputs
- [Artifact Types](../generators/artifact-types.md) - Learn about artifact types
