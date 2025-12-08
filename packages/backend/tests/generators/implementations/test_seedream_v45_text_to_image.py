"""
Tests for FalSeedreamV45TextToImageGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.seedream_v45_text_to_image import (
    FalSeedreamV45TextToImageGenerator,
    SeedreamV45TextToImageInput,
)


class TestSeedreamV45TextToImageInput:
    """Tests for SeedreamV45TextToImageInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = SeedreamV45TextToImageInput(
            prompt="A futuristic city at sunset",
            num_images=2,
            image_size="landscape_16_9",
            seed=42,
            enable_safety_checker=True,
        )

        assert input_data.prompt == "A futuristic city at sunset"
        assert input_data.num_images == 2
        assert input_data.image_size == "landscape_16_9"
        assert input_data.seed == 42
        assert input_data.enable_safety_checker is True

    def test_input_defaults(self):
        """Test default values."""
        input_data = SeedreamV45TextToImageInput(prompt="Test prompt")

        assert input_data.num_images == 1
        assert input_data.image_size is None
        assert input_data.seed is None
        assert input_data.enable_safety_checker is True

    def test_invalid_num_images_too_low(self):
        """Test validation fails for num_images below 1."""
        with pytest.raises(ValidationError):
            SeedreamV45TextToImageInput(
                prompt="Test",
                num_images=0,
            )

    def test_invalid_num_images_too_high(self):
        """Test validation fails for num_images above 6."""
        with pytest.raises(ValidationError):
            SeedreamV45TextToImageInput(
                prompt="Test",
                num_images=7,
            )

    def test_invalid_image_size(self):
        """Test validation fails for invalid image size."""
        with pytest.raises(ValidationError):
            SeedreamV45TextToImageInput(
                prompt="Test",
                image_size="invalid",  # type: ignore[arg-type]
            )

    def test_all_image_sizes(self):
        """Test all valid image size options."""
        valid_sizes = [
            "square_hd",
            "portrait_4_3",
            "landscape_16_9",
            "auto_2K",
            "auto_4K",
        ]

        for size in valid_sizes:
            input_data = SeedreamV45TextToImageInput(
                prompt="Test",
                image_size=size,  # type: ignore[arg-type]
            )
            assert input_data.image_size == size

    def test_num_images_boundary_values(self):
        """Test valid boundary values for num_images."""
        # Min value
        input_data = SeedreamV45TextToImageInput(prompt="Test", num_images=1)
        assert input_data.num_images == 1

        # Max value
        input_data = SeedreamV45TextToImageInput(prompt="Test", num_images=6)
        assert input_data.num_images == 6


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalSeedreamV45TextToImageGenerator:
    """Tests for FalSeedreamV45TextToImageGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalSeedreamV45TextToImageGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-seedream-v45-text-to-image"
        assert self.generator.artifact_type == "image"
        assert "Seedream" in self.generator.description
        assert "4.5" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == SeedreamV45TextToImageInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = SeedreamV45TextToImageInput(prompt="Test prompt")

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
        """Test successful generation with single image output."""
        input_data = SeedreamV45TextToImageInput(
            prompt="A beautiful mountain landscape",
            num_images=1,
            image_size="square_hd",
            enable_safety_checker=True,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.png"

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
                    "images": [
                        {
                            "url": fake_output_url,
                            "content_type": "image/png",
                            "width": 2048,
                            "height": 2048,
                            "file_name": "output.png",
                            "file_size": 1024000,
                        }
                    ],
                    "seed": 12345,
                }
            )

            # Create mock fal_client module
            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]

            sys.modules["fal_client"] = mock_fal_client

            # Mock storage result
            mock_artifact = ImageArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=2048,
                height=2048,
                format="png",
            )

            # Execute generation
            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return ""

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

            # Verify API calls
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/bytedance/seedream/v4.5/text-to-image",
                arguments={
                    "prompt": "A beautiful mountain landscape",
                    "num_images": 1,
                    "enable_safety_checker": True,
                    "image_size": "square_hd",
                },
            )

    @pytest.mark.asyncio
    async def test_generate_multiple_images(self):
        """Test successful generation with multiple images."""
        input_data = SeedreamV45TextToImageInput(
            prompt="A test prompt",
            num_images=3,
        )

        fake_output_urls = [
            "https://storage.googleapis.com/falserverless/output1.png",
            "https://storage.googleapis.com/falserverless/output2.png",
            "https://storage.googleapis.com/falserverless/output3.png",
        ]

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-multi"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [
                        {
                            "url": fake_output_urls[0],
                            "content_type": "image/png",
                            "width": 2048,
                            "height": 2048,
                        },
                        {
                            "url": fake_output_urls[1],
                            "content_type": "image/png",
                            "width": 2048,
                            "height": 2048,
                        },
                        {
                            "url": fake_output_urls[2],
                            "content_type": "image/png",
                            "width": 2048,
                            "height": 2048,
                        },
                    ],
                    "seed": 12345,
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            artifacts = []
            for i, url in enumerate(fake_output_urls):
                artifacts.append(
                    ImageArtifact(
                        generation_id=f"test_gen_{i}",
                        storage_url=url,
                        width=2048,
                        height=2048,
                        format="png",
                    )
                )

            artifact_index = 0

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return ""

                async def store_image_result(self, **kwargs):
                    nonlocal artifact_index
                    result = artifacts[artifact_index]
                    artifact_index += 1
                    return result

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
            assert len(result.outputs) == 3

    @pytest.mark.asyncio
    async def test_generate_with_seed(self):
        """Test generation with explicit seed value."""
        input_data = SeedreamV45TextToImageInput(
            prompt="Test prompt",
            seed=42,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-456"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [
                        {
                            "url": fake_output_url,
                            "content_type": "image/png",
                            "width": 2048,
                            "height": 2048,
                        }
                    ],
                    "seed": 42,
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = ImageArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=2048,
                height=2048,
                format="png",
            )

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return ""

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

            await self.generator.generate(input_data, DummyCtx())

            # Verify seed was included in API call
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["seed"] == 42

    @pytest.mark.asyncio
    async def test_generate_no_images_returned(self):
        """Test generation fails when API returns no images."""
        input_data = SeedreamV45TextToImageInput(prompt="test")

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"

            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={"images": [], "seed": 12345})

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return ""

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

            with pytest.raises(ValueError, match="No images returned"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_estimate_cost_single_image(self):
        """Test cost estimation for single image."""
        input_data = SeedreamV45TextToImageInput(prompt="Test prompt", num_images=1)

        cost = await self.generator.estimate_cost(input_data)

        # Cost should be $0.03 per image
        assert cost == 0.03
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_multiple_images(self):
        """Test cost estimation for multiple images."""
        input_data = SeedreamV45TextToImageInput(prompt="Test prompt", num_images=4)

        cost = await self.generator.estimate_cost(input_data)

        # Cost should be $0.03 * 4 = $0.12
        assert cost == 0.12
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = SeedreamV45TextToImageInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "num_images" in schema["properties"]
        assert "image_size" in schema["properties"]
        assert "seed" in schema["properties"]
        assert "enable_safety_checker" in schema["properties"]

        # Check prompt is required
        assert "prompt" in schema["required"]

        # Check num_images has constraints
        num_images_prop = schema["properties"]["num_images"]
        assert num_images_prop.get("minimum") == 1 or num_images_prop.get("default") == 1
