# Implement Package Source Copying

## Description

Implement the core functionality of `--dev-packages` mode: copying the `@weirdfingers/boards` package source from the monorepo and configuring the scaffolded project to use it as a local dependency via `file:` protocol.

This enables Boards contributors to test unpublished changes to the frontend package by:
1. Copying `packages/frontend` → `<project>/frontend`
2. Modifying `<project>/web/package.json` to reference `"@weirdfingers/boards": "file:../frontend"`
3. Excluding build artifacts and dependencies from the copy

Changes to the local package source hot-reload automatically in the running application (when using native package manager dev server with `--app-dev`).

## Dependencies

- CLI-5.5.1 (--dev-packages flag must exist)
- CLI-5.5.2 (monorepo detection must be implemented)
- CLI-4.4 (frontend dependency installation must work)

## Files to Create/Modify

- Create `/packages/cli-launcher/src/utils/package-copy.ts` (new file)
- Modify `/packages/cli-launcher/src/commands/up.ts` (integrate package copying logic)

## Testing

### Package Copying Tests

```typescript
// In package-copy.test.ts

describe('copyFrontendPackage', () => {
  it('should copy all source files', async () => {
    const monorepoRoot = await detectMonorepoRoot();
    const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'test-'));

    await copyFrontendPackage(monorepoRoot!, tempDir);

    // Verify key files exist
    expect(fs.existsSync(path.join(tempDir, 'package.json'))).toBe(true);
    expect(fs.existsSync(path.join(tempDir, 'src', 'hooks'))).toBe(true);
    expect(fs.existsSync(path.join(tempDir, 'src', 'graphql'))).toBe(true);
    expect(fs.existsSync(path.join(tempDir, 'tsconfig.json'))).toBe(true);
  });

  it('should exclude build artifacts', async () => {
    const monorepoRoot = await detectMonorepoRoot();
    const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'test-'));

    await copyFrontendPackage(monorepoRoot!, tempDir);

    // Verify exclusions
    expect(fs.existsSync(path.join(tempDir, 'node_modules'))).toBe(false);
    expect(fs.existsSync(path.join(tempDir, 'dist'))).toBe(false);
    expect(fs.existsSync(path.join(tempDir, '.turbo'))).toBe(false);
    expect(fs.existsSync(path.join(tempDir, '.next'))).toBe(false);
  });
});

describe('updatePackageJsonForDevPackages', () => {
  it('should modify dependency to file:../frontend', async () => {
    const tempPkg = {
      dependencies: {
        '@weirdfingers/boards': '0.7.0'
      }
    };

    const updated = updatePackageJsonForDevPackages(tempPkg);

    expect(updated.dependencies['@weirdfingers/boards']).toBe('file:../frontend');
  });
});
```

### End-to-End Test

```bash
# From monorepo root
cd boards
pnpm cli up ../test-dev-pkg --template basic --app-dev --dev-packages

# Verify structure
ls -la ../test-dev-pkg/frontend/src/hooks  # Should exist
cat ../test-dev-pkg/web/package.json | grep '"@weirdfingers/boards"'
# Should show: "@weirdfingers/boards": "file:../frontend"

# Start frontend
cd ../test-dev-pkg/web
pnpm install  # Should install from file:../frontend
pnpm dev

# Edit package source
# Edit ../test-dev-pkg/frontend/src/hooks/useBoards.ts
# Changes should hot-reload in browser
```

### Error Handling Tests

```bash
# Missing frontend package (corrupted monorepo)
# Should error with clear message

# Permission issues during copy
# Should error with actionable message

# Invalid package.json in web/
# Should handle gracefully
```

## Acceptance Criteria

### package-copy.ts Implementation

- [ ] Create new file: `/packages/cli-launcher/src/utils/package-copy.ts`

- [ ] Export `copyFrontendPackage()` function:
  ```typescript
  /**
   * Copy @weirdfingers/boards package source from monorepo to target directory.
   * Excludes build artifacts and dependencies.
   *
   * @param monorepoRoot - Root of Boards monorepo
   * @param targetDir - Destination directory for package source
   */
  export async function copyFrontendPackage(
    monorepoRoot: string,
    targetDir: string
  ): Promise<void>;
  ```

- [ ] Export `updatePackageJsonForDevPackages()` function:
  ```typescript
  /**
   * Modify web/package.json to use file:../frontend dependency.
   *
   * @param webDir - Path to web directory
   */
  export async function updatePackageJsonForDevPackages(
    webDir: string
  ): Promise<void>;
  ```

- [ ] Implement file filter for exclusions:
  ```typescript
  function shouldCopyFile(filePath: string): boolean {
    const excluded = [
      'node_modules',
      'dist',
      '.turbo',
      '.next',
      'coverage',
      '.DS_Store'
    ];
    return !excluded.some(ex => filePath.includes(ex));
  }
  ```

- [ ] Use `fs-extra` for recursive copy with filter
- [ ] Handle filesystem errors with clear messages
- [ ] Validate source directory exists before copying

### up.ts Integration

- [ ] Import package copy utilities:
  ```typescript
  import { copyFrontendPackage, updatePackageJsonForDevPackages } from '../utils/package-copy';
  ```

- [ ] Integrate into up command flow when `devPackages === true`:
  ```typescript
  if (ctx.devPackages && ctx.monorepoRoot) {
    // After scaffolding template, before dependency installation

    console.log('📦 Copying @weirdfingers/boards source from monorepo...');
    const targetFrontend = path.join(ctx.dir, 'frontend');
    await copyFrontendPackage(ctx.monorepoRoot, targetFrontend);

    console.log('🔗 Linking local package...');
    const webDir = path.join(ctx.dir, 'web');
    await updatePackageJsonForDevPackages(webDir);

    console.log('✅ Local package linked successfully!');
  }
  ```

- [ ] Update success message for dev-packages mode:
  ```typescript
  if (ctx.devPackages) {
    console.log(`
✅ Backend services are running!
✅ Local @weirdfingers/boards package linked!

   API:      http://localhost:${ctx.ports.api}
   GraphQL:  http://localhost:${ctx.ports.api}/graphql

Package development workflow:

   1. Edit package source:
      ${ctx.dir}/frontend/src/

   2. Start the frontend:
      cd ${ctx.dir}/web
      ${packageManager} dev

   3. Changes to the package will hot-reload automatically

The frontend will be available at http://localhost:3000
    `);
  }
  ```

### File Exclusions

- [ ] Exclude `node_modules/` (never copy dependencies)
- [ ] Exclude `dist/` (build output)
- [ ] Exclude `.turbo/` (Turborepo cache)
- [ ] Exclude `.next/` (Next.js build cache)
- [ ] Exclude `coverage/` (test coverage)
- [ ] Exclude `.DS_Store` (macOS metadata)
- [ ] Include all source files (`src/**`)
- [ ] Include config files (`package.json`, `tsconfig.json`, etc.)

### package.json Modification

- [ ] Read existing `web/package.json`
- [ ] Replace `@weirdfingers/boards` dependency value with `"file:../frontend"`
- [ ] Preserve all other dependencies unchanged
- [ ] Preserve all other package.json fields unchanged
- [ ] Write with proper formatting (2-space indent)
- [ ] Validate JSON is valid after modification

### Error Handling

- [ ] Validate `packages/frontend` exists in monorepo
- [ ] Handle filesystem permission errors gracefully
- [ ] Provide actionable error messages
- [ ] Clean up partial copies on failure
- [ ] Validate `web/package.json` exists before modifying
- [ ] Handle invalid JSON in package.json

### Logging

- [ ] Log when starting copy operation
- [ ] Log when copy completes
- [ ] Log when updating package.json
- [ ] Log success with workflow instructions
- [ ] Use consistent emoji indicators (📦 🔗 ✅)

### Unit Tests

- [ ] Test package source copying
- [ ] Test file exclusions work correctly
- [ ] Test package.json modification
- [ ] Test error handling for missing directories
- [ ] Test error handling for permission issues
- [ ] Mock filesystem for deterministic tests

### Integration Tests

- [ ] Test full workflow from `up` command
- [ ] Verify frontend package installed from file:
- [ ] Verify hot reload works with local package
- [ ] Test with different templates (baseboards, basic)
- [ ] Test cleanup on error

### Documentation

- [ ] JSDoc comments for exported functions
- [ ] Inline comments explaining complex logic
- [ ] Document file exclusion rationale
- [ ] Note about manual sync in success message

### Quality

- [ ] No linting warnings
- [ ] Properly formatted code
- [ ] Consistent with existing CLI patterns
- [ ] TypeScript compiles without errors
- [ ] Error messages are user-friendly

### Performance

- [ ] Efficient file copying (stream-based)
- [ ] No unnecessary filesystem reads
- [ ] Respects system resources
- [ ] Reasonable timeout for large directories
