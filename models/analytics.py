# backend/models/analytics.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, ForeignKey
from database import Base
from models.user import GUID


class AnalyticsCache(Base):
    __tablename__ = "analytics_cache"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    mtd_income = Column(Float, default=0)
    mtd_expenses = Column(Float, default=0)
    mtd_net_profit = Column(Float, default=0)
    wtd_income = Column(Float, default=0)
    wtd_expenses = Column(Float, default=0)
    total_transactions = Column(Integer, default=0)
    first_transaction_date = Column(String)
    current_arthascore = Column(Integer)
    last_updated = Column(String, default=lambda: datetime.utcnow().isoformat())

