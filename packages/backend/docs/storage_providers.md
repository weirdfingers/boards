# Storage Providers

Boards supports multiple storage providers for artifact storage through a pluggable architecture. This document describes the available providers and their configuration options.

## Available Providers

### Local Storage

The local filesystem provider is ideal for development and testing.

**Features:**
- Stores files on the local filesystem
- Optional public URL serving for development
- No external dependencies
- Fast for small to medium files

**Configuration:**
```yaml
providers:
  local:
    type: "local"
    config:
      base_path: "/tmp/boards/storage"  # Storage directory
      public_url_base: "http://localhost:8000/storage"  # Optional: base URL for serving files
```

**Use Cases:**
- Local development
- Testing environments
- Small deployments without cloud requirements

---

### AWS S3

The S3 provider offers robust cloud storage with optional CloudFront CDN integration.

**Features:**
- Scalable cloud storage
- Server-side encryption
- CloudFront CDN integration
- Presigned URLs for direct client uploads
- Multiple storage classes for cost optimization
- Cross-region replication support

**Dependencies:**
```bash
pip install boto3 aioboto3
# or
pip install boards-backend[storage-s3]
```

**Configuration:**
```yaml
providers:
  s3:
    type: "s3"
    config:
      bucket: "my-boards-bucket"               # Required: S3 bucket name
      region: "us-east-1"                      # AWS region
      aws_access_key_id: "${AWS_ACCESS_KEY_ID}"  # AWS credentials
      aws_secret_access_key: "${AWS_SECRET_ACCESS_KEY}"
      aws_session_token: "${AWS_SESSION_TOKEN}"  # Optional: for temporary credentials
      endpoint_url: "https://s3.amazonaws.com"  # Optional: custom endpoint (for S3-compatible services)
      cloudfront_domain: "d123.cloudfront.net"  # Optional: CloudFront distribution
      upload_config:                           # Optional: S3 upload parameters
        ServerSideEncryption: "AES256"
        StorageClass: "STANDARD"
        # Or use KMS encryption:
        # ServerSideEncryption: "aws:kms"
        # SSEKMSKeyId: "arn:aws:kms:region:account:key/key-id"
```

**Environment Variables:**
- `AWS_ACCESS_KEY_ID`: AWS access key (if not in config)
- `AWS_SECRET_ACCESS_KEY`: AWS secret key (if not in config)
- `AWS_SESSION_TOKEN`: Temporary session token (optional)
- `AWS_REGION`: Default region (if not in config)

**Use Cases:**
- Production deployments
- Large file storage
- Global content distribution with CloudFront
- Compliance requirements (encryption, audit trails)
- Integration with other AWS services

---

### Google Cloud Storage (GCS)

The GCS provider integrates with Google Cloud Platform and Cloud CDN.

**Features:**
- Google Cloud native storage
- Automatic encryption at rest
- Cloud CDN integration
- Multi-regional storage options
- IAM integration with fine-grained permissions
- Lifecycle management policies

**Dependencies:**
```bash
pip install google-cloud-storage
# or
pip install boards-backend[storage-gcs]
```

**Configuration:**
```yaml
providers:
  gcs:
    type: "gcs"
    config:
      bucket: "my-boards-gcs-bucket"           # Required: GCS bucket name
      project_id: "my-gcp-project"             # GCP project ID
      # Authentication options (choose one):
      credentials_path: "/path/to/service-account-key.json"  # Service account key file
      credentials_json: "${GCP_SERVICE_ACCOUNT_JSON}"        # Service account JSON as string
      # Or use default credentials (gcloud, environment, etc.)
      cdn_domain: "cdn.example.com"            # Optional: Cloud CDN domain
      upload_config:                           # Optional: GCS upload parameters
        cache_control: "public, max-age=3600"
        predefined_acl: "bucket-owner-read"
```

**Authentication Methods:**

1. **Service Account Key File:**
   ```yaml
   credentials_path: "/path/to/service-account-key.json"
   ```

2. **Service Account JSON String:**
   ```yaml
   credentials_json: "${GCP_SERVICE_ACCOUNT_JSON}"
   ```

3. **Default Credentials (recommended for production):**
   - Google Cloud SDK (`gcloud auth application-default login`)
   - Environment variable `GOOGLE_APPLICATION_CREDENTIALS`
   - Compute Engine/GKE service accounts
   - Cloud Run/Cloud Functions default credentials

**Use Cases:**
- Google Cloud Platform deployments
- Integration with other GCP services
- Global content distribution
- Machine learning workflows (easy integration with AI Platform)
- Multi-regional applications

---

### Supabase Storage

The Supabase provider integrates with Supabase's storage and authentication system.

**Features:**
- Integrated with Supabase auth
- Built-in CDN
- Row Level Security (RLS) integration
- Real-time subscriptions
- Automatic image transformations

**Dependencies:**
```bash
pip install supabase
```

**Configuration:**
```yaml
providers:
  supabase:
    type: "supabase"
    config:
      url: "${SUPABASE_URL}"                   # Supabase project URL
      key: "${SUPABASE_ANON_KEY}"              # Supabase anon key
      bucket: "boards-artifacts"               # Storage bucket name
```

**Use Cases:**
- Supabase-based applications
- Real-time collaborative features
- Integrated authentication and storage
- Rapid prototyping

## Provider Selection and Routing

Boards supports intelligent provider selection through routing rules:

```yaml
routing_rules:
  # Large files go to S3
  - condition:
      size_gt: "50MB"
    provider: "s3"
  
  # Images go to GCS with CDN
  - condition:
      artifact_type: "image"
    provider: "gcs"
  
  # Videos go to S3 for CloudFront streaming
  - condition:
      artifact_type: "video"
    provider: "s3"
  
  # Default fallback
  - provider: "local"
```

## Best Practices

### Security

1. **Never hardcode credentials** in configuration files
2. **Use environment variables** or secure credential management
3. **Enable encryption at rest** for sensitive data
4. **Use IAM roles** instead of access keys when possible
5. **Implement bucket policies** for additional security

### Performance

1. **Choose regions close to your users** for better latency
2. **Use CDN/CloudFront** for frequently accessed content
3. **Consider storage classes** for cost optimization
4. **Implement caching** at the application level
5. **Use presigned URLs** for direct client uploads

### Cost Optimization

1. **Use appropriate storage classes** (Standard, IA, Glacier, etc.)
2. **Implement lifecycle policies** for automatic data management
3. **Monitor usage and costs** regularly
4. **Use compression** for text-based content
5. **Clean up unused files** periodically

### Development vs Production

**Development:**
```yaml
default_provider: "local"
providers:
  local:
    type: "local"
    config:
      base_path: "/tmp/boards/storage"
```

**Production:**
```yaml
default_provider: "s3"
providers:
  s3:
    type: "s3"
    config:
      bucket: "prod-boards-artifacts"
      cloudfront_domain: "cdn.example.com"
  gcs:
    type: "gcs"
    config:
      bucket: "prod-boards-media"
      cdn_domain: "media.example.com"
```

## Migration Between Providers

When migrating between providers, consider:

1. **Gradual migration** using routing rules
2. **Data consistency** during the migration
3. **URL updates** for existing references
4. **Testing** with non-critical data first
5. **Backup strategies** for data safety

Example gradual migration:
```yaml
# Phase 1: Route new uploads to S3, keep existing on local
routing_rules:
  - condition:
      artifact_type: "image"
    provider: "s3"
  - provider: "local"  # Existing files

# Phase 2: Migrate all new uploads to S3
routing_rules:
  - provider: "s3"
```

## Troubleshooting

### Common Issues

1. **Authentication errors**: Check credentials and permissions
2. **Bucket access denied**: Verify bucket policies and IAM permissions
3. **Network timeouts**: Check network connectivity and endpoint URLs
4. **Large file uploads**: Consider chunked uploads and timeout settings
5. **CDN cache issues**: Check cache headers and purge policies

### Debugging

Enable debug logging:
```python
import logging
logging.getLogger("boards.storage").setLevel(logging.DEBUG)
```

### Monitoring

Key metrics to monitor:
- Upload success rates
- Download latency
- Storage costs
- Error rates by provider
- CDN hit rates (if applicable)