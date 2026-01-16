# Add --app-dev Flag

## Description

Add a new `--app-dev` command-line flag to the `up` command that enables local frontend development mode. When this flag is specified, the CLI will skip starting the web service in Docker and instead guide the user to run the frontend locally with their preferred package manager.

This is the first step in implementing app-dev mode, establishing the flag and its basic infrastructure.

## Dependencies

None (foundational ticket for Phase 4)

## Files to Create/Modify

- Modify `/packages/cli-launcher/src/types.ts`
- Modify `/packages/cli-launcher/src/commands/up.ts`

## Testing

### Flag Recognition Test
```bash
# Test flag is recognized
baseboards up test --app-dev

# Should not error with "Unknown option"
# Should proceed with modified behavior (even if not fully implemented yet)
```

### Help Text Test
```bash
baseboards up --help

# Should show:
# --app-dev    Run frontend locally instead of in Docker
```

### Context Test
```typescript
// In up.ts, verify flag is captured
console.log(ctx.appDev); // Should log: true when flag provided
```

### Combined Flags Test
```bash
# Test with other flags
baseboards up test --app-dev --template basic --attach

# Should work without conflicts
```

## Acceptance Criteria

### types.ts Changes

- [ ] Add `appDev` field to ProjectContext:
  ```typescript
  interface ProjectContext {
    dir: string;
    name: string;
    version: string;
    ports: {
      web: number;
      api: number;
      db: number;
      redis: number;
    };
    appDev: boolean; // NEW FIELD
  }
  ```

### up.ts Changes

- [ ] Add option to command:
  ```typescript
  .option("--app-dev", "Run frontend locally instead of in Docker")
  ```

- [ ] Parse flag in action handler:
  ```typescript
  const appDev = options.appDev || false;
  ```

- [ ] Add to ProjectContext:
  ```typescript
  const ctx: ProjectContext = {
    dir: resolvedDir,
    name: projectName,
    version: cliVersion,
    ports: { /*...*/ },
    appDev: appDev, // Pass through
  };
  ```

### Help Text

- [ ] Flag appears in `baseboards up --help` output
- [ ] Description clear and concise
- [ ] Positioned logically in option list

### Validation

- [ ] Flag parsing works (true when --app-dev provided, false otherwise)
- [ ] TypeScript compiles without errors
- [ ] No breaking changes to existing flags
- [ ] Boolean field correctly propagated through context

### Default Behavior

- [ ] Default value is `false` (no flag = docker mode)
- [ ] Explicitly providing flag sets to `true`
- [ ] No impact on other command logic yet (placeholder)

### Documentation

- [ ] JSDoc comment added to appDev field:
  ```typescript
  /**
   * Whether to run frontend locally instead of in Docker.
   * When true, web service is not started in Docker Compose.
   */
  appDev: boolean;
  ```

### Quality

- [ ] Consistent naming (camelCase: appDev)
- [ ] Follows existing option patterns
- [ ] No linting warnings
- [ ] Code formatted properly

### Future Tickets

- [ ] Note: This flag will be used in CLI-4.3 to control compose file loading
- [ ] Note: This flag will trigger package manager selection in CLI-4.2
- [ ] Note: This flag will change success messages in CLI-4.5
