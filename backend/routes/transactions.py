# backend/routes/transactions.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional

from database import get_db
from models.transaction import Transaction
from schemas.transaction import TransactionCreate, TransactionResponse

router = APIRouter()


@router.get("/{user_id}")
async def list_transactions(
    user_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, le=200),
    type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List transactions for a user (paginated)."""
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
    db: AsyncSession = Depends(get_db),
):
    """Manually add a transaction."""
    tx = Transaction(
        user_id=user_id,
        amount=tx_data.amount,
        type=tx_data.type.value,
        category_code=tx_data.category_code,
        counterparty=tx_data.counterparty,
        description=tx_data.description,
        payment_method=tx_data.payment_method.value,
        transaction_date=tx_data.transaction_date,
        source=tx_data.source.value,
        raw_input=tx_data.raw_input,
        confidence_score=tx_data.confidence_score or 1.0,
        verified=True,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx
