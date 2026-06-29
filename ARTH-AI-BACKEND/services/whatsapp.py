from twilio.rest import Client
from config import settings
import structlog

logger = structlog.get_logger()

class WhatsAppService:
    def __init__(self):
        self.provider = settings.WHATSAPP_PROVIDER
        self.client = None
        if self.provider != "meta_direct":
            if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
                try:
                    self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                except Exception as e:
                    logger.error("Failed to initialize Twilio client", error=str(e))
            self.from_number = settings.TWILIO_WHATSAPP_FROM or "whatsapp:+14155238886"

    async def send_message(self, to_phone: str, body: str) -> str:
        """Send WhatsApp message using configured provider"""
        if not to_phone.startswith("whatsapp:"):
            to_phone = f"whatsapp:{to_phone}"
        
        masked_phone = "whatsapp:..." + to_phone[-4:] if len(to_phone) > 4 else to_phone
        logger.info("Sending WhatsApp message", provider=self.provider, to=masked_phone)
        
        if self.provider == "meta_direct":
            if not settings.META_WHATSAPP_TOKEN or not settings.META_PHONE_NUMBER_ID:
                logger.warning("Meta WABA credentials missing, running in mock mode")
                return "mock-meta-sid-123"
            return await self._send_via_meta(to_phone, body)
            
        if not self.client:
            logger.info("Mock Twilio mode: Message not sent (credentials missing)")
            return "mock-sid-123"
            
        try:
            message = self.client.messages.create(
                body=body[:1500],  # WhatsApp limit
                from_=self.from_number,
                to=to_phone
            )
            logger.info("WhatsApp message sent", message_sid=message.sid, to=masked_phone)
            return message.sid
        except Exception as e:
            logger.error("WhatsApp send failed", error=str(e), to=masked_phone)
            raise

    async def send_document(self, to_phone: str, media_url: str, caption: str = "") -> str:
        """Send PDF document using configured provider"""
        if not to_phone.startswith("whatsapp:"):
            to_phone = f"whatsapp:{to_phone}"
            
        masked_phone = "whatsapp:..." + to_phone[-4:] if len(to_phone) > 4 else to_phone
        clean_url = media_url.split("?")[0] if media_url else ""
        logger.info("Sending WhatsApp document", provider=self.provider, to=masked_phone, media_url=clean_url, caption=caption)
        
        if self.provider == "meta_direct":
            if not settings.META_WHATSAPP_TOKEN or not settings.META_PHONE_NUMBER_ID:
                logger.warning("Meta WABA credentials missing, running in mock mode")
                return "mock-meta-doc-sid-123"
            return await self._send_document_via_meta(to_phone, media_url, caption)

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
            logger.error("WhatsApp document send failed", error=str(e), to=masked_phone)
            raise

    async def _send_via_meta(self, to_phone: str, body: str) -> str:
        """Send via Meta Cloud API (required for production WABA)."""
        import httpx
        clean_phone = to_phone.replace("whatsapp:", "")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://graph.facebook.com/v18.0/{settings.META_PHONE_NUMBER_ID}/messages",
                headers={"Authorization": f"Bearer {settings.META_WHATSAPP_TOKEN}"},
                json={
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": clean_phone,
                    "type": "text",
                    "text": {"body": body[:4096]}
                }
            )
            response.raise_for_status()
            return response.json().get("messages", [{}])[0].get("id", "")

    async def _send_document_via_meta(self, to_phone: str, media_url: str, caption: str = "") -> str:
        """Send document via Meta Cloud API (required for production WABA)."""
        import httpx
        clean_phone = to_phone.replace("whatsapp:", "")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://graph.facebook.com/v18.0/{settings.META_PHONE_NUMBER_ID}/messages",
                headers={"Authorization": f"Bearer {settings.META_WHATSAPP_TOKEN}"},
                json={
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": clean_phone,
                    "type": "document",
                    "document": {
                        "link": media_url,
                        "caption": caption[:1024]
                    }
                }
            )
            response.raise_for_status()
            return response.json().get("messages", [{}])[0].get("id", "")

