# backend/schemas/whatsapp.py
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import date
from enum import Enum
from schemas.transaction import TransactionType, PaymentMethod


class WhatsAppIncoming(BaseModel):
    """Twilio WhatsApp webhook payload schema."""
    From: str
    To: str
    Body: Optional[str] = ""
    NumMedia: Optional[str] = "0"
    MediaUrl0: Optional[str] = None
    MediaContentType0: Optional[str] = None


class ExtractedTransaction(BaseModel):
    """Standardized output from all AI extraction modules."""
    amount: float
    type: TransactionType
    category_code: str
    counterparty: Optional[str] = None
    description: str
    payment_method: PaymentMethod = PaymentMethod.cash
    transaction_date: str  # ISO date string
    confidence: float  # 0.0 to 1.0
    raw_text: Optional[str] = None
    language_detected: str = "hi"


class ArthScoreResponse(BaseModel):
    score: int  # 300-900
    grade: str
    grade_hi: str
    max_loan_eligible: float
    factors: Dict[str, int]
    insight_hi: str
    insight_en: str
    calculated_at: Optional[str] = None
    data_points: int = 0
