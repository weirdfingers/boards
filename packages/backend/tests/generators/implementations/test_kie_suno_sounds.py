"""
Tests for KieSunoSoundsGenerator.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import AudioArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.kie.audio.suno_sounds import (
    KieSunoSoundsGenerator,
    SunoSoundsInput,
)


class TestSunoSoundsInput:
    """Tests for SunoSoundsInput schema."""

    def test_valid_input_minimal(self):
        """Test valid input with just prompt."""
        input_data = SunoSoundsInput(
            prompt="dramatic thunder rolling across a stormy sky",
        )

        assert input_data.prompt == "dramatic thunder rolling across a stormy sky"
        assert input_data.model is None
        assert input_data.sound_loop is False
        assert input_data.sound_tempo is None
        assert input_data.sound_key == "Any"
        assert input_data.grab_lyrics is False

    def test_valid_input_all_fields(self):
        """Test valid input with all fields set."""
        input_data = SunoSoundsInput(
            prompt="upbeat electronic beat",
            model="V5",
            sound_loop=True,
            sound_tempo=120,
            sound_key="D#m",
            grab_lyrics=True,
        )

        assert input_data.prompt == "upbeat electronic beat"
        assert input_data.model == "V5"
        assert input_data.sound_loop is True
        assert input_data.sound_tempo == 120
        assert input_data.sound_key == "D#m"
        assert input_data.grab_lyrics is True

    def test_input_defaults(self):
        """Test default values."""
        input_data = SunoSoundsInput(prompt="test")

        assert input_data.model is None
        assert input_data.sound_loop is False
        assert input_data.sound_tempo is None
        assert input_data.sound_key == "Any"
        assert input_data.grab_lyrics is False

    def test_prompt_max_length(self):
        """Test validation for prompt max length."""
        long_prompt = "a" * 501

        with pytest.raises(ValidationError):
            SunoSoundsInput(prompt=long_prompt)

    def test_prompt_at_max_length(self):
        """Test prompt at exactly max length is valid."""
        prompt = "a" * 500
        input_data = SunoSoundsInput(prompt=prompt)
        assert len(input_data.prompt) == 500

    def test_invalid_model(self):
        """Test validation fails for invalid model."""
        with pytest.raises(ValidationError):
            SunoSoundsInput(
                prompt="test",
                model="V4",  # type: ignore[arg-type]
            )

    def test_valid_model_options(self):
        """Test all valid model options."""
        for model in ["V5", "V5_5"]:
            input_data = SunoSoundsInput(prompt="test", model=model)  # type: ignore[arg-type]
            assert input_data.model == model

    def test_sound_tempo_min(self):
        """Test sound_tempo minimum value."""
        input_data = SunoSoundsInput(prompt="test", sound_tempo=1)
        assert input_data.sound_tempo == 1

    def test_sound_tempo_max(self):
        """Test sound_tempo maximum value."""
        input_data = SunoSoundsInput(prompt="test", sound_tempo=300)
        assert input_data.sound_tempo == 300

    def test_sound_tempo_below_min(self):
        """Test validation fails for tempo below minimum."""
        with pytest.raises(ValidationError):
            SunoSoundsInput(prompt="test", sound_tempo=0)

    def test_sound_tempo_above_max(self):
        """Test validation fails for tempo above maximum."""
        with pytest.raises(ValidationError):
            SunoSoundsInput(prompt="test", sound_tempo=301)

    def test_invalid_sound_key(self):
        """Test validation fails for invalid sound key."""
        with pytest.raises(ValidationError):
            SunoSoundsInput(
                prompt="test",
                sound_key="X",  # type: ignore[arg-type]
            )

    def test_valid_sound_keys(self):
        """Test all valid major and minor keys."""
        major_keys = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        minor_keys = ["Cm", "C#m", "Dm", "D#m", "Em", "Fm", "F#m", "Gm", "G#m", "Am", "A#m", "Bm"]

        for key in ["Any"] + major_keys + minor_keys:
            input_data = SunoSoundsInput(prompt="test", sound_key=key)  # type: ignore[arg-type]
            assert input_data.sound_key == key


class TestKieSunoSoundsGenerator:
    """Tests for KieSunoSoundsGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = KieSunoSoundsGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "kie-suno-sounds"
        assert self.generator.artifact_type == "audio"
        assert "Suno Sounds" in self.generator.description
        assert self.generator.api_pattern == "dedicated"
        assert self.generator.model_id == "ai-music-api/sounds"

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == SunoSoundsInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = SunoSoundsInput(prompt="Test prompt")

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
                    return AudioArtifact(
                        generation_id="test_gen",
                        storage_url="",
                        format="mp3",
                        duration=None,
                        sample_rate=None,
                        channels=None,
                    )

                async def store_text_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            with pytest.raises(ValueError, match="KIE_API_KEY"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful audio generation."""
        input_data = SunoSoundsInput(
            prompt="dramatic thunder rolling",
            sound_loop=True,
            sound_tempo=120,
            sound_key="D#m",
        )

        fake_audio_url = "https://storage.kie.ai/output.mp3"
        fake_task_id = "task_suno_123456"

        with patch.dict(os.environ, {"KIE_API_KEY": "fake-key"}):
            mock_client = AsyncMock()

            # Mock task submission response
            submit_response = MagicMock()
            submit_response.status_code = 200
            submit_response.json.return_value = {
                "code": 200,
                "msg": "success",
                "data": {"taskId": fake_task_id},
            }

            # Mock status check response (return success immediately)
            status_response = MagicMock()
            status_response.status_code = 200
            status_response.json.return_value = {
                "code": 200,
                "msg": "All generated successfully.",
                "data": {
                    "callbackType": "complete",
                    "task_id": fake_task_id,
                    "status": "SUCCESS",
                    "response": {
                        "taskId": fake_task_id,
                        "sunoData": [
                            {
                                "id": "audio-id-1",
                                "audioUrl": fake_audio_url,
                                "streamAudioUrl": "https://storage.kie.ai/stream.mp3",
                                "imageUrl": "https://storage.kie.ai/cover.jpeg",
                                "prompt": "dramatic thunder rolling",
                                "modelName": "chirp-v3-5",
                                "title": "Thunder Storm",
                                "tags": "ambient, nature",
                                "createTime": 1700000000000,
                                "duration": 198.44,
                            }
                        ],
                    },
                },
            }

            async def mock_post(url, **kwargs):
                return submit_response

            async def mock_get(url, **kwargs):
                return status_response

            mock_client.post = AsyncMock(side_effect=mock_post)
            mock_client.get = AsyncMock(side_effect=mock_get)

            mock_artifact = AudioArtifact(
                generation_id="test_gen",
                storage_url=fake_audio_url,
                format="mp3",
                duration=198.44,
                sample_rate=None,
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

                async def store_video_result(self, **kwargs):
                    raise NotImplementedError

                async def store_audio_result(self, *args, **kwargs):
                    return mock_artifact

                async def store_text_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            mock_client_cm = MagicMock()
            mock_client_cm.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cm.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client_cm):
                result = await self.generator.generate(input_data, DummyCtx())

            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1
            assert result.outputs[0] == mock_artifact

    @pytest.mark.asyncio
    async def test_generate_multiple_outputs(self):
        """Test generation returning multiple audio clips."""
        input_data = SunoSoundsInput(prompt="upbeat electronic beat")

        fake_task_id = "task_suno_multi"

        with patch.dict(os.environ, {"KIE_API_KEY": "fake-key"}):
            mock_client = AsyncMock()

            submit_response = MagicMock()
            submit_response.status_code = 200
            submit_response.json.return_value = {
                "code": 200,
                "msg": "success",
                "data": {"taskId": fake_task_id},
            }

            status_response = MagicMock()
            status_response.status_code = 200
            status_response.json.return_value = {
                "code": 200,
                "msg": "All generated successfully.",
                "data": {
                    "status": "SUCCESS",
                    "task_id": fake_task_id,
                    "response": {
                        "taskId": fake_task_id,
                        "sunoData": [
                            {
                                "id": "audio-1",
                                "audioUrl": "https://storage.kie.ai/out1.mp3",
                                "duration": 120.5,
                            },
                            {
                                "id": "audio-2",
                                "audioUrl": "https://storage.kie.ai/out2.mp3",
                                "duration": 130.2,
                            },
                        ],
                    },
                },
            }

            async def mock_post(url, **kwargs):
                return submit_response

            async def mock_get(url, **kwargs):
                return status_response

            mock_client.post = AsyncMock(side_effect=mock_post)
            mock_client.get = AsyncMock(side_effect=mock_get)

            call_count = 0

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
                    nonlocal call_count
                    idx = call_count
                    call_count += 1
                    return AudioArtifact(
                        generation_id="test_gen",
                        storage_url=f"https://storage.kie.ai/out{idx + 1}.mp3",
                        format="mp3",
                        duration=120.5 if idx == 0 else 130.2,
                        sample_rate=None,
                        channels=None,
                    )

                async def store_text_result(self, *args, **kwargs):
                    raise NotImplementedError

                async def publish_progress(self, update):
                    return None

                async def set_external_job_id(self, external_id: str) -> None:
                    return None

            mock_client_cm = MagicMock()
            mock_client_cm.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cm.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client_cm):
                result = await self.generator.generate(input_data, DummyCtx())

            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 2

    @pytest.mark.asyncio
    async def test_generate_api_error(self):
        """Test generation fails when API returns error."""
        input_data = SunoSoundsInput(prompt="test")

        with patch.dict(os.environ, {"KIE_API_KEY": "fake-key"}):
            mock_client = AsyncMock()

            submit_response = MagicMock()
            submit_response.status_code = 200
            submit_response.json.return_value = {
                "code": 400,
                "msg": "Validation error: prompt too short",
            }

            async def mock_post(url, **kwargs):
                return submit_response

            mock_client.post = AsyncMock(side_effect=mock_post)

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

            mock_client_cm = MagicMock()
            mock_client_cm.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cm.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client_cm):
                with pytest.raises(ValueError, match="Validation error"):
                    await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_generate_task_failure(self):
        """Test generation fails when task status indicates failure."""
        input_data = SunoSoundsInput(prompt="test")

        fake_task_id = "task_suno_fail"

        with patch.dict(os.environ, {"KIE_API_KEY": "fake-key"}):
            mock_client = AsyncMock()

            submit_response = MagicMock()
            submit_response.status_code = 200
            submit_response.json.return_value = {
                "code": 200,
                "msg": "success",
                "data": {"taskId": fake_task_id},
            }

            status_response = MagicMock()
            status_response.status_code = 200
            status_response.json.return_value = {
                "code": 200,
                "msg": "failed",
                "data": {
                    "status": "GENERATE_AUDIO_FAILED",
                    "errorMsg": "Audio generation failed due to content policy",
                },
            }

            async def mock_post(url, **kwargs):
                return submit_response

            async def mock_get(url, **kwargs):
                return status_response

            mock_client.post = AsyncMock(side_effect=mock_post)
            mock_client.get = AsyncMock(side_effect=mock_get)

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

            mock_client_cm = MagicMock()
            mock_client_cm.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cm.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client_cm):
                with pytest.raises(ValueError, match="content policy"):
                    await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation."""
        input_data = SunoSoundsInput(prompt="test")

        cost = await self.generator.estimate_cost(input_data)
        assert cost == 0.0125
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = SunoSoundsInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "model" in schema["properties"]
        assert "sound_loop" in schema["properties"]
        assert "sound_tempo" in schema["properties"]
        assert "sound_key" in schema["properties"]
        assert "grab_lyrics" in schema["properties"]

        # Check that prompt has max length
        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop["maxLength"] == 500

        # Check sound_tempo constraints
        tempo_prop = schema["properties"]["sound_tempo"]
        # Check for constraints in the schema (may be nested in anyOf for optional)
        if "anyOf" in tempo_prop:
            int_schema = next(s for s in tempo_prop["anyOf"] if s.get("type") == "integer")
            assert int_schema["minimum"] == 1
            assert int_schema["maximum"] == 300
        else:
            assert tempo_prop["minimum"] == 1
            assert tempo_prop["maximum"] == 300

    def test_status_url(self):
        """Test status URL generation."""
        url = self.generator._get_status_url("test-task-123")
        assert url == "https://api.kie.ai/api/v1/generate/record-info?taskId=test-task-123"
