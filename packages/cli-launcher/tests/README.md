# CLI Launcher Tests

This directory contains tests for the `@weirdfingers/baseboards` CLI launcher package.

## Test Structure

Tests are organized into two categories:

1. **Unit/Integration Tests** (`integration/`) - TypeScript tests using Vitest
2. **Manual Scripted Tests** - Shell scripts that can be run independently

## Available Tests

### Integration Tests

#### `integration/dev-packages.test.ts`

**Purpose:** Comprehensive integration tests for the `--dev-packages` feature that enables Boards contributors to test unpublished package changes in local development.

**What it tests:**
- **Validation**: Ensures `--dev-packages` requires `--app-dev` mode and monorepo context
- **Monorepo Detection**: Verifies detection of Boards monorepo from CLI package location
- **Package Source Copying**: Tests copying of frontend package source to project directory
  - Includes all source files (`src/`, config files)
  - Excludes build artifacts (`node_modules`, `dist`, `.turbo`, `.next`, `coverage`)
  - Preserves directory structure
- **package.json Modification**: Tests updating dependency to `file:../frontend` while preserving other dependencies
- **End-to-End Workflow**: Validates complete setup from scaffolding to hot reload readiness
- **Error Handling**: Tests graceful failures with helpful error messages

**Test Categories:**
```typescript
- validation (3 tests)
- monorepo detection (4 tests)
- package source copying (5 tests)
- package.json modification (4 tests)
- end-to-end workflow (5 tests)
- error handling (3 tests)
```

**How to run:**
```bash
# From monorepo root
pnpm test

# Run only dev-packages tests
cd packages/cli-launcher
pnpm test dev-packages

# Watch mode
pnpm test dev-packages --watch
```

**Prerequisites:**
- Must run from within Boards monorepo (tests detect this automatically)
- Node.js 20+ and pnpm installed
- No Docker required (tests use mocked environments)

**Current status:** ✅ **PASSING** - All 24 tests passing

**Key Features Tested:**
1. ✅ Flag validation (requires `--app-dev`, requires monorepo)
2. ✅ Monorepo detection (`pnpm-workspace.yaml`, `packages/frontend` validation)
3. ✅ Source file copying with proper exclusions
4. ✅ Local package linking via `file:../frontend`
5. ✅ Error messages are clear and actionable
6. ✅ Filesystem operations are safe and isolated

**Manual Testing Workflow:**

For end-to-end manual testing of the feature:

```bash
# From monorepo root
cd boards
pnpm install

# Test basic workflow
pnpm cli up ../test-dev-pkg --template basic --app-dev --dev-packages

# Verify structure
ls ../test-dev-pkg/frontend/src/hooks  # Should see useBoards.ts etc
cat ../test-dev-pkg/web/package.json   # Should have file:../frontend

# Test installation
cd ../test-dev-pkg/web
pnpm install  # Should install from local file:

# Test hot reload
pnpm dev
# Edit ../test-dev-pkg/frontend/src/hooks/useBoards.ts
# Browser should reload with changes

# Test error cases
cd ../../boards
pnpm cli up ../test-error --dev-packages  # Should error: requires --app-dev
cd /tmp
npx @weirdfingers/baseboards up test --app-dev --dev-packages  # Should error: requires monorepo
```

**Troubleshooting:**

- **Tests skipped in CI**: Some tests auto-skip if not running in monorepo (expected behavior)
- **Permission errors**: Ensure temp directories are writable
- **Flaky tests**: All tests use isolated temp directories and cleanup properly

### Manual Scripted Tests

#### `test-dockerfile-api.sh`

**Purpose:** Validates that the Dockerfile.api template can successfully build a Docker image with the correct Python optional dependency groups.

**How it works:**
1. Copies the real `Dockerfile.api` from `template-sources/`
2. Copies the real `pyproject.toml` from `packages/backend/`
3. Builds a Docker image and checks for uv warnings about missing extras
4. Fails if any "does not have an extra named..." warnings are detected

**What it tests:**
- The Dockerfile.api references valid optional dependency groups from pyproject.toml
- The uv pip install command can resolve all specified dependencies without warnings
- Detects any warnings about missing extras (e.g., `does not have an extra named...`)
- Common error: referencing non-existent groups like `[providers]` which was removed

**How to run:**
```bash
cd packages/cli-launcher/tests
./test-dockerfile-api.sh
```

**Current status:** ✅ **PASSING** - Dockerfile.api now uses valid `[generators-all]` group

**Expected behavior:**
- ✅ Should pass when no warnings about missing extras are found
- ❌ Should fail if any "does not have an extra named..." warnings appear

**Requirements:**
- Docker must be installed and running
- No other dependencies needed (test creates temporary environment)

## Writing New Tests

When adding new tests:

1. Create a new `.sh` script in this directory
2. Make it executable: `chmod +x test-*.sh`
3. Follow the pattern:
   - Clear test purpose in header comment
   - Use `set -e` for fail-fast behavior
   - Use `mktemp -d` for isolated test environments
   - Clean up with trap: `trap cleanup EXIT`
   - Output clear ✅/❌ messages
4. Document the test in this README

## Test Categories

Current and planned test areas:

- [x] **Template Validation** - Dockerfile.api dependency groups
- [x] **Dev Packages Integration** - --dev-packages flag functionality
- [ ] **Template Processing** - prepare-templates.js output
- [ ] **CLI Commands** - baseboards init/up/down/logs
- [ ] **Docker Compose** - compose.yaml validation
- [ ] **Environment Setup** - .env.example files are complete

## Running All Tests

### TypeScript Tests (Vitest)

```bash
# From monorepo root
pnpm test

# From cli-launcher package
cd packages/cli-launcher
pnpm test

# Watch mode
pnpm test --watch

# With coverage
pnpm test --coverage
```

### Manual Shell Tests

To run all shell tests at once:

```bash
cd packages/cli-launcher/tests
for test in test-*.sh; do
  echo "Running $test..."
  ./"$test"
  echo ""
done
```

## CI Integration

Current CI integration:
- ✅ TypeScript/Vitest tests run in GitHub Actions via `pnpm test`
- ✅ Tests run as part of Turborepo pipeline
- ✅ Pre-commit hooks run tests

Future work:
- [ ] Add shell script tests to CI
- [ ] Add test coverage requirements
- [ ] Pre-publish checks (npm prepublishOnly script)
