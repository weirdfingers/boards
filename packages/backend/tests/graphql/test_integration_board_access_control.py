"""
Integration tests for board access control GraphQL resolvers
"""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select

from boards.api.app import create_app
from boards.database.seed_data import ensure_tenant
from boards.dbmodels import BoardMembers, Boards, Tenants, Users


def generate_auth_adapter_user_id(
    provider: str, subject: str, tenant_id: str
) -> uuid.UUID:
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
            Users.auth_subject.in_(["access-user-1", "access-user-2", "access-user-3"])
        )
        await session.execute(
            delete(Boards).where(Boards.owner_id.in_(test_user_ids_stmt))
        )

        await session.execute(
            delete(BoardMembers).where(BoardMembers.user_id.in_(test_user_ids_stmt))
        )

        await session.execute(
            delete(Users).where(
                Users.auth_subject.in_(
                    ["access-user-1", "access-user-2", "access-user-3"]
                )
            )
        )

        await session.execute(
            delete(Tenants).where(Tenants.slug.like("access-tenant%"))
        )

        await session.commit()
    except Exception:
        await session.rollback()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_board_access_control_integration(
    alembic_migrate, test_database, reset_shared_db_connections
):
    """Integration test for board access control (board details, members, owner)."""
    dsn, _ = test_database

    import os

    os.environ["BOARDS_DATABASE_URL"] = dsn
    os.environ["BOARDS_AUTH_PROVIDER"] = "none"
    os.environ["BOARDS_AUTH_CONFIG"] = (
        '{"default_user_id": "access-user-1", "default_tenant": "access-tenant"}'
    )

    app = create_app()

    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        from boards.database.connection import get_async_session

        async with get_async_session() as session:
            await cleanup_test_data(session)

            # Create tenant
            tenant_id = await ensure_tenant(session, slug="access-tenant")

            # Create users with deterministic IDs matching NoAuthAdapter fallback
            user1_id = generate_auth_adapter_user_id(
                "none", "access-user-1", "access-tenant"
            )
            user1 = Users(  # Default authenticated user
                id=user1_id,
                tenant_id=tenant_id,
                auth_provider="none",
                auth_subject="access-user-1",
                email="user1@example.com",
                display_name="User 1",
                avatar_url="https://example.com/avatar1.jpg",
                metadata_={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(user1)

            user2_id = generate_auth_adapter_user_id(
                "none", "access-user-2", "access-tenant"
            )
            user2 = Users(  # Board owner
                id=user2_id,
                tenant_id=tenant_id,
                auth_provider="none",
                auth_subject="access-user-2",
                email="user2@example.com",
                display_name="User 2",
                avatar_url="https://example.com/avatar2.jpg",
                metadata_={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(user2)

            user3_id = generate_auth_adapter_user_id(
                "none", "access-user-3", "access-tenant"
            )
            user3 = Users(  # Board member
                id=user3_id,
                tenant_id=tenant_id,
                auth_provider="none",
                auth_subject="access-user-3",
                email="user3@example.com",
                display_name="User 3",
                avatar_url="https://example.com/avatar3.jpg",
                metadata_={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(user3)

            # Create public board owned by user2 with user3 as member
            public_board = Boards(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                owner_id=user2.id,
                title="Public Board",
                description="A public board for access testing",
                is_public=True,
                settings={"theme": "light"},
                metadata_={"version": "1.0"},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(public_board)

            # Add user3 as member
            member_relationship = BoardMembers(
                id=uuid.uuid4(),
                board_id=public_board.id,
                user_id=user3.id,
                role="editor",
                invited_by=user2.id,
                joined_at=datetime.now(UTC),
            )
            session.add(member_relationship)

            # Create private board owned by user2 with user1 as member
            private_board = Boards(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                owner_id=user2.id,
                title="Private Board",
                description="A private board for access testing",
                is_public=False,
                settings={"theme": "dark"},
                metadata_={"version": "2.0"},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(private_board)

            # Add user1 as member
            private_member = BoardMembers(
                id=uuid.uuid4(),
                board_id=private_board.id,
                user_id=user1.id,
                role="viewer",
                invited_by=user2.id,
                joined_at=datetime.now(UTC),
            )
            session.add(private_member)
            await session.flush()

            # Store IDs before commit
            public_board_id = public_board.id
            private_board_id = private_board.id

            await session.commit()

        # Test accessing public board details (should work for anyone)
        board_details_query = """
        query GetBoardDetails($id: UUID!) {
            board(id: $id) {
                id
                title
                description
                isPublic
                settings
                metadata
                owner {
                    id
                    email
                    displayName
                    avatarUrl
                }
                members {
                    id
                    role
                    joinedAt
                    user {
                        id
                        displayName
                    }
                }
            }
        }
        """

        # Test public board access without auth
        response = await client.post(
            "/graphql",
            json={
                "query": board_details_query,
                "variables": {"id": str(public_board_id)},
            },
            headers={"X-Tenant": "access-tenant"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data

        board = data["data"]["board"]
        assert board is not None
        assert board["id"] == str(public_board_id)
        assert board["title"] == "Public Board"
        assert board["isPublic"] is True
        assert board["settings"]["theme"] == "light"
        assert board["metadata"]["version"] == "1.0"

        # Check owner details
        owner = board["owner"]
        assert owner["email"] == "user2@example.com"
        assert owner["displayName"] == "User 2"
        assert owner["avatarUrl"] == "https://example.com/avatar2.jpg"

        # Check members
        members = board["members"]
        assert len(members) == 1
        assert members[0]["role"] == "EDITOR"
        assert members[0]["user"]["displayName"] == "User 3"

        # Test private board access as authenticated member (user1)
        response = await client.post(
            "/graphql",
            json={
                "query": board_details_query,
                "variables": {"id": str(private_board_id)},
            },
            headers={"Authorization": "Bearer dev-token", "X-Tenant": "access-tenant"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data

        board = data["data"]["board"]
        assert board is not None
        assert board["id"] == str(private_board_id)
        assert board["title"] == "Private Board"
        assert board["isPublic"] is False
        assert board["settings"]["theme"] == "dark"

        # Check members (user1 should be listed)
        members = board["members"]
        assert len(members) == 1
        assert members[0]["role"] == "VIEWER"
        assert members[0]["user"]["displayName"] == "User 1"

        # Test private board access without explicit auth header
        # (NoAuthAdapter will still provide default authentication as access-user-1)
        response = await client.post(
            "/graphql",
            json={
                "query": board_details_query,
                "variables": {"id": str(private_board_id)},
            },
            headers={"X-Tenant": "access-tenant"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        # Should still return board data since NoAuthAdapter provides default auth as user1 (member)
        board = data["data"]["board"]
        assert board is not None
        assert board["id"] == str(private_board_id)

        # Test accessing non-existent board
        response = await client.post(
            "/graphql",
            json={"query": board_details_query, "variables": {"id": str(uuid.uuid4())}},
            headers={"X-Tenant": "access-tenant"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert data["data"]["board"] is None

        # Test that field resolvers validate preloading (should not error since we preload)
        simple_board_query = """
        query GetBoard($id: UUID!) {
            board(id: $id) {
                id
                title
                owner {
                    displayName
                }
            }
        }
        """

        response = await client.post(
            "/graphql",
            json={
                "query": simple_board_query,
                "variables": {"id": str(public_board_id)},
            },
            headers={"X-Tenant": "access-tenant"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert data["data"]["board"]["owner"]["displayName"] == "User 2"
