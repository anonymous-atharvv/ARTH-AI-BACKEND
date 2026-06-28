# backend/routes/score.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from agents.arthascore import ArthScoreEngine

router = APIRouter()


@router.get("/{user_id}")
async def get_arthascore(user_id: str, db: AsyncSession = Depends(get_db)):
    """Calculate and return ArthScore for a user."""
    engine = ArthScoreEngine(db)
    result = await engine.calculate(user_id, lookback_days=90)
    return result
