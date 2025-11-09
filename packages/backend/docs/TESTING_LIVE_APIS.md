# Live API Testing Guide for Generators

This guide explains how to test generators with real provider APIs (Replicate, Fal.ai, OpenAI, etc.) rather than mocked responses.

## Overview

Boards includes two types of generator tests:

1. **Unit tests** (`test_<generator>.py`) - Use mocks, run by default, fast and free
2. **Live API tests** (`test_<generator>_live.py`) - Call real APIs, opt-in only, consume credits

Live API tests are **never run by default**. They must be explicitly invoked and require valid API keys.

## When to Run Live API Tests

Run live API tests when:

- ✅ You've modified a generator implementation
- ✅ You've updated a provider SDK dependency
- ✅ You want to verify real API connectivity
- ✅ You're debugging unexpected behavior in production
- ✅ Before releasing a new generator to production

**Don't run live tests:**

- ❌ During regular development (use unit tests instead)
- ❌ In pre-commit hooks
- ❌ As part of `make test` or `make test-backend`
- ❌ In CI/CD pipelines (unless explicitly configured)

## Setting Up API Keys

Live tests require provider API keys. There are two ways to configure them:

### Option 1: Via Environment Variables (Direct)

```bash
# Replicate
export REPLICATE_API_TOKEN="r8_..."

# Fal.ai
export FAL_KEY="..."

# OpenAI
export OPENAI_API_KEY="sk-..."
```

### Option 2: Via Boards Configuration (Recommended)

```bash
# Single key
export BOARDS_GENERATOR_API_KEYS='{"REPLICATE_API_TOKEN": "r8_..."}'

# Multiple keys (JSON format)
export BOARDS_GENERATOR_API_KEYS='{
  "REPLICATE_API_TOKEN": "r8_...",
  "FAL_KEY": "...",
  "OPENAI_API_KEY": "sk-..."
}'
```

Or add to your `.env` file:

```bash
BOARDS_GENERATOR_API_KEYS={"REPLICATE_API_TOKEN": "r8_..."}
```

The Boards config system will automatically sync these keys to `os.environ` for third-party SDKs.

## Running Live API Tests

### Run a Single Generator's Live Test

This is the **most common workflow** when developing generators:

```bash
# After modifying flux_pro.py
export REPLICATE_API_TOKEN="r8_..."
pytest tests/generators/implementations/test_flux_pro_live.py -v -m live_api
```

Example output:
```
tests/generators/implementations/test_flux_pro_live.py::TestFluxProGeneratorLive::test_generate_basic PASSED
tests/generators/implementations/test_flux_pro_live.py::TestFluxProGeneratorLive::test_generate_with_aspect_ratio PASSED
```

If the API key is missing, tests will be skipped:
```
tests/generators/implementations/test_flux_pro_live.py::TestFluxProGeneratorLive::test_generate_basic SKIPPED (REPLICATE_API_TOKEN not set)
```

### Run All Live Tests for One Provider

```bash
# All Replicate generators
export REPLICATE_API_TOKEN="r8_..."
pytest -m live_replicate -v

# All Fal generators
export FAL_KEY="..."
pytest -m live_fal -v

# All OpenAI generators
export OPENAI_API_KEY="sk-..."
pytest -m live_openai -v
```

### Run All Live API Tests (Rarely Used)

```bash
# Requires ALL provider API keys to be set
export REPLICATE_API_TOKEN="r8_..."
export FAL_KEY="..."
export OPENAI_API_KEY="sk-..."

pytest -m live_api -v
```

⚠️ **Warning:** This will consume credits across all providers!

### Run With Extra Verbosity

```bash
# Show detailed output including print statements and logs
pytest tests/generators/implementations/test_flux_pro_live.py -v -s -m live_api

# Show full error tracebacks
pytest tests/generators/implementations/test_flux_pro_live.py -v --tb=long -m live_api
```

## Cost Management

Live API tests consume real provider credits. Follow these practices:

### 1. Cost Logging

All live tests log estimated costs before running:

```python
@pytest.mark.asyncio
async def test_generate_basic(self, cost_logger):
    cost_logger("replicate-flux-pro", 0.055)
    # Test implementation...
```

Look for log output like:
```
WARNING live_api_test_cost generator=replicate-flux-pro estimated_cost_usd=0.055
```

### 2. Minimal Inputs

Tests use minimal/cheap parameters:

```python
# ✅ Good - Simple prompt, small size
inputs = FluxProInput(
    prompt="A simple red circle",
    aspect_ratio="1:1",
)

# ❌ Bad - Complex prompt, large size, multiple images
inputs = FluxProInput(
    prompt="Ultra detailed 8K photorealistic...",
    aspect_ratio="21:9",
    num_images=10,
)
```

### 3. Approximate Costs (as of 2024)

| Provider | Generator | Estimated Cost |
|----------|-----------|----------------|
| Replicate | flux-pro | $0.055/image |
| Fal.ai | nano-banana | $0.05/image |
| Fal.ai | nano-banana-edit | $0.05/image |
| OpenAI | dalle3 | $0.04-$0.08/image |
| OpenAI | whisper | $0.006/minute |

Running a full test suite for one generator typically costs **$0.10 - $0.30**.

## Verifying Tests Are Excluded

Live tests are **automatically excluded by default** thanks to `pytest.ini` configuration:

```bash
# All of these commands exclude live tests by default:
make test-backend
cd packages/backend && uv run pytest
cd packages/backend && uv run pytest tests/
```

You should see output like:
```
337/350 tests collected (13 deselected)
```

The 13 deselected tests are the live API tests.

Check pytest markers to see which tests would run:
```bash
# List all live API tests (without running them)
pytest --collect-only -m live_api

# Verify default behavior excludes live tests
pytest --collect-only -q | tail -1
# Should show: "337/350 tests collected (13 deselected)"
```

## Troubleshooting

### Tests Are Skipped

**Problem:** All tests show `SKIPPED` status

**Cause:** API key not found

**Solution:**
```bash
# Verify API key is set
echo $REPLICATE_API_TOKEN

# If empty, export it
export REPLICATE_API_TOKEN="r8_..."

# Or check Boards config
python -c "from boards.config import settings; print(settings.generator_api_keys)"
```

### API Errors

**Problem:** Test fails with authentication error

**Solutions:**
1. Verify API key is valid (not expired/revoked)
2. Check API key has correct permissions
3. Verify provider account has sufficient credits

**Example error:**
```
ValueError: API configuration invalid. Missing REPLICATE_API_TOKEN
```

### Unexpected Costs

**Problem:** Tests consumed more credits than expected

**Prevention:**
1. Always read the test file first to understand what it does
2. Check cost logger output before tests run
3. Use single generator tests, not `pytest -m live_api`
4. Start with one test function: `pytest test_flux_pro_live.py::TestFluxProGeneratorLive::test_estimate_cost`

## Adding Live Tests for New Generators

When creating a new generator, follow these steps:

### 1. Create the Live Test File

```bash
# Template: test_<generator>_live.py
touch tests/generators/implementations/test_my_generator_live.py
```

### 2. Use This Template

```python
"""
Live API tests for MyGenerator.

To run: pytest tests/generators/implementations/test_my_generator_live.py -v -m live_api
"""
import pytest
from boards.config import initialize_generator_api_keys
from boards.generators.implementations.provider.type.my_generator import (
    MyGeneratorInput,
    MyGenerator,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_<provider>]


class TestMyGeneratorLive:
    """Live API tests for MyGenerator."""

    def setup_method(self):
        """Set up generator and sync API keys."""
        self.generator = MyGenerator()
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(
        self, skip_if_no_<provider>_key, dummy_context, cost_logger
    ):
        """Test basic generation with minimal parameters."""
        # Log cost
        estimated_cost = await self.generator.estimate_cost(
            MyGeneratorInput(prompt="test")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Minimal input to reduce cost
        inputs = MyGeneratorInput(prompt="Simple test")

        # Execute
        result = await self.generator.generate(inputs, dummy_context)

        # Verify
        assert result.outputs is not None
        assert len(result.outputs) > 0
        assert result.outputs[0].storage_url.startswith("https://")
```

### 3. Add Provider-Specific Skip Fixture (If New Provider)

If adding a new provider (not Replicate/Fal/OpenAI), add to `conftest.py`:

```python
@pytest.fixture
def skip_if_no_my_provider_key():
    """Skip test if MY_PROVIDER_API_KEY is not available."""
    if not check_api_key("MY_PROVIDER_API_KEY"):
        pytest.skip("MY_PROVIDER_API_KEY not set, skipping live API test")
```

### 4. Add Pytest Marker (If New Provider)

Update `pytest.ini`:

```ini
markers =
    ...
    live_my_provider: marks tests that call MyProvider API (subset of live_api)
```

### 5. Test Your Live Test

```bash
# Without API key - should skip
pytest tests/generators/implementations/test_my_generator_live.py -v -m live_api

# With API key - should run
export MY_PROVIDER_API_KEY="..."
pytest tests/generators/implementations/test_my_generator_live.py -v -m live_api
```

## Best Practices

### DO:
- ✅ Run live tests individually after modifying a generator
- ✅ Use minimal inputs to reduce costs
- ✅ Log estimated costs before running tests
- ✅ Keep live tests simple and focused
- ✅ Verify tests are skipped when API keys are missing
- ✅ Document expected costs in test docstrings

### DON'T:
- ❌ Run `pytest -m live_api` unless you mean it
- ❌ Add live tests to CI without explicit approval
- ❌ Use live tests for load/performance testing
- ❌ Test with expensive parameters (high quality, large sizes, etc.)
- ❌ Create hundreds of test cases for one generator
- ❌ Commit API keys to the repository

## Continuous Integration (Optional)

If you want to run live tests in CI (not recommended for most projects):

### GitHub Actions Example

```yaml
name: Live API Tests (Manual)

on:
  workflow_dispatch:  # Manual trigger only

jobs:
  live-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          cd packages/backend
          pip install uv
          uv sync
      - name: Run Replicate live tests
        env:
          REPLICATE_API_TOKEN: ${{ secrets.REPLICATE_API_TOKEN }}
        run: |
          cd packages/backend
          uv run pytest -m live_replicate --tb=short
```

**Important:** Only run on:
- Manual workflow dispatch
- Scheduled (e.g., nightly) runs
- Release branches

**Never** run live tests on every PR or commit.

## Summary

- Live API tests verify real connectivity to provider APIs
- They are **opt-in only** and never run by default
- Set up API keys via environment variables or Boards config
- Run individual tests after modifying generators: `pytest test_flux_pro_live.py -v -m live_api`
- Monitor costs using cost logger output
- Use minimal inputs to reduce expenses
- Follow the template when adding tests for new generators

For questions or issues, see the main [generator testing documentation](../../../apps/docs/docs/generators/testing.md).
