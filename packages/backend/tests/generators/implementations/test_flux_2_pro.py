"""
Tests for FalFlux2ProGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.flux_2_pro import (
    FalFlux2ProGenerator,
    Flux2ProInput,
)


class TestFlux2ProInput:
    """Tests for Flux2ProInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = Flux2ProInput(
            prompt="An intense close-up of a knight's visor reflecting battle",
            image_size="landscape_16_9",
            safety_tolerance="3",
            output_format="png",
        )

        assert input_data.prompt == "An intense close-up of a knight's visor reflecting battle"
        assert input_data.image_size == "landscape_16_9"
        assert input_data.safety_tolerance == "3"
        assert input_data.output_format == "png"

    def test_input_defaults(self):
        """Test default values."""
        input_data = Flux2ProInput(prompt="Test prompt")

        assert input_data.image_size == "landscape_4_3"
        assert input_data.output_format == "jpeg"
        assert input_data.safety_tolerance == "2"
        assert input_data.enable_safety_checker is True
        assert input_data.sync_mode is True
        assert input_data.seed is None

    def test_invalid_image_size(self):
        """Test validation fails for invalid image size."""
        with pytest.raises(ValidationError):
            Flux2ProInput(
                prompt="Test",
                image_size="invalid",  # type: ignore[arg-type]
            )

    def test_invalid_output_format(self):
        """Test validation fails for invalid output format."""
        with pytest.raises(ValidationError):
            Flux2ProInput(
                prompt="Test",
                output_format="invalid",  # type: ignore[arg-type]
            )

    def test_invalid_safety_tolerance(self):
        """Test validation fails for invalid safety tolerance."""
        with pytest.raises(ValidationError):
            Flux2ProInput(
                prompt="Test",
                safety_tolerance="0",  # type: ignore[arg-type]
            )

        with pytest.raises(ValidationError):
            Flux2ProInput(
                prompt="Test",
                safety_tolerance="6",  # type: ignore[arg-type]
            )

    def test_safety_tolerance_options(self):
        """Test all valid safety tolerance options."""
        valid_tolerances = ["1", "2", "3", "4", "5"]

        for tolerance in valid_tolerances:
            input_data = Flux2ProInput(prompt="Test", safety_tolerance=tolerance)  # type: ignore[arg-type]
            assert input_data.safety_tolerance == tolerance

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
            input_data = Flux2ProInput(prompt="Test", image_size=size)  # type: ignore[arg-type]
            assert input_data.image_size == size


class TestFlux2ProGenerator:
    """Tests for FalFlux2ProGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalFlux2ProGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-flux-2-pro"
        assert self.generator.artifact_type == "image"
        assert "FLUX.2 [pro]" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == Flux2ProInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = Flux2ProInput(prompt="Test prompt")

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
        input_data = Flux2ProInput(
            prompt="A beautiful sunset over the ocean",
            image_size="landscape_16_9",
            output_format="jpeg",
        )

        fake_image_url = "https://fal.media/files/fake-image-url.jpeg"

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
                            "width": 1920,
                            "height": 1080,
                            "content_type": "image/jpeg",
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
                width=1920,
                height=1080,
                format="jpeg",
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
            assert call_args[0][0] == "fal-ai/flux-2-pro"
            assert call_args[1]["arguments"]["prompt"] == "A beautiful sunset over the ocean"
            assert call_args[1]["arguments"]["image_size"] == "landscape_16_9"

    @pytest.mark.asyncio
    async def test_generate_with_seed(self):
        """Test generation with a specific seed."""
        input_data = Flux2ProInput(
            prompt="A forest in autumn",
            image_size="square",
            seed=42,
        )

        fake_image_url = "https://fal.media/files/seeded-image.jpeg"

        with patch.dict(os.environ, {"FAL_KEY": "fake-token"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "fal-request-456"

            # Create async generator for iter_events (empty for simplicity)
            async def mock_iter_events(with_logs=True):
                if False:
                    yield

            mock_handler.iter_events = mock_iter_events

            async def mock_get():
                return {
                    "images": [
                        {
                            "url": fake_image_url,
                            "width": 1024,
                            "height": 1024,
                            "content_type": "image/jpeg",
                        }
                    ],
                    "seed": 42,
                }

            mock_handler.get = mock_get

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]

            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = ImageArtifact(
                generation_id="test_gen",
                storage_url=fake_image_url,
                width=1024,
                height=1024,
                format="jpeg",
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

            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1

            # Verify seed was passed to API
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["seed"] == 42

    @pytest.mark.asyncio
    async def test_generate_empty_response(self):
        """Test handling of empty response from API."""
        input_data = Flux2ProInput(prompt="Test")

        with patch.dict(os.environ, {"FAL_KEY": "fake-token"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "fal-request-789"

            async def mock_iter_events(with_logs=True):
                if False:
                    yield

            mock_handler.iter_events = mock_iter_events

            async def mock_get():
                return {"images": [], "seed": 0}

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
    async def test_estimate_cost_standard_size(self):
        """Test cost estimation for standard size (1 megapixel)."""
        input_data = Flux2ProInput(prompt="Test prompt", image_size="square")

        cost = await self.generator.estimate_cost(input_data)

        # 1 megapixel = $0.03
        assert cost == 0.03
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_hd_square(self):
        """Test cost estimation for HD square (~1.5 megapixels)."""
        input_data = Flux2ProInput(prompt="Test prompt", image_size="square_hd")

        cost = await self.generator.estimate_cost(input_data)

        # 1.5 megapixels = $0.03 + 0.5 * $0.015 = $0.0375
        assert cost == pytest.approx(0.0375)
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_landscape(self):
        """Test cost estimation for landscape size."""
        input_data = Flux2ProInput(prompt="Test prompt", image_size="landscape_4_3")

        cost = await self.generator.estimate_cost(input_data)

        # 1 megapixel = $0.03
        assert cost == 0.03
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = Flux2ProInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "image_size" in schema["properties"]
        assert "output_format" in schema["properties"]
        assert "safety_tolerance" in schema["properties"]

        # Check that image_size has enum values
        image_size_prop = schema["properties"]["image_size"]
        assert "enum" in image_size_prop
        assert "square_hd" in image_size_prop["enum"]
        assert "landscape_4_3" in image_size_prop["enum"]

        # Check that safety_tolerance has enum values
        safety_prop = schema["properties"]["safety_tolerance"]
        assert "enum" in safety_prop
        assert "1" in safety_prop["enum"]
        assert "5" in safety_prop["enum"]

        # Check defaults
        assert image_size_prop["default"] == "landscape_4_3"
        assert schema["properties"]["output_format"]["default"] == "jpeg"
        assert safety_prop["default"] == "2"
