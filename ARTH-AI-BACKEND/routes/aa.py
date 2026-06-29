# backend/routes/aa.py
"""Endpoints for the Account Aggregator flow."""
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from database import get_db
from middleware.auth import get_current_user_id
from services.account_aggregator import AccountAggregatorService
from models.user import User

router = APIRouter()
logger = structlog.get_logger()

@router.post("/consent/initiate/{user_id}")
async def initiate_aa_consent(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Initiate Account Aggregator consent flow."""
    # Strict multi-tenancy verification
    if current_user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    service = AccountAggregatorService()
    consent_data = await service.initiate_consent(user_id, user.phone_number)
    
    consent_handle = consent_data.get("consent_handle")
    if consent_handle:
        from cache import get_redis
        try:
            redis = await get_redis()
            await redis.set(f"aa_consent:{consent_handle}", user_id, ex=86400)
        except Exception as redis_err:
            logger.error("Failed to store consent handle in Redis", error=str(redis_err))

    return consent_data


@router.post("/consent/callback")
async def aa_consent_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Called by AA when user approves/rejects consent."""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
        
    consent_handle = data.get("ConsentHandle") or data.get("consent_handle")
    status = data.get("status", "ACTIVE")  # "ACTIVE" or "REJECTED"

    logger.info("Received AA consent callback", consent_handle=consent_handle, status=status)

    if status == "ACTIVE" and consent_handle:
        from cache import get_redis
        try:
            redis = await get_redis()
            user_id = await redis.get(f"aa_consent:{consent_handle}")
        except Exception as redis_err:
            logger.error("Failed to retrieve consent handle from Redis", error=str(redis_err))
            user_id = None

        if not user_id:
            logger.warning("Consent handle not found or expired in Redis", consent_handle=consent_handle)
            raise HTTPException(status_code=404, detail="Consent request not found or expired")

        # Trigger background task to fetch and import transactions
        from tasks.aa_tasks import fetch_and_import_aa_data
        fetch_and_import_aa_data.delay(consent_handle, user_id)

    return {"status": "acknowledged"}
