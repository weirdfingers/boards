"""
Tests for FalKolorsVirtualTryOnGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.kolors_virtual_try_on import (
    FalKolorsVirtualTryOnGenerator,
    KolorsVirtualTryOnInput,
)


class TestKolorsVirtualTryOnInput:
    """Tests for KolorsVirtualTryOnInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        human_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/human.png",
            format="png",
            width=768,
            height=1024,
        )
        garment_artifact = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/garment.png",
            format="png",
            width=512,
            height=512,
        )

        input_data = KolorsVirtualTryOnInput(
            human_image_url=human_artifact,
            garment_image_url=garment_artifact,
        )

        assert input_data.human_image_url == human_artifact
        assert input_data.garment_image_url == garment_artifact
        assert input_data.sync_mode is False

    def test_input_defaults(self):
        """Test default values."""
        human_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/human.png",
            format="png",
            width=768,
            height=1024,
        )
        garment_artifact = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/garment.png",
            format="png",
            width=512,
            height=512,
        )

        input_data = KolorsVirtualTryOnInput(
            human_image_url=human_artifact,
            garment_image_url=garment_artifact,
        )

        assert input_data.sync_mode is False

    def test_input_with_sync_mode(self):
        """Test input with sync_mode enabled."""
        human_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/human.png",
            format="png",
            width=768,
            height=1024,
        )
        garment_artifact = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/garment.png",
            format="png",
            width=512,
            height=512,
        )

        input_data = KolorsVirtualTryOnInput(
            human_image_url=human_artifact,
            garment_image_url=garment_artifact,
            sync_mode=True,
        )

        assert input_data.sync_mode is True

    def test_missing_human_image(self):
        """Test validation fails when human_image_url is missing."""
        garment_artifact = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/garment.png",
            format="png",
            width=512,
            height=512,
        )

        with pytest.raises(ValidationError):
            KolorsVirtualTryOnInput(
                garment_image_url=garment_artifact,  # type: ignore[call-arg]
            )

    def test_missing_garment_image(self):
        """Test validation fails when garment_image_url is missing."""
        human_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/human.png",
            format="png",
            width=768,
            height=1024,
        )

        with pytest.raises(ValidationError):
            KolorsVirtualTryOnInput(
                human_image_url=human_artifact,  # type: ignore[call-arg]
            )


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalKolorsVirtualTryOnGenerator:
    """Tests for FalKolorsVirtualTryOnGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalKolorsVirtualTryOnGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-kolors-virtual-try-on"
        assert self.generator.artifact_type == "image"
        assert "kolors" in self.generator.description.lower()
        assert "try-on" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == KolorsVirtualTryOnInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            human_artifact = ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/human.png",
                format="png",
                width=768,
                height=1024,
            )
            garment_artifact = ImageArtifact(
                generation_id="gen2",
                storage_url="https://example.com/garment.png",
                format="png",
                width=512,
                height=512,
            )

            input_data = KolorsVirtualTryOnInput(
                human_image_url=human_artifact,
                garment_image_url=garment_artifact,
            )

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return ""

                async def store_image_result(self, **kwargs):
                    return ImageArtifact(
                        generation_id="test_gen",
                        storage_url="",
                        width=1,
                        height=1,
                        format="png",
                    )

                async def store_video_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_audio_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_text_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            with pytest.raises(ValueError, match="FAL_KEY"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_generate_successful(self):
        """Test successful generation."""
        human_artifact = ImageArtifact(
            generation_id="gen_human",
            storage_url="https://example.com/human.png",
            format="png",
            width=768,
            height=1024,
        )
        garment_artifact = ImageArtifact(
            generation_id="gen_garment",
            storage_url="https://example.com/garment.png",
            format="png",
            width=512,
            height=512,
        )

        input_data = KolorsVirtualTryOnInput(
            human_image_url=human_artifact,
            garment_image_url=garment_artifact,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.png"
        fake_uploaded_human_url = "https://fal.media/files/uploaded-human.png"
        fake_uploaded_garment_url = "https://fal.media/files/uploaded-garment.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            # Mock fal_client module
            import sys

            # Create mock handler with async iterator for events
            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-123"

            # Create async iterator that yields nothing (no events)
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())

            # Mock the get() method to return result
            mock_handler.get = AsyncMock(
                return_value={
                    "image": {
                        "url": fake_output_url,
                        "width": 768,
                        "height": 1024,
                        "content_type": "image/png",
                    }
                }
            )

            # Create mock fal_client module
            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]

            # Track upload calls
            upload_call_count = 0

            async def mock_upload(path):
                nonlocal upload_call_count
                upload_call_count += 1
                if upload_call_count == 1:
                    return fake_uploaded_human_url
                return fake_uploaded_garment_url

            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]

            sys.modules["fal_client"] = mock_fal_client

            # Mock storage result
            mock_artifact = ImageArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=768,
                height=1024,
                format="png",
            )

            # Execute generation
            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    # Return a fake local file path
                    if artifact.generation_id == "gen_human":
                        return "/tmp/fake_human.png"
                    return "/tmp/fake_garment.png"

                async def store_image_result(self, **kwargs):
                    return mock_artifact

                async def store_video_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_audio_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_text_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            result = await self.generator.generate(input_data, DummyCtx())

            # Verify result
            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1
            assert result.outputs[0] == mock_artifact

            # Verify file uploads were called twice (human and garment)
            assert mock_fal_client.upload_file_async.call_count == 2

            # Verify API call with uploaded URLs
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/kling/v1-5/kolors-virtual-try-on",
                arguments={
                    "human_image_url": fake_uploaded_human_url,
                    "garment_image_url": fake_uploaded_garment_url,
                    "sync_mode": False,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_no_image_returned(self):
        """Test generation fails when API returns no image."""
        human_artifact = ImageArtifact(
            generation_id="gen_human",
            storage_url="https://example.com/human.png",
            format="png",
            width=768,
            height=1024,
        )
        garment_artifact = ImageArtifact(
            generation_id="gen_garment",
            storage_url="https://example.com/garment.png",
            format="png",
            width=512,
            height=512,
        )

        input_data = KolorsVirtualTryOnInput(
            human_image_url=human_artifact,
            garment_image_url=garment_artifact,
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"

            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={})

            fake_uploaded_url = "https://fal.media/files/uploaded.png"

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(return_value=fake_uploaded_url)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return "/tmp/fake_image.png"

                async def store_image_result(self, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_audio_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_text_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            with pytest.raises(ValueError, match="No image returned"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation."""
        human_artifact = ImageArtifact(
            generation_id="gen_human",
            storage_url="https://example.com/human.png",
            format="png",
            width=768,
            height=1024,
        )
        garment_artifact = ImageArtifact(
            generation_id="gen_garment",
            storage_url="https://example.com/garment.png",
            format="png",
            width=512,
            height=512,
        )

        input_data = KolorsVirtualTryOnInput(
            human_image_url=human_artifact,
            garment_image_url=garment_artifact,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Fixed cost per generation
        assert cost == 0.05
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = KolorsVirtualTryOnInput.model_json_schema()

        assert schema["type"] == "object"
        assert "human_image_url" in schema["properties"]
        assert "garment_image_url" in schema["properties"]
        assert "sync_mode" in schema["properties"]

        # Check sync_mode default
        sync_mode_prop = schema["properties"]["sync_mode"]
        assert sync_mode_prop["default"] is False
