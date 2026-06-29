# backend/agents/passport_generator.py
"""Generates bank-grade Financial Passport as real PDF using WeasyPrint."""
from jinja2 import Template
from datetime import date, timedelta
from pathlib import Path
import uuid, os, structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from agents.arthascore import ArthScoreEngine
from services.analytics import AnalyticsService
from services.storage import StorageService

logger = structlog.get_logger()

PASSPORT_HTML = Path(__file__).parent.parent / "templates" / "passport.html"


class PassportGenerator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate(self, user_id: str, lookback_days: int = 90) -> dict:
        from models.user import User
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        scorer = ArthScoreEngine(self.db)
        score_data = await scorer.calculate(user_id, lookback_days=lookback_days)

        analytics = AnalyticsService(self.db)
        pnl = await analytics.get_pnl_data(user_id, f"{lookback_days}d")

        doc_id = f"AP-{user_id[:8].upper()}-{date.today().strftime('%Y%m%d')}"
        data = self._build_template_data(user, score_data, pnl, doc_id, lookback_days)

        # Render HTML
        template_src = PASSPORT_HTML.read_text(encoding="utf-8")
        html_content = Template(template_src).render(**data)

        # Attempt PDF with WeasyPrint; fall back to HTML if system deps missing
        pdf_bytes, file_ext, content_type = self._render_pdf(html_content)

        # Upload to storage
        storage = StorageService()
        file_key = f"passports/{user_id}/{date.today().isoformat()}/passport.{file_ext}"
        download_url = await storage.upload_file(pdf_bytes, file_key, content_type)

        # Log document
        await self._log_document(user_id, download_url, score_data)

        return {
            "download_url": download_url,
            "arthascore": score_data.get("score", 0),
            "loan_eligible": score_data.get("max_loan_eligible", 0),
            "expires_at": (date.today() + timedelta(days=7)).isoformat(),
            "doc_id": doc_id,
            "format": file_ext,
        }

    def _render_pdf(self, html_content: str):
        """Try WeasyPrint → fallback to HTML bytes."""
        try:
            from weasyprint import HTML as WeasyHTML
            pdf_bytes = WeasyHTML(string=html_content).write_pdf()
            logger.info("PDF rendered successfully", size_kb=len(pdf_bytes) // 1024)
            return pdf_bytes, "pdf", "application/pdf"
        except Exception as e:
            logger.warning("WeasyPrint unavailable, falling back to HTML", error=str(e))
            html_bytes = html_content.encode("utf-8")
            return html_bytes, "html", "text/html; charset=utf-8"

    def _build_template_data(self, user, score_data, pnl, doc_id, lookback_days: int = 90) -> dict:
        period_days = score_data.get("period_days") or lookback_days
        months_divisor = max(1.0, period_days / 30.0)

        return {
            "doc_id": doc_id,
            "generated_date": date.today().strftime("%d %B %Y"),
            "expiry_date": (date.today() + timedelta(days=7)).strftime("%d %B %Y"),
            "score": score_data.get("score", 0),
            "grade": score_data.get("grade", "N/A"),
            "grade_hi": score_data.get("grade_hi", "N/A"),
            "factors": {
                "Income Regularity": score_data.get("factors", {}).get("income_regularity", 0),
                "Growth Trend": score_data.get("factors", {}).get("growth_trajectory", 0),
                "Expense Control": score_data.get("factors", {}).get("expense_control", 0),
                "Business Activity": score_data.get("factors", {}).get("transaction_volume", 0),
                "Business Age": score_data.get("factors", {}).get("business_longevity", 0),
                "Payment Habit": score_data.get("factors", {}).get("payment_consistency", 0),
            },
            "max_loan": score_data.get("max_loan_eligible", 0),
            "name": getattr(user, "name", None) or "Business Owner",
            "business_type": getattr(user, "business_type", None) or "Micro Business",
            "location": getattr(user, "business_location", None) or "India",
            "total_income": pnl.get("total_income", 0),
            "total_expenses": pnl.get("total_expenses", 0),
            "net_profit": pnl.get("net_profit", 0),
            "avg_monthly_income": pnl.get("total_income", 0) / months_divisor,
            "net_margin_pct": round(pnl.get("net_margin_pct", 0), 1),
            "payment_regularity": score_data.get("factors", {}).get("payment_consistency", 70),
            "monthly_data": pnl.get("series", [])[:6],
        }
    async def _log_document(self, user_id: str, download_url: str, score_data: dict):
        from models.document import Document
        from datetime import timedelta
        doc = Document(
            user_id=user_id,
            document_type="financial_passport",
            file_url=download_url,
            period_start=date.today().replace(day=1).isoformat(),
            period_end=date.today().isoformat(),
            arthascore_at_generation=score_data.get("score", 0),
            summary_data={"score": score_data.get("score"), "loan_eligible": score_data.get("max_loan_eligible")},
            expires_at=(date.today() + timedelta(days=7)).isoformat(),
        )
        self.db.add(doc)
        await self.db.commit()
