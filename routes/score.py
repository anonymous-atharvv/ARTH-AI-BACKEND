# backend/routes/score.py
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from agents.arthascore import ArthScoreEngine
from middleware.auth import get_current_user_id
from config import settings
from cache import get_redis
from middleware.rate_limit import limiter

router = APIRouter()


@router.get("/{user_id}")
@limiter.limit("10/minute")
async def get_arthascore(
    request: Request,
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Calculate and return ArthScore for a user, using Redis cache if available."""
    if settings.ENVIRONMENT == "production":
        if current_user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif user_id != current_user_id and not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Try reading from cache
    try:
        redis = await get_redis()
        cached = await redis.get(f"arthscore:{user_id}")
        if cached:
            cached_str = cached.decode() if isinstance(cached, bytes) else cached
            return json.loads(cached_str)
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


@router.get("")
@router.get("/")
@limiter.limit("10/minute")
async def get_current_user_arthascore(
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Calculate and return ArthScore for the authenticated user."""
    return await get_arthascore(
        request=request,
        user_id=current_user_id,
        current_user_id=current_user_id,
        db=db,
    )


@router.get("/{user_id}/history")
@limiter.limit("30/minute")
async def get_arthascore_history(
    request: Request,
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Returns last 12 ArthScore snapshots for trajectory chart."""
    if settings.ENVIRONMENT == "production":
        if current_user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif user_id != current_user_id and not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Forbidden")

    from models.arthascore import ArthScoreHistory
    from sqlalchemy import desc

    result = await db.execute(
        select(ArthScoreHistory)
        .where(ArthScoreHistory.user_id == user_id)
        .order_by(desc(ArthScoreHistory.calculated_at))
        .limit(12)
    )
    history = result.scalars().all()

    return {
        "user_id": user_id,
        "history": [
            {
                "score": h.score,
                "grade": "Excellent" if h.score >= 750 else "Good" if h.score >= 650 else "Fair" if h.score >= 500 else "Needs Improvement",
                "date": h.calculated_at[:10],
                "data_points": h.data_points,
            }
            for h in reversed(history)
        ]
    }
