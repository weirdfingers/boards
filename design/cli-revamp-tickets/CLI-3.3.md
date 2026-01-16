# Merge Dev Overlay into Base Compose

## Description

Consolidate necessary settings from `compose.dev.yaml` into the main `compose.yaml` file and delete the dev overlay. This simplifies the system by removing the prod/dev distinction.

Changes involve:
- Keeping the pre-built image approach (no source mounts)
- Removing `--reload` flags (no hot-reload with pre-built images)
- Keeping `PYTHONUNBUFFERED=1` for better log visibility
- Deleting the `compose.dev.yaml` file entirely

After this change, the backend runs with pre-built images in a simple, streamlined mode (no hot-reload). Hot-reload is only available for frontend via `--app-dev` mode (Phase 4).

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

### No Hot Reload Test
```bash
# Start services
docker compose up -d

# Verify NO --reload flag
docker compose logs api | grep -i reload
# Should NOT show: "Uvicorn running with --reload"

# Verify using pre-built image (not source mounts)
docker compose config | grep -A10 "api:" | grep volumes
# Should NOT show: ./api:/app (no source code mount)
# Should only show: config and storage mounts
```

### Log Visibility Test
```bash
# Verify PYTHONUNBUFFERED is set for better logs
docker compose exec api printenv | grep PYTHONUNBUFFERED
# Should show: PYTHONUNBUFFERED=1

# Verify logs are visible in real-time
docker compose logs api -f
# Should show logs immediately without buffering
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

- [ ] Command does NOT include --reload flag:
  ```yaml
  command: ["uvicorn", "boards.api.app:app", "--host", "0.0.0.0", "--port", "8800"]
  ```
- [ ] Environment includes PYTHONUNBUFFERED for log visibility:
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
- [ ] No source code mounts (backend code in pre-built image)

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
- [ ] Core features work:
  - [ ] Logs visible in real-time (PYTHONUNBUFFERED)
  - [ ] Health checks pass
  - [ ] Migrations work
  - [ ] Config changes reflected (restart required)
  - [ ] No hot-reload (expected with pre-built images)
- [ ] No regressions in functionality

### Documentation

- [ ] Comments in compose.yaml explain dev mode
- [ ] README updated to remove prod/dev distinction
- [ ] Notes added about hot reload limitations with pre-built images
- [ ] Example .env files updated if needed

### Note on No Hot Reload

The system intentionally does NOT provide hot-reload with pre-built Docker images. This is a design decision:
- [ ] Document that there is no backend hot reload (by design)
- [ ] Explain that config files can be changed (requires container restart)
- [ ] Clarify that this CLI is for using Boards, not developing it
- [ ] For toolkit development itself, use the monorepo dev setup (not CLI)
- [ ] Frontend hot-reload is available via `--app-dev` flag (Phase 4)

### Quality

- [ ] compose.yaml is well-organized
- [ ] No duplicate settings
- [ ] YAML properly formatted
- [ ] Comments explain non-obvious settings
