"""
Integration tests for board GraphQL resolvers with real database
"""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select

from boards.api.app import create_app
from boards.dbmodels import Boards, Tenants, Users


async def cleanup_test_data(session):
    """Clean up any existing test data that might interfere with the test."""
    try:
        # Delete test data in reverse dependency order
        # (boards -> users -> tenants due to foreign key constraints)

        # Delete boards owned by test users
        test_user_ids_stmt = select(Users.id).where(
            Users.auth_subject.in_(["test-user-id", "other-user-id"])
        )
        await session.execute(
            delete(Boards).where(Boards.owner_id.in_(test_user_ids_stmt))
        )

        # Delete test users
        await session.execute(
            delete(Users).where(
                Users.auth_subject.in_(["test-user-id", "other-user-id"])
            )
        )

        # Delete test tenants
        await session.execute(delete(Tenants).where(Tenants.slug.like("test-tenant%")))

        await session.commit()
    except Exception:
        # If cleanup fails (e.g., tables don't exist yet), just rollback and continue
        await session.rollback()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_board_query_integration(alembic_migrate, test_database):
    """Integration test for board query with real database."""
    dsn, _ = test_database

    # Create test app with test database
    import os

    os.environ["BOARDS_DATABASE_URL"] = dsn
    os.environ["BOARDS_AUTH_PROVIDER"] = "none"
    os.environ["BOARDS_AUTH_CONFIG"] = (
        '{"default_user_id": "test-user-id", "default_tenant": "test-tenant"}'
    )

    # Clear the cached auth adapter to ensure our test config is used
    import boards.auth.factory
    boards.auth.factory._adapter = None

    app = create_app()

    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create test data in database
        from boards.database.connection import get_async_session

        async with get_async_session() as session:
            # Clean up any existing test data first
            await cleanup_test_data(session)

            # Create tenant with deterministic UUID based on slug
            import hashlib

            tenant_id = uuid.UUID(hashlib.md5(b"test-tenant").hexdigest()[:32])
            tenant = Tenants(
                id=tenant_id,
                name="Test Tenant",
                slug="test-tenant",
                settings={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(tenant)

            # Create user (this will be the default authenticated user)
            user = Users(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                auth_provider="none",
                auth_subject="test-user-id",
                email="test@example.com",
                display_name="Test User",
                metadata_={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(user)

            # Create a second user (will own the private board)
            other_user = Users(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                auth_provider="none",
                auth_subject="other-user-id",
                email="other@example.com",
                display_name="Other User",
                metadata_={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(other_user)

            # Create public board
            public_board = Boards(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                owner_id=user.id,
                title="Public Test Board",
                description="A public board for testing",
                is_public=True,
                settings={},
                metadata_={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(public_board)

            # Create private board (owned by other user)
            private_board = Boards(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                owner_id=other_user.id,
                title="Private Test Board",
                description="A private board for testing",
                is_public=False,
                settings={},
                metadata_={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(private_board)

            # Create another private board owned by the default user
            owned_private_board = Boards(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                owner_id=user.id,
                title="My Private Board",
                description="A private board owned by the default user",
                is_public=False,
                settings={},
                metadata_={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(owned_private_board)

            # Store IDs before commit
            public_board_id = public_board.id
            private_board_id = private_board.id
            owned_private_board_id = owned_private_board.id

            await session.commit()

        # Test querying public board without auth
        query = """
        query GetBoard($id: UUID!) {
            board(id: $id) {
                id
                title
                description
                isPublic
            }
        }
        """

        response = await client.post(
            "/graphql",
            json={"query": query, "variables": {"id": str(public_board_id)}},
            headers={"X-Tenant": "test-tenant"},
        )

        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")

        # If we get 422, it means validation error - let's see what it is
        if response.status_code == 422:
            print(f"Validation error: {response.text}")
            # Let's try a simpler query first
            simple_response = await client.post(
                "/graphql", json={"query": "{ __typename }"}
            )
            print(f"Simple query status: {simple_response.status_code}")
            print(f"Simple query response: {simple_response.text}")

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert data["data"]["board"]["id"] == str(public_board_id)
        assert data["data"]["board"]["title"] == "Public Test Board"
        assert data["data"]["board"]["isPublic"] is True

        # Test querying private board with default auth but no access (should return null)
        response = await client.post(
            "/graphql",
            json={"query": query, "variables": {"id": str(private_board_id)}},
            headers={"X-Tenant": "test-tenant"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert data["data"]["board"] is None

        # Test querying owned private board with auth (using no-auth mode)
        response = await client.post(
            "/graphql",
            json={"query": query, "variables": {"id": str(owned_private_board_id)}},
            headers={"Authorization": "Bearer dev-token", "X-Tenant": "test-tenant"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert data["data"]["board"]["id"] == str(owned_private_board_id)
        assert data["data"]["board"]["title"] == "My Private Board"
        assert data["data"]["board"]["isPublic"] is False

        # Test querying non-existent board
        response = await client.post(
            "/graphql",
            json={"query": query, "variables": {"id": str(uuid.uuid4())}},
            headers={"X-Tenant": "test-tenant"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert data["data"]["board"] is None
