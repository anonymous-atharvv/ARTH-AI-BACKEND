# backend/agents/passport_generator.py
"""
Generates bank-grade Financial Passport PDF.
Uses Jinja2 HTML template rendered to PDF (or saved as HTML for demo).
"""
from jinja2 import Template
from datetime import date, timedelta
from pathlib import Path
import uuid, os, structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from agents.arthascore import ArthScoreEngine
from services.analytics import AnalyticsService

logger = structlog.get_logger()

PASSPORT_HTML = Path(__file__).parent.parent / "templates" / "passport.html"


class PassportGenerator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate(self, user_id: str) -> dict:
        from models.user import User
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        scorer = ArthScoreEngine(self.db)
        score_data = await scorer.calculate(user_id, lookback_days=90)

        analytics = AnalyticsService(self.db)
        pnl = await analytics.get_pnl_data(user_id, "90d")

        doc_id = f"AP-{user_id[:8].upper()}-{date.today().strftime('%Y%m%d')}"

        data = {
            "doc_id": doc_id,
            "generated_date": date.today().strftime("%d %B %Y"),
            "expiry_date": (date.today() + timedelta(days=30)).strftime("%d %B %Y"),
            "score": score_data.get("score", 0),
            "grade": score_data.get("grade", "N/A"),
            "factors": {
                "Income Regularity": score_data.get("factors", {}).get("income_regularity", 0),
                "Growth Trend": score_data.get("factors", {}).get("growth_trajectory", 0),
                "Expense Control": score_data.get("factors", {}).get("expense_control", 0),
                "Business Activity": score_data.get("factors", {}).get("transaction_volume", 0),
                "Longevity": score_data.get("factors", {}).get("business_longevity", 0),
                "Payment Habit": score_data.get("factors", {}).get("payment_consistency", 0),
            },
            "max_loan": score_data.get("max_loan_eligible", 0),
            "name": getattr(user, "name", "Business Owner") or "Business Owner",
            "business_type": getattr(user, "business_type", "Micro Business") or "Micro Business",
            "location": getattr(user, "business_location", "India") or "India",
            "total_income": pnl.get("total_income", 0),
            "total_expenses": pnl.get("total_expenses", 0),
            "net_profit": pnl.get("net_profit", 0),
            "avg_monthly_income": pnl.get("total_income", 0) / 3,
            "net_margin_pct": pnl.get("net_margin_pct", 0),
            "payment_regularity": score_data.get("factors", {}).get("payment_consistency", 70),
            "monthly_data": pnl.get("series", [])[:6],
        }

        # Read and render template
        template_path = PASSPORT_HTML
        if template_path.exists():
            html = Template(template_path.read_text()).render(**data)
        else:
            html = f"<h1>ArthAI Financial Passport</h1><p>Score: {data['score']}/900</p>"

        # Save as HTML file (PDF requires weasyprint system deps)
        output_dir = Path(__file__).parent.parent / "static"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"passport_{user_id[:8]}.html"
        output_file.write_text(html)

        return {
            "download_url": f"/static/passport_{user_id[:8]}.html",
            "arthascore": score_data.get("score", 0),
            "loan_eligible": score_data.get("max_loan_eligible", 0),
            "expires_at": (date.today() + timedelta(days=30)).isoformat(),
        }
