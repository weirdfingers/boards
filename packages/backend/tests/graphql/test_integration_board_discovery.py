"""
Integration tests for board discovery GraphQL resolvers with real database
"""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select

from boards.api.app import create_app
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
        # Delete test data in reverse dependency order
        test_user_ids_stmt = select(Users.id).where(
            Users.auth_subject.in_(["discovery-user-1", "discovery-user-2"])
        )
        await session.execute(
            delete(Boards).where(Boards.owner_id.in_(test_user_ids_stmt))
        )

        await session.execute(
            delete(BoardMembers).where(BoardMembers.user_id.in_(test_user_ids_stmt))
        )

        await session.execute(
            delete(Users).where(
                Users.auth_subject.in_(["discovery-user-1", "discovery-user-2"])
            )
        )

        await session.execute(
            delete(Tenants).where(Tenants.slug.like("discovery-tenant%"))
        )

        await session.commit()
    except Exception:
        await session.rollback()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_board_discovery_integration(alembic_migrate, test_database):
    """Integration test for board discovery queries (myBoards and publicBoards)."""
    dsn, _ = test_database

    import os

    os.environ["BOARDS_DATABASE_URL"] = dsn
    os.environ["BOARDS_AUTH_PROVIDER"] = "none"
    os.environ["BOARDS_AUTH_CONFIG"] = (
        '{"default_user_id": "discovery-user-1", "default_tenant": "discovery-tenant"}'
    )

    # Note: Auth adapters are no longer cached for thread safety

    app = create_app()

    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        from boards.database.connection import get_async_session

        async with get_async_session() as session:
            await cleanup_test_data(session)

            # Create tenant
            import hashlib

            tenant_id = uuid.UUID(hashlib.md5(b"discovery-tenant").hexdigest()[:32])
            tenant = Tenants(
                id=tenant_id,
                name="Discovery Tenant",
                slug="discovery-tenant",
                settings={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(tenant)

            # Create user 1 (default authenticated user) - use same algorithm as NoAuthAdapter
            # fallback
            # NoAuthAdapter fallback uses string tenant from header, not UUID
            user1_id = generate_auth_adapter_user_id(
                "none", "discovery-user-1", "discovery-tenant"
            )
            user1 = Users(
                id=user1_id,
                tenant_id=tenant_id,
                auth_provider="none",
                auth_subject="discovery-user-1",
                email="user1@example.com",
                display_name="User 1",
                metadata_={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(user1)

            # Create user 2 - use same algorithm as NoAuthAdapter fallback
            user2_id = generate_auth_adapter_user_id(
                "none", "discovery-user-2", "discovery-tenant"
            )
            user2 = Users(
                id=user2_id,
                tenant_id=tenant_id,
                auth_provider="none",
                auth_subject="discovery-user-2",
                email="user2@example.com",
                display_name="User 2",
                metadata_={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(user2)

            # Create boards for testing
            # Board owned by user1 (public)
            owned_public_board = Boards(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                owner_id=user1.id,
                title="My Public Board",
                description="A public board owned by user1",
                is_public=True,
                settings={},
                metadata_={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(owned_public_board)

            # Board owned by user1 (private)
            owned_private_board = Boards(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                owner_id=user1.id,
                title="My Private Board",
                description="A private board owned by user1",
                is_public=False,
                settings={},
                metadata_={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(owned_private_board)

            # Board owned by user2 where user1 is a member
            member_board = Boards(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                owner_id=user2.id,
                title="Shared Board",
                description="A board where user1 is a member",
                is_public=False,
                settings={},
                metadata_={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(member_board)

            # Add user1 as member of member_board
            member_relationship = BoardMembers(
                id=uuid.uuid4(),
                board_id=member_board.id,
                user_id=user1.id,
                role="editor",
                joined_at=datetime.now(UTC),
            )
            session.add(member_relationship)

            # Public board owned by user2 (should appear in public boards)
            other_public_board = Boards(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                owner_id=user2.id,
                title="Other Public Board",
                description="A public board owned by user2",
                is_public=True,
                settings={},
                metadata_={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(other_public_board)
            await session.flush()

            # Store IDs before commit
            owned_public_id = owned_public_board.id
            owned_private_id = owned_private_board.id
            member_board_id = member_board.id
            other_public_id = other_public_board.id

            await session.commit()

        # The session is automatically closed when exiting the async context above
        # Test myBoards query (default ANY role)
        my_boards_query = """
        query MyBoards($limit: Int!, $offset: Int!) {
            myBoards(limit: $limit, offset: $offset) {
                id
                title
                isPublic
            }
        }
        """

        response = await client.post(
            "/graphql",
            json={"query": my_boards_query, "variables": {"limit": 10, "offset": 0}},
            headers={
                "Authorization": "Bearer dev-token",
                "X-Tenant": "discovery-tenant",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data

        my_boards = data["data"]["myBoards"]
        assert len(my_boards) == 3  # 2 owned + 1 member
        board_ids = {board["id"] for board in my_boards}
        assert str(owned_public_id) in board_ids
        assert str(owned_private_id) in board_ids
        assert str(member_board_id) in board_ids

        # Test myBoards with OWNER role filter
        response = await client.post(
            "/graphql",
            json={
                "query": """
                query MyBoards($limit: Int!, $offset: Int!, $role: BoardQueryRole!) {
                    myBoards(limit: $limit, offset: $offset, role: $role) {
                        id
                        title
                    }
                }
                """,
                "variables": {"limit": 10, "offset": 0, "role": "OWNER"},
            },
            headers={
                "Authorization": "Bearer dev-token",
                "X-Tenant": "discovery-tenant",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data

        owned_boards = data["data"]["myBoards"]
        assert len(owned_boards) == 2  # Only owned boards
        owned_board_ids = {board["id"] for board in owned_boards}
        assert str(owned_public_id) in owned_board_ids
        assert str(owned_private_id) in owned_board_ids
        assert str(member_board_id) not in owned_board_ids

        # Test myBoards with MEMBER role filter
        response = await client.post(
            "/graphql",
            json={
                "query": """
                query MyBoards($limit: Int!, $offset: Int!, $role: BoardQueryRole!) {
                    myBoards(limit: $limit, offset: $offset, role: $role) {
                        id
                        title
                    }
                }
                """,
                "variables": {"limit": 10, "offset": 0, "role": "MEMBER"},
            },
            headers={
                "Authorization": "Bearer dev-token",
                "X-Tenant": "discovery-tenant",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data

        member_boards = data["data"]["myBoards"]
        assert len(member_boards) == 1  # Only member boards (not owned)
        assert member_boards[0]["id"] == str(member_board_id)

        # Test publicBoards query
        public_boards_query = """
        query PublicBoards($limit: Int!, $offset: Int!) {
            publicBoards(limit: $limit, offset: $offset) {
                id
                title
                isPublic
            }
        }
        """

        response = await client.post(
            "/graphql",
            json={
                "query": public_boards_query,
                "variables": {"limit": 10, "offset": 0},
            },
            headers={
                "X-Tenant": "discovery-tenant"
            },  # No auth needed for public boards
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data

        public_boards = data["data"]["publicBoards"]
        assert len(public_boards) == 2  # Both public boards
        public_board_ids = {board["id"] for board in public_boards}
        assert str(owned_public_id) in public_board_ids
        assert str(other_public_id) in public_board_ids

        # Verify all are public
        for board in public_boards:
            assert board["isPublic"] is True

        # Test pagination
        response = await client.post(
            "/graphql",
            json={"query": public_boards_query, "variables": {"limit": 1, "offset": 0}},
            headers={"X-Tenant": "discovery-tenant"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert len(data["data"]["publicBoards"]) == 1  # Limited to 1
