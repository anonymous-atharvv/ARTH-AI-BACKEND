# backend/routes/transactions.py
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional
import redis.asyncio as aioredis

from database import get_db
from models.transaction import Transaction
from schemas.transaction import TransactionCreate, TransactionResponse
from middleware.auth import get_current_user_id
from config import settings
from services.analytics import AnalyticsService

router = APIRouter()

async def get_redis():
    return await aioredis.from_url(settings.REDIS_URL)


@router.get("/{user_id}")
async def list_transactions(
    user_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, le=200),
    type: Optional[str] = None,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List transactions for a user (paginated)."""
    if user_id != current_user_id and not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Forbidden")

    query = select(Transaction).where(Transaction.user_id == user_id)

    if type:
        query = query.where(Transaction.type == type)

    # Count total
    count_query = select(func.count()).select_from(
        query.subquery()
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch page
    query = query.order_by(desc(Transaction.transaction_date)).offset(
        (page - 1) * limit
    ).limit(limit)

    result = await db.execute(query)
    txs = result.scalars().all()

    return {
        "items": [TransactionResponse.model_validate(tx) for tx in txs],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
    }


@router.post("/{user_id}", response_model=TransactionResponse)
async def create_transaction(
    user_id: str,
    tx_data: TransactionCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Manually add a transaction."""
    if user_id != current_user_id and not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Forbidden")

    tx = Transaction(
        user_id=user_id,
        amount=tx_data.amount,
        type=tx_data.type.value if hasattr(tx_data.type, 'value') else tx_data.type,
        category_code=tx_data.category_code,
        counterparty=tx_data.counterparty,
        description=tx_data.description,
        payment_method=tx_data.payment_method.value if hasattr(tx_data.payment_method, 'value') else tx_data.payment_method,
        transaction_date=tx_data.transaction_date,
        source=tx_data.source.value if hasattr(tx_data.source, 'value') else tx_data.source,
        raw_input=tx_data.raw_input,
        confidence_score=tx_data.confidence_score or 1.0,
        verified=True,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)

    # Refresh analytics cache
    analytics = AnalyticsService(db)
    await analytics.refresh_cache(user_id)

    # Invalidate Redis cache for ArthScore
    try:
        redis = await get_redis()
        await redis.delete(f"arthscore:{user_id}")
    except Exception:
        pass

    return tx
