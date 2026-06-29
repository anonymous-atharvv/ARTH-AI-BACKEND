# backend/schemas/transaction.py
import re
from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any
from datetime import date, datetime
from enum import Enum


class TransactionType(str, Enum):
    income = "income"
    expense = "expense"
    transfer = "transfer"


class PaymentMethod(str, Enum):
    cash = "cash"
    upi = "upi"
    card = "card"
    credit = "credit"
    unknown = "unknown"


class TransactionSource(str, Enum):
    image = "image"
    voice = "voice"
    text = "text"
    upi_statement = "upi_statement"
    manual = "manual"


class TransactionCreate(BaseModel):
    amount: float
    type: TransactionType
    category_code: Optional[str] = None
    counterparty: Optional[str] = None
    description: Optional[str] = None
    payment_method: PaymentMethod = PaymentMethod.cash
    transaction_date: str  # ISO date string
    source: TransactionSource
    raw_input: Optional[str] = None
    confidence_score: Optional[float] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        if v > 10000000.0:
            raise ValueError("Amount exceeds limit of 10,000,000")
        return round(v, 2)

    @field_validator("description", "counterparty")
    @classmethod
    def sanitize_string(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        import html
        # Basic sanitization: strip HTML tags
        clean = re.sub(r"<[^>]*>", "", v)
        return html.escape(clean.strip())



class TransactionResponse(BaseModel):
    id: str
    amount: float
    type: str
    category_code: Optional[str] = None
    counterparty: Optional[str] = None
    description: Optional[str] = None
    payment_method: str = "cash"
    transaction_date: str
    source: str
    verified: bool = False
    confidence_score: Optional[float] = None
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}
