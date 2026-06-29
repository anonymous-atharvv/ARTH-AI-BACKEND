# backend/routes/demo.py
"""
Demo seed endpoint — loads Raju's 90-day synthetic transaction dataset.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import json
from pathlib import Path

from database import get_db
from models.user import User
from models.transaction import Transaction

router = APIRouter()


@router.post("/seed")
async def seed_demo_data(db: AsyncSession = Depends(get_db)):
    """
    Seeds Raju's 90-day synthetic transaction dataset.
    Call this ONCE to set up the demo.
    """
    demo_data_path = Path(__file__).parent.parent / "demo-data" / "raju_90days.json"

    if not demo_data_path.exists():
        return {"error": "Demo data file not found", "path": str(demo_data_path)}

    data = json.loads(demo_data_path.read_text())

    # Create or update Raju's user
    result = await db.execute(
        select(User).where(User.id == data["user"]["id"])
    )
    raju = result.scalar_one_or_none()

    if not raju:
        raju = User(
            id=data["user"]["id"],
            phone_number=data["user"]["phone_number"],
            name=data["user"]["name"],
            preferred_language=data["user"]["preferred_language"],
            business_type=data["user"]["business_type"],
            business_location=data["user"]["business_location"],
            onboarding_complete=data["user"]["onboarding_complete"],
        )
        db.add(raju)

    # Clear existing demo transactions
    await db.execute(
        delete(Transaction).where(Transaction.user_id == data["user"]["id"])
    )

    # Insert all transactions
    for tx_data in data["transactions"]:
        tx = Transaction(
            user_id=data["user"]["id"],
            amount=tx_data["amount"],
            type=tx_data["type"],
            category_code=tx_data["category_code"],
            counterparty=tx_data.get("counterparty"),
            description=tx_data["description"],
            payment_method=tx_data.get("payment_method", "cash"),
            transaction_date=tx_data["transaction_date"],
            source=tx_data["source"],
            confidence_score=0.95,
            verified=True,
        )
        db.add(tx)

    await db.commit()
    return {
        "message": "Demo data seeded successfully",
        "user": "Raju Kumar",
        "transactions_loaded": len(data["transactions"]),
        "demo_user_id": data["user"]["id"],
        "dashboard_url": f"/dashboard/{data['user']['id']}",
    }
