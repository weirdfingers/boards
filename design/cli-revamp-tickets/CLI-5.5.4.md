# Add Dev-Packages Integration Tests

## Description

Create comprehensive integration tests for the `--dev-packages` feature to ensure it works end-to-end for Boards contributors testing unpublished package changes.

These tests validate:
1. Monorepo detection works correctly
2. Package source is copied successfully
3. Local dependency linking works
4. Hot reload functions with local package changes
5. Error cases are handled gracefully

## Dependencies

- CLI-5.5.1 (--dev-packages flag)
- CLI-5.5.2 (monorepo detection)
- CLI-5.5.3 (package copying)
- CLI-4.4 (frontend dependency installation)

## Files to Create/Modify

- Create `/packages/cli-launcher/tests/integration/dev-packages.test.ts` (new file)
- Update `/packages/cli-launcher/tests/README.md` (document dev-packages tests)

## Testing

### Test Suite Structure

```typescript
// dev-packages.test.ts

describe('--dev-packages flag', () => {
  describe('validation', () => {
    it('should error when used without --app-dev', async () => { /*...*/ });
    it('should error when not in monorepo', async () => { /*...*/ });
    it('should accept flag when in monorepo with --app-dev', async () => { /*...*/ });
  });

  describe('monorepo detection', () => {
    it('should detect monorepo from packages/cli-launcher', async () => { /*...*/ });
    it('should return null outside monorepo', async () => { /*...*/ });
    it('should validate packages/frontend exists', async () => { /*...*/ });
    it('should validate @weirdfingers/boards package name', async () => { /*...*/ });
  });

  describe('package source copying', () => {
    it('should copy frontend package to <project>/frontend', async () => { /*...*/ });
    it('should exclude node_modules, dist, .turbo, .next', async () => { /*...*/ });
    it('should include all src files', async () => { /*...*/ });
    it('should include package.json and tsconfig.json', async () => { /*...*/ });
    it('should handle missing source gracefully', async () => { /*...*/ });
  });

  describe('package.json modification', () => {
    it('should update dependency to file:../frontend', async () => { /*...*/ });
    it('should preserve other dependencies', async () => { /*...*/ });
    it('should maintain JSON formatting', async () => { /*...*/ });
    it('should handle invalid package.json gracefully', async () => { /*...*/ });
  });

  describe('end-to-end workflow', () => {
    it('should scaffold project with local package', async () => { /*...*/ });
    it('should install dependencies from file:', async () => { /*...*/ });
    it('should start services successfully', async () => { /*...*/ });
    it('should enable hot reload for package changes', async () => { /*...*/ });
  });

  describe('error handling', () => {
    it('should error with helpful message outside monorepo', async () => { /*...*/ });
    it('should error when packages/frontend missing', async () => { /*...*/ });
    it('should error on filesystem permission issues', async () => { /*...*/ });
  });
});
```

### Manual Testing Checklist

```bash
# Prerequisites: Clone and setup Boards monorepo
git clone https://github.com/weirdfingers/boards.git
cd boards
pnpm install

# Test 1: Basic workflow
pnpm cli up ../test-dev-pkg --template basic --app-dev --dev-packages
# ✓ Should succeed
# ✓ Should create ../test-dev-pkg/frontend/
# ✓ Should link file:../frontend in package.json

# Test 2: Verify installation
cd ../test-dev-pkg/web
pnpm install
# ✓ Should install from file:../frontend
# ✓ Should not fetch from npm

# Test 3: Verify hot reload
pnpm dev
# (In separate terminal)
# Edit ../test-dev-pkg/frontend/src/hooks/useBoards.ts
# Add console.log('TEST HOT RELOAD')
# ✓ Browser should reload automatically
# ✓ Console should show new log

# Test 4: Error without --app-dev
cd ../../boards
pnpm cli up ../test-error --dev-packages
# ✗ Should error: "--dev-packages requires --app-dev mode"

# Test 5: Error outside monorepo
cd /tmp
npx @weirdfingers/baseboards up test --app-dev --dev-packages
# ✗ Should error: "requires running from within the Boards monorepo"

# Test 6: Baseboards template
cd boards
pnpm cli up ../test-baseboards --template baseboards --app-dev --dev-packages
# ✓ Should work with full template

# Test 7: Manual sync workflow
cd ../test-dev-pkg/frontend/src/hooks
# Make substantial changes to useBoards.ts
# Test in browser, verify works
cd ../../../../boards
cp -r ../test-dev-pkg/frontend/src/hooks/useBoards.ts packages/frontend/src/hooks/
# ✓ Changes should be in monorepo now
git diff packages/frontend/src/hooks/useBoards.ts
# ✓ Should show changes
```

## Acceptance Criteria

### Test File Creation

- [ ] Create `/packages/cli-launcher/tests/integration/dev-packages.test.ts`
- [ ] Follow existing test structure and patterns
- [ ] Use proper test utilities and helpers

### Validation Tests

- [ ] Test flag requires `--app-dev`
- [ ] Test error message is clear and actionable
- [ ] Test flag accepts boolean value correctly
- [ ] Test flag works with other flags (--template, --attach)

### Monorepo Detection Tests

- [ ] Test detection from within monorepo
- [ ] Test failure outside monorepo
- [ ] Test validation of packages/frontend existence
- [ ] Test validation of package name
- [ ] Mock filesystem for deterministic results

### Package Copying Tests

- [ ] Test source files are copied
- [ ] Test exclusions work (node_modules, dist, .turbo, .next)
- [ ] Test directory structure is preserved
- [ ] Test symlinks are handled correctly
- [ ] Test large files don't cause issues

### package.json Modification Tests

- [ ] Test dependency updated to `file:../frontend`
- [ ] Test other dependencies unchanged
- [ ] Test package.json remains valid JSON
- [ ] Test formatting is preserved
- [ ] Test error handling for invalid JSON

### End-to-End Tests

- [ ] Test complete workflow from `up` command
- [ ] Test package manager installs from file:
- [ ] Test services start successfully
- [ ] Test hot reload works
- [ ] Test with both templates (basic, baseboards)
- [ ] Clean up test artifacts after each test

### Error Handling Tests

- [ ] Test error outside monorepo
- [ ] Test error with missing packages/frontend
- [ ] Test error on permission issues
- [ ] Test error on disk space issues
- [ ] Test error messages are user-friendly
- [ ] Test error cleanup (no partial state left)

### Test Utilities

- [ ] Create helper for temporary test projects
- [ ] Create helper for mocking monorepo structure
- [ ] Create helper for cleaning up test artifacts
- [ ] Reuse existing CLI test utilities where possible

### Test Configuration

- [ ] Configure timeout for long-running tests
- [ ] Configure cleanup hooks (afterEach, afterAll)
- [ ] Configure mocks for external dependencies
- [ ] Configure parallel execution where safe

### Documentation

- [ ] Update tests/README.md with dev-packages tests
- [ ] Document test prerequisites (monorepo setup)
- [ ] Document manual testing procedure
- [ ] Add troubleshooting section for test failures

### CI/CD Integration

- [ ] Tests run in GitHub Actions
- [ ] Tests have access to monorepo structure (they run within it)
- [ ] Tests clean up after themselves
- [ ] Tests don't interfere with each other

### Coverage

- [ ] Validation logic covered
- [ ] Monorepo detection covered
- [ ] Package copying covered
- [ ] package.json modification covered
- [ ] Error paths covered
- [ ] Edge cases covered

### Quality

- [ ] All tests pass consistently
- [ ] No flaky tests
- [ ] No test pollution (tests isolated)
- [ ] Tests are fast (use mocks where appropriate)
- [ ] Tests are maintainable (clear assertions)

### Edge Cases

- [ ] Test with workspace protocol in package.json
- [ ] Test with pre-existing frontend/ directory
- [ ] Test with corrupted package source
- [ ] Test with insufficient permissions
- [ ] Test with disk space issues
- [ ] Test concurrent invocations

### Performance

- [ ] Tests complete in reasonable time (<30s per test)
- [ ] File operations are efficient
- [ ] Cleanup is thorough but fast
- [ ] No memory leaks in long-running tests

### User Experience Validation

- [ ] Success messages are clear
- [ ] Error messages are actionable
- [ ] Progress indicators work
- [ ] Help text is accurate
- [ ] Examples in docs are tested
