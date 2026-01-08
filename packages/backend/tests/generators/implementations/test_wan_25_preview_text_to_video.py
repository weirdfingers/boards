"""
Tests for FalWan25PreviewTextToVideoGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.wan_25_preview_text_to_video import (
    FalWan25PreviewTextToVideoGenerator,
    Wan25PreviewTextToVideoInput,
)


class TestWan25PreviewTextToVideoInput:
    """Tests for Wan25PreviewTextToVideoInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = Wan25PreviewTextToVideoInput(
            prompt="A beautiful sunset over the ocean",
            resolution="1080p",
            aspect_ratio="16:9",
            duration=10,
        )

        assert input_data.prompt == "A beautiful sunset over the ocean"
        assert input_data.resolution == "1080p"
        assert input_data.aspect_ratio == "16:9"
        assert input_data.duration == 10

    def test_input_defaults(self):
        """Test default values."""
        input_data = Wan25PreviewTextToVideoInput(
            prompt="Test prompt",
        )

        assert input_data.resolution == "1080p"
        assert input_data.aspect_ratio == "16:9"
        assert input_data.duration == 5
        assert input_data.audio_url is None
        assert input_data.seed is None
        assert input_data.enable_safety_checker is True
        assert input_data.negative_prompt is None
        assert input_data.enable_prompt_expansion is True

    def test_invalid_duration(self):
        """Test validation fails for invalid duration."""
        with pytest.raises(ValidationError):
            Wan25PreviewTextToVideoInput(
                prompt="Test",
                duration=7,  # type: ignore[arg-type]
            )

    def test_invalid_aspect_ratio(self):
        """Test validation fails for invalid aspect ratio."""
        with pytest.raises(ValidationError):
            Wan25PreviewTextToVideoInput(
                prompt="Test",
                aspect_ratio="4:3",  # type: ignore[arg-type]
            )

    def test_invalid_resolution(self):
        """Test validation fails for invalid resolution."""
        with pytest.raises(ValidationError):
            Wan25PreviewTextToVideoInput(
                prompt="Test",
                resolution="4k",  # type: ignore[arg-type]
            )

    def test_prompt_min_length(self):
        """Test prompt min length validation."""
        # This should fail (empty string)
        with pytest.raises(ValidationError):
            Wan25PreviewTextToVideoInput(prompt="")

    def test_prompt_max_length(self):
        """Test prompt max length validation."""
        # This should succeed (exactly at limit)
        long_prompt = "a" * 800
        input_data = Wan25PreviewTextToVideoInput(prompt=long_prompt)
        assert len(input_data.prompt) == 800

        # This should fail (over limit)
        too_long_prompt = "a" * 801
        with pytest.raises(ValidationError):
            Wan25PreviewTextToVideoInput(prompt=too_long_prompt)

    def test_negative_prompt_max_length(self):
        """Test negative_prompt max length validation."""
        # This should succeed (exactly at limit)
        input_data = Wan25PreviewTextToVideoInput(prompt="Test", negative_prompt="a" * 500)
        assert len(input_data.negative_prompt) == 500  # type: ignore[arg-type]

        # This should fail (over limit)
        with pytest.raises(ValidationError):
            Wan25PreviewTextToVideoInput(prompt="Test", negative_prompt="a" * 501)

    def test_all_duration_options(self):
        """Test all valid duration options."""
        valid_durations = [5, 10]

        for duration in valid_durations:
            input_data = Wan25PreviewTextToVideoInput(
                prompt="Test",
                duration=duration,  # type: ignore[arg-type]
            )
            assert input_data.duration == duration

    def test_all_aspect_ratio_options(self):
        """Test all valid aspect ratio options."""
        valid_ratios = ["16:9", "9:16", "1:1"]

        for ratio in valid_ratios:
            input_data = Wan25PreviewTextToVideoInput(
                prompt="Test",
                aspect_ratio=ratio,  # type: ignore[arg-type]
            )
            assert input_data.aspect_ratio == ratio

    def test_all_resolution_options(self):
        """Test all valid resolution options."""
        valid_resolutions = ["480p", "720p", "1080p"]

        for resolution in valid_resolutions:
            input_data = Wan25PreviewTextToVideoInput(
                prompt="Test",
                resolution=resolution,  # type: ignore[arg-type]
            )
            assert input_data.resolution == resolution

    def test_optional_parameters(self):
        """Test optional parameters are correctly set."""
        input_data = Wan25PreviewTextToVideoInput(
            prompt="Test prompt",
            audio_url="https://example.com/audio.mp3",
            seed=42,
            negative_prompt="blurry, low quality",
            enable_safety_checker=False,
            enable_prompt_expansion=False,
        )

        assert input_data.audio_url == "https://example.com/audio.mp3"
        assert input_data.seed == 42
        assert input_data.negative_prompt == "blurry, low quality"
        assert input_data.enable_safety_checker is False
        assert input_data.enable_prompt_expansion is False


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalWan25PreviewTextToVideoGenerator:
    """Tests for FalWan25PreviewTextToVideoGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalWan25PreviewTextToVideoGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-wan-25-preview-text-to-video"
        assert self.generator.artifact_type == "video"
        assert "Wan 2.5 Preview" in self.generator.description
        assert "text-to-video" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == Wan25PreviewTextToVideoInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = Wan25PreviewTextToVideoInput(
                prompt="Test prompt",
            )

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return ""

                async def store_image_result(self, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, **kwargs):
                    return VideoArtifact(
                        generation_id="test_gen",
                        storage_url="",
                        width=1,
                        height=1,
                        format="mp4",
                        duration=5.0,
                        fps=30,
                    )

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
    async def test_generate_successful_5_second_video(self):
        """Test successful generation with 5-second video."""
        input_data = Wan25PreviewTextToVideoInput(
            prompt="A cinematic sunset over mountains",
            duration=5,
            aspect_ratio="16:9",
            resolution="1080p",
        )

        fake_video_url = "https://storage.googleapis.com/falserverless/output.mp4"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            # Create mock handler with async iterator for events
            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-123"

            # Create async iterator that yields nothing (no events)
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())

            # Mock the get() method to return result with metadata
            mock_handler.get = AsyncMock(
                return_value={
                    "video": {
                        "url": fake_video_url,
                        "content_type": "video/mp4",
                        "file_name": "output.mp4",
                        "width": 1920,
                        "height": 1080,
                        "duration": 5.0,
                        "fps": 30,
                    },
                    "seed": 12345,
                    "actual_prompt": "A cinematic sunset over mountains (expanded)",
                }
            )

            # Create mock fal_client module
            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]

            sys.modules["fal_client"] = mock_fal_client

            # Mock storage result
            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_video_url,
                width=1920,
                height=1080,
                format="mp4",
                duration=5.0,
                fps=30,
            )

            # Execute generation
            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    raise NotImplementedError

                async def store_image_result(self, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, **kwargs):
                    return mock_artifact

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

            # Verify API call
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/wan-25-preview/text-to-video",
                arguments={
                    "prompt": "A cinematic sunset over mountains",
                    "aspect_ratio": "16:9",
                    "resolution": "1080p",
                    "duration": 5,
                    "enable_safety_checker": True,
                    "enable_prompt_expansion": True,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_successful_10_second_video_portrait(self):
        """Test successful generation with 10-second portrait video."""
        input_data = Wan25PreviewTextToVideoInput(
            prompt="A person walking through a city",
            duration=10,
            aspect_ratio="9:16",
            resolution="720p",
        )

        fake_video_url = "https://storage.googleapis.com/falserverless/output_portrait.mp4"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-456"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "video": {
                        "url": fake_video_url,
                        "content_type": "video/mp4",
                        "width": 720,
                        "height": 1280,
                        "duration": 10.0,
                        "fps": 24,
                    },
                    "seed": 67890,
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_video_url,
                width=720,
                height=1280,
                format="mp4",
                duration=10.0,
                fps=24,
            )

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    raise NotImplementedError

                async def store_image_result(self, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, **kwargs):
                    return mock_artifact

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

            # Verify API call with custom parameters
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["duration"] == 10
            assert call_args[1]["arguments"]["aspect_ratio"] == "9:16"
            assert call_args[1]["arguments"]["resolution"] == "720p"

    @pytest.mark.asyncio
    async def test_generate_with_optional_parameters(self):
        """Test generation with optional parameters."""
        input_data = Wan25PreviewTextToVideoInput(
            prompt="A dynamic scene",
            duration=5,
            audio_url="https://example.com/audio.mp3",
            seed=42,
            negative_prompt="blurry, low quality",
            enable_safety_checker=False,
            enable_prompt_expansion=False,
        )

        fake_video_url = "https://storage.googleapis.com/falserverless/output.mp4"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "video": {
                        "url": fake_video_url,
                        "content_type": "video/mp4",
                        "width": 1920,
                        "height": 1080,
                        "duration": 5.0,
                        "fps": 30,
                    }
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_video_url,
                width=1920,
                height=1080,
                format="mp4",
                duration=5.0,
                fps=30,
            )

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    raise NotImplementedError

                async def store_image_result(self, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, **kwargs):
                    return mock_artifact

                async def store_audio_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_text_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            await self.generator.generate(input_data, DummyCtx())

            # Verify API call includes optional parameters
            call_args = mock_fal_client.submit_async.call_args
            arguments = call_args[1]["arguments"]
            assert arguments["audio_url"] == "https://example.com/audio.mp3"
            assert arguments["seed"] == 42
            assert arguments["negative_prompt"] == "blurry, low quality"
            assert arguments["enable_safety_checker"] is False
            assert arguments["enable_prompt_expansion"] is False

    @pytest.mark.asyncio
    async def test_generate_with_fallback_dimensions(self):
        """Test generation uses fallback dimensions when not provided by API."""
        input_data = Wan25PreviewTextToVideoInput(
            prompt="Abstract art animation",
            aspect_ratio="1:1",
            resolution="720p",
        )

        fake_video_url = "https://storage.googleapis.com/falserverless/output.mp4"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-fallback"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            # Return response without width/height
            mock_handler.get = AsyncMock(
                return_value={
                    "video": {
                        "url": fake_video_url,
                        "content_type": "video/mp4",
                        # No width, height, duration, or fps
                    }
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_video_url,
                width=720,
                height=720,
                format="mp4",
                duration=5.0,
                fps=None,
            )

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    raise NotImplementedError

                async def store_image_result(self, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, **kwargs):
                    # Verify fallback dimensions for 1:1 at 720p
                    assert kwargs["width"] == 720
                    assert kwargs["height"] == 720
                    assert kwargs["duration"] == 5.0  # From input
                    return mock_artifact

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

    @pytest.mark.asyncio
    async def test_generate_no_video_returned(self):
        """Test generation fails when API returns no video."""
        input_data = Wan25PreviewTextToVideoInput(
            prompt="test",
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-error"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={})  # No video in response

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    raise NotImplementedError

                async def store_image_result(self, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, **kwargs):
                    raise NotImplementedError

                async def store_audio_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def store_text_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            with pytest.raises(ValueError, match="No video returned"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_estimate_cost_5_second(self):
        """Test cost estimation for 5-second video."""
        input_data = Wan25PreviewTextToVideoInput(
            prompt="Test prompt",
            duration=5,
        )

        cost = await self.generator.estimate_cost(input_data)

        # 5-second video: base cost * 1.0
        assert cost == 0.10
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_10_second(self):
        """Test cost estimation for 10-second video."""
        input_data = Wan25PreviewTextToVideoInput(
            prompt="Test prompt",
            duration=10,
        )

        cost = await self.generator.estimate_cost(input_data)

        # 10-second video: base cost * 2.0
        assert cost == 0.20
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = Wan25PreviewTextToVideoInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "resolution" in schema["properties"]
        assert "aspect_ratio" in schema["properties"]
        assert "duration" in schema["properties"]
        assert "audio_url" in schema["properties"]
        assert "seed" in schema["properties"]
        assert "enable_safety_checker" in schema["properties"]
        assert "negative_prompt" in schema["properties"]
        assert "enable_prompt_expansion" in schema["properties"]

        # Check prompt constraints
        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop["minLength"] == 1
        assert prompt_prop["maxLength"] == 800

        # Check negative_prompt constraints
        # Optional fields use anyOf structure in Pydantic JSON schema
        negative_prompt_prop = schema["properties"]["negative_prompt"]
        if "anyOf" in negative_prompt_prop:
            # Find the string type in anyOf
            string_type = next(
                (t for t in negative_prompt_prop["anyOf"] if t.get("type") == "string"), None
            )
            assert string_type is not None
            assert string_type.get("maxLength") == 500
        else:
            assert negative_prompt_prop.get("maxLength") == 500

        # Check resolution enum
        resolution_prop = schema["properties"]["resolution"]
        assert "enum" in resolution_prop or "anyOf" in resolution_prop

        # Check aspect_ratio enum
        aspect_ratio_prop = schema["properties"]["aspect_ratio"]
        assert "enum" in aspect_ratio_prop or "anyOf" in aspect_ratio_prop

        # Check duration enum
        duration_prop = schema["properties"]["duration"]
        assert "enum" in duration_prop or "anyOf" in duration_prop
