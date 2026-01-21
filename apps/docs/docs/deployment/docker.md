---
title: Docker Deployment
description: Deploy Boards using Docker Compose and container images.
sidebar_position: 2
---

# Docker Deployment

Deploy Boards using Docker Compose with pre-built container images from GitHub Container Registry (GHCR) or Docker Hub.

## Architecture Overview

A Boards deployment consists of four services:

| Service | Image | Purpose |
|---------|-------|---------|
| **api** | `ghcr.io/weirdfingers/boards-backend` | GraphQL API server (uvicorn) |
| **worker** | `ghcr.io/weirdfingers/boards-backend` | Background job processor |
| **db** | `postgres:16` | PostgreSQL database |
| **cache** | `redis:7` | Job queue and caching |

The API and worker use the same image but run different commands. The backend image is published to both GHCR (recommended) and Docker Hub:

- **GHCR**: `ghcr.io/weirdfingers/boards-backend:latest`
- **Docker Hub**: `cdiddy/weirdfingers-boards-backend:latest`

:::note Frontend Image
The frontend requires a custom build since it needs your environment-specific configuration baked in at build time. See [Frontend Deployment](./frontend.md) for details.
:::

## Quick Start

### 1. Create Project Directory

```bash
mkdir my-boards-app && cd my-boards-app
```

### 2. Create Docker Compose File

Create `compose.yaml`:

```yaml
name: boards

services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: boards
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-changeme}
      POSTGRES_DB: boards
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U boards -d boards"]
      interval: 5s
      timeout: 5s
      retries: 20
    networks:
      - internal

  cache:
    image: redis:7
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - cache-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 20
    networks:
      - internal

  api:
    image: ghcr.io/weirdfingers/boards-backend:${BACKEND_VERSION:-latest}
    command: ["uvicorn", "boards.api.app:app", "--host", "0.0.0.0", "--port", "8800"]
    environment:
      - BOARDS_DATABASE_URL=postgresql://boards:${POSTGRES_PASSWORD:-changeme}@db:5432/boards
      - BOARDS_REDIS_URL=redis://cache:6379/0
      - BOARDS_GENERATORS_CONFIG_PATH=/app/config/generators.yaml
      - BOARDS_STORAGE_CONFIG_PATH=/app/config/storage_config.yaml
      - PYTHONUNBUFFERED=1
    env_file:
      - .env
    volumes:
      - ./config:/app/config:ro
      - ./data/storage:/app/data/storage
      - ./extensions:/app/extensions:ro
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_healthy
    ports:
      - "${API_PORT:-8800}:8800"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8800/health"]
      interval: 30s
      timeout: 3s
      retries: 50
    networks:
      - internal

  worker:
    image: ghcr.io/weirdfingers/boards-backend:${BACKEND_VERSION:-latest}
    command: ["boards-worker", "--log-level", "info", "--processes", "1", "--threads", "1"]
    environment:
      - BOARDS_DATABASE_URL=postgresql://boards:${POSTGRES_PASSWORD:-changeme}@db:5432/boards
      - BOARDS_REDIS_URL=redis://cache:6379/0
      - BOARDS_GENERATORS_CONFIG_PATH=/app/config/generators.yaml
      - BOARDS_STORAGE_CONFIG_PATH=/app/config/storage_config.yaml
      - BOARDS_INTERNAL_API_URL=http://api:8800
      - PYTHONUNBUFFERED=1
    env_file:
      - .env
    volumes:
      - ./config:/app/config:ro
      - ./data/storage:/app/data/storage
      - ./extensions:/app/extensions:ro
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_healthy
    networks:
      - internal

networks:
  internal:
    driver: bridge

volumes:
  db-data:
  cache-data:
```

### 3. Create Environment File

Create `.env`:

```bash
# Database
POSTGRES_PASSWORD=your-secure-password-here

# Image version (optional, defaults to latest)
BACKEND_VERSION=latest

# API port (optional, defaults to 8800)
API_PORT=8800

# Auth provider (see Authentication docs)
BOARDS_AUTH_PROVIDER=none

# Generator API keys (JSON format)
BOARDS_GENERATOR_API_KEYS={"fal": "your-fal-key", "openai": "your-openai-key"}
```

### 4. Create Configuration Files

Create the config directory and files:

```bash
mkdir -p config data/storage extensions
```

Create `config/generators.yaml`:

```yaml
generators:
  - class: boards.generators.fal.flux.FluxProGenerator
    enabled: true
  - class: boards.generators.openai.dalle.DallE3Generator
    enabled: true
```

Create `config/storage_config.yaml`:

```yaml
default_provider: local

providers:
  local:
    type: local
    base_path: /app/data/storage
    public_url_base: http://localhost:8800/storage
```

### 5. Start Services

```bash
docker compose up -d
```

Verify services are running:

```bash
docker compose ps
docker compose logs -f api
```

The API will be available at `http://localhost:8800`.

## Production Configuration

### Using Managed Services

For production, consider using managed database and cache services:

```yaml
services:
  api:
    image: ghcr.io/weirdfingers/boards-backend:${BACKEND_VERSION:-latest}
    environment:
      # Use managed PostgreSQL (see Database docs)
      - BOARDS_DATABASE_URL=postgresql://user:pass@your-managed-db.com:5432/boards?sslmode=require
      # Use managed Redis (e.g., ElastiCache, Upstash)
      - BOARDS_REDIS_URL=rediss://user:pass@your-managed-redis.com:6379/0
    # ... rest of config
```

See the [Database](./database/managed-postgresql.md) documentation for provider-specific guides.

### Scaling Workers

Scale workers to handle more concurrent jobs:

```bash
# Scale to 3 worker instances
docker compose up -d --scale worker=3
```

Or configure in `compose.yaml`:

```yaml
services:
  worker:
    # ... existing config
    deploy:
      replicas: 3
```

### External Storage

For production, use cloud storage instead of local:

```yaml
# config/storage_config.yaml
default_provider: s3

providers:
  s3:
    type: s3
    bucket: my-boards-bucket
    region: us-east-1
    # Credentials from environment: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
```

See [Storage Configuration](./storage.md) for all providers.

### Reverse Proxy

Place a reverse proxy (nginx, Caddy, Traefik) in front for SSL termination:

```yaml
services:
  proxy:
    image: caddy:2
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy-data:/data
    depends_on:
      - api
    networks:
      - internal

volumes:
  caddy-data:
```

Example `Caddyfile`:

```
boards.example.com {
    reverse_proxy api:8800
}
```

## Common Operations

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f worker
```

### Restart Services

```bash
# Restart all
docker compose restart

# Restart specific service
docker compose restart api
```

### Update Images

```bash
# Pull latest images
docker compose pull

# Recreate containers with new images
docker compose up -d
```

### Database Migrations

Migrations run automatically on API startup. To run manually:

```bash
docker compose exec api python -m boards.db.migrate
```

### Backup Database

```bash
docker compose exec db pg_dump -U boards boards > backup.sql
```

### Restore Database

```bash
docker compose exec -T db psql -U boards boards < backup.sql
```

## Troubleshooting

### API Won't Start

Check health of dependencies:

```bash
docker compose ps
docker compose logs db
docker compose logs cache
```

Verify database connection:

```bash
docker compose exec api python -c "from boards.db import engine; print(engine.url)"
```

### Worker Not Processing Jobs

Check worker logs:

```bash
docker compose logs -f worker
```

Verify Redis connection:

```bash
docker compose exec cache redis-cli ping
```

### Out of Disk Space

Clean up old images and volumes:

```bash
docker system prune -a
docker volume prune
```

## Next Steps

- [Configuration Reference](./configuration.md) - All environment variables and config files
- [Storage Configuration](./storage.md) - Set up S3, GCS, or Supabase storage
- [Authentication](./authentication.md) - Configure auth providers
- [Frontend Deployment](./frontend.md) - Deploy the web frontend
- [Monitoring](./monitoring.md) - Logging and health checks
