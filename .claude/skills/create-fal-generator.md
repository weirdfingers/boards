# Create Fal AI Generator

This skill creates a new Fal AI generator implementation with all necessary files, tests, and configuration.

## Overview

Creates a complete Fal AI generator following the established patterns from the Boards project:

- Generator implementation with automatic artifact resolution
- Comprehensive test suite
- Module exports
- Configuration in generators.yaml

## Prerequisites

Before running this skill, gather the following information about the Fal AI model:

1. **Model API endpoint** (e.g., `fal-ai/nano-banana/edit`)
2. **Model documentation URL** (e.g., `https://fal.ai/models/fal-ai/nano-banana/edit`)
3. **Input parameters** from the Fal API docs
4. **Output format** (what the API returns)
5. **Artifact type** (image, video, audio, or text)
6. **Generator name** (kebab-case, e.g., `fal-nano-banana-edit`)
7. **Generator description** (concise, user-facing description)
8. **Cost per generation** (in USD)

## Instructions

### Step 1: Gather Information from User

Ask the user for the following (if not already provided):

```
1. What is the Fal AI model endpoint? (e.g., fal-ai/flux-pro)
2. What is the Fal AI documentation URL?
3. What artifact type does this generator produce? (image/video/audio/text)
4. What is a short, descriptive name for this generator? (kebab-case)
5. What is a user-facing description?
6. What is the cost per generation in USD?
```

### Step 2: Review API Documentation

Use WebFetch to retrieve and analyze the Fal AI documentation URL to understand:

- Required and optional input parameters
- Input parameter types and validation constraints
- Output format and structure
- Whether the model accepts artifact inputs (image_urls, audio_url, etc.)
- Any special requirements (aspect ratios, format options, etc.)

### Step 3: Create Generator Implementation

Create the generator implementation file at:
`packages/backend/src/boards/generators/implementations/fal/{artifact_type}/{generator_name}.py`

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

### Step 4: Create Test File

Create comprehensive tests at:
`packages/backend/tests/generators/implementations/test_{generator_name}.py`

Include tests for:

- Input validation (valid inputs, defaults, invalid values)
- Generator metadata
- Input schema
- Missing API key handling
- Successful generation (single and multiple outputs if applicable)
- Empty/error responses
- Cost estimation
- JSON schema generation

Use the test_nano_banana_edit.py as a reference template.

### Step 5: Update Module Exports

Add the generator to:
`packages/backend/src/boards/generators/implementations/fal/{artifact_type}/__init__.py`

```python
from .{generator_name} import Fal{GeneratorName}Generator

__all__ = [..., "Fal{GeneratorName}Generator"]
```

### Step 6: Update Configuration

Add the generator to:
`packages/backend/baseline-config/generators.yaml`

```yaml
- name: "{generator-name}"
  enabled: true
```

### Step 7: Verify Implementation

Run the following checks:

```bash
# Type checking
uv run pyright

# Linting
uv run ruff check src/ tests/

# Tests
uv run pytest tests/generators/implementations/test_{generator_name}.py -v
```

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

```
User: Create a generator for fal-ai/flux-pro
Claude: I'll help you create a Fal AI generator for flux-pro. Let me ask a few questions...
```

## Success Criteria

- [ ] Generator implementation created with proper structure
- [ ] Input schema matches Fal API requirements
- [ ] Artifact resolution works for any artifact inputs
- [ ] Tests cover all major scenarios
- [ ] All tests pass
- [ ] Type checking passes (0 errors)
- [ ] Linting passes
- [ ] Generator appears in module exports
- [ ] Generator enabled in configuration
- [ ] Cost estimation implemented
- [ ] Progress updates working
