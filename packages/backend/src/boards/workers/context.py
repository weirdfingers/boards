"""Execution context passed to generators for storage/DB/progress access."""

from __future__ import annotations

from uuid import UUID, uuid4

from ..database.connection import get_async_session
from ..generators import resolution
from ..generators.artifacts import AudioArtifact, ImageArtifact, TextArtifact, VideoArtifact
from ..jobs import repository as jobs_repo
from ..logging import get_logger
from ..progress.models import ProgressUpdate
from ..progress.publisher import ProgressPublisher
from ..storage.base import StorageManager

logger = get_logger(__name__)


class GeneratorExecutionContext:
    def __init__(
        self,
        generation_id: UUID,
        publisher: ProgressPublisher,
        storage_manager: StorageManager,
        tenant_id: UUID,
        board_id: UUID,
        user_id: UUID,
        generator_name: str,
        artifact_type: str,
        input_params: dict,
    ) -> None:
        self.generation_id = str(generation_id)
        self.publisher = publisher
        self.storage_manager = storage_manager
        self.tenant_id = str(tenant_id)
        self.board_id = str(board_id)
        self.user_id = str(user_id)
        self.generator_name = generator_name
        self.artifact_type = artifact_type
        self.input_params = input_params
        self._batch_id: str | None = None
        self._batch_generations: list[str] = []
        logger.info(
            "Created execution context",
            generation_id=str(generation_id),
            tenant_id=str(tenant_id),
            board_id=str(board_id),
        )

    async def resolve_artifact(self, artifact) -> str:
        """Resolve an artifact to a file path."""
        logger.debug("Resolving artifact", generation_id=self.generation_id)
        try:
            result = await resolution.resolve_artifact(artifact)
            logger.debug("Artifact resolved successfully", result=result)
            return result
        except Exception as e:
            logger.error("Failed to resolve artifact", error=str(e))
            raise

    async def store_image_result(
        self,
        storage_url: str,
        format: str,
        width: int | None = None,
        height: int | None = None,
        output_index: int = 0,
    ) -> ImageArtifact:
        """Store image generation result.

        Args:
            storage_url: URL to download the image from
            format: Image format (png, jpg, etc.)
            width: Image width in pixels (optional)
            height: Image height in pixels (optional)
            output_index: Index of this output in a batch (0 for primary, 1+ for additional)

        Returns:
            ImageArtifact with the generation_id set appropriately
        """
        logger.debug(
            "Storing image result",
            generation_id=self.generation_id,
            output_index=output_index,
        )
        try:
            # Determine which generation_id to use
            target_generation_id = await self._get_or_create_generation_for_output(output_index)

            result = await resolution.store_image_result(
                storage_manager=self.storage_manager,
                generation_id=target_generation_id,
                tenant_id=self.tenant_id,
                board_id=self.board_id,
                storage_url=storage_url,
                format=format,
                width=width,
                height=height,
            )
            logger.info(
                "Image result stored",
                generation_id=target_generation_id,
                output_index=output_index,
            )
            return result
        except Exception as e:
            logger.error("Failed to store image result", error=str(e))
            raise

    async def store_video_result(
        self,
        storage_url: str,
        format: str,
        width: int | None = None,
        height: int | None = None,
        duration: float | None = None,
        fps: float | None = None,
        output_index: int = 0,
    ) -> VideoArtifact:
        """Store video generation result.

        Args:
            storage_url: URL to download the video from
            format: Video format (mp4, webm, etc.)
            width: Video width in pixels (optional)
            height: Video height in pixels (optional)
            duration: Video duration in seconds (optional)
            fps: Frames per second (optional)
            output_index: Index of this output in a batch (0 for primary, 1+ for additional)

        Returns:
            VideoArtifact with the generation_id set appropriately
        """
        logger.debug(
            "Storing video result",
            generation_id=self.generation_id,
            output_index=output_index,
        )
        try:
            # Determine which generation_id to use
            target_generation_id = await self._get_or_create_generation_for_output(output_index)

            result = await resolution.store_video_result(
                storage_manager=self.storage_manager,
                generation_id=target_generation_id,
                tenant_id=self.tenant_id,
                board_id=self.board_id,
                storage_url=storage_url,
                format=format,
                width=width,
                height=height,
                duration=duration,
                fps=fps,
            )
            logger.info(
                "Video result stored",
                generation_id=target_generation_id,
                output_index=output_index,
            )
            return result
        except Exception as e:
            logger.error("Failed to store video result", error=str(e))
            raise

    async def store_audio_result(
        self,
        storage_url: str,
        format: str,
        duration: float | None = None,
        sample_rate: int | None = None,
        channels: int | None = None,
        output_index: int = 0,
    ) -> AudioArtifact:
        """Store audio generation result.

        Args:
            storage_url: URL to download the audio from
            format: Audio format (mp3, wav, etc.)
            duration: Audio duration in seconds (optional)
            sample_rate: Sample rate in Hz (optional)
            channels: Number of audio channels (optional)
            output_index: Index of this output in a batch (0 for primary, 1+ for additional)

        Returns:
            AudioArtifact with the generation_id set appropriately
        """
        logger.debug(
            "Storing audio result",
            generation_id=self.generation_id,
            output_index=output_index,
        )
        try:
            # Determine which generation_id to use
            target_generation_id = await self._get_or_create_generation_for_output(output_index)

            result = await resolution.store_audio_result(
                storage_manager=self.storage_manager,
                generation_id=target_generation_id,
                tenant_id=self.tenant_id,
                board_id=self.board_id,
                storage_url=storage_url,
                format=format,
                duration=duration,
                sample_rate=sample_rate,
                channels=channels,
            )
            logger.info(
                "Audio result stored",
                generation_id=target_generation_id,
                output_index=output_index,
            )
            return result
        except Exception as e:
            logger.error("Failed to store audio result", error=str(e))
            raise

    async def store_text_result(
        self,
        content: str,
        format: str,
        output_index: int = 0,
    ) -> TextArtifact:
        """Store text generation result.

        Args:
            content: Text content to store
            format: Text format (plain, markdown, html, etc.)
            output_index: Index of this output in a batch (0 for primary, 1+ for additional)

        Returns:
            TextArtifact with the generation_id set appropriately
        """
        logger.debug(
            "Storing text result",
            generation_id=self.generation_id,
            output_index=output_index,
        )
        try:
            # Determine which generation_id to use
            target_generation_id = await self._get_or_create_generation_for_output(output_index)

            result = await resolution.store_text_result(
                storage_manager=self.storage_manager,
                generation_id=target_generation_id,
                tenant_id=self.tenant_id,
                board_id=self.board_id,
                content=content,
                format=format,
            )
            logger.info(
                "Text result stored",
                generation_id=target_generation_id,
                output_index=output_index,
            )
            return result
        except Exception as e:
            logger.error("Failed to store text result", error=str(e))
            raise

    async def publish_progress(self, update: ProgressUpdate) -> None:
        """Publish progress update for the generation."""
        logger.debug(
            "Publishing progress",
            generation_id=self.generation_id,
            status=update.status,
            progress=update.progress,
        )
        try:
            await self.publisher.publish_progress(self.generation_id, update)
        except Exception as e:
            logger.error(
                "Failed to publish progress update - "
                "generation will continue but progress may not be visible",
                generation_id=self.generation_id,
                status=update.status,
                progress=update.progress,
                error=str(e),
                error_type=type(e).__name__,
            )
            # Don't raise here - progress updates are non-critical
            # The generation should continue even if progress updates fail

    async def set_external_job_id(self, external_id: str) -> None:
        """Set the external job ID from the provider."""
        logger.info(
            "Setting external job ID",
            external_job_id=external_id,
            generation_id=self.generation_id,
        )
        async with get_async_session() as session:
            await jobs_repo.set_external_job_id(session, self.generation_id, external_id)

    async def _get_or_create_generation_for_output(self, output_index: int) -> str:
        """Get or create a generation record for the given output index.

        Args:
            output_index: Index of the output (0 for primary, 1+ for batch outputs)

        Returns:
            generation_id to use for storing this output
        """
        # Index 0 is always the primary generation
        if output_index == 0:
            return self.generation_id

        # For batch outputs, ensure we have a batch_id
        if self._batch_id is None:
            self._batch_id = str(uuid4())
            logger.debug(
                "Created batch_id for multi-output generation",
                batch_id=self._batch_id,
                primary_generation_id=self.generation_id,
            )

        # Check if we've already created a generation for this index
        batch_index = output_index - 1  # Adjust since index 0 is primary
        if batch_index < len(self._batch_generations):
            return self._batch_generations[batch_index]

        # Create new batch generation record
        async with get_async_session() as session:
            batch_gen = await jobs_repo.create_batch_generation(
                session,
                tenant_id=UUID(self.tenant_id),
                board_id=UUID(self.board_id),
                user_id=UUID(self.user_id),
                generator_name=self.generator_name,
                artifact_type=self.artifact_type,
                input_params=self.input_params,
                batch_id=self._batch_id,
                batch_index=output_index,
            )
            await session.commit()
            batch_gen_id = str(batch_gen.id)

        self._batch_generations.append(batch_gen_id)
        logger.info(
            "Created batch generation record",
            batch_generation_id=batch_gen_id,
            primary_generation_id=self.generation_id,
            batch_id=self._batch_id,
            batch_index=output_index,
        )
        return batch_gen_id
