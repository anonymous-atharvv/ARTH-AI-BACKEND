# backend/models/arthascore.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, JSON, Float
from database import Base
from models.user import GUID


class ArthScoreHistory(Base):
    __tablename__ = "arthascore_history"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(GUID(), nullable=False)
    score = Column(Integer, nullable=False)
    income_regularity = Column(Integer)
    growth_trajectory = Column(Integer)
    expense_control = Column(Integer)
    transaction_volume = Column(Integer)
    business_longevity = Column(Integer)
    payment_consistency = Column(Integer)
    data_completeness = Column(Integer)
    data_points = Column(Integer)
    period_days = Column(Integer)
    snapshot_data = Column(JSON)
    calculated_at = Column(String, default=lambda: datetime.utcnow().isoformat())
