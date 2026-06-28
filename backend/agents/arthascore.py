# backend/agents/arthascore.py
"""
ArthScore: Proprietary creditworthiness score for informal economy.
Scale: 300-900 (mirrors CIBIL). MVP: 7 factors.
"""
import numpy as np
from datetime import date, timedelta
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

logger = structlog.get_logger()

FACTOR_WEIGHTS = {
    "income_regularity": 0.25, "growth_trajectory": 0.20,
    "expense_control": 0.15, "transaction_volume": 0.15,
    "business_longevity": 0.10, "payment_consistency": 0.10,
    "data_completeness": 0.05,
}


class ArthScoreEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate(self, user_id: str, lookback_days: int = 90) -> Dict:
        from models.transaction import Transaction
        cutoff = (date.today() - timedelta(days=lookback_days)).isoformat()
        result = await self.db.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= cutoff,
                Transaction.verified == True,
            ).order_by(Transaction.transaction_date)
        )
        txs = result.scalars().all()
        if len(txs) < 5:
            return self._no_data()

        inc_tx = [t for t in txs if t.type == "income"]
        exp_tx = [t for t in txs if t.type == "expense"]
        w_inc = self._weeks(inc_tx, lookback_days)

        total_inc = sum(float(t.amount) for t in inc_tx)
        total_exp = sum(float(t.amount) for t in exp_tx)

        dates = [date.fromisoformat(t.transaction_date) if isinstance(t.transaction_date, str) else t.transaction_date for t in txs]

        f = {
            "income_regularity": self._cv(w_inc),
            "growth_trajectory": self._growth(w_inc),
            "expense_control": max(0, int(min(100, ((total_inc - total_exp) / max(1, total_inc)) * 200))),
            "transaction_volume": max(0, int(min(100, (len(txs) / lookback_days / 0.67) * 80))),
            "business_longevity": min(100, int((date.today() - min(dates)).days / 365 * 100)),
            "payment_consistency": self._pay_cons(exp_tx, lookback_days),
            "data_completeness": int(min(100, len(set(t.transaction_date for t in txs)) / max(1, lookback_days * 6 / 7) * 100)),
        }

        ws = sum(f[k] * FACTOR_WEIGHTS[k] for k in FACTOR_WEIGHTS)
        score = max(300, min(900, int(300 + ws / 100 * 600)))
        grade, grade_hi = self._grade(score)
        mn = (total_inc - total_exp) / max(1, lookback_days / 30)
        ml = min(500000, round(max(0, mn * 4) / 1000) * 1000)

        return {
            "score": score, "grade": grade, "grade_hi": grade_hi, "factors": f,
            "max_loan_eligible": ml, "data_points": len(txs), "period_days": lookback_days,
            "insight_hi": f"ArthScore {score}/900 — {grade_hi}! Monthly net: ₹{mn:,.0f}.",
            "insight_en": f"ArthScore {score}/900 — {grade}! Monthly net: ₹{mn:,.0f}.",
            "calculated_at": date.today().isoformat(),
        }

    def _weeks(self, txs, days):
        n = days // 7
        w = [0.0] * n
        for t in txs:
            d = date.fromisoformat(t.transaction_date) if isinstance(t.transaction_date, str) else t.transaction_date
            i = (date.today() - d).days // 7
            if 0 <= i < n: w[n - 1 - i] += float(t.amount)
        return w

    def _cv(self, w):
        a = [x for x in w if x > 0]
        if len(a) < 2: return 50
        return max(0, int(100 * (1 - min(float(np.std(a) / np.mean(a)), 1.0))))

    def _growth(self, w):
        if len(w) < 3: return 50
        from sklearn.linear_model import LinearRegression
        X = np.arange(len(w)).reshape(-1, 1)
        m = LinearRegression().fit(X, np.array(w))
        avg = np.mean([x for x in w if x > 0]) or 1
        return max(0, min(100, int(50 + m.coef_[0] / avg * 250)))

    def _pay_cons(self, txs, days):
        if not txs: return 70
        ws = set()
        for t in txs:
            d = date.fromisoformat(t.transaction_date) if isinstance(t.transaction_date, str) else t.transaction_date
            ws.add((date.today() - d).days // 7)
        return int(len(ws) / max(1, days // 7) * 100)

    def _grade(self, s):
        if s >= 750: return "Excellent", "उत्कृष्ट"
        if s >= 650: return "Good", "अच्छा"
        if s >= 550: return "Fair", "ठीक-ठाक"
        return "Needs Improvement", "सुधार आवश्यक"

    def _no_data(self):
        return {"score": 0, "grade": "Insufficient Data", "grade_hi": "अपर्याप्त डेटा",
                "factors": {}, "max_loan_eligible": 0, "data_points": 0, "period_days": 0,
                "calculated_at": date.today().isoformat(),
                "insight_hi": "Kam se kam 5 transactions chahiye.", "insight_en": "Need 5+ transactions."}
