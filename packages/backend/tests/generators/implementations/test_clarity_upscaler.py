"""
Tests for FalClarityUpscalerGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.clarity_upscaler import (
    ClarityUpscalerInput,
    FalClarityUpscalerGenerator,
)


class TestClarityUpscalerInput:
    """Tests for ClarityUpscalerInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=512,
            height=512,
        )

        input_data = ClarityUpscalerInput(
            image_url=image_artifact,
            prompt="masterpiece, best quality, highres",
            upscale_factor=2.0,
        )

        assert input_data.image_url == image_artifact
        assert input_data.prompt == "masterpiece, best quality, highres"
        assert input_data.upscale_factor == 2.0

    def test_input_defaults(self):
        """Test default values."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=512,
            height=512,
        )

        input_data = ClarityUpscalerInput(image_url=image_artifact)

        assert input_data.prompt == "masterpiece, best quality, highres"
        assert input_data.upscale_factor == 2.0
        assert input_data.negative_prompt == "(worst quality, low quality, normal quality:2)"
        assert input_data.creativity == 0.35
        assert input_data.resemblance == 0.6
        assert input_data.guidance_scale == 4.0
        assert input_data.num_inference_steps == 18
        assert input_data.seed is None
        assert input_data.enable_safety_checker is True

    def test_upscale_factor_validation(self):
        """Test validation for upscale_factor constraints."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=512,
            height=512,
        )

        # Test below minimum
        with pytest.raises(ValidationError):
            ClarityUpscalerInput(
                image_url=image_artifact,
                upscale_factor=0.5,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            ClarityUpscalerInput(
                image_url=image_artifact,
                upscale_factor=5.0,
            )

        # Test valid boundaries
        input_min = ClarityUpscalerInput(image_url=image_artifact, upscale_factor=1.0)
        assert input_min.upscale_factor == 1.0

        input_max = ClarityUpscalerInput(image_url=image_artifact, upscale_factor=4.0)
        assert input_max.upscale_factor == 4.0

    def test_creativity_validation(self):
        """Test validation for creativity constraints."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=512,
            height=512,
        )

        # Test below minimum
        with pytest.raises(ValidationError):
            ClarityUpscalerInput(
                image_url=image_artifact,
                creativity=-0.1,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            ClarityUpscalerInput(
                image_url=image_artifact,
                creativity=1.1,
            )

    def test_resemblance_validation(self):
        """Test validation for resemblance constraints."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=512,
            height=512,
        )

        # Test below minimum
        with pytest.raises(ValidationError):
            ClarityUpscalerInput(
                image_url=image_artifact,
                resemblance=-0.1,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            ClarityUpscalerInput(
                image_url=image_artifact,
                resemblance=1.1,
            )

    def test_guidance_scale_validation(self):
        """Test validation for guidance_scale constraints."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=512,
            height=512,
        )

        # Test below minimum
        with pytest.raises(ValidationError):
            ClarityUpscalerInput(
                image_url=image_artifact,
                guidance_scale=-1.0,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            ClarityUpscalerInput(
                image_url=image_artifact,
                guidance_scale=21.0,
            )

    def test_num_inference_steps_validation(self):
        """Test validation for num_inference_steps constraints."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=512,
            height=512,
        )

        # Test below minimum
        with pytest.raises(ValidationError):
            ClarityUpscalerInput(
                image_url=image_artifact,
                num_inference_steps=3,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            ClarityUpscalerInput(
                image_url=image_artifact,
                num_inference_steps=51,
            )

        # Test valid boundaries
        input_min = ClarityUpscalerInput(image_url=image_artifact, num_inference_steps=4)
        assert input_min.num_inference_steps == 4

        input_max = ClarityUpscalerInput(image_url=image_artifact, num_inference_steps=50)
        assert input_max.num_inference_steps == 50


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalClarityUpscalerGenerator:
    """Tests for FalClarityUpscalerGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalClarityUpscalerGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-clarity-upscaler"
        assert self.generator.artifact_type == "image"
        assert "upscal" in self.generator.description.lower()
        assert "Clarity" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == ClarityUpscalerInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            image_artifact = ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/image.png",
                format="png",
                width=512,
                height=512,
            )

            input_data = ClarityUpscalerInput(image_url=image_artifact)

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
    async def test_generate_successful(self):
        """Test successful generation."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=512,
            height=512,
        )

        input_data = ClarityUpscalerInput(
            image_url=input_image,
            prompt="masterpiece, best quality, highres",
            upscale_factor=2.0,
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
                    "image": {
                        "url": fake_output_url,
                        "width": 1024,
                        "height": 1024,
                    },
                    "seed": 12345,
                    "timings": {},
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
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[0][0] == "fal-ai/clarity-upscaler"
            assert call_args[1]["arguments"]["image_url"] == fake_uploaded_url
            assert call_args[1]["arguments"]["prompt"] == "masterpiece, best quality, highres"
            assert call_args[1]["arguments"]["upscale_factor"] == 2.0

    @pytest.mark.asyncio
    async def test_generate_with_seed(self):
        """Test generation with seed parameter."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=512,
            height=512,
        )

        input_data = ClarityUpscalerInput(
            image_url=input_image,
            seed=42,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.png"
        fake_uploaded_url = "https://fal.media/files/uploaded-input.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-456"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "image": {"url": fake_output_url, "width": 1024, "height": 1024},
                    "seed": 42,
                    "timings": {},
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
                height=1024,
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

            # Verify seed was included in API call
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["seed"] == 42

    @pytest.mark.asyncio
    async def test_generate_no_image_returned(self):
        """Test generation fails when API returns no image."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=512,
            height=512,
        )

        input_data = ClarityUpscalerInput(image_url=input_image)

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={"seed": 123, "timings": {}})

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

            with pytest.raises(ValueError, match="No image returned"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=512,
            height=512,
        )

        input_data = ClarityUpscalerInput(image_url=input_image)

        cost = await self.generator.estimate_cost(input_data)

        assert cost == 0.05
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = ClarityUpscalerInput.model_json_schema()

        assert schema["type"] == "object"
        assert "image_url" in schema["properties"]
        assert "prompt" in schema["properties"]
        assert "upscale_factor" in schema["properties"]
        assert "creativity" in schema["properties"]
        assert "resemblance" in schema["properties"]
        assert "guidance_scale" in schema["properties"]
        assert "num_inference_steps" in schema["properties"]
        assert "seed" in schema["properties"]
        assert "enable_safety_checker" in schema["properties"]

        # Check upscale_factor constraints
        upscale_prop = schema["properties"]["upscale_factor"]
        assert upscale_prop["minimum"] == 1.0
        assert upscale_prop["maximum"] == 4.0
        assert upscale_prop["default"] == 2.0

        # Check num_inference_steps constraints
        steps_prop = schema["properties"]["num_inference_steps"]
        assert steps_prop["minimum"] == 4
        assert steps_prop["maximum"] == 50
        assert steps_prop["default"] == 18
