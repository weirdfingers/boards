"""
Tests for FalMinimaxHailuo02StandardTextToVideoGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.fal_minimax_hailuo_02_standard_text_to_video import (  # noqa: E501
    FalMinimaxHailuo02StandardTextToVideoGenerator,
    FalMinimaxHailuo02StandardTextToVideoInput,
)


class TestFalMinimaxHailuo02StandardTextToVideoInput:
    """Tests for FalMinimaxHailuo02StandardTextToVideoInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = FalMinimaxHailuo02StandardTextToVideoInput(
            prompt="A Galactic Smuggler walks through a neon-lit cyberpunk city",
            duration="10",
            prompt_optimizer=False,
        )

        assert input_data.prompt == "A Galactic Smuggler walks through a neon-lit cyberpunk city"
        assert input_data.duration == "10"
        assert input_data.prompt_optimizer is False

    def test_input_defaults(self):
        """Test default values."""
        input_data = FalMinimaxHailuo02StandardTextToVideoInput(
            prompt="Test prompt",
        )

        assert input_data.duration == "6"
        assert input_data.prompt_optimizer is True

    def test_invalid_duration(self):
        """Test validation fails for invalid duration."""
        with pytest.raises(ValidationError):
            FalMinimaxHailuo02StandardTextToVideoInput(
                prompt="Test",
                duration="15",  # type: ignore[arg-type]
            )

    def test_prompt_min_length(self):
        """Test prompt min length validation."""
        # Empty string should fail
        with pytest.raises(ValidationError):
            FalMinimaxHailuo02StandardTextToVideoInput(prompt="")

    def test_prompt_max_length(self):
        """Test prompt max length validation."""
        # This should succeed (exactly at limit)
        long_prompt = "a" * 2000
        input_data = FalMinimaxHailuo02StandardTextToVideoInput(prompt=long_prompt)
        assert len(input_data.prompt) == 2000

        # This should fail (over limit)
        too_long_prompt = "a" * 2001
        with pytest.raises(ValidationError):
            FalMinimaxHailuo02StandardTextToVideoInput(prompt=too_long_prompt)

    def test_all_duration_options(self):
        """Test all valid duration options."""
        valid_durations = ["6", "10"]

        for duration in valid_durations:
            input_data = FalMinimaxHailuo02StandardTextToVideoInput(
                prompt="Test",
                duration=duration,  # type: ignore[arg-type]
            )
            assert input_data.duration == duration

    def test_prompt_optimizer_boolean(self):
        """Test prompt_optimizer accepts boolean values."""
        # Test True
        input_true = FalMinimaxHailuo02StandardTextToVideoInput(
            prompt="Test", prompt_optimizer=True
        )
        assert input_true.prompt_optimizer is True

        # Test False
        input_false = FalMinimaxHailuo02StandardTextToVideoInput(
            prompt="Test", prompt_optimizer=False
        )
        assert input_false.prompt_optimizer is False


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalMinimaxHailuo02StandardTextToVideoGenerator:
    """Tests for FalMinimaxHailuo02StandardTextToVideoGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalMinimaxHailuo02StandardTextToVideoGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-minimax-hailuo-02-standard-text-to-video"
        assert self.generator.artifact_type == "video"
        assert "text-to-video" in self.generator.description.lower()
        assert "Hailuo" in self.generator.description or "MiniMax" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == FalMinimaxHailuo02StandardTextToVideoInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = FalMinimaxHailuo02StandardTextToVideoInput(
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
                        duration=6.0,
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
    async def test_generate_successful_6_second_video(self):
        """Test successful generation with 6-second video (default)."""
        input_data = FalMinimaxHailuo02StandardTextToVideoInput(
            prompt="A beautiful landscape with rolling hills",
            duration="6",
        )

        fake_video_url = "https://v3.fal.media/files/kangaroo/test_output.mp4"

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
                        "file_size": 4404019,
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
                width=1360,
                height=768,
                format="mp4",
                duration=6.0,
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
                "fal-ai/minimax/hailuo-02/standard/text-to-video",
                arguments={
                    "prompt": "A beautiful landscape with rolling hills",
                    "duration": "6",
                    "prompt_optimizer": True,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_successful_10_second_video(self):
        """Test successful generation with 10-second video."""
        input_data = FalMinimaxHailuo02StandardTextToVideoInput(
            prompt="A spaceship flying through stars",
            duration="10",
            prompt_optimizer=False,
        )

        fake_video_url = "https://v3.fal.media/files/kangaroo/test_output_10s.mp4"

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
                width=1360,
                height=768,
                format="mp4",
                duration=10.0,
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
                    # Verify correct dimensions for 768p
                    assert kwargs["width"] == 1360
                    assert kwargs["height"] == 768
                    assert kwargs["duration"] == 10.0
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
            assert call_args[1]["arguments"]["prompt_optimizer"] is False

    @pytest.mark.asyncio
    async def test_generate_no_video_returned(self):
        """Test generation fails when API returns no video."""
        input_data = FalMinimaxHailuo02StandardTextToVideoInput(
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
    async def test_generate_no_video_url(self):
        """Test generation fails when video has no URL."""
        input_data = FalMinimaxHailuo02StandardTextToVideoInput(
            prompt="test",
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-error"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={"video": {"content_type": "video/mp4"}}  # No URL
            )

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

            with pytest.raises(ValueError, match="Video missing URL"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_estimate_cost_6_second(self):
        """Test cost estimation for 6-second video."""
        input_data = FalMinimaxHailuo02StandardTextToVideoInput(
            prompt="Test prompt",
            duration="6",
        )

        cost = await self.generator.estimate_cost(input_data)

        # 6-second video: base cost * 1.0
        assert cost == 0.12
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_10_second(self):
        """Test cost estimation for 10-second video."""
        input_data = FalMinimaxHailuo02StandardTextToVideoInput(
            prompt="Test prompt",
            duration="10",
        )

        cost = await self.generator.estimate_cost(input_data)

        # 10-second video: base cost * 1.67
        expected_cost = 0.12 * 1.67
        assert cost == expected_cost
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = FalMinimaxHailuo02StandardTextToVideoInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "duration" in schema["properties"]
        assert "prompt_optimizer" in schema["properties"]

        # Check prompt constraints
        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop["minLength"] == 1
        assert prompt_prop["maxLength"] == 2000

        # Check duration enum
        duration_prop = schema["properties"]["duration"]
        assert "enum" in duration_prop or "anyOf" in duration_prop

        # Check prompt_optimizer default
        prompt_optimizer_prop = schema["properties"]["prompt_optimizer"]
        assert prompt_optimizer_prop["default"] is True
