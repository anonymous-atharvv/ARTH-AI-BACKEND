from twilio.rest import Client
from config import settings
import structlog

logger = structlog.get_logger()

class WhatsAppService:
    def __init__(self):
        # Allow running in mock/demo mode if SID or Token is not set
        self.client = None
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            try:
                self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            except Exception as e:
                logger.error("Failed to initialize Twilio client", error=str(e))
        self.from_number = settings.TWILIO_WHATSAPP_FROM or "whatsapp:+14155238886"

    async def send_message(self, to_phone: str, body: str) -> str:
        """Send WhatsApp message via Twilio"""
        if not to_phone.startswith("whatsapp:"):
            to_phone = f"whatsapp:{to_phone}"
        
        logger.info("Sending WhatsApp message", to=to_phone, body=body[:100])
        
        if not self.client:
            logger.info("Mock Twilio mode: Message not sent (credentials missing)")
            return "mock-sid-123"
            
        try:
            message = self.client.messages.create(
                body=body[:1500],  # WhatsApp limit
                from_=self.from_number,
                to=to_phone
            )
            logger.info("WhatsApp message sent", message_sid=message.sid, to=to_phone)
            return message.sid
        except Exception as e:
            logger.error("WhatsApp send failed", error=str(e), to=to_phone)
            raise

    async def send_document(self, to_phone: str, media_url: str, caption: str = "") -> str:
        """Send PDF document via WhatsApp"""
        if not to_phone.startswith("whatsapp:"):
            to_phone = f"whatsapp:{to_phone}"
            
        logger.info("Sending WhatsApp document", to=to_phone, media_url=media_url, caption=caption)
        
        if not self.client:
            logger.info("Mock Twilio mode: Document not sent (credentials missing)")
            return "mock-doc-sid-123"
            
        try:
            message = self.client.messages.create(
                body=caption,
                from_=self.from_number,
                to=to_phone,
                media_url=[media_url]
            )
            return message.sid
        except Exception as e:
            logger.error("WhatsApp document send failed", error=str(e), to=to_phone)
            raise
