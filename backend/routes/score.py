# backend/routes/score.py
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from database import get_db
from agents.arthascore import ArthScoreEngine
from middleware.auth import get_current_user_id
from config import settings

router = APIRouter()

async def get_redis():
    return await aioredis.from_url(settings.REDIS_URL)


@router.get("/{user_id}")
async def get_arthascore(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Calculate and return ArthScore for a user, using Redis cache if available."""
    if user_id != current_user_id and not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Try reading from cache
    try:
        redis = await get_redis()
        cached = await redis.get(f"arthscore:{user_id}")
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    engine = ArthScoreEngine(db)
    result = await engine.calculate(user_id, lookback_days=90)

    # Save to cache
    try:
        redis = await get_redis()
        await redis.setex(f"arthscore:{user_id}", 3600, json.dumps(result))
    except Exception:
        pass

    return result
