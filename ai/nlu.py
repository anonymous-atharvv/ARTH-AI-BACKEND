# backend/ai/nlu.py
"""
Natural Language Understanding for financial messages.
Handles:
- Intent classification (TRANSACTION, QUERY, REPORT_REQUEST, GREETING, HELP)
- Entity extraction (amount, type, category, counterparty, date)
- Supports Hinglish + 12 Indian languages
"""
import json
import re
from openai import AsyncOpenAI
from datetime import date
import structlog
from typing import Tuple, Optional

from config import settings
from schemas.whatsapp import ExtractedTransaction
from schemas.transaction import TransactionType, PaymentMethod

logger = structlog.get_logger()

# ─── INTENT CLASSIFICATION PROMPT ───────────────────────────────────────────
INTENT_SYSTEM_PROMPT = """You classify WhatsApp messages from Indian small business owners.

Classify into ONE of these intents:
- TRANSACTION: Recording a financial transaction (income/expense/payment)
- QUERY: Asking about their financial data ("kitna kamaya?", "mera profit kya hai?")
- REPORT_REQUEST: Requesting a document ("loan ke liye document chahiye", "passport banao")
- GREETING: Hello, hi, namaste, first contact
- HELP: Asking what ArthAI can do, confused about usage
- CONFIRMATION_YES: Confirming a previous suggestion (haan, 1, yes, sahi hai, thik hai)
- CONFIRMATION_NO: Rejecting a previous suggestion (nahi, 2, galat, wrong)

Return ONLY a JSON: {"intent": "TRANSACTION", "confidence": 0.95}

Examples:
"Aaj ₹850 ki sawari mili" → {"intent": "TRANSACTION", "confidence": 0.99}
"Is hafte kitna kamaya?" → {"intent": "QUERY", "confidence": 0.98}
"Loan ke liye document chahiye" → {"intent": "REPORT_REQUEST", "confidence": 0.97}
"Haan, sahi hai" → {"intent": "CONFIRMATION_YES", "confidence": 0.99}
"Ramesh ko ₹2000 diye petrol ke liye" → {"intent": "TRANSACTION", "confidence": 0.97}
"""

# ─── TRANSACTION EXTRACTION PROMPT ──────────────────────────────────────────
EXTRACTION_SYSTEM_PROMPT = """You extract financial transaction details from Indian business owner messages.
Messages come in Hindi, Marathi, Hinglish, or other Indian languages. Extract accurately.

AMOUNT PARSING RULES:
- "teen hazaar" = ₹3,000
- "do sau pachas" = ₹250
- "1.5 lakh" = ₹1,50,000
- "panch so" = ₹500
- "dus rupaye" = ₹10
- Symbol "₹" always precedes amount in Indian convention

TYPE DETERMINATION:
- "mili", "aaya", "kamaya", "sale", "earned", "received" → income
- "diya", "diye", "kharcha", "expense", "paid", "kharida" → expense
- Context: if buying something → expense; if selling/earning → income

Return ONLY this JSON (no explanation):
{
  "amount": <number in INR>,
  "type": <"income" or "expense">,
  "category_code": <exact code from list below>,
  "counterparty": <person/merchant name or null>,
  "description": <brief English description>,
  "payment_method": <"cash"|"upi"|"card"|"unknown">,
  "transaction_date": <"YYYY-MM-DD", today if not mentioned>,
  "confidence": <0.0-1.0>
}

VALID CATEGORY CODES:
Income: sales_product, sales_service, commission, rental_income, other_income
Expense: inventory, labor_wages, transport_fuel, rent_premises, utilities,
         equipment, marketing, professional_fees, loan_repayment, tax_government,
         food_personal, mobile_internet, other_expense

TODAY: {today_date}
"""

# ─── QUERY HANDLER PROMPT ────────────────────────────────────────────────────
QUERY_SYSTEM_PROMPT = """You are ArthAI, a friendly financial assistant for Indian small business owners.
The user will ask about their business finances. Answer in their language (usually Hindi or Hinglish).

You have access to their financial data in JSON format. Use it to answer accurately.

Response style:
- Friendly, like talking to a trusted friend who knows business
- Use Indian number formats (lakh, hazaar, etc.)
- Keep responses under 200 words
- End with a useful insight or encouragement
- If asked in Hindi, respond in Hindi/Hinglish
- Use simple language, no accounting jargon

Example response (Hindi):
"Raju bhai, is hafte aapne ₹7,800 kamaye aur ₹3,600 kharcha kiya.
Net profit ₹4,200 raha — average se 10% zyada!
Fuel expense thoda zyada tha (₹1,200 = 16% of income), dhyan rakhein."
"""

async def classify_intent(text: str) -> Tuple[str, float]:
    """Classify message intent. Returns (intent, confidence)"""
    if settings.MOCK_AI or not settings.OPENAI_API_KEY:
        res = _rule_based_classify(text)
        return res["intent"], res["confidence"]
        
    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL_NLU,
            messages=[
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            max_tokens=60,
            temperature=0.1
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        return data["intent"], data["confidence"]
    except Exception as e:
        logger.error("NLU classification failed", error=str(e))
        res = _rule_based_classify(text)
        return res["intent"], res["confidence"]

async def extract_transaction_from_text(
    text: str,
    user_language: str = "hi"
) -> ExtractedTransaction:
    """Extract structured transaction from natural language text"""
    if settings.MOCK_AI or not settings.OPENAI_API_KEY:
        # Try rule-based extraction
        amount = _extract_amount(text) or 100.0
        tx_type = "expense" if any(w in text.lower() for w in ("spent", "paid", "diya", "kharcha", "kharida")) else "income"
        category = "inventory" if tx_type == "expense" else "sales_product"
        return ExtractedTransaction(
            amount=amount,
            type=TransactionType(tx_type),
            category_code=category,
            counterparty="Local Supplier" if tx_type == "expense" else "Customer",
            description=f"Transaction: {text[:50]}",
            payment_method=PaymentMethod.cash,
            transaction_date=date.today(),
            confidence=0.7,
            raw_text=text,
            language_detected=user_language
        )

    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        prompt = EXTRACTION_SYSTEM_PROMPT.replace("{today_date}", date.today().isoformat())
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL_NLU,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ],
            max_tokens=300,
            temperature=0.1
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        
        tx_date_str = data.get("transaction_date")
        try:
            tx_date = date.fromisoformat(tx_date_str) if tx_date_str else date.today()
        except Exception:
            tx_date = date.today()

        return ExtractedTransaction(
            amount=float(data["amount"]),
            type=TransactionType(data["type"]),
            category_code=data["category_code"],
            counterparty=data.get("counterparty"),
            description=data.get("description", text[:200]),
            payment_method=PaymentMethod(data.get("payment_method", "cash")),
            transaction_date=tx_date,
            confidence=float(data["confidence"]),
            raw_text=text,
            language_detected=user_language
        )
    except Exception as e:
        logger.error("NLU extraction failed", error=str(e))
        amount = _extract_amount(text) or 100.0
        return ExtractedTransaction(
            amount=amount,
            type=TransactionType.expense,
            category_code="other_expense",
            counterparty=None,
            description=f"Failed extraction: {text[:50]}",
            payment_method=PaymentMethod.cash,
            transaction_date=date.today(),
            confidence=0.4,
            raw_text=text,
            language_detected=user_language
        )

async def answer_financial_query(
    question: str,
    financial_data: dict,
    user_language: str = "hi"
) -> str:
    """Answer natural language financial question using user's data"""
    if settings.MOCK_AI or not settings.OPENAI_API_KEY:
        # Standard templates for offline demo answers
        total_income = financial_data.get("mtd_income", 0)
        total_expenses = financial_data.get("mtd_expenses", 0)
        net_profit = financial_data.get("mtd_net_profit", 0)
        if user_language == "hi":
            return (
                f"Raju bhai, is mahine aapne ₹{total_income:,.0f} kamaye aur ₹{total_expenses:,.0f} kharcha kiya. "
                f"Aapka net profit ₹{net_profit:,.0f} raha. "
                "Hisaab sahi chal raha hai! 👍"
            )
        else:
            return (
                f"Raju, this month you earned ₹{total_income:,.0f} and spent ₹{total_expenses:,.0f}. "
                f"Your net profit is ₹{net_profit:,.0f}. "
                "Keep tracking! 👍"
            )

    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        lang_instruction = "Respond in Hindi/Hinglish (mix of Hindi and English)." if user_language == "hi" else "Respond in English."
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL_NLU,
            messages=[
                {"role": "system", "content": QUERY_SYSTEM_PROMPT + f"\n\n{lang_instruction}"},
                {"role": "user", "content": f"""User's financial data:
{json.dumps(financial_data, indent=2, ensure_ascii=False)}

User's question: {question}

Answer their question using the financial data. Be specific with numbers."""}
            ],
            max_tokens=300,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("Financial query answer failed", error=str(e))
        return "Failed to query financial engine. Please try again."

def _rule_based_classify(text: str) -> dict:
    text_lower = text.lower().strip()
    amount = _extract_amount(text_lower)
    if text_lower in ("haan", "yes", "ok", "sahi hai", "theek hai", "ha", "1"):
        return {"intent": "CONFIRMATION_YES", "confidence": 0.95}
    if text_lower in ("nahi", "no", "galat", "wrong", "incorrect", "2"):
        return {"intent": "CONFIRMATION_NO", "confidence": 0.95}
    if any(w in text_lower for w in ("report", "passport", "pdf", "document")):
        return {"intent": "REPORT_REQUEST", "confidence": 0.8}
    if amount:
        return {"intent": "TRANSACTION", "confidence": 0.7}
    if any(w in text_lower for w in ("kitna", "how much", "total", "kamai", "score", "profit")):
        return {"intent": "QUERY", "confidence": 0.7}
    return {"intent": "GREETING", "confidence": 0.5}

def _extract_amount(text: str) -> Optional[float]:
    patterns = [r'₹\s*([\d,]+)', r'rs\.?\s*([\d,]+)', r'([\d,]+)\s*(?:rupye|rupees|rs)', r'([\d,]+)\s*ka']
    for p in patterns:
        m = re.search(p, text)
        if m:
            return float(m.group(1).replace(",", ""))
    return None
