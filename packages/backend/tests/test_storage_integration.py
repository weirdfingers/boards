"""Tests for storage system integration with artifact resolution."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from boards.generators.artifacts import ImageArtifact
from boards.generators.resolution import (
    download_from_url,
    store_image_result,
)
from boards.storage.factory import create_development_storage
from boards.workers.context import GeneratorExecutionContext


def create_mock_http_response(content: bytes):
    """Helper to create a properly mocked streaming HTTP response."""
    mock_response = AsyncMock()
    # raise_for_status is not async in httpx
    mock_response.raise_for_status = MagicMock()

    # Mock aiter_bytes to return content in chunks
    async def mock_aiter_bytes(chunk_size=8192):
        if content:
            yield content

    mock_response.aiter_bytes = mock_aiter_bytes
    return mock_response


def create_mock_stream_context(content: bytes):
    """Helper to create a mock streaming context manager."""
    mock_stream_context = MagicMock()
    # Make it an async context manager
    mock_stream_context.__aenter__ = AsyncMock(return_value=create_mock_http_response(content))
    mock_stream_context.__aexit__ = AsyncMock(return_value=None)
    return mock_stream_context


@pytest.mark.asyncio
async def test_download_from_url():
    """Test downloading content from a URL."""
    test_content = b"fake image data"
    test_url = "https://example.com/test.png"

    with patch("httpx.AsyncClient") as mock_client:
        # stream() should return the context manager directly, not as a coroutine
        mock_client.return_value.__aenter__.return_value.stream = MagicMock(
            return_value=create_mock_stream_context(test_content)
        )

        # Test successful download
        content = await download_from_url(test_url)
        assert content == test_content


@pytest.mark.asyncio
async def test_download_from_url_empty_content():
    """Test that empty content raises an error."""
    test_url = "https://example.com/empty.png"

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.stream = MagicMock(
            return_value=create_mock_stream_context(b"")
        )

        # Test empty content raises error
        with pytest.raises(ValueError, match="empty"):
            await download_from_url(test_url)


@pytest.mark.asyncio
async def test_store_image_result_integration(tmp_path: Path):
    """Test full integration of storing an image result."""
    from boards.storage.implementations.local import LocalStorageProvider

    # Create a development storage manager
    storage_manager = create_development_storage()

    # Override the local storage path to use tmp_path
    local_provider = storage_manager.providers["local"]
    assert isinstance(local_provider, LocalStorageProvider)
    local_provider.base_path = tmp_path / "storage"
    local_provider.base_path.mkdir(parents=True, exist_ok=True)

    # Test data
    generation_id = str(uuid4())
    tenant_id = str(uuid4())
    board_id = str(uuid4())
    test_image_data = b"fake PNG data"
    provider_url = "https://replicate.delivery/test.png"

    # Mock the HTTP download
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.stream = MagicMock(
            return_value=create_mock_stream_context(test_image_data)
        )

        # Store the image result
        artifact = await store_image_result(
            storage_manager=storage_manager,
            generation_id=generation_id,
            tenant_id=tenant_id,
            board_id=board_id,
            storage_url=provider_url,
            format="png",
            width=1024,
            height=1024,
        )

        # Verify artifact properties
        assert isinstance(artifact, ImageArtifact)
        assert artifact.generation_id == generation_id
        assert artifact.format == "png"
        assert artifact.width == 1024
        assert artifact.height == 1024

        # Verify storage URL is not the provider URL
        assert artifact.storage_url != provider_url

        # For local storage, verify the file exists
        # The storage URL for local provider should contain the storage path
        assert "storage" in artifact.storage_url or artifact.storage_url.startswith("file://")


@pytest.mark.asyncio
async def test_execution_context_store_methods(tmp_path: Path):
    """Test execution context storage methods."""
    from boards.storage.implementations.local import LocalStorageProvider

    # Create storage manager
    storage_manager = create_development_storage()
    local_provider = storage_manager.providers["local"]
    assert isinstance(local_provider, LocalStorageProvider)
    local_provider.base_path = tmp_path / "storage"
    local_provider.base_path.mkdir(parents=True, exist_ok=True)

    # Create mock progress publisher
    from boards.config import Settings
    from boards.progress.publisher import ProgressPublisher

    settings = Settings()
    publisher = ProgressPublisher(settings)

    # Mock the publish and persist methods
    async def fake_publish(job_id, update):
        pass

    async def fake_persist(job_id, update):
        pass

    publisher.publish_progress = fake_publish  # type: ignore
    publisher._persist_update = fake_persist  # type: ignore

    # Create execution context
    generation_id = uuid4()
    tenant_id = uuid4()
    board_id = uuid4()

    context = GeneratorExecutionContext(
        generation_id=generation_id,
        publisher=publisher,
        storage_manager=storage_manager,
        tenant_id=tenant_id,
        board_id=board_id,
    )

    # Test storing image via context
    test_image_data = b"context test image"
    provider_url = "https://example.com/context-test.png"

    # Mock HTTP download
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.stream = MagicMock(
            return_value=create_mock_stream_context(test_image_data)
        )

        artifact = await context.store_image_result(
            storage_url=provider_url, format="png", width=512, height=512
        )

        assert isinstance(artifact, ImageArtifact)
        assert artifact.generation_id == str(generation_id)
        assert artifact.width == 512
        assert artifact.height == 512


@pytest.mark.asyncio
async def test_worker_integration_with_storage(monkeypatch, tmp_path: Path):
    """Test that the worker actor properly integrates with storage."""
    import sys
    from types import ModuleType
    from unittest.mock import AsyncMock, MagicMock

    # Mock Redis client FIRST, before any imports that use it
    # We need to mock at the RedisPoolManager level since it's a singleton
    mock_redis = MagicMock()
    mock_redis.publish = AsyncMock()

    from boards import redis_pool

    # Mock the singleton's client property
    monkeypatch.setattr(redis_pool._redis_pool_manager, "_client", mock_redis)
    monkeypatch.setattr(redis_pool, "get_redis_client", lambda: mock_redis)

    # Mock replicate module
    mock_file_output = SimpleNamespace(url="https://replicate.delivery/fake.png")
    mock_helpers = ModuleType("helpers")
    mock_helpers.FileOutput = MagicMock  # type: ignore[attr-defined]

    mock_replicate = ModuleType("replicate")
    mock_replicate.async_run = AsyncMock(return_value=mock_file_output)  # type: ignore[attr-defined]
    mock_replicate.helpers = mock_helpers  # type: ignore[attr-defined]

    sys.modules["replicate"] = mock_replicate
    sys.modules["replicate.helpers"] = mock_helpers

    # Register generator
    from boards.generators.implementations.image.flux_pro import FluxProGenerator
    from boards.generators.registry import registry
    from boards.jobs import repository as jobs_repo

    try:
        registry.register(FluxProGenerator())
    except Exception:
        pass

    from boards.progress.publisher import ProgressPublisher

    # Track storage operations
    stored_url = None

    async def fake_get_generation(session, generation_id):
        return SimpleNamespace(
            id=generation_id,
            generator_name="flux-pro",
            input_params={
                "prompt": "test prompt",
                "aspect_ratio": "1:1",
                "safety_tolerance": 2,
            },
            tenant_id=uuid4(),
            board_id=uuid4(),
        )

    async def fake_finalize_success(session, generation_id, **kwargs):
        nonlocal stored_url
        stored_url = kwargs.get("storage_url")
        return None

    async def fake_persist(self, job_id, update):
        return None

    monkeypatch.setattr(jobs_repo, "get_generation", fake_get_generation)
    monkeypatch.setattr(jobs_repo, "finalize_success", fake_finalize_success)
    monkeypatch.setattr(ProgressPublisher, "_persist_update", fake_persist, raising=False)

    # Mock storage manager creation to use tmp_path
    from boards.storage import factory
    from boards.storage.base import StorageConfig

    def mock_create_storage_manager(*args, **kwargs):
        from boards.storage.base import StorageManager
        from boards.storage.implementations.local import LocalStorageProvider

        storage_path = tmp_path / "storage"
        storage_path.mkdir(parents=True, exist_ok=True)

        config = StorageConfig(
            default_provider="local",
            providers={},
            routing_rules=[{"provider": "local"}],
        )
        manager = StorageManager(config)
        provider = LocalStorageProvider(
            base_path=storage_path, public_url_base="http://localhost/storage"
        )
        manager.register_provider("local", provider)
        return manager

    monkeypatch.setattr(factory, "create_storage_manager", mock_create_storage_manager)

    # Set environment variables
    import os

    os.environ["REPLICATE_API_TOKEN"] = "test-token"

    # Mock HTTP download
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.stream = MagicMock(
            return_value=create_mock_stream_context(b"fake image content")
        )

        # Execute worker
        from boards.workers.actors import process_generation

        original_fn = process_generation.fn.__wrapped__
        await original_fn("00000000-0000-0000-0000-00000000a1a1")

        # Verify storage URL was saved
        assert stored_url is not None
        assert "storage" in stored_url or stored_url.startswith("file://")
