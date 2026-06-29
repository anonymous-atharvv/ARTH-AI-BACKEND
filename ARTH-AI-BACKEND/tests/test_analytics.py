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


async def test_dashboard_summary_handles_date_objects(db_session):
    """Dashboard summary must handle ORM date values returned from PostgreSQL/SQLite."""
    from models.transaction import Transaction
    from services.analytics import AnalyticsService

    db_session.add(Transaction(
        user_id="date-user-001",
        amount=1250.0,
        type="income",
        category_code="sales_product",
        source="manual",
        transaction_date=date.today(),
        verified=True,
    ))
    await db_session.commit()

    analytics = AnalyticsService(db_session)
    summary = await analytics.get_dashboard_summary("date-user-001")

    assert summary["wtd_income"] == 1250.0
    assert summary["days_active_mtd"] == 1


async def test_current_user_transactions_alias(client: AsyncClient, db_session):
    """Collection endpoint should resolve to the authenticated user."""
    from middleware.auth import create_access_token
    from models.transaction import Transaction

    user_id = "alias-user-001"
    db_session.add(Transaction(
        user_id=user_id,
        amount=500.0,
        type="income",
        category_code="sales_service",
        source="manual",
        transaction_date=date.today(),
        verified=True,
    ))
    await db_session.commit()

    token = create_access_token(user_id, "+919999999999")
    response = await client.get(
        "/api/v1/transactions",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


async def test_pnl_series_periods_are_consistent(client: AsyncClient, db_session):
    """P&L series periods must be consistent and present."""
    from services.analytics import AnalyticsService
    analytics = AnalyticsService(db_session)
    pnl = await analytics.get_pnl_data("raju-demo-001", "90d")

    assert "series" in pnl
    assert pnl["total_income"] >= 0
    assert pnl["total_expenses"] >= 0
