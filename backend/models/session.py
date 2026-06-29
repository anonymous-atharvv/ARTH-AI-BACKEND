# backend/models/session.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, JSON
from database import Base
from models.user import GUID


class WhatsAppSession(Base):
    __tablename__ = "whatsapp_sessions"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(GUID(), nullable=True)
    phone_number = Column(String(15), nullable=False, unique=True)
    state = Column(String(50), nullable=False, default="IDLE")
    pending_transaction = Column(JSON)
    context = Column(JSON, default={})
    last_activity = Column(String, default=lambda: datetime.utcnow().isoformat())
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
