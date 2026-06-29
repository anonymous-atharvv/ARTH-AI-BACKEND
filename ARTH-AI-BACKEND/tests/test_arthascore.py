# backend/tests/test_arthascore.py
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

pytestmark = pytest.mark.asyncio

class TestArthScoreEngine:
    async def test_score_range_300_to_900(self, db_session):
        """ArthScore must always be between 300-900."""
        from agents.arthascore import ArthScoreEngine
        engine = ArthScoreEngine(db_session)

        # Mock 30 transactions
        mock_txs = [
            MagicMock(
                type="income", amount=1000.0,
                transaction_date="2026-01-01",
                verified=True
            ) for _ in range(30)
        ]

        with patch.object(db_session, 'execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value.scalars.return_value.all.return_value = mock_txs
            result = await engine.calculate("test-user-id", lookback_days=90)

        assert 300 <= result["score"] <= 900
        assert result["grade"] in ("Excellent", "Good", "Fair", "Needs Improvement")
        assert result["max_loan_eligible"] >= 0

    async def test_insufficient_data_returns_zero_score(self, db_session):
        """Under 5 transactions returns score=0, not an exception."""
        from agents.arthascore import ArthScoreEngine
        engine = ArthScoreEngine(db_session)

        with patch.object(db_session, 'execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value.scalars.return_value.all.return_value = []
            result = await engine.calculate("test-user-id", lookback_days=90)

        assert result["score"] == 0
        assert result["data_points"] == 0

    async def test_all_factors_within_0_100(self, db_session):
        """All score factors must be integers between 0 and 100."""
        from agents.arthascore import ArthScoreEngine
        engine = ArthScoreEngine(db_session)

        mock_txs = [
            MagicMock(type=t, amount=500.0, transaction_date="2026-01-01", verified=True)
            for t in (["income"] * 20 + ["expense"] * 10)
        ]

        with patch.object(db_session, 'execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value.scalars.return_value.all.return_value = mock_txs
            result = await engine.calculate("test-user-id", lookback_days=90)

        for factor_name, factor_value in result["factors"].items():
            assert 0 <= factor_value <= 100, \
                f"Factor '{factor_name}' = {factor_value} is outside 0-100 range"
