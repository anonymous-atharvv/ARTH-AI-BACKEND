# backend/services/cache_manager.py
"""Centralized cache invalidation service."""
from cache import get_redis

async def invalidate_user_caches(user_id: str):
    """
    Call this after any transaction mutation.
    Invalidates: ArthScore Redis cache, analytics summary flags.
    """
    try:
        redis = await get_redis()
        # Invalidate various Redis cache keys for the user
        await redis.delete(f"arthscore:{user_id}")
        await redis.delete(f"dashboard_cache:{user_id}")
        await redis.delete(f"pnl_cache:{user_id}:90d")
        await redis.delete(f"pnl_cache:{user_id}:30d")
        await redis.delete(f"pnl_cache:{user_id}:7d")
    except Exception:
        pass  # Fail-safe caching
