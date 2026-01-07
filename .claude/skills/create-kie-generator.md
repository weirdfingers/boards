# Create Kie.ai Generator

This skill creates a new Kie.ai generator implementation with all necessary files, tests, and configuration.

## Overview

Creates a complete Kie.ai generator following the established patterns from the Boards project:

- Generator implementation with automatic artifact resolution
- Comprehensive test suite
- Module exports
- Configuration in generators.yaml

Kie.ai provides access to multiple AI models through two API patterns:
- **Market API**: Unified endpoint for 30+ models (Kling, Sora2, Hailuo, Bytedance, etc.)
- **Dedicated APIs**: Specialized endpoints (Veo3, Suno, Runway, Luma, Flux Kontext, 4o Image)

## Instructions

### Step 1: Get Kie.ai Model Information

Ask the user for the Kie.ai model name and documentation if not already provided:

```
What Kie.ai model would you like to create a generator for?

Examples:
- Market models: google/nano-banana-edit, kling/text-to-video, sora2/pro-text-to-video
- Dedicated models: veo3, suno, runway, luma

Please also provide:
1. The documentation URL (e.g., https://docs.kie.ai/market/google/nano-banana-edit)
2. Copy the API request/response documentation from the page (click "Copy" in the docs)
```

### Step 2: Analyze Kie.ai API Documentation

The user will provide copied documentation from the Kie.ai docs. Analyze this to extract:

**From the documentation, determine:**

1. **API Pattern** - Which API family does this model use?
   - **Market API**: Uses `/api/v1/jobs/createTask` endpoint
     - Status check: `/api/v1/jobs/recordInfo?taskId={id}`
     - Request includes `model` parameter in body
   - **Dedicated API**: Uses model-specific endpoint (e.g., `/api/v1/veo/generate`)
     - Status check: Model-specific endpoint (e.g., `/api/v1/veo/record-info?taskId={id}`)
     - Request does NOT include `model` parameter

2. **Model Identifier**:
   - Market API: The `model` field value (e.g., `"google/nano-banana-edit"`)
   - Dedicated API: The endpoint path (e.g., `"veo3"`)

3. **Input Schema**:
   - Extract all parameters from the request body documentation
   - Identify required vs optional fields
   - Note validation constraints (min/max, enum values)
   - **Artifact inputs**: Any field ending in `_url`, `_urls`, `Url`, `Urls`, `imageUrl`, `videoUrl`, etc.
   - Types: string, integer, float, boolean, array, object

4. **Output Schema**:
   - Market API typically returns:
     ```json
     {
       "code": 200,
       "data": {
         "taskId": "...",
         "result": { /* model-specific output */ }
       }
     }
     ```
   - Dedicated API varies by model

5. **Artifact Type**: Determine from model name/description
   - `image` - image generation models
   - `video` - video generation models
   - `audio` - audio/music generation models
   - `text` - text generation models

6. **Callback Support**: Check if `callBackUrl` parameter is documented

### Step 3: Fetch Pricing Information

Try to scrape pricing from https://kie.ai/pricing using WebFetch:

```python
# Search for the model name in the pricing page
# Extract cost per generation
# If not found, ask user to provide pricing manually
```

If pricing cannot be found automatically, ask the user:
```
What is the cost per generation for this model? (in USD)
If there are multiple pricing tiers or the cost varies by parameters,
please provide the base cost and explain the formula.
```

### Step 4: Determine Generator Configuration

Based on the gathered information:

1. **Generator Name** (kebab-case): Convert the model identifier
   - Market models: `kie-{provider}-{model-name}`
     - Example: `google/nano-banana-edit` → `kie-nano-banana-edit`
     - Example: `sora2/pro-text-to-video` → `kie-sora2-pro-text-to-video`
   - Dedicated models: `kie-{model-name}`
     - Example: `veo3` → `kie-veo3`
     - Example: `suno` → `kie-suno`

2. **Python Class Name** (PascalCase):
   - Example: `kie-nano-banana-edit` → `KieNanoBananaEditGenerator`
   - Example: `kie-veo3` → `KieVeo3Generator`

3. **API Pattern Configuration**:
   - Market API: Set `api_pattern = "market"`
   - Dedicated API: Set `api_pattern = "dedicated"` and specify endpoints

4. **Input Fields**: Map documentation parameters to Pydantic fields
   - Convert types (string → str, integer → int, number → float, boolean → bool)
   - Detect artifact inputs (fields ending with `url`, `Url`, etc.)
   - Replace artifact URL fields with appropriate artifact types:
     - `image_url` → `ImageArtifact`
     - `image_urls` → `list[ImageArtifact]`
     - `video_url` → `VideoArtifact`
     - `audio_url` → `AudioArtifact`
   - Preserve validation from docs

5. **Output Handling**: Based on response schema
   - Extract output artifacts (images, videos, audio)
   - Determine if single or multiple outputs
   - Extract metadata fields (width, height, duration, format, etc.)

### Step 5: Create Generator Implementation

Create the generator implementation file at:
`packages/backend/src/boards/generators/implementations/kie/{artifact_type}/{generator_name}.py`

**Important Implementation Notes:**

1. **Import Structure**:
```python
import os
from typing import Literal

from pydantic import BaseModel, Field

from ....artifacts import ImageArtifact  # Or VideoArtifact, AudioArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult
```

2. **Input Schema**:
   - All artifact URL fields should be replaced with artifact types
   - These will be automatically resolved from generation IDs
   - Preserve all validation from documentation

3. **API Client**:
   - Use `httpx` AsyncClient for HTTP requests
   - Check for `KIE_API_KEY` environment variable
   - Base URL: `https://api.kie.ai`

4. **File Uploads** (if generator accepts artifact inputs):
   - Create `packages/backend/src/boards/generators/implementations/kie/utils.py` if it doesn't exist
   - Implement `upload_artifacts_to_kie()` function similar to Fal's pattern
   - Use Kie.ai's file upload API: `https://kieai.redpandaai.co/api/file-stream-upload`
   - **IMPORTANT**: Must include `uploadPath` parameter as form data (e.g., `"boards/temp"`)
   - Files expire after 3 days on Kie.ai storage

5. **Task Submission and Polling**:
   - **Market API Pattern**:
     ```python
     # Submit
     POST /api/v1/jobs/createTask
     Body: {"model": "provider/model-name", ...params}
     Response: {"code": 200, "data": {"taskId": "..."}}

     # Poll status
     GET /api/v1/jobs/recordInfo?taskId={taskId}
     Response: {
       "code": 200,
       "data": {
         "taskId": "...",
         "status": "PENDING|PROCESSING|SUCCESS|FAILED",
         "result": { /* outputs */ }
       }
     }
     ```

   - **Dedicated API Pattern** (varies by model):
     ```python
     # Example for Veo3:
     # Submit
     POST /api/v1/veo/generate
     Body: {...params}  # No model field
     Response: {"code": 200, "data": {"taskId": "..."}}

     # Poll status
     GET /api/v1/veo/record-info?taskId={taskId}
     Response: {
       "code": 200,
       "data": {
         "successFlag": 0|1|2|3,
         "resultUrls": "[...]"
       }
     }
     ```

6. **Progress Updates**:
   - Poll every 10-30 seconds depending on expected generation time
   - Publish progress updates during polling
   - Map status to progress percentage

7. **Error Handling**:
   - Check for `code` in response (200 = success)
   - Handle common error codes:
     - 401: Unauthorized (invalid API key)
     - 402: Insufficient credits
     - 422: Validation error
     - 429: Rate limited
     - 500: Server error

Follow this template structure:

```python
"""
{Generator Description}

Based on Kie.ai's {model_name} model.
See: {documentation_url}
"""

import os
import asyncio
from typing import Literal

from pydantic import BaseModel, Field
import httpx

from ....artifacts import {ArtifactType}
from ....base import (
    BaseGenerator,
    GeneratorExecutionContext,
    GeneratorResult,
)
from .....progress.models import ProgressUpdate


class {GeneratorName}Input(BaseModel):
    """Input schema for {generator_name}.

    Artifact fields are automatically detected via type introspection
    and resolved from generation IDs to artifact objects.
    """

    # Define input fields based on Kie.ai API documentation
    # Example:
    # prompt: str = Field(description="Text prompt")
    # image_sources: list[ImageArtifact] = Field(description="Input images")


class Kie{GeneratorName}Generator(BaseGenerator[{GeneratorName}Input]):
    """Generator for {description}."""

    name = "{generator-name}"
    description = "{description}"
    artifact_type = "{artifact_type}"

    # API pattern: "market" or "dedicated"
    api_pattern = "{market|dedicated}"

    # For market models: the model identifier
    # model_id = "provider/model-name"

    # For dedicated models: custom endpoints
    # submit_endpoint = "/api/v1/model/generate"
    # status_endpoint = "/api/v1/model/record-info"

    def get_input_schema(self) -> type[{GeneratorName}Input]:
        """Return the input schema for this generator."""
        return {GeneratorName}Input

    async def generate(
        self, inputs: {GeneratorName}Input, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate {artifact_type} using Kie.ai {model_name}."""
        # Check for API key
        api_key = os.getenv("KIE_API_KEY")
        if not api_key:
            raise ValueError("API configuration invalid. Missing KIE_API_KEY environment variable")

        # If generator accepts artifact inputs, upload them to Kie.ai storage
        # from ..utils import upload_artifacts_to_kie
        # artifact_urls = await upload_artifacts_to_kie(inputs.image_sources, context)

        # Prepare request body based on API pattern
        if self.api_pattern == "market":
            # Market API: include model parameter
            body = {
                "model": self.model_id,
                # Map input fields to API parameters
                # "prompt": inputs.prompt,
                # "imageUrls": artifact_urls,
            }
            submit_url = "https://api.kie.ai/api/v1/jobs/createTask"
            status_url_template = "https://api.kie.ai/api/v1/jobs/recordInfo?taskId={task_id}"
        else:
            # Dedicated API: no model parameter, custom endpoints
            body = {
                # Map input fields to API parameters
                # "prompt": inputs.prompt,
            }
            submit_url = f"https://api.kie.ai{self.submit_endpoint}"
            status_url_template = f"https://api.kie.ai{self.status_endpoint}?taskId={{task_id}}"

        # Submit task
        async with httpx.AsyncClient() as client:
            response = await client.post(
                submit_url,
                json=body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                raise ValueError(f"Kie.ai API request failed: {response.status_code} {response.text}")

            result = response.json()

            if result.get("code") != 200:
                raise ValueError(f"Kie.ai API error: {result.get('msg', 'Unknown error')}")

            task_id = result["data"]["taskId"]

        # Store external job ID
        await context.set_external_job_id(task_id)

        # Poll for completion
        status_url = status_url_template.format(task_id=task_id)

        max_polls = 120  # Maximum number of polls (20 minutes at 10s intervals)
        poll_interval = 10  # Seconds between polls

        async with httpx.AsyncClient() as client:
            for poll_count in range(max_polls):
                await asyncio.sleep(poll_interval)

                status_response = await client.get(
                    status_url,
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=30.0,
                )

                if status_response.status_code != 200:
                    raise ValueError(f"Status check failed: {status_response.status_code}")

                status_result = status_response.json()

                if status_result.get("code") != 200:
                    raise ValueError(f"Status check error: {status_result.get('msg')}")

                # Parse status based on API pattern
                if self.api_pattern == "market":
                    status = status_result["data"]["status"]

                    if status == "SUCCESS":
                        # Extract outputs
                        result_data = status_result["data"]["result"]
                        break
                    elif status == "FAILED":
                        raise ValueError(f"Generation failed: {status_result['data'].get('error')}")
                    # Continue polling for PENDING/PROCESSING
                else:
                    # Dedicated API (example for Veo3 pattern)
                    success_flag = status_result["data"]["successFlag"]

                    if success_flag == 1:
                        # Success
                        result_data = status_result["data"]
                        break
                    elif success_flag in (2, 3):
                        raise ValueError("Generation failed")
                    # Continue polling for 0 (processing)

                # Publish progress
                progress = min(90, (poll_count / max_polls) * 100)
                await context.publish_progress(
                    ProgressUpdate(
                        job_id=task_id,
                        status="processing",
                        progress=progress,
                        phase="generating",
                    )
                )
            else:
                raise ValueError("Generation timed out")

        # Extract outputs and store artifacts
        artifacts = []

        # Parse outputs based on model-specific response structure
        # Example for image outputs:
        # images = result_data.get("images", [])
        # for idx, image_url in enumerate(images):
        #     artifact = await context.store_image_result(
        #         storage_url=image_url,
        #         format=inputs.output_format,
        #         width=result_data.get("width", 1024),
        #         height=result_data.get("height", 1024),
        #         output_index=idx,
        #     )
        #     artifacts.append(artifact)

        return GeneratorResult(outputs=artifacts)

    async def estimate_cost(self, inputs: {GeneratorName}Input) -> float:
        """Estimate cost for this generation in USD."""
        # Base cost from pricing
        # Multiply by num_outputs if applicable
        return {cost_per_generation}
```

### Step 6: Create Kie.ai Utils Module

If `packages/backend/src/boards/generators/implementations/kie/utils.py` doesn't exist, create it:

```python
"""
Shared utilities for Kie.ai generators.

Provides helper functions for common operations across Kie generators.
"""

import asyncio
import httpx

from ...artifacts import AudioArtifact, DigitalArtifact, ImageArtifact, VideoArtifact
from ...base import GeneratorExecutionContext


async def upload_artifacts_to_kie[T: DigitalArtifact](
    artifacts: list[ImageArtifact] | list[VideoArtifact] | list[AudioArtifact] | list[T],
    context: GeneratorExecutionContext,
) -> list[str]:
    """
    Upload artifacts to Kie.ai's temporary storage for use in API requests.

    Kie.ai API endpoints require publicly accessible URLs for file inputs. Since our
    storage URLs might be local or private (localhost, private S3 buckets, etc.),
    we need to:
    1. Resolve each artifact to a local file path
    2. Upload to Kie.ai's public temporary storage
    3. Get back publicly accessible URLs

    Note: Files uploaded to Kie.ai storage expire after 3 days.

    Args:
        artifacts: List of artifacts (image, video, or audio) to upload
        context: Generator execution context for artifact resolution

    Returns:
        List of publicly accessible URLs from Kie.ai storage

    Raises:
        ValueError: If KIE_API_KEY is not set
        Any exceptions from file resolution or upload are propagated
    """
    import os

    api_key = os.getenv("KIE_API_KEY")
    if not api_key:
        raise ValueError("KIE_API_KEY environment variable is required for file uploads")

    async def upload_single_artifact(artifact: DigitalArtifact) -> str:
        """Upload a single artifact and return its public URL."""
        # Resolve artifact to local file path (downloads if needed)
        file_path_str = await context.resolve_artifact(artifact)

        # Upload to Kie.ai's temporary storage
        # Using file stream upload API
        async with httpx.AsyncClient() as client:
            with open(file_path_str, "rb") as f:
                files = {"file": f}
                # uploadPath is required by Kie.ai API - specifies the storage path
                data = {"uploadPath": "boards/temp"}
                response = await client.post(
                    "https://kieai.redpandaai.co/api/file-stream-upload",
                    files=files,
                    data=data,
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=120.0,  # 2 minute timeout for uploads
                )

            if response.status_code != 200:
                raise ValueError(f"File upload failed: {response.status_code} {response.text}")

            result = response.json()

            if not result.get("success"):
                raise ValueError(f"File upload failed: {result.get('msg')}")

            # Extract the public URL
            file_url = result["data"]["downloadUrl"]
            return file_url

    # Upload all artifacts in parallel for performance
    urls = await asyncio.gather(*[upload_single_artifact(artifact) for artifact in artifacts])

    return list(urls)
```

### Step 7: Create Unit Test File

Create comprehensive unit tests at:
`packages/backend/tests/generators/implementations/test_{generator_name}.py`

**Test Coverage:**
- Input validation (valid inputs, defaults, invalid values)
- Generator metadata
- Input schema
- Missing API key handling
- Successful generation (mock HTTP responses)
- Failed generation (API errors)
- Cost estimation
- JSON schema generation

Use existing Fal tests as reference templates, but mock `httpx.AsyncClient` instead of `fal_client`.

### Step 8: Create Live API Test File

Create live API tests at:
`packages/backend/tests/generators/implementations/test_{generator_name}_live.py`

**Live Test Strategy:**

```python
"""
Live API tests for Kie{GeneratorName}Generator.

These tests make actual API calls to the Kie.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_kie to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"KIE_API_KEY": "..."}'
    pytest tests/generators/implementations/test_{generator_name}_live.py -v -m live_api

Or using direct environment variable:
    export KIE_API_KEY="..."
    pytest tests/generators/implementations/test_{generator_name}_live.py -v -m live_kie

Or run all Kie live tests:
    pytest -m live_kie -v
"""

import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.implementations.kie.{artifact_type}.{generator_name} import (
    Kie{GeneratorName}Generator,
    {GeneratorName}Input,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_kie]


@pytest.fixture
def skip_if_no_kie_key():
    """Skip test if KIE_API_KEY is not available."""
    import os

    if not os.getenv("KIE_API_KEY"):
        pytest.skip("KIE_API_KEY not set - skipping live API test")


class Test{GeneratorName}GeneratorLive:
    """Live API tests for Kie{GeneratorName}Generator using real Kie.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = Kie{GeneratorName}Generator()
        # Sync API keys from settings to os.environ for use in generator
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_basic(self, skip_if_no_kie_key, dummy_context, cost_logger):
        """
        Test basic generation with minimal parameters.

        This test makes a real API call to Kie.ai and will consume credits.
        Uses minimal/cheap settings to reduce cost.
        """
        # Log estimated cost
        estimated_cost = await self.generator.estimate_cost(
            {GeneratorName}Input(prompt="test")  # Adjust based on required fields
        )
        cost_logger(self.generator.name, estimated_cost)

        # Create minimal input to reduce cost
        inputs = {GeneratorName}Input(
            prompt="Simple test prompt",
            # Add other required fields with minimal values
        )

        # Execute generation
        result = await self.generator.generate(inputs, dummy_context)

        # Verify result structure
        assert result.outputs is not None
        assert len(result.outputs) >= 1

        # Verify artifact properties
        artifact = result.outputs[0]
        assert artifact.storage_url is not None
```

### Step 9: Update Module Exports

Add the generator to:
`packages/backend/src/boards/generators/implementations/kie/{artifact_type}/__init__.py`

Create `__init__.py` files if they don't exist:

```python
# packages/backend/src/boards/generators/implementations/kie/__init__.py
"""Kie.ai generator implementations."""

# packages/backend/src/boards/generators/implementations/kie/{artifact_type}/__init__.py
from .{generator_name} import Kie{GeneratorName}Generator

__all__ = ["Kie{GeneratorName}Generator"]
```

### Step 10: Update Configuration

Add the generator to:
`packages/backend/baseline-config/generators.yaml`

```yaml
- name: "{generator-name}"
  enabled: true
```

### Step 11: Verify Implementation

Run the following checks:

```bash
# Type checking
cd packages/backend
uv run pyright src/boards/generators/implementations/kie

# Linting
uv run ruff check src/boards/generators/implementations/kie tests/generators/implementations/test_{generator_name}*.py

# Unit tests (mocked, always run)
uv run pytest tests/generators/implementations/test_{generator_name}.py -v

# Live API tests (optional, requires KIE_API_KEY)
export KIE_API_KEY="..."
uv run pytest tests/generators/implementations/test_{generator_name}_live.py -v -m live_kie
```

All checks must pass with 0 errors.

## Notes

### API Patterns

**Market API**:
- Unified endpoint for 30+ models
- Submit: `POST /api/v1/jobs/createTask` with `model` parameter
- Status: `GET /api/v1/jobs/recordInfo?taskId={id}`
- Status values: `PENDING`, `PROCESSING`, `SUCCESS`, `FAILED`

**Dedicated API** (varies by model):
- Model-specific endpoints
- Submit: `POST /api/v1/{model}/generate` (no `model` parameter in body)
- Status: Model-specific endpoint
- Example (Veo3): `successFlag` with values 0 (processing), 1 (success), 2/3 (failed)

### File Uploads

- Endpoint: `https://kieai.redpandaai.co/api/file-stream-upload`
- Files expire after 3 days
- Returns `downloadUrl` in response
- Use for any artifact inputs (images, videos, audio)

### Pricing

- Try to scrape from https://kie.ai/pricing
- Pricing is typically 30-80% lower than official APIs
- Format costs in USD

### Progress Updates

- Poll every 10-30 seconds based on expected generation time
- Publish updates with estimated progress percentage
- Use phases: "initializing", "generating", "finalizing"

## Success Criteria

- [ ] User provided model name and documentation
- [ ] API pattern correctly identified (Market vs Dedicated)
- [ ] Generator name properly derived
- [ ] Artifact type correctly identified
- [ ] Input schema accurately mapped from documentation
  - [ ] All required fields included
  - [ ] Optional fields with correct defaults
  - [ ] Artifact URL fields converted to artifact types
  - [ ] Validation constraints preserved
- [ ] API endpoints configured correctly
- [ ] Output handling matches response schema
- [ ] Cost estimation implemented (scraped or manual)
- [ ] File upload logic added if generator accepts artifacts
- [ ] Utils module created if needed
- [ ] Generator implementation created with proper structure
- [ ] Comprehensive unit test suite generated
- [ ] Live API test suite generated
  - [ ] Marked with `@pytest.mark.live_api` and `@pytest.mark.live_kie`
  - [ ] Uses `skip_if_no_kie_key`, `dummy_context`, and `cost_logger` fixtures
  - [ ] Tests use minimal/cheap parameters
- [ ] All unit tests pass
- [ ] Type checking passes (0 errors)
- [ ] Linting passes
- [ ] Generator appears in module exports
- [ ] Generator enabled in configuration
- [ ] (Optional) Live API test verified with real KIE_API_KEY
