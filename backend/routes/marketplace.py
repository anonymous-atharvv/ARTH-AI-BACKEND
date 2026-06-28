# backend/routes/marketplace.py
"""
Simulated NBFC loan marketplace for demo purposes.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from agents.arthascore import ArthScoreEngine

router = APIRouter()

NBFC_PARTNERS = [
    {
        "name": "FinFlex Capital", "min_score": 650, "max_loan": 200000,
        "interest_rate_pct": 18, "tenure_months": [6, 12, 24],
        "processing_fee_pct": 1.5, "tagline": "No collateral required",
        "turnaround_hours": 48, "logo": "🏦"
    },
    {
        "name": "MSME Credit Pro", "min_score": 600, "max_loan": 100000,
        "interest_rate_pct": 22, "tenure_months": [3, 6, 12],
        "processing_fee_pct": 2.0, "tagline": "Disbursed in 24 hours",
        "turnaround_hours": 24, "logo": "💳"
    },
    {
        "name": "BharatMicro Finance", "min_score": 550, "max_loan": 50000,
        "interest_rate_pct": 26, "tenure_months": [3, 6],
        "processing_fee_pct": 2.5, "tagline": "Flexible repayment",
        "turnaround_hours": 72, "logo": "🏛️"
    },
]


@router.get("/offers/{user_id}")
async def get_loan_offers(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get personalized loan offers based on ArthScore."""
    scorer = ArthScoreEngine(db)
    score_data = await scorer.calculate(user_id)
    score = score_data["score"]
    max_eligible = score_data["max_loan_eligible"]

    eligible_offers = []
    for nbfc in NBFC_PARTNERS:
        if score >= nbfc["min_score"]:
            loan_amount = min(max_eligible, nbfc["max_loan"])
            monthly_rate = nbfc["interest_rate_pct"] / 12 / 100
            n = nbfc["tenure_months"][0]
            if monthly_rate > 0:
                emi = loan_amount * monthly_rate * (1 + monthly_rate) ** n / (
                    (1 + monthly_rate) ** n - 1
                )
            else:
                emi = loan_amount / n

            eligible_offers.append({
                **nbfc,
                "loan_amount": loan_amount,
                "emi_per_month": round(emi),
                "total_interest": round(emi * n - loan_amount),
                "eligible": True,
                "your_arthascore": score,
            })

    eligible_offers.sort(key=lambda x: x["interest_rate_pct"])

    return {
        "arthascore": score,
        "grade": score_data["grade"],
        "total_offers": len(eligible_offers),
        "offers": eligible_offers,
        "comparison": {
            "formal_rate": eligible_offers[0]["interest_rate_pct"] if eligible_offers else None,
            "moneylender_rate": 48,
            "annual_savings": round(
                max_eligible * (0.48 - (eligible_offers[0]["interest_rate_pct"] / 100))
            ) if eligible_offers else 0,
        },
    }
