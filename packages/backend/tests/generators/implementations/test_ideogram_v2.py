"""
Tests for FalIdeogramV2Generator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.ideogram_v2 import (
    FalIdeogramV2Generator,
    IdeogramV2Input,
)


class TestIdeogramV2Input:
    """Tests for IdeogramV2Input schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = IdeogramV2Input(
            prompt="Create a modern logo with the text 'AI Studio'",
            aspect_ratio="16:9",
            style="design",
            expand_prompt=True,
            seed=42,
            negative_prompt="blurry, low quality",
        )

        assert input_data.prompt == "Create a modern logo with the text 'AI Studio'"
        assert input_data.aspect_ratio == "16:9"
        assert input_data.style == "design"
        assert input_data.expand_prompt is True
        assert input_data.seed == 42
        assert input_data.negative_prompt == "blurry, low quality"

    def test_input_defaults(self):
        """Test default values."""
        input_data = IdeogramV2Input(prompt="Test prompt")

        assert input_data.aspect_ratio == "1:1"
        assert input_data.style == "auto"
        assert input_data.expand_prompt is True
        assert input_data.seed is None
        assert input_data.negative_prompt == ""
        assert input_data.sync_mode is False

    def test_invalid_aspect_ratio(self):
        """Test validation fails for invalid aspect ratio."""
        with pytest.raises(ValidationError):
            IdeogramV2Input(
                prompt="Test",
                aspect_ratio="invalid",  # type: ignore[arg-type]
            )

    def test_invalid_style(self):
        """Test validation fails for invalid style."""
        with pytest.raises(ValidationError):
            IdeogramV2Input(
                prompt="Test",
                style="invalid",  # type: ignore[arg-type]
            )

    def test_all_aspect_ratios(self):
        """Test all valid aspect ratio options."""
        valid_ratios = [
            "1:1",
            "16:9",
            "9:16",
            "4:3",
            "3:4",
            "10:16",
            "16:10",
            "1:3",
            "3:1",
            "3:2",
            "2:3",
        ]

        for ratio in valid_ratios:
            input_data = IdeogramV2Input(
                prompt="Test",
                aspect_ratio=ratio,  # type: ignore[arg-type]
            )
            assert input_data.aspect_ratio == ratio

    def test_all_styles(self):
        """Test all valid style options."""
        valid_styles = ["auto", "general", "realistic", "design", "render_3D", "anime"]

        for style in valid_styles:
            input_data = IdeogramV2Input(
                prompt="Test",
                style=style,  # type: ignore[arg-type]
            )
            assert input_data.style == style


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalIdeogramV2Generator:
    """Tests for FalIdeogramV2Generator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalIdeogramV2Generator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-ideogram-v2"
        assert self.generator.artifact_type == "image"
        assert "Ideogram V2" in self.generator.description
        assert "typography" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == IdeogramV2Input

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = IdeogramV2Input(prompt="Test prompt")

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
        """Test successful generation with single image output."""
        input_data = IdeogramV2Input(
            prompt="A professional logo with the text 'Innovation'",
            aspect_ratio="1:1",
            style="design",
            expand_prompt=True,
            negative_prompt="blurry",
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.png"

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
                            "content_type": "image/png",
                            "file_name": "output.png",
                            "file_size": 1024000,
                        }
                    ],
                    "seed": 12345,
                }
            )

            # Create mock fal_client module
            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]

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
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/ideogram/v2",
                arguments={
                    "prompt": "A professional logo with the text 'Innovation'",
                    "aspect_ratio": "1:1",
                    "style": "design",
                    "expand_prompt": True,
                    "negative_prompt": "blurry",
                    "sync_mode": False,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_with_seed(self):
        """Test generation with explicit seed value."""
        input_data = IdeogramV2Input(
            prompt="Test prompt",
            seed=42,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-456"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [
                        {
                            "url": fake_output_url,
                            "content_type": "image/png",
                            "file_name": "output.png",
                            "file_size": 1024000,
                        }
                    ],
                    "seed": 42,
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
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

            await self.generator.generate(input_data, DummyCtx())

            # Verify seed was included in API call
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["seed"] == 42

    @pytest.mark.asyncio
    async def test_generate_no_images_returned(self):
        """Test generation fails when API returns no images."""
        input_data = IdeogramV2Input(prompt="test")

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"

            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={"images": [], "seed": 12345})

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
    async def test_estimate_cost(self):
        """Test cost estimation."""
        input_data = IdeogramV2Input(prompt="Test prompt")

        cost = await self.generator.estimate_cost(input_data)

        # Cost should be $0.04 per image
        assert cost == 0.04
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = IdeogramV2Input.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "aspect_ratio" in schema["properties"]
        assert "style" in schema["properties"]
        assert "expand_prompt" in schema["properties"]
        assert "seed" in schema["properties"]
        assert "negative_prompt" in schema["properties"]

        # Check prompt is required
        assert "prompt" in schema["required"]

        # Check aspect_ratio has enum values
        aspect_ratio_prop = schema["properties"]["aspect_ratio"]
        assert "enum" in aspect_ratio_prop or "anyOf" in aspect_ratio_prop

        # Check style has enum values
        style_prop = schema["properties"]["style"]
        assert "enum" in style_prop or "anyOf" in style_prop
