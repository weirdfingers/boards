"""
Integration tests for tag mutation GraphQL operations
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select

from boards.api.app import create_app
from boards.database.seed_data import ensure_tenant
from boards.dbmodels import Boards, Generations, Tags, Tenants, Users


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
        # Delete tags first (they reference tenants)
        await session.execute(
            delete(Tags).where(
                Tags.tenant_id.in_(select(Tenants.id).where(Tenants.slug.like("tag-tenant%")))
            )
        )

        # Delete generations and boards
        test_user_ids_stmt = select(Users.id).where(
            Users.auth_subject.in_(["tag-user-1", "tag-user-2"])
        )
        await session.execute(
            delete(Generations).where(Generations.user_id.in_(test_user_ids_stmt))
        )
        await session.execute(delete(Boards).where(Boards.owner_id.in_(test_user_ids_stmt)))

        await session.execute(
            delete(Users).where(Users.auth_subject.in_(["tag-user-1", "tag-user-2"]))
        )

        await session.execute(delete(Tenants).where(Tenants.slug.like("tag-tenant%")))

        await session.commit()
    except Exception:
        await session.rollback()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_tag_crud_integration(alembic_migrate, test_database, reset_shared_db_connections):
    """Integration test for complete tag CRUD operations."""
    dsn, _ = test_database

    import os

    os.environ["BOARDS_DATABASE_URL"] = dsn
    os.environ["BOARDS_AUTH_PROVIDER"] = "none"
    os.environ["BOARDS_AUTH_CONFIG"] = (
        '{"default_user_id": "tag-user-1", "default_tenant": "tag-tenant"}'
    )

    app = create_app()

    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        from boards.database.connection import get_async_session

        async with get_async_session() as session:
            await cleanup_test_data(session)

            # Create tenant and user
            tenant_id = await ensure_tenant(session, slug="tag-tenant")

            user_id = generate_auth_adapter_user_id("none", "tag-user-1", "tag-tenant")
            user = Users(
                id=user_id,
                tenant_id=tenant_id,
                auth_provider="none",
                auth_subject="tag-user-1",
                email="user1@example.com",
                display_name="User 1",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(user)
            await session.commit()

        # Test 1: Create Tag
        create_tag_mutation = """
        mutation CreateTag($input: CreateTagInput!) {
            createTag(input: $input) {
                id
                name
                slug
                description
                metadata
            }
        }
        """

        create_response = await client.post(
            "/graphql",
            json={
                "query": create_tag_mutation,
                "variables": {
                    "input": {
                        "name": "Model Photo",
                        "description": "Photos of models",
                        "metadata": {"category": "wardrobe"},
                    }
                },
            },
            headers={"authorization": "Bearer test-token", "x-tenant": "tag-tenant"},
        )

        assert create_response.status_code == 200
        create_data = create_response.json()
        assert "errors" not in create_data, f"GraphQL errors: {create_data.get('errors')}"

        tag_id = create_data["data"]["createTag"]["id"]
        assert create_data["data"]["createTag"]["name"] == "Model Photo"
        assert create_data["data"]["createTag"]["slug"] == "model-photo"
        assert create_data["data"]["createTag"]["description"] == "Photos of models"

        # Test 2: Query Tags
        tags_query = """
        query GetTags {
            tags {
                id
                name
                slug
            }
        }
        """

        tags_response = await client.post(
            "/graphql",
            json={"query": tags_query},
            headers={"authorization": "Bearer test-token", "x-tenant": "tag-tenant"},
        )

        assert tags_response.status_code == 200
        tags_data = tags_response.json()
        assert "errors" not in tags_data

        tags = tags_data["data"]["tags"]
        assert len(tags) >= 1
        assert any(t["slug"] == "model-photo" for t in tags)

        # Test 3: Query Tag by ID
        tag_by_id_query = """
        query GetTag($id: UUID!) {
            tag(id: $id) {
                id
                name
                slug
            }
        }
        """

        tag_response = await client.post(
            "/graphql",
            json={"query": tag_by_id_query, "variables": {"id": tag_id}},
            headers={"authorization": "Bearer test-token", "x-tenant": "tag-tenant"},
        )

        assert tag_response.status_code == 200
        tag_data = tag_response.json()
        assert "errors" not in tag_data
        assert tag_data["data"]["tag"]["name"] == "Model Photo"

        # Test 4: Query Tag by Slug
        tag_by_slug_query = """
        query GetTagBySlug($slug: String!) {
            tagBySlug(slug: $slug) {
                id
                name
                slug
            }
        }
        """

        slug_response = await client.post(
            "/graphql",
            json={"query": tag_by_slug_query, "variables": {"slug": "model-photo"}},
            headers={"authorization": "Bearer test-token", "x-tenant": "tag-tenant"},
        )

        assert slug_response.status_code == 200
        slug_data = slug_response.json()
        assert "errors" not in slug_data
        assert slug_data["data"]["tagBySlug"]["id"] == tag_id

        # Test 5: Update Tag
        update_tag_mutation = """
        mutation UpdateTag($input: UpdateTagInput!) {
            updateTag(input: $input) {
                id
                name
                slug
                description
            }
        }
        """

        update_response = await client.post(
            "/graphql",
            json={
                "query": update_tag_mutation,
                "variables": {
                    "input": {
                        "id": tag_id,
                        "name": "Model Photos",
                        "description": "Updated description",
                    }
                },
            },
            headers={"authorization": "Bearer test-token", "x-tenant": "tag-tenant"},
        )

        assert update_response.status_code == 200
        update_data = update_response.json()
        assert "errors" not in update_data
        assert update_data["data"]["updateTag"]["name"] == "Model Photos"
        assert update_data["data"]["updateTag"]["slug"] == "model-photos"
        assert update_data["data"]["updateTag"]["description"] == "Updated description"

        # Test 6: Delete Tag
        delete_tag_mutation = """
        mutation DeleteTag($id: UUID!) {
            deleteTag(id: $id)
        }
        """

        delete_response = await client.post(
            "/graphql",
            json={"query": delete_tag_mutation, "variables": {"id": tag_id}},
            headers={"authorization": "Bearer test-token", "x-tenant": "tag-tenant"},
        )

        assert delete_response.status_code == 200
        delete_data = delete_response.json()
        assert "errors" not in delete_data
        assert delete_data["data"]["deleteTag"] is True

        # Verify tag is deleted
        verify_response = await client.post(
            "/graphql",
            json={"query": tag_by_id_query, "variables": {"id": tag_id}},
            headers={"authorization": "Bearer test-token", "x-tenant": "tag-tenant"},
        )

        verify_data = verify_response.json()
        assert verify_data["data"]["tag"] is None


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_tag_generation_association_integration(
    alembic_migrate, test_database, reset_shared_db_connections
):
    """Integration test for tagging generations."""
    dsn, _ = test_database

    import os

    os.environ["BOARDS_DATABASE_URL"] = dsn
    os.environ["BOARDS_AUTH_PROVIDER"] = "none"
    os.environ["BOARDS_AUTH_CONFIG"] = (
        '{"default_user_id": "tag-user-1", "default_tenant": "tag-tenant"}'
    )

    app = create_app()

    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        from boards.database.connection import get_async_session

        # Set up test data inside the client context (after app creation)
        async with get_async_session() as session:
            await cleanup_test_data(session)

            # Create tenant and user
            tenant_id = await ensure_tenant(session, slug="tag-tenant")

            user_id = generate_auth_adapter_user_id("none", "tag-user-1", "tag-tenant")
            user = Users(
                id=user_id,
                tenant_id=tenant_id,
                auth_provider="none",
                auth_subject="tag-user-1",
                email="user1@example.com",
                display_name="User 1",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(user)
            await session.commit()

        # Create board via GraphQL (this creates proper relationships)
        create_board_mutation = """
        mutation CreateBoard($input: CreateBoardInput!) {
            createBoard(input: $input) {
                id
            }
        }
        """

        board_response = await client.post(
            "/graphql",
            json={
                "query": create_board_mutation,
                "variables": {"input": {"title": "Test Board for Tags", "isPublic": False}},
            },
            headers={"authorization": "Bearer test-token", "x-tenant": "tag-tenant"},
        )

        board_data = board_response.json()
        assert "errors" not in board_data, f"GraphQL errors: {board_data.get('errors')}"
        board_id = board_data["data"]["createBoard"]["id"]

        # Create generation using ORM (like test_tag_permission_integration does)
        async with get_async_session() as session:
            generation = Generations()
            generation.tenant_id = tenant_id
            generation.board_id = uuid.UUID(board_id)
            generation.user_id = user_id
            generation.generator_name = "test-generator"
            generation.artifact_type = "image"
            generation.status = "completed"
            generation.progress = Decimal(1)
            generation.input_params = {}
            generation.output_metadata = {}
            generation.created_at = datetime.now(UTC)
            generation.updated_at = datetime.now(UTC)

            session.add(generation)
            await session.commit()
            await session.refresh(generation)
            generation_id = str(generation.id)

        # Create tags
        create_tag_mutation = """
        mutation CreateTag($input: CreateTagInput!) {
            createTag(input: $input) {
                id
                name
                slug
            }
        }
        """

        tag1_response = await client.post(
            "/graphql",
            json={"query": create_tag_mutation, "variables": {"input": {"name": "Top"}}},
            headers={"authorization": "Bearer test-token", "x-tenant": "tag-tenant"},
        )

        tag1_data = tag1_response.json()
        assert "errors" not in tag1_data
        tag1_id = tag1_data["data"]["createTag"]["id"]

        tag2_response = await client.post(
            "/graphql",
            json={"query": create_tag_mutation, "variables": {"input": {"name": "Bottom"}}},
            headers={"authorization": "Bearer test-token", "x-tenant": "tag-tenant"},
        )

        tag2_data = tag2_response.json()
        tag2_id = tag2_data["data"]["createTag"]["id"]

        # First verify the generation is accessible via query
        verify_gen_query = """
        query GetGeneration($id: UUID!) {
            generation(id: $id) {
                id
                generatorName
            }
        }
        """

        verify_response = await client.post(
            "/graphql",
            json={"query": verify_gen_query, "variables": {"id": generation_id}},
            headers={"authorization": "Bearer test-token", "x-tenant": "tag-tenant"},
        )

        verify_data = verify_response.json()
        assert "errors" not in verify_data, f"Generation query failed: {verify_data.get('errors')}"
        assert verify_data["data"]["generation"] is not None, "Generation not found"

        # Add tags to generation
        add_tag_mutation = """
        mutation AddTagToGeneration($generationId: UUID!, $tagId: UUID!) {
            addTagToGeneration(generationId: $generationId, tagId: $tagId) {
                id
                name
            }
        }
        """

        add_tag1_response = await client.post(
            "/graphql",
            json={
                "query": add_tag_mutation,
                "variables": {"generationId": generation_id, "tagId": tag1_id},
            },
            headers={"authorization": "Bearer test-token", "x-tenant": "tag-tenant"},
        )

        assert add_tag1_response.status_code == 200
        add_tag1_data = add_tag1_response.json()
        assert "errors" not in add_tag1_data
        assert add_tag1_data["data"]["addTagToGeneration"]["name"] == "Top"

        add_tag2_response = await client.post(
            "/graphql",
            json={
                "query": add_tag_mutation,
                "variables": {"generationId": generation_id, "tagId": tag2_id},
            },
            headers={"authorization": "Bearer test-token", "x-tenant": "tag-tenant"},
        )

        assert "errors" not in add_tag2_response.json()

        # Query generation with tags
        generation_query = """
        query GetGeneration($id: UUID!) {
            generation(id: $id) {
                id
                tags {
                    id
                    name
                    slug
                }
            }
        }
        """

        gen_with_tags_response = await client.post(
            "/graphql",
            json={"query": generation_query, "variables": {"id": generation_id}},
            headers={"authorization": "Bearer test-token", "x-tenant": "tag-tenant"},
        )

        gen_with_tags_data = gen_with_tags_response.json()
        assert "errors" not in gen_with_tags_data

        tags = gen_with_tags_data["data"]["generation"]["tags"]
        assert len(tags) == 2
        tag_names = [t["name"] for t in tags]
        assert "Top" in tag_names
        assert "Bottom" in tag_names

        # Remove a tag
        remove_tag_mutation = """
        mutation RemoveTagFromGeneration($generationId: UUID!, $tagId: UUID!) {
            removeTagFromGeneration(generationId: $generationId, tagId: $tagId)
        }
        """

        remove_response = await client.post(
            "/graphql",
            json={
                "query": remove_tag_mutation,
                "variables": {"generationId": generation_id, "tagId": tag1_id},
            },
            headers={"authorization": "Bearer test-token", "x-tenant": "tag-tenant"},
        )

        assert remove_response.status_code == 200
        remove_data = remove_response.json()
        assert "errors" not in remove_data
        assert remove_data["data"]["removeTagFromGeneration"] is True

        # Verify tag was removed
        verify_response = await client.post(
            "/graphql",
            json={"query": generation_query, "variables": {"id": generation_id}},
            headers={"authorization": "Bearer test-token", "x-tenant": "tag-tenant"},
        )

        verify_data = verify_response.json()
        tags = verify_data["data"]["generation"]["tags"]
        assert len(tags) == 1
        assert tags[0]["name"] == "Bottom"


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_tag_duplicate_slug_error(
    alembic_migrate, test_database, reset_shared_db_connections
):
    """Integration test for duplicate slug error handling."""
    dsn, _ = test_database

    import os

    os.environ["BOARDS_DATABASE_URL"] = dsn
    os.environ["BOARDS_AUTH_PROVIDER"] = "none"
    os.environ["BOARDS_AUTH_CONFIG"] = (
        '{"default_user_id": "tag-user-1", "default_tenant": "tag-tenant"}'
    )

    app = create_app()

    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        from boards.database.connection import get_async_session

        async with get_async_session() as session:
            await cleanup_test_data(session)

            tenant_id = await ensure_tenant(session, slug="tag-tenant")

            user_id = generate_auth_adapter_user_id("none", "tag-user-1", "tag-tenant")
            user = Users(
                id=user_id,
                tenant_id=tenant_id,
                auth_provider="none",
                auth_subject="tag-user-1",
                email="user1@example.com",
                display_name="User 1",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(user)
            await session.commit()

        create_tag_mutation = """
        mutation CreateTag($input: CreateTagInput!) {
            createTag(input: $input) {
                id
                name
                slug
            }
        }
        """

        # Create first tag
        first_response = await client.post(
            "/graphql",
            json={"query": create_tag_mutation, "variables": {"input": {"name": "Shoes"}}},
            headers={"authorization": "Bearer test-token", "x-tenant": "tag-tenant"},
        )

        assert "errors" not in first_response.json()

        # Try to create duplicate
        duplicate_response = await client.post(
            "/graphql",
            json={"query": create_tag_mutation, "variables": {"input": {"name": "Shoes"}}},
            headers={"authorization": "Bearer test-token", "x-tenant": "tag-tenant"},
        )

        duplicate_data = duplicate_response.json()
        assert "errors" in duplicate_data
        assert "already exists" in str(duplicate_data["errors"])


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_tag_permission_integration(
    alembic_migrate, test_database, reset_shared_db_connections
):
    """Integration test for tag permission checks on generations."""
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

            # Create tenant and two users
            tenant_id = await ensure_tenant(session, slug="tag-tenant")

            owner_id = generate_auth_adapter_user_id("none", "tag-user-1", "tag-tenant")
            owner = Users(
                id=owner_id,
                tenant_id=tenant_id,
                auth_provider="none",
                auth_subject="tag-user-1",
                email="owner@example.com",
                display_name="Owner",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(owner)

            other_id = generate_auth_adapter_user_id("none", "tag-user-2", "tag-tenant")
            other = Users(
                id=other_id,
                tenant_id=tenant_id,
                auth_provider="none",
                auth_subject="tag-user-2",
                email="other@example.com",
                display_name="Other User",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(other)

            await session.commit()

        # Owner creates board and generation
        os.environ["BOARDS_AUTH_CONFIG"] = (
            '{"default_user_id": "tag-user-1", "default_tenant": "tag-tenant"}'
        )

        create_board_mutation = """
        mutation CreateBoard($input: CreateBoardInput!) {
            createBoard(input: $input) {
                id
            }
        }
        """

        board_response = await client.post(
            "/graphql",
            json={
                "query": create_board_mutation,
                "variables": {"input": {"title": "Private Board", "isPublic": False}},
            },
            headers={"authorization": "Bearer test-token", "x-tenant": "tag-tenant"},
        )

        board_id = board_response.json()["data"]["createBoard"]["id"]

        # Create generation directly in the database
        async with get_async_session() as session:
            generation = Generations()
            generation.tenant_id = tenant_id
            generation.board_id = uuid.UUID(board_id)
            generation.user_id = owner_id
            generation.generator_name = "test-generator"
            generation.artifact_type = "image"
            generation.status = "completed"
            generation.progress = Decimal(1)
            generation.input_params = {}
            generation.output_metadata = {}
            generation.created_at = datetime.now(UTC)
            generation.updated_at = datetime.now(UTC)

            session.add(generation)
            await session.commit()
            await session.refresh(generation)
            generation_id = str(generation.id)

        # Create a tag (as owner)
        create_tag_mutation = """
        mutation CreateTag($input: CreateTagInput!) {
            createTag(input: $input) {
                id
            }
        }
        """

        tag_response = await client.post(
            "/graphql",
            json={"query": create_tag_mutation, "variables": {"input": {"name": "Test"}}},
            headers={"authorization": "Bearer test-token", "x-tenant": "tag-tenant"},
        )

        tag_id = tag_response.json()["data"]["createTag"]["id"]

        # Switch to other user (not owner or member)
        os.environ["BOARDS_AUTH_CONFIG"] = (
            '{"default_user_id": "tag-user-2", "default_tenant": "tag-tenant"}'
        )

        # Other user tries to add tag to generation - should fail
        add_tag_mutation = """
        mutation AddTagToGeneration($generationId: UUID!, $tagId: UUID!) {
            addTagToGeneration(generationId: $generationId, tagId: $tagId) {
                id
            }
        }
        """

        add_response = await client.post(
            "/graphql",
            json={
                "query": add_tag_mutation,
                "variables": {"generationId": generation_id, "tagId": tag_id},
            },
            headers={"authorization": "Bearer test-token", "x-tenant": "tag-tenant"},
        )

        add_data = add_response.json()
        assert "errors" in add_data
        # Should fail because user doesn't have access to the private board
        assert (
            "denied" in str(add_data["errors"]).lower()
            or "not found" in str(add_data["errors"]).lower()
        )
