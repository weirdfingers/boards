"""
Tests for tenant isolation validation and enforcement.
"""

from unittest.mock import patch
from uuid import uuid4

import pytest

from src.boards.database.seed_data import ensure_tenant
from src.boards.dbmodels import Boards, Users
from src.boards.tenant_isolation import (
    TenantIsolationError,
    TenantIsolationValidator,
    ensure_tenant_isolation,
)


class TestTenantIsolationValidator:
    """Test the TenantIsolationValidator class."""

    @pytest.fixture
    async def tenant_a(self, db_session):
        """Create tenant A for testing."""
        return await ensure_tenant(db_session, name="Tenant A", slug="tenant-a")

    @pytest.fixture
    async def tenant_b(self, db_session):
        """Create tenant B for testing."""
        return await ensure_tenant(db_session, name="Tenant B", slug="tenant-b")

    @pytest.fixture
    async def user_in_tenant_a(self, db_session, tenant_a):
        """Create a user in tenant A."""
        user = Users(
            tenant_id=tenant_a,
            auth_provider="test",
            auth_subject="user-a",
            email="user-a@example.com",
            display_name="User A",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest.fixture
    async def user_in_tenant_b(self, db_session, tenant_b):
        """Create a user in tenant B."""
        user = Users(
            tenant_id=tenant_b,
            auth_provider="test",
            auth_subject="user-b",
            email="user-b@example.com",
            display_name="User B",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest.fixture
    async def board_in_tenant_a(self, db_session, tenant_a, user_in_tenant_a):
        """Create a board in tenant A."""
        board = Boards(
            tenant_id=tenant_a,
            owner_id=user_in_tenant_a.id,
            name="Board A",
            description="Test board in tenant A",
        )
        db_session.add(board)
        await db_session.commit()
        await db_session.refresh(board)
        return board

    async def test_validate_user_tenant_isolation_valid(
        self, db_session, tenant_a, user_in_tenant_a
    ):
        """Test user tenant isolation validation with valid user."""
        validator = TenantIsolationValidator(db_session)

        result = await validator.validate_user_tenant_isolation(
            user_in_tenant_a.id, tenant_a
        )

        assert result is True

    async def test_validate_user_tenant_isolation_invalid(
        self, db_session, tenant_a, tenant_b, user_in_tenant_a
    ):
        """Test user tenant isolation validation with invalid user."""
        validator = TenantIsolationValidator(db_session)

        result = await validator.validate_user_tenant_isolation(
            user_in_tenant_a.id, tenant_b
        )

        assert result is False

    async def test_validate_board_tenant_isolation_valid(
        self, db_session, tenant_a, board_in_tenant_a
    ):
        """Test board tenant isolation validation with valid board."""
        validator = TenantIsolationValidator(db_session)

        result = await validator.validate_board_tenant_isolation(
            board_in_tenant_a.id, tenant_a
        )

        assert result is True

    async def test_validate_board_tenant_isolation_invalid(
        self, db_session, tenant_b, board_in_tenant_a
    ):
        """Test board tenant isolation validation with invalid board."""
        validator = TenantIsolationValidator(db_session)

        result = await validator.validate_board_tenant_isolation(
            board_in_tenant_a.id, tenant_b
        )

        assert result is False

    async def test_audit_tenant_isolation_clean(
        self, db_session, tenant_a, user_in_tenant_a, board_in_tenant_a
    ):
        """Test tenant isolation audit with clean tenant."""
        # Use fixtures for setup
        _ = user_in_tenant_a, board_in_tenant_a
        validator = TenantIsolationValidator(db_session)

        audit_result = await validator.audit_tenant_isolation(tenant_a)

        assert audit_result["tenant_id"] == str(tenant_a)
        assert len(audit_result["isolation_violations"]) == 0
        assert audit_result["statistics"]["users_count"] == 1
        assert audit_result["statistics"]["boards_count"] == 1
        assert "no violations found" in audit_result["recommendations"][0]

    async def test_audit_tenant_isolation_with_violations(
        self, db_session, tenant_a, tenant_b, user_in_tenant_a
    ):
        """Test tenant isolation audit with violations."""
        # Create a board in tenant B owned by user in tenant A (violation)
        board = Boards(
            tenant_id=tenant_b,  # Different tenant than owner
            owner_id=user_in_tenant_a.id,
            name="Violation Board",
            description="Board that violates tenant isolation",
        )
        db_session.add(board)
        await db_session.commit()

        validator = TenantIsolationValidator(db_session)
        audit_result = await validator.audit_tenant_isolation(tenant_a)

        # Should detect the orphaned board violation
        violations = audit_result["isolation_violations"]
        assert len(violations) > 0

        orphaned_violations = [v for v in violations if v["type"] == "orphaned_board"]
        assert len(orphaned_violations) == 1
        assert orphaned_violations[0]["user_id"] == str(user_in_tenant_a.id)
        assert orphaned_violations[0]["board_id"] == str(board.id)


class TestEnsureTenantIsolation:
    """Test the ensure_tenant_isolation function."""

    @pytest.fixture
    async def tenant_id(self, db_session):
        """Create a tenant for testing."""
        return await ensure_tenant(db_session, name="Test Tenant", slug="test-tenant")

    @pytest.fixture
    async def user_id(self, db_session, tenant_id):
        """Create a user for testing."""
        user = Users(
            tenant_id=tenant_id,
            auth_provider="test",
            auth_subject="test-user",
            email="test@example.com",
            display_name="Test User",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user.id

    async def test_ensure_tenant_isolation_valid_user(
        self, db_session, user_id, tenant_id
    ):
        """Test ensure_tenant_isolation with valid user."""
        with patch("src.boards.config.settings.multi_tenant_mode", True):
            # Should not raise exception
            await ensure_tenant_isolation(
                db_session, user_id, tenant_id, "user"
            )

    async def test_ensure_tenant_isolation_invalid_user(
        self, db_session, user_id
    ):
        """Test ensure_tenant_isolation with invalid user."""
        wrong_tenant_id = uuid4()

        with patch("src.boards.config.settings.multi_tenant_mode", True):
            with pytest.raises(TenantIsolationError, match="does not belong to tenant"):
                await ensure_tenant_isolation(
                    db_session, user_id, wrong_tenant_id, "user"
                )

    async def test_ensure_tenant_isolation_single_tenant_mode(
        self, db_session, user_id
    ):
        """Test ensure_tenant_isolation in single-tenant mode (should skip validation)."""
        wrong_tenant_id = uuid4()

        with patch("src.boards.config.settings.multi_tenant_mode", False):
            # Should not raise exception in single-tenant mode
            await ensure_tenant_isolation(
                db_session, user_id, wrong_tenant_id, "user"
            )


class TestTenantIsolationIntegration:
    """Integration tests for tenant isolation across the system."""

    @pytest.fixture
    async def multi_tenant_setup(self, db_session):
        """Set up multi-tenant test environment."""
        # Create two tenants
        tenant_a = await ensure_tenant(db_session, name="Company A", slug="company-a")
        tenant_b = await ensure_tenant(db_session, name="Company B", slug="company-b")

        # Create users in each tenant
        user_a = Users(
            tenant_id=tenant_a,
            auth_provider="test",
            auth_subject="user-a",
            email="admin@company-a.com",
            display_name="Admin A",
        )
        user_b = Users(
            tenant_id=tenant_b,
            auth_provider="test",
            auth_subject="user-b",
            email="admin@company-b.com",
            display_name="Admin B",
        )
        db_session.add_all([user_a, user_b])
        await db_session.commit()
        await db_session.refresh(user_a)
        await db_session.refresh(user_b)

        # Create boards in each tenant
        board_a = Boards(
            tenant_id=tenant_a,
            owner_id=user_a.id,
            name="Company A Board",
            description="Board for Company A",
        )
        board_b = Boards(
            tenant_id=tenant_b,
            owner_id=user_b.id,
            name="Company B Board",
            description="Board for Company B",
        )
        db_session.add_all([board_a, board_b])
        await db_session.commit()
        await db_session.refresh(board_a)
        await db_session.refresh(board_b)

        return {
            "tenant_a": tenant_a,
            "tenant_b": tenant_b,
            "user_a": user_a,
            "user_b": user_b,
            "board_a": board_a,
            "board_b": board_b,
        }

    async def test_cross_tenant_access_prevention(
        self, db_session, multi_tenant_setup
    ):
        """Test that cross-tenant access is properly prevented."""
        setup = multi_tenant_setup

        with patch("src.boards.config.settings.multi_tenant_mode", True):
            # User A should not be able to access Board B
            with pytest.raises(TenantIsolationError):
                await ensure_tenant_isolation(
                    db_session,
                    setup["user_a"].id,
                    setup["tenant_a"],
                    "board",
                    setup["board_b"].id,  # Board from different tenant
                )

            # User B should not be able to access Board A
            with pytest.raises(TenantIsolationError):
                await ensure_tenant_isolation(
                    db_session,
                    setup["user_b"].id,
                    setup["tenant_b"],
                    "board",
                    setup["board_a"].id,  # Board from different tenant
                )

    async def test_same_tenant_access_allowed(
        self, db_session, multi_tenant_setup
    ):
        """Test that same-tenant access is allowed."""
        setup = multi_tenant_setup

        with patch("src.boards.config.settings.multi_tenant_mode", True):
            # User A should be able to access Board A (same tenant)
            await ensure_tenant_isolation(
                db_session,
                setup["user_a"].id,
                setup["tenant_a"],
                "board",
                setup["board_a"].id,
            )

            # User B should be able to access Board B (same tenant)
            await ensure_tenant_isolation(
                db_session,
                setup["user_b"].id,
                setup["tenant_b"],
                "board",
                setup["board_b"].id,
            )

    async def test_comprehensive_isolation_audit(
        self, db_session, multi_tenant_setup
    ):
        """Test comprehensive audit across multiple tenants."""
        setup = multi_tenant_setup
        validator = TenantIsolationValidator(db_session)

        # Audit tenant A
        audit_a = await validator.audit_tenant_isolation(setup["tenant_a"])
        assert len(audit_a["isolation_violations"]) == 0
        assert audit_a["statistics"]["users_count"] == 1
        assert audit_a["statistics"]["boards_count"] == 1

        # Audit tenant B
        audit_b = await validator.audit_tenant_isolation(setup["tenant_b"])
        assert len(audit_b["isolation_violations"]) == 0
        assert audit_b["statistics"]["users_count"] == 1
        assert audit_b["statistics"]["boards_count"] == 1
