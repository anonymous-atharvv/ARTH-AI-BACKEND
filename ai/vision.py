# backend/ai/vision.py
"""
GPT-4o-mini Vision: Receipt/Bill OCR to structured transaction data.
"""
import base64
import json
import structlog
import httpx
from typing import Optional
from datetime import date
from tenacity import retry, stop_after_attempt, wait_exponential
from config import settings
from schemas.whatsapp import ExtractedTransaction
from schemas.transaction import TransactionType, PaymentMethod

logger = structlog.get_logger()

RECEIPT_SYSTEM_PROMPT = """You are an AI specialized in reading Indian business receipts, bills, and invoices.
Extract ONLY what you can see. Return JSON:
{
  "amount": <float>,
  "type": "income" or "expense",
  "category_code": "<from standard categories>",
  "counterparty": "<shop/person name>",
  "description": "<1-line summary in Hinglish>",
  "payment_method": "cash" or "upi" or "card",
  "transaction_date": "<YYYY-MM-DD>",
  "confidence": <0.0-1.0>,
  "items_detected": [<list of items>],
  "language_detected": "<hi|en|mr|ta|te>"
}
Categories: sales_product, sales_service, inventory, labor_wages, transport_fuel, rent_premises,
utilities, equipment, marketing, food_personal, mobile_internet, other_expense, other_income."""

async def extract_from_image(image_bytes: bytes) -> Optional[dict]:
    """Extract transaction from receipt image using GPT-4V."""
    if settings.MOCK_AI or not settings.OPENAI_API_KEY:
        logger.warning("Mock AI enabled or OPENAI_API_KEY not set, returning mock")
        return _mock_extraction()

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        b64 = base64.b64encode(image_bytes).decode()
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL_VISION,
            messages=[
                {"role": "system", "content": RECEIPT_SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": "Extract transaction from this receipt:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"}},
                ]},
            ],
            response_format={"type": "json_object"}, temperature=0.1, max_tokens=500,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error("Vision extraction failed", error=str(e))
        return _mock_extraction()

def _mock_extraction():
    return {"amount": 500, "type": "expense", "category_code": "inventory",
            "counterparty": "Local Supplier", "description": "Stock purchase",
            "payment_method": "cash", "transaction_date": "2026-01-15",
            "confidence": 0.85, "language_detected": "hi"}

async def extract_from_receipt_image(media_url: str, language: str = "hi") -> ExtractedTransaction:
    """Download receipt image and extract structured transaction"""
    if not media_url or settings.MOCK_AI or not settings.OPENAI_API_KEY:
        mock = _mock_extraction()
        return ExtractedTransaction(
            amount=mock["amount"],
            type=TransactionType(mock["type"]),
            category_code=mock["category_code"],
            counterparty=mock["counterparty"],
            description=mock["description"],
            payment_method=PaymentMethod(mock["payment_method"]),
            transaction_date=date.fromisoformat(mock["transaction_date"]),
            confidence=mock["confidence"],
            raw_text="Mock image transaction",
            language_detected=mock["language_detected"]
        )

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(media_url)
            resp.raise_for_status()
            image_bytes = resp.content
            
        data = await extract_from_image(image_bytes)
        if not data:
            raise ValueError("Vision API returned empty result")
            
        tx_date_str = data.get("transaction_date")
        try:
            tx_date = date.fromisoformat(tx_date_str) if tx_date_str else date.today()
        except Exception:
            tx_date = date.today()

        return ExtractedTransaction(
            amount=float(data.get("amount", 0)),
            type=TransactionType(data.get("type", "expense")),
            category_code=data.get("category_code", "other_expense"),
            counterparty=data.get("counterparty"),
            description=data.get("description", "Image transaction"),
            payment_method=PaymentMethod(data.get("payment_method", "cash")),
            transaction_date=tx_date,
            confidence=float(data.get("confidence", 0.9)),
            raw_text="Receipt image OCR",
            language_detected=data.get("language_detected", language)
        )
    except Exception as e:
        logger.error("extract_from_receipt_image failed", error=str(e))
        mock = _mock_extraction()
        return ExtractedTransaction(
            amount=mock["amount"],
            type=TransactionType(mock["type"]),
            category_code=mock["category_code"],
            counterparty=mock["counterparty"],
            description=mock["description"],
            payment_method=PaymentMethod(mock["payment_method"]),
            transaction_date=date.today(),
            confidence=0.5,
            raw_text=f"Failed image OCR: {str(e)}",
            language_detected=language
        )
