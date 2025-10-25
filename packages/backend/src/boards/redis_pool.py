"""Centralized Redis connection pool management.

This module provides a singleton Redis connection pool that can be shared
across the application to reduce connection overhead and improve performance.
"""

from __future__ import annotations

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from .config import Settings
from .logging import get_logger

logger = get_logger(__name__)


class RedisPoolManager:
    """Singleton manager for Redis connection pool."""

    _instance: RedisPoolManager | None = None
    _pool: ConnectionPool | None = None
    _client: redis.Redis | None = None

    def __new__(cls) -> RedisPoolManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the Redis pool manager."""
        if self._pool is None:
            settings = Settings()

            # Create connection pool with sensible defaults
            # These can be tuned based on your application's needs
            self._pool = redis.ConnectionPool.from_url(
                settings.redis_url,
                decode_responses=True,
                max_connections=50,  # Maximum number of connections
                socket_connect_timeout=5,  # Connection timeout in seconds
                socket_timeout=5,  # Socket timeout in seconds
                retry_on_timeout=True,  # Retry on timeout
                health_check_interval=30,  # Health check every 30 seconds
            )

            # Create Redis client using the pool
            self._client = redis.Redis(connection_pool=self._pool)

            logger.info(
                "Redis connection pool initialized with max_connections=50, "
                "health_check_interval=30s"
            )

    @property
    def client(self) -> redis.Redis:
        """Get the Redis client with connection pooling."""
        if self._client is None:
            raise RuntimeError("Redis pool not initialized")
        return self._client

    @property
    def pool(self) -> ConnectionPool:
        """Get the underlying connection pool."""
        if self._pool is None:
            raise RuntimeError("Redis pool not initialized")
        return self._pool

    async def close(self):
        """Close the Redis connection pool."""
        if self._client:
            await self._client.close()
            logger.info("Redis client closed")
        if self._pool:
            await self._pool.disconnect()
            logger.info("Redis connection pool disconnected")

    async def health_check(self) -> bool:
        """Check if Redis connection is healthy."""
        try:
            if self._client is None:
                logger.error("Redis client not initialized")
                return False
            await self._client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


# Global instance
_redis_pool_manager = RedisPoolManager()


def get_redis_client() -> redis.Redis:
    """Get a Redis client with connection pooling.

    Returns:
        Redis client instance with connection pooling enabled.
    """
    return _redis_pool_manager.client


async def close_redis_pool():
    """Close the Redis connection pool.

    Call this during application shutdown to cleanly close connections.
    """
    await _redis_pool_manager.close()


async def check_redis_health() -> bool:
    """Check if Redis is healthy and accessible.

    Returns:
        True if Redis is healthy, False otherwise.
    """
    return await _redis_pool_manager.health_check()
