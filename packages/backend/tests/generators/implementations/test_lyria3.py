"""
Tests for FalLyria3Generator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import AudioArtifact, ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.audio.lyria3 import (
    FalLyria3Generator,
    Lyria3Input,
)


class TestLyria3Input:
    """Tests for Lyria3Input schema."""

    def test_valid_input(self):
        """Test valid input creation with all fields."""
        input_data = Lyria3Input(
            prompt="Upbeat electronic dance track with heavy bass and synth pads",
            negative_prompt="vocals, singing",
            image_url=ImageArtifact(
                generation_id="test_img",
                storage_url="https://example.com/image.png",
                format="png",
                width=256,
                height=256,
            ),
        )

        assert input_data.prompt == "Upbeat electronic dance track with heavy bass and synth pads"
        assert input_data.negative_prompt == "vocals, singing"
        assert input_data.image_url is not None
        assert input_data.image_url.storage_url == "https://example.com/image.png"

    def test_input_defaults(self):
        """Test default values."""
        input_data = Lyria3Input(
            prompt="A calm piano melody",
        )

        assert input_data.negative_prompt == ""
        assert input_data.image_url is None

    def test_prompt_required(self):
        """Test that prompt is required."""
        with pytest.raises(ValidationError):
            Lyria3Input()  # type: ignore[call-arg]

    def test_prompt_min_length(self):
        """Test prompt minimum length constraint."""
        with pytest.raises(ValidationError):
            Lyria3Input(prompt="")

    def test_prompt_max_length(self):
        """Test prompt maximum length constraint."""
        with pytest.raises(ValidationError):
            Lyria3Input(prompt="x" * 5001)

    def test_prompt_at_max_length(self):
        """Test prompt at exactly maximum length."""
        input_data = Lyria3Input(prompt="x" * 5000)
        assert len(input_data.prompt) == 5000

    def test_prompt_at_min_length(self):
        """Test prompt at exactly minimum length."""
        input_data = Lyria3Input(prompt="x")
        assert len(input_data.prompt) == 1

    def test_negative_prompt_optional(self):
        """Test negative prompt is optional with empty default."""
        input_data = Lyria3Input(prompt="Test music")
        assert input_data.negative_prompt == ""

    def test_image_url_optional(self):
        """Test image_url is optional with None default."""
        input_data = Lyria3Input(prompt="Test music")
        assert input_data.image_url is None

    def test_image_url_with_artifact(self):
        """Test image_url accepts ImageArtifact."""
        artifact = ImageArtifact(
            generation_id="test",
            storage_url="https://example.com/mood.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        input_data = Lyria3Input(prompt="Test", image_url=artifact)
        assert input_data.image_url == artifact


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalLyria3Generator:
    """Tests for FalLyria3Generator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalLyria3Generator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-lyria3"
        assert self.generator.artifact_type == "audio"
        assert "Lyria 3" in self.generator.description
        assert "Google" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == Lyria3Input

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = Lyria3Input(prompt="Test music generation")

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
                    return AudioArtifact(
                        generation_id="test_gen",
                        storage_url="",
                        format="mp3",
                        duration=0.0,
                        sample_rate=None,
                        channels=None,
                    )

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
        """Test successful generation with audio output."""
        input_data = Lyria3Input(
            prompt="Dreamy lo-fi hip hop beat with jazzy piano chords and vinyl crackle",
            negative_prompt="heavy metal, screaming",
        )

        fake_audio_url = "https://v3.fal.media/files/lyria/test_music.mp3"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-lyria3"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "audio": {
                        "url": fake_audio_url,
                        "content_type": "audio/mpeg",
                        "file_name": "music.mp3",
                        "file_size": 480000,
                    },
                    "lyrics": "Some generated lyrics here",
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = AudioArtifact(
                generation_id="test_gen",
                storage_url=fake_audio_url,
                format="mp3",
                duration=0.0,
                sample_rate=44100,
                channels=None,
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
                    raise NotImplementedError

                async def store_audio_result(self, **kwargs):
                    return mock_artifact

                async def store_text_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            result = await self.generator.generate(input_data, DummyCtx())

            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1
            assert result.outputs[0] == mock_artifact

            # Verify API calls
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/lyria3",
                arguments={
                    "prompt": "Dreamy lo-fi hip hop beat with jazzy piano chords and vinyl crackle",
                    "negative_prompt": "heavy metal, screaming",
                },
            )

    @pytest.mark.asyncio
    async def test_generate_minimal_input(self):
        """Test successful generation with only required prompt."""
        input_data = Lyria3Input(prompt="Simple piano melody")

        fake_audio_url = "https://v3.fal.media/files/lyria/minimal.mp3"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-minimal"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "audio": {
                        "url": fake_audio_url,
                    },
                    "lyrics": None,
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = AudioArtifact(
                generation_id="test_gen",
                storage_url=fake_audio_url,
                format="mp3",
                duration=0.0,
                sample_rate=44100,
                channels=None,
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
                    raise NotImplementedError

                async def store_audio_result(self, **kwargs):
                    return mock_artifact

                async def store_text_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            result = await self.generator.generate(input_data, DummyCtx())

            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1

            # Verify negative_prompt was NOT included (empty default)
            call_args = mock_fal_client.submit_async.call_args[1]["arguments"]
            assert "negative_prompt" not in call_args
            assert call_args["prompt"] == "Simple piano melody"

    @pytest.mark.asyncio
    async def test_generate_with_image_inspiration(self):
        """Test generation with optional image input for mood inspiration."""
        image_artifact = ImageArtifact(
            generation_id="test_img",
            storage_url="https://example.com/sunset.jpg",
            format="jpg",
            width=512,
            height=512,
        )
        input_data = Lyria3Input(
            prompt="Music inspired by this image",
            image_url=image_artifact,
        )

        fake_audio_url = "https://v3.fal.media/files/lyria/inspired.mp3"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-image"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "audio": {
                        "url": fake_audio_url,
                    },
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            mock_artifact = AudioArtifact(
                generation_id="test_gen",
                storage_url=fake_audio_url,
                format="mp3",
                duration=0.0,
                sample_rate=44100,
                channels=None,
            )

            uploaded_url = "https://fal.media/uploaded/sunset.jpg"

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

                async def store_audio_result(self, **kwargs):
                    return mock_artifact

                async def store_text_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            with patch(
                "boards.generators.implementations.fal.utils.upload_artifacts_to_fal",
                new_callable=AsyncMock,
                return_value=[uploaded_url],
            ) as mock_upload:
                result = await self.generator.generate(input_data, DummyCtx())

                assert isinstance(result, GeneratorResult)
                assert len(result.outputs) == 1

                # Verify image was uploaded
                mock_upload.assert_called_once()

                # Verify image_url was included in API call
                call_args = mock_fal_client.submit_async.call_args[1]["arguments"]
                assert call_args["image_url"] == uploaded_url

    @pytest.mark.asyncio
    async def test_generate_no_audio_returned(self):
        """Test generation fails when API returns no audio."""
        input_data = Lyria3Input(prompt="Test music")

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-empty"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={})

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

            with pytest.raises(ValueError, match="No audio data returned"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_generate_missing_audio_url(self):
        """Test generation fails when audio URL is missing."""
        input_data = Lyria3Input(prompt="Test music")

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-nourl"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={"audio": {"content_type": "audio/mpeg"}})

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

            with pytest.raises(ValueError, match="Audio URL missing"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation."""
        input_data = Lyria3Input(prompt="Test music")
        cost = await self.generator.estimate_cost(input_data)

        assert cost == 0.04
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_with_all_options(self):
        """Test cost estimation with all options (should be same fixed cost)."""
        input_data = Lyria3Input(
            prompt="Complex orchestral piece with full symphony",
            negative_prompt="electronic, synthesizer",
        )
        cost = await self.generator.estimate_cost(input_data)

        # Cost is fixed regardless of inputs
        assert cost == 0.04

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = Lyria3Input.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "negative_prompt" in schema["properties"]
        assert "image_url" in schema["properties"]

        # Check prompt is required
        assert "prompt" in schema["required"]

        # Check prompt constraints
        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop["minLength"] == 1
        assert prompt_prop["maxLength"] == 5000
