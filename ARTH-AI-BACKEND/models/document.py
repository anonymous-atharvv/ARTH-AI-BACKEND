# backend/models/document.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, JSON, Text
from database import Base
from models.user import GUID


class Document(Base):
    __tablename__ = "documents"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(GUID(), nullable=False)
    document_type = Column(String(50), nullable=False)
    file_url = Column(Text, nullable=False)
    period_start = Column(String)
    period_end = Column(String)
    arthascore_at_generation = Column(Integer)
    summary_data = Column(JSON)
    generated_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    expires_at = Column(String)
