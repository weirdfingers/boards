# Update Compose File Loading Logic

## Description

Update the compose file loading logic in the CLI to properly handle the new structure with base compose and web overlay. The CLI should:
- Always load `compose.yaml` (base with backend services)
- Conditionally load `compose.web.yaml` (overlay with web service)
- Skip web overlay when `--app-dev` flag is present (Phase 4 preparation)

This ticket finalizes Phase 3 by implementing the correct compose file loading strategy that enables Phase 4's app-dev mode.

## Dependencies

- CLI-3.2 (compose.web.yaml must exist)
- CLI-3.4 (mode logic must be removed)

## Files to Create/Modify

- Modify `/packages/cli-launcher/src/commands/up.ts`

## Testing

### Default Behavior Test
```bash
# Default (no flags) - should load both files
baseboards up test

# Verify both files loaded
docker compose -f compose.yaml -f compose.web.yaml ps
# Should show: db, cache, api, worker, web (5 services)
```

### Compose Files Detection Test
```typescript
// Add test or debug output
const files = getComposeFiles(ctx);
console.log(files);
// Should log: ["compose.yaml", "compose.web.yaml"]
```

### Service Count Test
```bash
# After scaffold and start
cd test-project
docker compose ps --format json | jq 'length'
# Should output: 5 (db, cache, api, worker, web)
```

### Web Service Test
```bash
# Verify web service is running
curl http://localhost:3300
# Should return Next.js page

# Verify web service is in Docker
docker compose ps web
# Should show web service running
```

### Docker Compose Command Test
Check the actual docker compose command executed:
```bash
# The CLI should run:
docker compose -f compose.yaml -f compose.web.yaml up -d --build --remove-orphans

# Not:
docker compose up -d --build --remove-orphans
```

## Acceptance Criteria

### Function Updates

- [ ] `getComposeFiles()` function updated (or created if doesn't exist):
  ```typescript
  function getComposeFiles(ctx: ProjectContext): string[] {
    const files = ["compose.yaml"]; // Always load base

    // For now, always add web overlay
    // In Phase 4, this will be conditional on --app-dev flag
    files.push("compose.web.yaml");

    return files;
  }
  ```

### Docker Compose Execution

- [ ] All docker compose commands use file list:
  ```typescript
  const files = getComposeFiles(ctx);
  const composeArgs = files.flatMap(f => ["-f", f]);

  // Example: docker compose -f compose.yaml -f compose.web.yaml up -d
  await exec("docker", ["compose", ...composeArgs, "up", "-d", "--build", "--remove-orphans"]);
  ```

### Commands Affected

- [ ] `startDockerCompose()` uses file list
- [ ] `waitForHealthy()` uses file list (if it calls docker compose)
- [ ] `runMigrations()` may use file list
- [ ] Any other docker compose invocations updated

### Path Handling

- [ ] Compose files resolved relative to project directory:
  ```typescript
  const files = getComposeFiles(ctx).map(f => path.join(ctx.dir, f));
  ```

### Error Handling

- [ ] Check that compose files exist before starting:
  ```typescript
  for (const file of files) {
    if (!fs.existsSync(path.join(ctx.dir, file))) {
      throw new Error(`Compose file not found: ${file}`);
    }
  }
  ```

### Validation

- [ ] Services start successfully with both files
- [ ] All 5 services (db, cache, api, worker, web) running
- [ ] Health checks pass for all services
- [ ] Web service accessible at configured port
- [ ] No errors in docker compose logs

### Future-Proofing

- [ ] Code structured to easily add conditional logic for --app-dev (Phase 4):
  ```typescript
  // Placeholder for Phase 4
  if (!ctx.appDev) {
    files.push("compose.web.yaml");
  }
  ```

- [ ] Comment noting this will change in Phase 4:
  ```typescript
  // TODO: In Phase 4, only add compose.web.yaml if NOT --app-dev mode
  files.push("compose.web.yaml");
  ```

### Quality

- [ ] TypeScript compiles without errors
- [ ] No hardcoded file paths
- [ ] Consistent with Docker Compose best practices
- [ ] Error messages helpful

### Documentation

- [ ] JSDoc comment explains compose file loading strategy
- [ ] Comments note Phase 4 changes coming
- [ ] Function signature clear and documented

### Testing

- [ ] Manual test: scaffold and verify 5 services
- [ ] Manual test: all health checks pass
- [ ] Manual test: web accessible
- [ ] No regressions in existing functionality
