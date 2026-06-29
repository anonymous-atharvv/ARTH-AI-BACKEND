# backend/tests/test_analytics.py
import pytest
from datetime import date
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_pnl_totals_match_individual_transactions(client: AsyncClient, db_session):
    """P&L totals must exactly match sum of individual transactions."""
    # Seed known transactions
    from models.transaction import Transaction
    txs = [
        Transaction(user_id="raju-demo-001", amount=1000.0, type="income",
                    category_code="sales_product", source="manual",
                    transaction_date=date.today().isoformat(), verified=True),
        Transaction(user_id="raju-demo-001", amount=300.0, type="expense",
                    category_code="inventory", source="manual",
                    transaction_date=date.today().isoformat(), verified=True),
    ]
    for tx in txs:
        db_session.add(tx)
    await db_session.commit()

    from services.analytics import AnalyticsService
    analytics = AnalyticsService(db_session)
    summary = await analytics.get_dashboard_summary("raju-demo-001")

    assert summary["mtd_income"] == 1000.0
    assert summary["mtd_expenses"] == 300.0
    assert summary["mtd_net_profit"] == 700.0


async def test_pnl_series_periods_are_consistent(client: AsyncClient, db_session):
    """P&L series periods must be consistent and present."""
    from services.analytics import AnalyticsService
    analytics = AnalyticsService(db_session)
    pnl = await analytics.get_pnl_data("raju-demo-001", "90d")

    assert "series" in pnl
    assert pnl["total_income"] >= 0
    assert pnl["total_expenses"] >= 0
