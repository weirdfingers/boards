from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from boards.workers.actors import process_generation


@pytest.mark.asyncio
async def test_worker_integration(
    db_session: AsyncSession,
    monkeypatch,
    tmp_path,
):
    """
    Integration test for the worker actor that verifies:
    1. Database operations (get_generation, finalize_success)
    2. Generator execution flow
    3. Storage integration (download from provider, upload to storage)
    4. Progress publishing (mocked to avoid Redis dependency)

    Mocked components:
    - Replicate API (external provider)
    - HTTP downloads (to avoid network calls)
    - Redis progress publishing (to avoid Redis dependency in tests)
    """
    import sys
    from datetime import UTC, datetime
    from types import ModuleType
    from unittest.mock import AsyncMock, MagicMock, patch

    from sqlalchemy import select

    from boards.dbmodels import Boards, Generations, Tenants, Users
    from boards.generators.implementations.replicate.image.flux_pro import ReplicateFluxProGenerator
    from boards.generators.registry import registry
    from boards.progress.publisher import ProgressPublisher

    # Setup: Create test data - user, board, and generation
    # Note: We rely on the db_session fixture which already has a default tenant

    # Get the default tenant (created by conftest fixture)
    result = await db_session.execute(select(Tenants).where(Tenants.slug == "default"))
    tenant = result.scalar_one()
    tenant_id = tenant.id

    # Create a test user
    user_id = uuid4()
    user = Users()
    user.id = user_id
    user.tenant_id = tenant_id
    user.auth_provider = "none"
    user.auth_subject = "test-worker-user"
    user.email = "worker@test.com"
    user.display_name = "Worker Test User"
    user.metadata_ = {}
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    db_session.add(user)

    # Create a test board
    board_id = uuid4()
    board = Boards()
    board.id = board_id
    board.tenant_id = tenant_id
    board.owner_id = user_id
    board.title = "Test Board for Worker"
    board.description = "Integration test board"
    board.metadata_ = {}
    board.created_at = datetime.now(UTC)
    board.updated_at = datetime.now(UTC)
    db_session.add(board)

    # Create a generation record
    generation_id = uuid4()
    generation = Generations()
    generation.id = generation_id
    generation.tenant_id = tenant_id
    generation.board_id = board_id
    generation.user_id = user_id
    generation.generator_name = "replicate-flux-pro"
    generation.artifact_type = "image"
    generation.input_params = {
        "prompt": "a test image",
        "aspect_ratio": "1:1",
        "safety_tolerance": 2,
    }
    generation.status = "pending"

    db_session.add(generation)
    await db_session.commit()

    # Mock Replicate API to avoid external network calls
    mock_file_output = SimpleNamespace(url="https://replicate.delivery/fake.png")
    mock_helpers = ModuleType("helpers")
    mock_helpers.FileOutput = MagicMock  # type: ignore[attr-defined]

    mock_replicate = ModuleType("replicate")
    mock_replicate.async_run = AsyncMock(return_value=mock_file_output)  # type: ignore[attr-defined]
    mock_replicate.helpers = mock_helpers  # type: ignore[attr-defined]

    sys.modules["replicate"] = mock_replicate
    sys.modules["replicate.helpers"] = mock_helpers

    # Ensure generator is registered
    try:
        registry.register(ReplicateFluxProGenerator())
    except Exception:
        pass

    # Mock Redis client to avoid Redis dependency
    # This prevents ProgressPublisher.__init__ from trying to connect to Redis
    mock_redis = AsyncMock()
    mock_redis.publish = AsyncMock()
    monkeypatch.setattr("boards.progress.publisher.get_redis_client", lambda: mock_redis)

    # Mock Redis progress publishing methods (avoid Redis dependency)
    async def fake_publish_progress(self, generation_id: UUID, update):
        # No-op for testing
        pass

    async def fake_publish_only(self, generation_id: UUID, update):
        # No-op for testing
        pass

    monkeypatch.setattr(ProgressPublisher, "publish_progress", fake_publish_progress)
    monkeypatch.setattr(ProgressPublisher, "publish_only", fake_publish_only)

    # Configure storage to use tmp_path (local filesystem)
    # Unset Supabase env vars if present to force local storage
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.setenv("BOARDS_STORAGE_DEFAULT_PROVIDER", "local")
    monkeypatch.setenv("REPLICATE_API_TOKEN", "test-token")

    # Mock HTTP download for storage integration with streaming
    def create_mock_http_response(content: bytes):
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
        mock_stream_context = MagicMock()
        mock_stream_context.__aenter__ = AsyncMock(return_value=create_mock_http_response(content))
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)
        return mock_stream_context

    # Execute the worker function
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.stream = MagicMock(
            return_value=create_mock_stream_context(b"fake image data from replicate")
        )

        # Access the original function before AsyncIO middleware wrapping
        original_fn = process_generation.fn.__wrapped__
        await original_fn(str(generation_id))

    # Verify: Check that the generation was finalized successfully
    await db_session.refresh(generation)
    assert generation.status == "completed"
    assert generation.storage_url is not None

    # The storage URL should be populated (exact format depends on storage provider config)
    assert len(generation.storage_url) > 0
