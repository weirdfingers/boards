# Update Compose Loading for App-Dev

## Description

Update the compose file loading logic to skip the web overlay when `--app-dev` flag is specified. This causes only backend services (db, cache, api, worker) to start in Docker, leaving the frontend to be run locally by the user.

This is the core implementation of app-dev mode's Docker orchestration.

## Dependencies

- CLI-3.5 (Compose file loading logic must be in place)
- CLI-4.1 (--app-dev flag must exist)

## Files to Create/Modify

- Modify `/packages/cli-launcher/src/commands/up.ts`

## Testing

### Default Mode Test
```bash
# Without --app-dev (default)
baseboards up test-default

cd test-default
docker compose ps

# Should show: db, cache, api, worker, web (5 services)
```

### App-Dev Mode Test
```bash
# With --app-dev
baseboards up test-appdev --app-dev

cd test-appdev
docker compose ps

# Should show: db, cache, api, worker (4 services, NO web)
```

### Compose Files Test
```bash
# In app-dev mode, verify compose command
cd test-appdev

# The CLI should have run:
# docker compose -f compose.yaml up -d

# NOT:
# docker compose -f compose.yaml -f compose.web.yaml up -d
```

### Service Count Test
```bash
# Default mode
baseboards up test1
docker compose -p test1 ps --format json | jq 'length'
# Should output: 5

# App-dev mode
baseboards up test2 --app-dev
docker compose -p test2 ps --format json | jq 'length'
# Should output: 4
```

### Backend Access Test
```bash
# In app-dev mode, backend should still be accessible
baseboards up test --app-dev

# Wait for services
sleep 10

# Test API access
curl http://localhost:8800/health
# Should return: {"status":"ok"}
```

## Acceptance Criteria

### getComposeFiles() Update

- [ ] Function updated to respect appDev flag:
  ```typescript
  function getComposeFiles(ctx: ProjectContext): string[] {
    const files = ["compose.yaml"]; // Always load base

    // Only add web overlay if NOT in app-dev mode
    if (!ctx.appDev) {
      files.push("compose.web.yaml");
    }

    return files;
  }
  ```

### Service Startup

- [ ] In app-dev mode, only 4 services start (db, cache, api, worker)
- [ ] In default mode, all 5 services start (including web)
- [ ] Health checks only wait for started services
- [ ] Migrations run successfully (don't depend on web)

### Docker Compose Commands

- [ ] All docker compose invocations use correct file list:
  ```typescript
  const files = getComposeFiles(ctx);
  ```

- [ ] Commands affected:
  - [ ] `startDockerCompose()`
  - [ ] `waitForHealthy()` (if it uses docker compose)
  - [ ] `runMigrations()`
  - [ ] `stopDockerCompose()` (in down.ts, if needed)

### Health Check Logic

- [ ] `waitForHealthy()` updated to not wait for web in app-dev mode:
  ```typescript
  const expectedServices = ["api", "db", "cache", "worker"];
  if (!ctx.appDev) {
    expectedServices.push("web");
  }
  ```

### Validation

- [ ] App-dev mode: 4 services running, all healthy
- [ ] Default mode: 5 services running, all healthy
- [ ] API accessible in both modes
- [ ] Database accessible in both modes
- [ ] Worker running in both modes
- [ ] No web service in app-dev mode

### Error Handling

- [ ] Clear error if compose.yaml missing
- [ ] Clear error if compose.web.yaml missing in default mode
- [ ] Services start timeout applies only to expected services

### Quality

- [ ] Logic is clear and maintainable
- [ ] Comments explain app-dev behavior
- [ ] No hardcoded service names where possible
- [ ] TypeScript compiles without errors

### Documentation

- [ ] JSDoc comments updated to mention app-dev mode
- [ ] Function comments explain conditional loading
- [ ] Code comments clarify why web is skipped

### Future Proofing

- [ ] Logic extensible for future overlays
- [ ] Service list can be easily adjusted
- [ ] Compose file list can be extended

### Testing

- [ ] Manual test: default mode starts 5 services
- [ ] Manual test: app-dev mode starts 4 services
- [ ] Manual test: health checks pass in both modes
- [ ] Manual test: API accessible in both modes
- [ ] No regressions in existing functionality
