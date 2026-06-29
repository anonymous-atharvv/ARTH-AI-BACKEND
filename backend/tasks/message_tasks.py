# backend/tasks/message_tasks.py
from tasks.celery_app import celery_app
import asyncio
import structlog

logger = structlog.get_logger()

@celery_app.task(
    name="process_whatsapp_message",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
)
def process_whatsapp_message(self, payload: dict):
    """
    Main async task for processing incoming WhatsApp messages.
    Runs the full LangGraph agent pipeline.
    """
    try:
        asyncio.run(_process_message_async(payload))
    except Exception as exc:
        logger.error("WhatsApp processing failed, retrying",
                     attempt=self.request.retries,
                     error=str(exc))
        raise self.retry(exc=exc)



@celery_app.task(
    name="refresh_analytics_cache",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=30,
)
def refresh_analytics_cache(self, user_id: str):
    """
    Asynchronously refreshes the database-cached analytics summary for a user.
    """
    asyncio.run(_refresh_cache_async(user_id))


async def _refresh_cache_async(user_id: str):
    from database import AsyncSessionLocal
    from services.analytics import AnalyticsService
    async with AsyncSessionLocal() as db:
        analytics = AnalyticsService(db)
        await analytics.refresh_cache(user_id)


async def _process_message_async(payload: dict):
    from agents.financial_agent import compiled_agent
    from database import AsyncSessionLocal
    from models.user import User
    from sqlalchemy import select
    
    phone = payload["from"].replace("whatsapp:", "")  # "+919876543210"
    
    async with AsyncSessionLocal() as db:
        # Get or create user
        result = await db.execute(select(User).where(User.phone_number == phone))
        user = result.scalar_one_or_none()
        
        if not user:
            # New user onboarding
            user = User(phone_number=phone, preferred_language="hi")
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            from services.conversation import ConversationStateManager, ConvState
            state_mgr = ConversationStateManager(db)
            await state_mgr.set_state(phone, ConvState.ONBOARDING_NAME)
            await state_mgr.set_user_id(phone, str(user.id))
            
            from services.whatsapp import WhatsAppService
            wa = WhatsAppService()
            await wa.send_message(phone,
                "🙏 Namaste! Main ArthAI hoon — aapka financial assistant.\n\n"
                "Mujhe bhejein:\n"
                "📸 Receipt ka photo → Main record kar lunga\n"
                "🎤 Voice note → Main samajh lunga\n"
                "✍️ Text → 'Aaj ₹500 ki sale hui'\n\n"
                "Pehle, aapka naam aur kaam kya hai? (e.g., 'Raju, auto-rickshaw')"
            )
            return
        
        # Build and run agent
        initial_state = {
            "user_phone": phone,
            "user_id": str(user.id),
            "user_language": user.preferred_language or "hi",
            "message_type": "",
            "raw_body": payload.get("body", ""),
            "media_url": payload.get("media_url"),
            "media_type": payload.get("media_type"),
            "intent": None,
            "intent_confidence": 0.0,
            "extracted_transaction": None,
            "needs_clarification": False,
            "clarification_message": None,
            "financial_summary": None,
            "response_text": "",
            "response_sent": False,
            "error": None,
        }
        
        await compiled_agent.ainvoke(initial_state)
