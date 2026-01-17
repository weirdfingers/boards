# Update Base Compose to Use Docker Image

## Description

Replace the local build context for the backend (`./api`) with the pre-built Docker image from GHCR. This is a foundational change that shifts from building the backend locally to using the published image.

Update the `compose.yaml` file to:
- Use `image:` instead of `build:` for api and worker services
- Reference `ghcr.io/weirdfingers/boards-backend:${BACKEND_VERSION}`
- Add volume mounts for extensibility:
  - `./config:/app/config:ro` - Backend configuration
  - `./data/storage:/app/data/storage` - Generated media persistence
  - `./extensions:/app/extensions:ro` - Custom generators and plugins (NEW)
- Add environment variables for extensibility:
  - `PYTHONPATH=/app:/app/extensions` - Enables loading custom Python modules
  - `BOARDS_GENERATORS_CONFIG_PATH` - Explicit path to generators config
  - `BOARDS_STORAGE_CONFIG_PATH` - Explicit path to storage config
- Preserve health checks and dependencies

This change simplifies the setup for users, ensures everyone runs the same tested backend image, and enables custom generators and plugins to be loaded from the host filesystem without rebuilding Docker images.

## Dependencies

- CLI-1.4 (Published image must be verified as working)

## Files to Create/Modify

- Modify `/packages/cli-launcher/template-sources/compose.yaml`

## Testing

### Local Test
```yaml
# Test updated compose file
cd /path/to/test-project
export BACKEND_VERSION=0.7.0

# Start services
docker compose up -d

# Verify images pulled (not built)
docker compose images
# Should show: ghcr.io/weirdfingers/boards-backend:0.7.0

# Verify services healthy
docker compose ps
# Should show all services healthy

# Check logs for no errors
docker compose logs api worker
```

### Volume Mounts Test
```bash
# Verify config is mounted correctly
docker compose exec api ls -la /app/config
# Should show: generators.yaml, storage_config.yaml

# Verify storage is writable
docker compose exec api touch /app/data/storage/test.txt
ls data/storage/test.txt
# Should exist on host

# Verify extensions directory is mounted
docker compose exec api ls -la /app/extensions
# Should show: generators/ plugins/

# Verify PYTHONPATH allows importing from extensions
docker compose exec api python -c "import sys; print('/app/extensions' in sys.path)"
# Should output: True
```

### Environment Variables Test
```bash
# Verify env vars are passed correctly
docker compose exec api printenv | grep BOARDS_

# Should show:
# BOARDS_DATABASE_URL=...
# BOARDS_REDIS_URL=...
# BOARDS_GENERATORS_CONFIG_PATH=/app/config/generators.yaml
# BOARDS_STORAGE_CONFIG_PATH=/app/config/storage_config.yaml

# Verify PYTHONPATH is set
docker compose exec api printenv PYTHONPATH
# Should show: /app:/app/extensions
```

### Version Override Test
```bash
# Test with different backend version
export BACKEND_VERSION=0.8.0
docker compose up -d

# Verify correct version pulled
docker compose images | grep boards-backend
# Should show 0.8.0
```

### Migration Test
```bash
# Verify migrations still work
docker compose exec api alembic upgrade head

# Check database
docker compose exec db psql -U boards -d boards_dev -c "\dt"
# Should show tables
```

## Acceptance Criteria

### API Service

- [ ] `build:` section removed
- [ ] `image:` line added:
  ```yaml
  image: ghcr.io/weirdfingers/boards-backend:${BACKEND_VERSION:-latest}
  ```
- [ ] Command without --reload flag: `["uvicorn", "boards.api.app:app", "--host", "0.0.0.0", "--port", "8800"]`
- [ ] Volume mounts updated:
  - [ ] `./config:/app/config:ro`
  - [ ] `./data/storage:/app/data/storage`
  - [ ] `./extensions:/app/extensions:ro` (NEW - for custom generators and plugins)
- [ ] Environment variables updated:
  - [ ] All existing BOARDS_* vars preserved
  - [ ] `PYTHONPATH=/app:/app/extensions` (NEW - enables loading custom modules)
  - [ ] `BOARDS_GENERATORS_CONFIG_PATH=/app/config/generators.yaml` (explicit)
  - [ ] `BOARDS_STORAGE_CONFIG_PATH=/app/config/storage_config.yaml` (explicit)
- [ ] Health check unchanged
- [ ] Dependencies unchanged (db, cache)

### Worker Service

- [ ] `build:` section removed
- [ ] `image:` line added (same as api):
  ```yaml
  image: ghcr.io/weirdfingers/boards-backend:${BACKEND_VERSION:-latest}
  ```
- [ ] Command unchanged: `["dramatiq-gevent", "boards.workers.actors:broker", ...]`
- [ ] Volume mounts updated (same as api):
  - [ ] `./config:/app/config:ro`
  - [ ] `./data/storage:/app/data/storage`
  - [ ] `./extensions:/app/extensions:ro` (NEW)
- [ ] Environment variables updated (same as api):
  - [ ] All existing BOARDS_* vars preserved
  - [ ] `PYTHONPATH=/app:/app/extensions` (NEW)
  - [ ] `BOARDS_GENERATORS_CONFIG_PATH=/app/config/generators.yaml` (explicit)
  - [ ] `BOARDS_STORAGE_CONFIG_PATH=/app/config/storage_config.yaml` (explicit)
- [ ] Health check unchanged
- [ ] Dependencies unchanged

### Configuration

- [ ] BACKEND_VERSION environment variable documented
- [ ] Default version set to `latest` or specific version
- [ ] Version can be overridden via docker/.env file

### Other Services

- [ ] DB service unchanged (still postgres:16)
- [ ] Cache service unchanged (still redis:7)
- [ ] Web service unchanged (still builds locally for now - will change in CLI-3.2)
- [ ] Networks unchanged
- [ ] Volumes unchanged

### Validation

- [ ] Services start successfully with new config
- [ ] No build steps occur (only image pulls)
- [ ] All healthchecks pass
- [ ] Migrations run successfully
- [ ] API endpoint accessible
- [ ] Worker processes jobs
- [ ] No regressions in functionality

### Documentation

- [ ] Comment added explaining BACKEND_VERSION variable
- [ ] Example docker/.env updated with BACKEND_VERSION
