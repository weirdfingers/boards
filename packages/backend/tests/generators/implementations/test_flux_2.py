"""
Tests for FalFlux2Generator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.flux_2 import (
    FalFlux2Generator,
    Flux2Input,
)


class TestFlux2Input:
    """Tests for Flux2Input schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = Flux2Input(
            prompt="A serene mountain landscape",
            image_size="landscape_16_9",
            num_images=2,
            acceleration="high",
            output_format="png",
        )

        assert input_data.prompt == "A serene mountain landscape"
        assert input_data.image_size == "landscape_16_9"
        assert input_data.num_images == 2
        assert input_data.acceleration == "high"
        assert input_data.output_format == "png"

    def test_input_defaults(self):
        """Test default values."""
        input_data = Flux2Input(prompt="Test prompt")

        assert input_data.num_images == 1
        assert input_data.image_size == "landscape_4_3"
        assert input_data.acceleration == "regular"
        assert input_data.output_format == "png"
        assert input_data.enable_prompt_expansion is False
        assert input_data.enable_safety_checker is True
        assert input_data.guidance_scale == 2.5
        assert input_data.num_inference_steps == 28
        assert input_data.seed is None
        assert input_data.sync_mode is True

    def test_invalid_image_size(self):
        """Test validation fails for invalid image size."""
        with pytest.raises(ValidationError):
            Flux2Input(
                prompt="Test",
                image_size="invalid",  # type: ignore[arg-type]
            )

    def test_invalid_acceleration(self):
        """Test validation fails for invalid acceleration."""
        with pytest.raises(ValidationError):
            Flux2Input(
                prompt="Test",
                acceleration="turbo",  # type: ignore[arg-type]
            )

    def test_invalid_output_format(self):
        """Test validation fails for invalid output format."""
        with pytest.raises(ValidationError):
            Flux2Input(
                prompt="Test",
                output_format="gif",  # type: ignore[arg-type]
            )

    def test_num_images_validation(self):
        """Test validation for num_images constraints."""
        # Test below minimum
        with pytest.raises(ValidationError):
            Flux2Input(prompt="Test", num_images=0)

        # Test above maximum
        with pytest.raises(ValidationError):
            Flux2Input(prompt="Test", num_images=5)

        # Test valid range (1-4)
        for num in [1, 2, 3, 4]:
            input_data = Flux2Input(prompt="Test", num_images=num)
            assert input_data.num_images == num

    def test_guidance_scale_validation(self):
        """Test validation for guidance_scale constraints."""
        # Test below minimum
        with pytest.raises(ValidationError):
            Flux2Input(prompt="Test", guidance_scale=-1.0)

        # Test above maximum
        with pytest.raises(ValidationError):
            Flux2Input(prompt="Test", guidance_scale=21.0)

        # Test valid range
        for scale in [0.0, 2.5, 10.0, 20.0]:
            input_data = Flux2Input(prompt="Test", guidance_scale=scale)
            assert input_data.guidance_scale == scale

    def test_num_inference_steps_validation(self):
        """Test validation for num_inference_steps constraints."""
        # Test below minimum
        with pytest.raises(ValidationError):
            Flux2Input(prompt="Test", num_inference_steps=3)

        # Test above maximum
        with pytest.raises(ValidationError):
            Flux2Input(prompt="Test", num_inference_steps=51)

        # Test valid range
        for steps in [4, 28, 50]:
            input_data = Flux2Input(prompt="Test", num_inference_steps=steps)
            assert input_data.num_inference_steps == steps

    def test_image_size_options(self):
        """Test all valid image size options."""
        valid_sizes = [
            "square_hd",
            "square",
            "portrait_4_3",
            "portrait_16_9",
            "landscape_4_3",
            "landscape_16_9",
        ]

        for size in valid_sizes:
            input_data = Flux2Input(prompt="Test", image_size=size)  # type: ignore[arg-type]
            assert input_data.image_size == size

    def test_acceleration_options(self):
        """Test all valid acceleration options."""
        valid_accelerations = ["none", "regular", "high"]

        for accel in valid_accelerations:
            input_data = Flux2Input(prompt="Test", acceleration=accel)  # type: ignore[arg-type]
            assert input_data.acceleration == accel


class TestFlux2Generator:
    """Tests for FalFlux2Generator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalFlux2Generator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-flux-2"
        assert self.generator.artifact_type == "image"
        assert "FLUX.2" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == Flux2Input

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = Flux2Input(prompt="Test prompt")

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

            with pytest.raises(ValueError, match="Missing FAL_KEY"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_generate_successful_single_image(self):
        """Test successful generation of a single image."""
        input_data = Flux2Input(
            prompt="A beautiful sunset over the ocean",
            image_size="landscape_16_9",
            num_images=1,
            output_format="png",
        )

        fake_image_url = "https://fal.media/files/fake-image-url.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-token"}):
            # Create mock fal_client module
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "fal-request-123"

            # Create async generator for iter_events
            async def mock_iter_events(with_logs=True):
                # Yield some fake events
                for i in range(5):
                    event = MagicMock()
                    event.logs = [f"Processing step {i}"]
                    yield event

            mock_handler.iter_events = mock_iter_events

            # Mock get() to return the final result
            async def mock_get():
                return {
                    "images": [
                        {
                            "url": fake_image_url,
                            "width": 1280,
                            "height": 720,
                            "content_type": "image/png",
                        }
                    ],
                    "seed": 12345,
                    "prompt": "A beautiful sunset over the ocean",
                }

            mock_handler.get = mock_get

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]

            sys.modules["fal_client"] = mock_fal_client

            # Mock storage result
            mock_artifact = ImageArtifact(
                generation_id="test_gen",
                storage_url=fake_image_url,
                width=1280,
                height=720,
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
            mock_fal_client.submit_async.assert_called_once()
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[0][0] == "fal-ai/flux-2"
            assert call_args[1]["arguments"]["prompt"] == "A beautiful sunset over the ocean"
            assert call_args[1]["arguments"]["image_size"] == "landscape_16_9"
            assert call_args[1]["arguments"]["num_images"] == 1

    @pytest.mark.asyncio
    async def test_generate_successful_batch(self):
        """Test successful generation of multiple images in a batch."""
        input_data = Flux2Input(
            prompt="A forest in autumn",
            num_images=3,
            output_format="png",
        )

        fake_image_urls = [
            "https://fal.media/files/image1.png",
            "https://fal.media/files/image2.png",
            "https://fal.media/files/image3.png",
        ]

        with patch.dict(os.environ, {"FAL_KEY": "fake-token"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "fal-request-456"

            # Create async generator for iter_events (empty for simplicity)
            async def mock_iter_events(with_logs=True):
                if False:
                    yield

            mock_handler.iter_events = mock_iter_events

            # Mock get() to return the final result with 3 images
            async def mock_get():
                return {
                    "images": [
                        {"url": url, "width": 1024, "height": 768, "content_type": "image/png"}
                        for url in fake_image_urls
                    ],
                    "seed": 67890,
                }

            mock_handler.get = mock_get

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]

            sys.modules["fal_client"] = mock_fal_client

            # Mock storage results
            stored_artifacts = []

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return ""

                async def store_image_result(self, **kwargs):
                    artifact = ImageArtifact(
                        generation_id="test_gen",
                        storage_url=kwargs["storage_url"],
                        width=kwargs["width"],
                        height=kwargs["height"],
                        format=kwargs["format"],
                    )
                    stored_artifacts.append(artifact)
                    return artifact

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
            assert len(stored_artifacts) == 3

            # Verify each artifact was stored with the correct URL
            for i, url in enumerate(fake_image_urls):
                assert stored_artifacts[i].storage_url == url

    @pytest.mark.asyncio
    async def test_generate_with_custom_parameters(self):
        """Test generation with custom acceleration and inference parameters."""
        input_data = Flux2Input(
            prompt="Detailed artwork",
            acceleration="none",
            guidance_scale=15.0,
            num_inference_steps=50,
            enable_prompt_expansion=True,
            seed=42,
        )

        fake_image_url = "https://fal.media/files/custom-image.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-token"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "fal-request-custom"

            async def mock_iter_events(with_logs=True):
                if False:
                    yield

            mock_handler.iter_events = mock_iter_events

            async def mock_get():
                return {
                    "images": [{"url": fake_image_url, "width": 1024, "height": 768}],
                    "seed": 42,
                }

            mock_handler.get = mock_get

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
                    return ImageArtifact(
                        generation_id="test_gen",
                        storage_url=kwargs["storage_url"],
                        width=kwargs["width"],
                        height=kwargs["height"],
                        format=kwargs["format"],
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

            # Verify API was called with custom parameters
            call_args = mock_fal_client.submit_async.call_args
            args = call_args[1]["arguments"]
            assert args["acceleration"] == "none"
            assert args["guidance_scale"] == 15.0
            assert args["num_inference_steps"] == 50
            assert args["enable_prompt_expansion"] is True
            assert args["seed"] == 42

    @pytest.mark.asyncio
    async def test_generate_empty_response(self):
        """Test handling of empty response from API."""
        input_data = Flux2Input(prompt="Test prompt")

        with patch.dict(os.environ, {"FAL_KEY": "fake-token"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "fal-request-empty"

            async def mock_iter_events(with_logs=True):
                if False:
                    yield

            mock_handler.iter_events = mock_iter_events

            async def mock_get():
                return {"images": []}

            mock_handler.get = mock_get

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

            with pytest.raises(ValueError, match="No images returned"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_estimate_cost_single_image(self):
        """Test cost estimation for a single image."""
        input_data = Flux2Input(prompt="Test prompt", num_images=1)

        cost = await self.generator.estimate_cost(input_data)

        assert cost == 0.055  # Expected cost per image
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_batch(self):
        """Test cost estimation for batch generation."""
        input_data = Flux2Input(prompt="Test prompt", num_images=4)

        cost = await self.generator.estimate_cost(input_data)

        assert cost == 0.22  # 4 images * $0.055
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = Flux2Input.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "image_size" in schema["properties"]
        assert "num_images" in schema["properties"]
        assert "acceleration" in schema["properties"]
        assert "guidance_scale" in schema["properties"]
        assert "num_inference_steps" in schema["properties"]

        # Check that image_size has enum values
        image_size_prop = schema["properties"]["image_size"]
        assert "enum" in image_size_prop

        # Check that num_images has constraints
        num_images_prop = schema["properties"]["num_images"]
        assert num_images_prop["minimum"] == 1
        assert num_images_prop["maximum"] == 4
        assert num_images_prop["default"] == 1

        # Check that guidance_scale has constraints
        guidance_prop = schema["properties"]["guidance_scale"]
        assert guidance_prop["minimum"] == 0.0
        assert guidance_prop["maximum"] == 20.0
        assert guidance_prop["default"] == 2.5

        # Check that num_inference_steps has constraints
        steps_prop = schema["properties"]["num_inference_steps"]
        assert steps_prop["minimum"] == 4
        assert steps_prop["maximum"] == 50
        assert steps_prop["default"] == 28
