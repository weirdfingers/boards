"""
Tests for FalGptImage15Generator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.gpt_image_1_5 import (
    FalGptImage15Generator,
    GptImage15Input,
)


class TestGptImage15Input:
    """Tests for GptImage15Input schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        prompt = (
            "A serene landscape with mountains reflecting in a "
            "crystal-clear lake at sunset, photorealistic style"
        )
        input_data = GptImage15Input(
            prompt=prompt,
            num_images=2,
            image_size="1536x1024",
            background="opaque",
            quality="high",
            output_format="png",
        )

        assert input_data.prompt == prompt
        assert input_data.num_images == 2
        assert input_data.image_size == "1536x1024"
        assert input_data.background == "opaque"
        assert input_data.quality == "high"
        assert input_data.output_format == "png"

    def test_input_defaults(self):
        """Test default values."""
        input_data = GptImage15Input(
            prompt="Test prompt for image generation",
        )

        assert input_data.num_images == 1
        assert input_data.image_size == "1024x1024"
        assert input_data.background == "auto"
        assert input_data.quality == "high"
        assert input_data.output_format == "png"

    def test_invalid_output_format(self):
        """Test validation fails for invalid output format."""
        with pytest.raises(ValidationError):
            GptImage15Input(
                prompt="Test",
                output_format="invalid",  # type: ignore[arg-type]
            )

    def test_invalid_image_size(self):
        """Test validation fails for invalid image size."""
        with pytest.raises(ValidationError):
            GptImage15Input(
                prompt="Test",
                image_size="512x512",  # type: ignore[arg-type]
            )

    def test_invalid_background(self):
        """Test validation fails for invalid background."""
        with pytest.raises(ValidationError):
            GptImage15Input(
                prompt="Test",
                background="blur",  # type: ignore[arg-type]
            )

    def test_invalid_quality(self):
        """Test validation fails for invalid quality."""
        with pytest.raises(ValidationError):
            GptImage15Input(
                prompt="Test",
                quality="ultra",  # type: ignore[arg-type]
            )

    def test_prompt_min_length(self):
        """Test validation fails for prompt too short."""
        with pytest.raises(ValidationError):
            GptImage15Input(
                prompt="a",  # Only 1 character, minimum is 2
            )

    def test_num_images_validation(self):
        """Test validation for num_images constraints."""
        # Test below minimum
        with pytest.raises(ValidationError):
            GptImage15Input(
                prompt="Test prompt",
                num_images=0,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            GptImage15Input(
                prompt="Test prompt",
                num_images=5,  # Maximum is 4
            )

    def test_output_format_options(self):
        """Test all valid output format options."""
        valid_formats = ["jpeg", "png", "webp"]

        for fmt in valid_formats:
            input_data = GptImage15Input(
                prompt="Test",
                output_format=fmt,  # type: ignore[arg-type]
            )
            assert input_data.output_format == fmt

    def test_image_size_options(self):
        """Test all valid image size options."""
        valid_sizes = ["1024x1024", "1536x1024", "1024x1536"]

        for size in valid_sizes:
            input_data = GptImage15Input(
                prompt="Test",
                image_size=size,  # type: ignore[arg-type]
            )
            assert input_data.image_size == size

    def test_background_options(self):
        """Test all valid background options."""
        valid_backgrounds = ["auto", "transparent", "opaque"]

        for bg in valid_backgrounds:
            input_data = GptImage15Input(
                prompt="Test",
                background=bg,  # type: ignore[arg-type]
            )
            assert input_data.background == bg

    def test_quality_options(self):
        """Test all valid quality options."""
        valid_qualities = ["low", "medium", "high"]

        for quality in valid_qualities:
            input_data = GptImage15Input(
                prompt="Test",
                quality=quality,  # type: ignore[arg-type]
            )
            assert input_data.quality == quality


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalGptImage15Generator:
    """Tests for FalGptImage15Generator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalGptImage15Generator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-gpt-image-1-5"
        assert self.generator.artifact_type == "image"
        assert "GPT Image 1.5" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == GptImage15Input

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = GptImage15Input(
                prompt="Test prompt for generation",
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
    async def test_generate_successful_single_image(self):
        """Test successful generation with single image output."""
        input_data = GptImage15Input(
            prompt="A beautiful sunset over the ocean",
            num_images=1,
            output_format="jpeg",
        )

        fake_output_url = "https://v3b.fal.media/files/b/elephant/generated_image.jpg"

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
                            "width": 1024,
                            "height": 1024,
                        }
                    ],
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
                width=1024,
                height=1024,
                format="jpeg",
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
                "fal-ai/gpt-image-1.5",
                arguments={
                    "prompt": "A beautiful sunset over the ocean",
                    "num_images": 1,
                    "image_size": "1024x1024",
                    "background": "auto",
                    "quality": "high",
                    "output_format": "jpeg",
                },
            )

    @pytest.mark.asyncio
    async def test_generate_successful_multiple_images(self):
        """Test successful generation with multiple image outputs."""
        input_data = GptImage15Input(
            prompt="A futuristic cityscape at night",
            num_images=3,
            output_format="png",
            image_size="1536x1024",
            quality="medium",
            background="opaque",
        )

        fake_output_urls = [
            "https://v3b.fal.media/files/b/elephant/output1.png",
            "https://v3b.fal.media/files/b/elephant/output2.png",
            "https://v3b.fal.media/files/b/elephant/output3.png",
        ]

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            # Create mock handler
            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-456"

            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [
                        {"url": fake_output_urls[0], "width": 1536, "height": 1024},
                        {"url": fake_output_urls[1], "width": 1536, "height": 1024},
                        {"url": fake_output_urls[2], "width": 1536, "height": 1024},
                    ],
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            # Mock storage results
            mock_artifacts = [
                ImageArtifact(
                    generation_id="test_gen",
                    storage_url=url,
                    width=1536,
                    height=1024,
                    format="png",
                )
                for url in fake_output_urls
            ]

            artifact_idx = 0

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return ""

                async def store_image_result(self, **kwargs):
                    nonlocal artifact_idx
                    result = mock_artifacts[artifact_idx]
                    artifact_idx += 1
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

            # Verify API call included all parameters
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["num_images"] == 3
            assert call_args[1]["arguments"]["image_size"] == "1536x1024"
            assert call_args[1]["arguments"]["quality"] == "medium"
            assert call_args[1]["arguments"]["background"] == "opaque"

    @pytest.mark.asyncio
    async def test_generate_no_images_returned(self):
        """Test generation fails when API returns no images."""
        input_data = GptImage15Input(
            prompt="test prompt",
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"

            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={"images": []})

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
    async def test_generate_with_transparent_background(self):
        """Test generation with transparent background."""
        input_data = GptImage15Input(
            prompt="A logo with transparent background",
            background="transparent",
            output_format="png",
        )

        fake_output_url = "https://v3b.fal.media/files/b/elephant/logo.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-transparent"

            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [
                        {
                            "url": fake_output_url,
                            "width": 1024,
                            "height": 1024,
                        }
                    ],
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = ImageArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1024,
                height=1024,
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

            result = await self.generator.generate(input_data, DummyCtx())

            # Verify API call included background parameter
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["background"] == "transparent"

            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1

    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation."""
        input_data = GptImage15Input(
            prompt="Test prompt",
            num_images=1,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Per-image cost (0.04 * 1)
        assert cost == 0.04
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_multiple_images(self):
        """Test cost estimation for multiple images."""
        input_data = GptImage15Input(
            prompt="Test prompt",
            num_images=4,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Per-image cost (0.04 * 4)
        assert cost == 0.16
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = GptImage15Input.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "num_images" in schema["properties"]
        assert "image_size" in schema["properties"]
        assert "background" in schema["properties"]
        assert "quality" in schema["properties"]
        assert "output_format" in schema["properties"]

        # Check that prompt has string constraints
        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop["type"] == "string"
        assert prompt_prop["minLength"] == 2

        # Check that num_images has constraints
        num_images_prop = schema["properties"]["num_images"]
        assert num_images_prop["minimum"] == 1
        assert num_images_prop["maximum"] == 4
        assert num_images_prop["default"] == 1

        # Check that image_size is an enum
        image_size_prop = schema["properties"]["image_size"]
        assert "enum" in image_size_prop
        assert set(image_size_prop["enum"]) == {"1024x1024", "1536x1024", "1024x1536"}

        # Check that output_format is an enum
        output_format_prop = schema["properties"]["output_format"]
        assert "enum" in output_format_prop
        assert set(output_format_prop["enum"]) == {"jpeg", "png", "webp"}

        # Check that background is an enum
        background_prop = schema["properties"]["background"]
        assert "enum" in background_prop
        assert set(background_prop["enum"]) == {"auto", "transparent", "opaque"}

        # Check that quality is an enum
        quality_prop = schema["properties"]["quality"]
        assert "enum" in quality_prop
        assert set(quality_prop["enum"]) == {"low", "medium", "high"}
