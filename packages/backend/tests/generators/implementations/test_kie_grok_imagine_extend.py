"""
Tests for KieGrokImagineExtendGenerator.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.kie.video.grok_imagine_extend import (
    GrokImagineExtendInput,
    KieGrokImagineExtendGenerator,
)


class TestGrokImagineExtendInput:
    """Tests for GrokImagineExtendInput schema."""

    def test_valid_input_minimal(self):
        """Test valid input with minimal required fields."""
        input_data = GrokImagineExtendInput(
            task_id="task_grok_12345678",
            prompt="The camera slowly pans forward",
        )

        assert input_data.task_id == "task_grok_12345678"
        assert input_data.prompt == "The camera slowly pans forward"
        assert input_data.extend_at is None
        assert input_data.extend_times == "6"

    def test_valid_input_all_fields(self):
        """Test valid input with all fields specified."""
        input_data = GrokImagineExtendInput(
            task_id="task_grok_12345678",
            prompt="The camera slowly pans forward",
            extend_at="0",
            extend_times="10",
        )

        assert input_data.task_id == "task_grok_12345678"
        assert input_data.prompt == "The camera slowly pans forward"
        assert input_data.extend_at == "0"
        assert input_data.extend_times == "10"

    def test_input_defaults(self):
        """Test default values."""
        input_data = GrokImagineExtendInput(
            task_id="task_123",
            prompt="Test prompt",
        )

        assert input_data.extend_at is None
        assert input_data.extend_times == "6"

    def test_invalid_extend_times(self):
        """Test validation fails for invalid extend_times."""
        with pytest.raises(ValidationError):
            GrokImagineExtendInput(
                task_id="task_123",
                prompt="Test",
                extend_times="5",  # type: ignore[arg-type]
            )

    def test_task_id_max_length(self):
        """Test validation for task_id max length."""
        long_task_id = "a" * 101

        with pytest.raises(ValidationError):
            GrokImagineExtendInput(
                task_id=long_task_id,
                prompt="Test",
            )

    def test_prompt_max_length(self):
        """Test validation for prompt max length."""
        long_prompt = "a" * 5001

        with pytest.raises(ValidationError):
            GrokImagineExtendInput(
                task_id="task_123",
                prompt=long_prompt,
            )

    def test_extend_times_options(self):
        """Test all valid extend_times options."""
        for times in ["6", "10"]:
            input_data = GrokImagineExtendInput(
                task_id="task_123",
                prompt="Test",
                extend_times=times,  # type: ignore[arg-type]
            )
            assert input_data.extend_times == times


class TestKieGrokImagineExtendGenerator:
    """Tests for KieGrokImagineExtendGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = KieGrokImagineExtendGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "kie-grok-imagine-extend"
        assert self.generator.artifact_type == "video"
        assert "Grok Imagine Extend" in self.generator.description
        assert self.generator.api_pattern == "market"
        assert self.generator.model_id == "grok-imagine/extend"

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == GrokImagineExtendInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = GrokImagineExtendInput(
                task_id="task_123",
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
                        duration=1.0,
                        format="mp4",
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

            with pytest.raises(ValueError, match="KIE_API_KEY"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_generate_success_6s(self):
        """Test successful 6-second video extension."""
        input_data = GrokImagineExtendInput(
            task_id="task_grok_12345678",
            prompt="The camera slowly pans forward",
            extend_times="6",
        )

        fake_video_url = "https://storage.kie.ai/extended_output.mp4"
        fake_task_id = "task_extend_123456"

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
                    "state": "success",
                    "resultJson": '{"resultUrls": ["' + fake_video_url + '"]}',
                },
            }

            # Configure mock client
            async def mock_post(url, **kwargs):
                return submit_response

            async def mock_get(url, **kwargs):
                return status_response

            mock_client.post = AsyncMock(side_effect=mock_post)
            mock_client.get = AsyncMock(side_effect=mock_get)

            # Mock storage result
            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_video_url,
                width=1280,
                height=720,
                duration=6.0,
                format="mp4",
                fps=30,
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

            # Mock httpx.AsyncClient context manager
            mock_client_cm = MagicMock()
            mock_client_cm.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cm.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client_cm):
                result = await self.generator.generate(input_data, DummyCtx())

            # Verify result
            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1
            assert result.outputs[0] == mock_artifact

    @pytest.mark.asyncio
    async def test_generate_success_10s_with_extend_at(self):
        """Test successful 10-second video extension with extend_at."""
        input_data = GrokImagineExtendInput(
            task_id="task_grok_12345678",
            prompt="Zoom into the scene",
            extend_at="0",
            extend_times="10",
        )

        fake_video_url = "https://storage.kie.ai/extended_10s.mp4"
        fake_task_id = "task_extend_789"

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
                    "state": "success",
                    "resultJson": '{"resultUrls": ["' + fake_video_url + '"]}',
                },
            }

            async def mock_post(url, **kwargs):
                return submit_response

            async def mock_get(url, **kwargs):
                return status_response

            mock_client.post = AsyncMock(side_effect=mock_post)
            mock_client.get = AsyncMock(side_effect=mock_get)

            mock_artifact = VideoArtifact(
                generation_id="test_gen",
                storage_url=fake_video_url,
                width=1280,
                height=720,
                duration=10.0,
                format="mp4",
                fps=30,
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
        input_data = GrokImagineExtendInput(
            task_id="task_123",
            prompt="test",
        )

        with patch.dict(os.environ, {"KIE_API_KEY": "fake-key"}):
            mock_client = AsyncMock()

            submit_response = MagicMock()
            submit_response.status_code = 200
            submit_response.json.return_value = {
                "code": 400,
                "msg": "Invalid task_id: task not found",
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
                with pytest.raises(ValueError, match="Invalid task_id"):
                    await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_estimate_cost_6s(self):
        """Test cost estimation for 6-second extension."""
        input_data = GrokImagineExtendInput(
            task_id="task_123",
            prompt="Test prompt",
            extend_times="6",
        )

        cost = await self.generator.estimate_cost(input_data)
        assert cost == 0.10
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_10s(self):
        """Test cost estimation for 10-second extension."""
        input_data = GrokImagineExtendInput(
            task_id="task_123",
            prompt="Test prompt",
            extend_times="10",
        )

        cost = await self.generator.estimate_cost(input_data)
        assert cost == 0.15
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = GrokImagineExtendInput.model_json_schema()

        assert schema["type"] == "object"
        assert "task_id" in schema["properties"]
        assert "prompt" in schema["properties"]
        assert "extend_at" in schema["properties"]
        assert "extend_times" in schema["properties"]

        # Check task_id has max length
        task_id_prop = schema["properties"]["task_id"]
        assert task_id_prop["maxLength"] == 100

        # Check prompt has max length
        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop["maxLength"] == 5000

        # Check extend_at is optional
        assert "task_id" in schema.get("required", [])
        assert "prompt" in schema.get("required", [])
