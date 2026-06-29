# backend/services/analytics.py
"""
Core financial calculation engine.
All P&L, cash flow, category aggregation, and forecasting.
Powers the dashboard and Financial Passport.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import date, timedelta, datetime
from typing import List, Dict
from collections import defaultdict
import structlog

from models.transaction import Transaction

logger = structlog.get_logger()


def _date_key(value) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_summary(self, user_id: str) -> dict:
        """Single endpoint for all dashboard KPIs."""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        result = await self.db.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= month_start.isoformat(),
            )
        )
        txs = result.scalars().all()

        mtd_income = sum(float(t.amount) for t in txs if t.type == "income")
        mtd_expenses = sum(float(t.amount) for t in txs if t.type == "expense")
        mtd_net = mtd_income - mtd_expenses

        week_start_key = week_start.isoformat()
        wtd_income = sum(
            float(t.amount) for t in txs
            if t.type == "income" and _date_key(t.transaction_date) >= week_start_key
        )
        wtd_expenses = sum(
            float(t.amount) for t in txs
            if t.type == "expense" and _date_key(t.transaction_date) >= week_start_key
        )

        days_active = len(set(_date_key(t.transaction_date) for t in txs))
        avg_daily_income = mtd_income / days_active if days_active > 0 else 0

        # Top categories
        income_by_cat = defaultdict(float)
        expense_by_cat = defaultdict(float)
        for t in txs:
            if t.type == "income":
                income_by_cat[t.category_code or "other_income"] += float(t.amount)
            elif t.type == "expense":
                expense_by_cat[t.category_code or "other_expense"] += float(t.amount)

        top_income_cat = max(income_by_cat, key=income_by_cat.get) if income_by_cat else None
        top_expense_cat = max(expense_by_cat, key=expense_by_cat.get) if expense_by_cat else None

        # Total all-time count
        count_result = await self.db.execute(
            select(func.count()).select_from(Transaction).where(Transaction.user_id == user_id)
        )
        total_tx_count = count_result.scalar() or 0

        return {
            "mtd_income": round(mtd_income, 2),
            "mtd_expenses": round(mtd_expenses, 2),
            "mtd_net_profit": round(mtd_net, 2),
            "mtd_margin_pct": round(mtd_net / mtd_income * 100, 1) if mtd_income else 0,
            "wtd_income": round(wtd_income, 2),
            "wtd_expenses": round(wtd_expenses, 2),
            "wtd_net": round(wtd_income - wtd_expenses, 2),
            "avg_daily_income": round(avg_daily_income, 0),
            "days_active_mtd": days_active,
            "top_income_category": top_income_cat,
            "top_expense_category": top_expense_cat,
            "income_by_category": dict(income_by_cat),
            "expense_by_category": dict(expense_by_cat),
            "total_transactions": total_tx_count,
        }

    async def get_pnl_data(self, user_id: str, period: str) -> dict:
        """P&L time series for chart rendering."""
        period_map = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
        days = period_map.get(period, 90)
        cutoff = date.today() - timedelta(days=days)

        result = await self.db.execute(
            select(Transaction).where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.transaction_date >= cutoff.isoformat(),
                )
            ).order_by(Transaction.transaction_date)
        )
        txs = result.scalars().all()

        if period in ("7d", "30d"):
            series = self._group_by_day(txs, days)
        elif period == "90d":
            series = self._group_by_week(txs, 13)
        else:
            series = self._group_by_month(txs, 12)

        total_income = sum(float(t.amount) for t in txs if t.type == "income")
        total_expenses = sum(float(t.amount) for t in txs if t.type == "expense")
        net_profit = total_income - total_expenses

        income_cats = defaultdict(float)
        expense_cats = defaultdict(float)
        for t in txs:
            if t.type == "income":
                income_cats[t.category_code or "other_income"] += float(t.amount)
            else:
                expense_cats[t.category_code or "other_expense"] += float(t.amount)

        return {
            "period": period,
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "net_profit": round(net_profit, 2),
            "net_margin_pct": round(net_profit / total_income * 100, 1) if total_income else 0,
            "series": series,
            "top_income_categories": sorted(
                [{"code": k, "amount": v} for k, v in income_cats.items()],
                key=lambda x: x["amount"], reverse=True,
            )[:5],
            "top_expense_categories": sorted(
                [{"code": k, "amount": v} for k, v in expense_cats.items()],
                key=lambda x: x["amount"], reverse=True,
            )[:5],
        }

    async def get_cash_flow(self, user_id: str) -> dict:
        """Last 30 days cash flow + 7-day simple forecast."""
        cutoff = date.today() - timedelta(days=30)

        result = await self.db.execute(
            select(Transaction).where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.transaction_date >= cutoff.isoformat(),
                )
            ).order_by(Transaction.transaction_date)
        )
        txs = result.scalars().all()

        daily_net = defaultdict(float)
        for t in txs:
            sign = 1 if t.type == "income" else -1
            daily_net[_date_key(t.transaction_date)] += sign * float(t.amount)

        history = []
        for i in range(30, 0, -1):
            d = date.today() - timedelta(days=i)
            history.append({
                "date": d.isoformat(),
                "label": d.strftime("%b %d"),
                "net": round(daily_net.get(d.isoformat(), 0), 0),
                "cumulative": 0,
            })

        running = 0
        for h in history:
            running += h["net"]
            h["cumulative"] = round(running, 0)

        # Simple forecast
        forecast = []
        avg_daily = sum(h["net"] for h in history) / 30 if history else 0
        for i in range(1, 8):
            future_date = date.today() + timedelta(days=i)
            forecast.append({
                "date": future_date.isoformat(),
                "label": future_date.strftime("%b %d"),
                "forecast_net": round(avg_daily, 0),
                "is_forecast": True,
            })

        return {
            "history": history,
            "forecast": forecast,
            "avg_daily_net_30d": round(avg_daily, 0),
            "projected_weekly_net": round(avg_daily * 7, 0),
        }

    def _group_by_day(self, txs, days: int) -> List[dict]:
        daily = defaultdict(lambda: {"income": 0.0, "expenses": 0.0})
        for t in txs:
            key = t.transaction_date if isinstance(t.transaction_date, str) else t.transaction_date.isoformat()
            if t.type == "income":
                daily[key]["income"] += float(t.amount)
            else:
                daily[key]["expenses"] += float(t.amount)

        series = []
        for i in range(days, 0, -1):
            d = date.today() - timedelta(days=i)
            key = d.isoformat()
            inc = daily[key]["income"]
            exp = daily[key]["expenses"]
            series.append({
                "period_label": d.strftime("%b %d"),
                "income": round(inc, 0),
                "expenses": round(exp, 0),
                "net": round(inc - exp, 0),
            })
        return series

    def _group_by_week(self, txs, num_weeks: int) -> List[dict]:
        weekly = defaultdict(lambda: {"income": 0.0, "expenses": 0.0})
        for t in txs:
            tx_date_str = _date_key(t.transaction_date)
            tx_date = date.fromisoformat(tx_date_str)
            days_ago = (date.today() - tx_date).days
            week_num = days_ago // 7
            bucket = "income" if t.type == "income" else "expenses"
            weekly[week_num][bucket] += float(t.amount)

        series = []
        for w in range(num_weeks, 0, -1):
            inc = weekly[w]["income"]
            exp = weekly[w]["expenses"]
            week_start = date.today() - timedelta(days=w * 7 + 7)
            series.append({
                "period_label": f"W {week_start.strftime('%b %d')}",
                "income": round(inc, 0),
                "expenses": round(exp, 0),
                "net": round(inc - exp, 0),
            })
        return series

    def _group_by_month(self, txs, num_months: int) -> List[dict]:
        monthly = defaultdict(lambda: {"income": 0.0, "expenses": 0.0})
        for t in txs:
            tx_date_str = _date_key(t.transaction_date)
            key = tx_date_str[:7]  # "YYYY-MM"
            bucket = "income" if t.type == "income" else "expenses"
            monthly[key][bucket] += float(t.amount)

        series = []
        today = date.today()
        for m in range(num_months, 0, -1):
            month_date = date(today.year, today.month, 1) - timedelta(days=m * 28)
            key = month_date.strftime("%Y-%m")
            inc = monthly[key]["income"]
            exp = monthly[key]["expenses"]
            series.append({
                "period_label": month_date.strftime("%b '%y"),
                "income": round(inc, 0),
                "expenses": round(exp, 0),
                "net": round(inc - exp, 0),
            })
        return series

    async def refresh_cache(self, user_id: str):
        """Update analytics_cache after each transaction — SQLite + PostgreSQL safe."""
        try:
            from models.analytics import AnalyticsCache
            
            summary = await self.get_dashboard_summary(user_id)
            
            # Check if cache row exists
            result = await self.db.execute(
                select(AnalyticsCache).where(AnalyticsCache.user_id == user_id)
            )
            cache = result.scalar_one_or_none()
            
            if cache:
                cache.mtd_income = summary["mtd_income"]
                cache.mtd_expenses = summary["mtd_expenses"]
                cache.mtd_net_profit = summary["mtd_net_profit"]
                cache.wtd_income = summary["wtd_income"]
                cache.wtd_expenses = summary["wtd_expenses"]
                cache.total_transactions = summary["total_transactions"]
                cache.last_updated = datetime.utcnow().isoformat()
            else:
                cache = AnalyticsCache(
                    user_id=user_id,
                    mtd_income=summary["mtd_income"],
                    mtd_expenses=summary["mtd_expenses"],
                    mtd_net_profit=summary["mtd_net_profit"],
                    wtd_income=summary["wtd_income"],
                    wtd_expenses=summary["wtd_expenses"],
                    total_transactions=summary["total_transactions"],
                )
                self.db.add(cache)
            
            await self.db.commit()
        except Exception as e:
            logger.error("Analytics cache refresh failed", error=str(e))
            # Non-fatal — don't crash the transaction flow
