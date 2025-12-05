"""
Tests for FalQwenImageGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.qwen_image import (
    CustomImageSize,
    FalQwenImageGenerator,
    LoraConfig,
    QwenImageInput,
)


class TestLoraConfig:
    """Tests for LoraConfig schema."""

    def test_valid_lora_config(self):
        """Test valid LoRA configuration."""
        lora = LoraConfig(path="https://example.com/lora.safetensors", scale=1.5)

        assert lora.path == "https://example.com/lora.safetensors"
        assert lora.scale == 1.5

    def test_lora_config_defaults(self):
        """Test LoRA configuration defaults."""
        lora = LoraConfig(path="https://example.com/lora.safetensors")

        assert lora.scale == 1.0

    def test_lora_config_scale_validation(self):
        """Test LoRA scale validation."""
        # Test below minimum
        with pytest.raises(ValidationError):
            LoraConfig(path="https://example.com/lora.safetensors", scale=-0.1)

        # Test above maximum
        with pytest.raises(ValidationError):
            LoraConfig(path="https://example.com/lora.safetensors", scale=4.1)


class TestCustomImageSize:
    """Tests for CustomImageSize schema."""

    def test_valid_custom_size(self):
        """Test valid custom image size."""
        size = CustomImageSize(width=1920, height=1080)

        assert size.width == 1920
        assert size.height == 1080


class TestQwenImageInput:
    """Tests for QwenImageInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = QwenImageInput(
            prompt="A serene mountain landscape with text 'Hello World'",
            num_images=2,
            image_size="landscape_16_9",
            output_format="png",
        )

        assert input_data.prompt == "A serene mountain landscape with text 'Hello World'"
        assert input_data.num_images == 2
        assert input_data.image_size == "landscape_16_9"
        assert input_data.output_format == "png"

    def test_input_defaults(self):
        """Test default values."""
        input_data = QwenImageInput(prompt="Test prompt")

        assert input_data.num_images == 1
        assert input_data.num_inference_steps == 30
        assert input_data.image_size == "landscape_4_3"
        assert input_data.output_format == "png"
        assert input_data.guidance_scale == 2.5
        assert input_data.seed is None
        assert input_data.negative_prompt == " "
        assert input_data.acceleration == "none"
        assert input_data.enable_safety_checker is True
        assert input_data.use_turbo is False
        assert input_data.sync_mode is False
        assert input_data.loras == []

    def test_invalid_output_format(self):
        """Test validation fails for invalid output format."""
        with pytest.raises(ValidationError):
            QwenImageInput(
                prompt="Test",
                output_format="invalid",  # type: ignore[arg-type]
            )

    def test_invalid_image_size(self):
        """Test validation fails for invalid image size string."""
        with pytest.raises(ValidationError):
            QwenImageInput(
                prompt="Test",
                image_size="invalid",  # type: ignore[arg-type]
            )

    def test_custom_image_size(self):
        """Test custom image size object."""
        custom_size = CustomImageSize(width=2048, height=1536)
        input_data = QwenImageInput(prompt="Test", image_size=custom_size)

        assert isinstance(input_data.image_size, CustomImageSize)
        assert input_data.image_size.width == 2048
        assert input_data.image_size.height == 1536

    def test_num_images_validation(self):
        """Test validation for num_images constraints."""
        # Test below minimum
        with pytest.raises(ValidationError):
            QwenImageInput(prompt="Test", num_images=0)

        # Test above maximum
        with pytest.raises(ValidationError):
            QwenImageInput(prompt="Test", num_images=5)

    def test_num_inference_steps_validation(self):
        """Test validation for num_inference_steps constraints."""
        # Test below minimum
        with pytest.raises(ValidationError):
            QwenImageInput(prompt="Test", num_inference_steps=1)

        # Test above maximum
        with pytest.raises(ValidationError):
            QwenImageInput(prompt="Test", num_inference_steps=251)

    def test_guidance_scale_validation(self):
        """Test validation for guidance_scale constraints."""
        # Test below minimum
        with pytest.raises(ValidationError):
            QwenImageInput(prompt="Test", guidance_scale=-0.1)

        # Test above maximum
        with pytest.raises(ValidationError):
            QwenImageInput(prompt="Test", guidance_scale=20.1)

    def test_acceleration_options(self):
        """Test all valid acceleration options."""
        valid_accelerations = ["none", "regular", "high"]

        for accel in valid_accelerations:
            input_data = QwenImageInput(
                prompt="Test",
                acceleration=accel,  # type: ignore[arg-type]
            )
            assert input_data.acceleration == accel

    def test_loras_validation(self):
        """Test LoRAs validation (max 3)."""
        loras = [
            LoraConfig(path="https://example.com/lora1.safetensors", scale=1.0),
            LoraConfig(path="https://example.com/lora2.safetensors", scale=1.5),
            LoraConfig(path="https://example.com/lora3.safetensors", scale=2.0),
        ]

        input_data = QwenImageInput(prompt="Test", loras=loras)
        assert len(input_data.loras) == 3

        # Test above maximum (4 LoRAs)
        loras_too_many = loras + [
            LoraConfig(path="https://example.com/lora4.safetensors", scale=1.0)
        ]
        with pytest.raises(ValidationError):
            QwenImageInput(prompt="Test", loras=loras_too_many)


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalQwenImageGenerator:
    """Tests for FalQwenImageGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalQwenImageGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-qwen-image"
        assert self.generator.artifact_type == "image"
        assert "Qwen-Image" in self.generator.description
        assert "text rendering" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == QwenImageInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = QwenImageInput(prompt="Test prompt")

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
        input_data = QwenImageInput(
            prompt="A mountain landscape with text 'Qwen-Image'",
            num_images=1,
            output_format="png",
            image_size="landscape_4_3",
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
                            "width": 1536,
                            "height": 1152,
                            "content_type": "image/png",
                        }
                    ],
                    "seed": 12345,
                    "has_nsfw_concepts": [False],
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
                width=1536,
                height=1152,
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
                "fal-ai/qwen-image",
                arguments={
                    "prompt": "A mountain landscape with text 'Qwen-Image'",
                    "num_images": 1,
                    "num_inference_steps": 30,
                    "image_size": "landscape_4_3",
                    "output_format": "png",
                    "guidance_scale": 2.5,
                    "negative_prompt": " ",
                    "acceleration": "none",
                    "enable_safety_checker": True,
                    "use_turbo": False,
                    "sync_mode": False,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_with_custom_image_size(self):
        """Test generation with custom image dimensions."""
        custom_size = CustomImageSize(width=2048, height=1536)
        input_data = QwenImageInput(
            prompt="Test with custom size",
            image_size=custom_size,
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
                            "width": 2048,
                            "height": 1536,
                            "content_type": "image/png",
                        }
                    ],
                    "seed": 67890,
                    "has_nsfw_concepts": [False],
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = ImageArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=2048,
                height=1536,
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

            # Verify result
            assert isinstance(result, GeneratorResult)
            assert result.outputs == [mock_artifact]

            # Verify custom image_size was passed as dict
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["image_size"] == {"width": 2048, "height": 1536}

    @pytest.mark.asyncio
    async def test_generate_with_loras(self):
        """Test generation with LoRA configurations."""
        loras = [
            LoraConfig(path="https://example.com/lora1.safetensors", scale=1.0),
            LoraConfig(path="https://example.com/lora2.safetensors", scale=1.5),
        ]

        input_data = QwenImageInput(
            prompt="Test with LoRAs",
            loras=loras,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [
                        {
                            "url": fake_output_url,
                            "width": 1024,
                            "height": 768,
                            "content_type": "image/png",
                        }
                    ],
                    "seed": 11111,
                    "has_nsfw_concepts": [False],
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = ImageArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1024,
                height=768,
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

            # Verify result
            assert isinstance(result, GeneratorResult)
            assert result.outputs == [mock_artifact]

            # Verify LoRAs were passed correctly
            call_args = mock_fal_client.submit_async.call_args
            expected_loras = [
                {"path": "https://example.com/lora1.safetensors", "scale": 1.0},
                {"path": "https://example.com/lora2.safetensors", "scale": 1.5},
            ]
            assert call_args[1]["arguments"]["loras"] == expected_loras

    @pytest.mark.asyncio
    async def test_generate_successful_multiple_images(self):
        """Test successful generation with multiple image outputs."""
        input_data = QwenImageInput(
            prompt="Generate multiple test images",
            num_images=3,
            output_format="jpeg",
        )

        fake_output_urls = [
            "https://storage.googleapis.com/falserverless/output1.jpeg",
            "https://storage.googleapis.com/falserverless/output2.jpeg",
            "https://storage.googleapis.com/falserverless/output3.jpeg",
        ]

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-multi"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [
                        {"url": url, "width": 1024, "height": 1024, "content_type": "image/jpeg"}
                        for url in fake_output_urls
                    ],
                    "seed": 99999,
                    "has_nsfw_concepts": [False, False, False],
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifacts = [
                ImageArtifact(
                    generation_id="test_gen",
                    storage_url=url,
                    width=1024,
                    height=1024,
                    format="jpeg",
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

    @pytest.mark.asyncio
    async def test_generate_no_images_returned(self):
        """Test generation fails when API returns no images."""
        input_data = QwenImageInput(prompt="test")

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
    async def test_estimate_cost_single_image(self):
        """Test cost estimation for single image."""
        input_data = QwenImageInput(prompt="Test prompt", num_images=1)

        cost = await self.generator.estimate_cost(input_data)

        assert cost == 0.05
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_multiple_images(self):
        """Test cost estimation for multiple images."""
        input_data = QwenImageInput(prompt="Test prompt", num_images=4)

        cost = await self.generator.estimate_cost(input_data)

        # Per-image cost (0.05 * 4)
        assert cost == 0.20
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = QwenImageInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "num_images" in schema["properties"]
        assert "image_size" in schema["properties"]
        assert "output_format" in schema["properties"]
        assert "loras" in schema["properties"]

        # Check that num_images has constraints
        num_images_prop = schema["properties"]["num_images"]
        assert num_images_prop["minimum"] == 1
        assert num_images_prop["maximum"] == 4
        assert num_images_prop["default"] == 1

        # Check that guidance_scale has constraints
        guidance_scale_prop = schema["properties"]["guidance_scale"]
        assert guidance_scale_prop["minimum"] == 0.0
        assert guidance_scale_prop["maximum"] == 20.0
        assert guidance_scale_prop["default"] == 2.5
