"""
Tests for FalQwenImageEditGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.qwen_image_edit import (
    FalQwenImageEditGenerator,
    ImageSize,
    QwenImageEditInput,
)


class TestImageSize:
    """Tests for ImageSize schema."""

    def test_valid_image_size(self):
        """Test valid custom image size creation."""
        size = ImageSize(width=1024, height=768)

        assert size.width == 1024
        assert size.height == 768

    def test_image_size_defaults(self):
        """Test default values for image size."""
        size = ImageSize()

        assert size.width == 512
        assert size.height == 512

    def test_image_size_validation_min(self):
        """Test validation fails for size below minimum."""
        with pytest.raises(ValidationError):
            ImageSize(width=0, height=512)

        with pytest.raises(ValidationError):
            ImageSize(width=512, height=-1)

    def test_image_size_validation_max(self):
        """Test validation fails for size above maximum."""
        with pytest.raises(ValidationError):
            ImageSize(width=15000, height=512)

        with pytest.raises(ValidationError):
            ImageSize(width=512, height=20000)


class TestQwenImageEditInput:
    """Tests for QwenImageEditInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = QwenImageEditInput(
            prompt="Change bag to apple macbook",
            image_url=image_artifact,
            num_images=2,
            output_format="jpeg",
        )

        assert input_data.prompt == "Change bag to apple macbook"
        assert input_data.image_url == image_artifact
        assert input_data.num_images == 2
        assert input_data.output_format == "jpeg"

    def test_input_defaults(self):
        """Test default values."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = QwenImageEditInput(
            prompt="Test prompt",
            image_url=image_artifact,
        )

        assert input_data.num_images == 1
        assert input_data.image_size is None
        assert input_data.acceleration == "regular"
        assert input_data.output_format == "png"
        assert input_data.guidance_scale == 4.0
        assert input_data.num_inference_steps == 30
        assert input_data.seed is None
        assert input_data.negative_prompt == " "
        assert input_data.sync_mode is False
        assert input_data.enable_safety_checker is True

    def test_invalid_output_format(self):
        """Test validation fails for invalid output format."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        with pytest.raises(ValidationError):
            QwenImageEditInput(
                prompt="Test",
                image_url=image_artifact,
                output_format="invalid",  # type: ignore[arg-type]
            )

    def test_invalid_acceleration(self):
        """Test validation fails for invalid acceleration."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        with pytest.raises(ValidationError):
            QwenImageEditInput(
                prompt="Test",
                image_url=image_artifact,
                acceleration="turbo",  # type: ignore[arg-type]
            )

    def test_invalid_image_size_string(self):
        """Test validation fails for invalid image_size string."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        with pytest.raises(ValidationError):
            QwenImageEditInput(
                prompt="Test",
                image_url=image_artifact,
                image_size="invalid_size",  # type: ignore[arg-type]
            )

    def test_num_images_validation(self):
        """Test validation for num_images constraints."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        # Test below minimum
        with pytest.raises(ValidationError):
            QwenImageEditInput(
                prompt="Test",
                image_url=image_artifact,
                num_images=0,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            QwenImageEditInput(
                prompt="Test",
                image_url=image_artifact,
                num_images=5,
            )

    def test_guidance_scale_validation(self):
        """Test validation for guidance_scale constraints."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        # Test below minimum
        with pytest.raises(ValidationError):
            QwenImageEditInput(
                prompt="Test",
                image_url=image_artifact,
                guidance_scale=-1.0,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            QwenImageEditInput(
                prompt="Test",
                image_url=image_artifact,
                guidance_scale=25.0,
            )

    def test_num_inference_steps_validation(self):
        """Test validation for num_inference_steps constraints."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        # Test below minimum
        with pytest.raises(ValidationError):
            QwenImageEditInput(
                prompt="Test",
                image_url=image_artifact,
                num_inference_steps=1,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            QwenImageEditInput(
                prompt="Test",
                image_url=image_artifact,
                num_inference_steps=100,
            )

    def test_image_size_preset_options(self):
        """Test all valid image_size preset options."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        valid_presets = [
            "square_hd",
            "square",
            "portrait_4_3",
            "portrait_16_9",
            "landscape_4_3",
            "landscape_16_9",
        ]

        for preset in valid_presets:
            input_data = QwenImageEditInput(
                prompt="Test",
                image_url=image_artifact,
                image_size=preset,  # type: ignore[arg-type]
            )
            assert input_data.image_size == preset

    def test_image_size_custom_object(self):
        """Test custom image_size with ImageSize object."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        custom_size = ImageSize(width=1920, height=1080)

        input_data = QwenImageEditInput(
            prompt="Test",
            image_url=image_artifact,
            image_size=custom_size,
        )

        assert input_data.image_size == custom_size
        assert isinstance(input_data.image_size, ImageSize)
        assert input_data.image_size.width == 1920
        assert input_data.image_size.height == 1080

    def test_acceleration_options(self):
        """Test all valid acceleration options."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        valid_accelerations = ["none", "regular", "high"]

        for acceleration in valid_accelerations:
            input_data = QwenImageEditInput(
                prompt="Test",
                image_url=image_artifact,
                acceleration=acceleration,  # type: ignore[arg-type]
            )
            assert input_data.acceleration == acceleration


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalQwenImageEditGenerator:
    """Tests for FalQwenImageEditGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalQwenImageEditGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-qwen-image-edit"
        assert self.generator.artifact_type == "image"
        assert "qwen" in self.generator.description.lower()
        assert "edit" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == QwenImageEditInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            image_artifact = ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/image.png",
                format="png",
                width=1024,
                height=768,
            )

            input_data = QwenImageEditInput(
                prompt="Test prompt",
                image_url=image_artifact,
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
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = QwenImageEditInput(
            prompt="Change bag to apple macbook",
            image_url=input_image,
            num_images=1,
            output_format="jpeg",
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.png"
        fake_uploaded_url = "https://fal.media/files/uploaded-input.png"

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
                            "height": 768,
                            "content_type": "image/jpeg",
                        }
                    ],
                    "prompt": "Change bag to apple macbook",
                    "seed": 42,
                    "has_nsfw_concepts": [False],
                }
            )

            # Create mock fal_client module
            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(return_value=fake_uploaded_url)  # type: ignore[attr-defined]

            sys.modules["fal_client"] = mock_fal_client

            # Mock storage result
            mock_artifact = ImageArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1024,
                height=768,
                format="jpeg",
            )

            # Execute generation
            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    # Return a fake local file path
                    return "/tmp/fake_image.png"

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

            # Verify file upload was called
            mock_fal_client.upload_file_async.assert_called_once_with("/tmp/fake_image.png")

            # Verify API calls with uploaded URL
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[0][0] == "fal-ai/qwen-image-edit"
            assert call_args[1]["arguments"]["prompt"] == "Change bag to apple macbook"
            assert call_args[1]["arguments"]["image_url"] == fake_uploaded_url
            assert call_args[1]["arguments"]["num_images"] == 1
            assert call_args[1]["arguments"]["output_format"] == "jpeg"

    @pytest.mark.asyncio
    async def test_generate_successful_multiple_images(self):
        """Test successful generation with multiple image outputs."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1920,
            height=1080,
        )

        input_data = QwenImageEditInput(
            prompt="enhance the colors",
            image_url=input_image,
            num_images=3,
            output_format="png",
            image_size="landscape_16_9",
        )

        fake_output_urls = [
            "https://storage.googleapis.com/falserverless/output1.png",
            "https://storage.googleapis.com/falserverless/output2.png",
            "https://storage.googleapis.com/falserverless/output3.png",
        ]
        fake_uploaded_url = "https://fal.media/files/uploaded-input.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            # Create mock handler
            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-456"

            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [
                        {"url": fake_output_urls[0], "width": 1920, "height": 1080},
                        {"url": fake_output_urls[1], "width": 1920, "height": 1080},
                        {"url": fake_output_urls[2], "width": 1920, "height": 1080},
                    ],
                    "prompt": "enhance the colors",
                    "seed": 12345,
                    "has_nsfw_concepts": [False, False, False],
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(return_value=fake_uploaded_url)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            # Mock storage results
            mock_artifacts = [
                ImageArtifact(
                    generation_id="test_gen",
                    storage_url=url,
                    width=1920,
                    height=1080,
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
                    return "/tmp/fake_image.png"

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

            # Verify API call included image_size
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["image_size"] == "landscape_16_9"

    @pytest.mark.asyncio
    async def test_generate_with_custom_image_size(self):
        """Test generation with custom ImageSize object."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        custom_size = ImageSize(width=2048, height=1536)

        input_data = QwenImageEditInput(
            prompt="test prompt",
            image_url=input_image,
            image_size=custom_size,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.png"
        fake_uploaded_url = "https://fal.media/files/uploaded.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"

            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [{"url": fake_output_url, "width": 2048, "height": 1536}],
                    "prompt": "test prompt",
                    "seed": 42,
                    "has_nsfw_concepts": [False],
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(return_value=fake_uploaded_url)  # type: ignore[attr-defined]
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
                    return "/tmp/fake_image.png"

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

            # Verify API call included custom image_size as dict
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["image_size"] == {"width": 2048, "height": 1536}

    @pytest.mark.asyncio
    async def test_generate_no_images_returned(self):
        """Test generation fails when API returns no images."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = QwenImageEditInput(
            prompt="test",
            image_url=input_image,
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-empty"

            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={"images": [], "prompt": "test", "seed": 0, "has_nsfw_concepts": []}
            )

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

            with pytest.raises(ValueError, match="No images returned"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = QwenImageEditInput(
            prompt="Test prompt",
            image_url=input_image,
            num_images=1,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Per-image cost (0.05 * 1)
        assert cost == 0.05
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_multiple_images(self):
        """Test cost estimation for multiple images."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = QwenImageEditInput(
            prompt="Test prompt",
            image_url=input_image,
            num_images=4,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Per-image cost (0.05 * 4)
        assert cost == 0.20
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = QwenImageEditInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "image_url" in schema["properties"]
        assert "num_images" in schema["properties"]
        assert "image_size" in schema["properties"]
        assert "output_format" in schema["properties"]
        assert "acceleration" in schema["properties"]
        assert "guidance_scale" in schema["properties"]
        assert "num_inference_steps" in schema["properties"]

        # Check that num_images has constraints
        num_images_prop = schema["properties"]["num_images"]
        assert num_images_prop["minimum"] == 1
        assert num_images_prop["maximum"] == 4
        assert num_images_prop["default"] == 1

        # Check that guidance_scale has constraints
        guidance_scale_prop = schema["properties"]["guidance_scale"]
        assert guidance_scale_prop["minimum"] == 0.0
        assert guidance_scale_prop["maximum"] == 20.0
        assert guidance_scale_prop["default"] == 4.0

        # Check that num_inference_steps has constraints
        num_inference_steps_prop = schema["properties"]["num_inference_steps"]
        assert num_inference_steps_prop["minimum"] == 2
        assert num_inference_steps_prop["maximum"] == 50
        assert num_inference_steps_prop["default"] == 30
