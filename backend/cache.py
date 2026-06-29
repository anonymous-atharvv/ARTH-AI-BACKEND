# backend/cache.py
"""Singleton Redis connection pool for ArthAI."""
import redis.asyncio as aioredis
from config import settings
import structlog

logger = structlog.get_logger()
_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Return the shared Redis connection pool. Safe to call from any async context."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )
        logger.info("Redis connection pool created", url=settings.REDIS_URL[:20])
    return _redis_pool


async def close_redis():
    """Call on application shutdown."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None
