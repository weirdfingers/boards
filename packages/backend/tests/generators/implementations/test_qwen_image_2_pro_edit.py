"""
Tests for FalQwenImage2ProEditGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.qwen_image_2_pro_edit import (
    FalQwenImage2ProEditGenerator,
    ImageSize,
    QwenImage2ProEditInput,
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
            ImageSize(width=256, height=512)

        with pytest.raises(ValidationError):
            ImageSize(width=512, height=100)

    def test_image_size_validation_max(self):
        """Test validation fails for size above maximum."""
        with pytest.raises(ValidationError):
            ImageSize(width=3000, height=512)

        with pytest.raises(ValidationError):
            ImageSize(width=512, height=4096)


class TestQwenImage2ProEditInput:
    """Tests for QwenImage2ProEditInput schema."""

    def _make_artifact(self) -> ImageArtifact:
        return ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

    def test_valid_input(self):
        """Test valid input creation."""
        artifact = self._make_artifact()

        input_data = QwenImage2ProEditInput(
            prompt="Change bag to apple macbook",
            image_urls=[artifact],
            num_images=2,
            output_format="jpeg",
        )

        assert input_data.prompt == "Change bag to apple macbook"
        assert len(input_data.image_urls) == 1
        assert input_data.num_images == 2
        assert input_data.output_format == "jpeg"

    def test_input_defaults(self):
        """Test default values."""
        artifact = self._make_artifact()

        input_data = QwenImage2ProEditInput(
            prompt="Test prompt",
            image_urls=[artifact],
        )

        assert input_data.num_images == 1
        assert input_data.image_size is None
        assert input_data.output_format == "png"
        assert input_data.seed is None
        assert input_data.negative_prompt == ""
        assert input_data.enable_prompt_expansion is True
        assert input_data.sync_mode is False
        assert input_data.enable_safety_checker is True

    def test_multiple_image_urls(self):
        """Test input with multiple reference images."""
        artifacts = [self._make_artifact() for _ in range(3)]

        input_data = QwenImage2ProEditInput(
            prompt="Blend these images",
            image_urls=artifacts,
        )

        assert len(input_data.image_urls) == 3

    def test_too_many_image_urls(self):
        """Test validation fails for more than 3 reference images."""
        artifacts = [self._make_artifact() for _ in range(4)]

        with pytest.raises(ValidationError):
            QwenImage2ProEditInput(
                prompt="Test",
                image_urls=artifacts,
            )

    def test_empty_image_urls(self):
        """Test validation fails for empty image_urls."""
        with pytest.raises(ValidationError):
            QwenImage2ProEditInput(
                prompt="Test",
                image_urls=[],
            )

    def test_invalid_output_format(self):
        """Test validation fails for invalid output format."""
        artifact = self._make_artifact()

        with pytest.raises(ValidationError):
            QwenImage2ProEditInput(
                prompt="Test",
                image_urls=[artifact],
                output_format="bmp",  # type: ignore[arg-type]
            )

    def test_webp_output_format(self):
        """Test webp output format is supported."""
        artifact = self._make_artifact()

        input_data = QwenImage2ProEditInput(
            prompt="Test",
            image_urls=[artifact],
            output_format="webp",
        )

        assert input_data.output_format == "webp"

    def test_invalid_image_size_string(self):
        """Test validation fails for invalid image_size string."""
        artifact = self._make_artifact()

        with pytest.raises(ValidationError):
            QwenImage2ProEditInput(
                prompt="Test",
                image_urls=[artifact],
                image_size="invalid_size",  # type: ignore[arg-type]
            )

    def test_num_images_validation(self):
        """Test validation for num_images constraints."""
        artifact = self._make_artifact()

        with pytest.raises(ValidationError):
            QwenImage2ProEditInput(
                prompt="Test",
                image_urls=[artifact],
                num_images=0,
            )

        with pytest.raises(ValidationError):
            QwenImage2ProEditInput(
                prompt="Test",
                image_urls=[artifact],
                num_images=7,
            )

    def test_image_size_preset_options(self):
        """Test all valid image_size preset options."""
        artifact = self._make_artifact()

        valid_presets = [
            "square_hd",
            "square",
            "portrait_4_3",
            "portrait_16_9",
            "landscape_4_3",
            "landscape_16_9",
        ]

        for preset in valid_presets:
            input_data = QwenImage2ProEditInput(
                prompt="Test",
                image_urls=[artifact],
                image_size=preset,  # type: ignore[arg-type]
            )
            assert input_data.image_size == preset

    def test_image_size_custom_object(self):
        """Test custom image_size with ImageSize object."""
        artifact = self._make_artifact()
        custom_size = ImageSize(width=1920, height=1080)

        input_data = QwenImage2ProEditInput(
            prompt="Test",
            image_urls=[artifact],
            image_size=custom_size,
        )

        assert isinstance(input_data.image_size, ImageSize)
        assert input_data.image_size.width == 1920
        assert input_data.image_size.height == 1080

    def test_seed_validation(self):
        """Test seed range validation."""
        artifact = self._make_artifact()

        with pytest.raises(ValidationError):
            QwenImage2ProEditInput(
                prompt="Test",
                image_urls=[artifact],
                seed=-1,
            )


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalQwenImage2ProEditGenerator:
    """Tests for FalQwenImage2ProEditGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalQwenImage2ProEditGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-qwen-image-2-pro-edit"
        assert self.generator.artifact_type == "image"
        assert "qwen" in self.generator.description.lower()
        assert "edit" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == QwenImage2ProEditInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            artifact = ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/image.png",
                format="png",
                width=1024,
                height=768,
            )

            input_data = QwenImage2ProEditInput(
                prompt="Test prompt",
                image_urls=[artifact],
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

        input_data = QwenImage2ProEditInput(
            prompt="Change bag to apple macbook",
            image_urls=[input_image],
            num_images=1,
            output_format="jpeg",
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.png"
        fake_uploaded_url = "https://fal.media/files/uploaded-input.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-123"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
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
                    "seed": 42,
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(return_value=fake_uploaded_url)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = ImageArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1024,
                height=768,
                format="jpeg",
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

            result = await self.generator.generate(input_data, DummyCtx())

            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1
            assert result.outputs[0] == mock_artifact

            # Verify file upload was called for the input image
            mock_fal_client.upload_file_async.assert_called_once_with("/tmp/fake_image.png")

            # Verify API call
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[0][0] == "fal-ai/qwen-image-2/pro/edit"
            assert call_args[1]["arguments"]["prompt"] == "Change bag to apple macbook"
            assert call_args[1]["arguments"]["image_urls"] == [fake_uploaded_url]
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

        input_data = QwenImage2ProEditInput(
            prompt="enhance the colors",
            image_urls=[input_image],
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
                    "seed": 12345,
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(return_value=fake_uploaded_url)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

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

            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 3

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

        input_data = QwenImage2ProEditInput(
            prompt="test prompt",
            image_urls=[input_image],
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
                    "seed": 42,
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

            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["image_size"] == {"width": 2048, "height": 1536}

    @pytest.mark.asyncio
    async def test_generate_with_multiple_input_images(self):
        """Test generation with multiple reference images."""
        input_images = [
            ImageArtifact(
                generation_id=f"gen_input_{i}",
                storage_url=f"https://example.com/input{i}.png",
                format="png",
                width=1024,
                height=768,
            )
            for i in range(2)
        ]

        input_data = QwenImage2ProEditInput(
            prompt="Blend these images together",
            image_urls=input_images,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.png"
        fake_uploaded_urls = [
            "https://fal.media/files/uploaded-0.png",
            "https://fal.media/files/uploaded-1.png",
        ]

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-multi"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [{"url": fake_output_url, "width": 1024, "height": 768}],
                    "seed": 42,
                }
            )

            upload_call_count = 0

            async def mock_upload(path):
                nonlocal upload_call_count
                url = fake_uploaded_urls[upload_call_count]
                upload_call_count += 1
                return url

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]
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
                    return f"/tmp/fake_image_{artifact.generation_id}.png"

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

            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1

            # Verify both images were uploaded
            assert mock_fal_client.upload_file_async.call_count == 2

            # Verify API call contains both uploaded URLs
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["image_urls"] == fake_uploaded_urls

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

        input_data = QwenImage2ProEditInput(
            prompt="test",
            image_urls=[input_image],
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-empty"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={"images": [], "seed": 0})

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
        artifact = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = QwenImage2ProEditInput(
            prompt="Test prompt",
            image_urls=[artifact],
            num_images=1,
        )

        cost = await self.generator.estimate_cost(input_data)

        assert cost == 0.06
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_multiple_images(self):
        """Test cost estimation for multiple images."""
        artifact = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = QwenImage2ProEditInput(
            prompt="Test prompt",
            image_urls=[artifact],
            num_images=6,
        )

        cost = await self.generator.estimate_cost(input_data)

        assert cost == pytest.approx(0.36)
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = QwenImage2ProEditInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "image_urls" in schema["properties"]
        assert "num_images" in schema["properties"]
        assert "image_size" in schema["properties"]
        assert "output_format" in schema["properties"]
        assert "enable_prompt_expansion" in schema["properties"]
        assert "negative_prompt" in schema["properties"]

        # Check that num_images has constraints
        num_images_prop = schema["properties"]["num_images"]
        assert num_images_prop["minimum"] == 1
        assert num_images_prop["maximum"] == 6
        assert num_images_prop["default"] == 1
