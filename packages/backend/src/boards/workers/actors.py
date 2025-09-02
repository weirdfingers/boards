"""Dramatiq actors for generation processing."""

from __future__ import annotations

import dramatiq
from dramatiq import actor
from dramatiq.brokers.redis import RedisBroker

from ..config import Settings
from ..generators.registry import registry as generator_registry
from ..progress.publisher import ProgressPublisher
from ..progress.models import ProgressUpdate
from ..database.connection import get_async_session
from ..jobs import repository as jobs_repo
from .context import GeneratorExecutionContext


settings = Settings()
broker = RedisBroker(url=settings.redis_url)
dramatiq.set_broker(broker)


@actor(queue_name="boards-jobs")
def process_generation(generation_id: str) -> None:
    """Entry actor: load job context and dispatch to the generator."""
    # For now, keep this actor sync and hand off to an async runner if needed.
    import asyncio

    asyncio.run(_process_generation_async(generation_id))


async def _process_generation_async(generation_id: str) -> None:
    publisher = ProgressPublisher(settings)
    await publisher.publish_progress(
        generation_id,
        ProgressUpdate(
            job_id=generation_id,
            status="processing",
            progress=0.0,
            phase="initializing",
        ),
    )

    # Load generation from DB
    async with get_async_session() as session:
        gen = await jobs_repo.get_generation(session, generation_id)

    generator = generator_registry.get(gen.generator_name)
    if generator is None:
        raise RuntimeError(f"Unknown generator: {gen.generator_name}")

    # Build typed inputs
    input_schema = generator.get_input_schema()
    typed_inputs = input_schema.model_validate(gen.input_params)

    # Build context and run generator
    context = GeneratorExecutionContext(gen.id, publisher)

    await publisher.publish_progress(
        generation_id,
        ProgressUpdate(
            job_id=generation_id,
            status="processing",
            progress=0.05,
            phase="processing",
            message="Starting generation",
        ),
    )

    output = await generator.generate(typed_inputs, context)

    # Finalize DB (placeholder minimal finalize)
    async with get_async_session() as session:
        await jobs_repo.finalize_success(session, generation_id)

    await publisher.publish_progress(
        generation_id,
        ProgressUpdate(
            job_id=generation_id,
            status="completed",
            progress=1.0,
            phase="finalizing",
            message="Completed",
        ),
    )
