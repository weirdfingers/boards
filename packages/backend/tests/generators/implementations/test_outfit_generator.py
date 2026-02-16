"""
Tests for OutfitGenerator.
"""

import os
import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from boards.generators.artifacts import ImageArtifact
from boards.generators.base import GeneratorExecutionContext, GeneratorResult
from boards.generators.implementations.fal.image.outfit_generator import (
    OutfitGenerator,
    OutfitGeneratorInput,
)


def _make_artifact(gen_id: str = "gen1", url: str = "https://example.com/img.png") -> ImageArtifact:
    """Helper to create a test ImageArtifact."""
    return ImageArtifact(
        generation_id=gen_id,
        storage_url=url,
        format="png",
        width=1024,
        height=1024,
    )


class TestOutfitGeneratorInput:
    """Tests for OutfitGeneratorInput schema."""

    def test_valid_input_single_garment(self):
        """Test valid input with one garment."""
        input_data = OutfitGeneratorInput(
            model_image=_make_artifact("model"),
            bottoms_image=_make_artifact("bottoms"),
        )
        assert input_data.model_image.generation_id == "model"
        assert input_data.bottoms_image is not None
        assert input_data.inside_top_image is None

    def test_valid_input_all_garments(self):
        """Test valid input with all garment slots filled."""
        input_data = OutfitGeneratorInput(
            model_image=_make_artifact("model"),
            socks_image=_make_artifact("socks"),
            inside_top_image=_make_artifact("inside_top"),
            bottoms_image=_make_artifact("bottoms"),
            outside_top_image=_make_artifact("outside_top"),
            shoes_image=_make_artifact("shoes"),
            hat_image=_make_artifact("hat"),
        )
        assert input_data.socks_image is not None
        assert input_data.hat_image is not None

    def test_no_garments_rejected(self):
        """Test validation fails when no garment is provided."""
        with pytest.raises(ValidationError, match="At least one garment"):
            OutfitGeneratorInput(
                model_image=_make_artifact("model"),
            )

    def test_all_garments_none_rejected(self):
        """Test validation fails when all garments are explicitly None."""
        with pytest.raises(ValidationError, match="At least one garment"):
            OutfitGeneratorInput(
                model_image=_make_artifact("model"),
                inside_top_image=None,
                outside_top_image=None,
                bottoms_image=None,
                shoes_image=None,
                socks_image=None,
                hat_image=None,
            )

    def test_defaults_are_none(self):
        """Test that all garment slots default to None."""
        input_data = OutfitGeneratorInput(
            model_image=_make_artifact("model"),
            hat_image=_make_artifact("hat"),  # Need at least one
        )
        assert input_data.inside_top_image is None
        assert input_data.outside_top_image is None
        assert input_data.bottoms_image is None
        assert input_data.shoes_image is None
        assert input_data.socks_image is None


class TestOutfitGeneratorMetadata:
    """Tests for OutfitGenerator metadata."""

    def setup_method(self):
        self.generator = OutfitGenerator()

    def test_name(self):
        assert self.generator.name == "outfit-generator"

    def test_artifact_type(self):
        assert self.generator.artifact_type == "image"

    def test_description(self):
        desc = self.generator.description.lower()
        assert "garment" in desc or "outfit" in desc

    def test_input_schema(self):
        assert self.generator.get_input_schema() == OutfitGeneratorInput


async def _empty_async_event_iterator():
    """Helper to create an empty async iterator for mock event streams."""
    if False:
        yield  # Makes this an async generator


def _make_mock_handler(request_id: str, result_url: str):
    """Helper to create a mock fal_client handler."""
    handler = MagicMock()
    handler.request_id = request_id
    handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
    handler.get = AsyncMock(
        return_value={
            "image": {
                "url": result_url,
                "content_type": "image/png",
                "width": 768,
                "height": 1024,
            },
        }
    )
    return handler


class TestOutfitGeneratorGenerate:
    """Tests for OutfitGenerator.generate()."""

    def setup_method(self):
        self.generator = OutfitGenerator()

    @pytest.mark.asyncio
    async def test_generate_missing_api_key(self, dummy_context):
        """Test generation fails when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            input_data = OutfitGeneratorInput(
                model_image=_make_artifact("model"),
                bottoms_image=_make_artifact("bottoms"),
            )
            with pytest.raises(ValueError, match="FAL_KEY"):
                await self.generator.generate(input_data, dummy_context)

    @pytest.mark.asyncio
    async def test_generate_single_garment(self, dummy_context):
        """Test generation with a single garment makes one Kolors call."""
        input_data = OutfitGeneratorInput(
            model_image=_make_artifact("model", "https://example.com/model.png"),
            bottoms_image=_make_artifact("bottoms", "https://example.com/bottoms.png"),
        )

        result_url = "https://fal.media/result/final.png"
        mock_handler = _make_mock_handler("req-1", result_url)

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(  # type: ignore[attr-defined]
                return_value="https://fal.media/uploaded.png"
            )
            sys.modules["fal_client"] = mock_fal_client

            result = await self.generator.generate(input_data, dummy_context)

            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1

            # Verify only one Kolors call
            assert mock_fal_client.submit_async.call_count == 1
            call_args = mock_fal_client.submit_async.call_args
            assert call_args[0][0] == "fal-ai/kling/v1-5/kolors-virtual-try-on"

    @pytest.mark.asyncio
    async def test_generate_multiple_garments_correct_order(self, dummy_context):
        """Test that multiple garments are applied in layering order."""
        input_data = OutfitGeneratorInput(
            model_image=_make_artifact("model", "https://example.com/model.png"),
            hat_image=_make_artifact("hat", "https://example.com/hat.png"),
            inside_top_image=_make_artifact("top", "https://example.com/top.png"),
            bottoms_image=_make_artifact("bottoms", "https://example.com/bottoms.png"),
        )

        # Each Kolors call returns a different URL
        result_urls = [
            "https://fal.media/result/step1.png",
            "https://fal.media/result/step2.png",
            "https://fal.media/result/step3.png",
        ]
        handlers = [_make_mock_handler(f"req-{i}", url) for i, url in enumerate(result_urls)]
        handler_idx = 0

        async def mock_submit(endpoint, arguments):
            nonlocal handler_idx
            h = handlers[handler_idx]
            handler_idx += 1
            return h

        upload_idx = 0
        upload_urls = [
            "https://fal.media/model.png",
            "https://fal.media/top.png",
            "https://fal.media/bottoms.png",
            "https://fal.media/hat.png",
        ]

        async def mock_upload(file_path):
            nonlocal upload_idx
            url = upload_urls[upload_idx]
            upload_idx += 1
            return url

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(side_effect=mock_submit)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(side_effect=mock_upload)  # type: ignore[attr-defined]
            sys.modules["fal_client"] = mock_fal_client

            result = await self.generator.generate(input_data, dummy_context)

            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1

            # 3 garments = 3 Kolors calls
            assert mock_fal_client.submit_async.call_count == 3

            # Verify layering order: Inside Top → Bottoms → Hat
            calls = mock_fal_client.submit_async.call_args_list

            # First call: model image + inside top
            assert calls[0][1]["arguments"]["human_image_url"] == "https://fal.media/model.png"

            # Second call: result of step 1 + bottoms (uses Fal result URL directly)
            assert calls[1][1]["arguments"]["human_image_url"] == result_urls[0]

            # Third call: result of step 2 + hat
            assert calls[2][1]["arguments"]["human_image_url"] == result_urls[1]

    @pytest.mark.asyncio
    async def test_generate_all_garments(self, dummy_context):
        """Test generation with all 6 garment slots filled."""
        input_data = OutfitGeneratorInput(
            model_image=_make_artifact("model"),
            socks_image=_make_artifact("socks"),
            inside_top_image=_make_artifact("inside_top"),
            bottoms_image=_make_artifact("bottoms"),
            outside_top_image=_make_artifact("outside_top"),
            shoes_image=_make_artifact("shoes"),
            hat_image=_make_artifact("hat"),
        )

        handlers = [
            _make_mock_handler(f"req-{i}", f"https://fal.media/result/step{i}.png")
            for i in range(6)
        ]
        handler_idx = 0

        async def mock_submit(endpoint, arguments):
            nonlocal handler_idx
            h = handlers[handler_idx]
            handler_idx += 1
            return h

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(side_effect=mock_submit)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(  # type: ignore[attr-defined]
                return_value="https://fal.media/uploaded.png"
            )
            sys.modules["fal_client"] = mock_fal_client

            result = await self.generator.generate(input_data, dummy_context)

            assert isinstance(result, GeneratorResult)
            assert len(result.outputs) == 1
            # 6 garments = 6 Kolors calls
            assert mock_fal_client.submit_async.call_count == 6

    @pytest.mark.asyncio
    async def test_generate_publishes_progress(self):
        """Test that progress messages are published with slot names and step counts."""
        input_data = OutfitGeneratorInput(
            model_image=_make_artifact("model"),
            inside_top_image=_make_artifact("top"),
            shoes_image=_make_artifact("shoes"),
        )

        handlers = [
            _make_mock_handler(f"req-{i}", f"https://fal.media/result/step{i}.png")
            for i in range(2)
        ]
        handler_idx = 0

        async def mock_submit(endpoint, arguments):
            nonlocal handler_idx
            h = handlers[handler_idx]
            handler_idx += 1
            return h

        progress_messages: list[str] = []

        class ProgressTrackingContext(GeneratorExecutionContext):
            generation_id = "test_gen"

            async def resolve_artifact(self, artifact):
                return "/tmp/fake.png"

            async def store_image_result(
                self,
                storage_url,
                format,
                width=None,
                height=None,
                output_index=0,
            ):
                return ImageArtifact(
                    generation_id="test_gen",
                    storage_url=storage_url,
                    width=width,
                    height=height,
                    format=format,
                )

            async def store_video_result(self, *args, **kwargs):
                raise NotImplementedError

            async def store_audio_result(self, *args, **kwargs):
                raise NotImplementedError

            async def store_text_result(self, *args, **kwargs):
                raise NotImplementedError

            async def publish_progress(self, update):
                if update.message:
                    progress_messages.append(update.message)

            async def set_external_job_id(self, external_id):
                pass

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(side_effect=mock_submit)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(  # type: ignore[attr-defined]
                return_value="https://fal.media/uploaded.png"
            )
            sys.modules["fal_client"] = mock_fal_client

            await self.generator.generate(input_data, ProgressTrackingContext())

        # Verify progress messages include slot names and step counts
        assert any("Initializing" in msg for msg in progress_messages)
        assert any("Inside Top" in msg and "1/2" in msg for msg in progress_messages)
        assert any("Shoes" in msg and "2/2" in msg for msg in progress_messages)
        assert any("Finalizing" in msg for msg in progress_messages)

    @pytest.mark.asyncio
    async def test_generate_kolors_failure_raises(self, dummy_context):
        """Test that a Kolors API failure raises an error."""
        input_data = OutfitGeneratorInput(
            model_image=_make_artifact("model"),
            bottoms_image=_make_artifact("bottoms"),
        )

        mock_handler = MagicMock()
        mock_handler.request_id = "req-fail"
        mock_handler.iter_events = MagicMock(return_value=_empty_async_event_iterator())
        mock_handler.get = AsyncMock(return_value={})  # No "image" key

        with patch.dict(os.environ, {"FAL_KEY": "fake-key"}):
            mock_fal_client = ModuleType("fal_client")
            mock_fal_client.submit_async = AsyncMock(return_value=mock_handler)  # type: ignore[attr-defined]
            mock_fal_client.upload_file_async = AsyncMock(  # type: ignore[attr-defined]
                return_value="https://fal.media/uploaded.png"
            )
            sys.modules["fal_client"] = mock_fal_client

            with pytest.raises(ValueError, match="No image returned"):
                await self.generator.generate(input_data, dummy_context)


class TestOutfitGeneratorEstimateCost:
    """Tests for OutfitGenerator.estimate_cost()."""

    def setup_method(self):
        self.generator = OutfitGenerator()

    @pytest.mark.asyncio
    async def test_single_garment_cost(self):
        """One garment = $0.05."""
        input_data = OutfitGeneratorInput(
            model_image=_make_artifact("model"),
            bottoms_image=_make_artifact("bottoms"),
        )
        cost = await self.generator.estimate_cost(input_data)
        assert cost == 0.05

    @pytest.mark.asyncio
    async def test_three_garments_cost(self):
        """Three garments = $0.15."""
        input_data = OutfitGeneratorInput(
            model_image=_make_artifact("model"),
            inside_top_image=_make_artifact("top"),
            bottoms_image=_make_artifact("bottoms"),
            shoes_image=_make_artifact("shoes"),
        )
        cost = await self.generator.estimate_cost(input_data)
        assert cost == pytest.approx(0.15)

    @pytest.mark.asyncio
    async def test_all_garments_cost(self):
        """Six garments = $0.30."""
        input_data = OutfitGeneratorInput(
            model_image=_make_artifact("model"),
            socks_image=_make_artifact("socks"),
            inside_top_image=_make_artifact("top"),
            bottoms_image=_make_artifact("bottoms"),
            outside_top_image=_make_artifact("outside"),
            shoes_image=_make_artifact("shoes"),
            hat_image=_make_artifact("hat"),
        )
        cost = await self.generator.estimate_cost(input_data)
        assert cost == pytest.approx(0.30)

    def test_json_schema_generation(self):
        """Test that input schema can generate JSON schema for frontend."""
        schema = OutfitGeneratorInput.model_json_schema()

        assert schema["type"] == "object"
        assert "model_image" in schema["properties"]
        assert "inside_top_image" in schema["properties"]
        assert "outside_top_image" in schema["properties"]
        assert "bottoms_image" in schema["properties"]
        assert "shoes_image" in schema["properties"]
        assert "socks_image" in schema["properties"]
        assert "hat_image" in schema["properties"]

        # model_image should be required
        assert "model_image" in schema.get("required", [])
