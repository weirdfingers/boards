"""
Tests for FalBytedanceSeedanceV15ProTextToVideoGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.fal_bytedance_seedance_v1_5_pro_text_to_video import (  # noqa: E501
    BytedanceSeedanceV15ProTextToVideoInput,
    FalBytedanceSeedanceV15ProTextToVideoGenerator,
)


class TestBytedanceSeedanceV15ProTextToVideoInput:
    """Tests for BytedanceSeedanceV15ProTextToVideoInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = BytedanceSeedanceV15ProTextToVideoInput(
            prompt="A skier glides over fresh snow",
            aspect_ratio="16:9",
            resolution="720p",
            duration=5,
            generate_audio=True,
            camera_fixed=False,
            seed=42,
        )

        assert input_data.prompt == "A skier glides over fresh snow"
        assert input_data.aspect_ratio == "16:9"
        assert input_data.resolution == "720p"
        assert input_data.duration == 5
        assert input_data.generate_audio is True
        assert input_data.enable_safety_checker is True
        assert input_data.camera_fixed is False
        assert input_data.seed == 42

    def test_input_defaults(self):
        """Test default values."""
        input_data = BytedanceSeedanceV15ProTextToVideoInput(
            prompt="Test prompt",
        )

        assert input_data.aspect_ratio == "16:9"
        assert input_data.resolution == "720p"
        assert input_data.duration == 5
        assert input_data.generate_audio is True
        assert input_data.enable_safety_checker is True
        assert input_data.camera_fixed is False
        assert input_data.seed is None

    def test_invalid_aspect_ratio(self):
        """Test validation fails for invalid aspect ratio."""
        with pytest.raises(ValidationError):
            BytedanceSeedanceV15ProTextToVideoInput(
                prompt="Test",
                aspect_ratio="auto",  # type: ignore[arg-type]
            )

    def test_invalid_resolution(self):
        """Test validation fails for invalid resolution."""
        with pytest.raises(ValidationError):
            BytedanceSeedanceV15ProTextToVideoInput(
                prompt="Test",
                resolution="4k",  # type: ignore[arg-type]
            )

    def test_invalid_duration_too_low(self):
        """Test validation fails for duration below minimum."""
        with pytest.raises(ValidationError):
            BytedanceSeedanceV15ProTextToVideoInput(
                prompt="Test",
                duration=2,
            )

    def test_invalid_duration_too_high(self):
        """Test validation fails for duration above maximum."""
        with pytest.raises(ValidationError):
            BytedanceSeedanceV15ProTextToVideoInput(
                prompt="Test",
                duration=15,
            )

    def test_aspect_ratio_options(self):
        """Test all valid aspect ratio options."""
        valid_ratios = ["21:9", "16:9", "4:3", "1:1", "3:4", "9:16"]

        for ratio in valid_ratios:
            input_data = BytedanceSeedanceV15ProTextToVideoInput(
                prompt="Test",
                aspect_ratio=ratio,  # type: ignore[arg-type]
            )
            assert input_data.aspect_ratio == ratio

    def test_resolution_options(self):
        """Test all valid resolution options."""
        valid_resolutions = ["480p", "720p", "1080p"]

        for resolution in valid_resolutions:
            input_data = BytedanceSeedanceV15ProTextToVideoInput(
                prompt="Test",
                resolution=resolution,  # type: ignore[arg-type]
            )
            assert input_data.resolution == resolution

    def test_duration_range(self):
        """Test valid duration values (4-12)."""
        for duration in range(4, 13):
            input_data = BytedanceSeedanceV15ProTextToVideoInput(
                prompt="Test",
                duration=duration,
            )
            assert input_data.duration == duration


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalBytedanceSeedanceV15ProTextToVideoGenerator:
    """Tests for FalBytedanceSeedanceV15ProTextToVideoGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalBytedanceSeedanceV15ProTextToVideoGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-bytedance-seedance-v1-5-pro-text-to-video"
        assert self.generator.artifact_type == "video"
        assert "SeedDance" in self.generator.description
        assert "v1.5" in self.generator.description
        assert "text-to-video" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == BytedanceSeedanceV15ProTextToVideoInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = BytedanceSeedanceV15ProTextToVideoInput(
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
                        duration=1,
                        format="mp4",
                        fps=None,
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
    async def test_generate_successful_720p(self):
        """Test successful generation with 720p resolution."""
        input_data = BytedanceSeedanceV15ProTextToVideoInput(
            prompt="A skier glides over fresh snow",
            resolution="720p",
            aspect_ratio="16:9",
            duration=5,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.mp4"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            # Create mock handler with async iterator for events
            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-123"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "video": {
                        "url": fake_output_url,
                        "content_type": "video/mp4",
                        "file_name": "output.mp4",
                        "file_size": 2048000,
                    },
                    "seed": 12345,
                }
            )

            # Create mock fal_client module
            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            # Mock storage result
            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1280,
                height=720,
                duration=5,
                format="mp4",
                fps=None,
            )

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return "/tmp/fake_image.png"

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
                "fal-ai/bytedance/seedance/v1.5/pro/text-to-video",
                arguments={
                    "prompt": "A skier glides over fresh snow",
                    "aspect_ratio": "16:9",
                    "resolution": "720p",
                    "duration": 5,
                    "generate_audio": True,
                    "enable_safety_checker": True,
                    "camera_fixed": False,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_with_seed_and_1080p(self):
        """Test successful generation with seed and 1080p resolution."""
        input_data = BytedanceSeedanceV15ProTextToVideoInput(
            prompt="Ocean waves at sunset",
            resolution="1080p",
            aspect_ratio="21:9",
            duration=8,
            seed=42,
            generate_audio=False,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.mp4"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-456"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "video": {"url": fake_output_url, "content_type": "video/mp4"},
                    "seed": 42,
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=2520,
                height=1080,
                duration=8,
                format="mp4",
                fps=None,
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
            assert len(result.outputs) == 1

            # Verify API call includes seed and audio disabled
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["seed"] == 42
            assert call_args[1]["arguments"]["generate_audio"] is False
            assert call_args[1]["arguments"]["duration"] == 8
            assert call_args[1]["arguments"]["resolution"] == "1080p"

    @pytest.mark.asyncio
    async def test_generate_no_video_returned(self):
        """Test generation fails when API returns no video."""
        input_data = BytedanceSeedanceV15ProTextToVideoInput(
            prompt="test",
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={})  # No video field

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
    async def test_estimate_cost_720p_5s_with_audio(self):
        """Test cost estimation for 720p 5-second video with audio."""
        input_data = BytedanceSeedanceV15ProTextToVideoInput(
            prompt="Test prompt",
            resolution="720p",
            duration=5,
            generate_audio=True,
        )

        cost = await self.generator.estimate_cost(input_data)

        # tokens = (1280 * 720 * 30 * 5) / 1024 = 135000
        # cost = (135000 / 1_000_000) * 2.4 = 0.324
        expected_cost = 0.324
        assert abs(cost - expected_cost) < 0.001
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_720p_5s_without_audio(self):
        """Test cost estimation for 720p 5-second video without audio."""
        input_data = BytedanceSeedanceV15ProTextToVideoInput(
            prompt="Test prompt",
            resolution="720p",
            duration=5,
            generate_audio=False,
        )

        cost = await self.generator.estimate_cost(input_data)

        # tokens = (1280 * 720 * 30 * 5) / 1024 = 135000
        # cost = (135000 / 1_000_000) * 1.2 = 0.162
        expected_cost = 0.162
        assert abs(cost - expected_cost) < 0.001
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_1080p_12s(self):
        """Test cost estimation for 1080p 12-second video with audio."""
        input_data = BytedanceSeedanceV15ProTextToVideoInput(
            prompt="Test prompt",
            resolution="1080p",
            duration=12,
        )

        cost = await self.generator.estimate_cost(input_data)

        # tokens = (1920 * 1080 * 30 * 12) / 1024 = 729000
        # cost = (729000 / 1_000_000) * 2.4 = 1.7496
        expected_cost = 1.7496
        assert abs(cost - expected_cost) < 0.01
        assert isinstance(cost, float)

    def test_calculate_dimensions(self):
        """Test dimension calculation for various aspect ratios."""
        gen = FalBytedanceSeedanceV15ProTextToVideoGenerator()

        assert gen._calculate_dimensions("16:9", "1080p") == (1920, 1080)
        assert gen._calculate_dimensions("16:9", "720p") == (1280, 720)
        assert gen._calculate_dimensions("16:9", "480p") == (853, 480)
        assert gen._calculate_dimensions("1:1", "720p") == (720, 720)
        assert gen._calculate_dimensions("9:16", "720p") == (405, 720)
        assert gen._calculate_dimensions("21:9", "1080p") == (2520, 1080)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = BytedanceSeedanceV15ProTextToVideoInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "aspect_ratio" in schema["properties"]
        assert "resolution" in schema["properties"]
        assert "duration" in schema["properties"]
        assert "generate_audio" in schema["properties"]
        assert "enable_safety_checker" in schema["properties"]
        assert "camera_fixed" in schema["properties"]
        assert "seed" in schema["properties"]

        # Check that only prompt is required
        assert schema["required"] == ["prompt"]

        # Check defaults
        assert schema["properties"]["aspect_ratio"]["default"] == "16:9"
        assert schema["properties"]["resolution"]["default"] == "720p"
        assert schema["properties"]["duration"]["default"] == 5
        assert schema["properties"]["generate_audio"]["default"] is True
        assert schema["properties"]["enable_safety_checker"]["default"] is True
        assert schema["properties"]["camera_fixed"]["default"] is False
