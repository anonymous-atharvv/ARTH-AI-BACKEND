# backend/schemas/transaction.py
from pydantic import BaseModel
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
