from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import json
import structlog

logger = structlog.get_logger()

class ConvState:
    IDLE = "IDLE"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    AWAITING_CATEGORY = "AWAITING_CATEGORY"
    REPORT_GENERATING = "REPORT_GENERATING"
    ONBOARDING_NAME = "ONBOARDING_NAME"
    ONBOARDING_BUSINESS = "ONBOARDING_BUSINESS"
    ONBOARDING_LANGUAGE = "ONBOARDING_LANGUAGE"


class ConversationStateManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_state(self, phone: str) -> dict:
        """Get current conversation state for a user"""
        from models.session import WhatsAppSession
        result = await self.db.execute(
            select(WhatsAppSession).where(WhatsAppSession.phone_number == phone)
        )
        session = result.scalar_one_or_none()

        if not session:
            return {"state": ConvState.IDLE, "pending_transaction": None, "context": {}}

        return {
            "state": session.state,
            "pending_transaction": session.pending_transaction,
            "context": session.context or {}
        }

    async def set_state(self, phone: str, state: str,
                        pending_transaction=None, context=None):
        """Update conversation state"""
        from models.session import WhatsAppSession
        # A simple upsert implementation that works with both SQLite and PG:
        result = await self.db.execute(
            select(WhatsAppSession).where(WhatsAppSession.phone_number == phone)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            session = WhatsAppSession(
                phone_number=phone,
                state=state,
                pending_transaction=pending_transaction,
                context=context or {},
                last_activity=datetime.utcnow()
            )
            self.db.add(session)
        else:
            session.state = state
            if pending_transaction is not None:
                session.pending_transaction = pending_transaction
            if context is not None:
                session.context = context
            session.last_activity = datetime.utcnow()
            
        await self.db.commit()

    async def reset(self, phone: str):
        """Reset to IDLE state"""
        await self.set_state(phone, ConvState.IDLE)

    def is_confirmation_yes(self, text: str) -> bool:
        """Detect positive confirmation in multiple languages"""
        text_lower = text.lower().strip()
        yes_words = {
            "1", "haan", "han", "ha", "yes", "yeah", "yep", "ok", "okay",
            "sahi", "sahi hai", "thik", "thik hai", "bilkul", "zaroor",
            "correct", "right", "true", "✅", "👍"
        }
        return any(w in text_lower for w in yes_words)

    def is_confirmation_no(self, text: str) -> bool:
        """Detect negative confirmation in multiple languages"""
        text_lower = text.lower().strip()
        no_words = {
            "2", "nahi", "no", "nope", "galat", "wrong", "incorrect",
            "nai", "na", "nahin", "❌", "👎"
        }
        return any(w in text_lower for w in no_words)
