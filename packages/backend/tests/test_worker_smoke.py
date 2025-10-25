from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest

from boards.workers.actors import process_generation


@pytest.mark.requires_redis
def test_worker_smoke(monkeypatch):
    # Mock replicate module to avoid network
    import sys
    from types import ModuleType
    from unittest.mock import AsyncMock, MagicMock, patch

    # Create mock FileOutput with url as a plain string
    mock_file_output = SimpleNamespace(url="https://example.com/fake.png")

    # Create mock helpers module
    mock_helpers = ModuleType("helpers")
    mock_helpers.FileOutput = MagicMock  # type: ignore[attr-defined]

    # Create mock replicate module
    mock_replicate = ModuleType("replicate")
    mock_replicate.async_run = AsyncMock(return_value=mock_file_output)  # type: ignore[attr-defined]
    mock_replicate.helpers = mock_helpers  # type: ignore[attr-defined]

    sys.modules["replicate"] = mock_replicate
    sys.modules["replicate.helpers"] = mock_helpers

    # Bypass DB in repository and persistence
    from boards.generators.implementations.image.flux_pro import FluxProGenerator

    # Ensure generator registry contains flux-pro
    from boards.generators.registry import registry
    from boards.jobs import repository as jobs_repo

    try:
        registry.register(FluxProGenerator())
    except Exception:
        pass
    from boards.progress.publisher import ProgressPublisher

    async def fake_get_generation(session, generation_id):
        return SimpleNamespace(
            id=generation_id,
            generator_name="flux-pro",
            input_params={
                "prompt": "hello",
                "aspect_ratio": "1:1",
                "safety_tolerance": 2,
            },
            tenant_id=uuid4(),
            board_id=uuid4(),
        )

    async def fake_finalize_success(session, generation_id, **kwargs):
        return None

    async def fake_persist(self, job_id, update):
        return None

    monkeypatch.setattr(jobs_repo, "get_generation", fake_get_generation)
    monkeypatch.setattr(jobs_repo, "finalize_success", fake_finalize_success)
    monkeypatch.setattr(ProgressPublisher, "_persist_update", fake_persist, raising=False)

    # Provide API key env for generator
    import os

    os.environ["REPLICATE_API_TOKEN"] = "test-token"

    # Mock HTTP download for storage integration
    def create_mock_http_response(content: bytes):
        mock_response = AsyncMock()
        mock_response.content = content

        async def mock_raise_for_status():
            pass

        mock_response.raise_for_status = mock_raise_for_status
        return mock_response

    # Execute the underlying async function directly (bypass dramatiq actor wrapper)
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=create_mock_http_response(b"fake image content")
        )

        # Access the original function before AsyncIO middleware wrapping
        original_fn = process_generation.fn.__wrapped__
        asyncio.run(original_fn("00000000-0000-0000-0000-00000000a1a1"))
