# backend/routes/reports.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user_id
from config import settings

router = APIRouter()


@router.post("/passport/{user_id}")
async def generate_financial_passport(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates a bank-grade Financial Passport PDF.
    Returns download URL + ArthScore + loan eligibility.
    """
    if user_id != current_user_id and not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Forbidden")

    from agents.passport_generator import PassportGenerator

    generator = PassportGenerator(db)
    result = await generator.generate(user_id)
    return result


@router.post("/gst-invoice/{user_id}/{transaction_id}")
async def generate_gst_invoice(
    user_id: str,
    transaction_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates a GST-compliant tax invoice for a transaction.
    """
    if user_id != current_user_id and not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Forbidden")

    from agents.gst_invoice_generator import GSTInvoiceGenerator
    generator = GSTInvoiceGenerator(db)
    result = await generator.generate(user_id, transaction_id)
    return result
