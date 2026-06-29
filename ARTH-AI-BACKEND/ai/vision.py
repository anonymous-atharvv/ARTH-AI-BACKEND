# backend/ai/vision.py
"""
Gemini Vision: Receipt/Bill OCR to structured transaction data.
"""
import base64
import json
import structlog
import httpx
import google.generativeai as genai
import io
from PIL import Image
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
    """Extract transaction from receipt image using Gemini Vision."""
    if settings.MOCK_AI or not settings.GEMINI_API_KEY:
        logger.warning("Mock AI enabled or GEMINI_API_KEY not set, returning mock")
        return _mock_extraction()

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        img = Image.open(io.BytesIO(image_bytes))
        model = genai.GenerativeModel(
            settings.GEMINI_MODEL_VISION,
            system_instruction=RECEIPT_SYSTEM_PROMPT,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=500,
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )
        response = await model.generate_content_async([
            "Extract transaction from this receipt:",
            img,
        ])
        return json.loads(response.text)
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
    if not media_url or settings.MOCK_AI or not settings.GEMINI_API_KEY:
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
