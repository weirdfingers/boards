# Remove --prod Flag from CLI

## Description

Remove the `--prod` flag and production mode logic from the CLI, simplifying to a single development mode. This removes the prod/dev distinction throughout the codebase.

Changes involve:
- Remove `--prod` flag from command options
- Remove `--dev` flag (it becomes implicit/default)
- Remove `mode` field from ProjectContext type
- Remove mode-based conditionals in code
- Update help text and error messages
- Simplify compose file loading logic (preparation for CLI-3.5)

After this change, `baseboards up` always runs in development mode.

## Dependencies

- CLI-3.3 (compose.dev.yaml must be deleted first)

## Files to Create/Modify

- Modify `/packages/cli-launcher/src/commands/up.ts`
- Modify `/packages/cli-launcher/src/types.ts`

## Testing

### Flag Removal Test
```bash
# Old prod flag should error
baseboards up test --prod

# Expected: Error message or flag not recognized
# "Unknown option: --prod"

# Old dev flag should be ignored or error
baseboards up test --dev

# Expected: Either ignored (no-op) or error message
```

### Default Behavior Test
```bash
# No flags - should work
baseboards up test

# Should scaffold and start in dev mode
```

### Help Text Test
```bash
baseboards up --help

# Should NOT mention:
# - --prod flag
# - --dev flag
# - "production mode"
# - "development mode"

# Should focus on:
# - template selection
# - port configuration
# - other relevant flags
```

### Code Verification Test
```bash
# Search codebase for mode references
cd packages/cli-launcher
grep -r "mode:" src/
# Should find no ProjectContext.mode references

grep -r "prod" src/ | grep -v "reproduce" | grep -v "product"
# Should find no --prod flag handling
```

## Acceptance Criteria

### types.ts Changes

- [ ] `mode` field removed from ProjectContext interface:
  ```typescript
  // Before:
  interface ProjectContext {
    dir: string;
    name: string;
    version: string;
    mode: "dev" | "prod"; // REMOVE THIS
    ports: {/*...*/};
  }

  // After:
  interface ProjectContext {
    dir: string;
    name: string;
    version: string;
    ports: {/*...*/};
  }
  ```

### up.ts Changes

- [ ] `.option("--prod", ...)` line removed
- [ ] `.option("--dev", ...)` line removed (if exists)
- [ ] Mode parsing logic removed
- [ ] Mode validation removed
- [ ] Mode-based conditionals removed or simplified
- [ ] Default behavior is development mode (always)

### Removed Logic

- [ ] No more `if (mode === "prod")` conditionals
- [ ] No more `if (mode === "dev")` conditionals
- [ ] No more mode parameter passing
- [ ] No more mode-based error messages

### Help Text Updates

- [ ] `baseboards up --help` shows no mode flags
- [ ] Description doesn't mention prod/dev distinction
- [ ] Focus on template and configuration options

### Error Messages

- [ ] Remove mode-related error messages
- [ ] Update any messages that referenced prod/dev
- [ ] Ensure clarity that system runs in development mode

### Simplification

- [ ] `getComposeFiles()` simplified (preparation for CLI-3.5)
- [ ] Code paths consolidated (no mode branching)
- [ ] Comments updated to remove mode references

### Quality

- [ ] TypeScript compiles without errors
- [ ] No unused variables related to mode
- [ ] No dead code paths
- [ ] Linter happy (no warnings)

### Backward Compatibility Note

This is a **breaking change**:
- [ ] Document that --prod no longer works
- [ ] Users must use Docker for production deployments
- [ ] CLI is for development/testing only
- [ ] Add to migration guide (Phase 6)

### Documentation

- [ ] Function comments updated
- [ ] No references to "production mode"
- [ ] Clear that CLI is for development
- [ ] Help text accurate and helpful

### Testing

- [ ] Scaffolding still works without mode flag
- [ ] All services start correctly
- [ ] No regressions in core functionality
- [ ] Error handling still robust
