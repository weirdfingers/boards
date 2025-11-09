"""
Tests for FalKlingVideoV25TurboProTextToVideoGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.kling_video_v2_5_turbo_pro_text_to_video import (
    FalKlingVideoV25TurboProTextToVideoGenerator,
    KlingVideoV25TurboProTextToVideoInput,
)


class TestKlingVideoV25TurboProTextToVideoInput:
    """Tests for KlingVideoV25TurboProTextToVideoInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = KlingVideoV25TurboProTextToVideoInput(
            prompt="A noble lord walks among his people",
            duration="10",
            aspect_ratio="9:16",
            negative_prompt="low quality, blurry",
            cfg_scale=0.7,
        )

        assert input_data.prompt == "A noble lord walks among his people"
        assert input_data.duration == "10"
        assert input_data.aspect_ratio == "9:16"
        assert input_data.negative_prompt == "low quality, blurry"
        assert input_data.cfg_scale == 0.7

    def test_input_defaults(self):
        """Test default values."""
        input_data = KlingVideoV25TurboProTextToVideoInput(
            prompt="Test prompt",
        )

        assert input_data.duration == "5"
        assert input_data.aspect_ratio == "16:9"
        assert input_data.negative_prompt == "blur, distort, and low quality"
        assert input_data.cfg_scale == 0.5

    def test_invalid_duration(self):
        """Test validation fails for invalid duration."""
        with pytest.raises(ValidationError):
            KlingVideoV25TurboProTextToVideoInput(
                prompt="Test",
                duration="15",  # type: ignore[arg-type]
            )

    def test_invalid_aspect_ratio(self):
        """Test validation fails for invalid aspect ratio."""
        with pytest.raises(ValidationError):
            KlingVideoV25TurboProTextToVideoInput(
                prompt="Test",
                aspect_ratio="4:3",  # type: ignore[arg-type]
            )

    def test_cfg_scale_validation(self):
        """Test validation for cfg_scale constraints."""
        # Test below minimum
        with pytest.raises(ValidationError):
            KlingVideoV25TurboProTextToVideoInput(
                prompt="Test",
                cfg_scale=-0.1,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            KlingVideoV25TurboProTextToVideoInput(
                prompt="Test",
                cfg_scale=1.5,
            )

        # Test valid boundaries
        input_min = KlingVideoV25TurboProTextToVideoInput(prompt="Test", cfg_scale=0.0)
        assert input_min.cfg_scale == 0.0

        input_max = KlingVideoV25TurboProTextToVideoInput(prompt="Test", cfg_scale=1.0)
        assert input_max.cfg_scale == 1.0

    def test_prompt_max_length(self):
        """Test prompt max length validation."""
        # This should succeed (exactly at limit)
        long_prompt = "a" * 2500
        input_data = KlingVideoV25TurboProTextToVideoInput(prompt=long_prompt)
        assert len(input_data.prompt) == 2500

        # This should fail (over limit)
        too_long_prompt = "a" * 2501
        with pytest.raises(ValidationError):
            KlingVideoV25TurboProTextToVideoInput(prompt=too_long_prompt)

    def test_negative_prompt_max_length(self):
        """Test negative_prompt max length validation."""
        # This should succeed (exactly at limit)
        long_negative = "a" * 2500
        input_data = KlingVideoV25TurboProTextToVideoInput(
            prompt="test", negative_prompt=long_negative
        )
        assert len(input_data.negative_prompt) == 2500

        # This should fail (over limit)
        too_long_negative = "a" * 2501
        with pytest.raises(ValidationError):
            KlingVideoV25TurboProTextToVideoInput(prompt="test", negative_prompt=too_long_negative)

    def test_all_duration_options(self):
        """Test all valid duration options."""
        valid_durations = ["5", "10"]

        for duration in valid_durations:
            input_data = KlingVideoV25TurboProTextToVideoInput(
                prompt="Test",
                duration=duration,  # type: ignore[arg-type]
            )
            assert input_data.duration == duration

    def test_all_aspect_ratio_options(self):
        """Test all valid aspect ratio options."""
        valid_ratios = ["16:9", "9:16", "1:1"]

        for ratio in valid_ratios:
            input_data = KlingVideoV25TurboProTextToVideoInput(
                prompt="Test",
                aspect_ratio=ratio,  # type: ignore[arg-type]
            )
            assert input_data.aspect_ratio == ratio


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalKlingVideoV25TurboProTextToVideoGenerator:
    """Tests for FalKlingVideoV25TurboProTextToVideoGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalKlingVideoV25TurboProTextToVideoGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-kling-video-v2-5-turbo-pro-text-to-video"
        assert self.generator.artifact_type == "video"
        assert "text-to-video" in self.generator.description.lower()
        assert "Kling" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == KlingVideoV25TurboProTextToVideoInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = KlingVideoV25TurboProTextToVideoInput(
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
        input_data = KlingVideoV25TurboProTextToVideoInput(
            prompt="A cinematic sunset over mountains",
            duration="5",
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

            # Mock the get() method to return result
            mock_handler.get = AsyncMock(
                return_value={
                    "video": {
                        "url": fake_video_url,
                        "content_type": "video/mp4",
                        "file_name": "output.mp4",
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
                width=1920,
                height=1080,
                format="mp4",
                duration=5.0,
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
                "fal-ai/kling-video/v2.5-turbo/pro/text-to-video",
                arguments={
                    "prompt": "A cinematic sunset over mountains",
                    "duration": "5",
                    "aspect_ratio": "16:9",
                    "negative_prompt": "blur, distort, and low quality",
                    "cfg_scale": 0.5,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_successful_10_second_video_portrait(self):
        """Test successful generation with 10-second portrait video."""
        input_data = KlingVideoV25TurboProTextToVideoInput(
            prompt="A person walking through a city",
            duration="10",
            aspect_ratio="9:16",
            negative_prompt="blurry, distorted",
            cfg_scale=0.8,
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
                    }
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_video_url,
                width=1080,
                height=1920,
                format="mp4",
                duration=10.0,
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
            assert call_args[1]["arguments"]["duration"] == "10"
            assert call_args[1]["arguments"]["aspect_ratio"] == "9:16"
            assert call_args[1]["arguments"]["cfg_scale"] == 0.8

    @pytest.mark.asyncio
    async def test_generate_square_aspect_ratio(self):
        """Test generation with square (1:1) aspect ratio."""
        input_data = KlingVideoV25TurboProTextToVideoInput(
            prompt="Abstract art animation",
            aspect_ratio="1:1",
        )

        fake_video_url = "https://storage.googleapis.com/falserverless/output_square.mp4"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={"video": {"url": fake_video_url, "content_type": "video/mp4"}}
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_video_url,
                width=1080,
                height=1080,
                format="mp4",
                duration=5.0,
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
                    # Verify width and height for square format
                    assert kwargs["width"] == 1080
                    assert kwargs["height"] == 1080
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
        input_data = KlingVideoV25TurboProTextToVideoInput(
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
        input_data = KlingVideoV25TurboProTextToVideoInput(
            prompt="Test prompt",
            duration="5",
        )

        cost = await self.generator.estimate_cost(input_data)

        # 5-second video: base cost * 1.0
        assert cost == 0.15
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_10_second(self):
        """Test cost estimation for 10-second video."""
        input_data = KlingVideoV25TurboProTextToVideoInput(
            prompt="Test prompt",
            duration="10",
        )

        cost = await self.generator.estimate_cost(input_data)

        # 10-second video: base cost * 2.0
        assert cost == 0.30
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = KlingVideoV25TurboProTextToVideoInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "duration" in schema["properties"]
        assert "aspect_ratio" in schema["properties"]
        assert "negative_prompt" in schema["properties"]
        assert "cfg_scale" in schema["properties"]

        # Check prompt constraints
        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop["maxLength"] == 2500

        # Check duration enum
        duration_prop = schema["properties"]["duration"]
        assert "enum" in duration_prop or "anyOf" in duration_prop

        # Check aspect_ratio enum
        aspect_ratio_prop = schema["properties"]["aspect_ratio"]
        assert "enum" in aspect_ratio_prop or "anyOf" in aspect_ratio_prop

        # Check cfg_scale constraints
        cfg_scale_prop = schema["properties"]["cfg_scale"]
        assert cfg_scale_prop["minimum"] == 0.0
        assert cfg_scale_prop["maximum"] == 1.0
        assert cfg_scale_prop["default"] == 0.5
