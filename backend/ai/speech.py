# backend/ai/speech.py
"""Sarvam AI + OpenAI Whisper speech-to-text for Indian languages."""
import httpx
import structlog
from datetime import date
from config import settings
from schemas.whatsapp import ExtractedTransaction
from schemas.transaction import TransactionType, PaymentMethod

logger = structlog.get_logger()

async def transcribe_audio(audio_bytes: bytes, language: str = "hi-IN") -> dict:
    """Transcribe audio — tries Sarvam first, falls back to Whisper."""
    if settings.ENABLE_SARVAM_ASR and settings.SARVAM_API_KEY:
        return await _sarvam_transcribe(audio_bytes, language)
    if settings.OPENAI_API_KEY:
        return await _whisper_transcribe(audio_bytes, language)
    return {"text": "Demo transcription: Aaj maine 500 rupye ka saman kharida.", "language": "hi", "confidence": 0.85}

async def _sarvam_transcribe(audio_bytes: bytes, language: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.sarvam.ai/speech-to-text-translate",
                headers={"api-subscription-key": settings.SARVAM_API_KEY},
                files={"file": ("audio.ogg", audio_bytes, "audio/ogg")},
                data={"model": settings.SARVAM_ASR_MODEL, "language_code": language},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return {"text": data.get("transcript", ""), "language": language[:2], "confidence": 0.9}
    except Exception as e:
        logger.error("Sarvam ASR failed, falling back", error=str(e))
        return await _whisper_transcribe(audio_bytes, language)

async def _whisper_transcribe(audio_bytes: bytes, language: str) -> dict:
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(audio_bytes)
            f.flush()
            with open(f.name, "rb") as audio_file:
                result = await client.audio.transcriptions.create(model="whisper-1", file=audio_file, language=language[:2])
            os.unlink(f.name)
        return {"text": result.text, "language": language[:2], "confidence": 0.85}
    except Exception as e:
        logger.error("Whisper failed", error=str(e))
        return {"text": "", "language": language[:2], "confidence": 0}

async def voice_to_transaction(media_url: str, language: str = "hi") -> ExtractedTransaction:
    """Download voice note, transcribe it, and convert transcript to transaction"""
    from ai.nlu import extract_transaction_from_text
    
    if not media_url or not (settings.OPENAI_API_KEY or settings.SARVAM_API_KEY):
        return ExtractedTransaction(
            amount=250.0,
            type=TransactionType.expense,
            category_code="fuel_transport" if language == "hi" else "transport_fuel",
            counterparty="Auto Fuel",
            description="Aaj ₹250 ka auto fuel bharwaya (Mock)",
            payment_method=PaymentMethod.cash,
            transaction_date=date.today(),
            confidence=0.85,
            raw_text="Aaj ₹250 ka auto fuel bharwaya",
            language_detected=language
        )

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(media_url)
            resp.raise_for_status()
            audio_bytes = resp.content

        transcription_result = await transcribe_audio(audio_bytes, "hi-IN" if language == "hi" else "en-US")
        transcript = transcription_result.get("text", "")
        
        if not transcript:
            raise ValueError("Audio transcription returned empty text")
            
        extracted = await extract_transaction_from_text(transcript, language)
        extracted.raw_text = transcript
        return extracted
    except Exception as e:
        logger.error("voice_to_transaction failed", error=str(e))
        return ExtractedTransaction(
            amount=0.0,
            type=TransactionType.expense,
            category_code="other_expense",
            counterparty=None,
            description="Failed to transcribe voice",
            payment_method=PaymentMethod.cash,
            transaction_date=date.today(),
            confidence=0.0,
            raw_text=f"Failed voice note processing: {str(e)}",
            language_detected=language
        )
