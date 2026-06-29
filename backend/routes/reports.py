from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user_id
from middleware.rate_limit import limiter
from config import settings

router = APIRouter()


@router.post("/passport/{user_id}")
@limiter.limit("3/hour")
async def generate_financial_passport(
    request: Request,
    user_id: str,
    lookback_days: int = Query(90, ge=7, le=365),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates a bank-grade Financial Passport PDF.
    Returns download URL + ArthScore + loan eligibility.
    """
    if settings.ENVIRONMENT == "production":
        if current_user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif user_id != current_user_id and not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Forbidden")

    from agents.passport_generator import PassportGenerator

    generator = PassportGenerator(db)
    result = await generator.generate(user_id, lookback_days=lookback_days)

    from services.audit import log_audit_event
    await log_audit_event(
        db,
        action="generate_passport",
        user_id=user_id,
        request=request,
        details={"lookback_days": lookback_days, "doc_id": result.get("doc_id")}
    )
    return result


@router.post("/gst-invoice/{user_id}/{transaction_id}")
async def generate_gst_invoice(
    request: Request,
    user_id: str,
    transaction_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates a GST-compliant tax invoice for a transaction.
    """
    if settings.ENVIRONMENT == "production":
        if current_user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif user_id != current_user_id and not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Forbidden")

    from agents.gst_invoice_generator import GSTInvoiceGenerator
    generator = GSTInvoiceGenerator(db)
    result = await generator.generate(user_id, transaction_id)

    from services.audit import log_audit_event
    await log_audit_event(
        db,
        action="generate_gst_invoice",
        user_id=user_id,
        request=request,
        details={"transaction_id": transaction_id}
    )
    return result


@router.get("/gst-report/{user_id}")
async def get_gstr1_report(
    request: Request,
    user_id: str,
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Generates a GSTR-1 compliant monthly sales tax summary.
    """
    if settings.ENVIRONMENT == "production":
        if current_user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif user_id != current_user_id and not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Forbidden")

    from services.gst_compliance import generate_gstr1_data
    result = await generate_gstr1_data(db, user_id, year, month)

    from services.audit import log_audit_event
    await log_audit_event(
        db,
        action="generate_gstr1_report",
        user_id=user_id,
        request=request,
        details={"year": year, "month": month}
    )
    return result

