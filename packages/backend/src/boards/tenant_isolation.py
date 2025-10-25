"""
Tenant isolation validation and enforcement utilities.

This module provides utilities to validate and enforce tenant isolation
across the application to ensure data security in multi-tenant deployments.
"""

from __future__ import annotations

from datetime import UTC
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .dbmodels import Boards, Generations, Users
from .logging import get_logger

logger = get_logger(__name__)


class TenantIsolationError(Exception):
    """Raised when tenant isolation validation fails."""

    pass


class TenantIsolationValidator:
    """
    Utility class for validating tenant isolation in multi-tenant environments.

    This class provides methods to:
    1. Validate tenant-scoped queries
    2. Check for cross-tenant data access
    3. Ensure proper tenant filtering
    4. Audit tenant isolation compliance
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_user_tenant_isolation(self, user_id: UUID, tenant_id: UUID) -> bool:
        """
        Validate that a user belongs to the specified tenant.

        Args:
            user_id: UUID of the user
            tenant_id: UUID of the tenant

        Returns:
            True if user belongs to tenant, False otherwise

        Raises:
            TenantIsolationError: If validation fails
        """
        try:
            stmt = select(Users).where((Users.id == user_id) & (Users.tenant_id == tenant_id))
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.warning(
                    "User tenant isolation violation",
                    user_id=str(user_id),
                    expected_tenant=str(tenant_id),
                )
                return False

            return True

        except Exception as e:
            logger.error(
                "User tenant isolation validation failed",
                user_id=str(user_id),
                tenant_id=str(tenant_id),
                error=str(e),
            )
            raise TenantIsolationError(f"User tenant validation failed: {e}") from e

    async def validate_board_tenant_isolation(self, board_id: UUID, tenant_id: UUID) -> bool:
        """
        Validate that a board belongs to the specified tenant.

        Args:
            board_id: UUID of the board
            tenant_id: UUID of the tenant

        Returns:
            True if board belongs to tenant, False otherwise
        """
        try:
            stmt = select(Boards).where((Boards.id == board_id) & (Boards.tenant_id == tenant_id))
            result = await self.db.execute(stmt)
            board = result.scalar_one_or_none()

            if not board:
                logger.warning(
                    "Board tenant isolation violation",
                    board_id=str(board_id),
                    expected_tenant=str(tenant_id),
                )
                return False

            return True

        except Exception as e:
            logger.error(
                "Board tenant isolation validation failed",
                board_id=str(board_id),
                tenant_id=str(tenant_id),
                error=str(e),
            )
            raise TenantIsolationError(f"Board tenant validation failed: {e}") from e

    async def validate_generation_tenant_isolation(
        self, generation_id: UUID, tenant_id: UUID
    ) -> bool:
        """
        Validate that a generation belongs to the specified tenant.
        """
        try:
            stmt = select(Generations).where(
                (Generations.id == generation_id) & (Generations.tenant_id == tenant_id)
            )
            result = await self.db.execute(stmt)
            generation = result.scalar_one_or_none()

            if not generation:
                logger.warning(
                    "Generation tenant isolation violation",
                    generation_id=str(generation_id),
                    expected_tenant=str(tenant_id),
                )
                return False

            return True

        except Exception as e:
            logger.error(
                "Generation tenant isolation validation failed",
                generation_id=str(generation_id),
                tenant_id=str(tenant_id),
                error=str(e),
            )
            raise TenantIsolationError(f"Generation tenant validation failed: {e}") from e

    async def audit_tenant_isolation(self, tenant_id: UUID) -> dict[str, Any]:
        """
        Perform comprehensive tenant isolation audit.

        Args:
            tenant_id: UUID of the tenant to audit

        Returns:
            Dictionary with audit results and statistics
        """
        logger.info("Starting tenant isolation audit", tenant_id=str(tenant_id))

        audit_results = {
            "tenant_id": str(tenant_id),
            "audit_timestamp": None,
            "isolation_violations": [],
            "statistics": {},
            "recommendations": [],
        }

        try:
            from datetime import datetime

            audit_results["audit_timestamp"] = datetime.now(UTC).isoformat()

            # 1. Check for orphaned records
            orphaned_records = await self._check_orphaned_records(tenant_id)
            if orphaned_records:
                audit_results["isolation_violations"].extend(orphaned_records)

            # 2. Check cross-tenant board memberships
            cross_tenant_memberships = await self._check_cross_tenant_memberships(tenant_id)
            if cross_tenant_memberships:
                audit_results["isolation_violations"].extend(cross_tenant_memberships)

            # 3. Gather tenant statistics
            audit_results["statistics"] = await self._gather_tenant_statistics(tenant_id)

            # 4. Generate recommendations
            audit_results["recommendations"] = self._generate_isolation_recommendations(
                audit_results["isolation_violations"]
            )

            logger.info(
                "Tenant isolation audit completed",
                tenant_id=str(tenant_id),
                violations_count=len(audit_results["isolation_violations"]),
            )

            return audit_results

        except Exception as e:
            logger.error(
                "Tenant isolation audit failed",
                tenant_id=str(tenant_id),
                error=str(e),
            )
            raise TenantIsolationError(f"Tenant isolation audit failed: {e}") from e

    async def _check_orphaned_records(self, tenant_id: UUID) -> list[dict[str, Any]]:
        """Check for records that should belong to tenant but don't."""
        violations = []

        try:
            # Check for users with boards in different tenants
            stmt = text(
                """
                SELECT u.id as user_id, b.id as board_id, b.tenant_id as board_tenant_id
                FROM users u
                JOIN boards b ON u.id = b.owner_id
                WHERE u.tenant_id = :tenant_id AND b.tenant_id != :tenant_id
            """
            )
            result = await self.db.execute(stmt, {"tenant_id": tenant_id})
            orphaned_boards = result.fetchall()

            for row in orphaned_boards:
                violations.append(
                    {
                        "type": "orphaned_board",
                        "description": f"User {row.user_id} owns board {row.board_id} in different tenant",  # noqa: E501
                        "user_id": str(row.user_id),
                        "board_id": str(row.board_id),
                        "board_tenant_id": str(row.board_tenant_id),
                    }
                )

            # Check for generations with boards in different tenants
            stmt = text(
                """
                SELECT g.id as generation_id,
                    g.tenant_id,
                    g.board_id,
                    b.tenant_id as board_tenant_id
                FROM generations g
                JOIN boards b ON g.board_id = b.id
                WHERE g.tenant_id = :tenant_id AND b.tenant_id != :tenant_id
            """
            )
            result = await self.db.execute(stmt, {"tenant_id": tenant_id})
            orphaned_generations = result.fetchall()

            for row in orphaned_generations:
                violations.append(
                    {
                        "type": "orphaned_generation",
                        "description": f"Generation {row.generation_id} belongs to different tenant than its board",  # noqa: E501
                        "generation_id": str(row.generation_id),
                        "board_id": str(row.board_id),
                        "board_tenant_id": str(row.board_tenant_id),
                    }
                )

        except Exception as e:
            logger.error("Failed to check orphaned records", error=str(e))

        return violations

    async def _check_cross_tenant_memberships(self, tenant_id: UUID) -> list[dict[str, Any]]:
        """Check for cross-tenant board memberships."""
        violations = []

        try:
            stmt = text(
                """
                SELECT bm.board_id,
                    bm.user_id,
                    b.tenant_id as board_tenant_id,
                    u.tenant_id as user_tenant_id
                FROM board_members bm
                JOIN boards b ON bm.board_id = b.id
                JOIN users u ON bm.user_id = u.id
                WHERE b.tenant_id = :tenant_id AND u.tenant_id != :tenant_id
            """
            )
            result = await self.db.execute(stmt, {"tenant_id": tenant_id})
            cross_tenant_members = result.fetchall()

            for row in cross_tenant_members:
                violations.append(
                    {
                        "type": "cross_tenant_membership",
                        "description": "User from different tenant has board membership",
                        "board_id": str(row.board_id),
                        "user_id": str(row.user_id),
                        "board_tenant_id": str(row.board_tenant_id),
                        "user_tenant_id": str(row.user_tenant_id),
                    }
                )

        except Exception as e:
            logger.error("Failed to check cross-tenant memberships", error=str(e))

        return violations

    async def _gather_tenant_statistics(self, tenant_id: UUID) -> dict[str, int]:
        """Gather statistics for the tenant."""
        stats = {}

        try:
            # Count users
            stmt = select(Users).where(Users.tenant_id == tenant_id)
            result = await self.db.execute(stmt)
            stats["users_count"] = len(result.scalars().all())

            # Count boards
            stmt = select(Boards).where(Boards.tenant_id == tenant_id)
            result = await self.db.execute(stmt)
            stats["boards_count"] = len(result.scalars().all())

            # Count generations
            stmt = select(Generations).where(Generations.tenant_id == tenant_id)
            result = await self.db.execute(stmt)
            stats["generations_count"] = len(result.scalars().all())

            # Count board memberships
            stmt = text(
                """
                SELECT COUNT(*) as count
                FROM board_members bm
                JOIN boards b ON bm.board_id = b.id
                WHERE b.tenant_id = :tenant_id
            """
            )
            result = await self.db.execute(stmt, {"tenant_id": tenant_id})
            stats["board_memberships_count"] = result.scalar()

        except Exception as e:
            logger.error("Failed to gather tenant statistics", error=str(e))

        return stats

    def _generate_isolation_recommendations(self, violations: list[dict[str, Any]]) -> list[str]:
        """Generate recommendations based on isolation violations."""
        recommendations = []

        if not violations:
            recommendations.append("Tenant isolation is properly maintained - no violations found")
            return recommendations

        violation_types = {v["type"] for v in violations}

        if "orphaned_board" in violation_types:
            recommendations.append(
                "Fix orphaned boards by ensuring board tenant_id matches owner's tenant_id"
            )

        if "orphaned_generation" in violation_types:
            recommendations.append(
                "Fix orphaned generations by ensuring generation tenant_id matches board tenant_id"
            )

        if "cross_tenant_membership" in violation_types:
            recommendations.append(
                "Remove cross-tenant board memberships or migrate users to appropriate tenants"
            )

        recommendations.append("Run isolation audit regularly to detect future violations")
        recommendations.append(
            "Consider adding database constraints to prevent isolation violations"
        )

        return recommendations


async def ensure_tenant_isolation(
    db: AsyncSession,
    user_id: UUID | None,
    tenant_id: UUID,
    resource_type: str,
    resource_id: UUID | None = None,
) -> None:
    """
    Ensure tenant isolation for a specific operation.

    Args:
        db: Database session
        user_id: ID of the user performing the operation
        tenant_id: ID of the tenant context
        resource_type: Type of resource being accessed (user, board, generation)
        resource_id: ID of the specific resource (if applicable)

    Raises:
        TenantIsolationError: If isolation validation fails
    """
    if not settings.multi_tenant_mode:
        # Skip validation in single-tenant mode
        return

    validator = TenantIsolationValidator(db)

    try:
        # Validate user belongs to tenant
        if user_id:
            user_valid = await validator.validate_user_tenant_isolation(user_id, tenant_id)
            if not user_valid:
                raise TenantIsolationError(f"User {user_id} does not belong to tenant {tenant_id}")

        # Validate resource belongs to tenant (if resource_id provided)
        if resource_id:
            if resource_type == "board":
                board_valid = await validator.validate_board_tenant_isolation(
                    resource_id, tenant_id
                )
                if not board_valid:
                    raise TenantIsolationError(
                        f"Board {resource_id} does not belong to tenant {tenant_id}"
                    )

            elif resource_type == "generation":
                generation_valid = await validator.validate_generation_tenant_isolation(
                    resource_id, tenant_id
                )
                if not generation_valid:
                    raise TenantIsolationError(
                        f"Generation {resource_id} does not belong to tenant {tenant_id}"
                    )

        logger.debug(
            "Tenant isolation validated successfully",
            user_id=str(user_id) if user_id else None,
            tenant_id=str(tenant_id),
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
        )

    except TenantIsolationError:
        # Re-raise isolation errors
        raise
    except Exception as e:
        logger.error(
            "Tenant isolation validation error",
            user_id=str(user_id) if user_id else None,
            tenant_id=str(tenant_id),
            resource_type=resource_type,
            error=str(e),
        )
        raise TenantIsolationError(f"Tenant isolation validation failed: {e}") from e
