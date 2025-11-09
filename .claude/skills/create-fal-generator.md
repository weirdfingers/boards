# Create Fal AI Generator

This skill creates a new Fal AI generator implementation with all necessary files, tests, and configuration.

## Overview

Creates a complete Fal AI generator following the established patterns from the Boards project:

- Generator implementation with automatic artifact resolution
- Comprehensive test suite
- Module exports
- Configuration in generators.yaml

The skill uses Fal AI's structured API information to automatically extract:
- Input/output schemas from OpenAPI spec
- Model description and pricing from LLM-optimized docs
- Parameter validation and types

## Instructions

### Step 1: Get Fal Model Name

Ask the user for the Fal AI model name if not already provided:

```
What is the Fal AI model name? (e.g., fal-ai/flux-pro, fal-ai/nano-banana/edit)
```

This will be used to fetch structured API information.

### Step 2: Fetch Fal AI API Information

Use the Fal model name to gather comprehensive information from Fal's structured endpoints:

**2a. Fetch OpenAPI Schema:**

URL: `https://fal.ai/api/openapi/queue/openapi.json?endpoint_id={fal_model_name}`

Extract:
- Input schema (parameters, types, validation, required fields)
- Output schema (response structure)
- Example values

**2b. Fetch LLM-Optimized Documentation:**

URL: `https://fal.ai/models/{fal_model_name}/llms.txt`

Extract:
- Model description (user-facing)
- Pricing information (cost per generation)
- Usage examples
- Special notes or requirements
- Output artifact type (image/video/audio/text)

**2c. Analyze the Information:**

From the OpenAPI schema, determine:
- Which parameters accept file URLs (image_url, image_urls, audio_url, etc.)
- Whether artifacts need to be uploaded to Fal's storage
- Parameter validation constraints (min/max values, allowed options)
- Default values

From the llms.txt documentation:
- Artifact type (image/video/audio/text) based on output description
- Cost per generation in USD
- User-facing description for the generator
- Any special capabilities or limitations

### Step 3: Determine Generator Configuration

Based on the gathered information, determine:

1. **Generator Name** (kebab-case): Convert the Fal model name
   - Example: `fal-ai/flux-pro` → `fal-flux-pro`
   - Example: `fal-ai/nano-banana/edit` → `fal-nano-banana-edit`

2. **Python Class Name** (PascalCase):
   - Example: `fal-flux-pro` → `FalFluxProGenerator`
   - Example: `fal-nano-banana-edit` → `FalNanoBananaEditGenerator`

3. **Artifact Type**: From the output schema or llms.txt (image/video/audio/text)

4. **Input Fields**: Map OpenAPI schema properties to Pydantic fields
   - Detect artifact inputs (any field ending in `_url` or `_urls`)
   - Convert types (string → str, number → float, integer → int, array → list)
   - Preserve validation (minimum, maximum, enum values)
   - Map required fields

5. **Output Handling**: Based on response schema
   - Detect single vs multiple outputs
   - Extract dimensions, format, duration fields
   - Determine if batch processing is needed

6. **Cost Calculation**: From pricing in llms.txt
   - Base cost per generation
   - Multiply by num_outputs if applicable

### Step 4: Create Generator Implementation

Create the generator implementation file at:
`packages/backend/src/boards/generators/implementations/fal/{artifact_type}/{generator_name}.py`

**Important Implementation Notes:**

1. **Input Schema Mapping:**
   - Convert OpenAPI schema properties to Pydantic Field definitions
   - For file URL fields (`image_url`, `image_urls`, `video_url`, etc.):
     - Replace with artifact types: `ImageArtifact`, `VideoArtifact`, `AudioArtifact`
     - Use singular for single files, `list[...]` for multiple files
     - These will be automatically resolved from generation IDs
   - Preserve all validation from OpenAPI (min/max, enum, required)
   - Use OpenAPI descriptions for Field descriptions
   - Use OpenAPI default values

2. **File Upload Detection:**
   - If ANY input field is an artifact type (ImageArtifact, etc.)
   - Import and use: `from ..utils import upload_artifacts_to_fal`
   - Upload artifacts before submitting to Fal API
   - Replace artifact objects with uploaded URLs in arguments

3. **Output Processing:**
   - Based on OpenAPI response schema
   - Extract output artifacts (images, videos, audio)
   - Use appropriate `store_{artifact}_result()` method
   - Include `output_index` for multiple outputs
   - Extract metadata fields (width, height, duration, fps, etc.)

Follow this template structure:

```python
"""
{Generator Description}

Based on Fal AI's {model_endpoint} model.
See: {documentation_url}
"""

import os
from typing import Literal

from pydantic import BaseModel, Field

from .....generators.artifacts import {ArtifactType}
from .....generators.base import (
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

    # Define input fields based on Fal API documentation
    # Use appropriate types, Field() with descriptions, and validation
    # For artifact inputs, use ImageArtifact, VideoArtifact, etc.
    # Example:
    # prompt: str = Field(description="Text prompt")
    # image_sources: list[ImageArtifact] = Field(description="Input images", min_length=1)


class Fal{GeneratorName}Generator(BaseGenerator[{GeneratorName}Input]):
    """Generator for {description}."""

    name = "{generator-name}"
    description = "{description}"
    artifact_type = "{artifact_type}"

    def get_input_schema(self) -> type[{GeneratorName}Input]:
        """Return the input schema for this generator."""
        return {GeneratorName}Input

    async def generate(
        self, inputs: {GeneratorName}Input, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Generate {artifact_type} using fal.ai {model_endpoint}."""
        # Check for API key
        if not os.getenv("FAL_KEY"):
            raise ValueError("API configuration invalid. Missing FAL_KEY environment variable")

        # Import fal_client
        try:
            import fal_client
        except ImportError as e:
            raise ImportError(
                "fal.ai SDK is required for Fal{GeneratorName}Generator. "
                "Install with: pip install weirdfingers-boards[generators-fal]"
            ) from e

        # If generator accepts artifact inputs (e.g., image_urls), upload them
        # from ..utils import upload_artifacts_to_fal
        # artifact_urls = await upload_artifacts_to_fal(inputs.image_sources, context)

        # Prepare arguments for fal.ai API
        arguments = {
            # Map input fields to Fal API parameters
            # "prompt": inputs.prompt,
            # "image_urls": artifact_urls,
        }

        # Submit async job
        handler = await fal_client.submit_async(
            "{model_endpoint}",
            arguments=arguments,
        )

        # Store external job ID
        await context.set_external_job_id(handler.request_id)

        # Stream progress updates
        from .....progress.models import ProgressUpdate

        event_count = 0
        async for event in handler.iter_events(with_logs=True):
            event_count += 1
            # Sample every 3rd event to avoid spam
            if event_count % 3 == 0:
                await context.publish_progress(
                    ProgressUpdate(
                        job_id=context.generation_id,
                        status="processing",
                        progress=0.5,  # Estimate based on event type if possible
                        phase="generating",
                    )
                )

        # Get final result
        result = await handler.get()

        # Extract outputs from result and store artifacts
        # Adapt based on actual API response structure
        artifacts = []

        # For image outputs:
        # images = result.get("images", [])
        # for idx, image_data in enumerate(images):
        #     artifact = await context.store_image_result(
        #         storage_url=image_data["url"],
        #         format=inputs.output_format,
        #         width=image_data.get("width", 1024),
        #         height=image_data.get("height", 1024),
        #         output_index=idx,
        #     )
        #     artifacts.append(artifact)

        return GeneratorResult(outputs=artifacts)

    async def estimate_cost(self, inputs: {GeneratorName}Input) -> float:
        """Estimate cost for this generation in USD."""
        # Cost per output * number of outputs
        # Adjust based on actual pricing
        return {cost_per_generation} * inputs.{number_of_outputs}
```

### Step 5: Create Test File

Create comprehensive tests at:
`packages/backend/tests/generators/implementations/test_{generator_name}.py`

**Test Generation Strategy:**

1. **Use OpenAPI Schema for Test Data:**
   - Use example values from OpenAPI schema
   - Test enum validation with valid/invalid options
   - Test min/max constraints from schema
   - Test required vs optional fields

2. **Mock Fal Client:**
   - Create helper: `_empty_async_event_iterator()` (async generator)
   - Mock `fal_client.submit_async()` to return handler
   - Mock `handler.get()` to return expected response from OpenAPI schema
   - If using artifacts, mock `upload_artifacts_to_fal()` return URLs

3. **Test Coverage:**
   - Input validation (valid inputs, defaults, invalid values based on OpenAPI)
   - Generator metadata
   - Input schema
   - Missing API key handling
   - Successful generation (single and multiple outputs if applicable)
   - Empty/error responses
   - Cost estimation (verify formula matches pricing)
   - JSON schema generation

Use `test_nano_banana_edit.py` as a reference template.

### Step 6: Update Module Exports

Add the generator to:
`packages/backend/src/boards/generators/implementations/fal/{artifact_type}/__init__.py`

```python
from .{generator_name} import Fal{GeneratorName}Generator

__all__ = [..., "Fal{GeneratorName}Generator"]
```

### Step 7: Update Configuration

Add the generator to:
`packages/backend/baseline-config/generators.yaml`

```yaml
- name: "{generator-name}"
  enabled: true
```

### Step 8: Verify Implementation

Run the following checks:

```bash
# Type checking
uv run pyright

# Linting
uv run ruff check src/ tests/

# Tests
uv run pytest tests/generators/implementations/test_{generator_name}.py -v
```

All checks must pass with 0 errors.

## Notes

### Artifact Resolution

- If the generator accepts artifacts as inputs (images, videos, etc.), use the appropriate artifact types (`ImageArtifact`, `VideoArtifact`, etc.)
- The artifact resolution system will automatically detect these fields and resolve generation IDs to artifact objects
- No manual configuration needed - just declare the field type

### File Uploads to Fal

- If the Fal API requires publicly accessible URLs (check the "Files" section in docs)
- Use the shared utility: `from ..utils import upload_artifacts_to_fal`
- This handles uploading artifacts to Fal's temporary storage

### Multiple Outputs

- If the generator supports `num_images` or similar parameter
- Use `output_index` parameter in `store_{artifact}_result()` calls
- Each output gets its own generation record with the same batch_id

### Cost Estimation

- Check Fal AI pricing documentation
- Return cost in USD
- Consider number of outputs if applicable

### Progress Updates

- Sample events to avoid excessive updates (every 3rd event is good)
- Map event types to progress percentages when possible
- Use phases: "initializing", "generating", "finalizing"

## Example Usage

**Example 1: Simple image generator**

```
User: Create a generator for fal-ai/flux-pro
Claude: I'll create a Fal AI generator for flux-pro. Let me fetch the API information...

[Fetches OpenAPI schema and llms.txt]

I found:
- Model: Flux Pro 1.1 - High quality text-to-image generation
- Artifact type: image
- Pricing: $0.055 per generation
- Inputs: prompt (required), image_size (optional), num_inference_steps (optional)
- Output: Single image with URL, width, height

Creating generator implementation...
```

**Example 2: Image editing generator with artifacts**

```
User: Create a generator for fal-ai/nano-banana/edit
Claude: I'll create a Fal AI generator for nano-banana/edit. Fetching API information...

[Fetches OpenAPI schema and llms.txt]

I found:
- Model: Nano Banana Edit - Gemini-powered image editing
- Artifact type: image
- Pricing: $0.039 per image
- Inputs: prompt (required), image_urls (required, array), num_images (optional)
- Output: Multiple images with descriptions

This generator accepts image inputs. I'll use ImageArtifact for the input and
upload_artifacts_to_fal() to handle file uploads.

Creating generator implementation...
```

**Example 3: Video generator**

```
User: Add support for fal-ai/minimax-video
Claude: Creating Fal AI generator for minimax-video...

[Fetches API information]

I found:
- Model: Minimax Video - Text/Image to video generation
- Artifact type: video
- Pricing: $0.12 per generation
- Inputs: prompt (required), image_url (optional), duration (optional)
- Output: Video file with URL, width, height, duration

Creating video generator with optional image input...
```

## Fal API Endpoints Reference

### OpenAPI Schema
**URL Pattern**: `https://fal.ai/api/openapi/queue/openapi.json?endpoint_id={model_name}`

**Example**: `https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/flux-pro`

**Contains**:
- Complete input/output JSON schemas
- Parameter types, validation, defaults
- Required vs optional fields
- Example values
- Response structure

**Key sections to extract**:
- `paths['/'].post.requestBody.content['application/json'].schema` - Input schema
- `paths['/'].post.responses['200'].content['application/json'].schema` - Output schema

### LLM-Optimized Documentation
**URL Pattern**: `https://fal.ai/models/{model_name}/llms.txt`

**Example**: `https://fal.ai/models/fal-ai/flux-pro/llms.txt`

**Contains**:
- Model description
- Pricing information
- Usage examples
- Special notes
- Capabilities

**Key information to extract**:
- Model description (first paragraph usually)
- Cost per generation (look for "$" or "USD")
- Artifact type (mentions "image", "video", "audio", or "text")
- Special requirements or limitations

## Success Criteria

- [ ] OpenAPI schema successfully fetched and parsed
- [ ] LLM documentation successfully fetched and parsed
- [ ] Generator name properly derived from Fal model name
- [ ] Artifact type correctly identified
- [ ] Input schema accurately mapped from OpenAPI
  - [ ] All required fields included
  - [ ] Optional fields with correct defaults
  - [ ] File URL fields converted to artifact types
  - [ ] Validation constraints preserved (min/max, enum)
- [ ] Output handling matches OpenAPI response schema
- [ ] Cost estimation formula matches pricing documentation
- [ ] File upload logic added if generator accepts artifacts
- [ ] Generator implementation created with proper structure
- [ ] Comprehensive test suite generated
  - [ ] Tests use OpenAPI examples
  - [ ] All validation constraints tested
- [ ] All tests pass
- [ ] Type checking passes (0 errors)
- [ ] Linting passes
- [ ] Generator appears in module exports
- [ ] Generator enabled in configuration
