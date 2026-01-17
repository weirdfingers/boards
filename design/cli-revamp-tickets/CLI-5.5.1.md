# Add --dev-packages Flag and Validation

## Description

Add a new `--dev-packages` command-line flag to the `up` command that enables local package development mode. When this flag is specified, the CLI will copy the unpublished `@weirdfingers/boards` package source from the monorepo and configure the template to use it via `file:` dependency.

This feature is **only for Boards contributors** working within the Boards monorepo to test unpublished package changes. It does NOT work when running via `npx` from npm.

This ticket implements the flag and validation logic, establishing the foundation for package development mode.

## Dependencies

- CLI-4.1 (--app-dev flag must exist)

## Files to Create/Modify

- Modify `/packages/cli-launcher/src/types.ts`
- Modify `/packages/cli-launcher/src/commands/up.ts`

## Testing

### Flag Recognition Test
```bash
# From monorepo root
pnpm cli up ../test --app-dev --dev-packages

# Should not error with "Unknown option"
# Should proceed with dev-packages logic
```

### Validation Test: Requires --app-dev
```bash
# From monorepo root
pnpm cli up ../test --dev-packages

# Should error:
# "--dev-packages requires --app-dev mode"
```

### Help Text Test
```bash
pnpm cli up --help

# Should show:
# --dev-packages    Include unpublished @weirdfingers/boards source (requires --app-dev)
```

### Combined Flags Test
```bash
pnpm cli up ../test --app-dev --dev-packages --template basic

# Should work without conflicts
```

## Acceptance Criteria

### types.ts Changes

- [ ] Add `devPackages` field to ProjectContext:
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
    appDev: boolean;
    devPackages: boolean; // NEW FIELD
  }
  ```

### up.ts Changes

- [ ] Add option to command:
  ```typescript
  .option("--dev-packages", "Include unpublished @weirdfingers/boards source (requires --app-dev)")
  ```

- [ ] Parse flag in action handler:
  ```typescript
  const devPackages = options.devPackages || false;
  ```

- [ ] Add validation for --app-dev requirement:
  ```typescript
  if (devPackages && !appDev) {
    throw new Error(
      '--dev-packages requires --app-dev mode. ' +
      'Docker-based web service cannot use local package sources.'
    );
  }
  ```

- [ ] Add to ProjectContext:
  ```typescript
  const ctx: ProjectContext = {
    dir: resolvedDir,
    name: projectName,
    version: cliVersion,
    ports: { /*...*/ },
    appDev: appDev,
    devPackages: devPackages, // Pass through
  };
  ```

### Help Text

- [ ] Flag appears in `baseboards up --help` output
- [ ] Description mentions requirement for `--app-dev`
- [ ] Positioned after `--app-dev` in option list

### Validation Logic

- [ ] Error thrown if `--dev-packages` used without `--app-dev`
- [ ] Error message is clear and actionable
- [ ] Boolean field correctly propagated through context
- [ ] TypeScript compiles without errors

### Default Behavior

- [ ] Default value is `false` (no flag = published package)
- [ ] Explicitly providing flag sets to `true`
- [ ] No impact on other command logic yet (placeholder for CLI-5.5.3)

### Documentation

- [ ] JSDoc comment added to devPackages field:
  ```typescript
  /**
   * Whether to include unpublished @weirdfingers/boards package source.
   * Only works when CLI runs from within the Boards monorepo.
   * When true, packages/frontend is copied to project and linked via file: dependency.
   * Requires appDev to be true.
   */
  devPackages: boolean;
  ```

### Quality

- [ ] Consistent naming (camelCase: devPackages)
- [ ] Follows existing option patterns
- [ ] No linting warnings
- [ ] Code formatted properly

### Future Tickets

- [ ] Note: This flag will trigger monorepo detection in CLI-5.5.2
- [ ] Note: This flag will trigger package copying in CLI-5.5.3
- [ ] Note: Integration tests will be added in CLI-5.5.4
