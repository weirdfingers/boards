from __future__ import annotations

import asyncio
from types import SimpleNamespace

from boards.workers.actors import _process_generation_async


def test_worker_smoke(monkeypatch):
    # Mock replicate module to avoid network
    import sys

    class FakeReplicate:
        async def async_run(self, *args, **kwargs):
            return ["https://example.com/fake.png"]

    sys.modules["replicate"] = FakeReplicate()  # type: ignore

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
        )

    async def fake_finalize_success(session, generation_id, **kwargs):
        return None

    async def fake_persist(self, job_id, update):
        return None

    monkeypatch.setattr(jobs_repo, "get_generation", fake_get_generation)
    monkeypatch.setattr(jobs_repo, "finalize_success", fake_finalize_success)
    monkeypatch.setattr(
        ProgressPublisher, "_persist_update", fake_persist, raising=False
    )

    # Provide API key env for generator
    import os

    os.environ["REPLICATE_API_TOKEN"] = "test-token"
    # Execute
    asyncio.run(_process_generation_async("00000000-0000-0000-0000-00000000a1a1"))
