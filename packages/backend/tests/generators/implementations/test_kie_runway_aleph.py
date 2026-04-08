"""
Tests for KieRunwayAlephGenerator.
"""

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact, VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.kie.video.runway_aleph import (
    KieRunwayAlephGenerator,
    KieRunwayAlephInput,
)


def _make_video_artifact(generation_id: str = "gen1") -> VideoArtifact:
    return VideoArtifact(
        generation_id=generation_id,
        storage_url="https://example.com/video.mp4",
        format="mp4",
        width=1920,
        height=1080,
        duration=5.0,
        fps=30,
    )


def _make_image_artifact(generation_id: str = "gen_img") -> ImageArtifact:
    return ImageArtifact(
        generation_id=generation_id,
        storage_url="https://example.com/image.png",
        format="png",
        width=1920,
        height=1080,
    )


class DummyCtx(GeneratorExecutionContext):
    generation_id = "test_gen"
    provider_correlation_id = "corr"
    tenant_id = "test_tenant"
    board_id = "test_board"

    def __init__(self, resolve_path: str = ""):
        self._resolve_path = resolve_path

    async def resolve_artifact(self, artifact):
        return self._resolve_path

    async def store_image_result(self, **kwargs):
        raise NotImplementedError

    async def store_video_result(self, **kwargs):
        return VideoArtifact(
            generation_id="test_gen",
            storage_url=kwargs.get("storage_url", ""),
            width=kwargs.get("width", 1920),
            height=kwargs.get("height", 1080),
            duration=kwargs.get("duration", 5.0),
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


class TestKieRunwayAlephInput:
    """Tests for KieRunwayAlephInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        video = _make_video_artifact()
        input_data = KieRunwayAlephInput(
            prompt="make it look cinematic",
            video_source=video,
        )

        assert input_data.prompt == "make it look cinematic"
        assert input_data.video_source == video
        assert input_data.reference_image is None
        assert input_data.aspect_ratio is None
        assert input_data.seed is None

    def test_valid_input_with_all_options(self):
        """Test valid input with all optional fields."""
        video = _make_video_artifact()
        image = _make_image_artifact()
        input_data = KieRunwayAlephInput(
            prompt="restyle as anime",
            video_source=video,
            reference_image=image,
            aspect_ratio="16:9",
            seed=42,
        )

        assert input_data.reference_image == image
        assert input_data.aspect_ratio == "16:9"
        assert input_data.seed == 42

    def test_invalid_aspect_ratio(self):
        """Test validation fails for invalid aspect ratio."""
        with pytest.raises(ValidationError):
            KieRunwayAlephInput(
                prompt="Test",
                video_source=_make_video_artifact(),
                aspect_ratio="2:1",  # type: ignore[arg-type]
            )

    def test_prompt_max_length(self):
        """Test validation for prompt max length."""
        with pytest.raises(ValidationError):
            KieRunwayAlephInput(
                prompt="a" * 5001,
                video_source=_make_video_artifact(),
            )

    def test_all_valid_aspect_ratios(self):
        """Test all valid aspect ratio options."""
        valid_ratios = ["16:9", "9:16", "4:3", "3:4", "1:1", "21:9"]
        for ratio in valid_ratios:
            input_data = KieRunwayAlephInput(
                prompt="Test",
                video_source=_make_video_artifact(),
                aspect_ratio=ratio,  # type: ignore[arg-type]
            )
            assert input_data.aspect_ratio == ratio

    def test_video_source_required(self):
        """Test that video_source is required."""
        with pytest.raises(ValidationError):
            KieRunwayAlephInput(prompt="Test")  # type: ignore[call-arg]


class TestKieRunwayAlephGenerator:
    """Tests for KieRunwayAlephGenerator."""

    def setup_method(self):
        self.generator = KieRunwayAlephGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "kie-runway-aleph"
        assert self.generator.artifact_type == "video"
        assert "Aleph" in self.generator.description
        assert self.generator.api_pattern == "dedicated"
        assert self.generator.model_id == "aleph"

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == KieRunwayAlephInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = KieRunwayAlephInput(
                prompt="Test prompt",
                video_source=_make_video_artifact(),
            )

            with pytest.raises(ValueError, match="KIE_API_KEY"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful video-to-video generation."""
        input_data = KieRunwayAlephInput(
            prompt="make it look cinematic",
            video_source=_make_video_artifact(),
            aspect_ratio="16:9",
        )

        fake_video_url = "https://storage.kie.ai/output.mp4"
        fake_uploaded_url = "https://kieai.redpandaai.co/files/uploaded-video.mp4"
        fake_task_id = "task_aleph_123456"

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            tmp_file.write(b"fake video data")
            tmp_path = tmp_file.name

        try:
            with patch.dict(os.environ, {"KIE_API_KEY": "fake-key"}):
                mock_client = AsyncMock()

                # Mock file upload response
                upload_response = MagicMock()
                upload_response.status_code = 200
                upload_response.json.return_value = {
                    "success": True,
                    "data": {"downloadUrl": fake_uploaded_url},
                }

                # Mock task submission response
                submit_response = MagicMock()
                submit_response.status_code = 200
                submit_response.json.return_value = {
                    "code": 200,
                    "msg": "success",
                    "data": {"taskId": fake_task_id},
                }

                # Mock status check response (success immediately)
                status_response = MagicMock()
                status_response.status_code = 200
                status_response.json.return_value = {
                    "code": 200,
                    "msg": "success",
                    "data": {
                        "taskId": fake_task_id,
                        "successFlag": 1,
                        "response": {
                            "taskId": fake_task_id,
                            "resultVideoUrl": fake_video_url,
                        },
                    },
                }

                async def mock_post(url, **kwargs):
                    if "file-stream-upload" in url:
                        return upload_response
                    return submit_response

                async def mock_get(url, **kwargs):
                    return status_response

                mock_client.post = AsyncMock(side_effect=mock_post)
                mock_client.get = AsyncMock(side_effect=mock_get)

                mock_client_cm = MagicMock()
                mock_client_cm.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cm.__aexit__ = AsyncMock(return_value=None)

                with patch("httpx.AsyncClient", return_value=mock_client_cm):
                    result = await self.generator.generate(input_data, DummyCtx(tmp_path))

                assert isinstance(result, GeneratorResult)
                assert len(result.outputs) == 1
                assert result.outputs[0].storage_url == fake_video_url
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_generate_with_reference_image(self):
        """Test generation with reference image."""
        input_data = KieRunwayAlephInput(
            prompt="restyle as anime",
            video_source=_make_video_artifact(),
            reference_image=_make_image_artifact(),
        )

        fake_video_url = "https://storage.kie.ai/output.mp4"
        fake_uploaded_url = "https://kieai.redpandaai.co/files/uploaded.mp4"
        fake_task_id = "task_aleph_789"

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            tmp_file.write(b"fake data")
            tmp_path = tmp_file.name

        try:
            with patch.dict(os.environ, {"KIE_API_KEY": "fake-key"}):
                mock_client = AsyncMock()

                upload_response = MagicMock()
                upload_response.status_code = 200
                upload_response.json.return_value = {
                    "success": True,
                    "data": {"downloadUrl": fake_uploaded_url},
                }

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
                        "successFlag": 1,
                        "response": {
                            "taskId": fake_task_id,
                            "resultVideoUrl": fake_video_url,
                        },
                    },
                }

                post_calls = []

                async def mock_post(url, **kwargs):
                    post_calls.append((url, kwargs))
                    if "file-stream-upload" in url:
                        return upload_response
                    return submit_response

                async def mock_get(url, **kwargs):
                    return status_response

                mock_client.post = AsyncMock(side_effect=mock_post)
                mock_client.get = AsyncMock(side_effect=mock_get)

                mock_client_cm = MagicMock()
                mock_client_cm.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cm.__aexit__ = AsyncMock(return_value=None)

                with patch("httpx.AsyncClient", return_value=mock_client_cm):
                    result = await self.generator.generate(input_data, DummyCtx(tmp_path))

                assert isinstance(result, GeneratorResult)
                assert len(result.outputs) == 1

                # Verify the submit call included referenceImage
                submit_calls = [(url, kw) for url, kw in post_calls if "aleph/generate" in url]
                assert len(submit_calls) == 1
                submit_body = submit_calls[0][1].get("json", {})
                assert "referenceImage" in submit_body
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_generate_api_error(self):
        """Test generation fails when API returns error."""
        input_data = KieRunwayAlephInput(
            prompt="test",
            video_source=_make_video_artifact(),
        )

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            tmp_file.write(b"fake data")
            tmp_path = tmp_file.name

        try:
            with patch.dict(os.environ, {"KIE_API_KEY": "fake-key"}):
                mock_client = AsyncMock()

                # Upload succeeds
                upload_response = MagicMock()
                upload_response.status_code = 200
                upload_response.json.return_value = {
                    "success": True,
                    "data": {"downloadUrl": "https://example.com/uploaded.mp4"},
                }

                # Submit returns error
                submit_response = MagicMock()
                submit_response.status_code = 200
                submit_response.json.return_value = {
                    "code": 400,
                    "msg": "Validation error: invalid video format",
                }

                async def mock_post(url, **kwargs):
                    if "file-stream-upload" in url:
                        return upload_response
                    return submit_response

                mock_client.post = AsyncMock(side_effect=mock_post)

                mock_client_cm = MagicMock()
                mock_client_cm.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cm.__aexit__ = AsyncMock(return_value=None)

                with patch("httpx.AsyncClient", return_value=mock_client_cm):
                    with pytest.raises(ValueError, match="Validation error"):
                        await self.generator.generate(input_data, DummyCtx(tmp_path))
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation."""
        input_data = KieRunwayAlephInput(
            prompt="Test prompt",
            video_source=_make_video_artifact(),
        )

        cost = await self.generator.estimate_cost(input_data)
        assert cost == 0.10
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = KieRunwayAlephInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "video_source" in schema["properties"]
        assert "reference_image" in schema["properties"]
        assert "aspect_ratio" in schema["properties"]
        assert "seed" in schema["properties"]

        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop["maxLength"] == 5000

    def test_get_dimensions(self):
        """Test dimension calculation for different aspect ratios."""
        assert self.generator._get_dimensions("16:9") == (1920, 1080)
        assert self.generator._get_dimensions("9:16") == (1080, 1920)
        assert self.generator._get_dimensions("4:3") == (1440, 1080)
        assert self.generator._get_dimensions("3:4") == (1080, 1440)
        assert self.generator._get_dimensions("1:1") == (1080, 1080)
        assert self.generator._get_dimensions("21:9") == (2520, 1080)
        assert self.generator._get_dimensions(None) == (1920, 1080)
