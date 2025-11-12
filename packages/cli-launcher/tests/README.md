# CLI Launcher Tests

This directory contains manual tests for the `@weirdfingers/baseboards` CLI launcher package.

## Test Structure

These are **manual scripted tests** that can be run independently to validate different aspects of the CLI launcher functionality.

## Available Tests

### `test-dockerfile-api.sh`

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
- [ ] **Template Processing** - prepare-templates.js output
- [ ] **CLI Commands** - baseboards init/up/down/logs
- [ ] **Docker Compose** - compose.yaml validation
- [ ] **Environment Setup** - .env.example files are complete

## Running All Tests

To run all tests at once:

```bash
cd packages/cli-launcher/tests
for test in test-*.sh; do
  echo "Running $test..."
  ./"$test"
  echo ""
done
```

## CI Integration

These tests are currently manual. Future work could integrate them into:
- Pre-publish checks (npm prepublishOnly script)
- GitHub Actions workflow
- Turborepo test pipeline
