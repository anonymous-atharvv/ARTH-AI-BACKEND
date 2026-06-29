from fastapi import APIRouter, Request, Response, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from twilio.request_validator import RequestValidator
from config import settings
import structlog

router = APIRouter()
logger = structlog.get_logger()


def validate_twilio_request(request_url: str, form_params: dict, signature: str) -> bool:
    """Validate Twilio webhook signature."""
    if settings.WEBHOOK_SKIP_VERIFY or not settings.TWILIO_AUTH_TOKEN:
        return True  # Skip signature validation
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    return validator.validate(request_url, form_params, signature)


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        form_data = await request.form()
        params = dict(form_data)
        
        # Validate Twilio signature
        signature = request.headers.get("X-Twilio-Signature", "")
        request_url = str(request.url)
        
        if not validate_twilio_request(request_url, params, signature):
            logger.warning("Invalid Twilio signature rejected", url=request_url)
            raise HTTPException(status_code=403, detail="Invalid webhook signature")
        
        payload = {
            "from": params.get("From", ""),
            "body": params.get("Body", ""),
            "media_url": params.get("MediaUrl0"),
            "media_type": params.get("MediaContentType0"),
            "num_media": int(params.get("NumMedia", 0) or 0),
            "message_sid": params.get("SmsMessageSid") or params.get("MessageSid"),
        }
        
        logger.info("WhatsApp message received",
                    from_number=payload["from"][-4:],  # Last 4 digits only for privacy
                    has_media=payload["num_media"] > 0)
        
        try:
            from tasks.message_tasks import process_whatsapp_message
            process_whatsapp_message.delay(payload)
        except Exception as celery_err:
            logger.warning("Celery unavailable, async fallback", error=str(celery_err))
            background_tasks.add_task(_process_async, payload)
        
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml"
        )
    except Exception as e:
        logger.error("Webhook processing failed", error=str(e))
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml"
        )


async def _process_async(payload):
    from tasks.message_tasks import _process_message_async
    await _process_message_async(payload)


@router.get("/whatsapp")
async def whatsapp_verify(request: Request):
    """Health check endpoint for Twilio webhook validation."""
    return PlainTextResponse("Home WhatsApp webhook active")
