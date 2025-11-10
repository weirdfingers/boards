"""
Tests for FalVeo31ReferenceToVideoGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact, VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.veo31_reference_to_video import (
    FalVeo31ReferenceToVideoGenerator,
    Veo31ReferenceToVideoInput,
)


class TestVeo31ReferenceToVideoInput:
    """Tests for Veo31ReferenceToVideoInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        ref_images = [
            ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/ref1.png",
                format="png",
                width=1920,
                height=1080,
            ),
            ImageArtifact(
                generation_id="gen2",
                storage_url="https://example.com/ref2.png",
                format="png",
                width=1920,
                height=1080,
            ),
        ]

        input_data = Veo31ReferenceToVideoInput(
            image_urls=ref_images,
            prompt="A graceful ballerina dancing outside",
            duration="8s",
            resolution="1080p",
            generate_audio=True,
        )

        assert input_data.prompt == "A graceful ballerina dancing outside"
        assert input_data.image_urls == ref_images
        assert input_data.duration == "8s"
        assert input_data.resolution == "1080p"
        assert input_data.generate_audio is True

    def test_input_defaults(self):
        """Test default values."""
        ref_images = [
            ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/ref1.png",
                format="png",
                width=1024,
                height=768,
            ),
        ]

        input_data = Veo31ReferenceToVideoInput(
            image_urls=ref_images,
            prompt="Test prompt",
        )

        assert input_data.duration == "8s"
        assert input_data.resolution == "720p"
        assert input_data.generate_audio is True

    def test_invalid_resolution(self):
        """Test validation fails for invalid resolution."""
        ref_images = [
            ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/ref1.png",
                format="png",
                width=1024,
                height=768,
            ),
        ]

        with pytest.raises(ValidationError):
            Veo31ReferenceToVideoInput(
                image_urls=ref_images,
                prompt="Test",
                resolution="4k",  # type: ignore[arg-type]
            )

    def test_resolution_options(self):
        """Test all valid resolution options."""
        ref_images = [
            ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/ref1.png",
                format="png",
                width=1024,
                height=768,
            ),
        ]

        valid_resolutions = ["720p", "1080p"]

        for resolution in valid_resolutions:
            input_data = Veo31ReferenceToVideoInput(
                image_urls=ref_images,
                prompt="Test",
                resolution=resolution,  # type: ignore[arg-type]
            )
            assert input_data.resolution == resolution


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalVeo31ReferenceToVideoGenerator:
    """Tests for FalVeo31ReferenceToVideoGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalVeo31ReferenceToVideoGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-veo31-reference-to-video"
        assert self.generator.artifact_type == "video"
        assert "Veo 3.1" in self.generator.description
        assert "reference" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == Veo31ReferenceToVideoInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            ref_images = [
                ImageArtifact(
                    generation_id="gen1",
                    storage_url="https://example.com/ref1.png",
                    format="png",
                    width=1024,
                    height=768,
                ),
            ]

            input_data = Veo31ReferenceToVideoInput(
                image_urls=ref_images,
                prompt="Test prompt",
            )

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return ""

                async def store_image_result(self, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, **kwargs):
                    return VideoArtifact(
                        generation_id="test_gen",
                        storage_url="",
                        width=1,
                        height=1,
                        duration=1,
                        format="mp4",
                        fps=None,
                    )

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
    async def test_generate_successful_720p(self):
        """Test successful generation with 720p resolution."""
        ref_images = [
            ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/ref1.png",
                format="png",
                width=1280,
                height=720,
            ),
            ImageArtifact(
                generation_id="gen2",
                storage_url="https://example.com/ref2.png",
                format="png",
                width=1280,
                height=720,
            ),
        ]

        input_data = Veo31ReferenceToVideoInput(
            image_urls=ref_images,
            prompt="A graceful ballerina dancing outside",
            resolution="720p",
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.mp4"
        fake_uploaded_urls = [
            "https://fal.media/files/ref1.png",
            "https://fal.media/files/ref2.png",
        ]

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            # Create mock handler with async iterator for events
            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-123"

            # Create async iterator that yields nothing (no events)
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())

            # Mock the get() method to return result
            mock_handler.get = AsyncMock(
                return_value={
                    "video": {
                        "url": fake_output_url,
                        "content_type": "video/mp4",
                        "file_name": "output.mp4",
                        "file_size": 1024000,
                    }
                }
            )

            # Mock file uploads
            upload_call_count = 0

            async def mock_upload(file_path):
                nonlocal upload_call_count
                url = fake_uploaded_urls[upload_call_count]
                upload_call_count += 1
                return url

            # Create mock fal_client module
            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]

            sys.modules["fal_client"] = mock_fal_client

            # Mock storage result
            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1280,
                height=720,
                duration=8,
                format="mp4",
                fps=None,
            )

            resolve_call_count = 0

            # Execute generation
            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    nonlocal resolve_call_count
                    # Return different fake paths for reference images
                    path = f"/tmp/fake_ref_{resolve_call_count}.png"
                    resolve_call_count += 1
                    return path

                async def store_image_result(self, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, **kwargs):
                    return mock_artifact

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

            # Verify file uploads were called for all reference images
            assert mock_fal_client.upload_file_async.call_count == 2

            # Verify API calls with uploaded URLs
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/veo3.1/reference-to-video",
                arguments={
                    "image_urls": fake_uploaded_urls,
                    "prompt": "A graceful ballerina dancing outside",
                    "duration": "8s",
                    "resolution": "720p",
                    "generate_audio": True,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_successful_1080p(self):
        """Test successful generation with 1080p resolution."""
        ref_images = [
            ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/ref1.png",
                format="png",
                width=1920,
                height=1080,
            ),
        ]

        input_data = Veo31ReferenceToVideoInput(
            image_urls=ref_images,
            prompt="cinematic video effect",
            resolution="1080p",
            generate_audio=False,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.mp4"
        fake_uploaded_urls = [
            "https://fal.media/files/ref1.png",
        ]

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-456"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "video": {
                        "url": fake_output_url,
                        "content_type": "video/mp4",
                    }
                }
            )

            upload_call_count = 0

            async def mock_upload(file_path):
                nonlocal upload_call_count
                url = fake_uploaded_urls[upload_call_count]
                upload_call_count += 1
                return url

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1920,
                height=1080,
                duration=8,
                format="mp4",
                fps=None,
            )

            resolve_call_count = 0

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    nonlocal resolve_call_count
                    path = f"/tmp/fake_ref_{resolve_call_count}.png"
                    resolve_call_count += 1
                    return path

                async def store_image_result(self, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, **kwargs):
                    return mock_artifact

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

            # Verify API call arguments
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["resolution"] == "1080p"
            assert call_args[1]["arguments"]["generate_audio"] is False

    @pytest.mark.asyncio
    async def test_generate_no_video_returned(self):
        """Test generation fails when API returns no video."""
        ref_images = [
            ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/ref1.png",
                format="png",
                width=1024,
                height=768,
            ),
        ]

        input_data = Veo31ReferenceToVideoInput(
            image_urls=ref_images,
            prompt="test",
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={})  # No video field

            fake_uploaded_urls = [
                "https://fal.media/files/ref1.png",
            ]
            upload_call_count = 0

            async def mock_upload(file_path):
                nonlocal upload_call_count
                url = fake_uploaded_urls[upload_call_count]
                upload_call_count += 1
                return url

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            resolve_call_count = 0

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    nonlocal resolve_call_count
                    path = f"/tmp/fake_ref_{resolve_call_count}.png"
                    resolve_call_count += 1
                    return path

                async def store_image_result(self, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, **kwargs):
                    raise NotImplementedError

                async def store_audio_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_text_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            with pytest.raises(ValueError, match="No video returned"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_estimate_cost_with_audio(self):
        """Test cost estimation with audio enabled."""
        ref_images = [
            ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/ref1.png",
                format="png",
                width=1024,
                height=768,
            ),
        ]

        input_data = Veo31ReferenceToVideoInput(
            image_urls=ref_images,
            prompt="Test prompt",
            generate_audio=True,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Base cost with audio
        assert cost == 0.15
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_without_audio(self):
        """Test cost estimation with audio disabled (50% cheaper)."""
        ref_images = [
            ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/ref1.png",
                format="png",
                width=1024,
                height=768,
            ),
        ]

        input_data = Veo31ReferenceToVideoInput(
            image_urls=ref_images,
            prompt="Test prompt",
            generate_audio=False,
        )

        cost = await self.generator.estimate_cost(input_data)

        # 50% of base cost when audio disabled
        assert cost == 0.075
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = Veo31ReferenceToVideoInput.model_json_schema()

        assert schema["type"] == "object"
        assert "image_urls" in schema["properties"]
        assert "prompt" in schema["properties"]
        assert "duration" in schema["properties"]
        assert "resolution" in schema["properties"]
        assert "generate_audio" in schema["properties"]

        # Check that required fields are marked
        assert set(schema["required"]) == {"image_urls", "prompt"}

        # Check defaults
        duration_prop = schema["properties"]["duration"]
        assert duration_prop["default"] == "8s"

        resolution_prop = schema["properties"]["resolution"]
        assert resolution_prop["default"] == "720p"

        generate_audio_prop = schema["properties"]["generate_audio"]
        assert generate_audio_prop["default"] is True
