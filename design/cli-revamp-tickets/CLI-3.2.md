# Create Web Service Overlay Compose

## Description

Create a separate overlay file (`compose.web.yaml`) that defines the web service with a **production build** (no hot-reload, no volume mounts). This enables optional loading of the web service, which is needed for app-dev mode (Phase 4) where users may want to run the frontend locally instead of in Docker.

The overlay approach using Docker Compose allows:
- Base compose file runs backend services (api, worker, db, cache)
- Web overlay adds frontend service as a production-built container when needed
- CLI loads appropriate combination based on flags (`--app-dev` skips the overlay)

This is preparation for the `--app-dev` flag in Phase 4.

**Key difference from previous dev mode:** The web service now uses a production build via `Dockerfile.web` with no source mounts or hot-reload.

## Dependencies

None (can be done in parallel with CLI-3.1)

## Files to Create/Modify

- Create `/packages/cli-launcher/template-sources/compose.web.yaml`

## Testing

### Overlay Loading Test
```bash
# Test with base only (backend services)
docker compose -f compose.yaml up -d
docker compose ps

# Should show: db, cache, api, worker (no web)

# Test with overlay (all services)
docker compose -f compose.yaml -f compose.web.yaml up -d
docker compose ps

# Should show: db, cache, api, worker, web
```

### Web Service Test
```bash
# Start with web overlay
docker compose -f compose.yaml -f compose.web.yaml up -d

# Verify web service builds
docker compose images | grep web

# Verify web service is healthy
docker compose ps web

# Test web access
curl http://localhost:3300
# Should return Next.js page
```

### Production Build Test
```bash
# Verify web service uses production build (not dev mode)
docker compose logs web
# Should NOT show: "pnpm dev" or "Fast Refresh"
# Should show: "Server listening on port 3000" or similar production output
```

### Dependency Test
```bash
# Verify web depends on api
docker compose -f compose.yaml -f compose.web.yaml up -d

# Check that web waits for api
docker compose logs web | grep -i "waiting"
# Should show it waited for api health check
```

## Acceptance Criteria

### File Structure

- [ ] New file created: `/packages/cli-launcher/template-sources/compose.web.yaml`
- [ ] File contains only web service definition
- [ ] Uses proper YAML overlay syntax (services key at root)

### Web Service Definition

- [ ] Service named `web`
- [ ] Build configuration:
  ```yaml
  build:
    context: ./web
    dockerfile: ../Dockerfile.web
  ```
- [ ] Environment variables from `web/.env` file
- [ ] Additional environment variable:
  ```yaml
  environment:
    - INTERNAL_API_URL=http://api:8800
  ```
- [ ] No volume mounts (production build in image)
- [ ] No custom command (uses default from Dockerfile.web)
- [ ] Depends on api service:
  ```yaml
  depends_on:
    api:
      condition: service_healthy
  ```
- [ ] Port mapping:
  ```yaml
  ports:
    - "${WEB_PORT:-3300}:3000"
  ```
- [ ] Health check:
  ```yaml
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:3000/"]
    interval: 5s
    timeout: 3s
    retries: 50
  ```
- [ ] Network connection:
  ```yaml
  networks:
    - internal
  ```

### Integration

- [ ] Works when loaded after base compose
- [ ] No conflicts with base compose services
- [ ] Uses same network as backend services
- [ ] Environment variables interpolate correctly

### Testing

- [ ] Loading base only works (4 services)
- [ ] Loading base + overlay works (5 services)
- [ ] Web service can communicate with api service
- [ ] Production build works correctly (no hot-reload)
- [ ] Health checks pass
- [ ] Ports configurable via WEB_PORT env var

### Cleanup

- [ ] No duplicate definitions from base file
- [ ] Minimal, focused file (only web service)
- [ ] Properly formatted YAML
- [ ] Comments explain overlay purpose
