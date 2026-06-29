# backend/ai/speech.py
"""Sarvam AI + Gemini speech-to-text for Indian languages."""
import httpx
import structlog
import google.generativeai as genai
import tempfile
import os
from datetime import date
from config import settings
from schemas.whatsapp import ExtractedTransaction
from schemas.transaction import TransactionType, PaymentMethod

logger = structlog.get_logger()

async def transcribe_audio(audio_bytes: bytes, language: str = "hi-IN") -> dict:
    """Transcribe audio — tries Sarvam first, falls back to Gemini."""
    if not settings.MOCK_AI:
        if settings.ENABLE_SARVAM_ASR and settings.SARVAM_API_KEY:
            return await _sarvam_transcribe(audio_bytes, language)
        if settings.GEMINI_API_KEY:
            return await _gemini_transcribe(audio_bytes, language)
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
        return await _gemini_transcribe(audio_bytes, language)

async def _gemini_transcribe(audio_bytes: bytes, language: str) -> dict:
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL_VISION)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(audio_bytes)
            f.flush()
            uploaded = genai.upload_file(f.name)
        os.unlink(f.name)
        response = await model.generate_content_async([
            "Transcribe this audio exactly as spoken. Return only the transcribed text:",
            uploaded,
        ])
        return {"text": response.text.strip(), "language": language[:2], "confidence": 0.85}
    except Exception as e:
        logger.error("Gemini transcription failed", error=str(e))
        return {"text": "", "language": language[:2], "confidence": 0}

async def voice_to_transaction(media_url: str, language: str = "hi") -> ExtractedTransaction:
    """Download voice note, transcribe it, and convert transcript to transaction"""
    from ai.nlu import extract_transaction_from_text
    
    if not media_url or settings.MOCK_AI or not (settings.GEMINI_API_KEY or settings.SARVAM_API_KEY):
        return ExtractedTransaction(
            amount=250.0,
            type=TransactionType.expense,
            category_code="transport_fuel",
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

        from ai.language_router import get_sarvam_language_code
        lang_code = get_sarvam_language_code(language)
        transcription_result = await transcribe_audio(audio_bytes, lang_code)
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
