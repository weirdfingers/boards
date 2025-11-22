"""
Tests for FalNanoBananaProGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.nano_banana_pro import (
    FalNanoBananaProGenerator,
    NanoBananaProInput,
)


class TestNanoBananaProInput:
    """Tests for NanoBananaProInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = NanoBananaProInput(
            prompt="A beautiful sunset over the ocean",
            aspect_ratio="16:9",
            num_images=2,
            resolution="2K",
            output_format="jpeg",
        )

        assert input_data.prompt == "A beautiful sunset over the ocean"
        assert input_data.aspect_ratio == "16:9"
        assert input_data.num_images == 2
        assert input_data.resolution == "2K"
        assert input_data.output_format == "jpeg"

    def test_input_defaults(self):
        """Test default values."""
        input_data = NanoBananaProInput(
            prompt="Test prompt",
        )

        assert input_data.aspect_ratio == "1:1"
        assert input_data.num_images == 1
        assert input_data.resolution == "1K"
        assert input_data.output_format == "png"
        assert input_data.sync_mode is True

    def test_prompt_min_length(self):
        """Test validation fails for prompt below minimum length."""
        with pytest.raises(ValidationError):
            NanoBananaProInput(
                prompt="ab",  # 2 chars, minimum is 3
            )

    def test_invalid_output_format(self):
        """Test validation fails for invalid output format."""
        with pytest.raises(ValidationError):
            NanoBananaProInput(
                prompt="Test prompt",
                output_format="invalid",  # type: ignore[arg-type]
            )

    def test_invalid_aspect_ratio(self):
        """Test validation fails for invalid aspect ratio."""
        with pytest.raises(ValidationError):
            NanoBananaProInput(
                prompt="Test prompt",
                aspect_ratio="invalid",  # type: ignore[arg-type]
            )

    def test_invalid_resolution(self):
        """Test validation fails for invalid resolution."""
        with pytest.raises(ValidationError):
            NanoBananaProInput(
                prompt="Test prompt",
                resolution="8K",  # type: ignore[arg-type]
            )

    def test_num_images_validation(self):
        """Test validation for num_images constraints."""
        # Test below minimum
        with pytest.raises(ValidationError):
            NanoBananaProInput(
                prompt="Test prompt",
                num_images=0,
            )

        # Test above maximum (max is 4 for nano-banana-pro)
        with pytest.raises(ValidationError):
            NanoBananaProInput(
                prompt="Test prompt",
                num_images=5,
            )

    def test_aspect_ratio_options(self):
        """Test all valid aspect ratio options."""
        valid_ratios = [
            "21:9",
            "16:9",
            "3:2",
            "4:3",
            "5:4",
            "1:1",
            "4:5",
            "3:4",
            "2:3",
            "9:16",
        ]

        for ratio in valid_ratios:
            input_data = NanoBananaProInput(
                prompt="Test prompt",
                aspect_ratio=ratio,  # type: ignore[arg-type]
            )
            assert input_data.aspect_ratio == ratio

    def test_resolution_options(self):
        """Test all valid resolution options."""
        valid_resolutions = ["1K", "2K", "4K"]

        for resolution in valid_resolutions:
            input_data = NanoBananaProInput(
                prompt="Test prompt",
                resolution=resolution,  # type: ignore[arg-type]
            )
            assert input_data.resolution == resolution

    def test_output_format_options(self):
        """Test all valid output format options."""
        valid_formats = ["jpeg", "png", "webp"]

        for fmt in valid_formats:
            input_data = NanoBananaProInput(
                prompt="Test prompt",
                output_format=fmt,  # type: ignore[arg-type]
            )
            assert input_data.output_format == fmt


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalNanoBananaProGenerator:
    """Tests for FalNanoBananaProGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalNanoBananaProGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-nano-banana-pro"
        assert self.generator.artifact_type == "image"
        assert "nano-banana-pro" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == NanoBananaProInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = NanoBananaProInput(
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
        input_data = NanoBananaProInput(
            prompt="A beautiful landscape",
            aspect_ratio="16:9",
            num_images=1,
            resolution="1K",
            output_format="jpeg",
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
                            "width": 1920,
                            "height": 1080,
                        }
                    ],
                    "description": "A beautiful landscape image.",
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
                width=1920,
                height=1080,
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
                "fal-ai/nano-banana-pro",
                arguments={
                    "prompt": "A beautiful landscape",
                    "aspect_ratio": "16:9",
                    "num_images": 1,
                    "resolution": "1K",
                    "output_format": "jpeg",
                    "sync_mode": True,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_successful_multiple_images(self):
        """Test successful generation with multiple image outputs."""
        input_data = NanoBananaProInput(
            prompt="Abstract art",
            aspect_ratio="1:1",
            num_images=3,
            resolution="2K",
            output_format="png",
        )

        fake_output_urls = [
            "https://storage.googleapis.com/falserverless/output1.png",
            "https://storage.googleapis.com/falserverless/output2.png",
            "https://storage.googleapis.com/falserverless/output3.png",
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
                        {"url": fake_output_urls[0], "width": 2048, "height": 2048},
                        {"url": fake_output_urls[1], "width": 2048, "height": 2048},
                        {"url": fake_output_urls[2], "width": 2048, "height": 2048},
                    ],
                    "description": "Abstract art images.",
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
                    width=2048,
                    height=2048,
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

            # Verify API call
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["num_images"] == 3
            assert call_args[1]["arguments"]["resolution"] == "2K"

    @pytest.mark.asyncio
    async def test_generate_no_images_returned(self):
        """Test generation fails when API returns no images."""
        input_data = NanoBananaProInput(
            prompt="Test prompt",
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"

            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={"images": [], "description": ""})

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
    async def test_generate_missing_url_in_response(self):
        """Test generation fails when image data is missing URL."""
        input_data = NanoBananaProInput(
            prompt="Test prompt",
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-000"

            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [{"width": 1024, "height": 1024}],  # Missing url
                    "description": "",
                }
            )

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

            with pytest.raises(ValueError, match="missing URL"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation."""
        input_data = NanoBananaProInput(
            prompt="Test prompt",
            num_images=1,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Per-image cost (0.039 * 1)
        assert cost == 0.039
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_multiple_images(self):
        """Test cost estimation for multiple images."""
        input_data = NanoBananaProInput(
            prompt="Test prompt",
            num_images=4,  # Max for nano-banana-pro
        )

        cost = await self.generator.estimate_cost(input_data)

        # Per-image cost (0.039 * 4)
        assert cost == pytest.approx(0.156)
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = NanoBananaProInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "aspect_ratio" in schema["properties"]
        assert "num_images" in schema["properties"]
        assert "resolution" in schema["properties"]
        assert "output_format" in schema["properties"]

        # Check that num_images has constraints
        num_images_prop = schema["properties"]["num_images"]
        assert num_images_prop["minimum"] == 1
        assert num_images_prop["maximum"] == 4
        assert num_images_prop["default"] == 1

        # Check that prompt has length constraints
        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop["minLength"] == 3
        assert prompt_prop["maxLength"] == 50000
