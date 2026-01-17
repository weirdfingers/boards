# Implement Monorepo Detection Utility

## Description

Create a utility function to detect if the CLI is running from within the Boards monorepo. This is critical for the `--dev-packages` feature, which requires access to the unpublished `packages/frontend` source code.

When running via `npx @weirdfingers/baseboards` from npm, the CLI package is installed in a temporary location with no access to monorepo packages. The `--dev-packages` feature only works when the CLI is run from within a cloned Boards monorepo.

This utility validates monorepo presence by checking for:
1. `pnpm-workspace.yaml` file (indicates pnpm monorepo)
2. `packages/frontend/package.json` file (validates Boards structure)
3. Package name is `@weirdfingers/boards` (confirms correct repo)

## Dependencies

- CLI-5.5.1 (--dev-packages flag must exist)

## Files to Create/Modify

- Create `/packages/cli-launcher/src/utils/monorepo-detection.ts` (new file)
- Modify `/packages/cli-launcher/src/commands/up.ts` (import and use detection utility)

## Testing

### Monorepo Detection Tests

```typescript
// In monorepo-detection.test.ts

describe('detectMonorepoRoot', () => {
  it('should detect monorepo root from CLI package location', async () => {
    // When running from packages/cli-launcher
    const root = await detectMonorepoRoot();
    expect(root).toBeTruthy();
    expect(root).toContain('boards');
  });

  it('should return null when not in monorepo', async () => {
    // Mock running from /tmp or npm cache
    jest.spyOn(process, 'cwd').mockReturnValue('/tmp');
    const root = await detectMonorepoRoot();
    expect(root).toBeNull();
  });

  it('should validate packages/frontend exists', async () => {
    const root = await detectMonorepoRoot();
    if (root) {
      const frontendPath = path.join(root, 'packages', 'frontend');
      expect(fs.existsSync(frontendPath)).toBe(true);
    }
  });

  it('should validate @weirdfingers/boards package name', async () => {
    const root = await detectMonorepoRoot();
    if (root) {
      const pkgPath = path.join(root, 'packages', 'frontend', 'package.json');
      const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
      expect(pkg.name).toBe('@weirdfingers/boards');
    }
  });
});
```

### Integration Test with --dev-packages

```bash
# Run from monorepo root - should succeed
cd boards
pnpm cli up ../test --app-dev --dev-packages

# Run from outside monorepo - should error
cd /tmp
npx @weirdfingers/baseboards up test --app-dev --dev-packages
# Expected error: "--dev-packages requires running from within the Boards monorepo"
```

### Error Message Test

```bash
# From outside monorepo
npx @weirdfingers/baseboards up test --app-dev --dev-packages

# Should show helpful error:
# --dev-packages requires running from within the Boards monorepo.
#
# This feature is for Boards contributors testing unpublished package changes.
# Clone the monorepo and run: cd boards && pnpm cli up <dir> --app-dev --dev-packages
#
# If you want to develop apps using the published package, use --app-dev without --dev-packages.
```

## Acceptance Criteria

### monorepo-detection.ts Implementation

- [ ] Create new file: `/packages/cli-launcher/src/utils/monorepo-detection.ts`

- [ ] Export `detectMonorepoRoot()` function:
  ```typescript
  /**
   * Detect if CLI is running from within the Boards monorepo.
   * Returns monorepo root path if found, null otherwise.
   *
   * Walks up the directory tree from CLI package location looking for:
   * 1. pnpm-workspace.yaml (monorepo marker)
   * 2. packages/frontend/package.json (Boards structure)
   * 3. Package name === '@weirdfingers/boards' (correct repo)
   */
  export async function detectMonorepoRoot(): Promise<string | null>;
  ```

- [ ] Implementation walks up directory tree (max 5 levels)
- [ ] Checks for `pnpm-workspace.yaml` at each level
- [ ] Validates `packages/frontend/package.json` exists
- [ ] Reads and verifies package name is `@weirdfingers/boards`
- [ ] Returns root path on success, null on failure
- [ ] Handles filesystem errors gracefully

### up.ts Integration

- [ ] Import detection utility:
  ```typescript
  import { detectMonorepoRoot } from '../utils/monorepo-detection';
  ```

- [ ] Call detection when `--dev-packages` is used:
  ```typescript
  if (ctx.devPackages) {
    const monorepoRoot = await detectMonorepoRoot();
    if (!monorepoRoot) {
      throw new Error(
        '--dev-packages requires running from within the Boards monorepo.\n\n' +
        'This feature is for Boards contributors testing unpublished package changes.\n' +
        'Clone the monorepo and run: cd boards && pnpm cli up <dir> --app-dev --dev-packages\n\n' +
        'If you want to develop apps using the published package, use --app-dev without --dev-packages.'
      );
    }

    // Store for use in CLI-5.5.3
    ctx.monorepoRoot = monorepoRoot;
  }
  ```

- [ ] Error message is clear and actionable
- [ ] Provides instructions for cloning repo
- [ ] Mentions alternative (`--app-dev` without `--dev-packages`)

### Error Handling

- [ ] Handles missing `pnpm-workspace.yaml` gracefully
- [ ] Handles missing `packages/frontend` gracefully
- [ ] Handles invalid package.json gracefully
- [ ] Handles filesystem permission errors gracefully
- [ ] Returns null instead of throwing (let caller decide error message)

### TypeScript Types

- [ ] Add `monorepoRoot` to ProjectContext:
  ```typescript
  interface ProjectContext {
    // ... existing fields
    devPackages: boolean;
    monorepoRoot?: string; // NEW FIELD (only set when devPackages=true)
  }
  ```

### Unit Tests

- [ ] Test detection from various starting directories
- [ ] Test failure when not in monorepo
- [ ] Test validation of package name
- [ ] Test handling of missing files/directories
- [ ] Test maximum depth limit (5 levels)
- [ ] Mock filesystem for deterministic tests

### Documentation

- [ ] JSDoc comments for exported function
- [ ] Inline comments explaining validation logic
- [ ] README note about monorepo-only feature

### Quality

- [ ] No linting warnings
- [ ] Properly formatted code
- [ ] Error messages are user-friendly
- [ ] Follows existing code patterns
- [ ] TypeScript compiles without errors

### Performance

- [ ] Minimal filesystem operations
- [ ] Stops walking up tree at first match
- [ ] Respects depth limit to avoid infinite loops
- [ ] Uses async file operations (non-blocking)
