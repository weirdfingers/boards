"""
Live API tests for KieGrokImagineExtendGenerator.

These tests make actual API calls to the Kie.ai service and consume API credits.
They are marked with @pytest.mark.live_api and @pytest.mark.live_kie to
ensure they are never run by default.

To run these tests:
    export BOARDS_GENERATOR_API_KEYS='{"KIE_API_KEY": "..."}'
    pytest tests/generators/implementations/test_kie_grok_imagine_extend_live.py -v -m live_api

Or using direct environment variable:
    export KIE_API_KEY="..."
    pytest tests/generators/implementations/test_kie_grok_imagine_extend_live.py -v -m live_kie

Or run all Kie live tests:
    pytest -m live_kie -v

Note: This test first creates a base video via the grok-imagine Market API,
then extends it. Both steps consume credits.
"""

import asyncio
import os

import httpx
import pytest

from boards.config import initialize_generator_api_keys
from boards.generators.artifacts import VideoArtifact
from boards.generators.implementations.kie.video.grok_imagine_extend import (
    GrokImagineExtendInput,
    KieGrokImagineExtendGenerator,
)

pytestmark = [pytest.mark.live_api, pytest.mark.live_kie]


async def _create_base_video(api_key: str) -> str:
    """Create a base video via Kie.ai grok-imagine Market API and return its task_id.

    This submits a simple text-to-video generation using the grok-imagine model,
    then polls until completion. The returned task_id can be used for extend.
    """
    submit_url = "https://api.kie.ai/api/v1/jobs/createTask"
    body = {
        "model": "grok-imagine/text-to-video",
        "input": {
            "prompt": "A gentle ocean wave rolling onto a sandy beach",
            "aspect_ratio": "16:9",
            "duration": 6,
            "resolution": "480p",
        },
    }

    async with httpx.AsyncClient() as client:
        # Submit the base generation
        response = await client.post(
            submit_url,
            json=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        assert response.status_code == 200, f"Submit failed: {response.status_code} {response.text}"
        result = response.json()
        assert result.get("code") == 200, f"API error: {result}"

        task_id = result.get("data", {}).get("taskId")
        assert task_id, f"No taskId in response: {result}"

        # Poll for completion
        status_url = f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={task_id}"
        for _ in range(120):  # Up to 20 minutes
            await asyncio.sleep(10)
            status_response = await client.get(
                status_url,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30.0,
            )
            assert status_response.status_code == 200
            status_result = status_response.json()
            task_data = status_result.get("data", {})
            state = task_data.get("state")

            if state == "success":
                return task_id
            elif state in ["failed", "fail"]:
                fail_msg = task_data.get("failMsg", "Unknown error")
                pytest.fail(f"Base video generation failed: {fail_msg}")

        pytest.fail("Base video generation timed out after 20 minutes")
    # unreachable but satisfies type checker
    return ""


class TestGrokImagineExtendGeneratorLive:
    """Live API tests for KieGrokImagineExtendGenerator using real Kie.ai API."""

    def setup_method(self):
        """Set up generator and ensure API keys are synced to environment."""
        self.generator = KieGrokImagineExtendGenerator()
        initialize_generator_api_keys()

    @pytest.mark.asyncio
    async def test_generate_extend_6s(self, skip_if_no_kie_key, dummy_context, cost_logger):
        """
        Test basic 6-second video extension.

        This test first generates a base video using grok-imagine,
        then extends it using grok-imagine/extend. Both steps consume credits.
        """
        api_key = os.environ["KIE_API_KEY"]

        # Step 1: Create a base video to get a valid task_id
        base_task_id = await _create_base_video(api_key)

        # Step 2: Extend the generated video
        inputs = GrokImagineExtendInput(
            task_id=base_task_id,
            prompt="The camera slowly pans forward revealing more of the scene",
            extend_times="6",
        )

        # Log estimated cost (extend only; base video cost is separate)
        estimated_cost = await self.generator.estimate_cost(inputs)
        cost_logger(self.generator.name, estimated_cost)

        result = await self.generator.generate(inputs, dummy_context)

        # Verify result structure
        assert result.outputs is not None
        assert len(result.outputs) >= 1

        # Verify artifact properties
        artifact = result.outputs[0]
        assert isinstance(artifact, VideoArtifact)
        assert artifact.storage_url is not None
        assert artifact.storage_url.startswith("https://")
        assert artifact.format == "mp4"
