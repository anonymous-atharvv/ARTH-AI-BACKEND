# backend/models/transaction.py
import uuid
from datetime import datetime, date as date_type
from sqlalchemy import Column, String, Float, Boolean, Date, Text, JSON, func, Index
from sqlalchemy.types import TypeDecorator
from database import Base
from models.user import GUID


class ISODate(TypeDecorator):
    """Store dates as ISO strings in SQLite, native Date in PostgreSQL."""
    impl = String(10)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, date_type):
            return value.isoformat()
        if isinstance(value, str):
            return value[:10]  # truncate to YYYY-MM-DD
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, date_type):
            return value
        try:
            return date_type.fromisoformat(str(value)[:10])
        except (ValueError, TypeError):
            return None


class Transaction(Base):
    __tablename__ = "transactions"

    __table_args__ = (
        Index("idx_transactions_user_date", "user_id", "transaction_date"),
    )

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(GUID(), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    type = Column(String(10), nullable=False)
    category_code = Column(String(50), index=True)
    counterparty = Column(String(200))
    description = Column(String(500))
    payment_method = Column(String(20), default="cash")
    transaction_date = Column(ISODate, nullable=False, index=True)  # ← KEY FIX
    transaction_time = Column(String(8))
    source = Column(String(20), nullable=False)
    raw_input = Column(Text)
    extracted_data = Column(JSON)
    confidence_score = Column(Float, default=0.95)
    verified = Column(Boolean, default=False)
    location = Column(String(200))
    notes = Column(Text)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    updated_at = Column(String, default=lambda: datetime.utcnow().isoformat())
