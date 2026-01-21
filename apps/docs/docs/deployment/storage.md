---
title: Storage Configuration
description: Configure object storage for generated artifacts.
sidebar_position: 6
---

# Storage Configuration

Boards stores generated images, videos, audio, and other artifacts in object storage. This guide covers configuring the supported storage providers.

## Supported Providers

| Provider | Best For |
|----------|----------|
| **Local** | Development, single-server deployments |
| **S3** | AWS deployments, S3-compatible services |
| **GCS** | Google Cloud deployments |
| **Supabase** | When using Supabase for auth/database |

## Configuration File

Create `storage_config.yaml`:

```yaml
# Default provider for all operations
default_provider: s3

# Provider configurations
providers:
  local:
    type: local
    base_path: /app/data/storage
    public_url_base: http://localhost:8800/storage

  s3:
    type: s3
    bucket: my-boards-bucket
    region: us-east-1

  gcs:
    type: gcs
    bucket: my-boards-bucket
    project: my-gcp-project

  supabase:
    type: supabase
    bucket: boards-storage

# Optional: File limits
max_file_size: 104857600  # 100MB
```

Set the config path:

```bash
BOARDS_STORAGE_CONFIG_PATH=/app/config/storage_config.yaml
```

## Local Storage

For development and single-server deployments:

```yaml
providers:
  local:
    type: local
    base_path: /app/data/storage
    public_url_base: http://localhost:8800/storage
```

Mount a volume in Docker:

```yaml
services:
  api:
    volumes:
      - ./data/storage:/app/data/storage
```

:::warning
Local storage doesn't work with multiple API replicas unless using a shared filesystem (NFS, EFS).
:::

## Amazon S3

### Configuration

```yaml
providers:
  s3:
    type: s3
    bucket: my-boards-bucket
    region: us-east-1
    # Optional: custom endpoint for S3-compatible services
    # endpoint_url: https://s3.example.com
```

### Environment Variables

```bash
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1  # Optional if set in config
```

### S3 Bucket Setup

Create a bucket with appropriate permissions:

```bash
aws s3 mb s3://my-boards-bucket --region us-east-1
```

Bucket policy for public read access to artifacts:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-boards-bucket/*"
    }
  ]
}
```

For private access (signed URLs), no bucket policy is needed.

### CORS Configuration

Enable CORS for browser uploads:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST"],
    "AllowedOrigins": ["https://your-app.com"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

### IAM Policy

Minimum permissions for the application:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-boards-bucket",
        "arn:aws:s3:::my-boards-bucket/*"
      ]
    }
  ]
}
```

### S3-Compatible Services

Boards works with S3-compatible services. Set the endpoint:

```yaml
providers:
  s3:
    type: s3
    bucket: my-bucket
    region: auto
    endpoint_url: https://s3.example.com
```

**Compatible services:**
- MinIO
- Cloudflare R2
- DigitalOcean Spaces
- Backblaze B2
- Wasabi

## Google Cloud Storage

### Configuration

```yaml
providers:
  gcs:
    type: gcs
    bucket: my-boards-bucket
    project: my-gcp-project
```

### Authentication

Set the service account credentials:

```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

Or in Kubernetes with Workload Identity, the credentials are automatic.

### Bucket Setup

```bash
gsutil mb -p my-gcp-project -l us-central1 gs://my-boards-bucket
```

### Public Access

For public artifacts:

```bash
gsutil iam ch allUsers:objectViewer gs://my-boards-bucket
```

### CORS Configuration

```bash
cat > cors.json << EOF
[
  {
    "origin": ["https://your-app.com"],
    "method": ["GET", "PUT", "POST"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
EOF

gsutil cors set cors.json gs://my-boards-bucket
```

### IAM Permissions

Required roles:
- `roles/storage.objectCreator` - Upload files
- `roles/storage.objectViewer` - Read files
- `roles/storage.objectAdmin` - Full access (if deleting files)

## Supabase Storage

### Configuration

```yaml
providers:
  supabase:
    type: supabase
    bucket: boards-storage
```

### Environment Variables

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### Bucket Setup

Create a bucket in Supabase dashboard:

1. Go to **Storage** > **New bucket**
2. Name: `boards-storage`
3. Public: Enable for public artifacts

Or via SQL:

```sql
INSERT INTO storage.buckets (id, name, public)
VALUES ('boards-storage', 'boards-storage', true);
```

### RLS Policies

If using Row Level Security:

```sql
-- Allow authenticated uploads
CREATE POLICY "Allow uploads"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'boards-storage');

-- Allow public reads
CREATE POLICY "Allow public reads"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'boards-storage');
```

## Advanced Configuration

### Routing Rules

Route different artifact types to different providers:

```yaml
default_provider: s3

providers:
  local:
    type: local
    base_path: /app/data/cache
    public_url_base: http://localhost:8800/cache
  s3:
    type: s3
    bucket: my-boards-bucket
    region: us-east-1

routing:
  rules:
    # Cache small files locally
    - match:
        max_size: 1048576  # 1MB
      provider: local
    # Videos always to S3
    - match:
        artifact_type: video
      provider: s3
```

### File Size Limits

```yaml
max_file_size: 104857600  # 100MB in bytes
```

### Allowed Content Types

```yaml
allowed_content_types:
  - image/jpeg
  - image/png
  - image/webp
  - image/gif
  - video/mp4
  - video/webm
  - audio/mpeg
  - audio/wav
  - application/json
```

## CDN Integration

For better performance, serve artifacts through a CDN:

### CloudFront (S3)

1. Create a CloudFront distribution pointing to your S3 bucket
2. Update the public URL:

```yaml
providers:
  s3:
    type: s3
    bucket: my-boards-bucket
    region: us-east-1
    public_url_base: https://d1234567890.cloudfront.net
```

### Cloud CDN (GCS)

1. Create a load balancer with Cloud CDN enabled
2. Point to your GCS bucket as backend
3. Update the public URL in config

## Troubleshooting

### Permission Denied

1. Verify credentials are set correctly
2. Check IAM permissions on the bucket
3. Ensure bucket exists and name is correct

### CORS Errors

1. Configure CORS on the bucket
2. Verify allowed origins match your domain
3. Check browser console for specific error

### Large File Uploads Failing

1. Check `max_file_size` configuration
2. Verify network timeout settings
3. Consider multipart upload for very large files

## Next Steps

- [Docker Deployment](./docker.md) - Configure storage volumes
- [Kubernetes Deployment](./kubernetes.md) - Mount config files
- [Configuration Reference](./configuration.md) - All storage variables
