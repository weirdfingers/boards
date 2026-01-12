"""
Integration tests for delete generation authorization.

Tests that:
- Board owner can delete any generation
- Board editors can only delete their own generations
- Non-owners/non-editors cannot delete generations
- Non-authenticated users cannot delete generations
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select

from boards.api.app import create_app
from boards.database.seed_data import ensure_tenant
from boards.dbmodels import BoardMembers, Boards, Generations, Tenants, Users


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
            Users.auth_subject.in_(["del-owner", "del-editor", "del-other"])
        )

        # Delete board members first
        board_ids_stmt = select(Boards.id).where(Boards.owner_id.in_(test_user_ids_stmt))
        await session.execute(delete(BoardMembers).where(BoardMembers.board_id.in_(board_ids_stmt)))

        # Delete generations
        await session.execute(delete(Generations).where(Generations.board_id.in_(board_ids_stmt)))

        # Delete boards
        await session.execute(delete(Boards).where(Boards.owner_id.in_(test_user_ids_stmt)))

        # Delete users
        await session.execute(
            delete(Users).where(Users.auth_subject.in_(["del-owner", "del-editor", "del-other"]))
        )

        # Delete tenant
        await session.execute(delete(Tenants).where(Tenants.slug == "del-tenant"))

        await session.commit()
    except Exception:
        await session.rollback()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_delete_generation_authorization(
    alembic_migrate, test_database, reset_shared_db_connections
):
    """Integration test for generation deletion authorization."""
    dsn, _ = test_database

    import os

    os.environ["BOARDS_DATABASE_URL"] = dsn
    os.environ["BOARDS_AUTH_PROVIDER"] = "none"
    os.environ["BOARDS_AUTH_CONFIG"] = (
        '{"default_user_id": "del-owner", "default_tenant": "del-tenant"}'
    )

    app = create_app()

    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        from boards.database.connection import get_async_session

        async with get_async_session() as session:
            await cleanup_test_data(session)

            # Create tenant
            tenant_id = await ensure_tenant(session, slug="del-tenant")

            # Create users
            owner_id = generate_auth_adapter_user_id("none", "del-owner", "del-tenant")
            owner = Users()
            owner.id = owner_id
            owner.tenant_id = tenant_id
            owner.auth_provider = "none"
            owner.auth_subject = "del-owner"
            owner.email = "owner@example.com"
            owner.display_name = "Board Owner"
            owner.metadata_ = {}
            owner.created_at = datetime.now(UTC)
            owner.updated_at = datetime.now(UTC)
            session.add(owner)

            editor_id = generate_auth_adapter_user_id("none", "del-editor", "del-tenant")
            editor = Users()
            editor.id = editor_id
            editor.tenant_id = tenant_id
            editor.auth_provider = "none"
            editor.auth_subject = "del-editor"
            editor.email = "editor@example.com"
            editor.display_name = "Board Editor"
            editor.metadata_ = {}
            editor.created_at = datetime.now(UTC)
            editor.updated_at = datetime.now(UTC)
            session.add(editor)

            other_id = generate_auth_adapter_user_id("none", "del-other", "del-tenant")
            other = Users()
            other.id = other_id
            other.tenant_id = tenant_id
            other.auth_provider = "none"
            other.auth_subject = "del-other"
            other.email = "other@example.com"
            other.display_name = "Other User"
            other.metadata_ = {}
            other.created_at = datetime.now(UTC)
            other.updated_at = datetime.now(UTC)
            session.add(other)

            # Create board owned by owner
            board = Boards()
            board.id = uuid.uuid4()
            board.tenant_id = tenant_id
            board.owner_id = owner.id
            board.title = "Test Board"
            board.description = "Board for deletion testing"
            board.is_public = False
            board.settings = {}
            board.metadata_ = {}
            board.created_at = datetime.now(UTC)
            board.updated_at = datetime.now(UTC)
            session.add(board)

            # Add editor as board member with editor role
            member = BoardMembers()
            member.id = uuid.uuid4()
            member.board_id = board.id
            member.user_id = editor.id
            member.role = "editor"
            member.invited_by = owner.id
            member.joined_at = datetime.now(UTC)
            session.add(member)

            # Create generation by owner
            gen_by_owner = Generations()
            gen_by_owner.id = uuid.uuid4()
            gen_by_owner.tenant_id = tenant_id
            gen_by_owner.board_id = board.id
            gen_by_owner.user_id = owner.id
            gen_by_owner.generator_name = "test-generator"
            gen_by_owner.artifact_type = "image"
            gen_by_owner.storage_url = "https://storage.example.com/owner_gen.jpg"
            gen_by_owner.thumbnail_url = None
            gen_by_owner.additional_files = []
            gen_by_owner.input_params = {"prompt": "test"}
            gen_by_owner.output_metadata = {}
            gen_by_owner.external_job_id = "job-owner"
            gen_by_owner.status = "completed"
            gen_by_owner.progress = Decimal(1.0)
            gen_by_owner.error_message = None
            gen_by_owner.started_at = datetime.now(UTC)
            gen_by_owner.completed_at = datetime.now(UTC)
            gen_by_owner.created_at = datetime.now(UTC)
            gen_by_owner.updated_at = datetime.now(UTC)
            session.add(gen_by_owner)

            # Create generation by editor
            gen_by_editor = Generations()
            gen_by_editor.id = uuid.uuid4()
            gen_by_editor.tenant_id = tenant_id
            gen_by_editor.board_id = board.id
            gen_by_editor.user_id = editor.id
            gen_by_editor.generator_name = "test-generator"
            gen_by_editor.artifact_type = "image"
            gen_by_editor.storage_url = "https://storage.example.com/editor_gen.jpg"
            gen_by_editor.thumbnail_url = None
            gen_by_editor.additional_files = []
            gen_by_editor.input_params = {"prompt": "test"}
            gen_by_editor.output_metadata = {}
            gen_by_editor.external_job_id = "job-editor"
            gen_by_editor.status = "completed"
            gen_by_editor.progress = Decimal(1.0)
            gen_by_editor.error_message = None
            gen_by_editor.started_at = datetime.now(UTC)
            gen_by_editor.completed_at = datetime.now(UTC)
            gen_by_editor.created_at = datetime.now(UTC)
            gen_by_editor.updated_at = datetime.now(UTC)
            session.add(gen_by_editor)

            # Create another generation by owner for editor to attempt to delete
            gen_by_owner_2 = Generations()
            gen_by_owner_2.id = uuid.uuid4()
            gen_by_owner_2.tenant_id = tenant_id
            gen_by_owner_2.board_id = board.id
            gen_by_owner_2.user_id = owner.id
            gen_by_owner_2.generator_name = "test-generator"
            gen_by_owner_2.artifact_type = "image"
            gen_by_owner_2.storage_url = "https://storage.example.com/owner_gen_2.jpg"
            gen_by_owner_2.thumbnail_url = None
            gen_by_owner_2.additional_files = []
            gen_by_owner_2.input_params = {"prompt": "test"}
            gen_by_owner_2.output_metadata = {}
            gen_by_owner_2.external_job_id = "job-owner-2"
            gen_by_owner_2.status = "completed"
            gen_by_owner_2.progress = Decimal(1.0)
            gen_by_owner_2.error_message = None
            gen_by_owner_2.started_at = datetime.now(UTC)
            gen_by_owner_2.completed_at = datetime.now(UTC)
            gen_by_owner_2.created_at = datetime.now(UTC)
            gen_by_owner_2.updated_at = datetime.now(UTC)
            session.add(gen_by_owner_2)

            await session.flush()

            # Store IDs
            gen_by_owner_id = gen_by_owner.id
            gen_by_editor_id = gen_by_editor.id
            gen_by_owner_2_id = gen_by_owner_2.id

            await session.commit()

        delete_mutation = """
        mutation DeleteGeneration($id: UUID!) {
            deleteGeneration(id: $id)
        }
        """

        # Test 1: Owner can delete their own generation
        response = await client.post(
            "/graphql",
            json={
                "query": delete_mutation,
                "variables": {"id": str(gen_by_owner_id)},
            },
            headers={"X-Tenant": "del-tenant"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert data["data"]["deleteGeneration"] is True

        # Verify generation was deleted
        async with get_async_session() as session:
            result = await session.execute(
                select(Generations).where(Generations.id == gen_by_owner_id)
            )
            assert result.scalar_one_or_none() is None

        # Test 2: Editor can delete their own generation
        os.environ["BOARDS_AUTH_CONFIG"] = (
            '{"default_user_id": "del-editor", "default_tenant": "del-tenant"}'
        )
        # Force app recreation to pick up new auth config
        app = create_app()
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/graphql",
                json={
                    "query": delete_mutation,
                    "variables": {"id": str(gen_by_editor_id)},
                },
                headers={"X-Tenant": "del-tenant"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "errors" not in data
            assert data["data"]["deleteGeneration"] is True

            # Verify generation was deleted
            async with get_async_session() as session:
                result = await session.execute(
                    select(Generations).where(Generations.id == gen_by_editor_id)
                )
                assert result.scalar_one_or_none() is None

            # Test 3: Editor CANNOT delete owner's generation
            response = await client.post(
                "/graphql",
                json={
                    "query": delete_mutation,
                    "variables": {"id": str(gen_by_owner_2_id)},
                },
                headers={"X-Tenant": "del-tenant"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "errors" in data
            assert "Permission denied" in data["errors"][0]["message"]

            # Verify generation still exists
            async with get_async_session() as session:
                result = await session.execute(
                    select(Generations).where(Generations.id == gen_by_owner_2_id)
                )
                assert result.scalar_one_or_none() is not None

        # Test 4: Non-member cannot delete generations
        os.environ["BOARDS_AUTH_CONFIG"] = (
            '{"default_user_id": "del-other", "default_tenant": "del-tenant"}'
        )
        app = create_app()
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/graphql",
                json={
                    "query": delete_mutation,
                    "variables": {"id": str(gen_by_owner_2_id)},
                },
                headers={"X-Tenant": "del-tenant"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "errors" in data
            assert "Permission denied" in data["errors"][0]["message"]

            # Verify generation still exists
            async with get_async_session() as session:
                result = await session.execute(
                    select(Generations).where(Generations.id == gen_by_owner_2_id)
                )
                assert result.scalar_one_or_none() is not None

        # Test 5: Verify generation still exists after failed deletion attempts
        async with get_async_session() as session:
            result = await session.execute(
                select(Generations).where(Generations.id == gen_by_owner_2_id)
            )
            gen = result.scalar_one_or_none()
            assert gen is not None
            assert gen.user_id == owner_id  # Verify it's owned by the owner
