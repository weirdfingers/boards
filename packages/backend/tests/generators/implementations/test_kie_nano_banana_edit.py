"""
Tests for KieNanoBananaEditGenerator.
"""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.kie.image.nano_banana_edit import (
    KieNanoBananaEditGenerator,
    NanoBananaEditInput,
)


class TestNanoBananaEditInput:
    """Tests for NanoBananaEditInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        image_artifact_1 = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image1.png",
            format="png",
            width=1024,
            height=768,
        )
        image_artifact_2 = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/image2.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = NanoBananaEditInput(
            prompt="make a photo of the man driving the car",
            image_sources=[image_artifact_1, image_artifact_2],
            output_format="jpeg",
            image_size="16:9",
        )

        assert input_data.prompt == "make a photo of the man driving the car"
        assert len(input_data.image_sources) == 2
        assert input_data.output_format == "jpeg"
        assert input_data.image_size == "16:9"

    def test_input_defaults(self):
        """Test default values."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = NanoBananaEditInput(
            prompt="Test prompt",
            image_sources=[image_artifact],
        )

        assert input_data.output_format == "png"
        assert input_data.image_size == "1:1"

    def test_invalid_output_format(self):
        """Test validation fails for invalid output format."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        with pytest.raises(ValidationError):
            NanoBananaEditInput(
                prompt="Test",
                image_sources=[image_artifact],
                output_format="invalid",  # type: ignore[arg-type]
            )

    def test_invalid_image_size(self):
        """Test validation fails for invalid image size."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        with pytest.raises(ValidationError):
            NanoBananaEditInput(
                prompt="Test",
                image_sources=[image_artifact],
                image_size="invalid",  # type: ignore[arg-type]
            )

    def test_empty_image_sources(self):
        """Test validation fails for empty image_sources."""
        with pytest.raises(ValidationError):
            NanoBananaEditInput(
                prompt="Test",
                image_sources=[],  # Empty list should fail min_length=1
            )

    def test_too_many_image_sources(self):
        """Test validation fails for too many image sources."""
        # Create 11 image artifacts (exceeds max of 10)
        image_artifacts = [
            ImageArtifact(
                generation_id=f"gen{i}",
                storage_url=f"https://example.com/image{i}.png",
                format="png",
                width=1024,
                height=768,
            )
            for i in range(11)
        ]

        with pytest.raises(ValidationError):
            NanoBananaEditInput(
                prompt="Test",
                image_sources=image_artifacts,
            )

    def test_prompt_max_length(self):
        """Test validation for prompt max length."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        # Test prompt that exceeds 5000 characters
        long_prompt = "a" * 5001

        with pytest.raises(ValidationError):
            NanoBananaEditInput(
                prompt=long_prompt,
                image_sources=[image_artifact],
            )

    def test_image_size_options(self):
        """Test all valid image size options."""
        image_artifact = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=768,
        )

        valid_sizes = [
            "1:1",
            "9:16",
            "16:9",
            "3:4",
            "4:3",
            "3:2",
            "2:3",
            "5:4",
            "4:5",
            "21:9",
            "auto",
        ]

        for size in valid_sizes:
            input_data = NanoBananaEditInput(
                prompt="Test",
                image_sources=[image_artifact],
                image_size=size,  # type: ignore[arg-type]
            )
            assert input_data.image_size == size


class TestKieNanoBananaEditGenerator:
    """Tests for KieNanoBananaEditGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = KieNanoBananaEditGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "kie-nano-banana-edit"
        assert self.generator.artifact_type == "image"
        assert "edit" in self.generator.description.lower()
        assert "Gemini" in self.generator.description
        assert self.generator.api_pattern == "market"
        assert self.generator.model_id == "google/nano-banana-edit"

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == NanoBananaEditInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            image_artifact = ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/image.png",
                format="png",
                width=1024,
                height=768,
            )

            input_data = NanoBananaEditInput(
                prompt="Test prompt",
                image_sources=[image_artifact],
            )

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
    async def test_generate_successful_single_image(self):
        """Test successful generation with single image output."""
        import tempfile

        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = NanoBananaEditInput(
            prompt="make the sky more dramatic",
            image_sources=[input_image],
            output_format="jpeg",
        )

        fake_output_url = "https://storage.kie.ai/output.png"
        fake_uploaded_url = "https://kieai.redpandaai.co/files/uploaded-input.png"
        fake_task_id = "task_google_123456"

        # Create a temporary file to simulate the resolved artifact
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            tmp_file.write(b"fake image data")
            tmp_path = tmp_file.name

        try:
            with patch.dict(os.environ, {"KIE_API_KEY": "fake-key"}):
                # Mock httpx.AsyncClient
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
                # Market API uses lowercase 'state' and 'resultJson' (JSON string)
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

                # Configure mock client to return appropriate responses
                async def mock_post(url, **kwargs):
                    if "file-stream-upload" in url:
                        return upload_response
                    return submit_response

                async def mock_get(url, **kwargs):
                    # Simulate a short delay for the first poll
                    return status_response

                mock_client.post = AsyncMock(side_effect=mock_post)
                mock_client.get = AsyncMock(side_effect=mock_get)

                # Mock storage result
                mock_artifact = ImageArtifact(
                    generation_id="test_gen",
                    storage_url=fake_output_url,
                    width=1024,
                    height=768,
                    format="jpeg",
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

                # Mock httpx.AsyncClient to return our mock client from context manager
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
        import tempfile

        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = NanoBananaEditInput(
            prompt="test",
            image_sources=[input_image],
        )

        fake_uploaded_url = "https://kieai.redpandaai.co/files/uploaded.png"

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

                # Mock task submission error response
                submit_response = MagicMock()
                submit_response.status_code = 200
                submit_response.json.return_value = {
                    "code": 422,
                    "msg": "Validation error: prompt too short",
                }

                async def mock_post(url, **kwargs):
                    if "file-stream-upload" in url:
                        return upload_response
                    return submit_response

                mock_client.post = AsyncMock(side_effect=mock_post)

                class DummyCtx(GeneratorExecutionContext):
                    generation_id = "test_gen"
                    provider_correlation_id = "corr"
                    tenant_id = "test_tenant"
                    board_id = "test_board"

                    async def resolve_artifact(self, artifact):
                        return tmp_path

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

                # Mock httpx.AsyncClient to return our mock client from context manager
                mock_client_cm = MagicMock()
                mock_client_cm.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cm.__aexit__ = AsyncMock(return_value=None)

                with patch("httpx.AsyncClient", return_value=mock_client_cm):
                    with pytest.raises(ValueError, match="Validation error"):
                        await self.generator.generate(input_data, DummyCtx())
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation."""
        input_image = ImageArtifact(
            generation_id="gen_input",
            storage_url="https://example.com/input.png",
            format="png",
            width=1024,
            height=768,
        )

        input_data = NanoBananaEditInput(
            prompt="Test prompt",
            image_sources=[input_image],
        )

        cost = await self.generator.estimate_cost(input_data)

        # Per-image cost (0.025 * 1)
        assert cost == 0.025
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_multiple_images(self):
        """Test cost estimation for multiple images."""
        input_images = [
            ImageArtifact(
                generation_id=f"gen_input_{i}",
                storage_url=f"https://example.com/input{i}.png",
                format="png",
                width=1024,
                height=768,
            )
            for i in range(5)
        ]

        input_data = NanoBananaEditInput(
            prompt="Test prompt",
            image_sources=input_images,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Per-image cost (0.025 * 5)
        assert cost == 0.125
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = NanoBananaEditInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "image_sources" in schema["properties"]
        assert "output_format" in schema["properties"]
        assert "image_size" in schema["properties"]

        # Check that image_sources is an array
        image_sources_prop = schema["properties"]["image_sources"]
        assert image_sources_prop["type"] == "array"
        assert "minItems" in image_sources_prop
        assert "maxItems" in image_sources_prop

        # Check that prompt has max length
        prompt_prop = schema["properties"]["prompt"]
        assert prompt_prop["maxLength"] == 5000
