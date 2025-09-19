"""Dramatiq actors for generation processing."""

from __future__ import annotations

import traceback

import dramatiq
from dramatiq import actor
from dramatiq.brokers.redis import RedisBroker

from ..config import Settings
from ..database.connection import get_async_session
from ..generators.registry import registry as generator_registry
from ..jobs import repository as jobs_repo
from ..logging import get_logger
from ..progress.models import ProgressUpdate
from ..progress.publisher import ProgressPublisher
from .context import GeneratorExecutionContext

logger = get_logger(__name__)


settings = Settings()
broker = RedisBroker(url=settings.redis_url)
dramatiq.set_broker(broker)


@actor(queue_name="boards-jobs", max_retries=3, min_backoff=5000, max_backoff=30000)
def process_generation(generation_id: str) -> None:
    """Entry actor: load job context and dispatch to the generator.

    Retry policy:
    - max_retries: 3 attempts
    - min_backoff: 5 seconds
    - max_backoff: 30 seconds
    """
    # For now, keep this actor sync and hand off to an async runner if needed.
    import asyncio

    logger.info("Starting generation processing", generation_id=generation_id)
    asyncio.run(_process_generation_async(generation_id))


async def _process_generation_async(generation_id: str) -> None:
    """Process a generation job with comprehensive error handling."""
    publisher = ProgressPublisher(settings)
    gen = None

    try:
        # Initialize processing
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

        # Validate generator exists
        generator = generator_registry.get(gen.generator_name)
        if generator is None:
            error_msg = "Unknown generator"
            logger.error(error_msg, generator_name=gen.generator_name)
            raise RuntimeError(f"Unknown generator: {gen.generator_name}")

        # Build and validate typed inputs
        try:
            input_schema = generator.get_input_schema()
            typed_inputs = input_schema.model_validate(gen.input_params)
        except Exception as e:
            error_msg = "Invalid input parameters"
            logger.error(error_msg, generation_id=generation_id, error=str(e))
            raise ValueError(f"Invalid input parameters: {e}")

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

        # Execute generator with error handling
        try:
            logger.info(
                "Executing generator",
                generator_name=gen.generator_name,
                generation_id=generation_id,
            )
            output = await generator.generate(typed_inputs, context)
            logger.info(
                "Generator completed successfully",
                generator_name=gen.generator_name,
                generation_id=generation_id,
            )
        except Exception as e:
            error_msg = "Generator execution failed"
            logger.error(error_msg, generation_id=generation_id, error=str(e))

            # Update job status to failed
            async with get_async_session() as session:
                await jobs_repo.update_progress(
                    session,
                    generation_id,
                    status="failed",
                    progress=0.0,
                    error_message=error_msg,
                )

            # TODO: Refund credits here if applicable
            # await refund_credits(gen.user_id, gen.estimated_cost)

            raise

        # Finalize DB
        async with get_async_session() as session:
            await jobs_repo.finalize_success(session, generation_id)

        logger.info("Job finalized successfully", generation_id=generation_id)

        # Publish completion
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

    except Exception as e:
        # Log the full traceback for debugging
        logger.error(
            "Job failed with error",
            generation_id=generation_id,
            error=str(e),
            traceback=traceback.format_exc(),
        )

        # Publish failure status
        try:
            await publisher.publish_progress(
                generation_id,
                ProgressUpdate(
                    job_id=generation_id,
                    status="failed",
                    progress=0.0,
                    phase="finalizing",  # Use finalizing phase for errors
                    message=str(e),
                ),
            )
        except Exception as pub_error:
            logger.error("Failed to publish error status", error=str(pub_error))

        # Update database with failure status if not already done
        if gen is not None:
            try:
                async with get_async_session() as session:
                    await jobs_repo.update_progress(
                        session,
                        generation_id,
                        status="failed",
                        progress=0.0,
                        error_message=str(e),
                    )
            except Exception as db_error:
                logger.error("Failed to update job failure status", error=str(db_error))

        # Re-raise for Dramatiq retry mechanism
        raise
