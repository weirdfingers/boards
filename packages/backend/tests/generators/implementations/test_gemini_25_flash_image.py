"""
Tests for FalGemini25FlashImageGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.gemini_25_flash_image import (
    FalGemini25FlashImageGenerator,
    Gemini25FlashImageInput,
)


class TestGemini25FlashImageInput:
    """Tests for Gemini25FlashImageInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = Gemini25FlashImageInput(
            prompt="A serene landscape with mountains and a lake",
            num_images=2,
            aspect_ratio="16:9",
            output_format="jpeg",
        )

        assert input_data.prompt == "A serene landscape with mountains and a lake"
        assert input_data.num_images == 2
        assert input_data.aspect_ratio == "16:9"
        assert input_data.output_format == "jpeg"

    def test_input_defaults(self):
        """Test default values."""
        input_data = Gemini25FlashImageInput(prompt="Test prompt")

        assert input_data.num_images == 1
        assert input_data.aspect_ratio == "1:1"
        assert input_data.output_format == "png"
        assert input_data.sync_mode is False
        assert input_data.limit_generations is False

    def test_prompt_min_length(self):
        """Test validation fails for prompt below minimum length."""
        with pytest.raises(ValidationError):
            Gemini25FlashImageInput(prompt="ab")  # Only 2 chars, min is 3

    def test_prompt_max_length(self):
        """Test validation fails for prompt above maximum length."""
        long_prompt = "a" * 5001  # Max is 5000
        with pytest.raises(ValidationError):
            Gemini25FlashImageInput(prompt=long_prompt)

    def test_invalid_output_format(self):
        """Test validation fails for invalid output format."""
        with pytest.raises(ValidationError):
            Gemini25FlashImageInput(
                prompt="Test prompt",
                output_format="bmp",  # type: ignore[arg-type]
            )

    def test_invalid_aspect_ratio(self):
        """Test validation fails for invalid aspect ratio."""
        with pytest.raises(ValidationError):
            Gemini25FlashImageInput(
                prompt="Test prompt",
                aspect_ratio="32:9",  # type: ignore[arg-type]
            )

    def test_num_images_validation(self):
        """Test validation for num_images constraints."""
        # Test below minimum
        with pytest.raises(ValidationError):
            Gemini25FlashImageInput(
                prompt="Test prompt",
                num_images=0,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            Gemini25FlashImageInput(
                prompt="Test prompt",
                num_images=5,
            )

    def test_all_aspect_ratios(self):
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
            input_data = Gemini25FlashImageInput(
                prompt="Test prompt",
                aspect_ratio=ratio,  # type: ignore[arg-type]
            )
            assert input_data.aspect_ratio == ratio

    def test_all_output_formats(self):
        """Test all valid output format options."""
        valid_formats = ["jpeg", "png", "webp"]

        for fmt in valid_formats:
            input_data = Gemini25FlashImageInput(
                prompt="Test prompt",
                output_format=fmt,  # type: ignore[arg-type]
            )
            assert input_data.output_format == fmt


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalGemini25FlashImageGenerator:
    """Tests for FalGemini25FlashImageGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalGemini25FlashImageGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-gemini-25-flash-image"
        assert self.generator.artifact_type == "image"
        assert "Gemini" in self.generator.description
        assert "text-to-image" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == Gemini25FlashImageInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = Gemini25FlashImageInput(prompt="Test prompt")

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
        input_data = Gemini25FlashImageInput(
            prompt="A beautiful sunset over the ocean",
            num_images=1,
            aspect_ratio="16:9",
            output_format="jpeg",
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.jpg"

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
                    "description": "A beautiful sunset over the ocean",
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

            # Verify API call
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/gemini-25-flash-image",
                arguments={
                    "prompt": "A beautiful sunset over the ocean",
                    "num_images": 1,
                    "aspect_ratio": "16:9",
                    "output_format": "jpeg",
                    "sync_mode": False,
                    "limit_generations": False,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_successful_multiple_images(self):
        """Test successful generation with multiple image outputs."""
        input_data = Gemini25FlashImageInput(
            prompt="A futuristic city with flying cars",
            num_images=3,
            aspect_ratio="3:2",
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
                        {"url": fake_output_urls[0], "width": 1500, "height": 1000},
                        {"url": fake_output_urls[1], "width": 1500, "height": 1000},
                        {"url": fake_output_urls[2], "width": 1500, "height": 1000},
                    ],
                    "description": "Futuristic city variations",
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
                    width=1500,
                    height=1000,
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
            assert all(isinstance(artifact, ImageArtifact) for artifact in result.outputs)

    @pytest.mark.asyncio
    async def test_generate_with_missing_dimensions(self):
        """Test generation handles missing width/height by using defaults."""
        input_data = Gemini25FlashImageInput(
            prompt="Abstract art",
            num_images=1,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"

            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            # Return image without width/height
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [
                        {
                            "url": fake_output_url,
                            # Missing width and height
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
                width=1024,  # Default value
                height=1024,  # Default value
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
                    # Verify default dimensions are used
                    assert kwargs["width"] == 1024
                    assert kwargs["height"] == 1024
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

            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1

    @pytest.mark.asyncio
    async def test_generate_no_images_returned(self):
        """Test generation fails when API returns no images."""
        input_data = Gemini25FlashImageInput(prompt="Test prompt")

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-empty"

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
    async def test_estimate_cost(self):
        """Test cost estimation."""
        input_data = Gemini25FlashImageInput(
            prompt="Test prompt",
            num_images=1,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Placeholder cost (0.00 * 1)
        assert cost == 0.00
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_multiple_images(self):
        """Test cost estimation for multiple images."""
        input_data = Gemini25FlashImageInput(
            prompt="Test prompt",
            num_images=4,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Placeholder cost (0.00 * 4)
        assert cost == 0.00
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = Gemini25FlashImageInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "num_images" in schema["properties"]
        assert "aspect_ratio" in schema["properties"]
        assert "output_format" in schema["properties"]

        # Check prompt constraints
        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop["minLength"] == 3
        assert prompt_prop["maxLength"] == 5000

        # Check num_images constraints
        num_images_prop = schema["properties"]["num_images"]
        assert num_images_prop["minimum"] == 1
        assert num_images_prop["maximum"] == 4
        assert num_images_prop["default"] == 1

        # Check aspect_ratio enum
        aspect_ratio_prop = schema["properties"]["aspect_ratio"]
        assert "enum" in aspect_ratio_prop or "anyOf" in aspect_ratio_prop
        assert aspect_ratio_prop["default"] == "1:1"

        # Check output_format enum
        output_format_prop = schema["properties"]["output_format"]
        assert "enum" in output_format_prop or "anyOf" in output_format_prop
        assert output_format_prop["default"] == "png"
