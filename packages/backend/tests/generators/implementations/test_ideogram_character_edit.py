"""
Tests for FalIdeogramCharacterEditGenerator.
"""

import os
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.ideogram_character_edit import (
    ColorPalette,
    ColorPaletteMember,
    FalIdeogramCharacterEditGenerator,
    IdeogramCharacterEditInput,
    RGBColor,
)


class TestIdeogramCharacterEditInput:
    """Tests for IdeogramCharacterEditInput schema."""

    def test_valid_input(self):
        """Test valid input creation with required fields."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=1024,
        )
        mask = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/mask.png",
            format="png",
            width=1024,
            height=1024,
        )
        reference = ImageArtifact(
            generation_id="gen3",
            storage_url="https://example.com/reference.png",
            format="png",
            width=512,
            height=512,
        )

        input_data = IdeogramCharacterEditInput(
            prompt="Change the character's expression to happy",
            image_url=image,
            mask_url=mask,
            reference_image_urls=[reference],
        )

        assert input_data.prompt == "Change the character's expression to happy"
        assert input_data.image_url == image
        assert input_data.mask_url == mask
        assert len(input_data.reference_image_urls) == 1

    def test_input_defaults(self):
        """Test default values."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=1024,
        )
        mask = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/mask.png",
            format="png",
            width=1024,
            height=1024,
        )
        reference = ImageArtifact(
            generation_id="gen3",
            storage_url="https://example.com/reference.png",
            format="png",
            width=512,
            height=512,
        )

        input_data = IdeogramCharacterEditInput(
            prompt="Test prompt",
            image_url=image,
            mask_url=mask,
            reference_image_urls=[reference],
        )

        assert input_data.style == "AUTO"
        assert input_data.expand_prompt is True
        assert input_data.rendering_speed == "BALANCED"
        assert input_data.reference_mask_urls is None
        assert input_data.image_urls is None
        assert input_data.num_images == 1
        assert input_data.style_codes is None
        assert input_data.color_palette is None
        assert input_data.sync_mode is False
        assert input_data.seed is None

    def test_invalid_style(self):
        """Test validation fails for invalid style."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=1024,
        )
        mask = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/mask.png",
            format="png",
            width=1024,
            height=1024,
        )
        reference = ImageArtifact(
            generation_id="gen3",
            storage_url="https://example.com/reference.png",
            format="png",
            width=512,
            height=512,
        )

        with pytest.raises(ValidationError):
            IdeogramCharacterEditInput(
                prompt="Test",
                image_url=image,
                mask_url=mask,
                reference_image_urls=[reference],
                style="INVALID",  # type: ignore[arg-type]
            )

    def test_invalid_rendering_speed(self):
        """Test validation fails for invalid rendering speed."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=1024,
        )
        mask = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/mask.png",
            format="png",
            width=1024,
            height=1024,
        )
        reference = ImageArtifact(
            generation_id="gen3",
            storage_url="https://example.com/reference.png",
            format="png",
            width=512,
            height=512,
        )

        with pytest.raises(ValidationError):
            IdeogramCharacterEditInput(
                prompt="Test",
                image_url=image,
                mask_url=mask,
                reference_image_urls=[reference],
                rendering_speed="INVALID",  # type: ignore[arg-type]
            )

    def test_empty_reference_images(self):
        """Test validation fails for empty reference_image_urls."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=1024,
        )
        mask = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/mask.png",
            format="png",
            width=1024,
            height=1024,
        )

        with pytest.raises(ValidationError):
            IdeogramCharacterEditInput(
                prompt="Test",
                image_url=image,
                mask_url=mask,
                reference_image_urls=[],  # Empty list should fail min_length=1
            )

    def test_num_images_validation(self):
        """Test validation for num_images constraints."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=1024,
        )
        mask = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/mask.png",
            format="png",
            width=1024,
            height=1024,
        )
        reference = ImageArtifact(
            generation_id="gen3",
            storage_url="https://example.com/reference.png",
            format="png",
            width=512,
            height=512,
        )

        # Test below minimum
        with pytest.raises(ValidationError):
            IdeogramCharacterEditInput(
                prompt="Test",
                image_url=image,
                mask_url=mask,
                reference_image_urls=[reference],
                num_images=0,
            )

        # Test above maximum
        with pytest.raises(ValidationError):
            IdeogramCharacterEditInput(
                prompt="Test",
                image_url=image,
                mask_url=mask,
                reference_image_urls=[reference],
                num_images=9,
            )

    def test_style_options(self):
        """Test all valid style options."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=1024,
        )
        mask = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/mask.png",
            format="png",
            width=1024,
            height=1024,
        )
        reference = ImageArtifact(
            generation_id="gen3",
            storage_url="https://example.com/reference.png",
            format="png",
            width=512,
            height=512,
        )

        valid_styles = ["AUTO", "REALISTIC", "FICTION"]

        for style in valid_styles:
            input_data = IdeogramCharacterEditInput(
                prompt="Test",
                image_url=image,
                mask_url=mask,
                reference_image_urls=[reference],
                style=style,  # type: ignore[arg-type]
            )
            assert input_data.style == style

    def test_rendering_speed_options(self):
        """Test all valid rendering speed options."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=1024,
        )
        mask = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/mask.png",
            format="png",
            width=1024,
            height=1024,
        )
        reference = ImageArtifact(
            generation_id="gen3",
            storage_url="https://example.com/reference.png",
            format="png",
            width=512,
            height=512,
        )

        valid_speeds = ["TURBO", "BALANCED", "QUALITY"]

        for speed in valid_speeds:
            input_data = IdeogramCharacterEditInput(
                prompt="Test",
                image_url=image,
                mask_url=mask,
                reference_image_urls=[reference],
                rendering_speed=speed,  # type: ignore[arg-type]
            )
            assert input_data.rendering_speed == speed

    def test_color_palette_preset(self):
        """Test color palette with preset name."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=1024,
        )
        mask = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/mask.png",
            format="png",
            width=1024,
            height=1024,
        )
        reference = ImageArtifact(
            generation_id="gen3",
            storage_url="https://example.com/reference.png",
            format="png",
            width=512,
            height=512,
        )

        palette = ColorPalette(name="EMBER")

        input_data = IdeogramCharacterEditInput(
            prompt="Test",
            image_url=image,
            mask_url=mask,
            reference_image_urls=[reference],
            color_palette=palette,
        )

        assert input_data.color_palette is not None
        assert input_data.color_palette.name == "EMBER"

    def test_color_palette_custom(self):
        """Test color palette with custom RGB colors."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=1024,
        )
        mask = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/mask.png",
            format="png",
            width=1024,
            height=1024,
        )
        reference = ImageArtifact(
            generation_id="gen3",
            storage_url="https://example.com/reference.png",
            format="png",
            width=512,
            height=512,
        )

        palette = ColorPalette(
            members=[
                ColorPaletteMember(
                    rgb=RGBColor(r=255, g=0, b=0),
                    color_weight=0.7,
                ),
                ColorPaletteMember(
                    rgb=RGBColor(r=0, g=255, b=0),
                    color_weight=0.3,
                ),
            ]
        )

        input_data = IdeogramCharacterEditInput(
            prompt="Test",
            image_url=image,
            mask_url=mask,
            reference_image_urls=[reference],
            color_palette=palette,
        )

        assert input_data.color_palette is not None
        assert input_data.color_palette.members is not None
        assert len(input_data.color_palette.members) == 2
        assert input_data.color_palette.members[0].rgb.r == 255
        assert input_data.color_palette.members[1].color_weight == 0.3


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


class TestFalIdeogramCharacterEditGenerator:
    """Tests for FalIdeogramCharacterEditGenerator."""

    def setup_method(self):
        """Set up generator for testing."""
        self.generator = FalIdeogramCharacterEditGenerator()

    def test_generator_metadata(self):
        """Test generator metadata."""
        assert self.generator.name == "fal-ideogram-character-edit"
        assert self.generator.artifact_type == "image"
        assert "character" in self.generator.description.lower()
        assert "Ideogram" in self.generator.description

    def test_input_schema(self):
        """Test input schema."""
        schema_class = self.generator.get_input_schema()
        assert schema_class == IdeogramCharacterEditInput

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            image = ImageArtifact(
                generation_id="gen1",
                storage_url="https://example.com/image.png",
                format="png",
                width=1024,
                height=1024,
            )
            mask = ImageArtifact(
                generation_id="gen2",
                storage_url="https://example.com/mask.png",
                format="png",
                width=1024,
                height=1024,
            )
            reference = ImageArtifact(
                generation_id="gen3",
                storage_url="https://example.com/reference.png",
                format="png",
                width=512,
                height=512,
            )

            input_data = IdeogramCharacterEditInput(
                prompt="Test prompt",
                image_url=image,
                mask_url=mask,
                reference_image_urls=[reference],
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
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=1024,
        )
        mask = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/mask.png",
            format="png",
            width=1024,
            height=1024,
        )
        reference = ImageArtifact(
            generation_id="gen3",
            storage_url="https://example.com/reference.png",
            format="png",
            width=512,
            height=512,
        )

        input_data = IdeogramCharacterEditInput(
            prompt="Change the character's clothing to a red dress",
            image_url=image,
            mask_url=mask,
            reference_image_urls=[reference],
            num_images=1,
        )

        fake_output_url = "https://storage.googleapis.com/falserverless/output.png"
        fake_uploaded_urls = {
            "image": "https://fal.media/files/uploaded-image.png",
            "mask": "https://fal.media/files/uploaded-mask.png",
            "reference": "https://fal.media/files/uploaded-reference.png",
        }

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            # Create mock handler
            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-123"

            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())

            # Mock the get() method to return result
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [
                        {
                            "url": fake_output_url,
                            "content_type": "image/webp",
                            "width": 1024,
                            "height": 1024,
                        }
                    ],
                    "seed": 42,
                }
            )

            # Track upload calls
            upload_call_count = 0

            async def mock_upload(file_path):
                nonlocal upload_call_count
                upload_call_count += 1
                if upload_call_count == 1:
                    return fake_uploaded_urls["image"]
                elif upload_call_count == 2:
                    return fake_uploaded_urls["mask"]
                else:
                    return fake_uploaded_urls["reference"]

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]

            sys.modules["fal_client"] = mock_fal_client

            # Mock storage result
            mock_artifact = ImageArtifact(
                generation_id="test_gen",
                storage_url=fake_output_url,
                width=1024,
                height=1024,
                format="webp",
            )

            # Execute generation
            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return f"/tmp/fake_{artifact.generation_id}.png"

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

            # Verify file uploads were called (3 total: image, mask, reference)
            assert mock_fal_client.upload_file_async.call_count == 3

            # Verify API call
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[0][0] == "fal-ai/ideogram/character/edit"
            assert (
                call_args[1]["arguments"]["prompt"]
                == "Change the character's clothing to a red dress"
            )
            assert call_args[1]["arguments"]["image_url"] == fake_uploaded_urls["image"]
            assert call_args[1]["arguments"]["mask_url"] == fake_uploaded_urls["mask"]
            assert call_args[1]["arguments"]["reference_image_urls"] == [
                fake_uploaded_urls["reference"]
            ]

    @pytest.mark.asyncio
    async def test_generate_successful_multiple_images(self):
        """Test successful generation with multiple image outputs."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=1024,
        )
        mask = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/mask.png",
            format="png",
            width=1024,
            height=1024,
        )
        reference = ImageArtifact(
            generation_id="gen3",
            storage_url="https://example.com/reference.png",
            format="png",
            width=512,
            height=512,
        )

        input_data = IdeogramCharacterEditInput(
            prompt="Make the character smile",
            image_url=image,
            mask_url=mask,
            reference_image_urls=[reference],
            num_images=3,
            rendering_speed="TURBO",
        )

        fake_output_urls = [
            "https://storage.googleapis.com/falserverless/output1.png",
            "https://storage.googleapis.com/falserverless/output2.png",
            "https://storage.googleapis.com/falserverless/output3.png",
        ]

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-456"

            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(
                return_value={
                    "images": [
                        {"url": url, "content_type": "image/png", "width": 1024, "height": 1024}
                        for url in fake_output_urls
                    ],
                    "seed": 123,
                }
            )

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(return_value="https://fal.media/files/uploaded.png")  # type: ignore[attr-defined]
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
                    return f"/tmp/fake_{artifact.generation_id}.png"

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

            # Verify rendering_speed was passed
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[1]["arguments"]["rendering_speed"] == "TURBO"

    @pytest.mark.asyncio
    async def test_generate_no_images_returned(self):
        """Test generation fails when API returns no images."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=1024,
        )
        mask = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/mask.png",
            format="png",
            width=1024,
            height=1024,
        )
        reference = ImageArtifact(
            generation_id="gen3",
            storage_url="https://example.com/reference.png",
            format="png",
            width=512,
            height=512,
        )

        input_data = IdeogramCharacterEditInput(
            prompt="test",
            image_url=image,
            mask_url=mask,
            reference_image_urls=[reference],
        )

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            import sys

            mock_handler = MagicMock()
            mock_handler.request_id = "test-request-789"

            mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
            mock_handler.get = AsyncMock(return_value={"images": [], "seed": 0})

            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(return_value="https://fal.media/files/uploaded.png")  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            class DummyCtx(GeneratorExecutionContext):
                generation_id = "test_gen"
                provider_correlation_id = "corr"
                tenant_id = "test_tenant"
                board_id = "test_board"

                async def resolve_artifact(self, artifact):
                    return "/tmp/fake.png"

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

            with pytest.raises(ValueError, match="No images returned"):
                await self.generator.generate(input_data, DummyCtx())

    @pytest.mark.asyncio
    async def test_estimate_cost(self):
        """Test cost estimation."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=1024,
        )
        mask = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/mask.png",
            format="png",
            width=1024,
            height=1024,
        )
        reference = ImageArtifact(
            generation_id="gen3",
            storage_url="https://example.com/reference.png",
            format="png",
            width=512,
            height=512,
        )

        input_data = IdeogramCharacterEditInput(
            prompt="Test prompt",
            image_url=image,
            mask_url=mask,
            reference_image_urls=[reference],
            num_images=1,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Per-image cost (0.05 * 1)
        assert cost == 0.05
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_estimate_cost_multiple_images(self):
        """Test cost estimation for multiple images."""
        image = ImageArtifact(
            generation_id="gen1",
            storage_url="https://example.com/image.png",
            format="png",
            width=1024,
            height=1024,
        )
        mask = ImageArtifact(
            generation_id="gen2",
            storage_url="https://example.com/mask.png",
            format="png",
            width=1024,
            height=1024,
        )
        reference = ImageArtifact(
            generation_id="gen3",
            storage_url="https://example.com/reference.png",
            format="png",
            width=512,
            height=512,
        )

        input_data = IdeogramCharacterEditInput(
            prompt="Test prompt",
            image_url=image,
            mask_url=mask,
            reference_image_urls=[reference],
            num_images=4,
        )

        cost = await self.generator.estimate_cost(input_data)

        # Per-image cost (0.05 * 4)
        assert cost == 0.20
        assert isinstance(cost, float)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = IdeogramCharacterEditInput.model_json_schema()

        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "image_url" in schema["properties"]
        assert "mask_url" in schema["properties"]
        assert "reference_image_urls" in schema["properties"]
        assert "style" in schema["properties"]
        assert "rendering_speed" in schema["properties"]
        assert "num_images" in schema["properties"]
        assert "color_palette" in schema["properties"]

        # Check that reference_image_urls is an array
        reference_images_prop = schema["properties"]["reference_image_urls"]
        assert reference_images_prop["type"] == "array"
        assert "minItems" in reference_images_prop

        # Check that num_images has constraints
        num_images_prop = schema["properties"]["num_images"]
        assert num_images_prop["minimum"] == 1
        assert num_images_prop["maximum"] == 8
        assert num_images_prop["default"] == 1
