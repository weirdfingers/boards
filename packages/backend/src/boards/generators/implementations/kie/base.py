"""Base classes for Kie.ai generators.

Provides common functionality shared across all Kie.ai generator implementations,
including API key validation, HTTP client setup, response validation, and polling logic.

Kie.ai supports two API patterns:
- Market API: Unified endpoint for 30+ models using /api/v1/jobs endpoints
- Dedicated API: Model-specific endpoints with custom paths
"""

import asyncio
import os
from abc import abstractmethod
from typing import Any, ClassVar, Literal

import httpx

from ....progress.models import ProgressUpdate
from ...base import BaseGenerator, GeneratorExecutionContext


class KieBaseGenerator(BaseGenerator):
    """Base class for all Kie.ai generators with common functionality.

    Provides shared methods for API key management, HTTP requests,
    response validation, and external job ID storage.

    Subclasses must define:
    - api_pattern: Either "market" or "dedicated"
    - model_id: Model identifier (for market) or endpoint path (for dedicated)
    """

    # Subclasses must define these
    api_pattern: ClassVar[Literal["market", "dedicated"]]
    model_id: str

    def _get_api_key(self) -> str:
        """Get and validate KIE_API_KEY from environment.

        Returns:
            The API key string

        Raises:
            ValueError: If KIE_API_KEY is not set
        """
        api_key = os.getenv("KIE_API_KEY")
        if not api_key:
            raise ValueError("API configuration invalid. Missing KIE_API_KEY environment variable")
        return api_key

    def _validate_response(self, response: dict[str, Any]) -> None:
        """Validate standard Kie.ai response structure.

        All Kie.ai APIs return responses with a "code" field where 200 indicates success.

        Args:
            response: The JSON response from Kie.ai API

        Raises:
            ValueError: If the response code is not 200
        """
        if response.get("code") != 200:
            error_msg = response.get("msg", "Unknown error")
            raise ValueError(f"Kie.ai API error: {error_msg}")

    async def _make_request(
        self,
        url: str,
        method: Literal["GET", "POST"],
        api_key: str,
        json: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Make HTTP request to Kie.ai API with standard error handling.

        Args:
            url: Full URL to request
            method: HTTP method (GET or POST)
            api_key: API key for authorization
            json: Request body for POST requests
            timeout: Request timeout in seconds

        Returns:
            The validated JSON response

        Raises:
            ValueError: If the request fails or returns an error response
        """
        async with httpx.AsyncClient() as client:
            if method == "POST":
                response = await client.post(
                    url,
                    json=json,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=timeout,
                )
            else:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=timeout,
                )

            if response.status_code != 200:
                raise ValueError(
                    f"Kie.ai API request failed: {response.status_code} {response.text}"
                )

            result = response.json()
            self._validate_response(result)
            return result

    @abstractmethod
    async def _poll_for_completion(
        self,
        task_id: str,
        api_key: str,
        context: GeneratorExecutionContext,
    ) -> dict[str, Any]:
        """Poll for task completion.

        Subclasses implement this based on their API pattern (Market vs Dedicated).

        Args:
            task_id: The task ID to poll
            api_key: API key for authorization
            context: Generator execution context for progress updates

        Returns:
            The completed task data containing results

        Raises:
            ValueError: If polling fails or task fails
        """
        pass


class KieMarketAPIGenerator(KieBaseGenerator):
    """Base class for Kie.ai Market API generators.

    Market API is used for 30+ models through a unified endpoint.
    - Submit: POST /api/v1/jobs/createTask with model parameter
    - Status: GET /api/v1/jobs/recordInfo?taskId={id}
    - Status field: "state" with values: "waiting", "pending", "processing", "success", "failed"
    """

    api_pattern: ClassVar[Literal["market"]] = "market"

    async def _poll_for_completion(
        self,
        task_id: str,
        api_key: str,
        context: GeneratorExecutionContext,
        max_polls: int = 120,
        poll_interval: int = 10,
    ) -> dict[str, Any]:
        """Poll Market API for task completion using state field.

        Args:
            task_id: The task ID to poll
            api_key: API key for authorization
            context: Generator execution context for progress updates
            max_polls: Maximum number of polling attempts (default: 120 = 20 minutes)
            poll_interval: Seconds between polls (default: 10)

        Returns:
            The completed task data from the "data" field

        Raises:
            ValueError: If task fails or times out
        """
        status_url = f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={task_id}"

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
                self._validate_response(status_result)

                task_data = status_result.get("data", {})
                state = task_data.get("state")

                if state == "success":
                    return task_data
                elif state == "failed":
                    error_msg = task_data.get("failMsg", "Unknown error")
                    raise ValueError(f"Generation failed: {error_msg}")
                elif state not in ["waiting", "pending", "processing", None]:
                    raise ValueError(
                        f"Unknown state '{state}' from Kie.ai API. Full response: {status_result}"
                    )

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
                timeout_minutes = (max_polls * poll_interval) / 60
                raise ValueError(f"Generation timed out after {timeout_minutes} minutes")


class KieDedicatedAPIGenerator(KieBaseGenerator):
    """Base class for Kie.ai Dedicated API generators.

    Dedicated APIs have model-specific endpoints with custom paths.
    - Submit: POST /api/v1/{model}/generate (no model parameter in body)
    - Status: GET /api/v1/{model}/record-info?taskId={id}
    - Status field: "successFlag" with values: 0 (processing), 1 (success), 2/3 (failed)
    """

    api_pattern: ClassVar[Literal["dedicated"]] = "dedicated"

    @abstractmethod
    def _get_status_url(self, task_id: str) -> str:
        """Get the status check URL for this specific dedicated API.

        Each dedicated API has its own status endpoint path.

        Args:
            task_id: The task ID to check status for

        Returns:
            Full URL for status checking
        """
        pass

    async def _poll_for_completion(
        self,
        task_id: str,
        api_key: str,
        context: GeneratorExecutionContext,
        max_polls: int = 180,
        poll_interval: int = 10,
    ) -> dict[str, Any]:
        """Poll Dedicated API for task completion using successFlag field.

        Args:
            task_id: The task ID to poll
            api_key: API key for authorization
            context: Generator execution context for progress updates
            max_polls: Maximum number of polling attempts (default: 180 = 30 minutes)
            poll_interval: Seconds between polls (default: 10)

        Returns:
            The completed task data from the "data" field

        Raises:
            ValueError: If task fails or times out
        """
        status_url = self._get_status_url(task_id)

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
                self._validate_response(status_result)

                task_data = status_result.get("data", {})
                success_flag = task_data.get("successFlag")

                if success_flag == 1:
                    return task_data
                elif success_flag in [2, 3]:
                    error_msg = task_data.get("errorMsg", "Unknown error")
                    raise ValueError(f"Generation failed: {error_msg}")

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
                timeout_minutes = (max_polls * poll_interval) / 60
                raise ValueError(f"Generation timed out after {timeout_minutes} minutes")
