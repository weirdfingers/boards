"""Dramatiq actors for generation processing."""

from __future__ import annotations

import logging
import traceback
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

logger = logging.getLogger(__name__)


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

    logger.info(f"Starting generation processing for job {generation_id}")
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
        
        # Load generation from DB with transaction safety
        async with get_async_session() as session:
            try:
                gen = await jobs_repo.get_generation(session, generation_id)
                await session.commit()
            except Exception as e:
                logger.error(f"Failed to load generation {generation_id}: {e}")
                await session.rollback()
                raise
        
        # Validate generator exists
        generator = generator_registry.get(gen.generator_name)
        if generator is None:
            error_msg = f"Unknown generator: {gen.generator_name}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Build and validate typed inputs
        try:
            input_schema = generator.get_input_schema()
            typed_inputs = input_schema.model_validate(gen.input_params)
        except Exception as e:
            error_msg = f"Invalid input parameters: {e}"
            logger.error(f"Job {generation_id}: {error_msg}")
            raise ValueError(error_msg)
        
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
            logger.info(f"Executing generator {gen.generator_name} for job {generation_id}")
            output = await generator.generate(typed_inputs, context)
            logger.info(f"Generator {gen.generator_name} completed successfully for job {generation_id}")
        except Exception as e:
            error_msg = f"Generator execution failed: {str(e)}"
            logger.error(f"Job {generation_id}: {error_msg}", exc_info=True)
            
            # Update job status to failed
            async with get_async_session() as session:
                try:
                    await jobs_repo.update_progress(
                        session,
                        generation_id,
                        status="failed",
                        progress=0.0,
                        error_message=error_msg,
                    )
                    await session.commit()
                except Exception as db_error:
                    logger.error(f"Failed to update job status: {db_error}")
                    await session.rollback()
            
            # TODO: Refund credits here if applicable
            # await refund_credits(gen.user_id, gen.estimated_cost)
            
            raise
        
        # Finalize DB with transaction safety
        async with get_async_session() as session:
            try:
                await jobs_repo.finalize_success(session, generation_id)
                await session.commit()
                logger.info(f"Job {generation_id} finalized successfully")
            except Exception as e:
                logger.error(f"Failed to finalize job {generation_id}: {e}")
                await session.rollback()
                raise
        
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
        logger.error(f"Job {generation_id} failed with error: {e}\n{traceback.format_exc()}")
        
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
            logger.error(f"Failed to publish error status: {pub_error}")
        
        # Update database with failure status if not already done
        if gen is not None:
            async with get_async_session() as session:
                try:
                    await jobs_repo.update_progress(
                        session,
                        generation_id,
                        status="failed",
                        progress=0.0,
                        error_message=str(e),
                    )
                    await session.commit()
                except Exception as db_error:
                    logger.error(f"Failed to update job failure status: {db_error}")
                    await session.rollback()
        
        # Re-raise for Dramatiq retry mechanism
        raise
