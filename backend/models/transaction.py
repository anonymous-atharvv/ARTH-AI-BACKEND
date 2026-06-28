# backend/models/transaction.py
import uuid
from datetime import datetime, date as date_type
from sqlalchemy import Column, String, Numeric, Boolean, Date, Time, Text, JSON, Float
from database import Base
from models.user import GUID


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(GUID(), nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String(10), nullable=False)  # income | expense | transfer
    category_code = Column(String(50))
    counterparty = Column(String(200))
    description = Column(String(500))
    payment_method = Column(String(20), default="cash")
    transaction_date = Column(String, nullable=False)  # ISO date string for SQLite compat
    transaction_time = Column(String)
    source = Column(String(20), nullable=False)  # image | voice | text | upi_statement | manual
    raw_input = Column(Text)
    extracted_data = Column(JSON)
    confidence_score = Column(Float)
    verified = Column(Boolean, default=False)
    location = Column(String(200))
    notes = Column(Text)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    updated_at = Column(String, default=lambda: datetime.utcnow().isoformat())
