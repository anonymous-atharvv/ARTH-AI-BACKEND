# backend/routes/analytics.py
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services.analytics import AnalyticsService
from middleware.auth import get_current_user_id
from config import settings

router = APIRouter()


@router.get("/pnl/{user_id}")
async def get_pnl(
    user_id: str,
    period: str = Query("90d", enum=["7d", "30d", "90d", "1y"]),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Returns P&L data for charting."""
    if settings.ENVIRONMENT == "production":
        if current_user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif user_id != current_user_id and not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Forbidden")

    service = AnalyticsService(db)
    return await service.get_pnl_data(user_id, period)


@router.get("/pnl")
async def get_current_user_pnl(
    period: str = Query("90d", enum=["7d", "30d", "90d", "1y"]),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Returns P&L data for the authenticated user."""
    service = AnalyticsService(db)
    return await service.get_pnl_data(current_user_id, period)


@router.get("/cash-flow/forecast/{user_id}")
async def get_cash_flow_forecast(
    user_id: str,
    forecast_days: int = Query(30, ge=7, le=90),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Predictive 30-day cash flow forecast with seasonality."""
    if settings.ENVIRONMENT == "production":
        if current_user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif user_id != current_user_id and not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Forbidden")

    from services.forecasting import forecast_cash_flow
    return await forecast_cash_flow(db, user_id, forecast_days)


@router.get("/cash-flow/forecast")
async def get_current_user_cash_flow_forecast(
    forecast_days: int = Query(30, ge=7, le=90),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Predictive cash flow forecast for the authenticated user."""
    from services.forecasting import forecast_cash_flow
    return await forecast_cash_flow(db, current_user_id, forecast_days)


@router.get("/cash-flow/{user_id}")
async def get_cash_flow(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """7-day and 30-day cash flow + 7-day forecast."""
    if settings.ENVIRONMENT == "production":
        if current_user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif user_id != current_user_id and not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Forbidden")

    service = AnalyticsService(db)
    return await service.get_cash_flow(user_id)


@router.get("/cash-flow")
async def get_current_user_cash_flow(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Cash flow data for the authenticated user."""
    service = AnalyticsService(db)
    return await service.get_cash_flow(current_user_id)


@router.get("/summary/{user_id}")
async def get_summary(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Dashboard summary — all KPIs in one call."""
    if settings.ENVIRONMENT == "production":
        if current_user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif user_id != current_user_id and not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Forbidden")

    service = AnalyticsService(db)
    return await service.get_dashboard_summary(user_id)


@router.get("/summary")
async def get_current_user_summary(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Dashboard summary for the authenticated user."""
    service = AnalyticsService(db)
    return await service.get_dashboard_summary(current_user_id)


@router.get("/benchmarks/{user_id}")
async def get_benchmarks(
    user_id: str,
    period_days: int = Query(30, ge=7, le=365),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Peer cohort benchmarking comparison."""
    if settings.ENVIRONMENT == "production":
        if current_user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif user_id != current_user_id and not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Forbidden")

    from services.benchmarking import get_peer_benchmarks
    return await get_peer_benchmarks(db, user_id, period_days)


@router.get("/benchmarks")
async def get_current_user_benchmarks(
    period_days: int = Query(30, ge=7, le=365),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Peer cohort benchmarking for the authenticated user."""
    from services.benchmarking import get_peer_benchmarks
    return await get_peer_benchmarks(db, current_user_id, period_days)
