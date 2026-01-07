"""
Kie.ai nano-banana image-to-image editing generator.

Edit images using Kie.ai's google/nano-banana-edit model (powered by Google Gemini).
Supports editing multiple input images with a text prompt.

Based on Kie.ai's google/nano-banana-edit model.
See: https://docs.kie.ai/market/google/nano-banana-edit
"""

import asyncio
import os
from typing import Literal

import httpx
from pydantic import BaseModel, Field

from .....progress.models import ProgressUpdate
from ....artifacts import ImageArtifact
from ....base import BaseGenerator, GeneratorExecutionContext, GeneratorResult


class NanoBananaEditInput(BaseModel):
    """Input schema for nano-banana image editing.

    Artifact fields (like image_sources) are automatically detected via type
    introspection and resolved from generation IDs to ImageArtifact objects.
    """

    prompt: str = Field(
        description="The prompt for image editing",
        max_length=5000,
    )
    image_sources: list[ImageArtifact] = Field(
        description="List of input images for editing (from previous generations)",
        min_length=1,
        max_length=10,
    )
    output_format: Literal["png", "jpeg"] = Field(
        default="png",
        description="Output image format",
    )
    image_size: Literal[
        "1:1",
        "9:16",
        "16:9",
        "3:4",
        "4:3",
        "3:2",
        "2:3",
        "5:4",
        "4:5",
        "21:9",
        "auto",
    ] = Field(
        default="1:1",
        description="Output image aspect ratio",
    )


class KieNanoBananaEditGenerator(BaseGenerator):
    """nano-banana image editing generator using Kie.ai Market API."""

    name = "kie-nano-banana-edit"
    artifact_type = "image"
    description = "Kie.ai: Google nano-banana edit - AI-powered image editing with Gemini"

    # Market API configuration
    api_pattern = "market"
    model_id = "google/nano-banana-edit"

    def get_input_schema(self) -> type[NanoBananaEditInput]:
        return NanoBananaEditInput

    async def generate(
        self, inputs: NanoBananaEditInput, context: GeneratorExecutionContext
    ) -> GeneratorResult:
        """Edit images using Kie.ai google/nano-banana-edit model."""
        # Check for API key
        api_key = os.getenv("KIE_API_KEY")
        if not api_key:
            raise ValueError("API configuration invalid. Missing KIE_API_KEY environment variable")

        # Upload image artifacts to Kie.ai's public storage
        # Kie.ai API requires publicly accessible URLs, but our storage_url might be:
        # - Localhost URLs (not publicly accessible)
        # - Private S3 buckets (not publicly accessible)
        # So we upload to Kie.ai's temporary storage first
        from ..utils import upload_artifacts_to_kie

        image_urls = await upload_artifacts_to_kie(inputs.image_sources, context)

        # Prepare request body for Market API
        body = {
            "model": self.model_id,
            "input": {
                "prompt": inputs.prompt,
                "image_urls": image_urls,
                "output_format": inputs.output_format,
                "image_size": inputs.image_size,
            },
        }

        # Submit task
        submit_url = "https://api.kie.ai/api/v1/jobs/createTask"

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
                raise ValueError(
                    f"Kie.ai API request failed: {response.status_code} {response.text}"
                )

            result = response.json()

            if result.get("code") != 200:
                raise ValueError(f"Kie.ai API error: {result.get('msg', 'Unknown error')}")

            task_id = result["data"]["taskId"]

        # Store external job ID
        await context.set_external_job_id(task_id)

        # Poll for completion
        status_url = f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={task_id}"

        max_polls = 120  # Maximum number of polls (20 minutes at 10s intervals)
        poll_interval = 10  # Seconds between polls

        result_data = None

        async with httpx.AsyncClient() as client:
            for poll_count in range(max_polls):
                # Don't sleep on first poll - check status immediately
                if poll_count > 0:
                    await asyncio.sleep(poll_interval)

                status_response = await client.get(
                    status_url,
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=30.0,
                )

                if status_response.status_code != 200:
                    raise ValueError(
                        f"Status check failed: {status_response.status_code} {status_response.text}"
                    )

                status_result = status_response.json()

                if status_result.get("code") != 200:
                    raise ValueError(f"Status check error: {status_result.get('msg')}")

                # Parse Market API response
                task_data = status_result.get("data", {})
                # Market API uses 'state' field, not 'status'
                state = task_data.get("state")

                # Log every poll to help debug
                from boards.logging import get_logger

                logger = get_logger(__name__)
                logger.info(
                    "Status poll response",
                    poll_count=poll_count,
                    task_id=task_id,
                    state=state,
                    task_data_keys=list(task_data.keys()) if task_data else None,
                )

                if state == "success":
                    # Extract outputs from resultJson
                    result_json = task_data.get("resultJson")
                    if result_json:
                        import json

                        result_data = json.loads(result_json)
                    else:
                        result_data = task_data.get("result")
                    break
                elif state == "failed":
                    error_msg = task_data.get("failMsg", "Unknown error")
                    raise ValueError(f"Generation failed: {error_msg}")
                elif state not in ["waiting", "pending", "processing", None]:
                    # Unknown state - log and fail
                    raise ValueError(
                        f"Unknown state '{state}' from Kie.ai API. "
                        f"Full response: {status_result}"
                    )
                # Continue polling for waiting/pending/processing

                # Publish progress
                progress = min(90, (poll_count / max_polls) * 100)
                await context.publish_progress(
                    ProgressUpdate(
                        job_id=task_id,
                        status="processing",
                        progress=progress,
                        phase="processing",
                    )
                )
            else:
                raise ValueError("Generation timed out after 20 minutes")

        if not result_data:
            raise ValueError("No result data returned from Kie.ai API")

        # Extract image URLs from result
        # The response structure may vary, but typically contains image URLs
        # Based on the API pattern, result should contain the generated images
        images = result_data.get("images", [])

        if not images:
            # Sometimes the result might directly contain URLs in different structure
            # Try to extract from common patterns
            if isinstance(result_data, dict):
                # Check for common response patterns
                if "resultUrls" in result_data:
                    # Market API returns resultUrls as array of strings
                    images = [{"url": url} for url in result_data["resultUrls"]]
                elif "image_urls" in result_data:
                    images = [{"url": url} for url in result_data["image_urls"]]
                elif "url" in result_data:
                    images = [{"url": result_data["url"]}]
                else:
                    raise ValueError(f"No images found in result: {result_data}")
            else:
                raise ValueError("No images returned from Kie.ai API")

        # Store each image using output_index
        artifacts = []
        for idx, image_data in enumerate(images):
            if isinstance(image_data, str):
                image_url = image_data
                width = 1024
                height = 1024
            elif isinstance(image_data, dict):
                image_url = image_data.get("url")
                # Extract dimensions if available, otherwise use sensible defaults
                width = image_data.get("width", 1024)
                height = image_data.get("height", 1024)
            else:
                raise ValueError(f"Unexpected image data format: {type(image_data)}")

            if not image_url:
                raise ValueError(f"Image {idx} missing URL in Kie.ai response")

            # Store with appropriate output_index
            artifact = await context.store_image_result(
                storage_url=image_url,
                format=inputs.output_format,
                width=width,
                height=height,
                output_index=idx,
            )
            artifacts.append(artifact)

        return GeneratorResult(outputs=artifacts)

    async def estimate_cost(self, inputs: NanoBananaEditInput) -> float:
        """Estimate cost for nano-banana edit generation.

        nano-banana/edit uses Google Gemini for image editing.
        Estimated at $0.025 per image (approximately 35% cheaper than Fal's $0.039).

        Note: Actual pricing should be verified at https://kie.ai/pricing
        """
        # Cost per image - this is an estimate and should be updated with actual pricing
        per_image_cost = 0.025
        num_images = len(inputs.image_sources)
        return per_image_cost * num_images
