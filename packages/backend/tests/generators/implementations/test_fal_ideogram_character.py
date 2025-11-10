"""
Tests for FalIdeogramCharacterGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.fal_ideogram_character import (
    FalIdeogramCharacterGenerator,
    IdeogramCharacterInput,
)


class TestIdeogramCharacterInput:
    """Tests for IdeogramCharacterInput schema."""

    def test_valid_input(self):
        """Test valid input creation."""
        reference_image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/character.png",
            format="png",
            width=1024,
            height=1024,
        )

        input_data = IdeogramCharacterInput(
            prompt="Place the woman leisurely enjoying a cup of espresso at a café in Siena",
            reference_image_urls=[reference_image],
            style="REALISTIC",
            rendering_speed="QUALITY",
            num_images=2,
        )

        assert (
            input_data.prompt
            == "Place the woman leisurely enjoying a cup of espresso at a café in Siena"
        )
        assert len(input_data.reference_image_urls) == 1
        assert input_data.style == "REALISTIC"
        assert input_data.rendering_speed == "QUALITY"
        assert input_data.num_images == 2

    def test_input_defaults(self):
        """Test default values."""
        reference_image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/character.png",
            format="png",
            width=512,
            height=512,
        )

        input_data = IdeogramCharacterInput(
            prompt="Test prompt",
            reference_image_urls=[reference_image],
        )

        assert input_data.image_size == "square_hd"
        assert input_data.style == "AUTO"
        assert input_data.expand_prompt is True
        assert input_data.rendering_speed == "BALANCED"
        assert input_data.num_images == 1
        assert input_data.negative_prompt is None
        assert input_data.sync_mode is False
        assert input_data.seed is None
        assert input_data.reference_mask_urls is None
        assert input_data.image_urls is None
        assert input_data.style_codes is None
        assert input_data.color_palette is None

    def test_invalid_style(self):
        """Test validation fails for invalid style."""
        reference_image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/character.png",
            format="png",
            width=1024,
            height=1024,
        )

        with pytest.raises(ValidationError):
            IdeogramCharacterInput(
                prompt="Test",
                reference_image_urls=[reference_image],
                style="INVALID",  # type: ignore[arg-type]
            )

    def test_invalid_rendering_speed(self):
        """Test validation fails for invalid rendering speed."""
        reference_image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/character.png",
            format="png",
            width=1024,
            height=1024,
        )

        with pytest.raises(ValidationError):
            IdeogramCharacterInput(
                prompt="Test",
                reference_image_urls=[reference_image],
                rendering_speed="ULTRA_FAST",  # type: ignore[arg-type]
            )

    def test_empty_reference_images(self):
        """Test validation fails for empty reference_image_urls."""
        with pytest.raises(ValidationError):
            IdeogramCharacterInput(
                prompt="Test",
                reference_image_urls=[],  # type: ignore[arg-type]
            )

    def test_num_images_validation(self):
        """Test validation for num_images constraints."""
        reference_image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/character.png",
            format="png",
            width=1024,
            height=1024,
        )

        # Test below minimum
        with pytest.raises(ValidationError):
            IdeogramCharacterInput(
                prompt="Test",
                reference_image_urls=[reference_image],
                num_images=0,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            IdeogramCharacterInput(
                prompt="Test",
                reference_image_urls=[reference_image],
                num_images=9,
            )

    def test_style_options(self):
        """Test all valid style options."""
        reference_image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/character.png",
            format="png",
            width=1024,
            height=1024,
        )

        valid_styles = ["AUTO", "REALISTIC", "FICTION"]

        for style in valid_styles:
            input_data = IdeogramCharacterInput(
                prompt="Test",
                reference_image_urls=[reference_image],
                style=style,  # type: ignore[arg-type]
            )
            assert input_data.style == style

    def test_rendering_speed_options(self):
        """Test all valid rendering speed options."""
        reference_image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/character.png",
            format="png",
            width=1024,
            height=1024,
        )

        valid_speeds = ["TURBO", "BALANCED", "QUALITY"]

        for speed in valid_speeds:
            input_data = IdeogramCharacterInput(
                prompt="Test",
                reference_image_urls=[reference_image],
                rendering_speed=speed,  # type: ignore[arg-type]
            )
            assert input_data.rendering_speed == speed

    def test_optional_mask_and_style_images(self):
        """Test optional reference mask and style images."""
        reference_image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/character.png",
            format="png",
            width=1024,
            height=1024,
        )
        mask_image = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/mask.png",
            format="png",
            width=1024,
            height=1024,
        )
        style_image = ImageArtifact(
            generation_id="gen3",
            storage_url="https://example.com/style.png",
            format="png",
            width=1024,
            height=1024,
        )

        input_data = IdeogramCharacterInput(
            prompt="Test prompt",
            reference_image_urls=[reference_image],
            reference_mask_urls=[mask_image],
            image_urls=[style_image],
        )

        assert len(input_data.reference_image_urls) == 1
        assert (
            input_data.reference_mask_urls is not None
            and len(input_data.reference_mask_urls) == 1
        )
        assert input_data.image_urls is not None and len(input_data.image_urls) == 1


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalIdeogramCharacterGenerator:
    """Tests for FalIdeogramCharacterGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalIdeogramCharacterGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-ideogram-character"
        assert self.generator.artifact_type == "image"
        assert "consistent character" in self.generator.description.lower()

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == IdeogramCharacterInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            reference_image = ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/character.png",
                format="png",
                width=1024,
                height=1024,
            )

            input_data = IdeogramCharacterInput(
                prompt="Test prompt",
                reference_image_urls=[reference_image],
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

            with pytest.raises(ValueError, match="FAL_KEY"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_generate_successful_single_image(self):
        """Test successful generation with single image output."""
        reference_image = ImageArtifact(
            generation_id="gen_reference",
            storage_url="https://example.com/character.png",
            format="png",
            width=1024,
            height=1024,
        )

        input_data = IdeogramCharacterInput(
            prompt="Place the character in a sunny park",
            reference_image_urls=[reference_image],
            num_images=1,
            rendering_speed="BALANCED",
            style="REALISTIC",
        )

        fake_output_url = "https://v3.fal.media/files/monkey/output.png"
        fake_uploaded_url = "https://fal.media/files/uploaded-reference.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            # Mock fal_client module
            import sys

            # Create mock handler with async iterator for events
            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-123"

            # Create async iterator that yields nothing (no events)
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())

            # Mock the get() method to return result
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [
                        {
                            "url": fake_output_url,
                            "content_type": "image/png",
                            "file_name": "output.png",
                            "file_size": 1234567,
                        }
                    ],
                    "seed": 123456,
                }
            )

            # Create mock fal_client module
            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(return_value=fake_uploaded_url)  # type: ignore[attr-defined]

            sys.modules["fal_client"] = mock_fal_client

            # Mock storage result
            mock_artifact = ImageArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1024,
                height=1024,
                format="png",
            )

            # Execute generation
            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    # Return a fake local file path
                    return "/tmp/fake_reference.png"

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

            result = await self.generator.generate(input_data, DummyCtx())

            # Verify result
            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1
            assert result.outputs[0] == mock_artifact

            # Verify file upload was called
            mock_fal_client.upload_file_async.assert_called_once_with("/tmp/fake_reference.png")

            # Verify API calls with uploaded URL
            mock_fal_client.submit_async.assert_called_once_with(
                "fal-ai/ideogram/character",
                arguments={
                    "prompt": "Place the character in a sunny park",
                    "reference_image_urls": [fake_uploaded_url],
                    "image_size": "square_hd",
                    "style": "REALISTIC",
                    "expand_prompt": True,
                    "rendering_speed": "BALANCED",
                    "num_images": 1,
                    "sync_mode": False,
                },
            )

    @pytest.mark.asyncio
    async def test_generate_successful_multiple_images(self):
        """Test successful generation with multiple image outputs."""
        reference_image = ImageArtifact(
            generation_id="gen_reference",
            storage_url="https://example.com/character.png",
            format="png",
            width=1024,
            height=1024,
        )

        input_data = IdeogramCharacterInput(
            prompt="Place the character in different settings",
            reference_image_urls=[reference_image],
            num_images=3,
            rendering_speed="TURBO",
            style="FICTION",
        )

        fake_output_urls = [
            "https://v3.fal.media/files/monkey/output1.png",
            "https://v3.fal.media/files/monkey/output2.png",
            "https://v3.fal.media/files/monkey/output3.png",
        ]
        fake_uploaded_url = "https://fal.media/files/uploaded-reference.png"

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            # Create mock handler
            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-456"

            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [
                        {
                            "url": url,
                            "content_type": "image/png",
                            "file_name": f"output{i}.png",
                            "file_size": 1234567,
                        }
                        for i, url in enumerate(fake_output_urls)
                    ],
                    "seed": 789012,
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(return_value=fake_uploaded_url)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            # Mock storage results
            mock_artifacts = [
                ImageArtifact(
                    generation_id="test_gen",
                    storage_url=url,
                    width=1024,
                    height=1024,
                    format="png",
                )
                for url in fake_output_urls
            ]

            artifact_idx = 0

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return "/tmp/fake_reference.png"

                async def store_image_result(self, **kwargs):
                    nonlocal artifact_idx
                    result = mock_artifacts[artifact_idx]
                    artifact_idx += 1
                    return result

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

            result = await self.generator.generate(input_data, DummyCtx())

            # Verify result
            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 3

            # Verify file upload was called once for the reference image
            assert mock_fal_client.upload_file_async.call_count == 1

            # Verify API call
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["num_images"] == 3
            assert call_args[1]["arguments"]["style"] == "FICTION"
            assert call_args[1]["arguments"]["rendering_speed"] == "TURBO"

    @pytest.mark.asyncio
    async def test_generate_with_optional_parameters(self):
        """Test generation with optional mask and style images."""
        reference_image = ImageArtifact(
            generation_id="gen_reference",
            storage_url="https://example.com/character.png",
            format="png",
            width=1024,
            height=1024,
        )
        mask_image = ImageArtifact(
            generation_id="gen_mask",
            storage_url="https://example.com/mask.png",
            format="png",
            width=1024,
            height=1024,
        )
        style_image = ImageArtifact(
            generation_id="gen_style",
            storage_url="https://example.com/style.png",
            format="png",
            width=1024,
            height=1024,
        )

        input_data = IdeogramCharacterInput(
            prompt="Character in a specific style",
            reference_image_urls=[reference_image],
            reference_mask_urls=[mask_image],
            image_urls=[style_image],
            negative_prompt="ugly, blurry",
            seed=42,
            style_codes=["ABCD1234"],
        )

        fake_output_url = "https://v3.fal.media/files/monkey/output.png"
        fake_uploaded_urls = [
            "https://fal.media/files/uploaded-reference.png",
            "https://fal.media/files/uploaded-mask.png",
            "https://fal.media/files/uploaded-style.png",
        ]

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"
            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [
                        {
                            "url": fake_output_url,
                            "content_type": "image/png",
                            "file_name": "output.png",
                            "file_size": 1234567,
                        }
                    ],
                    "seed": 42,
                }
            )

            # Mock file uploads to return different URLs for each file
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

            mock_artifact = ImageArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1024,
                height=1024,
                format="png",
            )

            resolve_call_count = 0

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    nonlocal resolve_call_count
                    paths = ["/tmp/reference.png", "/tmp/mask.png", "/tmp/style.png"]
                    path = paths[resolve_call_count]
                    resolve_call_count += 1
                    return path

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

            result = await self.generator.generate(input_data, DummyCtx())

            # Verify result
            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1

            # Verify file uploads were called for all 3 images
            assert mock_fal_client.upload_file_async.call_count == 3

            # Verify API call included all optional parameters
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["negative_prompt"] == "ugly, blurry"
            assert call_args[1]["arguments"]["seed"] == 42
            assert call_args[1]["arguments"]["style_codes"] == ["ABCD1234"]
            assert call_args[1]["arguments"]["reference_mask_urls"] == [fake_uploaded_urls[1]]
            assert call_args[1]["arguments"]["image_urls"] == [fake_uploaded_urls[2]]

    @pytest.mark.asyncio
    async def test_estimate_cost_turbo(self):
        """Test cost estimation for TURBO rendering speed."""
        reference_image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/character.png",
            format="png",
            width=1024,
            height=1024,
        )

        input_data = IdeogramCharacterInput(
            prompt="Test prompt",
            reference_image_urls=[reference_image],
            rendering_speed="TURBO",
            num_images=1,
        )

        cost = await self.generator.estimate_cost(input_data)
        assert cost == 0.10
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_balanced(self):
        """Test cost estimation for BALANCED rendering speed."""
        reference_image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/character.png",
            format="png",
            width=1024,
            height=1024,
        )

        input_data = IdeogramCharacterInput(
            prompt="Test prompt",
            reference_image_urls=[reference_image],
            rendering_speed="BALANCED",
            num_images=1,
        )

        cost = await self.generator.estimate_cost(input_data)
        assert cost == 0.15
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_quality(self):
        """Test cost estimation for QUALITY rendering speed."""
        reference_image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/character.png",
            format="png",
            width=1024,
            height=1024,
        )

        input_data = IdeogramCharacterInput(
            prompt="Test prompt",
            reference_image_urls=[reference_image],
            rendering_speed="QUALITY",
            num_images=1,
        )

        cost = await self.generator.estimate_cost(input_data)
        assert cost == 0.20
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_multiple_images(self):
        """Test cost estimation for multiple images."""
        reference_image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/character.png",
            format="png",
            width=1024,
            height=1024,
        )

        input_data = IdeogramCharacterInput(
            prompt="Test prompt",
            reference_image_urls=[reference_image],
            rendering_speed="BALANCED",
            num_images=4,
        )

        cost = await self.generator.estimate_cost(input_data)
        # 0.15 * 4 = 0.60
        assert cost == 0.60
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = IdeogramCharacterInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "reference_image_urls" in schema["properties"]
        assert "image_size" in schema["properties"]
        assert "style" in schema["properties"]
        assert "rendering_speed" in schema["properties"]
        assert "num_images" in schema["properties"]

        # Check that reference_image_urls is an array
        reference_prop = schema["properties"]["reference_image_urls"]
        assert reference_prop["type"] == "array"
        assert "minItems" in reference_prop

        # Check that num_images has constraints
        num_images_prop = schema["properties"]["num_images"]
        assert num_images_prop["minimum"] == 1
        assert num_images_prop["maximum"] == 8
        assert num_images_prop["default"] == 1

        # Check that style has enum values
        style_prop = schema["properties"]["style"]
        assert "enum" in style_prop or "anyOf" in style_prop

        # Check that rendering_speed has enum values
        speed_prop = schema["properties"]["rendering_speed"]
        assert "enum" in speed_prop or "anyOf" in speed_prop
