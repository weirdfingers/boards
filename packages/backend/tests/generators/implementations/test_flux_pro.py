"""
Tests for FluxProGenerator.
"""

import os
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext
from boards.generators.implementations.image.flux_pro import (
    FluxProGenerator,
    FluxProInput,
    FluxProOutput,
)


class TestFluxProInput:
    """Tests for FluxProInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = FluxProInput(
            prompt="A beautiful landscape", aspect_ratio="16:9", safety_tolerance=3
        )

        assert input_data.prompt == "A beautiful landscape"
        assert input_data.aspect_ratio == "16:9"
        assert input_data.safety_tolerance == 3

    def test_input_defaults(self):
        """Test default values."""
        input_data = FluxProInput(prompt="Test prompt")

        assert input_data.aspect_ratio == "1:1"
        assert input_data.safety_tolerance == 2

    def test_invalid_aspect_ratio(self):
        """Test validation fails for invalid aspect ratio."""
        with pytest.raises(ValidationError):
            FluxProInput(prompt="Test", aspect_ratio="invalid")

    def test_invalid_safety_tolerance(self):
        """Test validation fails for invalid safety tolerance."""
        with pytest.raises(ValidationError):
            FluxProInput(prompt="Test", safety_tolerance=0)  # Below minimum

        with pytest.raises(ValidationError):
            FluxProInput(prompt="Test", safety_tolerance=6)  # Above maximum


class TestFluxProGenerator:
    """Tests for FluxProGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FluxProGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "flux-pro"
        assert self.generator.artifact_type == "image"
        assert "FLUX.1.1" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == FluxProInput

    def test_output_schema(self):
        """Test output schema."""
        schema_class = self.generator.get_output_schema()
        assert schema_class == FluxProOutput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = FluxProInput(prompt="Test prompt")

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"

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

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            with pytest.raises(ValueError):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_generate_successful(self):
        """Test successful generation."""
        input_data = FluxProInput(
            prompt="A serene mountain lake", aspect_ratio="16:9", safety_tolerance=2
        )

        fake_output_url = "https://replicate.delivery/pbxt/fake-image-url.png"

        with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "fake-token"}):
            # Create a mock replicate module via sys.modules
            import sys

            mock_replicate = AsyncMock()
            mock_replicate.async_run = AsyncMock(return_value=[fake_output_url])
            sys.modules["replicate"] = mock_replicate

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

                async def resolve_artifact(self, artifact):
                    return ""

                async def store_image_result(self, **kwargs):
                    return mock_artifact

                async def store_video_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_audio_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            result = await self.generator.generate(input_data, DummyCtx())

            # Verify result
            assert isinstance(result, FluxProOutput)
            assert result.image == mock_artifact

            # Verify API calls
            mock_replicate.async_run.assert_called_once_with(
                "black-forest-labs/flux-1.1-pro",
                input={
                    "prompt": "A serene mountain lake",
                    "aspect_ratio": "16:9",
                    "safety_tolerance": 2,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_single_url_response(self):
        """Test generation when Replicate returns a single URL instead of list."""
        input_data = FluxProInput(prompt="Test")
        fake_output_url = "https://replicate.delivery/pbxt/single-url.png"

        with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "fake-token"}):
            import sys

            mock_replicate = AsyncMock()
            mock_replicate.async_run = AsyncMock(return_value=fake_output_url)
            sys.modules["replicate"] = mock_replicate

            mock_artifact = ImageArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1024,
                height=1024,
                format="png",
            )

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"

                async def resolve_artifact(self, artifact):
                    return ""

                async def store_image_result(self, **kwargs):
                    return mock_artifact

                async def store_video_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_audio_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            result = await self.generator.generate(input_data, DummyCtx())

            assert isinstance(result, FluxProOutput)
            assert result.image == mock_artifact

    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation."""
        input_data = FluxProInput(prompt="Test prompt")

        cost = await self.generator.estimate_cost(input_data)

        assert cost == 0.055  # Expected FLUX.1.1 Pro cost
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = FluxProInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "aspect_ratio" in schema["properties"]
        assert "safety_tolerance" in schema["properties"]

        # Check that aspect_ratio has enum values
        aspect_ratio_prop = schema["properties"]["aspect_ratio"]
        assert "pattern" in aspect_ratio_prop

        # Check that safety_tolerance has constraints
        safety_prop = schema["properties"]["safety_tolerance"]
        assert safety_prop["minimum"] == 1
        assert safety_prop["maximum"] == 5
        assert safety_prop["default"] == 2
