# Create Production Backend Dockerfile

## Description

Create an optimized production Dockerfile for the backend package that supports both API server and worker roles. This Dockerfile will be used to build and publish pre-built Docker images to GHCR (GitHub Container Registry) and Docker Hub, eliminating the need for users to build the backend locally.

The Dockerfile should:
- Use Python 3.12-slim as the base image
- Use `uv` for fast dependency management
- Support multi-stage builds for minimal image size
- Create a non-root user for security
- Support both `api` and `worker` commands via command override
- Include health checks
- Be optimized for layer caching

This is a foundational ticket that enables the rest of Phase 1 (Docker image publishing) and Phase 3 (using pre-built images in compose files).

## Dependencies

None

## Files to Create/Modify

- Create `/packages/backend/Dockerfile`

## Testing

### Build Test
```bash
cd packages/backend
docker build -t boards-backend:test .
```

### Run API Test
```bash
# Start with API command
docker run -p 8800:8800 \
  -e BOARDS_DATABASE_URL=postgresql://user:pass@host/db \
  -e BOARDS_REDIS_URL=redis://host:6379/0 \
  boards-backend:test \
  uvicorn boards.api.app:app --host 0.0.0.0 --port 8800

# Verify health endpoint
curl http://localhost:8800/health
```

### Run Worker Test
```bash
# Start with worker command
docker run \
  -e BOARDS_DATABASE_URL=postgresql://user:pass@host/db \
  -e BOARDS_REDIS_URL=redis://host:6379/0 \
  boards-backend:test \
  dramatiq-gevent boards.workers.actors:broker --processes 1 --threads 50

# Verify worker process is running
docker exec <container_id> pgrep -f dramatiq
```

### Size Test
```bash
# Verify image size is reasonable (< 500MB)
docker images boards-backend:test
```

### Multi-stage Build Test
```bash
# Verify no build artifacts in final image
docker run boards-backend:test ls -la /app
```

## Acceptance Criteria

- [ ] Dockerfile builds successfully without errors
- [ ] Final image size is under 500MB
- [ ] Image uses Python 3.12-slim base
- [ ] Dependencies installed with `uv sync --frozen --no-dev`
- [ ] Non-root user created (uid 1000, username: boards)
- [ ] Image supports both API and worker commands via CMD override
- [ ] Health check endpoint works (curl to /health succeeds)
- [ ] Both uvicorn and dramatiq-gevent commands execute successfully
- [ ] Layer caching works (re-build without changes is fast)
- [ ] All application code copied to /app directory
- [ ] Alembic migrations included in image
