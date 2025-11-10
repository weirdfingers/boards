"""
Tests for FalGptImage1EditImageGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.gpt_image_1_edit_image import (
    FalGptImage1EditImageGenerator,
    GptImage1EditImageInput,
)


class TestGptImage1EditImageInput:
    """Tests for GptImage1EditImageInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = GptImage1EditImageInput(
            prompt="Make this pixel-art style",
            image_urls=[image_artifact],
            num_images=2,
            image_size="1024x1024",
        )

        assert input_data.prompt == "Make this pixel-art style"
        assert len(input_data.image_urls) == 1
        assert input_data.num_images == 2
        assert input_data.image_size == "1024x1024"

    def test_input_defaults(self):
        """Test default values."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = GptImage1EditImageInput(
            prompt="Test prompt",
            image_urls=[image_artifact],
        )

        assert input_data.num_images == 1
        assert input_data.image_size == "auto"
        assert input_data.input_fidelity == "low"
        assert input_data.quality == "auto"

    def test_invalid_image_size(self):
        """Test validation fails for invalid image size."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        with pytest.raises(ValidationError):
            GptImage1EditImageInput(
                prompt="Test",
                image_urls=[image_artifact],
                image_size="invalid",  # type: ignore[arg-type]
            )

    def test_invalid_input_fidelity(self):
        """Test validation fails for invalid input fidelity."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        with pytest.raises(ValidationError):
            GptImage1EditImageInput(
                prompt="Test",
                image_urls=[image_artifact],
                input_fidelity="invalid",  # type: ignore[arg-type]
            )

    def test_invalid_quality(self):
        """Test validation fails for invalid quality."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        with pytest.raises(ValidationError):
            GptImage1EditImageInput(
                prompt="Test",
                image_urls=[image_artifact],
                quality="invalid",  # type: ignore[arg-type]
            )

    def test_empty_image_urls(self):
        """Test validation fails for empty image_urls."""
        with pytest.raises(ValidationError):
            GptImage1EditImageInput(
                prompt="Test",
                image_urls=[],  # Empty list should fail min_length=1
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
            GptImage1EditImageInput(
                prompt="Test",
                image_urls=[image_artifact],
                num_images=0,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            GptImage1EditImageInput(
                prompt="Test",
                image_urls=[image_artifact],
                num_images=5,
            )

    def test_prompt_length_validation(self):
        """Test validation for prompt length constraints."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        # Test empty prompt (below minimum)
        with pytest.raises(ValidationError):
            GptImage1EditImageInput(
                prompt="",
                image_urls=[image_artifact],
            )

        # Test very long prompt (within limit)
        long_prompt = "a" * 32000
        input_data = GptImage1EditImageInput(
            prompt=long_prompt,
            image_urls=[image_artifact],
        )
        assert len(input_data.prompt) == 32000

    def test_image_size_options(self):
        """Test all valid image size options."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        valid_sizes = ["auto", "1024x1024", "1536x1024", "1024x1536"]

        for size in valid_sizes:
            input_data = GptImage1EditImageInput(
                prompt="Test",
                image_urls=[image_artifact],
                image_size=size,  # type: ignore[arg-type]
            )
            assert input_data.image_size == size

    def test_quality_options(self):
        """Test all valid quality options."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        valid_qualities = ["auto", "low", "medium", "high"]

        for quality in valid_qualities:
            input_data = GptImage1EditImageInput(
                prompt="Test",
                image_urls=[image_artifact],
                quality=quality,  # type: ignore[arg-type]
            )
            assert input_data.quality == quality


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalGptImage1EditImageGenerator:
    """Tests for FalGptImage1EditImageGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalGptImage1EditImageGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-gpt-image-1-edit-image"
        assert self.generator.artifact_type == "image"
        assert "GPT-Image-1" in self.generator.description
        assert "OpenAI" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == GptImage1EditImageInput

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

            input_data = GptImage1EditImageInput(
                prompt="Test prompt",
                image_urls=[image_artifact],
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

        input_data = GptImage1EditImageInput(
            prompt="Make this pixel-art style",
            image_urls=[input_image],
            num_images=1,
            image_size="1024x1024",
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
                            "height": 1024,
                            "content_type": "image/png",
                        }
                    ],
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
                height=1024,
                format="png",
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
                "fal-ai/gpt-image-1/edit-image",
                arguments={
                    "prompt": "Make this pixel-art style",
                    "image_urls": [fake_uploaded_url],  # Should use uploaded URL, not original
                    "num_images": 1,
                    "image_size": "1024x1024",
                    "input_fidelity": "low",
                    "quality": "auto",
                },
            )

    @pytest.mark.asyncio
    async def test_generate_successful_multiple_images(self):
        """Test successful generation with multiple image outputs."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1536,
            height=1024,
        )

        input_data = GptImage1EditImageInput(
            prompt="enhance the colors",
            image_urls=[input_image],
            num_images=4,
            image_size="1536x1024",
            input_fidelity="high",
            quality="high",
        )

        fake_output_urls = [
            "https://storage.googleapis.com/falserverless/output1.png",
            "https://storage.googleapis.com/falserverless/output2.png",
            "https://storage.googleapis.com/falserverless/output3.png",
            "https://storage.googleapis.com/falserverless/output4.png",
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
                        {"url": url, "width": 1536, "height": 1024, "content_type": "image/png"}
                        for url in fake_output_urls
                    ],
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
            assert len(result.outputs) == 4

            # Verify file upload was called
            mock_fal_client.upload_file_async.assert_called_once()

            # Verify API call included all parameters
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["image_size"] == "1536x1024"
            assert call_args[1]["arguments"]["input_fidelity"] == "high"
            assert call_args[1]["arguments"]["quality"] == "high"
            assert call_args[1]["arguments"]["num_images"] == 4
            assert call_args[1]["arguments"]["image_urls"] == [fake_uploaded_url]

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

        input_data = GptImage1EditImageInput(
            prompt="test",
            image_urls=[input_image],
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

        input_data = GptImage1EditImageInput(
            prompt="Test prompt",
            image_urls=[input_image],
            num_images=1,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Per-image cost (0.04 * 1)
        assert cost == 0.04
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

        input_data = GptImage1EditImageInput(
            prompt="Test prompt",
            image_urls=[input_image],
            num_images=4,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Per-image cost (0.04 * 4)
        assert cost == 0.16
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = GptImage1EditImageInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "image_urls" in schema["properties"]
        assert "num_images" in schema["properties"]
        assert "image_size" in schema["properties"]
        assert "input_fidelity" in schema["properties"]
        assert "quality" in schema["properties"]

        # Check that image_urls is an array
        image_urls_prop = schema["properties"]["image_urls"]
        assert image_urls_prop["type"] == "array"
        assert "minItems" in image_urls_prop

        # Check that num_images has constraints
        num_images_prop = schema["properties"]["num_images"]
        assert num_images_prop["minimum"] == 1
        assert num_images_prop["maximum"] == 4
        assert num_images_prop["default"] == 1

        # Check prompt constraints
        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop["minLength"] == 1
        assert prompt_prop["maxLength"] == 32000
