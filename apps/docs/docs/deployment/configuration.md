---
title: Configuration Reference
description: Environment variables, secrets, and configuration files for Boards deployment.
sidebar_position: 5
---

# Configuration Reference

Complete reference for environment variables and configuration files used to deploy Boards.

## Environment Variables

### Database

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `BOARDS_DATABASE_URL` | Yes | PostgreSQL connection URL | `postgresql://user:pass@host:5432/boards` |

Connection URL supports these query parameters:
- `sslmode=require` - Enable SSL (recommended for managed databases)
- `connect_timeout=10` - Connection timeout in seconds

### Redis

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `BOARDS_REDIS_URL` | Yes | Redis connection URL | `redis://host:6379/0` |

For TLS-enabled Redis (ElastiCache, Upstash), use `rediss://` protocol:
```
rediss://user:password@host:6379/0
```

### Authentication

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `BOARDS_AUTH_PROVIDER` | No | Auth provider to use | `none`, `jwt`, `supabase`, `clerk`, `auth0`, `oidc` |

**Provider-specific variables:**

#### JWT
| Variable | Required | Description |
|----------|----------|-------------|
| `BOARDS_JWT_SECRET` | Yes (if JWT) | Secret key for JWT signing |
| `BOARDS_JWT_ALGORITHM` | No | Algorithm (default: `HS256`) |
| `BOARDS_JWT_ISSUER` | No | Expected token issuer |

#### Supabase
| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Service role key (backend only) |
| `SUPABASE_ANON_KEY` | No | Anonymous key (for frontend) |

#### Clerk
| Variable | Required | Description |
|----------|----------|-------------|
| `CLERK_SECRET_KEY` | Yes | Clerk secret key |
| `CLERK_PUBLISHABLE_KEY` | No | Publishable key (for frontend) |

#### Auth0
| Variable | Required | Description |
|----------|----------|-------------|
| `AUTH0_DOMAIN` | Yes | Auth0 domain |
| `AUTH0_CLIENT_ID` | Yes | Client ID |
| `AUTH0_CLIENT_SECRET` | Yes | Client secret |
| `AUTH0_AUDIENCE` | No | API audience |

#### OIDC (Generic)
| Variable | Required | Description |
|----------|----------|-------------|
| `BOARDS_OIDC_ISSUER` | Yes | OIDC issuer URL |
| `BOARDS_OIDC_CLIENT_ID` | Yes | Client ID |
| `BOARDS_OIDC_CLIENT_SECRET` | No | Client secret |

See [Authentication](./authentication.md) for detailed setup guides.

### Generators

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `BOARDS_GENERATORS_CONFIG_PATH` | No | Path to generators.yaml | `/app/config/generators.yaml` |
| `BOARDS_GENERATOR_API_KEYS` | Yes | JSON object with API keys | `{"fal": "key", "openai": "key"}` |

### Storage

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `BOARDS_STORAGE_CONFIG_PATH` | No | Path to storage_config.yaml | `/app/config/storage_config.yaml` |
| `BOARDS_STORAGE_PROVIDER` | No | Override default provider | `s3`, `gcs`, `supabase`, `local` |

**Provider-specific variables:**

#### S3 / S3-Compatible
| Variable | Required | Description |
|----------|----------|-------------|
| `AWS_ACCESS_KEY_ID` | Yes | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | Yes | AWS secret key |
| `AWS_REGION` | No | AWS region (can also be in config) |

#### Google Cloud Storage
| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | Path to service account JSON |

#### Supabase Storage
| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Service role key |

See [Storage Configuration](./storage.md) for detailed setup.

### Logging

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOARDS_LOG_LEVEL` | No | `info` | Log level: `debug`, `info`, `warning`, `error` |
| `BOARDS_LOG_FORMAT` | No | `console` | Output format: `console`, `json` |

Use `json` format in production for structured logging.

### Worker

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `BOARDS_INTERNAL_API_URL` | No | Internal API URL for worker | `http://api:8800` |

Worker command-line options:
```bash
boards-worker --log-level info --processes 1 --threads 1
```

### Multi-tenancy

| Variable | Required | Description |
|----------|----------|-------------|
| `BOARDS_MULTI_TENANT` | No | Enable multi-tenancy (`true`/`false`) |
| `BOARDS_DEFAULT_TENANT_ID` | No | Default tenant ID for single-tenant mode |

### Security

| Variable | Required | Description |
|----------|----------|-------------|
| `BOARDS_SECRET_KEY` | Recommended | Application secret key |
| `BOARDS_ALLOWED_ORIGINS` | Recommended | CORS allowed origins (comma-separated) |

## Configuration Files

### generators.yaml

Defines which AI generators are available:

```yaml
generators:
  # Fal.ai generators
  - class: boards.generators.fal.flux.FluxProGenerator
    enabled: true
  - class: boards.generators.fal.flux.FluxDevGenerator
    enabled: true

  # OpenAI generators
  - class: boards.generators.openai.dalle.DallE3Generator
    enabled: true

  # Replicate generators
  - class: boards.generators.replicate.flux.FluxProReplicateGenerator
    enabled: false

  # Custom generators (from extensions volume)
  - class: my_generators.custom.MyCustomGenerator
    enabled: true
```

The `class` path is a Python import path. Custom generators should be placed in the `/app/extensions` volume.

### storage_config.yaml

Defines storage providers and routing rules:

```yaml
# Default provider for all storage operations
default_provider: s3

# Available storage providers
providers:
  # Local filesystem (development)
  local:
    type: local
    base_path: /app/data/storage
    public_url_base: http://localhost:8800/storage

  # Amazon S3
  s3:
    type: s3
    bucket: my-boards-bucket
    region: us-east-1
    # Optional: custom endpoint for S3-compatible services
    # endpoint_url: https://s3.example.com

  # Google Cloud Storage
  gcs:
    type: gcs
    bucket: my-boards-bucket
    project: my-gcp-project

  # Supabase Storage
  supabase:
    type: supabase
    bucket: boards-storage

# Optional: Route different artifact types to different providers
routing:
  # Large files to S3, small files to local cache
  rules:
    - match:
        max_size: 1048576  # 1MB
      provider: local
    - match:
        artifact_type: video
      provider: s3

# File size limits
max_file_size: 104857600  # 100MB

# Allowed content types
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

## Environment Variable Precedence

Configuration is loaded in this order (later values override earlier):

1. Default values in code
2. Configuration files (YAML)
3. Environment variables

Environment variables always take precedence over config files.

## Secrets Management

### Development

For local development, use `.env` files:

```bash
# .env
BOARDS_DATABASE_URL=postgresql://boards:password@localhost:5432/boards
BOARDS_REDIS_URL=redis://localhost:6379/0
BOARDS_GENERATOR_API_KEYS={"fal": "your-key"}
```

### Production

For production deployments, use your platform's secrets management:

| Platform | Recommended Solution |
|----------|---------------------|
| Docker Compose | Docker secrets or external secret management |
| Kubernetes | Kubernetes Secrets + External Secrets Operator |
| AWS | Secrets Manager or Parameter Store |
| GCP | Secret Manager |
| Azure | Key Vault |

Example with Kubernetes External Secrets:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: boards-secrets
  namespace: boards
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: boards-secrets
  data:
    - secretKey: database-url
      remoteRef:
        key: boards/production/database-url
    - secretKey: generator-api-keys
      remoteRef:
        key: boards/production/generator-api-keys
```

## Validation

Test your configuration before deploying:

```bash
# Docker Compose
docker compose config

# Kubernetes
kubectl apply --dry-run=client -f boards-k8s.yaml

# Check API health after deployment
curl http://localhost:8800/health
```

## Next Steps

- [Database Configuration](./database/managed-postgresql.md) - Set up PostgreSQL
- [Storage Configuration](./storage.md) - Configure object storage
- [Authentication](./authentication.md) - Set up auth providers
