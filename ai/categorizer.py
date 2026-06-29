# backend/ai/categorizer.py
"""Auto-categorize transactions based on description and context."""
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog
from config import settings

logger = structlog.get_logger()

CATEGORY_KEYWORDS = {
    "sales_product": ["sold", "becha", "bikri", "sale", "bik gaya", "customer"],
    "sales_service": ["service", "repair", "seva", "kaam kiya", "labour charge"],
    "inventory": ["stock", "maal", "saman", "kharida", "purchase", "wholesale"],
    "labor_wages": ["wages", "mazdoori", "salary", "tankhah", "labour"],
    "transport_fuel": ["petrol", "diesel", "fuel", "transport", "delivery", "auto"],
    "rent_premises": ["rent", "kiraya", "dukaan", "shop"],
    "utilities": ["bijli", "electricity", "pani", "water", "gas"],
    "equipment": ["repair", "machine", "tool", "equipment"],
    "food_personal": ["khana", "food", "chai", "lunch", "dinner", "nashta"],
    "mobile_internet": ["recharge", "mobile", "internet", "data", "phone"],
}


def auto_categorize(description: str, tx_type: str = "expense") -> str:
    desc_lower = description.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return cat
    return "other_income" if tx_type == "income" else "other_expense"


async def categorize_with_embeddings(description: str, tx_type: str, db: AsyncSession) -> str:
    """Two-stage categorization: keyword → semantic fallback."""
    category = auto_categorize(description, tx_type)
    if category not in ("other_expense", "other_income"):
        return category  # Confident keyword match

    if not settings.OPENAI_API_KEY:
        return category

    try:
        from openai import AsyncOpenAI
        from models.transaction_embedding import TransactionEmbedding

        # Get current embedding
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=description
        )
        curr_embedding = response.data[0].embedding

        # Fetch stored embeddings
        stmt = select(TransactionEmbedding)
        res = await db.execute(stmt)
        stored = res.scalars().all()

        if not stored:
            return category

        best_similarity = -1.0
        best_category = category

        # Compute cosine similarity
        curr_vector = np.array(curr_embedding)
        curr_norm = np.linalg.norm(curr_vector)

        if curr_norm > 0:
            for item in stored:
                if not item.embedding:
                    continue
                # item.embedding is stored as JSON list of floats
                item_vector = np.array(item.embedding)
                item_norm = np.linalg.norm(item_vector)
                if item_norm > 0:
                    sim = np.dot(curr_vector, item_vector) / (curr_norm * item_norm)
                    if sim > best_similarity:
                        best_similarity = sim
                        best_category = item.category_code

            logger.info("Semantic categorization completed",
                        best_similarity=best_similarity,
                        inferred_category=best_category,
                        original_category=category)

            # Similarity threshold (e.g. 0.75 or 0.8)
            if best_similarity >= 0.75:
                return best_category

    except Exception as e:
        logger.warning("Embedding categorization failed, falling back to keyword search", error=str(e))

    return category


async def save_transaction_embedding(transaction_id: str, description: str, category_code: str, db: AsyncSession):
    """Generate and save embedding for a new transaction description."""
    if not settings.OPENAI_API_KEY:
        return
    try:
        from openai import AsyncOpenAI
        from models.transaction_embedding import TransactionEmbedding

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=description
        )
        embedding = response.data[0].embedding

        tx_emb = TransactionEmbedding(
            transaction_id=transaction_id,
            embedding=embedding,
            description_normalized=description.strip().lower(),
            category_code=category_code,
            confidence=1.0
        )
        db.add(tx_emb)
        await db.commit()
        logger.info("Saved transaction embedding", transaction_id=transaction_id)
    except Exception as e:
        logger.warning("Failed to save transaction embedding", transaction_id=transaction_id, error=str(e))
        try:
            await db.rollback()
        except Exception:
            pass

