"""
Tests for KieQwenImage2Generator.
"""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.kie.image.qwen_image_2 import (
    KieQwenImage2Generator,
    QwenImage2Input,
)


class TestQwenImage2Input:
    """Tests for QwenImage2Input schema."""

    def test_valid_text_to_image_input(self):
        """Test valid text-to-image input creation."""
        input_data = QwenImage2Input(
            prompt="A beautiful sunset over the ocean",
            image_size="16:9",
            output_format="jpeg",
        )

        assert input_data.prompt == "A beautiful sunset over the ocean"
        assert input_data.image_sources is None
        assert input_data.image_size == "16:9"
        assert input_data.output_format == "jpeg"
        assert input_data.seed is None

    def test_valid_image_edit_input(self):
        """Test valid image editing input creation."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = QwenImage2Input(
            prompt="Make the sky more dramatic",
            image_sources=[image_artifact],
            image_size="4:3",
            output_format="png",
            seed=42,
        )

        assert input_data.prompt == "Make the sky more dramatic"
        assert input_data.image_sources is not None
        assert len(input_data.image_sources) == 1
        assert input_data.image_size == "4:3"
        assert input_data.seed == 42

    def test_input_defaults(self):
        """Test default values."""
        input_data = QwenImage2Input(prompt="Test prompt")

        assert input_data.image_sources is None
        assert input_data.image_size == "1:1"
        assert input_data.output_format == "png"
        assert input_data.seed is None

    def test_invalid_output_format(self):
        """Test validation fails for invalid output format."""
        with pytest.raises(ValidationError):
            QwenImage2Input(
                prompt="Test",
                output_format="invalid",  # type: ignore[arg-type]
            )

    def test_invalid_image_size(self):
        """Test validation fails for invalid image size."""
        with pytest.raises(ValidationError):
            QwenImage2Input(
                prompt="Test",
                image_size="2:3",  # type: ignore[arg-type]
            )

    def test_empty_image_sources(self):
        """Test validation fails for empty image_sources list."""
        with pytest.raises(ValidationError):
            QwenImage2Input(
                prompt="Test",
                image_sources=[],
            )

    def test_too_many_image_sources(self):
        """Test validation fails for more than 3 image sources."""
        image_artifacts = [
            ImageArtifact(
                generation_id=f"gen{i}",
                storage_url=f"https://example.com/image{i}.png",
                format="png",
                width=1024,
                height=768,
            )
            for i in range(4)
        ]

        with pytest.raises(ValidationError):
            QwenImage2Input(
                prompt="Test",
                image_sources=image_artifacts,
            )

    def test_prompt_max_length(self):
        """Test validation for prompt max length."""
        long_prompt = "a" * 5001

        with pytest.raises(ValidationError):
            QwenImage2Input(prompt=long_prompt)

    def test_image_size_options(self):
        """Test all valid image size options."""
        valid_sizes = ["1:1", "4:3", "3:4", "16:9", "9:16"]

        for size in valid_sizes:
            input_data = QwenImage2Input(
                prompt="Test",
                image_size=size,  # type: ignore[arg-type]
            )
            assert input_data.image_size == size

    def test_multiple_image_sources(self):
        """Test valid input with multiple image sources (up to 3)."""
        image_artifacts = [
            ImageArtifact(
                generation_id=f"gen{i}",
                storage_url=f"https://example.com/image{i}.png",
                format="png",
                width=1024,
                height=768,
            )
            for i in range(3)
        ]

        input_data = QwenImage2Input(
            prompt="Edit these images",
            image_sources=image_artifacts,
        )

        assert input_data.image_sources is not None
        assert len(input_data.image_sources) == 3


class TestKieQwenImage2Generator:
    """Tests for KieQwenImage2Generator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = KieQwenImage2Generator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "kie-qwen-image-2"
        assert self.generator.artifact_type == "image"
        assert "Qwen" in self.generator.description
        assert "2K" in self.generator.description
        assert self.generator.api_pattern == "market"
        assert self.generator.model_id == "qwen2/text-to-image"

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == QwenImage2Input

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = QwenImage2Input(prompt="Test prompt")

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return ""

                async def store_image_result(self, **kwargs):
                    return ImageArtifact(
                        generation_id="test_gen",
                        storage_url="",
                        width=1,
                        height=1,
                        format="png",
                    )

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

            with pytest.raises(ValueError, match="KIE_API_KEY"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_generate_text_to_image_successful(self):
        """Test successful text-to-image generation."""
        input_data = QwenImage2Input(
            prompt="A cat sitting on a windowsill",
            image_size="1:1",
            output_format="png",
        )

        fake_output_url = "https://storage.kie.ai/output.png"
        fake_task_id = "task_qwen2_123456"

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

            # Mock status check response
            status_response = MagicMock()
            status_response.status_code = 200
            status_response.json.return_value = {
                "code": 200,
                "data": {
                    "taskId": fake_task_id,
                    "state": "success",
                    "resultJson": json.dumps({"resultUrls": [fake_output_url]}),
                },
            }

            mock_client.post = AsyncMock(return_value=submit_response)
            mock_client.get = AsyncMock(return_value=status_response)

            mock_artifact = ImageArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=2048,
                height=2048,
                format="png",
            )

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return ""

                async def store_image_result(self, **kwargs):
                    return mock_artifact

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

            mock_client_cm = MagicMock()
            mock_client_cm.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cm.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client_cm):
                result = await self.generator.generate(input_data, DummyCtx())

            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1
            assert result.outputs[0] == mock_artifact

            # Verify text-to-image model was used
            call_args = mock_client.post.call_args
            request_body = call_args.kwargs.get("json") or call_args[1].get("json")
            assert request_body["model"] == "qwen2/text-to-image"
            assert "image_url" not in request_body["input"]

    @pytest.mark.asyncio
    async def test_generate_image_edit_successful(self):
        """Test successful image editing generation."""
        import tempfile

        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = QwenImage2Input(
            prompt="Make the background a forest",
            image_sources=[input_image],
            image_size="4:3",
            output_format="jpeg",
        )

        fake_output_url = "https://storage.kie.ai/edited.jpeg"
        fake_uploaded_url = "https://kieai.redpandaai.co/files/uploaded-input.png"
        fake_task_id = "task_qwen2_edit_789"

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            tmp_file.write(b"fake image data")
            tmp_path = tmp_file.name

        try:
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

                # Mock status check response
                status_response = MagicMock()
                status_response.status_code = 200
                status_response.json.return_value = {
                    "code": 200,
                    "data": {
                        "taskId": fake_task_id,
                        "state": "success",
                        "resultJson": json.dumps({"resultUrls": [fake_output_url]}),
                    },
                }

                # Mock file upload response
                upload_response = MagicMock()
                upload_response.status_code = 200
                upload_response.json.return_value = {
                    "success": True,
                    "data": {"downloadUrl": fake_uploaded_url},
                }

                async def mock_post(url, **kwargs):
                    if "file-stream-upload" in url:
                        return upload_response
                    return submit_response

                mock_client.post = AsyncMock(side_effect=mock_post)
                mock_client.get = AsyncMock(return_value=status_response)

                mock_artifact = ImageArtifact(
                    generation_id="test_gen",
                    storage_url=fake_output_url,
                    width=2048,
                    height=1536,
                    format="jpeg",
                )

                class DummyCtx(GeneratorExecutionContext):
                    generation_id = "test_gen"
                    provider_correlation_id = "corr"
                    tenant_id = "test_tenant"
                    board_id = "test_board"

                    async def resolve_artifact(self, artifact):
                        return tmp_path

                    async def store_image_result(self, **kwargs):
                        return mock_artifact

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

                mock_client_cm = MagicMock()
                mock_client_cm.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cm.__aexit__ = AsyncMock(return_value=None)

                with patch("httpx.AsyncClient", return_value=mock_client_cm):
                    result = await self.generator.generate(input_data, DummyCtx())

                assert isinstance(result, GeneratorResult)
                assert len(result.outputs) == 1
                assert result.outputs[0] == mock_artifact
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_generate_api_error(self):
        """Test generation fails when API returns error."""
        input_data = QwenImage2Input(prompt="test")

        with patch.dict(os.environ, {"KIE_API_KEY": "fake-key"}):
            mock_client = AsyncMock()

            submit_response = MagicMock()
            submit_response.status_code = 200
            submit_response.json.return_value = {
                "code": 422,
                "msg": "Validation error: prompt too short",
            }

            mock_client.post = AsyncMock(return_value=submit_response)

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

            mock_client_cm = MagicMock()
            mock_client_cm.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cm.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client_cm):
                with pytest.raises(ValueError, match="Validation error"):
                    await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation."""
        input_data = QwenImage2Input(prompt="Test prompt")

        cost = await self.generator.estimate_cost(input_data)

        assert cost == 0.03
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_edit_mode(self):
        """Test cost estimation in edit mode is the same."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = QwenImage2Input(
            prompt="Edit this",
            image_sources=[image_artifact],
        )

        cost = await self.generator.estimate_cost(input_data)

        assert cost == 0.03
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = QwenImage2Input.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "image_sources" in schema["properties"]
        assert "image_size" in schema["properties"]
        assert "output_format" in schema["properties"]
        assert "seed" in schema["properties"]

        # Check that prompt has max length
        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop["maxLength"] == 5000
