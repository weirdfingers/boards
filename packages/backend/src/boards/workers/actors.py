"""Dramatiq actors for generation processing."""

from __future__ import annotations

import traceback

import dramatiq
from dramatiq import actor
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AsyncIO

from ..config import Settings
from ..database.connection import get_async_session
from ..generators.registry import registry as generator_registry
from ..jobs import repository as jobs_repo
from ..logging import get_logger
from ..progress.models import ProgressUpdate
from ..progress.publisher import ProgressPublisher
from ..storage.factory import create_storage_manager
from .context import GeneratorExecutionContext
from .middleware import GeneratorLoaderMiddleware

logger = get_logger(__name__)


settings = Settings()
broker = RedisBroker(url=settings.redis_url)
dramatiq.set_broker(broker)

# Enable async actor support - Dramatiq will manage event loops per thread
# This avoids the event loop conflicts from using asyncio.run()
broker.add_middleware(AsyncIO())

# Load generators when worker process starts via middleware
# Middleware runs before_worker_boot hook once per worker process at startup
broker.add_middleware(GeneratorLoaderMiddleware())


@actor(queue_name="boards-jobs", max_retries=3, min_backoff=5000, max_backoff=30000)
async def process_generation(generation_id: str) -> None:
    """Entry actor: load job context and dispatch to the generator.

    Retry policy:
    - max_retries: 3 attempts
    - min_backoff: 5 seconds
    - max_backoff: 30 seconds

    Note: This is an async actor. Dramatiq manages the event loop lifecycle properly,
    avoiding the event loop conflicts that would occur with asyncio.run().

    Process a generation job with comprehensive error handling.
    """
    logger.info("Starting generation processing", generation_id=generation_id)

    publisher = ProgressPublisher(settings)

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
            # Access all attributes while session is active to avoid DetachedInstanceError
            generator_name = gen.generator_name
            input_params = gen.input_params
            gen_id = gen.id
            tenant_id = gen.tenant_id
            board_id = gen.board_id
            user_id = gen.user_id
            artifact_type = gen.artifact_type

        # Initialize storage manager
        # This will use the default storage configuration from environment/config
        storage_manager = create_storage_manager()

        # Validate generator exists
        generator = generator_registry.get(generator_name)
        if generator is None:
            error_msg = "Unknown generator"
            logger.error(error_msg, generator_name=generator_name)
            raise RuntimeError(f"Unknown generator: {generator_name}")

        # Build and validate typed inputs
        # First resolve any artifact fields (generation IDs -> artifact objects)
        # This happens automatically via type introspection
        try:
            input_schema = generator.get_input_schema()

            # Automatically resolve generation IDs to artifacts before validation
            from ..generators.artifact_resolution import resolve_input_artifacts

            async with get_async_session() as session:
                resolved_params = await resolve_input_artifacts(
                    input_params,
                    input_schema,  # Schema is introspected to find artifact fields
                    session,
                    tenant_id,
                )
            typed_inputs = input_schema.model_validate(resolved_params)
        except Exception as e:
            error_msg = "Invalid input parameters"
            logger.error(error_msg, generation_id=generation_id, error=str(e))
            raise ValueError(f"Invalid input parameters: {e}") from e

        # Build context and run generator
        context = GeneratorExecutionContext(
            gen_id,
            publisher,
            storage_manager,
            tenant_id,
            board_id,
            user_id,
            generator_name,
            artifact_type,
            input_params,
        )

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

        # Execute generator
        logger.info(
            "Executing generator",
            generator_name=generator_name,
            generation_id=generation_id,
        )
        # TODO: Consider implementing credit refund logic on failure
        # await refund_credits(gen.user_id, gen.estimated_cost)
        output = await generator.generate(typed_inputs, context)
        logger.info(
            "Generator completed successfully",
            generator_name=generator_name,
            generation_id=generation_id,
            artifact_count=len(output.outputs),
        )

        # Find the artifact with matching generation_id (primary generation)
        # Generators should return exactly one artifact with the matching generation_id
        matching_artifacts = [art for art in output.outputs if art.generation_id == generation_id]

        if len(matching_artifacts) == 0:
            raise RuntimeError(
                f"No artifact found with generation_id {generation_id} in generator output. "
                f"Generator returned {len(output.outputs)} artifact(s) but none matched."
            )

        if len(matching_artifacts) > 1:
            logger.warning(
                "Generator returned multiple artifacts with same generation_id, using first one",
                generation_id=generation_id,
                artifact_count=len(matching_artifacts),
            )

        artifact = matching_artifacts[0]

        # Extract storage URL and convert artifact to dict
        storage_url = artifact.storage_url
        output_metadata = artifact.model_dump()

        # If this was a batch generation, add batch metadata to primary generation
        if context._batch_id is not None:
            output_metadata["batch_id"] = context._batch_id
            output_metadata["batch_index"] = 0
            output_metadata["batch_size"] = len(output.outputs)
            logger.info(
                "Primary generation is part of batch",
                generation_id=generation_id,
                batch_id=context._batch_id,
                batch_size=len(output.outputs),
            )

        # Finalize DB with storage URL and output metadata
        async with get_async_session() as session:
            await jobs_repo.finalize_success(
                session,
                generation_id,
                storage_url=storage_url,
                output_metadata=output_metadata,
            )

        # Finalize all batch generation records (if any)
        if context._batch_id is not None:
            batch_artifacts = [art for art in output.outputs if art.generation_id != generation_id]
            logger.info(
                "Finalizing batch generation records",
                batch_id=context._batch_id,
                batch_count=len(batch_artifacts),
            )
            for batch_artifact in batch_artifacts:
                async with get_async_session() as session:
                    batch_metadata = batch_artifact.model_dump()
                    # Add batch metadata to each batch generation
                    batch_metadata["batch_id"] = context._batch_id
                    # batch_index was set during generation creation via create_batch_generation()
                    batch_metadata["batch_size"] = len(output.outputs)

                    await jobs_repo.finalize_success(
                        session,
                        batch_artifact.generation_id,
                        storage_url=batch_artifact.storage_url,
                        output_metadata=batch_metadata,
                    )
                    logger.info(
                        "Batch generation finalized",
                        batch_generation_id=batch_artifact.generation_id,
                        batch_id=context._batch_id,
                    )

        logger.info("Job finalized successfully", generation_id=generation_id)

        # Publish completion (DB already updated by finalize_success)
        await publisher.publish_only(
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

        # Publish failure status (this also persists to DB via ProgressPublisher)
        try:
            await publisher.publish_progress(
                generation_id,
                ProgressUpdate(
                    job_id=generation_id,
                    status="failed",
                    progress=0.0,
                    phase="finalizing",
                    message=str(e),
                ),
            )
        except Exception as pub_error:
            logger.error("Failed to publish error status", error=str(pub_error))

        # Re-raise for Dramatiq retry mechanism
        # raise
