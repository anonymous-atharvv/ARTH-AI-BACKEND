# backend/models/insight.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, JSON
from database import Base
from models.user import GUID


class InsightLog(Base):
    __tablename__ = "insights_log"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(GUID(), nullable=False)
    insight_type = Column(String(50))
    insight_data = Column(JSON)
    sent_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    acknowledged = Column(Boolean, default=False)
