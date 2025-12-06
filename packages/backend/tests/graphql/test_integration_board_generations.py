"""
Integration tests for board generations GraphQL resolvers
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select

from boards.api.app import create_app
from boards.database.seed_data import ensure_tenant
from boards.dbmodels import Boards, Generations, Tenants, Users


def generate_auth_adapter_user_id(provider: str, subject: str, tenant_id: str) -> uuid.UUID:
    """Generate user ID using the same algorithm as the NoAuthAdapter."""
    import hashlib

    stable_input = f"{provider}:{subject}:{tenant_id}"
    user_id_hash = hashlib.sha256(stable_input.encode()).hexdigest()[:32]
    formatted_uuid = (
        f"{user_id_hash[:8]}-{user_id_hash[8:12]}-"
        f"{user_id_hash[12:16]}-{user_id_hash[16:20]}-"
        f"{user_id_hash[20:32]}"
    )
    return uuid.UUID(formatted_uuid)


async def cleanup_test_data(session):
    """Clean up any existing test data that might interfere with the test."""
    try:
        test_user_ids_stmt = select(Users.id).where(
            Users.auth_subject.in_(["gen-user-1", "gen-user-2"])
        )

        # Delete generations first (they reference boards)
        board_ids_stmt = select(Boards.id).where(Boards.owner_id.in_(test_user_ids_stmt))
        await session.execute(delete(Generations).where(Generations.board_id.in_(board_ids_stmt)))

        await session.execute(delete(Boards).where(Boards.owner_id.in_(test_user_ids_stmt)))

        await session.execute(
            delete(Users).where(Users.auth_subject.in_(["gen-user-1", "gen-user-2"]))
        )

        await session.execute(delete(Tenants).where(Tenants.slug.like("gen-tenant%")))

        await session.commit()
    except Exception:
        await session.rollback()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_board_generations_integration(
    alembic_migrate, test_database, reset_shared_db_connections
):
    """Integration test for board generations GraphQL resolvers."""
    dsn, _ = test_database

    import os

    os.environ["BOARDS_DATABASE_URL"] = dsn
    os.environ["BOARDS_AUTH_PROVIDER"] = "none"
    os.environ["BOARDS_AUTH_CONFIG"] = (
        '{"default_user_id": "gen-user-1", "default_tenant": "gen-tenant"}'
    )

    app = create_app()

    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        from boards.database.connection import get_async_session

        async with get_async_session() as session:
            await cleanup_test_data(session)

            # Create tenant
            tenant_id = await ensure_tenant(session, slug="gen-tenant")

            # Create users with deterministic IDs matching NoAuthAdapter fallback
            user1_id = generate_auth_adapter_user_id("none", "gen-user-1", "gen-tenant")
            user1 = Users(  # Default authenticated user
                id=user1_id,
                tenant_id=tenant_id,
                auth_provider="none",
                auth_subject="gen-user-1",
                email="user1@example.com",
                display_name="User 1",
                metadata_={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(user1)

            user2_id = generate_auth_adapter_user_id("none", "gen-user-2", "gen-tenant")
            user2 = Users(
                id=user2_id,
                tenant_id=tenant_id,
                auth_provider="none",
                auth_subject="gen-user-2",
                email="user2@example.com",
                display_name="User 2",
                metadata_={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(user2)

            # Create public board owned by user1
            public_board = Boards(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                owner_id=user1.id,
                title="Public Board with Generations",
                description="A public board for generation testing",
                is_public=True,
                settings={},
                metadata_={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(public_board)

            # Create private board owned by user2
            private_board = Boards(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                owner_id=user2.id,
                title="Private Board",
                description="A private board for testing access denial",
                is_public=False,
                settings={},
                metadata_={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(private_board)

            # Create generations for public board
            gen1 = Generations()
            gen1.id = uuid.uuid4()
            gen1.tenant_id = tenant_id
            gen1.board_id = public_board.id
            gen1.user_id = user1.id
            gen1.generator_name = "stable-diffusion"
            gen1.artifact_type = "image"
            gen1.storage_url = "https://storage.example.com/gen1.jpg"
            gen1.thumbnail_url = "https://storage.example.com/gen1_thumb.jpg"
            gen1.additional_files = []
            gen1.input_params = {"prompt": "A beautiful sunset", "steps": 50}
            gen1.output_metadata = {"resolution": "512x512", "format": "jpeg"}
            gen1.external_job_id = "job-123"
            gen1.status = "completed"
            gen1.progress = Decimal(1.0)
            gen1.error_message = None
            gen1.started_at = datetime.now(UTC)
            gen1.completed_at = datetime.now(UTC)
            gen1.created_at = datetime.now(UTC)
            gen1.updated_at = datetime.now(UTC)
            session.add(gen1)

            gen2 = Generations()
            gen2.id = uuid.uuid4()
            gen2.tenant_id = tenant_id
            gen2.board_id = public_board.id
            gen2.user_id = user1.id
            gen2.generator_name = "stable-diffusion"
            gen2.artifact_type = "image"
            gen2.storage_url = "https://storage.example.com/gen2.jpg"
            gen2.thumbnail_url = "https://storage.example.com/gen2_thumb.jpg"
            gen2.additional_files = []
            gen2.input_params = {"prompt": "A mountain landscape", "steps": 30}
            gen2.output_metadata = {"resolution": "768x768", "format": "png"}
            gen2.external_job_id = "job-456"
            gen2.status = "completed"
            gen2.progress = Decimal(1.0)
            gen2.error_message = None
            gen2.started_at = datetime.now(UTC)
            gen2.completed_at = datetime.now(UTC)
            gen2.created_at = datetime.now(UTC) - timedelta(hours=1)  # Older
            gen2.updated_at = datetime.now(UTC)
            session.add(gen2)

            # Create generation for private board
            private_gen = Generations()
            private_gen.id = uuid.uuid4()
            private_gen.tenant_id = tenant_id
            private_gen.board_id = private_board.id
            private_gen.user_id = user2.id
            private_gen.generator_name = "gpt-4"
            private_gen.artifact_type = "text"
            private_gen.storage_url = None
            private_gen.thumbnail_url = None
            private_gen.additional_files = []
            private_gen.input_params = {"prompt": "Write a story", "max_tokens": 1000}
            private_gen.output_metadata = {"tokens_used": 500}
            private_gen.external_job_id = "job-789"
            private_gen.status = "processing"
            private_gen.progress = Decimal(0.5)
            private_gen.error_message = None
            private_gen.started_at = datetime.now(UTC)
            private_gen.completed_at = None
            private_gen.created_at = datetime.now(UTC)
            private_gen.updated_at = datetime.now(UTC)
            session.add(private_gen)
            await session.flush()

            # Store IDs before commit
            public_board_id = public_board.id
            private_board_id = private_board.id
            gen1_id = gen1.id
            gen2_id = gen2.id

            await session.commit()

        # Test accessing generations for public board (no auth required)
        board_generations_query = """
        query GetBoardGenerations($id: UUID!, $limit: Int!, $offset: Int!) {
            board(id: $id) {
                id
                title
                generations(limit: $limit, offset: $offset) {
                    id
                    generatorName
                    artifactType
                    status
                    progress
                    storageUrl
                    inputParams
                    outputMetadata
                    createdAt
                }
            }
        }
        """

        response = await client.post(
            "/graphql",
            json={
                "query": board_generations_query,
                "variables": {"id": str(public_board_id), "limit": 10, "offset": 0},
            },
            headers={"X-Tenant": "gen-tenant"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data

        board = data["data"]["board"]
        assert board is not None
        assert board["id"] == str(public_board_id)

        generations = board["generations"]
        assert len(generations) == 2

        # Should be ordered by created_at desc (gen1 first, then gen2)
        assert generations[0]["id"] == str(gen1_id)
        assert generations[0]["generatorName"] == "stable-diffusion"
        assert generations[0]["artifactType"] == "IMAGE"
        assert generations[0]["status"] == "COMPLETED"
        assert generations[0]["progress"] == 1.0
        assert generations[0]["storageUrl"] == "https://storage.example.com/gen1.jpg"
        assert generations[0]["inputParams"]["prompt"] == "A beautiful sunset"
        assert generations[0]["outputMetadata"]["resolution"] == "512x512"

        assert generations[1]["id"] == str(gen2_id)
        assert generations[1]["inputParams"]["prompt"] == "A mountain landscape"

        # Test pagination
        response = await client.post(
            "/graphql",
            json={
                "query": board_generations_query,
                "variables": {"id": str(public_board_id), "limit": 1, "offset": 0},
            },
            headers={"X-Tenant": "gen-tenant"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data

        generations = data["data"]["board"]["generations"]
        assert len(generations) == 1
        assert generations[0]["id"] == str(gen1_id)  # Most recent

        # Test offset
        response = await client.post(
            "/graphql",
            json={
                "query": board_generations_query,
                "variables": {"id": str(public_board_id), "limit": 1, "offset": 1},
            },
            headers={"X-Tenant": "gen-tenant"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data

        generations = data["data"]["board"]["generations"]
        assert len(generations) == 1
        assert generations[0]["id"] == str(gen2_id)  # Second item

        # Test accessing private board generations without auth (should return empty list)
        response = await client.post(
            "/graphql",
            json={
                "query": board_generations_query,
                "variables": {"id": str(private_board_id), "limit": 10, "offset": 0},
            },
            headers={"X-Tenant": "gen-tenant"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data

        board = data["data"]["board"]
        assert board is None  # Can't access private board

        # Test accessing non-existent board
        response = await client.post(
            "/graphql",
            json={
                "query": board_generations_query,
                "variables": {"id": str(uuid.uuid4()), "limit": 10, "offset": 0},
            },
            headers={"X-Tenant": "gen-tenant"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert data["data"]["board"] is None
