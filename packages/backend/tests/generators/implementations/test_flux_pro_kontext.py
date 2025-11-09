"""
Tests for FalFluxProKontextGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.flux_pro_kontext import (
    FalFluxProKontextGenerator,
    FluxProKontextInput,
)


class TestFluxProKontextInput:
    """Tests for FluxProKontextInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/reference.png",
            format="png",
            width=1024,
            height=1024,
        )

        input_data = FluxProKontextInput(
            prompt="Put a donut next to the flour",
            image_url=image_artifact,
            num_images=2,
            output_format="jpeg",
            aspect_ratio="16:9",
        )

        assert input_data.prompt == "Put a donut next to the flour"
        assert input_data.image_url == image_artifact
        assert input_data.num_images == 2
        assert input_data.output_format == "jpeg"
        assert input_data.aspect_ratio == "16:9"

    def test_input_defaults(self):
        """Test default values."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/reference.png",
            format="png",
            width=1024,
            height=1024,
        )

        input_data = FluxProKontextInput(
            prompt="Test prompt",
            image_url=image_artifact,
        )

        assert input_data.num_images == 1
        assert input_data.output_format == "jpeg"
        assert input_data.sync_mode is False
        assert input_data.safety_tolerance == "2"
        assert input_data.guidance_scale == 3.5
        assert input_data.seed is None
        assert input_data.enhance_prompt is False
        assert input_data.aspect_ratio is None

    def test_invalid_output_format(self):
        """Test validation fails for invalid output format."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/reference.png",
            format="png",
            width=1024,
            height=1024,
        )

        with pytest.raises(ValidationError):
            FluxProKontextInput(
                prompt="Test",
                image_url=image_artifact,
                output_format="invalid",  # type: ignore[arg-type]
            )

    def test_invalid_aspect_ratio(self):
        """Test validation fails for invalid aspect ratio."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/reference.png",
            format="png",
            width=1024,
            height=1024,
        )

        with pytest.raises(ValidationError):
            FluxProKontextInput(
                prompt="Test",
                image_url=image_artifact,
                aspect_ratio="invalid",  # type: ignore[arg-type]
            )

    def test_num_images_validation(self):
        """Test validation for num_images constraints."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/reference.png",
            format="png",
            width=1024,
            height=1024,
        )

        # Test below minimum
        with pytest.raises(ValidationError):
            FluxProKontextInput(
                prompt="Test",
                image_url=image_artifact,
                num_images=0,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            FluxProKontextInput(
                prompt="Test",
                image_url=image_artifact,
                num_images=5,
            )

    def test_guidance_scale_validation(self):
        """Test validation for guidance_scale constraints."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/reference.png",
            format="png",
            width=1024,
            height=1024,
        )

        # Test below minimum
        with pytest.raises(ValidationError):
            FluxProKontextInput(
                prompt="Test",
                image_url=image_artifact,
                guidance_scale=0.5,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            FluxProKontextInput(
                prompt="Test",
                image_url=image_artifact,
                guidance_scale=25.0,
            )

    def test_aspect_ratio_options(self):
        """Test all valid aspect ratio options."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/reference.png",
            format="png",
            width=1024,
            height=1024,
        )

        valid_ratios = [
            "21:9",
            "16:9",
            "4:3",
            "3:2",
            "1:1",
            "2:3",
            "3:4",
            "9:16",
            "9:21",
        ]

        for ratio in valid_ratios:
            input_data = FluxProKontextInput(
                prompt="Test",
                image_url=image_artifact,
                aspect_ratio=ratio,  # type: ignore[arg-type]
            )
            assert input_data.aspect_ratio == ratio


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalFluxProKontextGenerator:
    """Tests for FalFluxProKontextGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalFluxProKontextGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-flux-pro-kontext"
        assert self.generator.artifact_type == "image"
        assert "kontext" in self.generator.description.lower()
        assert "image-to-image" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == FluxProKontextInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            image_artifact = ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/reference.png",
                format="png",
                width=1024,
                height=1024,
            )

            input_data = FluxProKontextInput(
                prompt="Test prompt",
                image_url=image_artifact,
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
            height=1024,
        )

        input_data = FluxProKontextInput(
            prompt="Put a donut next to the flour",
            image_url=input_image,
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
                            "height": 1024,
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
                "fal-ai/flux-pro/kontext",
                arguments={
                    "prompt": "Put a donut next to the flour",
                    "image_url": fake_uploaded_url,  # Should use uploaded URL, not original
                    "num_images": 1,
                    "output_format": "jpeg",
                    "sync_mode": False,
                    "safety_tolerance": "2",
                    "guidance_scale": 3.5,
                    "enhance_prompt": False,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_with_optional_parameters(self):
        """Test successful generation with optional parameters."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1920,
            height=1080,
        )

        input_data = FluxProKontextInput(
            prompt="Transform the scene",
            image_url=input_image,
            num_images=2,
            output_format="png",
            aspect_ratio="16:9",
            seed=42,
            guidance_scale=5.0,
            safety_tolerance="4",
            enhance_prompt=True,
        )

        fake_output_urls = [
            "https://storage.googleapis.com/falserverless/output1.png",
            "https://storage.googleapis.com/falserverless/output2.png",
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
                        {"url": fake_output_urls[0], "width": 1920, "height": 1080},
                        {"url": fake_output_urls[1], "width": 1920, "height": 1080},
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
                    width=1920,
                    height=1080,
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
            assert len(result.outputs) == 2

            # Verify API call included all optional parameters
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["aspect_ratio"] == "16:9"
            assert call_args[1]["arguments"]["seed"] == 42
            assert call_args[1]["arguments"]["guidance_scale"] == 5.0
            assert call_args[1]["arguments"]["safety_tolerance"] == "4"
            assert call_args[1]["arguments"]["enhance_prompt"] is True
            assert call_args[1]["arguments"]["image_url"] == fake_uploaded_url

    @pytest.mark.asyncio
    async def test_generate_no_images_returned(self):
        """Test generation fails when API returns no images."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=1024,
        )

        input_data = FluxProKontextInput(
            prompt="test",
            image_url=input_image,
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
            height=1024,
        )

        input_data = FluxProKontextInput(
            prompt="Test prompt",
            image_url=input_image,
            num_images=1,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Per-image cost (0.055 * 1)
        assert cost == 0.055
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_multiple_images(self):
        """Test cost estimation for multiple images."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=1024,
        )

        input_data = FluxProKontextInput(
            prompt="Test prompt",
            image_url=input_image,
            num_images=4,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Per-image cost (0.055 * 4)
        assert cost == 0.22
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = FluxProKontextInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "image_url" in schema["properties"]
        assert "num_images" in schema["properties"]
        assert "output_format" in schema["properties"]
        assert "aspect_ratio" in schema["properties"]
        assert "guidance_scale" in schema["properties"]
        assert "safety_tolerance" in schema["properties"]
        assert "seed" in schema["properties"]
        assert "enhance_prompt" in schema["properties"]

        # Check that num_images has constraints
        num_images_prop = schema["properties"]["num_images"]
        assert num_images_prop["minimum"] == 1
        assert num_images_prop["maximum"] == 4
        assert num_images_prop["default"] == 1

        # Check that guidance_scale has constraints
        guidance_scale_prop = schema["properties"]["guidance_scale"]
        assert guidance_scale_prop["minimum"] == 1.0
        assert guidance_scale_prop["maximum"] == 20.0
        assert guidance_scale_prop["default"] == 3.5
