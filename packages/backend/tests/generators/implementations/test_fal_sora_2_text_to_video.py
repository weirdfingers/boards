"""
Tests for FalSora2TextToVideoGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.fal_sora_2_text_to_video import (
    FalSora2TextToVideoGenerator,
    Sora2TextToVideoInput,
)


class TestSora2TextToVideoInput:
    """Tests for Sora2TextToVideoInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = Sora2TextToVideoInput(
            prompt="A dramatic Hollywood breakup scene at dusk",
            resolution="720p",
            aspect_ratio="9:16",
            duration=8,
        )

        assert input_data.prompt == "A dramatic Hollywood breakup scene at dusk"
        assert input_data.resolution == "720p"
        assert input_data.aspect_ratio == "9:16"
        assert input_data.duration == 8

    def test_input_defaults(self):
        """Test default values."""
        input_data = Sora2TextToVideoInput(
            prompt="Test prompt",
        )

        assert input_data.resolution == "720p"
        assert input_data.aspect_ratio == "16:9"
        assert input_data.duration == 4

    def test_invalid_duration(self):
        """Test validation fails for invalid duration."""
        with pytest.raises(ValidationError):
            Sora2TextToVideoInput(
                prompt="Test",
                duration=5,  # type: ignore[arg-type]
            )

    def test_invalid_aspect_ratio(self):
        """Test validation fails for invalid aspect ratio."""
        with pytest.raises(ValidationError):
            Sora2TextToVideoInput(
                prompt="Test",
                aspect_ratio="4:3",  # type: ignore[arg-type]
            )

    def test_prompt_min_length(self):
        """Test prompt min length validation."""
        # This should fail (empty string)
        with pytest.raises(ValidationError):
            Sora2TextToVideoInput(prompt="")

    def test_prompt_max_length(self):
        """Test prompt max length validation."""
        # This should succeed (exactly at limit)
        long_prompt = "a" * 5000
        input_data = Sora2TextToVideoInput(prompt=long_prompt)
        assert len(input_data.prompt) == 5000

        # This should fail (over limit)
        too_long_prompt = "a" * 5001
        with pytest.raises(ValidationError):
            Sora2TextToVideoInput(prompt=too_long_prompt)

    def test_all_duration_options(self):
        """Test all valid duration options."""
        valid_durations = [4, 8, 12]

        for duration in valid_durations:
            input_data = Sora2TextToVideoInput(
                prompt="Test",
                duration=duration,  # type: ignore[arg-type]
            )
            assert input_data.duration == duration

    def test_all_aspect_ratio_options(self):
        """Test all valid aspect ratio options."""
        valid_ratios = ["16:9", "9:16"]

        for ratio in valid_ratios:
            input_data = Sora2TextToVideoInput(
                prompt="Test",
                aspect_ratio=ratio,  # type: ignore[arg-type]
            )
            assert input_data.aspect_ratio == ratio


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalSora2TextToVideoGenerator:
    """Tests for FalSora2TextToVideoGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalSora2TextToVideoGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-sora-2-text-to-video"
        assert self.generator.artifact_type == "video"
        assert "text-to-video" in self.generator.description.lower()
        assert "Sora 2" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == Sora2TextToVideoInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = Sora2TextToVideoInput(
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
                        duration=4.0,
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
    async def test_generate_successful_4_second_video(self):
        """Test successful generation with 4-second video."""
        input_data = Sora2TextToVideoInput(
            prompt="A cinematic sunset over mountains",
            duration=4,
            aspect_ratio="16:9",
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
                        "width": 1280,
                        "height": 720,
                        "duration": 4.0,
                        "fps": 30,
                    }
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
                width=1280,
                height=720,
                format="mp4",
                duration=4.0,
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
                "fal-ai/sora-2/text-to-video",
                arguments={
                    "prompt": "A cinematic sunset over mountains",
                    "resolution": "720p",
                    "aspect_ratio": "16:9",
                    "duration": 4,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_successful_12_second_video_portrait(self):
        """Test successful generation with 12-second portrait video."""
        input_data = Sora2TextToVideoInput(
            prompt="A person walking through a city",
            duration=12,
            aspect_ratio="9:16",
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
                        "duration": 12.0,
                        "fps": 24,
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
                height=1280,
                format="mp4",
                duration=12.0,
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
            assert call_args[1]["arguments"]["duration"] == 12
            assert call_args[1]["arguments"]["aspect_ratio"] == "9:16"

    @pytest.mark.asyncio
    async def test_generate_with_fallback_dimensions(self):
        """Test generation uses fallback dimensions when not provided by API."""
        input_data = Sora2TextToVideoInput(
            prompt="Abstract art animation",
            aspect_ratio="16:9",
        )

        fake_video_url = "https://storage.googleapis.com/falserverless/output.mp4"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
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
                width=1280,
                height=720,
                format="mp4",
                duration=4.0,
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
                    # Verify fallback dimensions for 16:9 at 720p
                    assert kwargs["width"] == 1280
                    assert kwargs["height"] == 720
                    assert kwargs["duration"] == 4.0  # From input
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
        input_data = Sora2TextToVideoInput(
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
    async def test_estimate_cost_4_second(self):
        """Test cost estimation for 4-second video."""
        input_data = Sora2TextToVideoInput(
            prompt="Test prompt",
            duration=4,
        )

        cost = await self.generator.estimate_cost(input_data)

        # 4-second video: base cost * 1.0
        assert cost == 0.20
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_8_second(self):
        """Test cost estimation for 8-second video."""
        input_data = Sora2TextToVideoInput(
            prompt="Test prompt",
            duration=8,
        )

        cost = await self.generator.estimate_cost(input_data)

        # 8-second video: base cost * 2.0
        assert cost == 0.40
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_12_second(self):
        """Test cost estimation for 12-second video."""
        input_data = Sora2TextToVideoInput(
            prompt="Test prompt",
            duration=12,
        )

        cost = await self.generator.estimate_cost(input_data)

        # 12-second video: base cost * 3.0
        assert cost == pytest.approx(0.60)
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = Sora2TextToVideoInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "resolution" in schema["properties"]
        assert "aspect_ratio" in schema["properties"]
        assert "duration" in schema["properties"]

        # Check prompt constraints
        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop["minLength"] == 1
        assert prompt_prop["maxLength"] == 5000

        # Check resolution enum
        resolution_prop = schema["properties"]["resolution"]
        assert "enum" in resolution_prop or "const" in resolution_prop

        # Check aspect_ratio enum
        aspect_ratio_prop = schema["properties"]["aspect_ratio"]
        assert "enum" in aspect_ratio_prop or "anyOf" in aspect_ratio_prop

        # Check duration enum
        duration_prop = schema["properties"]["duration"]
        assert "enum" in duration_prop or "anyOf" in duration_prop
