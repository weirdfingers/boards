"""
Tests for KieVeo3Generator.
"""

import json
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact, VideoArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.kie.video.veo3 import (
    KieVeo3Generator,
    KieVeo3Input,
)


class TestKieVeo3Input:
    """Tests for KieVeo3Input schema."""

    def test_valid_input_text_to_video(self):
        """Test valid text-to-video input creation."""
        input_data = KieVeo3Input(
            prompt="a cat playing piano",
            aspect_ratio="16:9",
            model="veo3",
        )

        assert input_data.prompt == "a cat playing piano"
        assert input_data.image_sources is None
        assert input_data.aspect_ratio == "16:9"
        assert input_data.model == "veo3"

    def test_valid_input_image_to_video(self):
        """Test valid image-to-video input creation."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1920,
            height=1080,
        )

        input_data = KieVeo3Input(
            prompt="animate this image",
            image_sources=[image_artifact],
            aspect_ratio="16:9",
            model="veo3_fast",
        )

        assert input_data.prompt == "animate this image"
        assert input_data.image_sources is not None
        assert len(input_data.image_sources) == 1
        assert input_data.aspect_ratio == "16:9"
        assert input_data.model == "veo3_fast"

    def test_input_defaults(self):
        """Test default values."""
        input_data = KieVeo3Input(
            prompt="Test prompt",
        )

        assert input_data.image_sources is None
        assert input_data.aspect_ratio == "16:9"
        assert input_data.model == "veo3"

    def test_invalid_aspect_ratio(self):
        """Test validation fails for invalid aspect ratio."""
        with pytest.raises(ValidationError):
            KieVeo3Input(
                prompt="Test",
                aspect_ratio="4:3",  # type: ignore[arg-type]
            )

    def test_invalid_model(self):
        """Test validation fails for invalid model."""
        with pytest.raises(ValidationError):
            KieVeo3Input(
                prompt="Test",
                model="veo2",  # type: ignore[arg-type]
            )

    def test_too_many_image_sources(self):
        """Test validation fails for too many image sources."""
        # Create 3 image artifacts (exceeds max of 2)
        image_artifacts = [
            ImageArtifact(
                generation_id=f"gen{i}",
                storage_url=f"https://example.com/image{i}.png",
                format="png",
                width=1920,
                height=1080,
            )
            for i in range(3)
        ]

        with pytest.raises(ValidationError):
            KieVeo3Input(
                prompt="Test",
                image_sources=image_artifacts,
            )

    def test_prompt_max_length(self):
        """Test validation for prompt max length."""
        # Test prompt that exceeds 5000 characters
        long_prompt = "a" * 5001

        with pytest.raises(ValidationError):
            KieVeo3Input(
                prompt=long_prompt,
            )

    def test_aspect_ratio_options(self):
        """Test all valid aspect ratio options."""
        valid_ratios = ["16:9", "9:16", "Auto"]

        for ratio in valid_ratios:
            input_data = KieVeo3Input(
                prompt="Test",
                aspect_ratio=ratio,  # type: ignore[arg-type]
            )
            assert input_data.aspect_ratio == ratio


class TestKieVeo3Generator:
    """Tests for KieVeo3Generator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = KieVeo3Generator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "kie-veo3"
        assert self.generator.artifact_type == "video"
        assert "Veo 3.1" in self.generator.description
        assert self.generator.api_pattern == "dedicated"
        assert self.generator.model_id == "veo3"

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == KieVeo3Input

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = KieVeo3Input(
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
    async def test_generate_text_to_video_success(self):
        """Test successful text-to-video generation."""
        input_data = KieVeo3Input(
            prompt="a cat playing piano",
            aspect_ratio="16:9",
            model="veo3",
        )

        fake_video_url = "https://storage.kie.ai/output.mp4"
        fake_task_id = "task_veo3_123456"

        with patch.dict(os.environ, {"KIE_API_KEY": "fake-key"}):
            # Mock httpx.AsyncClient
            mock_client = AsyncMock()

            # Mock task submission response
            submit_response = MagicMock()
            submit_response.status_code = 200
            submit_response.json.return_value = {
                "success": True,
                "data": {"taskId": fake_task_id},
            }

            # Mock status check response (return success immediately)
            status_response = MagicMock()
            status_response.status_code = 200
            # resultUrls is a JSON string according to docs
            result_urls_json = json.dumps([fake_video_url])
            status_response.json.return_value = {
                "success": True,
                "data": {
                    "taskId": fake_task_id,
                    "successFlag": 1,
                    "resultUrls": result_urls_json,
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
                width=1920,
                height=1080,
                duration=8.0,
                format="mp4",
                fps=30,
            )

            # Execute generation
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
    async def test_generate_image_to_video_success(self):
        """Test successful image-to-video generation."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1920,
            height=1080,
        )

        input_data = KieVeo3Input(
            prompt="animate this image",
            image_sources=[input_image],
            aspect_ratio="9:16",
            model="veo3_fast",
        )

        fake_video_url = "https://storage.kie.ai/output.mp4"
        fake_uploaded_url = "https://kieai.redpandaai.co/files/uploaded-input.png"
        fake_task_id = "task_veo3_123456"

        # Create a temporary file to simulate the resolved artifact
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            tmp_file.write(b"fake image data")
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
                    "success": True,
                    "data": {"taskId": fake_task_id},
                }

                # Mock status check response
                status_response = MagicMock()
                status_response.status_code = 200
                result_urls_json = json.dumps([fake_video_url])
                status_response.json.return_value = {
                    "success": True,
                    "data": {
                        "taskId": fake_task_id,
                        "successFlag": 1,
                        "resultUrls": result_urls_json,
                    },
                }

                # Configure mock client
                async def mock_post(url, **kwargs):
                    if "file-stream-upload" in url:
                        return upload_response
                    return submit_response

                async def mock_get(url, **kwargs):
                    return status_response

                mock_client.post = AsyncMock(side_effect=mock_post)
                mock_client.get = AsyncMock(side_effect=mock_get)

                # Mock storage result
                mock_artifact = VideoArtifact(
                    generation_id="test_gen",
                    storage_url=fake_video_url,
                    width=1080,
                    height=1920,
                    duration=8.0,
                    format="mp4",
                    fps=30,
                )

                # Execute generation
                class DummyCtx(GeneratorExecutionContext):
                    generation_id = "test_gen"
                    provider_correlation_id = "corr"
                    tenant_id = "test_tenant"
                    board_id = "test_board"

                    async def resolve_artifact(self, artifact):
                        return tmp_path

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
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_generate_api_error(self):
        """Test generation fails when API returns error."""
        input_data = KieVeo3Input(
            prompt="test",
        )

        with patch.dict(os.environ, {"KIE_API_KEY": "fake-key"}):
            mock_client = AsyncMock()

            # Mock task submission error response
            submit_response = MagicMock()
            submit_response.status_code = 200
            submit_response.json.return_value = {
                "success": False,
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

            # Mock httpx.AsyncClient context manager
            mock_client_cm = MagicMock()
            mock_client_cm.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cm.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client_cm):
                with pytest.raises(ValueError, match="Validation error"):
                    await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_estimate_cost_veo3(self):
        """Test cost estimation for veo3 model."""
        input_data = KieVeo3Input(
            prompt="Test prompt",
            model="veo3",
        )

        cost = await self.generator.estimate_cost(input_data)
        assert cost == 0.08
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_veo3_fast(self):
        """Test cost estimation for veo3_fast model."""
        input_data = KieVeo3Input(
            prompt="Test prompt",
            model="veo3_fast",
        )

        cost = await self.generator.estimate_cost(input_data)
        assert cost == 0.04
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = KieVeo3Input.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "image_sources" in schema["properties"]
        assert "aspect_ratio" in schema["properties"]
        assert "model" in schema["properties"]

        # Check that prompt has max length
        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop["maxLength"] == 5000

        # Check that image_sources is optional array
        image_sources_prop = schema["properties"]["image_sources"]
        assert "anyOf" in image_sources_prop or image_sources_prop.get("type") == "array"
