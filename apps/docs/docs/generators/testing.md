# Testing Generators

Comprehensive testing ensures your generators work reliably and handle edge cases gracefully. This guide covers testing patterns, mocking strategies, and best practices.

## Testing Philosophy

Good generator tests should verify:

1. **Input validation** works correctly
2. **Core generation logic** produces expected outputs  
3. **Error conditions** are handled appropriately
4. **Cost estimation** is accurate
5. **Integration** with provider SDKs works
6. **Edge cases** don't break the generator

## Test Structure

### Basic Test Setup

```python
import pytest
import os
from unittest.mock import patch, AsyncMock, MagicMock

from boards.generators.implementations.image.my_generator import (
    MyGenerator,
    MyInput,
    MyOutput,
)
from boards.generators.artifacts import ImageArtifact


class TestMyGenerator:
    def setup_method(self):
        """Set up fresh generator for each test."""
        self.generator = MyGenerator()
    
    def teardown_method(self):
        """Clean up after each test."""
        # Clean up any temporary files, reset state, etc.
        pass
```

### Test Organization

Organize tests into logical groups:

```python
class TestMyGenerator:
    """Tests for MyGenerator."""
    
    # Metadata and schema tests
    def test_generator_metadata(self):
        """Test generator has correct metadata."""
    
    def test_input_schema(self):
        """Test input schema validation."""
    
    def test_output_schema(self):
        """Test output schema structure."""
    
    # Generation tests
    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful generation."""
    
    @pytest.mark.asyncio
    async def test_generate_with_optional_params(self):
        """Test generation with optional parameters."""
    
    # Error condition tests
    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test error when API key is missing."""
    
    @pytest.mark.asyncio
    async def test_generate_provider_error(self):
        """Test handling of provider API errors."""
    
    # Cost estimation tests
    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation logic."""
```

## Testing Input Validation

### Schema Validation Tests

```python
def test_valid_input_creation(self):
    """Test creating valid input objects."""
    input_obj = MyInput(
        prompt="A beautiful sunset",
        style="realistic",
        quality=0.8
    )
    
    assert input_obj.prompt == "A beautiful sunset"
    assert input_obj.style == "realistic"
    assert input_obj.quality == 0.8


def test_input_defaults(self):
    """Test input default values."""
    input_obj = MyInput(prompt="Test prompt")
    
    assert input_obj.style == "standard"  # Default value
    assert input_obj.quality == 0.75     # Default value


def test_input_validation_errors(self):
    """Test input validation catches errors."""
    # Empty prompt should fail
    with pytest.raises(ValidationError):
        MyInput(prompt="")
    
    # Quality out of range should fail
    with pytest.raises(ValidationError):
        MyInput(prompt="Test", quality=1.5)
    
    # Invalid style should fail
    with pytest.raises(ValidationError):
        MyInput(prompt="Test", style="invalid_style")


def test_custom_validation(self):
    """Test custom field validation."""
    # Test that custom validator works
    with pytest.raises(ValidationError, match="inappropriate content"):
        MyInput(prompt="This contains inappropriate content")


def test_artifact_input_validation(self):
    """Test artifact input validation."""
    valid_image = ImageArtifact(
        generation_id="test",
        storage_url="https://example.com/image.png",
        width=512,
        height=512,
        format="png"
    )
    
    input_obj = MyInputWithArtifact(
        prompt="Test",
        reference_image=valid_image
    )
    
    assert input_obj.reference_image == valid_image
```

### JSON Schema Generation Tests

```python
def test_json_schema_generation(self):
    """Test that input schema generates valid JSON schema."""
    schema = MyInput.model_json_schema()
    
    # Check basic structure
    assert schema["type"] == "object"
    assert "properties" in schema
    assert "required" in schema
    
    # Check specific fields
    prompt_field = schema["properties"]["prompt"]
    assert prompt_field["type"] == "string"
    assert "description" in prompt_field
    
    # Check constraints
    quality_field = schema["properties"]["quality"]
    assert quality_field["minimum"] == 0.0
    assert quality_field["maximum"] == 1.0
    assert quality_field["default"] == 0.75
    
    # Check required fields
    assert "prompt" in schema["required"]
```

## Testing Generation Logic

### Successful Generation Tests

```python
@pytest.mark.asyncio
async def test_generate_success(self):
    """Test successful image generation."""
    inputs = MyInput(
        prompt="A red apple on a wooden table",
        style="photorealistic",
        quality=0.8
    )
    
    fake_result_url = "https://provider.com/result/fake_image.png"
    
    with patch.dict(os.environ, {"PROVIDER_API_KEY": "fake-key"}):
        with patch('provider_sdk.generate') as mock_generate:
            with patch('my_generator.store_image_result') as mock_store:
                # Setup mocks
                mock_generate.return_value = fake_result_url
                
                mock_artifact = ImageArtifact(
                    generation_id="test_gen",
                    storage_url=fake_result_url,
                    width=1024,
                    height=1024,
                    format="png"
                )
                mock_store.return_value = mock_artifact
                
                # Execute generation
                result = await self.generator.generate(inputs)
                
                # Verify result structure
                assert isinstance(result, MyOutput)
                assert isinstance(result.image, ImageArtifact)
                assert result.image.storage_url == fake_result_url
                
                # Verify provider was called correctly
                mock_generate.assert_called_once()
                call_kwargs = mock_generate.call_args.kwargs
                assert call_kwargs["prompt"] == inputs.prompt
                assert call_kwargs["style"] == inputs.style
                assert call_kwargs["quality"] == inputs.quality
                
                # Verify storage was called correctly
                mock_store.assert_called_once_with(
                    storage_url=fake_result_url,
                    format="png",
                    generation_id="temp_gen_id",
                    width=1024,
                    height=1024
                )


@pytest.mark.asyncio
async def test_generate_with_artifact_input(self):
    """Test generation with artifact inputs."""
    reference_image = ImageArtifact(
        generation_id="ref_gen",
        storage_url="https://example.com/reference.png",
        width=512,
        height=512,
        format="png"
    )
    
    inputs = MyInputWithArtifact(
        prompt="Transform this image",
        reference_image=reference_image,
        strength=0.7
    )
    
    with patch.dict(os.environ, {"API_KEY": "fake-key"}):
        with patch('boards.generators.resolution.resolve_artifact') as mock_resolve:
            with patch('provider_sdk.transform') as mock_transform:
                with patch('my_generator.store_image_result') as mock_store:
                    # Mock artifact resolution
                    mock_resolve.return_value = "/tmp/reference_image.png"
                    
                    # Mock provider response
                    mock_transform.return_value = "https://result.com/output.png"
                    
                    # Mock storage
                    mock_artifact = ImageArtifact(
                        generation_id="test",
                        storage_url="https://result.com/output.png",
                        width=512,
                        height=512,
                        format="png"
                    )
                    mock_store.return_value = mock_artifact
                    
                    # Execute
                    result = await self.generator.generate(inputs)
                    
                    # Verify artifact was resolved
                    mock_resolve.assert_called_once_with(reference_image)
                    
                    # Verify provider was called with resolved path
                    mock_transform.assert_called_once()
                    call_kwargs = mock_transform.call_args.kwargs
                    assert call_kwargs["image_path"] == "/tmp/reference_image.png"
                    assert call_kwargs["prompt"] == inputs.prompt
                    assert call_kwargs["strength"] == inputs.strength
```

### Async Testing Patterns

```python
@pytest.mark.asyncio
async def test_async_provider_call(self):
    """Test async provider SDK integration."""
    inputs = MyInput(prompt="Test prompt")
    
    with patch.dict(os.environ, {"API_KEY": "fake-key"}):
        with patch('provider_sdk.AsyncClient') as mock_client_class:
            # Create async mock
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock async method
            mock_client.generate.return_value = "result_url"
            
            with patch('my_generator.store_image_result') as mock_store:
                mock_store.return_value = create_mock_artifact()
                
                result = await self.generator.generate(inputs)
                
                # Verify async client was used
                mock_client_class.assert_called_once()
                mock_client.generate.assert_called_once()


@pytest.mark.asyncio
async def test_concurrent_generations(self):
    """Test multiple concurrent generations."""
    import asyncio
    
    inputs_list = [
        MyInput(prompt=f"Test prompt {i}")
        for i in range(3)
    ]
    
    with patch.dict(os.environ, {"API_KEY": "fake-key"}):
        with patch('provider_sdk.generate') as mock_generate:
            with patch('my_generator.store_image_result') as mock_store:
                # Setup mocks for multiple calls
                mock_generate.side_effect = [
                    "result_1.png",
                    "result_2.png", 
                    "result_3.png"
                ]
                mock_store.side_effect = [
                    create_mock_artifact("result_1.png"),
                    create_mock_artifact("result_2.png"),
                    create_mock_artifact("result_3.png")
                ]
                
                # Run concurrent generations
                tasks = [
                    self.generator.generate(inputs)
                    for inputs in inputs_list
                ]
                results = await asyncio.gather(*tasks)
                
                # Verify all completed successfully
                assert len(results) == 3
                assert all(isinstance(r, MyOutput) for r in results)
                
                # Verify all provider calls were made
                assert mock_generate.call_count == 3
```

## Testing Error Conditions

### Environment and Configuration Errors

```python
@pytest.mark.asyncio
async def test_missing_api_key(self):
    """Test error when required API key is missing."""
    inputs = MyInput(prompt="Test prompt")
    
    # Clear environment variables
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError) as exc_info:
            await self.generator.generate(inputs)
        
        assert "API_KEY" in str(exc_info.value)
        assert "required" in str(exc_info.value)


@pytest.mark.asyncio
async def test_invalid_api_key(self):
    """Test handling of invalid API key."""
    inputs = MyInput(prompt="Test prompt")
    
    with patch.dict(os.environ, {"API_KEY": "invalid-key"}):
        with patch('provider_sdk.generate') as mock_generate:
            # Mock authentication error
            mock_generate.side_effect = provider_sdk.AuthenticationError("Invalid API key")
            
            with pytest.raises(ValueError) as exc_info:
                await self.generator.generate(inputs)
            
            assert "Invalid API key" in str(exc_info.value)
            assert "check" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_missing_dependency(self):
    """Test error when required dependency is missing."""
    inputs = MyInput(prompt="Test prompt")
    
    with patch.dict(os.environ, {"API_KEY": "valid-key"}):
        # Mock import error
        with patch('builtins.__import__') as mock_import:
            mock_import.side_effect = ImportError("No module named 'provider_sdk'")
            
            with pytest.raises(ValueError) as exc_info:
                await self.generator.generate(inputs)
            
            assert "not installed" in str(exc_info.value)
            assert "pip install" in str(exc_info.value)
```

### Provider API Errors

```python
@pytest.mark.asyncio
async def test_rate_limit_error(self):
    """Test handling of rate limit errors."""
    inputs = MyInput(prompt="Test prompt")
    
    with patch.dict(os.environ, {"API_KEY": "valid-key"}):
        with patch('provider_sdk.generate') as mock_generate:
            # Mock rate limit error with retry info
            error = provider_sdk.RateLimitError("Rate limited")
            error.retry_after = 60
            mock_generate.side_effect = error
            
            with pytest.raises(ValueError) as exc_info:
                await self.generator.generate(inputs)
            
            error_msg = str(exc_info.value)
            assert "rate limit" in error_msg.lower()
            assert "60" in error_msg  # Retry time


@pytest.mark.asyncio
async def test_quota_exceeded_error(self):
    """Test handling of quota/credit errors."""
    inputs = MyInput(prompt="Test prompt")
    
    with patch.dict(os.environ, {"API_KEY": "valid-key"}):
        with patch('provider_sdk.generate') as mock_generate:
            mock_generate.side_effect = provider_sdk.InsufficientCreditsError("Out of credits")
            
            with pytest.raises(ValueError) as exc_info:
                await self.generator.generate(inputs)
            
            assert "credits" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_provider_validation_error(self):
    """Test handling of provider input validation errors."""
    inputs = MyInput(prompt="Test prompt")
    
    with patch.dict(os.environ, {"API_KEY": "valid-key"}):
        with patch('provider_sdk.generate') as mock_generate:
            mock_generate.side_effect = provider_sdk.ValidationError("Invalid prompt format")
            
            with pytest.raises(ValueError) as exc_info:
                await self.generator.generate(inputs)
            
            assert "Invalid input" in str(exc_info.value)


@pytest.mark.asyncio
async def test_unexpected_provider_error(self):
    """Test handling of unexpected provider errors."""
    inputs = MyInput(prompt="Test prompt")
    
    with patch.dict(os.environ, {"API_KEY": "valid-key"}):
        with patch('provider_sdk.generate') as mock_generate:
            # Unexpected error type
            mock_generate.side_effect = ConnectionError("Network timeout")
            
            with pytest.raises(RuntimeError) as exc_info:
                await self.generator.generate(inputs)
            
            error_msg = str(exc_info.value)
            assert "unexpected error" in error_msg.lower()
            assert "try again" in error_msg.lower()
```

### Artifact Resolution Errors

```python
@pytest.mark.asyncio
async def test_artifact_resolution_failure(self):
    """Test error when artifact cannot be resolved."""
    bad_artifact = ImageArtifact(
        generation_id="test",
        storage_url="https://nonexistent.com/missing.png",
        width=512,
        height=512,
        format="png"
    )
    
    inputs = MyInputWithArtifact(
        prompt="Test",
        reference_image=bad_artifact
    )
    
    with patch.dict(os.environ, {"API_KEY": "valid-key"}):
        with patch('boards.generators.resolution.resolve_artifact') as mock_resolve:
            # Mock resolution failure
            mock_resolve.side_effect = httpx.HTTPStatusError(
                "404 Not Found",
                request=MagicMock(),
                response=MagicMock()
            )
            
            with pytest.raises(httpx.HTTPStatusError):
                await self.generator.generate(inputs)


@pytest.mark.asyncio  
async def test_text_artifact_resolution_error(self):
    """Test error when trying to resolve TextArtifact."""
    text_artifact = TextArtifact(
        generation_id="test",
        content="Some text"
    )
    
    # This should raise an error since TextArtifact can't be resolved to file
    with pytest.raises(ValueError, match="TextArtifact cannot be resolved"):
        await resolve_artifact(text_artifact)
```

## Testing Cost Estimation

### Basic Cost Tests

```python
@pytest.mark.asyncio
async def test_estimate_cost_basic(self):
    """Test basic cost estimation."""
    inputs = MyInput(prompt="Test prompt")
    
    cost = await self.generator.estimate_cost(inputs)
    
    assert isinstance(cost, float)
    assert cost > 0
    assert cost < 10  # Sanity check - shouldn't be crazy expensive


@pytest.mark.asyncio
async def test_estimate_cost_with_parameters(self):
    """Test cost estimation varies with parameters."""
    base_input = MyInput(prompt="Test", quality=0.5)
    high_quality_input = MyInput(prompt="Test", quality=1.0)
    
    base_cost = await self.generator.estimate_cost(base_input)
    high_cost = await self.generator.estimate_cost(high_quality_input)
    
    # Higher quality should cost more
    assert high_cost > base_cost


@pytest.mark.asyncio
async def test_estimate_cost_with_size(self):
    """Test cost estimation considers image size."""
    small_input = MyInput(prompt="Test", width=512, height=512)
    large_input = MyInput(prompt="Test", width=1024, height=1024)
    
    small_cost = await self.generator.estimate_cost(small_input)
    large_cost = await self.generator.estimate_cost(large_input)
    
    # Larger images should cost more
    assert large_cost > small_cost


@pytest.mark.asyncio
async def test_cost_estimation_accuracy(self):
    """Test that cost estimation is reasonably accurate."""
    inputs = MyInput(prompt="Test", quality=0.75, steps=50)
    
    # Test multiple times to ensure consistency
    costs = []
    for _ in range(5):
        cost = await self.generator.estimate_cost(inputs)
        costs.append(cost)
    
    # All estimates should be the same (deterministic)
    assert len(set(costs)) == 1
    
    # Cost should be in reasonable range
    cost = costs[0]
    assert 0.001 <= cost <= 1.0  # Between $0.001 and $1.00
```

## Mocking Strategies

### Provider SDK Mocking

```python
class MockProviderSDK:
    """Mock provider SDK for testing."""
    
    def __init__(self, api_key):
        self.api_key = api_key
        if api_key == "invalid":
            raise provider_sdk.AuthenticationError("Invalid API key")
    
    async def generate(self, **kwargs):
        """Mock generate method."""
        if "error" in kwargs.get("prompt", ""):
            raise provider_sdk.ValidationError("Invalid prompt")
        
        return f"https://mock-result.com/{hash(str(kwargs))}.png"


@pytest.fixture
def mock_provider():
    """Fixture providing mock provider."""
    with patch('provider_sdk.Client', MockProviderSDK):
        yield MockProviderSDK


@pytest.mark.asyncio
async def test_with_mock_provider(mock_provider):
    """Test using provider fixture."""
    inputs = MyInput(prompt="Test prompt")
    
    with patch.dict(os.environ, {"API_KEY": "valid-key"}):
        with patch('my_generator.store_image_result') as mock_store:
            mock_store.return_value = create_mock_artifact()
            
            result = await self.generator.generate(inputs)
            assert isinstance(result, MyOutput)
```

### Artifact Mocking

```python
def create_mock_image_artifact(
    generation_id="test_gen",
    storage_url="https://mock.com/image.png", 
    width=1024,
    height=1024,
    format="png"
):
    """Helper to create mock image artifacts."""
    return ImageArtifact(
        generation_id=generation_id,
        storage_url=storage_url,
        width=width,
        height=height,
        format=format
    )


def create_mock_video_artifact(
    generation_id="test_gen",
    storage_url="https://mock.com/video.mp4",
    width=1920,
    height=1080,
    duration=30.0,
    fps=24.0
):
    """Helper to create mock video artifacts."""
    return VideoArtifact(
        generation_id=generation_id,
        storage_url=storage_url,
        width=width,
        height=height,
        format="mp4",
        duration=duration,
        fps=fps
    )


@pytest.fixture
def sample_artifacts():
    """Fixture providing sample artifacts for testing."""
    return {
        "image": create_mock_image_artifact(),
        "video": create_mock_video_artifact(),
        "audio": AudioArtifact(
            generation_id="test",
            storage_url="https://mock.com/audio.mp3",
            format="mp3",
            duration=120.0,
            sample_rate=44100,
            channels=2
        )
    }
```

## Integration Testing

### End-to-End Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_generation_flow(self):
    """Test complete generation flow with real dependencies."""
    # Skip if no API key provided
    api_key = os.getenv("PROVIDER_API_KEY")
    if not api_key:
        pytest.skip("PROVIDER_API_KEY not provided for integration test")
    
    inputs = MyInput(
        prompt="A simple test image",
        quality=0.5  # Use lowest quality for faster testing
    )
    
    # Run actual generation
    result = await self.generator.generate(inputs)
    
    # Verify result structure
    assert isinstance(result, MyOutput)
    assert isinstance(result.image, ImageArtifact)
    assert result.image.storage_url is not None
    assert result.image.width > 0
    assert result.image.height > 0
    
    # Verify cost estimation is reasonable
    estimated_cost = await self.generator.estimate_cost(inputs)
    assert 0.001 <= estimated_cost <= 1.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_artifact_chaining(self):
    """Test using output of one generator as input to another."""
    if not os.getenv("PROVIDER_API_KEY"):
        pytest.skip("API key required for integration test")
    
    # Generate initial image
    text_to_image_input = TextToImageInput(prompt="A red apple")
    image_result = await text_to_image_generator.generate(text_to_image_input)
    
    # Use generated image as input to style transfer
    style_input = StyleTransferInput(
        content_image=image_result.image,
        style_prompt="oil painting style"
    )
    style_result = await style_transfer_generator.generate(style_input)
    
    # Verify the chain worked
    assert isinstance(style_result.image, ImageArtifact)
    assert style_result.image.generation_id != image_result.image.generation_id
```

## Test Configuration

### pytest Configuration

```ini
# pytest.ini
[tool:pytest]
markers = 
    asyncio: mark test as async
    integration: mark test as integration test (requires API keys)
    slow: mark test as slow running

asyncio_mode = auto

# Skip integration tests by default
addopts = -m "not integration"

# Test discovery
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
```

### Environment Setup

```python
# conftest.py
import pytest
import os
from unittest.mock import patch

@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean environment for each test."""
    # Clear relevant environment variables
    env_vars_to_clear = [
        "PROVIDER_API_KEY",
        "ANOTHER_API_KEY", 
    ]
    
    original_values = {}
    for var in env_vars_to_clear:
        original_values[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]
    
    yield
    
    # Restore original values
    for var, value in original_values.items():
        if value is not None:
            os.environ[var] = value


@pytest.fixture
def mock_storage():
    """Mock the storage system."""
    with patch('boards.generators.resolution.store_image_result') as mock_store:
        mock_store.return_value = create_mock_image_artifact()
        yield mock_store
```

## Running Tests

### Local Testing

```bash
# Run all generator tests
pytest tests/generators/ -v

# Run specific generator tests
pytest tests/generators/implementations/test_my_generator.py -v

# Run with coverage
pytest tests/generators/ --cov=src/boards/generators --cov-report=html

# Run only fast tests
pytest tests/generators/ -m "not slow and not integration"

# Run integration tests (requires API keys)
pytest tests/generators/ -m integration -v
```

### CI/CD Testing

```yaml
# .github/workflows/test.yml
name: Generator Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-asyncio pytest-cov
      
      - name: Run unit tests
        run: pytest tests/generators/ -m "not integration" --cov
      
      - name: Run integration tests
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        env:
          PROVIDER_API_KEY: ${{ secrets.PROVIDER_API_KEY }}
        run: pytest tests/generators/ -m integration
```

## Live API Testing (Optional)

In addition to unit tests with mocked providers, Boards supports **live API tests** that make actual calls to provider APIs (Replicate, Fal.ai, OpenAI, etc.). These tests verify real connectivity and API response formats.

:::warning Cost Warning
Live API tests consume real API credits and should **never run by default**. They are opt-in only and must be explicitly invoked.
:::

### When to Use Live Tests

Run live API tests when:

- ✅ You've modified a generator implementation
- ✅ You've updated a provider SDK dependency
- ✅ You want to verify real API connectivity
- ✅ You're debugging unexpected production behavior
- ✅ Before releasing a generator to production

**Don't use for:**

- ❌ Regular development (use unit tests instead)
- ❌ Pre-commit hooks or standard CI runs
- ❌ Load/performance testing

### Running Live Tests

Live tests are marked with `@pytest.mark.live_api` and provider-specific markers (`live_replicate`, `live_fal`, `live_openai`). They are **excluded from default test runs**.

```bash
# Run a single generator's live test (most common)
export REPLICATE_API_TOKEN="r8_..."
pytest tests/generators/implementations/test_flux_pro_live.py -v

# Or using Boards configuration
export BOARDS_GENERATOR_API_KEYS='{"REPLICATE_API_TOKEN": "r8_..."}'
pytest tests/generators/implementations/test_flux_pro_live.py -v

# Run all live tests for one provider
pytest -m live_replicate -v

# Verify live tests are excluded from default runs
make test-backend  # Should NOT run live tests
```

### Live Test Structure

Live tests follow a similar structure to unit tests but make real API calls:

```python
"""
Live API tests for MyGenerator.

To run: pytest tests/generators/implementations/test_my_generator_live.py -v
"""
import pytest
from boards.config import initialize_generator_api_keys
from boards.generators.implementations.provider.type.my_generator import (
    MyGenerator,
    MyInput,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_provider]


class TestMyGeneratorLive:
    """Live API tests for MyGenerator."""

    def setup_method(self):
        """Set up generator and sync API keys."""
        self.generator = MyGenerator()
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(
        self, skip_if_no_provider_key, dummy_context, cost_logger
    ):
        """Test basic generation with minimal parameters."""
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            MyInput(prompt="test")
        )
        cost_logger(self.generator.name, estimated_cost)

        # Use minimal inputs to reduce cost
        inputs = MyInput(prompt="Simple test prompt")

        # Execute actual API call
        result = await self.generator.generate(inputs, dummy_context)

        # Verify real response structure
        assert result.outputs is not None
        assert len(result.outputs) > 0
        assert result.outputs[0].storage_url is not None
```

### Cost Management

Live tests log estimated costs before running:

```python
# Tests automatically log costs
@pytest.mark.asyncio
async def test_generate_basic(self, cost_logger):
    cost_logger("replicate-flux-pro", 0.055)
    # ... test implementation
```

Best practices:

- Use minimal/cheap parameters (low quality, small sizes, single outputs)
- Test one generator at a time
- Review cost estimates in logs before running
- Typical cost per test: $0.10 - $0.30

### Complete Documentation

For detailed information on live API testing, including:

- Setting up API keys
- Adding tests for new generators
- Troubleshooting common issues
- CI/CD integration (optional)

See the [Live API Testing Guide](./live-api-testing.md).

---

This comprehensive testing approach ensures your generators are reliable, handle errors gracefully, and work correctly with the Boards system!
