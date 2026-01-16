# Add Frontend Dependency Installation

## Description

Implement automatic frontend dependency installation when using `--app-dev` mode. After backend services start, the CLI should prompt for package manager selection and then run the install command in the web directory.

This ensures that when users start developing locally, their dependencies are ready to go.

## Dependencies

- CLI-4.2 (Package manager selection must be implemented)
- CLI-4.3 (App-dev mode must skip web service)

## Files to Create/Modify

- Modify `/packages/cli-launcher/src/commands/up.ts`

## Testing

### Installation Test
```bash
# Start in app-dev mode
baseboards up test --app-dev --template basic

# Observe:
# 1. Backend services start
# 2. Prompt appears: "Select your package manager:"
# 3. After selection, see: "Installing dependencies..."
# 4. Installation completes

# Verify installation worked
cd test/web
ls node_modules/
# Should show installed packages

# Check for @weirdfingers/boards
ls node_modules/@weirdfingers/boards
# Should exist
```

### Package Manager Selection Test
```bash
# Test with pnpm
baseboards up test-pnpm --app-dev
# Select pnpm
# Verify: "Running pnpm install..." message
# Verify: pnpm-lock.yaml created

# Test with npm
baseboards up test-npm --app-dev
# Select npm
# Verify: "Running npm install..." message
# Verify: package-lock.json created

# Test with yarn
baseboards up test-yarn --app-dev
# Select yarn
# Verify: "Running yarn install..." message
# Verify: yarn.lock created
```

### Progress Indicator Test
```bash
# Should show progress during install
baseboards up test --app-dev

# Expected output:
# Installing dependencies with pnpm...
# [spinner or progress indicator]
# Dependencies installed successfully
```

### Error Handling Test
```bash
# Test with corrupted package.json
cd test-project/web
echo "invalid json" > package.json

baseboards up ../test-project --app-dev

# Should: Show clear error message
# Should: Exit gracefully
# Should: Not leave services running if install fails
```

### Skip for Default Mode Test
```bash
# Without --app-dev flag
baseboards up test-default

# Should NOT prompt for package manager
# Should NOT install dependencies
# Web service handles its own install in Docker
```

## Acceptance Criteria

### Flow Integration

- [ ] Only runs in app-dev mode:
  ```typescript
  if (ctx.appDev) {
    // Install dependencies
  }
  ```

- [ ] Runs after backend services are healthy:
  ```typescript
  await waitForHealth(ctx);
  await runMigrations(ctx);

  if (ctx.appDev) {
    await installFrontendDependencies(ctx);
  }
  ```

### Package Manager Selection

- [ ] Prompts for package manager:
  ```typescript
  const packageManager = await promptPackageManager();
  ```

- [ ] Stores selection for later use (CLI-4.5):
  ```typescript
  ctx.packageManager = packageManager; // Add to context type
  ```

### Installation Execution

- [ ] Function created: `installFrontendDependencies(ctx, packageManager)`:
  ```typescript
  async function installFrontendDependencies(
    ctx: ProjectContext,
    packageManager: PackageManager
  ): Promise<void> {
    const webDir = path.join(ctx.dir, "web");

    // Determine install command
    const installCmd = packageManager === "npm" ? "install" : "install";

    // Show progress
    console.log(`\nInstalling dependencies with ${packageManager}...`);

    // Run install
    try {
      await exec(packageManager, [installCmd], {
        cwd: webDir,
        stdio: "inherit", // Show install output
      });
      console.log("Dependencies installed successfully\n");
    } catch (error) {
      console.error(`Failed to install dependencies: ${error.message}`);
      throw error;
    }
  }
  ```

### Progress Indication

- [ ] Shows clear message before starting
- [ ] Shows package manager being used
- [ ] Install output visible to user (stdio: inherit)
- [ ] Success message after completion

### Error Handling

- [ ] Installation errors caught and reported
- [ ] Error message suggests checking package.json
- [ ] Error message suggests checking package manager is installed
- [ ] Process exits gracefully on error
- [ ] Partial state handled (services may be running)

### Type Updates

- [ ] Add packageManager to ProjectContext:
  ```typescript
  interface ProjectContext {
    // ... existing fields
    appDev: boolean;
    packageManager?: PackageManager; // Optional, only set in app-dev mode
  }
  ```

### Validation

- [ ] Dependencies actually installed (node_modules exists)
- [ ] Lock files created (pnpm-lock.yaml, package-lock.json, or yarn.lock)
- [ ] @weirdfingers/boards package present
- [ ] Installation succeeds for all package managers

### Quality

- [ ] Uses existing exec utility from utils
- [ ] Error handling consistent with other commands
- [ ] TypeScript types properly defined
- [ ] Code follows existing patterns

### Documentation

- [ ] Function documented with JSDoc
- [ ] Comments explain why install happens in app-dev mode
- [ ] Error messages helpful and actionable

### Testing

- [ ] Works with pnpm (create pnpm-lock.yaml)
- [ ] Works with npm (create package-lock.json)
- [ ] Works with yarn (create yarn.lock)
- [ ] Works with bun (create bun.lockb)
- [ ] Error handling works (bad package.json)
- [ ] Only runs in app-dev mode (not in default mode)
