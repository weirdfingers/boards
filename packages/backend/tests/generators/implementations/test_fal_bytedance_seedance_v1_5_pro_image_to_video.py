"""
Tests for FalBytedanceSeedanceV15ProImageToVideoGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact, VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.fal_bytedance_seedance_v1_5_pro_image_to_video import (  # noqa: E501
    BytedanceSeedanceV15ProImageToVideoInput,
    FalBytedanceSeedanceV15ProImageToVideoGenerator,
)


class TestBytedanceSeedanceV15ProImageToVideoInput:
    """Tests for BytedanceSeedanceV15ProImageToVideoInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1920,
            height=1080,
        )

        input_data = BytedanceSeedanceV15ProImageToVideoInput(
            prompt="A skier glides over fresh snow",
            image=image,
            aspect_ratio="16:9",
            resolution="720p",
            duration=5,
            generate_audio=True,
            camera_fixed=False,
            seed=42,
        )

        assert input_data.prompt == "A skier glides over fresh snow"
        assert input_data.image == image
        assert input_data.aspect_ratio == "16:9"
        assert input_data.resolution == "720p"
        assert input_data.duration == 5
        assert input_data.generate_audio is True
        assert input_data.camera_fixed is False
        assert input_data.seed == 42
        assert input_data.end_image is None

    def test_input_defaults(self):
        """Test default values."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = BytedanceSeedanceV15ProImageToVideoInput(
            prompt="Test prompt",
            image=image,
        )

        assert input_data.aspect_ratio == "16:9"
        assert input_data.resolution == "720p"
        assert input_data.duration == 5
        assert input_data.generate_audio is True
        assert input_data.camera_fixed is False
        assert input_data.seed is None
        assert input_data.end_image is None

    def test_input_with_end_image(self):
        """Test input with optional end image."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )
        end_image = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/end.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = BytedanceSeedanceV15ProImageToVideoInput(
            prompt="Smooth transition",
            image=image,
            end_image=end_image,
        )

        assert input_data.end_image == end_image

    def test_invalid_aspect_ratio(self):
        """Test validation fails for invalid aspect ratio."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        with pytest.raises(ValidationError):
            BytedanceSeedanceV15ProImageToVideoInput(
                prompt="Test",
                image=image,
                aspect_ratio="auto",  # type: ignore[arg-type]
            )

    def test_invalid_resolution(self):
        """Test validation fails for invalid resolution."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        with pytest.raises(ValidationError):
            BytedanceSeedanceV15ProImageToVideoInput(
                prompt="Test",
                image=image,
                resolution="1080p",  # type: ignore[arg-type]
            )

    def test_invalid_duration_too_low(self):
        """Test validation fails for duration below minimum."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        with pytest.raises(ValidationError):
            BytedanceSeedanceV15ProImageToVideoInput(
                prompt="Test",
                image=image,
                duration=2,
            )

    def test_invalid_duration_too_high(self):
        """Test validation fails for duration above maximum."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        with pytest.raises(ValidationError):
            BytedanceSeedanceV15ProImageToVideoInput(
                prompt="Test",
                image=image,
                duration=15,
            )

    def test_aspect_ratio_options(self):
        """Test all valid aspect ratio options."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        valid_ratios = ["21:9", "16:9", "4:3", "1:1", "3:4", "9:16"]

        for ratio in valid_ratios:
            input_data = BytedanceSeedanceV15ProImageToVideoInput(
                prompt="Test",
                image=image,
                aspect_ratio=ratio,  # type: ignore[arg-type]
            )
            assert input_data.aspect_ratio == ratio

    def test_resolution_options(self):
        """Test all valid resolution options."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        valid_resolutions = ["480p", "720p"]

        for resolution in valid_resolutions:
            input_data = BytedanceSeedanceV15ProImageToVideoInput(
                prompt="Test",
                image=image,
                resolution=resolution,  # type: ignore[arg-type]
            )
            assert input_data.resolution == resolution

    def test_duration_range(self):
        """Test valid duration values (4-12)."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        for duration in range(4, 13):
            input_data = BytedanceSeedanceV15ProImageToVideoInput(
                prompt="Test",
                image=image,
                duration=duration,
            )
            assert input_data.duration == duration


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalBytedanceSeedanceV15ProImageToVideoGenerator:
    """Tests for FalBytedanceSeedanceV15ProImageToVideoGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalBytedanceSeedanceV15ProImageToVideoGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-bytedance-seedance-v1-5-pro-image-to-video"
        assert self.generator.artifact_type == "video"
        assert "SeedDance" in self.generator.description
        assert "v1.5" in self.generator.description
        assert "image-to-video" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == BytedanceSeedanceV15ProImageToVideoInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            image = ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/image.png",
                format="png",
                width=1024,
                height=768,
            )

            input_data = BytedanceSeedanceV15ProImageToVideoInput(
                prompt="Test prompt",
                image=image,
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
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1280,
            height=720,
        )

        input_data = BytedanceSeedanceV15ProImageToVideoInput(
            prompt="A skier glides over fresh snow",
            image=image,
            resolution="720p",
            aspect_ratio="16:9",
            duration=5,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.mp4"
        fake_uploaded_image = "https://fal.media/files/image.png"

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
                        "url": fake_output_url,
                        "content_type": "video/mp4",
                        "file_name": "output.mp4",
                        "file_size": 2048000,
                    },
                    "seed": 12345,
                }
            )

            # Mock file upload
            async def mock_upload(file_path):
                return fake_uploaded_image

            # Create mock fal_client module
            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]

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

            # Execute generation
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

            # Verify file upload was called
            assert mock_fal_client.upload_file_async.call_count == 1

            # Verify API call with uploaded URL
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/bytedance/seedance/v1.5/pro/image-to-video",
                arguments={
                    "prompt": "A skier glides over fresh snow",
                    "image_url": fake_uploaded_image,
                    "aspect_ratio": "16:9",
                    "resolution": "720p",
                    "duration": 5,
                    "generate_audio": True,
                    "camera_fixed": False,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_with_end_image(self):
        """Test successful generation with end image."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1280,
            height=720,
        )
        end_image = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/end.png",
            format="png",
            width=1280,
            height=720,
        )

        input_data = BytedanceSeedanceV15ProImageToVideoInput(
            prompt="Smooth transition",
            image=image,
            end_image=end_image,
            resolution="720p",
            duration=8,
            seed=42,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.mp4"
        fake_uploaded_urls = [
            "https://fal.media/files/image.png",
            "https://fal.media/files/end.png",
        ]

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-456"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "video": {
                        "url": fake_output_url,
                        "content_type": "video/mp4",
                    },
                    "seed": 42,
                }
            )

            upload_call_count = 0

            async def mock_upload(file_path):
                nonlocal upload_call_count
                url = fake_uploaded_urls[upload_call_count]
                upload_call_count += 1
                return url

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1280,
                height=720,
                duration=8,
                format="mp4",
                fps=None,
            )

            resolve_call_count = 0

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    nonlocal resolve_call_count
                    path = f"/tmp/fake_image_{resolve_call_count}.png"
                    resolve_call_count += 1
                    return path

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

            # Verify file uploads were called for both images
            assert mock_fal_client.upload_file_async.call_count == 2

            # Verify API call includes end_image_url and seed
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["end_image_url"] == fake_uploaded_urls[1]
            assert call_args[1]["arguments"]["seed"] == 42
            assert call_args[1]["arguments"]["duration"] == 8

    @pytest.mark.asyncio
    async def test_generate_without_audio(self):
        """Test generation with audio disabled."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1280,
            height=720,
        )

        input_data = BytedanceSeedanceV15ProImageToVideoInput(
            prompt="Silent scene",
            image=image,
            generate_audio=False,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.mp4"
        fake_uploaded_image = "https://fal.media/files/image.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "video": {"url": fake_output_url, "content_type": "video/mp4"},
                    "seed": 99,
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(return_value=fake_uploaded_image)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

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

            await self.generator.generate(input_data, DummyCtx())

            # Verify generate_audio=False was passed
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["generate_audio"] is False

    @pytest.mark.asyncio
    async def test_generate_no_video_returned(self):
        """Test generation fails when API returns no video."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = BytedanceSeedanceV15ProImageToVideoInput(
            prompt="test",
            image=image,
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={})  # No video field

            fake_uploaded_url = "https://fal.media/files/image.png"

            async def mock_upload(file_path):
                return fake_uploaded_url

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]
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
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1280,
            height=720,
        )

        input_data = BytedanceSeedanceV15ProImageToVideoInput(
            prompt="Test prompt",
            image=image,
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
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1280,
            height=720,
        )

        input_data = BytedanceSeedanceV15ProImageToVideoInput(
            prompt="Test prompt",
            image=image,
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
    async def test_estimate_cost_480p_12s(self):
        """Test cost estimation for 480p 12-second video with audio."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=854,
            height=480,
        )

        input_data = BytedanceSeedanceV15ProImageToVideoInput(
            prompt="Test prompt",
            image=image,
            resolution="480p",
            duration=12,
        )

        cost = await self.generator.estimate_cost(input_data)

        # tokens = (854 * 480 * 30 * 12) / 1024 = 144506.25
        # cost = (144506.25 / 1_000_000) * 2.4 = 0.346815
        expected_cost = 0.346815
        assert abs(cost - expected_cost) < 0.001
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = BytedanceSeedanceV15ProImageToVideoInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "image" in schema["properties"]
        assert "aspect_ratio" in schema["properties"]
        assert "resolution" in schema["properties"]
        assert "duration" in schema["properties"]
        assert "end_image" in schema["properties"]
        assert "generate_audio" in schema["properties"]
        assert "camera_fixed" in schema["properties"]
        assert "seed" in schema["properties"]

        # Check that required fields are marked
        assert set(schema["required"]) == {"prompt", "image"}

        # Check defaults
        assert schema["properties"]["aspect_ratio"]["default"] == "16:9"
        assert schema["properties"]["resolution"]["default"] == "720p"
        assert schema["properties"]["duration"]["default"] == 5
        assert schema["properties"]["generate_audio"]["default"] is True
        assert schema["properties"]["camera_fixed"]["default"] is False
