"""
Tests for FalNanoBananaEditGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.nano_banana_edit import (
    FalNanoBananaEditGenerator,
    NanoBananaEditInput,
)


class TestNanoBananaEditInput:
    """Tests for NanoBananaEditInput schema."""

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

        input_data = NanoBananaEditInput(
            prompt="make a photo of the man driving the car",
            image_sources=[image_artifact_1, image_artifact_2],
            num_images=2,
            output_format="jpeg",
        )

        assert input_data.prompt == "make a photo of the man driving the car"
        assert len(input_data.image_sources) == 2
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

        input_data = NanoBananaEditInput(
            prompt="Test prompt",
            image_sources=[image_artifact],
        )

        assert input_data.num_images == 1
        assert input_data.output_format == "jpeg"
        assert input_data.sync_mode is False
        assert input_data.limit_generations is False
        assert input_data.aspect_ratio is None

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
            NanoBananaEditInput(
                prompt="Test",
                image_sources=[image_artifact],
                output_format="invalid",  # type: ignore[arg-type]
            )

    def test_invalid_aspect_ratio(self):
        """Test validation fails for invalid aspect ratio."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        with pytest.raises(ValidationError):
            NanoBananaEditInput(
                prompt="Test",
                image_sources=[image_artifact],
                aspect_ratio="invalid",  # type: ignore[arg-type]
            )

    def test_empty_image_sources(self):
        """Test validation fails for empty image_sources."""
        with pytest.raises(ValidationError):
            NanoBananaEditInput(
                prompt="Test",
                image_sources=[],  # Empty list should fail min_length=1
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
            NanoBananaEditInput(
                prompt="Test",
                image_sources=[image_artifact],
                num_images=0,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            NanoBananaEditInput(
                prompt="Test",
                image_sources=[image_artifact],
                num_images=11,
            )

    def test_aspect_ratio_options(self):
        """Test all valid aspect ratio options."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        valid_ratios = [
            "21:9",
            "1:1",
            "4:3",
            "3:2",
            "2:3",
            "5:4",
            "4:5",
            "3:4",
            "16:9",
            "9:16",
        ]

        for ratio in valid_ratios:
            input_data = NanoBananaEditInput(
                prompt="Test",
                image_sources=[image_artifact],
                aspect_ratio=ratio,  # type: ignore[arg-type]
            )
            assert input_data.aspect_ratio == ratio


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalNanoBananaEditGenerator:
    """Tests for FalNanoBananaEditGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalNanoBananaEditGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-nano-banana-edit"
        assert self.generator.artifact_type == "image"
        assert "edit" in self.generator.description.lower()
        assert "Gemini" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == NanoBananaEditInput

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

            input_data = NanoBananaEditInput(
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

        input_data = NanoBananaEditInput(
            prompt="make the sky more dramatic",
            image_sources=[input_image],
            num_images=1,
            output_format="jpeg",
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.png"
        fake_description = "Here is a photo with a more dramatic sky."
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
                        }
                    ],
                    "description": fake_description,
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
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/nano-banana/edit",
                arguments={
                    "prompt": "make the sky more dramatic",
                    "image_urls": [fake_uploaded_url],  # Should use uploaded URL, not original
                    "num_images": 1,
                    "output_format": "jpeg",
                    "sync_mode": False,
                    "limit_generations": False,
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

        input_data = NanoBananaEditInput(
            prompt="enhance the colors",
            image_sources=[input_image_1, input_image_2],
            num_images=2,
            output_format="png",
            aspect_ratio="16:9",
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

            # Create mock handler
            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-456"

            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [
                        {"url": fake_output_urls[0], "width": 1920, "height": 1080},
                        {"url": fake_output_urls[1], "width": 1920, "height": 1080},
                    ],
                    "description": "Enhanced colors applied.",
                }
            )

            # Mock file uploads to return different URLs for each file
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
            resolve_call_count = 0

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    nonlocal resolve_call_count
                    # Return different fake paths for each artifact
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

            # Verify result
            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 2

            # Verify file uploads were called for both images
            assert mock_fal_client.upload_file_async.call_count == 2

            # Verify API call included aspect_ratio and uploaded URLs
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["aspect_ratio"] == "16:9"
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

        input_data = NanoBananaEditInput(
            prompt="test",
            image_sources=[input_image],
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"

            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={"images": [], "description": ""})

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

        input_data = NanoBananaEditInput(
            prompt="Test prompt",
            image_sources=[input_image],
            num_images=1,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Per-image cost (0.039 * 1)
        assert cost == 0.039
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

        input_data = NanoBananaEditInput(
            prompt="Test prompt",
            image_sources=[input_image],
            num_images=5,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Per-image cost (0.039 * 5)
        assert cost == 0.195
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = NanoBananaEditInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "image_sources" in schema["properties"]
        assert "num_images" in schema["properties"]
        assert "output_format" in schema["properties"]
        assert "aspect_ratio" in schema["properties"]

        # Check that image_sources is an array
        image_sources_prop = schema["properties"]["image_sources"]
        assert image_sources_prop["type"] == "array"
        assert "minItems" in image_sources_prop

        # Check that num_images has constraints
        num_images_prop = schema["properties"]["num_images"]
        assert num_images_prop["minimum"] == 1
        assert num_images_prop["maximum"] == 10
        assert num_images_prop["default"] == 1
