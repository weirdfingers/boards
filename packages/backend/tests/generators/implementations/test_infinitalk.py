"""
Tests for FalInfinitalkGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import AudioArtifact, ImageArtifact, VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.video.infinitalk import (
    FalInfinitalkGenerator,
    InfinitalkInput,
)


class TestInfinitalkInput:
    """Tests for InfinitalkInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
            duration=10.0,
            sample_rate=44100,
            channels=2,
        )

        input_data = InfinitalkInput(
            image=image_artifact,
            audio=audio_artifact,
            prompt="Test prompt",
            num_frames=200,
            resolution="720p",
            acceleration="high",
            seed=123,
        )

        assert input_data.image == image_artifact
        assert input_data.audio == audio_artifact
        assert input_data.prompt == "Test prompt"
        assert input_data.num_frames == 200
        assert input_data.resolution == "720p"
        assert input_data.acceleration == "high"
        assert input_data.seed == 123

    def test_input_defaults(self):
        """Test default values."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        input_data = InfinitalkInput(
            image=image_artifact,
            audio=audio_artifact,
            prompt="Test prompt",
        )

        assert input_data.num_frames == 145
        assert input_data.resolution == "480p"
        assert input_data.acceleration == "regular"
        assert input_data.seed == 42

    def test_invalid_resolution(self):
        """Test validation fails for invalid resolution."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        with pytest.raises(ValidationError):
            InfinitalkInput(
                image=image_artifact,
                audio=audio_artifact,
                prompt="Test prompt",
                resolution="1080p",  # type: ignore[arg-type]
            )

    def test_invalid_acceleration(self):
        """Test validation fails for invalid acceleration."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        with pytest.raises(ValidationError):
            InfinitalkInput(
                image=image_artifact,
                audio=audio_artifact,
                prompt="Test prompt",
                acceleration="super-fast",  # type: ignore[arg-type]
            )

    def test_num_frames_below_minimum(self):
        """Test validation fails for num_frames below minimum."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        with pytest.raises(ValidationError):
            InfinitalkInput(
                image=image_artifact,
                audio=audio_artifact,
                prompt="Test prompt",
                num_frames=40,  # Below minimum of 41
            )

    def test_num_frames_above_maximum(self):
        """Test validation fails for num_frames above maximum."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        with pytest.raises(ValidationError):
            InfinitalkInput(
                image=image_artifact,
                audio=audio_artifact,
                prompt="Test prompt",
                num_frames=722,  # Above maximum of 721
            )

    def test_resolution_options(self):
        """Test all valid resolution options."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        valid_resolutions = ["480p", "720p"]

        for resolution in valid_resolutions:
            input_data = InfinitalkInput(
                image=image_artifact,
                audio=audio_artifact,
                prompt="Test prompt",
                resolution=resolution,  # type: ignore[arg-type]
            )
            assert input_data.resolution == resolution

    def test_acceleration_options(self):
        """Test all valid acceleration options."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        valid_accelerations = ["none", "regular", "high"]

        for acceleration in valid_accelerations:
            input_data = InfinitalkInput(
                image=image_artifact,
                audio=audio_artifact,
                prompt="Test prompt",
                acceleration=acceleration,  # type: ignore[arg-type]
            )
            assert input_data.acceleration == acceleration


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalInfinitalkGenerator:
    """Tests for FalInfinitalkGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalInfinitalkGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-infinitalk"
        assert self.generator.artifact_type == "video"
        assert "infinitalk" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == InfinitalkInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            image_artifact = ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/image.jpg",
                format="jpg",
                width=512,
                height=512,
            )
            audio_artifact = AudioArtifact(
                generation_id="gen2",
                storage_url="https://example.com/audio.wav",
                format="wav",
                duration=None,
                sample_rate=None,
                channels=None,
            )

            input_data = InfinitalkInput(
                image=image_artifact,
                audio=audio_artifact,
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

                async def store_video_result(self, *args, **kwargs):
                    return VideoArtifact(
                        generation_id="test_gen",
                        storage_url="",
                        width=1,
                        height=1,
                        format="mp4",
                        duration=None,
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
    async def test_generate_successful(self):
        """Test successful generation with default parameters."""
        image_artifact = ImageArtifact(
            generation_id="gen_input_image",
            storage_url="https://example.com/input-image.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen_input_audio",
            storage_url="https://example.com/input-audio.wav",
            format="wav",
            duration=5.0,
            sample_rate=44100,
            channels=2,
        )

        input_data = InfinitalkInput(
            image=image_artifact,
            audio=audio_artifact,
            prompt="Generate a talking avatar",
            num_frames=145,
            resolution="480p",
            acceleration="regular",
            seed=42,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.mp4"
        fake_uploaded_image_url = "https://fal.media/files/uploaded-image.jpg"
        fake_uploaded_audio_url = "https://fal.media/files/uploaded-audio.wav"

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
                        "file_size": 8404019,
                    },
                    "seed": 42,
                }
            )

            # Track upload calls to return different URLs for image and audio
            upload_call_count = 0

            async def mock_upload(file_path):
                nonlocal upload_call_count
                url = fake_uploaded_image_url if upload_call_count == 0 else fake_uploaded_audio_url
                upload_call_count += 1
                return url

            # Create mock fal_client module
            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]

            sys.modules["fal_client"] = mock_fal_client

            # Mock storage result
            mock_video_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=854,
                height=480,
                format="mp4",
                duration=5.0,
                fps=29,
            )

            # Execute generation
            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    # Return different fake paths for image and audio
                    if isinstance(artifact, ImageArtifact):
                        return "/tmp/fake_image.jpg"
                    elif isinstance(artifact, AudioArtifact):
                        return "/tmp/fake_audio.wav"
                    return "/tmp/fake_file"

                async def store_image_result(self, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, **kwargs):
                    return mock_video_artifact

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
            assert result.outputs[0] == mock_video_artifact

            # Verify file uploads were called for both image and audio
            assert mock_fal_client.upload_file_async.call_count == 2

            # Verify API calls with uploaded URLs
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/infinitalk",
                arguments={
                    "image_url": fake_uploaded_image_url,
                    "audio_url": fake_uploaded_audio_url,
                    "prompt": "Generate a talking avatar",
                    "num_frames": 145,
                    "resolution": "480p",
                    "acceleration": "regular",
                    "seed": 42,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_successful_720p(self):
        """Test successful generation with 720p resolution."""
        image_artifact = ImageArtifact(
            generation_id="gen_input_image",
            storage_url="https://example.com/input-image.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen_input_audio",
            storage_url="https://example.com/input-audio.wav",
            format="wav",
            duration=8.0,
            sample_rate=48000,
            channels=1,
        )

        input_data = InfinitalkInput(
            image=image_artifact,
            audio=audio_artifact,
            prompt="Generate a high quality talking avatar",
            num_frames=300,
            resolution="720p",
            acceleration="high",
            seed=999,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output-720p.mp4"
        fake_uploaded_image_url = "https://fal.media/files/uploaded-image-hq.jpg"
        fake_uploaded_audio_url = "https://fal.media/files/uploaded-audio-hq.wav"

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
                        "file_name": "output-720p.mp4",
                        "file_size": 15808038,
                    },
                    "seed": 999,
                }
            )

            upload_call_count = 0

            async def mock_upload(file_path):
                nonlocal upload_call_count
                url = fake_uploaded_image_url if upload_call_count == 0 else fake_uploaded_audio_url
                upload_call_count += 1
                return url

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_video_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1280,
                height=720,
                format="mp4",
                duration=8.0,
                fps=37,
            )

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    if isinstance(artifact, ImageArtifact):
                        return "/tmp/fake_image_hq.jpg"
                    elif isinstance(artifact, AudioArtifact):
                        return "/tmp/fake_audio_hq.wav"
                    return "/tmp/fake_file"

                async def store_image_result(self, **kwargs):
                    raise NotImplementedError

                async def store_video_result(self, **kwargs):
                    return mock_video_artifact

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
            assert result.outputs[0] == mock_video_artifact

            # Verify API call used 720p resolution and other parameters
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["resolution"] == "720p"
            assert call_args[1]["arguments"]["num_frames"] == 300
            assert call_args[1]["arguments"]["acceleration"] == "high"
            assert call_args[1]["arguments"]["seed"] == 999

    @pytest.mark.asyncio
    async def test_generate_no_video_returned(self):
        """Test generation fails when API returns no video."""
        image_artifact = ImageArtifact(
            generation_id="gen_input_image",
            storage_url="https://example.com/input-image.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen_input_audio",
            storage_url="https://example.com/input-audio.wav",
            format="wav",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        input_data = InfinitalkInput(
            image=image_artifact,
            audio=audio_artifact,
            prompt="Test prompt",
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={})  # No video in response

            fake_uploaded_image_url = "https://fal.media/files/uploaded-image.jpg"
            fake_uploaded_audio_url = "https://fal.media/files/uploaded-audio.wav"

            upload_call_count = 0

            async def mock_upload(file_path):
                nonlocal upload_call_count
                url = fake_uploaded_image_url if upload_call_count == 0 else fake_uploaded_audio_url
                upload_call_count += 1
                return url

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
                    if isinstance(artifact, ImageArtifact):
                        return "/tmp/fake_image.jpg"
                    elif isinstance(artifact, AudioArtifact):
                        return "/tmp/fake_audio.wav"
                    return "/tmp/fake_file"

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
    async def test_estimate_cost_default_params(self):
        """Test cost estimation with default parameters."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        input_data = InfinitalkInput(
            image=image_artifact,
            audio=audio_artifact,
            prompt="Test prompt",
        )

        cost = await self.generator.estimate_cost(input_data)

        # Base cost (0.10) with default params
        assert cost == 0.10
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_720p(self):
        """Test cost estimation for 720p resolution."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        input_data = InfinitalkInput(
            image=image_artifact,
            audio=audio_artifact,
            prompt="Test prompt",
            resolution="720p",
        )

        cost = await self.generator.estimate_cost(input_data)

        # Base cost * 1.5 for 720p (0.10 * 1.5 = 0.15)
        assert cost == pytest.approx(0.15, rel=0.001)
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_more_frames(self):
        """Test cost estimation with more frames."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        input_data = InfinitalkInput(
            image=image_artifact,
            audio=audio_artifact,
            prompt="Test prompt",
            num_frames=290,  # 2x the default 145
        )

        cost = await self.generator.estimate_cost(input_data)

        # Base cost * 2 for double frames (0.10 * 2.0 = 0.20)
        assert cost == pytest.approx(0.20, rel=0.001)
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_combined(self):
        """Test cost estimation with both 720p and more frames."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        audio_artifact = AudioArtifact(
            generation_id="gen2",
            storage_url="https://example.com/audio.wav",
            format="wav",
            duration=None,
            sample_rate=None,
            channels=None,
        )

        input_data = InfinitalkInput(
            image=image_artifact,
            audio=audio_artifact,
            prompt="Test prompt",
            resolution="720p",
            num_frames=290,  # 2x the default 145
        )

        cost = await self.generator.estimate_cost(input_data)

        # Base cost * 1.5 (720p) * 2.0 (frames) = 0.10 * 1.5 * 2.0 = 0.30
        assert cost == pytest.approx(0.30, rel=0.001)
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = InfinitalkInput.model_json_schema()

        assert schema["type"] == "object"
        assert "image" in schema["properties"]
        assert "audio" in schema["properties"]
        assert "prompt" in schema["properties"]
        assert "num_frames" in schema["properties"]
        assert "resolution" in schema["properties"]
        assert "acceleration" in schema["properties"]
        assert "seed" in schema["properties"]

        # Check that image, audio, and prompt are required
        assert "image" in schema["required"]
        assert "audio" in schema["required"]
        assert "prompt" in schema["required"]

        # Check resolution enum values
        resolution_prop = schema["properties"]["resolution"]
        assert "enum" in resolution_prop
        assert "480p" in resolution_prop["enum"]
        assert "720p" in resolution_prop["enum"]

        # Check acceleration enum values
        acceleration_prop = schema["properties"]["acceleration"]
        assert "enum" in acceleration_prop
        assert "none" in acceleration_prop["enum"]
        assert "regular" in acceleration_prop["enum"]
        assert "high" in acceleration_prop["enum"]

    def test_parse_resolution(self):
        """Test resolution parsing helper method."""
        assert self.generator._parse_resolution("480p") == (854, 480)
        assert self.generator._parse_resolution("720p") == (1280, 720)
        assert self.generator._parse_resolution("invalid") == (854, 480)  # Default to 480p
