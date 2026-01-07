"""
Tests for FalGptImage15EditGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.gpt_image_15_edit import (
    FalGptImage15EditGenerator,
    GptImage15EditInput,
)


class TestGptImage15EditInput:
    """Tests for GptImage15EditInput schema."""

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

        input_data = GptImage15EditInput(
            prompt="Make the image look vintage",
            image_urls=[image_artifact_1, image_artifact_2],
            num_images=2,
            output_format="jpeg",
            quality="medium",
        )

        assert input_data.prompt == "Make the image look vintage"
        assert len(input_data.image_urls) == 2
        assert input_data.num_images == 2
        assert input_data.output_format == "jpeg"
        assert input_data.quality == "medium"

    def test_input_defaults(self):
        """Test default values."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = GptImage15EditInput(
            prompt="Test prompt",
            image_urls=[image_artifact],
        )

        assert input_data.num_images == 1
        assert input_data.output_format == "png"
        assert input_data.quality == "high"
        assert input_data.input_fidelity == "high"
        assert input_data.image_size == "auto"
        assert input_data.background == "auto"
        assert input_data.mask_image_url is None

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
            GptImage15EditInput(
                prompt="Test",
                image_urls=[image_artifact],
                output_format="invalid",  # type: ignore[arg-type]
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
            GptImage15EditInput(
                prompt="Test",
                image_urls=[image_artifact],
                quality="invalid",  # type: ignore[arg-type]
            )

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
            GptImage15EditInput(
                prompt="Test",
                image_urls=[image_artifact],
                image_size="512x512",  # type: ignore[arg-type]
            )

    def test_invalid_background(self):
        """Test validation fails for invalid background."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        with pytest.raises(ValidationError):
            GptImage15EditInput(
                prompt="Test",
                image_urls=[image_artifact],
                background="invalid",  # type: ignore[arg-type]
            )

    def test_empty_image_urls(self):
        """Test validation fails for empty image_urls."""
        with pytest.raises(ValidationError):
            GptImage15EditInput(
                prompt="Test",
                image_urls=[],  # Empty list should fail min_length=1
            )

    def test_prompt_too_short(self):
        """Test validation fails for prompt less than 2 characters."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        with pytest.raises(ValidationError):
            GptImage15EditInput(
                prompt="X",  # Too short - min_length is 2
                image_urls=[image_artifact],
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
            GptImage15EditInput(
                prompt="Test",
                image_urls=[image_artifact],
                num_images=0,
            )

        # Test above maximum (4)
        with pytest.raises(ValidationError):
            GptImage15EditInput(
                prompt="Test",
                image_urls=[image_artifact],
                num_images=5,
            )

    def test_with_mask_image(self):
        """Test input with mask image."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )
        mask_artifact = ImageArtifact(
            generation_id="gen_mask",
            storage_url="https://example.com/mask.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = GptImage15EditInput(
            prompt="Change the background",
            image_urls=[image_artifact],
            mask_image_url=mask_artifact,
        )

        assert input_data.mask_image_url is not None
        assert input_data.mask_image_url.generation_id == "gen_mask"

    def test_quality_options(self):
        """Test all valid quality options."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        valid_qualities = ["low", "medium", "high"]

        for quality in valid_qualities:
            input_data = GptImage15EditInput(
                prompt="Test",
                image_urls=[image_artifact],
                quality=quality,  # type: ignore[arg-type]
            )
            assert input_data.quality == quality

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
            input_data = GptImage15EditInput(
                prompt="Test",
                image_urls=[image_artifact],
                image_size=size,  # type: ignore[arg-type]
            )
            assert input_data.image_size == size


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalGptImage15EditGenerator:
    """Tests for FalGptImage15EditGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalGptImage15EditGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-gpt-image-15-edit"
        assert self.generator.artifact_type == "image"
        assert "GPT-Image-1.5" in self.generator.description
        assert "Edit" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == GptImage15EditInput

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

            input_data = GptImage15EditInput(
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

        input_data = GptImage15EditInput(
            prompt="Make the sky more dramatic",
            image_urls=[input_image],
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
                "fal-ai/gpt-image-1.5/edit",
                arguments={
                    "prompt": "Make the sky more dramatic",
                    "image_urls": [fake_uploaded_url],
                    "num_images": 1,
                    "image_size": "auto",
                    "quality": "high",
                    "input_fidelity": "high",
                    "output_format": "jpeg",
                    "background": "auto",
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

        input_data = GptImage15EditInput(
            prompt="Enhance the colors",
            image_urls=[input_image_1, input_image_2],
            num_images=2,
            output_format="png",
            quality="medium",
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

            # Verify API call included quality and uploaded URLs
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["quality"] == "medium"
            assert call_args[1]["arguments"]["image_urls"] == fake_uploaded_urls

    @pytest.mark.asyncio
    async def test_generate_with_mask_image(self):
        """Test generation with mask image."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=1024,
        )
        mask_image = ImageArtifact(
            generation_id="gen_mask",
            storage_url="https://example.com/mask.png",
            format="png",
            width=1024,
            height=1024,
        )

        input_data = GptImage15EditInput(
            prompt="Change the background to a beach",
            image_urls=[input_image],
            mask_image_url=mask_image,
            num_images=1,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.png"
        fake_uploaded_image_url = "https://fal.media/files/uploaded-input.png"
        fake_uploaded_mask_url = "https://fal.media/files/uploaded-mask.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-mask"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [{"url": fake_output_url, "width": 1024, "height": 1024}],
                }
            )

            # Track which file is being uploaded
            upload_call_count = 0

            async def mock_upload(file_path):
                nonlocal upload_call_count
                upload_call_count += 1
                if "mask" in file_path:
                    return fake_uploaded_mask_url
                return fake_uploaded_image_url

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = ImageArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1024,
                height=1024,
                format="png",
            )

            resolve_count = 0

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    nonlocal resolve_count
                    resolve_count += 1
                    if artifact.generation_id == "gen_mask":
                        return "/tmp/fake_mask.png"
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

            # Verify API call included mask_image_url
            call_args = mock_fal_client.submit_async.call_args
            assert "mask_image_url" in call_args[1]["arguments"]
            assert call_args[1]["arguments"]["mask_image_url"] == fake_uploaded_mask_url

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

        input_data = GptImage15EditInput(
            prompt="test prompt",
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
    async def test_estimate_cost_low_quality(self):
        """Test cost estimation for low quality."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = GptImage15EditInput(
            prompt="Test prompt",
            image_urls=[input_image],
            num_images=1,
            quality="low",
        )

        cost = await self.generator.estimate_cost(input_data)

        # Low quality cost (0.011 * 1)
        assert cost == 0.011
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_medium_quality(self):
        """Test cost estimation for medium quality."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = GptImage15EditInput(
            prompt="Test prompt",
            image_urls=[input_image],
            num_images=1,
            quality="medium",
        )

        cost = await self.generator.estimate_cost(input_data)

        # Medium quality cost (0.045 * 1)
        assert cost == 0.045
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_high_quality(self):
        """Test cost estimation for high quality (default)."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = GptImage15EditInput(
            prompt="Test prompt",
            image_urls=[input_image],
            num_images=1,
            quality="high",
        )

        cost = await self.generator.estimate_cost(input_data)

        # High quality cost (0.177 * 1)
        assert cost == 0.177
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

        input_data = GptImage15EditInput(
            prompt="Test prompt",
            image_urls=[input_image],
            num_images=4,
            quality="high",
        )

        cost = await self.generator.estimate_cost(input_data)

        # High quality cost (0.177 * 4)
        assert cost == 0.708
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = GptImage15EditInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "image_urls" in schema["properties"]
        assert "mask_image_url" in schema["properties"]
        assert "num_images" in schema["properties"]
        assert "output_format" in schema["properties"]
        assert "quality" in schema["properties"]
        assert "image_size" in schema["properties"]
        assert "background" in schema["properties"]
        assert "input_fidelity" in schema["properties"]

        # Check that image_urls is an array
        image_urls_prop = schema["properties"]["image_urls"]
        assert image_urls_prop["type"] == "array"
        assert "minItems" in image_urls_prop

        # Check that num_images has constraints
        num_images_prop = schema["properties"]["num_images"]
        assert num_images_prop["minimum"] == 1
        assert num_images_prop["maximum"] == 4
        assert num_images_prop["default"] == 1

        # Check that prompt has min_length constraint
        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop["minLength"] == 2
