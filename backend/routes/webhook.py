# backend/routes/webhook.py
"""
WhatsApp Webhook — Entry point for ALL WhatsApp interactions.
Twilio sends a POST request here on every message.
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import PlainTextResponse
import structlog
import asyncio

router = APIRouter()
logger = structlog.get_logger()

@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Receives all WhatsApp messages from Twilio.
    Returns HTTP 200 + empty TwiML immediately.
    Dispatches task for async AI processing.
    """
    try:
        form_data = await request.form()
        payload = dict(form_data)

        logger.info("WhatsApp message received",
                    from_number=payload.get("From", ""),
                    has_media=int(payload.get("NumMedia", 0)) > 0,
                    body_length=len(payload.get("Body", "")))

        # Normalize the payload fields to match what the task expects
        normalized_payload = {
            "from": payload.get("From", ""),
            "body": payload.get("Body", ""),
            "media_url": payload.get("MediaUrl0"),
            "media_type": payload.get("MediaContentType0"),
        }

        # Dispatch Celery task
        try:
            from tasks.message_tasks import process_whatsapp_message
            process_whatsapp_message.delay(normalized_payload)
            logger.info("Celery task dispatched successfully")
        except Exception as celery_err:
            logger.warning("Celery queue unavailable, processing synchronously", error=str(celery_err))
            # Fallback to direct synchronous execution in a background task
            from tasks.message_tasks import _process_message_async
            asyncio.create_task(_process_message_async(normalized_payload))

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

@router.get("/whatsapp")
async def whatsapp_verify(request: Request):
    """Health check endpoint for Twilio webhook validation."""
    return PlainTextResponse("ArthAI WhatsApp webhook active")
