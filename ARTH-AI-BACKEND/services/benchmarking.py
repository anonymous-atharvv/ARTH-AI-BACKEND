# backend/services/benchmarking.py
"""
Provides merchant peer comparison without exposing individual user data.
Uses anonymized aggregates across same business_type + location bucket.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models.transaction import Transaction
from models.user import User
from config import settings
import structlog

logger = structlog.get_logger()

async def get_peer_benchmarks(db: AsyncSession, user_id: str, period_days: int = 30) -> dict:
    """
    Compare user metrics against anonymous peer cohort.
    Returns percentile rankings and category-level comparisons.
    """
    from datetime import date, timedelta
    from services.analytics import AnalyticsService

    cutoff = (date.today() - timedelta(days=period_days)).isoformat()

    # Get user's business type and location
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.business_type:
        return {"available": False, "reason": "Business type not set"}

    # Get user's own metrics
    analytics = AnalyticsService(db)
    user_summary = await analytics.get_dashboard_summary(user_id)
    user_income = user_summary.get("mtd_income", 0)

    # Detect database engine dialect to avoid executing pg-specific functions on SQLite
    dialect_name = db.bind.dialect.name if db.bind else "sqlite"

    if dialect_name == "sqlite":
        # SQLite dialect: fetch raw transaction amounts and compute median / count in Python
        peer_txs_result = await db.execute(
            select(Transaction.amount, Transaction.user_id)
            .join(User, User.id == Transaction.user_id)
            .where(
                Transaction.type == "income",
                Transaction.transaction_date >= cutoff,
                User.business_type == user.business_type,
                User.id != user_id
            )
        )
        rows = peer_txs_result.all()
        peer_amounts = [float(row[0]) for row in rows]
        peer_user_ids = {row[1] for row in rows}
        peer_count = len(peer_user_ids)

        # Relax peer count restriction for DEMO/development/local environments
        if peer_count < 5 and settings.DEMO_MODE:
            peer_count = 6
            peer_amounts = [20000.0, 22000.0, 24000.0, 26000.0, 28000.0, 30000.0]

        if peer_count < 5:
            return {"available": False, "reason": "Insufficient peer data (need 5+ similar businesses)"}

        peer_avg = sum(peer_amounts) / len(peer_amounts) if peer_amounts else 0
        sorted_amounts = sorted(peer_amounts)
        n = len(sorted_amounts)
        median_income = sorted_amounts[n // 2] if n % 2 == 1 else (sorted_amounts[n // 2 - 1] + sorted_amounts[n // 2]) / 2 if n > 0 else 0
    else:
        # PostgreSQL dialect: use native percentile_cont aggregate functions
        peer_income_result = await db.execute(
            select(
                func.avg(Transaction.amount).label("avg_income"),
                func.percentile_cont(0.5).within_group(Transaction.amount).label("median_income"),
                func.count(func.distinct(Transaction.user_id)).label("peer_count"),
            )
            .join(User, User.id == Transaction.user_id)
            .where(
                Transaction.type == "income",
                Transaction.transaction_date >= cutoff,
                User.business_type == user.business_type,
                User.id != user_id,
            )
        )
        peer_data = peer_income_result.fetchone()

        peer_count = int(peer_data.peer_count) if peer_data and peer_data.peer_count is not None else 0

        # Relax peer count restriction for DEMO/development/local environments
        if peer_count < 5 and settings.DEMO_MODE:
            peer_count = 6
            peer_avg = 25000.0
            median_income = 25000.0
        elif peer_count < 5:
            return {"available": False, "reason": "Insufficient peer data (need 5+ similar businesses)"}
        else:
            peer_avg = float(peer_data.avg_income or 0)
            median_income = float(peer_data.median_income or 0)

    pct_vs_peers = ((user_income - peer_avg) / peer_avg * 100) if peer_avg > 0 else 0

    return {
        "available": True,
        "business_type": user.business_type,
        "period_days": period_days,
        "peer_count": peer_count,
        "user_income": user_income,
        "peer_avg_income": round(peer_avg, 0),
        "median_income": round(median_income, 0),
        "percentile_vs_peers": round(pct_vs_peers, 1),
        "insight_en": f"Your income is {abs(pct_vs_peers):.0f}% {'above' if pct_vs_peers >= 0 else 'below'} similar {user.business_type} businesses this month.",
        "insight_hi": f"Aapki income is mahine {user.business_type} se {'zyada' if pct_vs_peers >= 0 else 'kam'} ({abs(pct_vs_peers):.0f}%) rahi.",
    }
