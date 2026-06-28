# backend/routes/analytics.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services.analytics import AnalyticsService

router = APIRouter()


@router.get("/pnl/{user_id}")
async def get_pnl(
    user_id: str,
    period: str = Query("90d", enum=["7d", "30d", "90d", "1y"]),
    db: AsyncSession = Depends(get_db),
):
    """Returns P&L data for charting."""
    service = AnalyticsService(db)
    return await service.get_pnl_data(user_id, period)


@router.get("/cash-flow/{user_id}")
async def get_cash_flow(user_id: str, db: AsyncSession = Depends(get_db)):
    """7-day and 30-day cash flow + 7-day forecast."""
    service = AnalyticsService(db)
    return await service.get_cash_flow(user_id)


@router.get("/summary/{user_id}")
async def get_summary(user_id: str, db: AsyncSession = Depends(get_db)):
    """Dashboard summary — all KPIs in one call."""
    service = AnalyticsService(db)
    return await service.get_dashboard_summary(user_id)
