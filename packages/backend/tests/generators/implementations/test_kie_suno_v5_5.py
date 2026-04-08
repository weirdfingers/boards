"""
Tests for KieSunoV55Generator.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import AudioArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.kie.audio.suno_v5_5 import (
    KieSunoV55Generator,
    SunoV55Input,
)


class TestSunoV55Input:
    """Tests for SunoV55Input schema."""

    def test_valid_input_with_lyrics(self):
        """Test valid input with lyrics."""
        input_data = SunoV55Input(
            title="My Song",
            style="upbeat pop with synth bass",
            lyrics="La la la, this is my song",
        )

        assert input_data.title == "My Song"
        assert input_data.style == "upbeat pop with synth bass"
        assert input_data.lyrics == "La la la, this is my song"
        assert input_data.instrumental is False
        assert input_data.vocal_gender is None
        assert input_data.persona_id is None

    def test_valid_input_instrumental(self):
        """Test valid instrumental input."""
        input_data = SunoV55Input(
            title="Chill Beats",
            style="lo-fi hip hop with jazzy piano",
            instrumental=True,
        )

        assert input_data.title == "Chill Beats"
        assert input_data.instrumental is True
        assert input_data.lyrics == ""

    def test_input_defaults(self):
        """Test default values."""
        input_data = SunoV55Input(
            title="Test",
            style="pop",
        )

        assert input_data.lyrics == ""
        assert input_data.instrumental is False
        assert input_data.vocal_gender is None
        assert input_data.persona_id is None

    def test_vocal_gender_male(self):
        """Test male vocal gender."""
        input_data = SunoV55Input(
            title="Test",
            style="rock",
            vocal_gender="m",
        )
        assert input_data.vocal_gender == "m"

    def test_vocal_gender_female(self):
        """Test female vocal gender."""
        input_data = SunoV55Input(
            title="Test",
            style="rock",
            vocal_gender="f",
        )
        assert input_data.vocal_gender == "f"

    def test_invalid_vocal_gender(self):
        """Test validation fails for invalid vocal gender."""
        with pytest.raises(ValidationError):
            SunoV55Input(
                title="Test",
                style="rock",
                vocal_gender="x",  # type: ignore[arg-type]
            )

    def test_title_max_length(self):
        """Test validation for title max length."""
        with pytest.raises(ValidationError):
            SunoV55Input(
                title="a" * 201,
                style="pop",
            )

    def test_style_max_length(self):
        """Test validation for style max length."""
        with pytest.raises(ValidationError):
            SunoV55Input(
                title="Test",
                style="a" * 1001,
            )

    def test_lyrics_max_length(self):
        """Test validation for lyrics max length."""
        with pytest.raises(ValidationError):
            SunoV55Input(
                title="Test",
                style="pop",
                lyrics="a" * 5001,
            )

    def test_with_persona_id(self):
        """Test input with persona ID."""
        input_data = SunoV55Input(
            title="Test",
            style="pop",
            persona_id="persona_abc123",
        )
        assert input_data.persona_id == "persona_abc123"


class TestKieSunoV55Generator:
    """Tests for KieSunoV55Generator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = KieSunoV55Generator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "kie-suno-v5-5"
        assert self.generator.artifact_type == "audio"
        assert "Suno V5.5" in self.generator.description
        assert self.generator.api_pattern == "dedicated"
        assert self.generator.model_id == "suno"

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == SunoV55Input

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = SunoV55Input(
                title="Test Song",
                style="pop",
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
                    return AudioArtifact(
                        generation_id="test_gen",
                        storage_url="",
                        format="mp3",
                        sample_rate=44100,
                        duration=None,
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
        """Test successful music generation."""
        input_data = SunoV55Input(
            title="Happy Song",
            style="upbeat pop",
            lyrics="La la la",
            vocal_gender="f",
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
                "msg": "success",
                "data": {
                    "taskId": fake_task_id,
                    "status": "SUCCESS",
                    "response": {
                        "sunoData": [
                            {
                                "id": "audio_001",
                                "audioUrl": fake_audio_url,
                                "title": "Happy Song",
                                "duration": 120.0,
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
                sample_rate=44100,
                duration=None,
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
    async def test_generate_instrumental_success(self):
        """Test successful instrumental generation."""
        input_data = SunoV55Input(
            title="Chill Beats",
            style="lo-fi hip hop",
            instrumental=True,
        )

        fake_audio_url = "https://storage.kie.ai/output.mp3"
        fake_task_id = "task_suno_789"

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
                "msg": "success",
                "data": {
                    "taskId": fake_task_id,
                    "status": "SUCCESS",
                    "response": {
                        "sunoData": [
                            {
                                "id": "audio_002",
                                "audioUrl": fake_audio_url,
                                "title": "Chill Beats",
                                "duration": 90.0,
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
                sample_rate=44100,
                duration=None,
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
    async def test_generate_api_error(self):
        """Test generation fails when API returns error."""
        input_data = SunoV55Input(
            title="Test",
            style="pop",
        )

        with patch.dict(os.environ, {"KIE_API_KEY": "fake-key"}):
            mock_client = AsyncMock()

            submit_response = MagicMock()
            submit_response.status_code = 200
            submit_response.json.return_value = {
                "code": 400,
                "msg": "Validation error: style too short",
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
    async def test_estimate_cost(self):
        """Test cost estimation."""
        input_data = SunoV55Input(
            title="Test",
            style="pop",
        )

        cost = await self.generator.estimate_cost(input_data)
        assert cost == 0.06
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = SunoV55Input.model_json_schema()

        assert schema["type"] == "object"
        assert "title" in schema["properties"]
        assert "style" in schema["properties"]
        assert "lyrics" in schema["properties"]
        assert "instrumental" in schema["properties"]
        assert "vocal_gender" in schema["properties"]
        assert "persona_id" in schema["properties"]

        # Check title has max length
        title_prop = schema["properties"]["title"]
        assert title_prop["maxLength"] == 200

        # Check style has max length
        style_prop = schema["properties"]["style"]
        assert style_prop["maxLength"] == 1000

        # Check lyrics has max length
        lyrics_prop = schema["properties"]["lyrics"]
        assert lyrics_prop["maxLength"] == 5000

    @pytest.mark.asyncio
    async def test_estimate_cost_fixed(self):
        """Test that cost estimation returns fixed rate for Suno V5.5."""
        input_data = SunoV55Input(
            title="Test",
            style="pop",
            instrumental=True,
        )
        cost = await self.generator.estimate_cost(input_data)
        assert cost == 0.06
