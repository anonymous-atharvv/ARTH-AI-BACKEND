# backend/routes/reports.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db

router = APIRouter()


@router.post("/passport/{user_id}")
async def generate_financial_passport(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Generates a bank-grade Financial Passport PDF.
    Returns download URL + ArthScore + loan eligibility.
    """
    from agents.passport_generator import PassportGenerator

    generator = PassportGenerator(db)
    result = await generator.generate(user_id)
    return result
