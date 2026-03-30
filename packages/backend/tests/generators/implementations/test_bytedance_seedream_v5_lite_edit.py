"""
Tests for FalBytedanceSeedreamV5LiteEditGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.bytedance_seedream_v5_lite_edit import (
    BytedanceSeedreamV5LiteEditInput,
    FalBytedanceSeedreamV5LiteEditGenerator,
)


class TestBytedanceSeedreamV5LiteEditInput:
    """Tests for BytedanceSeedreamV5LiteEditInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        image_artifact_1 = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image1.png",
            format="png",
            width=1024,
            height=768,
        )
        image_artifact_2 = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/image2.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = BytedanceSeedreamV5LiteEditInput(
            prompt="make the background more vibrant",
            image_sources=[image_artifact_1, image_artifact_2],
            num_images=2,
            image_size="square_hd",
        )

        assert input_data.prompt == "make the background more vibrant"
        assert len(input_data.image_sources) == 2
        assert input_data.num_images == 2
        assert input_data.image_size == "square_hd"

    def test_input_defaults(self):
        """Test default values."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = BytedanceSeedreamV5LiteEditInput(
            prompt="Test prompt",
            image_sources=[image_artifact],
        )

        assert input_data.num_images == 1
        assert input_data.image_size is None
        assert input_data.enable_safety_checker is True
        assert input_data.seed is None

    def test_empty_image_sources(self):
        """Test validation fails for empty image_sources."""
        with pytest.raises(ValidationError):
            BytedanceSeedreamV5LiteEditInput(
                prompt="Test",
                image_sources=[],
            )

    def test_too_many_image_sources(self):
        """Test validation fails for more than 10 images."""
        image_artifacts = [
            ImageArtifact(
                generation_id=f"gen{i}",
                storage_url=f"https://example.com/image{i}.png",
                format="png",
                width=1024,
                height=768,
            )
            for i in range(11)
        ]

        with pytest.raises(ValidationError):
            BytedanceSeedreamV5LiteEditInput(
                prompt="Test",
                image_sources=image_artifacts,
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

        with pytest.raises(ValidationError):
            BytedanceSeedreamV5LiteEditInput(
                prompt="Test",
                image_sources=[image_artifact],
                num_images=0,
            )

        with pytest.raises(ValidationError):
            BytedanceSeedreamV5LiteEditInput(
                prompt="Test",
                image_sources=[image_artifact],
                num_images=7,
            )

    def test_invalid_image_size(self):
        """Test validation fails for invalid image_size."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        with pytest.raises(ValidationError):
            BytedanceSeedreamV5LiteEditInput(
                prompt="Test",
                image_sources=[image_artifact],
                image_size="invalid_size",  # type: ignore[arg-type]
            )

    def test_image_size_options(self):
        """Test all valid image size options."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        valid_sizes = [
            "square_hd",
            "square",
            "portrait_4_3",
            "portrait_16_9",
            "landscape_4_3",
            "landscape_16_9",
            "auto_2K",
            "auto_4K",
        ]

        for size in valid_sizes:
            input_data = BytedanceSeedreamV5LiteEditInput(
                prompt="Test",
                image_sources=[image_artifact],
                image_size=size,  # type: ignore[arg-type]
            )
            assert input_data.image_size == size

    def test_max_images_at_boundary(self):
        """Test 10 images (maximum allowed) is accepted."""
        image_artifacts = [
            ImageArtifact(
                generation_id=f"gen{i}",
                storage_url=f"https://example.com/image{i}.png",
                format="png",
                width=1024,
                height=768,
            )
            for i in range(10)
        ]

        input_data = BytedanceSeedreamV5LiteEditInput(
            prompt="Test",
            image_sources=image_artifacts,
        )
        assert len(input_data.image_sources) == 10


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield


class TestFalBytedanceSeedreamV5LiteEditGenerator:
    """Tests for FalBytedanceSeedreamV5LiteEditGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalBytedanceSeedreamV5LiteEditGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-bytedance-seedream-v5-lite-edit"
        assert self.generator.artifact_type == "image"
        assert "Seedream" in self.generator.description
        assert "5.0" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == BytedanceSeedreamV5LiteEditInput

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

            input_data = BytedanceSeedreamV5LiteEditInput(
                prompt="Test prompt",
                image_sources=[image_artifact],
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

        input_data = BytedanceSeedreamV5LiteEditInput(
            prompt="make the sky more dramatic",
            image_sources=[input_image],
            num_images=1,
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
                            "width": 2048,
                            "height": 2048,
                            "content_type": "image/png",
                        }
                    ],
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
                height=2048,
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

            result = await self.generator.generate(input_data, DummyCtx())

            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1
            assert result.outputs[0] == mock_artifact

            mock_fal_client.upload_file_async.assert_called_once_with("/tmp/fake_image.png")

            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/bytedance/seedream/v5/lite/edit",
                arguments={
                    "prompt": "make the sky more dramatic",
                    "image_urls": [fake_uploaded_url],
                    "num_images": 1,
                    "enable_safety_checker": True,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_successful_multiple_images(self):
        """Test successful generation with multiple image outputs."""
        input_image_1 = ImageArtifact(
            generation_id="gen_input1",
            storage_url="https://example.com/input1.png",
            format="png",
            width=1920,
            height=1080,
        )
        input_image_2 = ImageArtifact(
            generation_id="gen_input2",
            storage_url="https://example.com/input2.png",
            format="png",
            width=1920,
            height=1080,
        )

        input_data = BytedanceSeedreamV5LiteEditInput(
            prompt="enhance the colors",
            image_sources=[input_image_1, input_image_2],
            num_images=2,
            image_size="landscape_16_9",
        )

        fake_output_urls = [
            "https://storage.googleapis.com/falserverless/output1.png",
            "https://storage.googleapis.com/falserverless/output2.png",
        ]
        fake_uploaded_urls = [
            "https://fal.media/files/uploaded-input1.png",
            "https://fal.media/files/uploaded-input2.png",
        ]

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-456"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [
                        {
                            "url": fake_output_urls[0],
                            "width": 1920,
                            "height": 1080,
                            "content_type": "image/jpeg",
                        },
                        {
                            "url": fake_output_urls[1],
                            "width": 1920,
                            "height": 1080,
                            "content_type": "image/jpeg",
                        },
                    ],
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

            mock_artifacts = [
                ImageArtifact(
                    generation_id="test_gen",
                    storage_url=url,
                    width=1920,
                    height=1080,
                    format="jpeg",
                )
                for url in fake_output_urls
            ]

            artifact_idx = 0
            resolve_call_count = 0

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    nonlocal resolve_call_count
                    path = f"/tmp/fake_image_{resolve_call_count}.png"
                    resolve_call_count += 1
                    return path

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
            assert len(result.outputs) == 2

            assert mock_fal_client.upload_file_async.call_count == 2

            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["image_size"] == "landscape_16_9"
            assert call_args[1]["arguments"]["image_urls"] == fake_uploaded_urls

    @pytest.mark.asyncio
    async def test_generate_with_seed(self):
        """Test generation with seed parameter."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = BytedanceSeedreamV5LiteEditInput(
            prompt="test prompt",
            image_sources=[input_image],
            seed=42,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.png"
        fake_uploaded_url = "https://fal.media/files/uploaded-input.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-seed"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [{"url": fake_output_url, "width": 2048, "height": 2048}],
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
                height=2048,
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
            assert call_args[1]["arguments"]["seed"] == 42

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

        input_data = BytedanceSeedreamV5LiteEditInput(
            prompt="test",
            image_sources=[input_image],
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={"images": []})

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

        input_data = BytedanceSeedreamV5LiteEditInput(
            prompt="Test prompt",
            image_sources=[input_image],
            num_images=1,
        )

        cost = await self.generator.estimate_cost(input_data)
        assert cost == 0.035
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

        input_data = BytedanceSeedreamV5LiteEditInput(
            prompt="Test prompt",
            image_sources=[input_image],
            num_images=5,
        )

        cost = await self.generator.estimate_cost(input_data)
        assert cost == pytest.approx(0.175)
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = BytedanceSeedreamV5LiteEditInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "image_sources" in schema["properties"]
        assert "num_images" in schema["properties"]
        assert "image_size" in schema["properties"]
        assert "seed" in schema["properties"]
        assert "enable_safety_checker" in schema["properties"]

        image_sources_prop = schema["properties"]["image_sources"]
        assert image_sources_prop["type"] == "array"
        assert image_sources_prop["minItems"] == 1
        assert image_sources_prop["maxItems"] == 10

        num_images_prop = schema["properties"]["num_images"]
        assert num_images_prop["minimum"] == 1
        assert num_images_prop["maximum"] == 6
        assert num_images_prop["default"] == 1

    @pytest.mark.asyncio
    async def test_content_type_parsing(self):
        """Test that content_type is correctly parsed for image format."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = BytedanceSeedreamV5LiteEditInput(
            prompt="test prompt",
            image_sources=[input_image],
            num_images=1,
        )

        fake_uploaded_url = "https://fal.media/files/uploaded-input.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-content-type"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [
                        {
                            "url": "https://example.com/output.webp",
                            "width": 2048,
                            "height": 2048,
                            "content_type": "image/webp",
                        }
                    ],
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(return_value=fake_uploaded_url)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            stored_format = None

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return "/tmp/fake_image.png"

                async def store_image_result(self, **kwargs):
                    nonlocal stored_format
                    stored_format = kwargs.get("format")
                    return ImageArtifact(
                        generation_id="test_gen",
                        storage_url=kwargs.get("storage_url", ""),
                        width=kwargs.get("width", 2048),
                        height=kwargs.get("height", 2048),
                        format=stored_format or "png",
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

            await self.generator.generate(input_data, DummyCtx())

            assert stored_format == "webp"
