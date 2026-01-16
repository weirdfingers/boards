# Merge Dev Overlay into Base Compose

## Description

Consolidate the development mode settings from `compose.dev.yaml` into the main `compose.yaml` file, making dev mode the only mode. This simplifies the system by removing the prod/dev distinction.

Changes involve:
- Moving dev-specific volume mounts to base compose
- Moving dev-specific commands (--reload flags) to base compose
- Moving dev-specific environment variables to base compose
- Deleting the `compose.dev.yaml` file entirely

After this change, the backend always runs in development mode with hot reload and source mounts (though using the pre-built Docker image from CLI-3.1).

## Dependencies

- CLI-3.1 (Base compose must already use Docker image)

## Files to Create/Modify

- Modify `/packages/cli-launcher/template-sources/compose.yaml`
- Delete `/packages/cli-launcher/template-sources/compose.dev.yaml`

## Testing

### Single File Test
```bash
# Start with base compose only (no overlay)
docker compose up -d

# Verify all services start
docker compose ps
# Should show all services running and healthy
```

### Hot Reload Test
```bash
# Start services
docker compose up -d

# Verify --reload flag is active
docker compose logs api | grep -i reload
# Should show: "Uvicorn running with --reload"

# Make change to trigger reload (if possible with image)
# Note: Hot reload may not work with pre-built image
# This is expected behavior - document in ticket
```

### Development Features Test
```bash
# Verify PYTHONUNBUFFERED is set
docker compose exec api printenv | grep PYTHONUNBUFFERED
# Should show: PYTHONUNBUFFERED=1

# Verify config mounts are read-write (not read-only)
docker compose exec api touch /app/config/test.txt
# Should succeed (no permission denied)
```

### No Build Context Test
```bash
# Verify no local code mounts for backend
docker compose config | grep -A5 "api:" | grep volumes
# Should NOT show: ./api:/app (source code mount)
# Should show: ./config:/app/config (config mount only)
```

### Comparison Test
```bash
# Before: had compose.yaml + compose.dev.yaml
# After: only compose.yaml

# Verify old dev behavior preserved:
# - Logs visible (PYTHONUNBUFFERED)
# - Health checks work
# - API responds quickly
```

## Acceptance Criteria

### API Service Updates

- [ ] Command includes --reload flag:
  ```yaml
  command: ["uvicorn", "boards.api.app:app", "--host", "0.0.0.0", "--port", "8800", "--reload"]
  ```
- [ ] Environment includes PYTHONUNBUFFERED:
  ```yaml
  environment:
    - PYTHONUNBUFFERED=1
  ```
- [ ] Config mounts remain (from CLI-3.1):
  ```yaml
  volumes:
    - ./config:/app/config:ro
    - ./data/storage:/app/data/storage
  ```
- [ ] No source code mounts (backend code in image)

### Worker Service Updates

- [ ] Environment includes PYTHONUNBUFFERED:
  ```yaml
  environment:
    - PYTHONUNBUFFERED=1
  ```
- [ ] Same volume mounts as api
- [ ] Command unchanged (no reload for worker)

### File Cleanup

- [ ] `compose.dev.yaml` file deleted
- [ ] No references to compose.dev.yaml in other files
- [ ] Template preparation script updated (if needed)

### Validation

- [ ] Services start with only base compose file
- [ ] No need to specify -f compose.dev.yaml
- [ ] All development features work:
  - [ ] Logs visible in real-time
  - [ ] Health checks pass
  - [ ] Migrations work
  - [ ] Config changes reflected (restart required)
- [ ] No regressions in functionality

### Documentation

- [ ] Comments in compose.yaml explain dev mode
- [ ] README updated to remove prod/dev distinction
- [ ] Notes added about hot reload limitations with pre-built images
- [ ] Example .env files updated if needed

### Note on Hot Reload

Since we're using pre-built Docker images (CLI-3.1), hot reload of backend code is not possible. This is expected:
- [ ] Document that backend hot reload requires rebuilding image
- [ ] Explain that config files can still be changed (requires restart)
- [ ] Clarify that this is for running, not developing the toolkit itself
- [ ] For toolkit development, use local build setup (not CLI)

### Quality

- [ ] compose.yaml is well-organized
- [ ] No duplicate settings
- [ ] YAML properly formatted
- [ ] Comments explain non-obvious settings
