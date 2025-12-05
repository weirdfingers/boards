"""
Tests for FalBytedanceSeedanceV1ProTextToVideoGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.bytedance_seedance_v1_pro_text_to_video import (
    BytedanceSeedanceV1ProTextToVideoInput,
    FalBytedanceSeedanceV1ProTextToVideoGenerator,
)


class TestBytedanceSeedanceV1ProTextToVideoInput:
    """Tests for BytedanceSeedanceV1ProTextToVideoInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        input_data = BytedanceSeedanceV1ProTextToVideoInput(
            prompt="A bright blue race car speeds along a snowy racetrack",
            aspect_ratio="16:9",
            resolution="1080p",
            duration="5",
            enable_safety_checker=True,
            camera_fixed=False,
            seed=12345,
        )

        assert input_data.prompt == "A bright blue race car speeds along a snowy racetrack"
        assert input_data.aspect_ratio == "16:9"
        assert input_data.resolution == "1080p"
        assert input_data.duration == "5"
        assert input_data.enable_safety_checker is True
        assert input_data.camera_fixed is False
        assert input_data.seed == 12345

    def test_input_defaults(self):
        """Test default values."""
        input_data = BytedanceSeedanceV1ProTextToVideoInput(
            prompt="Test prompt",
        )

        assert input_data.aspect_ratio == "16:9"
        assert input_data.resolution == "1080p"
        assert input_data.duration == "5"
        assert input_data.enable_safety_checker is True
        assert input_data.camera_fixed is False
        assert input_data.seed is None

    def test_invalid_aspect_ratio(self):
        """Test validation fails for invalid aspect ratio."""
        with pytest.raises(ValidationError):
            BytedanceSeedanceV1ProTextToVideoInput(
                prompt="Test",
                aspect_ratio="32:9",  # type: ignore[arg-type]
            )

    def test_invalid_resolution(self):
        """Test validation fails for invalid resolution."""
        with pytest.raises(ValidationError):
            BytedanceSeedanceV1ProTextToVideoInput(
                prompt="Test",
                resolution="2160p",  # type: ignore[arg-type]
            )

    def test_invalid_duration(self):
        """Test validation fails for invalid duration."""
        with pytest.raises(ValidationError):
            BytedanceSeedanceV1ProTextToVideoInput(
                prompt="Test",
                duration="15",  # type: ignore[arg-type]
            )

        with pytest.raises(ValidationError):
            BytedanceSeedanceV1ProTextToVideoInput(
                prompt="Test",
                duration="1",  # type: ignore[arg-type]
            )

    def test_all_aspect_ratio_options(self):
        """Test all valid aspect ratio options."""
        valid_ratios = ["21:9", "16:9", "4:3", "1:1", "3:4", "9:16"]

        for ratio in valid_ratios:
            input_data = BytedanceSeedanceV1ProTextToVideoInput(
                prompt="Test",
                aspect_ratio=ratio,  # type: ignore[arg-type]
            )
            assert input_data.aspect_ratio == ratio

    def test_all_resolution_options(self):
        """Test all valid resolution options."""
        valid_resolutions = ["480p", "720p", "1080p"]

        for resolution in valid_resolutions:
            input_data = BytedanceSeedanceV1ProTextToVideoInput(
                prompt="Test",
                resolution=resolution,  # type: ignore[arg-type]
            )
            assert input_data.resolution == resolution

    def test_all_duration_options(self):
        """Test all valid duration options (2-12 seconds)."""
        valid_durations = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]

        for duration in valid_durations:
            input_data = BytedanceSeedanceV1ProTextToVideoInput(
                prompt="Test",
                duration=duration,  # type: ignore[arg-type]
            )
            assert input_data.duration == duration

    def test_seed_optional(self):
        """Test seed is optional and can be None."""
        input_data = BytedanceSeedanceV1ProTextToVideoInput(
            prompt="Test",
        )
        assert input_data.seed is None

        input_data_with_seed = BytedanceSeedanceV1ProTextToVideoInput(
            prompt="Test",
            seed=-1,  # -1 for randomization
        )
        assert input_data_with_seed.seed == -1


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalBytedanceSeedanceV1ProTextToVideoGenerator:
    """Tests for FalBytedanceSeedanceV1ProTextToVideoGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalBytedanceSeedanceV1ProTextToVideoGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-bytedance-seedance-v1-pro-text-to-video"
        assert self.generator.artifact_type == "video"
        assert "text-to-video" in self.generator.description.lower()
        assert "Seedance" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == BytedanceSeedanceV1ProTextToVideoInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = BytedanceSeedanceV1ProTextToVideoInput(
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
    async def test_generate_successful_default_settings(self):
        """Test successful generation with default settings."""
        input_data = BytedanceSeedanceV1ProTextToVideoInput(
            prompt="A bright blue race car speeds along a snowy racetrack",
        )

        fake_video_url = "https://storage.googleapis.com/falserverless/output.mp4"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            # Create mock handler
            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-123"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "video": {
                        "url": fake_video_url,
                        "content_type": "video/mp4",
                        "file_name": "output.mp4",
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

            # Verify API call (seed should not be included when None)
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/bytedance/seedance/v1/pro/text-to-video",
                arguments={
                    "prompt": "A bright blue race car speeds along a snowy racetrack",
                    "aspect_ratio": "16:9",
                    "resolution": "1080p",
                    "duration": "5",
                    "enable_safety_checker": True,
                    "camera_fixed": False,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_with_all_options(self):
        """Test generation with all custom options."""
        input_data = BytedanceSeedanceV1ProTextToVideoInput(
            prompt="A cinematic sunset over mountains",
            aspect_ratio="21:9",
            resolution="720p",
            duration="10",
            enable_safety_checker=False,
            camera_fixed=True,
            seed=99999,
        )

        fake_video_url = "https://storage.googleapis.com/falserverless/output_custom.mp4"

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
                    },
                    "seed": 99999,
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            # Calculate expected dimensions: 21:9 at 720p
            # Height = 720, Width = 720 * 21 / 9 = 1680
            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_video_url,
                width=1680,
                height=720,
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
                    # Verify dimensions calculation
                    assert kwargs["width"] == 1680
                    assert kwargs["height"] == 720
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

            # Verify API call includes seed
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["seed"] == 99999
            assert call_args[1]["arguments"]["aspect_ratio"] == "21:9"
            assert call_args[1]["arguments"]["resolution"] == "720p"
            assert call_args[1]["arguments"]["duration"] == "10"
            assert call_args[1]["arguments"]["enable_safety_checker"] is False
            assert call_args[1]["arguments"]["camera_fixed"] is True

    @pytest.mark.asyncio
    async def test_generate_portrait_video(self):
        """Test generation with portrait (9:16) aspect ratio."""
        input_data = BytedanceSeedanceV1ProTextToVideoInput(
            prompt="A person walking through a city",
            aspect_ratio="9:16",
            resolution="1080p",
        )

        fake_video_url = "https://storage.googleapis.com/falserverless/output_portrait.mp4"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-portrait"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={"video": {"url": fake_video_url}, "seed": 1})

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            # Expected dimensions: 9:16 at 1080p
            # Height = 1080, Width = 1080 * 9 / 16 = 607.5 = 607
            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_video_url,
                width=607,
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
                    assert kwargs["width"] == 607
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
    async def test_generate_square_aspect_ratio(self):
        """Test generation with square (1:1) aspect ratio."""
        input_data = BytedanceSeedanceV1ProTextToVideoInput(
            prompt="Abstract art animation",
            aspect_ratio="1:1",
            resolution="480p",
        )

        fake_video_url = "https://storage.googleapis.com/falserverless/output_square.mp4"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-square"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={"video": {"url": fake_video_url}, "seed": 1})

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            # Expected dimensions: 1:1 at 480p = 480x480
            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_video_url,
                width=480,
                height=480,
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
                    assert kwargs["width"] == 480
                    assert kwargs["height"] == 480
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
        input_data = BytedanceSeedanceV1ProTextToVideoInput(
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
    async def test_estimate_cost_default_settings(self):
        """Test cost estimation with default settings."""
        input_data = BytedanceSeedanceV1ProTextToVideoInput(
            prompt="Test prompt",
        )

        cost = await self.generator.estimate_cost(input_data)

        # 5-second video, 1080p: base_cost * 1.0 * 1.3 = 0.12 * 1.0 * 1.3 = 0.156
        expected_cost = 0.12 * 1.0 * 1.3
        assert cost == pytest.approx(expected_cost)
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_longer_duration(self):
        """Test cost estimation for longer duration video."""
        input_data = BytedanceSeedanceV1ProTextToVideoInput(
            prompt="Test prompt",
            duration="12",  # Maximum duration
        )

        cost = await self.generator.estimate_cost(input_data)

        # 12-second video, 1080p: base_cost * (1.0 + (12-5)*0.05) * 1.3
        # = 0.12 * 1.35 * 1.3 = 0.2106
        expected_cost = 0.12 * 1.35 * 1.3
        assert cost == pytest.approx(expected_cost)
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_lower_resolution(self):
        """Test cost estimation for lower resolution."""
        input_data = BytedanceSeedanceV1ProTextToVideoInput(
            prompt="Test prompt",
            resolution="480p",
            duration="2",  # Minimum duration
        )

        cost = await self.generator.estimate_cost(input_data)

        # 2-second video, 480p: base_cost * (1.0 + (2-5)*0.05) * 0.8
        # = 0.12 * 0.85 * 0.8 = 0.0816
        expected_cost = 0.12 * 0.85 * 0.8
        assert cost == pytest.approx(expected_cost)
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_720p(self):
        """Test cost estimation for 720p resolution."""
        input_data = BytedanceSeedanceV1ProTextToVideoInput(
            prompt="Test prompt",
            resolution="720p",
        )

        cost = await self.generator.estimate_cost(input_data)

        # 5-second video, 720p: base_cost * 1.0 * 1.0 = 0.12
        expected_cost = 0.12 * 1.0 * 1.0
        assert cost == pytest.approx(expected_cost)
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = BytedanceSeedanceV1ProTextToVideoInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "aspect_ratio" in schema["properties"]
        assert "resolution" in schema["properties"]
        assert "duration" in schema["properties"]
        assert "enable_safety_checker" in schema["properties"]
        assert "camera_fixed" in schema["properties"]
        assert "seed" in schema["properties"]

        # Check aspect_ratio enum
        aspect_ratio_prop = schema["properties"]["aspect_ratio"]
        assert "enum" in aspect_ratio_prop or "anyOf" in aspect_ratio_prop

        # Check resolution enum
        resolution_prop = schema["properties"]["resolution"]
        assert "enum" in resolution_prop or "anyOf" in resolution_prop

        # Check duration enum
        duration_prop = schema["properties"]["duration"]
        assert "enum" in duration_prop or "anyOf" in duration_prop

    def test_calculate_dimensions(self):
        """Test dimension calculation for various aspect ratios and resolutions."""
        # Test 16:9 at different resolutions
        assert self.generator._calculate_dimensions("16:9", "1080p") == (1920, 1080)
        assert self.generator._calculate_dimensions("16:9", "720p") == (1280, 720)
        assert self.generator._calculate_dimensions("16:9", "480p") == (853, 480)

        # Test 21:9 ultrawide
        assert self.generator._calculate_dimensions("21:9", "1080p") == (2520, 1080)

        # Test portrait 9:16
        assert self.generator._calculate_dimensions("9:16", "1080p") == (607, 1080)

        # Test square 1:1
        assert self.generator._calculate_dimensions("1:1", "1080p") == (1080, 1080)
        assert self.generator._calculate_dimensions("1:1", "720p") == (720, 720)
        assert self.generator._calculate_dimensions("1:1", "480p") == (480, 480)

        # Test 4:3
        assert self.generator._calculate_dimensions("4:3", "720p") == (960, 720)

        # Test 3:4 portrait
        assert self.generator._calculate_dimensions("3:4", "720p") == (540, 720)
