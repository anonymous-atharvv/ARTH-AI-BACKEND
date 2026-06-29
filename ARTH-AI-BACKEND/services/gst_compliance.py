# backend/services/gst_compliance.py
"""
Generates GSTR-1 compatible data from transaction records.
Enables income tax compliant reporting for MSMEs.
"""
from datetime import date
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession

async def generate_gstr1_data(db: AsyncSession, user_id: str, year: int, month: int) -> dict:
    """
    Returns GSTR-1 ready summary for a given month.
    B2C supplies (sales to unregistered buyers) summary.
    """
    from models.transaction import Transaction
    from sqlalchemy import select, and_
    from models.user import User

    month_start = date(year, month, 1).isoformat()
    if month == 12:
        month_end = date(year + 1, 1, 1).isoformat()
    else:
        month_end = date(year, month + 1, 1).isoformat()

    result = await db.execute(
        select(Transaction).where(
            and_(
                Transaction.user_id == user_id,
                Transaction.type == "income",
                Transaction.transaction_date >= month_start,
                Transaction.transaction_date < month_end,
            )
        )
    )
    txs = result.scalars().all()

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    user_name = user.name if user else "Business Owner"
    business_type = user.business_type if user else "Business"

    total_sales = sum(float(t.amount) for t in txs)
    # Assume 18% GST (standard rate for services/retail)
    taxable_value = total_sales / 1.18
    total_igst = 0  # Interstate — assume intrastate for now
    total_cgst = (total_sales - taxable_value) / 2
    total_sgst = (total_sales - taxable_value) / 2

    by_category = defaultdict(float)
    for t in txs:
        by_category[t.category_code or "other"] += float(t.amount)

    return {
        "taxpayer_name": user_name,
        "business_type": business_type,
        "filing_period": f"{year}-{month:02d}",
        "generated_on": date.today().isoformat(),
        "b2c_summary": {
            "total_taxable_value": round(taxable_value, 2),
            "total_cgst": round(total_cgst, 2),
            "total_sgst": round(total_sgst, 2),
            "total_igst": total_igst,
            "total_invoice_value": round(total_sales, 2),
            "transaction_count": len(txs),
        },
        "category_breakdown": dict(by_category),
        "note": "ArthAI-generated estimate. Please verify with CA before filing.",
        "disclaimer": "This is based on transactions recorded via ArthAI. Consult a CA for official GST compliance.",
    }
