"""
Tests for FalImagen4PreviewGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.imagen4_preview import (
    FalImagen4PreviewGenerator,
    Imagen4PreviewInput,
)


class TestImagen4PreviewInput:
    """Tests for Imagen4PreviewInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = Imagen4PreviewInput(
            prompt="A serene mountain landscape",
            aspect_ratio="16:9",
            resolution="2K",
            num_images=2,
            negative_prompt="blurry, low quality",
        )

        assert input_data.prompt == "A serene mountain landscape"
        assert input_data.aspect_ratio == "16:9"
        assert input_data.resolution == "2K"
        assert input_data.num_images == 2
        assert input_data.negative_prompt == "blurry, low quality"

    def test_input_defaults(self):
        """Test default values."""
        input_data = Imagen4PreviewInput(prompt="Test prompt")

        assert input_data.aspect_ratio == "1:1"
        assert input_data.resolution == "1K"
        assert input_data.num_images == 1
        assert input_data.negative_prompt == ""
        assert input_data.seed is None

    def test_invalid_aspect_ratio(self):
        """Test validation fails for invalid aspect ratio."""
        with pytest.raises(ValidationError):
            Imagen4PreviewInput(
                prompt="Test",
                aspect_ratio="invalid",  # type: ignore[arg-type]
            )

    def test_invalid_resolution(self):
        """Test validation fails for invalid resolution."""
        with pytest.raises(ValidationError):
            Imagen4PreviewInput(
                prompt="Test",
                resolution="invalid",  # type: ignore[arg-type]
            )

    def test_num_images_validation(self):
        """Test validation for num_images constraints."""
        # Test below minimum
        with pytest.raises(ValidationError):
            Imagen4PreviewInput(prompt="Test", num_images=0)

        # Test above maximum
        with pytest.raises(ValidationError):
            Imagen4PreviewInput(prompt="Test", num_images=5)

        # Test valid range (1-4)
        for num in [1, 2, 3, 4]:
            input_data = Imagen4PreviewInput(prompt="Test", num_images=num)
            assert input_data.num_images == num

    def test_aspect_ratio_options(self):
        """Test all valid aspect ratio options."""
        valid_ratios = ["1:1", "16:9", "9:16", "3:4", "4:3"]

        for ratio in valid_ratios:
            input_data = Imagen4PreviewInput(prompt="Test", aspect_ratio=ratio)  # type: ignore[arg-type]
            assert input_data.aspect_ratio == ratio

    def test_resolution_options(self):
        """Test all valid resolution options."""
        valid_resolutions = ["1K", "2K"]

        for resolution in valid_resolutions:
            input_data = Imagen4PreviewInput(prompt="Test", resolution=resolution)  # type: ignore[arg-type]
            assert input_data.resolution == resolution


class TestImagen4PreviewGenerator:
    """Tests for FalImagen4PreviewGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalImagen4PreviewGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-imagen4-preview"
        assert self.generator.artifact_type == "image"
        assert "Imagen 4" in self.generator.description
        assert "Google" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == Imagen4PreviewInput

    def test_calculate_dimensions_1k(self):
        """Test dimension calculation for 1K resolution."""
        # Test all aspect ratios with 1K
        assert self.generator._calculate_dimensions("1:1", "1K") == (1024, 1024)
        assert self.generator._calculate_dimensions("16:9", "1K") == (1024, 576)
        assert self.generator._calculate_dimensions("9:16", "1K") == (576, 1024)
        assert self.generator._calculate_dimensions("4:3", "1K") == (1024, 768)
        assert self.generator._calculate_dimensions("3:4", "1K") == (768, 1024)

    def test_calculate_dimensions_2k(self):
        """Test dimension calculation for 2K resolution."""
        # Test all aspect ratios with 2K
        assert self.generator._calculate_dimensions("1:1", "2K") == (2048, 2048)
        assert self.generator._calculate_dimensions("16:9", "2K") == (2048, 1152)
        assert self.generator._calculate_dimensions("9:16", "2K") == (1152, 2048)
        assert self.generator._calculate_dimensions("4:3", "2K") == (2048, 1536)
        assert self.generator._calculate_dimensions("3:4", "2K") == (1536, 2048)

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = Imagen4PreviewInput(prompt="Test prompt")

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
        input_data = Imagen4PreviewInput(
            prompt="A beautiful sunset over the ocean",
            aspect_ratio="16:9",
            resolution="1K",
            num_images=1,
        )

        fake_image_url = "https://v3.fal.media/files/rabbit/imagen4-output.png"

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
                            "content_type": "image/png",
                            "file_name": "output.png",
                            "file_size": 1024000,
                        }
                    ],
                    "seed": 12345,
                }

            mock_handler.get = mock_get

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]

            sys.modules["fal_client"] = mock_fal_client

            # Mock storage result
            mock_artifact = ImageArtifact(
                generation_id="test_gen",
                storage_url=fake_image_url,
                width=1024,
                height=576,
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
            assert call_args[0][0] == "fal-ai/imagen4/preview"
            assert call_args[1]["arguments"]["prompt"] == "A beautiful sunset over the ocean"
            assert call_args[1]["arguments"]["aspect_ratio"] == "16:9"
            assert call_args[1]["arguments"]["resolution"] == "1K"
            assert call_args[1]["arguments"]["num_images"] == 1

    @pytest.mark.asyncio
    async def test_generate_successful_batch(self):
        """Test successful generation of multiple images in a batch."""
        input_data = Imagen4PreviewInput(
            prompt="A forest in autumn",
            num_images=3,
            aspect_ratio="1:1",
            resolution="1K",
        )

        fake_image_urls = [
            "https://v3.fal.media/files/image1.png",
            "https://v3.fal.media/files/image2.png",
            "https://v3.fal.media/files/image3.png",
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
                        {
                            "url": url,
                            "content_type": "image/png",
                            "file_name": f"output{i}.png",
                            "file_size": 1024000,
                        }
                        for i, url in enumerate(fake_image_urls)
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
                assert stored_artifacts[i].width == 1024
                assert stored_artifacts[i].height == 1024

    @pytest.mark.asyncio
    async def test_generate_with_jpeg_content_type(self):
        """Test format detection from JPEG content type."""
        input_data = Imagen4PreviewInput(prompt="Test")

        fake_image_url = "https://v3.fal.media/files/output.jpg"

        with patch.dict(os.environ, {"FAL_KEY": "fake-token"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "fal-request-789"

            async def mock_iter_events(with_logs=True):
                if False:
                    yield

            mock_handler.iter_events = mock_iter_events

            async def mock_get():
                return {
                    "images": [
                        {
                            "url": fake_image_url,
                            "content_type": "image/jpeg",  # JPEG content type
                            "file_name": "output.jpg",
                            "file_size": 512000,
                        }
                    ],
                }

            mock_handler.get = mock_get

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            stored_format = None

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return ""

                async def store_image_result(self, **kwargs):
                    nonlocal stored_format
                    stored_format = kwargs["format"]
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

            # Verify JPEG format was detected
            assert stored_format == "jpeg"

    @pytest.mark.asyncio
    async def test_estimate_cost_single_image(self):
        """Test cost estimation for a single image."""
        input_data = Imagen4PreviewInput(prompt="Test prompt", num_images=1)

        cost = await self.generator.estimate_cost(input_data)

        assert cost == 0.04  # Expected cost per image
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_batch(self):
        """Test cost estimation for batch generation."""
        input_data = Imagen4PreviewInput(prompt="Test prompt", num_images=4)

        cost = await self.generator.estimate_cost(input_data)

        assert cost == 0.16  # 4 images * $0.04
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = Imagen4PreviewInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "aspect_ratio" in schema["properties"]
        assert "resolution" in schema["properties"]
        assert "num_images" in schema["properties"]
        assert "negative_prompt" in schema["properties"]
        assert "seed" in schema["properties"]

        # Check that aspect_ratio has enum values
        aspect_ratio_prop = schema["properties"]["aspect_ratio"]
        assert "enum" in aspect_ratio_prop

        # Check that resolution has enum values
        resolution_prop = schema["properties"]["resolution"]
        assert "enum" in resolution_prop

        # Check that num_images has constraints
        num_images_prop = schema["properties"]["num_images"]
        assert num_images_prop["minimum"] == 1
        assert num_images_prop["maximum"] == 4
        assert num_images_prop["default"] == 1
