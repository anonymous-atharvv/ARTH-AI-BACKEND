# backend/ai/upi_statement_parser.py
"""
Multi-format UPI statement parser.
Handles: Paytm export PDF, PhonePe history screenshot, BHIM text forward,
         GPay screenshot, bank SMS forward.
"""
import json
import base64
import structlog
import google.generativeai as genai
import io
from PIL import Image
from datetime import date
from config import settings

logger = structlog.get_logger()

UPI_PARSE_PROMPT = """You are parsing a UPI transaction statement image or PDF export.
Extract ALL transactions you can see. For each transaction return:
- amount: float (in INR)  
- type: "credit" or "debit"
- counterparty: string (who sent/received money)
- upi_id: string (UPI ID if visible, e.g. "merchant@paytm")
- date: YYYY-MM-DD
- reference_id: string (UTR number if visible)
- payment_app: "paytm"|"phonepe"|"gpay"|"bhim"|"other"

Return ONLY a JSON array. Example:
[{"amount": 500.0, "type": "debit", "counterparty": "Big Bazar", "upi_id": "bigbazar@ybl", "date": "2026-03-15", "reference_id": "UTR123456789", "payment_app": "phonepe"}]

If a field is not visible, use null. Extract ALL transactions, even if many."""

async def parse_upi_statement_image(image_bytes: bytes, user_language: str = "hi") -> list[dict]:
    """Extract all transactions from a UPI statement screenshot using vision AI."""
    if settings.MOCK_AI or not settings.GEMINI_API_KEY:
        logger.info("Mock AI enabled or GEMINI_API_KEY not set. Using mock/stub statement parse response.")
        # Fallback to realistic mock transaction list
        return [
            {
                "amount": 1500.0,
                "type": "debit",
                "counterparty": "Kirana Supply Wholesaler",
                "upi_id": "kiranasupply@okaxis",
                "date": date.today().isoformat(),
                "reference_id": "TXN987654321",
                "payment_app": "paytm"
            },
            {
                "amount": 350.0,
                "type": "credit",
                "counterparty": "Raju (Customer)",
                "upi_id": "raju@paytm",
                "date": date.today().isoformat(),
                "reference_id": "TXN123450987",
                "payment_app": "gpay"
            }
        ]

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        img = Image.open(io.BytesIO(image_bytes))
        model = genai.GenerativeModel(
            settings.GEMINI_MODEL_VISION,
            system_instruction=UPI_PARSE_PROMPT,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=2000,
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )
        response = await model.generate_content_async([
            "Extract all UPI transactions from this statement.",
            img,
        ])

        raw = response.text
        data = json.loads(raw)

        # Handle both {"transactions": [...]} and plain array
        if isinstance(data, dict):
            transactions = data.get("transactions", data.get("data", []))
            if not transactions:
                # If the key isn't standard, check for any list value
                for val in data.values():
                    if isinstance(val, list):
                        transactions = val
                        break
        else:
            transactions = data

        return transactions
    except Exception as e:
        logger.error("Failed to parse UPI statement using Vision API", error=str(e))
        return []
