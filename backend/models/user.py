# backend/models/user.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, JSON
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.types import TypeDecorator, CHAR
from database import Base


class GUID(TypeDecorator):
    """Platform-independent GUID type — uses CHAR(36) for SQLite, UUID for PostgreSQL."""
    impl = CHAR(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return str(value)
        return value


class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone_number = Column(String(15), unique=True, nullable=False)
    name = Column(String(100))
    preferred_language = Column(String(10), default="hi")
    business_type = Column(String(100))
    business_location = Column(String(200))
    onboarding_complete = Column(Boolean, default=False)
    whatsapp_session_state = Column(JSON, default={"state": "IDLE"})
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    updated_at = Column(String, default=lambda: datetime.utcnow().isoformat())
