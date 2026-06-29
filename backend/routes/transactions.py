# backend/routes/transactions.py
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional

from database import get_db
from models.transaction import Transaction
from schemas.transaction import TransactionCreate, TransactionResponse
from middleware.auth import get_current_user_id
from config import settings

router = APIRouter()


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
    if settings.ENVIRONMENT == "production":
        if current_user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif user_id != current_user_id and not settings.DEMO_MODE:
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


@router.get("")
@router.get("/")
async def list_current_user_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, le=200),
    type: Optional[str] = None,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List transactions for the authenticated user."""
    return await list_transactions(
        user_id=current_user_id,
        page=page,
        limit=limit,
        type=type,
        current_user_id=current_user_id,
        db=db,
    )


@router.post("/{user_id}", response_model=TransactionResponse)
async def create_transaction(
    user_id: str,
    tx_data: TransactionCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Manually add a transaction."""
    if settings.ENVIRONMENT == "production":
        if current_user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif user_id != current_user_id and not settings.DEMO_MODE:
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

    # Generate and save transaction embedding for future categorization
    try:
        from ai.categorizer import save_transaction_embedding
        await save_transaction_embedding(
            str(tx.id),
            tx.description or tx.raw_input or "",
            tx.category_code,
            db
        )
    except Exception:
        pass

    # Refresh analytics cache asynchronously

    try:
        from tasks.message_tasks import refresh_analytics_cache
        refresh_analytics_cache.delay(user_id)
    except Exception:
        # Fallback if Celery is down
        from services.analytics import AnalyticsService
        analytics = AnalyticsService(db)
        await analytics.refresh_cache(user_id)

    # Invalidate Redis cache
    from services.cache_manager import invalidate_user_caches
    await invalidate_user_caches(user_id)

    return tx
