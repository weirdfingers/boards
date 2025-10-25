"""
Integration tests for board mutation GraphQL operations
"""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select

from boards.api.app import create_app
from boards.database.seed_data import ensure_tenant
from boards.dbmodels import BoardMembers, Boards, Tenants, Users


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
            Users.auth_subject.in_(["board-user-1", "board-user-2", "board-user-3"])
        )
        await session.execute(delete(Boards).where(Boards.owner_id.in_(test_user_ids_stmt)))

        await session.execute(
            delete(BoardMembers).where(BoardMembers.user_id.in_(test_user_ids_stmt))
        )

        await session.execute(
            delete(Users).where(
                Users.auth_subject.in_(["board-user-1", "board-user-2", "board-user-3"])
            )
        )

        await session.execute(delete(Tenants).where(Tenants.slug.like("board-tenant%")))

        await session.commit()
    except Exception:
        await session.rollback()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_board_crud_integration(alembic_migrate, test_database, reset_shared_db_connections):
    """Integration test for complete board CRUD operations."""
    dsn, _ = test_database

    import os

    os.environ["BOARDS_DATABASE_URL"] = dsn
    os.environ["BOARDS_AUTH_PROVIDER"] = "none"
    os.environ["BOARDS_AUTH_CONFIG"] = (
        '{"default_user_id": "board-user-1", "default_tenant": "board-tenant"}'
    )

    app = create_app()

    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        from boards.database.connection import get_async_session

        async with get_async_session() as session:
            await cleanup_test_data(session)

            # Create tenant and users
            tenant_id = await ensure_tenant(session, slug="board-tenant")

            # Create users
            user1_id = generate_auth_adapter_user_id("none", "board-user-1", "board-tenant")
            user2_id = generate_auth_adapter_user_id("none", "board-user-2", "board-tenant")

            user1 = Users(
                id=user1_id,
                tenant_id=tenant_id,
                auth_provider="none",
                auth_subject="board-user-1",
                email="user1@example.com",
                display_name="User 1",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(user1)

            user2 = Users(
                id=user2_id,
                tenant_id=tenant_id,
                auth_provider="none",
                auth_subject="board-user-2",
                email="user2@example.com",
                display_name="User 2",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(user2)

            await session.commit()

        # Test 1: Create Board
        create_board_mutation = """
        mutation CreateBoard($input: CreateBoardInput!) {
            createBoard(input: $input) {
                id
                title
                description
                isPublic
                settings
                ownerId
            }
        }
        """

        create_response = await client.post(
            "/graphql",
            json={
                "query": create_board_mutation,
                "variables": {
                    "input": {
                        "title": "Integration Test Board",
                        "description": "Testing board creation",
                        "isPublic": False,
                        "settings": {"theme": "dark"},
                    }
                },
            },
            headers={"authorization": "Bearer test-token", "x-tenant": "board-tenant"},
        )

        assert create_response.status_code == 200
        create_data = create_response.json()
        assert "errors" not in create_data

        board_id = create_data["data"]["createBoard"]["id"]
        assert create_data["data"]["createBoard"]["title"] == "Integration Test Board"
        assert create_data["data"]["createBoard"]["ownerId"] == str(user1_id)

        # Test 2: Update Board
        update_board_mutation = """
        mutation UpdateBoard($input: UpdateBoardInput!) {
            updateBoard(input: $input) {
                id
                title
                description
                isPublic
            }
        }
        """

        update_response = await client.post(
            "/graphql",
            json={
                "query": update_board_mutation,
                "variables": {
                    "input": {
                        "id": board_id,
                        "title": "Updated Board Title",
                        "isPublic": True,
                    }
                },
            },
            headers={"authorization": "Bearer test-token", "x-tenant": "board-tenant"},
        )

        assert update_response.status_code == 200
        update_data = update_response.json()
        assert "errors" not in update_data
        assert update_data["data"]["updateBoard"]["title"] == "Updated Board Title"
        assert update_data["data"]["updateBoard"]["isPublic"] is True

        # Test 3: Add Board Member
        add_member_mutation = """
        mutation AddBoardMember($input: AddBoardMemberInput!) {
            addBoardMember(input: $input) {
                id
                title
            }
        }
        """

        add_member_response = await client.post(
            "/graphql",
            json={
                "query": add_member_mutation,
                "variables": {
                    "input": {
                        "boardId": board_id,
                        "userId": str(user2_id),
                        "role": "EDITOR",
                    }
                },
            },
            headers={"authorization": "Bearer test-token", "x-tenant": "board-tenant"},
        )

        assert add_member_response.status_code == 200
        add_member_data = add_member_response.json()
        assert "errors" not in add_member_data

        # Test 4: Query Board with Members
        board_query = """
        query GetBoard($id: UUID!) {
            board(id: $id) {
                id
                title
                members {
                    id
                    userId
                    role
                    user {
                        id
                        displayName
                    }
                }
                owner {
                    id
                    displayName
                }
            }
        }
        """

        board_response = await client.post(
            "/graphql",
            json={"query": board_query, "variables": {"id": board_id}},
            headers={"authorization": "Bearer test-token", "x-tenant": "board-tenant"},
        )

        assert board_response.status_code == 200
        board_data = board_response.json()
        assert "errors" not in board_data

        board = board_data["data"]["board"]
        assert len(board["members"]) == 1
        assert board["members"][0]["role"] == "EDITOR"
        assert board["owner"]["displayName"] == "User 1"

        # Test 5: Update Member Role
        update_role_mutation = """
        mutation UpdateBoardMemberRole($boardId: UUID!, $userId: UUID!, $role: BoardRole!) {
            updateBoardMemberRole(boardId: $boardId, userId: $userId, role: $role) {
                id
                title
            }
        }
        """

        update_role_response = await client.post(
            "/graphql",
            json={
                "query": update_role_mutation,
                "variables": {
                    "boardId": board_id,
                    "userId": str(user2_id),
                    "role": "ADMIN",
                },
            },
            headers={"authorization": "Bearer test-token", "x-tenant": "board-tenant"},
        )

        assert update_role_response.status_code == 200
        update_role_data = update_role_response.json()
        assert "errors" not in update_role_data

        # Test 6: Remove Member
        remove_member_mutation = """
        mutation RemoveBoardMember($boardId: UUID!, $userId: UUID!) {
            removeBoardMember(boardId: $boardId, userId: $userId) {
                id
                title
            }
        }
        """

        remove_member_response = await client.post(
            "/graphql",
            json={
                "query": remove_member_mutation,
                "variables": {"boardId": board_id, "userId": str(user2_id)},
            },
            headers={"authorization": "Bearer test-token", "x-tenant": "board-tenant"},
        )

        assert remove_member_response.status_code == 200
        remove_member_data = remove_member_response.json()
        assert "errors" not in remove_member_data

        # Test 7: Delete Board
        delete_board_mutation = """
        mutation DeleteBoard($id: UUID!) {
            deleteBoard(id: $id)
        }
        """

        delete_response = await client.post(
            "/graphql",
            json={"query": delete_board_mutation, "variables": {"id": board_id}},
            headers={"authorization": "Bearer test-token", "x-tenant": "board-tenant"},
        )

        assert delete_response.status_code == 200
        delete_data = delete_response.json()
        assert "errors" not in delete_data
        assert delete_data["data"]["deleteBoard"] is True

        # Verify board is deleted
        board_check_response = await client.post(
            "/graphql",
            json={"query": board_query, "variables": {"id": board_id}},
            headers={"authorization": "Bearer test-token", "x-tenant": "board-tenant"},
        )

        board_check_data = board_check_response.json()
        assert board_check_data["data"]["board"] is None


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_board_search_integration(
    alembic_migrate, test_database, reset_shared_db_connections
):
    """Integration test for board search functionality."""
    dsn, _ = test_database

    import os

    os.environ["BOARDS_DATABASE_URL"] = dsn
    os.environ["BOARDS_AUTH_PROVIDER"] = "none"
    os.environ["BOARDS_AUTH_CONFIG"] = (
        '{"default_user_id": "board-user-1", "default_tenant": "board-tenant"}'
    )

    app = create_app()

    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        from boards.database.connection import get_async_session

        async with get_async_session() as session:
            await cleanup_test_data(session)

            # Create tenant and user
            tenant_id = await ensure_tenant(session, slug="board-tenant")

            user_id = generate_auth_adapter_user_id("none", "board-user-1", "board-tenant")
            user = Users(
                id=user_id,
                tenant_id=tenant_id,
                auth_provider="none",
                auth_subject="board-user-1",
                email="user1@example.com",
                display_name="User 1",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(user)

            await session.commit()

        # Create test boards
        create_board_mutation = """
        mutation CreateBoard($input: CreateBoardInput!) {
            createBoard(input: $input) {
                id
                title
            }
        }
        """

        # Create boards with different titles
        boards_to_create = [
            {"title": "Python Programming Guide", "description": "Learn Python"},
            {"title": "JavaScript Basics", "description": "JavaScript fundamentals"},
            {"title": "Advanced Python Techniques", "description": "Advanced concepts"},
            {"title": "Machine Learning", "description": "Python for ML"},
        ]

        for board_data in boards_to_create:
            await client.post(
                "/graphql",
                json={
                    "query": create_board_mutation,
                    "variables": {
                        "input": {
                            "title": board_data["title"],
                            "description": board_data["description"],
                            "isPublic": True,
                        }
                    },
                },
                headers={
                    "authorization": "Bearer test-token",
                    "x-tenant": "board-tenant",
                },
            )

        # Test search functionality
        search_query = """
        query SearchBoards($query: String!, $limit: Int!, $offset: Int!) {
            searchBoards(query: $query, limit: $limit, offset: $offset) {
                id
                title
                description
            }
        }
        """

        # Search for "Python" - should return 3 boards
        search_response = await client.post(
            "/graphql",
            json={
                "query": search_query,
                "variables": {"query": "Python", "limit": 10, "offset": 0},
            },
            headers={"authorization": "Bearer test-token", "x-tenant": "board-tenant"},
        )

        assert search_response.status_code == 200
        search_data = search_response.json()
        assert "errors" not in search_data

        results = search_data["data"]["searchBoards"]
        assert len(results) == 3

        python_titles = [board["title"] for board in results]
        assert "Python Programming Guide" in python_titles
        assert "Advanced Python Techniques" in python_titles
        assert "Machine Learning" in python_titles
        assert "JavaScript Basics" not in python_titles

        # Test case-insensitive search
        search_response_lower = await client.post(
            "/graphql",
            json={
                "query": search_query,
                "variables": {"query": "python", "limit": 10, "offset": 0},
            },
            headers={"authorization": "Bearer test-token", "x-tenant": "board-tenant"},
        )

        search_data_lower = search_response_lower.json()
        assert len(search_data_lower["data"]["searchBoards"]) == 3

        # Test pagination
        paginated_response = await client.post(
            "/graphql",
            json={
                "query": search_query,
                "variables": {"query": "Python", "limit": 2, "offset": 0},
            },
            headers={"authorization": "Bearer test-token", "x-tenant": "board-tenant"},
        )

        paginated_data = paginated_response.json()
        assert len(paginated_data["data"]["searchBoards"]) == 2


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_board_permission_integration(
    alembic_migrate, test_database, reset_shared_db_connections
):
    """Integration test for board permissions and access control."""
    dsn, _ = test_database

    import os

    os.environ["BOARDS_DATABASE_URL"] = dsn
    os.environ["BOARDS_AUTH_PROVIDER"] = "none"

    app = create_app()

    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        from boards.database.connection import get_async_session

        async with get_async_session() as session:
            await cleanup_test_data(session)

            # Create tenant and users
            tenant_id = await ensure_tenant(session, slug="board-tenant")

            # Owner user
            owner_id = generate_auth_adapter_user_id("none", "board-user-1", "board-tenant")
            owner = Users(
                id=owner_id,
                tenant_id=tenant_id,
                auth_provider="none",
                auth_subject="board-user-1",
                email="owner@example.com",
                display_name="Board Owner",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(owner)

            # Regular user
            user_id = generate_auth_adapter_user_id("none", "board-user-2", "board-tenant")
            user = Users(
                id=user_id,
                tenant_id=tenant_id,
                auth_provider="none",
                auth_subject="board-user-2",
                email="user@example.com",
                display_name="Regular User",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(user)

            await session.commit()

        # Create board as owner
        os.environ["BOARDS_AUTH_CONFIG"] = (
            '{"default_user_id": "board-user-1", "default_tenant": "board-tenant"}'
        )

        create_board_mutation = """
        mutation CreateBoard($input: CreateBoardInput!) {
            createBoard(input: $input) {
                id
                title
            }
        }
        """

        create_response = await client.post(
            "/graphql",
            json={
                "query": create_board_mutation,
                "variables": {"input": {"title": "Private Board", "isPublic": False}},
            },
            headers={"authorization": "Bearer test-token", "x-tenant": "board-tenant"},
        )

        board_id = create_response.json()["data"]["createBoard"]["id"]

        # Test: Regular user cannot update the board
        os.environ["BOARDS_AUTH_CONFIG"] = (
            '{"default_user_id": "board-user-2", "default_tenant": "board-tenant"}'
        )

        update_mutation = """
        mutation UpdateBoard($input: UpdateBoardInput!) {
            updateBoard(input: $input) {
                id
                title
            }
        }
        """

        update_response = await client.post(
            "/graphql",
            json={
                "query": update_mutation,
                "variables": {"input": {"id": board_id, "title": "Hacked Board"}},
            },
            headers={"authorization": "Bearer test-token", "x-tenant": "board-tenant"},
        )

        update_data = update_response.json()
        assert "errors" in update_data
        assert "Permission denied" in str(update_data["errors"])

        # Test: Regular user cannot delete the board
        delete_mutation = """
        mutation DeleteBoard($id: UUID!) {
            deleteBoard(id: $id)
        }
        """

        delete_response = await client.post(
            "/graphql",
            json={"query": delete_mutation, "variables": {"id": board_id}},
            headers={"authorization": "Bearer test-token", "x-tenant": "board-tenant"},
        )

        delete_data = delete_response.json()
        assert "errors" in delete_data
        assert "Permission denied" in str(delete_data["errors"])

        # Test: Owner can still update and delete
        os.environ["BOARDS_AUTH_CONFIG"] = (
            '{"default_user_id": "board-user-1", "default_tenant": "board-tenant"}'
        )

        success_update_response = await client.post(
            "/graphql",
            json={
                "query": update_mutation,
                "variables": {"input": {"id": board_id, "title": "Updated by Owner"}},
            },
            headers={"authorization": "Bearer test-token", "x-tenant": "board-tenant"},
        )

        success_data = success_update_response.json()
        assert "errors" not in success_data
        assert success_data["data"]["updateBoard"]["title"] == "Updated by Owner"
