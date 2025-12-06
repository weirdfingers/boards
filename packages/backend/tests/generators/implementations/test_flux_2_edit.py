"""
Tests for FalFlux2EditGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.flux_2_edit import (
    FalFlux2EditGenerator,
    Flux2EditImageSize,
    Flux2EditInput,
)


class TestFlux2EditInput:
    """Tests for Flux2EditInput schema."""

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

        input_data = Flux2EditInput(
            prompt="Change the background to a sunset",
            image_sources=[image_artifact_1, image_artifact_2],
            num_images=2,
            output_format="jpeg",
        )

        assert input_data.prompt == "Change the background to a sunset"
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

        input_data = Flux2EditInput(
            prompt="Test prompt",
            image_sources=[image_artifact],
        )

        assert input_data.num_images == 1
        assert input_data.output_format == "png"
        assert input_data.acceleration == "regular"
        assert input_data.num_inference_steps == 28
        assert input_data.guidance_scale == 2.5
        assert input_data.enable_prompt_expansion is False
        assert input_data.enable_safety_checker is True
        assert input_data.sync_mode is False
        assert input_data.image_size is None
        assert input_data.seed is None

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
            Flux2EditInput(
                prompt="Test",
                image_sources=[image_artifact],
                output_format="invalid",  # type: ignore[arg-type]
            )

    def test_invalid_acceleration(self):
        """Test validation fails for invalid acceleration mode."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        with pytest.raises(ValidationError):
            Flux2EditInput(
                prompt="Test",
                image_sources=[image_artifact],
                acceleration="turbo",  # type: ignore[arg-type]
            )

    def test_empty_image_sources(self):
        """Test validation fails for empty image_sources."""
        with pytest.raises(ValidationError):
            Flux2EditInput(
                prompt="Test",
                image_sources=[],  # Empty list should fail min_length=1
            )

    def test_too_many_image_sources(self):
        """Test validation fails for more than 3 image sources."""
        artifacts = [
            ImageArtifact(
                generation_id=f"gen{i}",
                storage_url=f"https://example.com/image{i}.png",
                format="png",
                width=1024,
                height=768,
            )
            for i in range(4)  # 4 images - exceeds max_length=3
        ]

        with pytest.raises(ValidationError):
            Flux2EditInput(
                prompt="Test",
                image_sources=artifacts,
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
            Flux2EditInput(
                prompt="Test",
                image_sources=[image_artifact],
                num_images=0,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            Flux2EditInput(
                prompt="Test",
                image_sources=[image_artifact],
                num_images=5,
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
            Flux2EditInput(
                prompt="Test",
                image_sources=[image_artifact],
                num_inference_steps=3,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            Flux2EditInput(
                prompt="Test",
                image_sources=[image_artifact],
                num_inference_steps=51,
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
            Flux2EditInput(
                prompt="Test",
                image_sources=[image_artifact],
                guidance_scale=-1.0,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            Flux2EditInput(
                prompt="Test",
                image_sources=[image_artifact],
                guidance_scale=21.0,
            )

    def test_image_size_predefined(self):
        """Test predefined image size options."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        valid_sizes = ["square_hd", "portrait_4_3", "landscape_16_9"]

        for size in valid_sizes:
            input_data = Flux2EditInput(
                prompt="Test",
                image_sources=[image_artifact],
                image_size=size,  # type: ignore[arg-type]
            )
            assert input_data.image_size == size

    def test_image_size_custom(self):
        """Test custom image size configuration."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        custom_size = Flux2EditImageSize(width=1024, height=768)
        input_data = Flux2EditInput(
            prompt="Test",
            image_sources=[image_artifact],
            image_size=custom_size,
        )
        assert isinstance(input_data.image_size, Flux2EditImageSize)
        assert input_data.image_size.width == 1024
        assert input_data.image_size.height == 768

    def test_custom_image_size_validation(self):
        """Test custom image size validation constraints."""
        # Test width below minimum
        with pytest.raises(ValidationError):
            Flux2EditImageSize(width=256, height=1024)

        # Test width above maximum
        with pytest.raises(ValidationError):
            Flux2EditImageSize(width=4096, height=1024)

        # Test height below minimum
        with pytest.raises(ValidationError):
            Flux2EditImageSize(width=1024, height=256)

        # Test height above maximum
        with pytest.raises(ValidationError):
            Flux2EditImageSize(width=1024, height=4096)

    def test_acceleration_options(self):
        """Test all valid acceleration options."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        valid_options = ["none", "regular", "high"]

        for option in valid_options:
            input_data = Flux2EditInput(
                prompt="Test",
                image_sources=[image_artifact],
                acceleration=option,  # type: ignore[arg-type]
            )
            assert input_data.acceleration == option


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalFlux2EditGenerator:
    """Tests for FalFlux2EditGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalFlux2EditGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-flux-2-edit"
        assert self.generator.artifact_type == "image"
        assert "FLUX" in self.generator.description
        assert "Edit" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == Flux2EditInput

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

            input_data = Flux2EditInput(
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

        input_data = Flux2EditInput(
            prompt="Change his clothes to casual suit and tie",
            image_sources=[input_image],
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
                    "seed": 12345,
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
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/flux-2/edit",
                arguments={
                    "prompt": "Change his clothes to casual suit and tie",
                    "image_urls": [fake_uploaded_url],
                    "num_images": 1,
                    "acceleration": "regular",
                    "num_inference_steps": 28,
                    "output_format": "jpeg",
                    "guidance_scale": 2.5,
                    "enable_prompt_expansion": False,
                    "enable_safety_checker": True,
                    "sync_mode": False,
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

        input_data = Flux2EditInput(
            prompt="Add a dramatic sky",
            image_sources=[input_image_1, input_image_2],
            num_images=2,
            output_format="png",
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
                    "seed": 54321,
                    "has_nsfw_concepts": [False, False],
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

            # Verify API call included image_size and uploaded URLs
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["image_size"] == "landscape_16_9"
            assert call_args[1]["arguments"]["image_urls"] == fake_uploaded_urls

    @pytest.mark.asyncio
    async def test_generate_with_custom_image_size(self):
        """Test generation with custom image size dimensions."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        custom_size = Flux2EditImageSize(width=1024, height=768)
        input_data = Flux2EditInput(
            prompt="Enhance details",
            image_sources=[input_image],
            num_images=1,
            output_format="png",
            image_size=custom_size,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.png"
        fake_uploaded_url = "https://fal.media/files/uploaded-input.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [{"url": fake_output_url, "width": 1024, "height": 768}],
                    "seed": 99999,
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

            # Verify result
            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1

            # Verify API call included custom image_size as object
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["image_size"] == {"width": 1024, "height": 768}

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

        input_data = Flux2EditInput(
            prompt="test",
            image_sources=[input_image],
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-999"

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

        input_data = Flux2EditInput(
            prompt="Test prompt",
            image_sources=[input_image],
            num_images=1,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Per-image cost (0.06 * 1)
        assert cost == 0.06
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

        input_data = Flux2EditInput(
            prompt="Test prompt",
            image_sources=[input_image],
            num_images=4,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Per-image cost (0.06 * 4)
        assert cost == 0.24
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = Flux2EditInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "image_sources" in schema["properties"]
        assert "num_images" in schema["properties"]
        assert "output_format" in schema["properties"]
        assert "acceleration" in schema["properties"]
        assert "num_inference_steps" in schema["properties"]
        assert "guidance_scale" in schema["properties"]
        assert "image_size" in schema["properties"]

        # Check that image_sources is an array with constraints
        image_sources_prop = schema["properties"]["image_sources"]
        assert image_sources_prop["type"] == "array"
        assert "minItems" in image_sources_prop
        assert "maxItems" in image_sources_prop
        assert image_sources_prop["minItems"] == 1
        assert image_sources_prop["maxItems"] == 3

        # Check that num_images has constraints
        num_images_prop = schema["properties"]["num_images"]
        assert num_images_prop["minimum"] == 1
        assert num_images_prop["maximum"] == 4
        assert num_images_prop["default"] == 1

        # Check that num_inference_steps has constraints
        inference_steps_prop = schema["properties"]["num_inference_steps"]
        assert inference_steps_prop["minimum"] == 4
        assert inference_steps_prop["maximum"] == 50
        assert inference_steps_prop["default"] == 28

        # Check that guidance_scale has constraints
        guidance_prop = schema["properties"]["guidance_scale"]
        assert guidance_prop["minimum"] == 0.0
        assert guidance_prop["maximum"] == 20.0
        assert guidance_prop["default"] == 2.5
