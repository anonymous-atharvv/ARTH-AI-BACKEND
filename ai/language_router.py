# backend/ai/language_router.py
"""
Routes each message to the appropriate AI model based on detected language.
Supports: hi, mr, ta, te, gu, bn, kn, ml, pa, or, ur, en
"""
import re
import structlog
from config import settings

logger = structlog.get_logger()

# Unicode block ranges for Indian scripts
SCRIPT_DETECTORS = {
    "hi": (r"[\u0900-\u097F]", "Hindi (Devanagari)"),
    "mr": (r"[\u0900-\u097F]", "Marathi (Devanagari)"),  # Differentiate by vocabulary
    "gu": (r"[\u0A80-\u0AFF]", "Gujarati"),
    "pa": (r"[\u0A00-\u0A7F]", "Punjabi (Gurmukhi)"),
    "bn": (r"[\u0980-\u09FF]", "Bengali"),
    "ta": (r"[\u0B80-\u0BFF]", "Tamil"),
    "te": (r"[\u0C00-\u0C7F]", "Telugu"),
    "kn": (r"[\u0C80-\u0CFF]", "Kannada"),
    "ml": (r"[\u0D00-\u0D7F]", "Malayalam"),
    "or": (r"[\u0B00-\u0B7F]", "Odia"),
    "ur": (r"[\u0600-\u06FF]", "Urdu"),
    "en": (r"[a-zA-Z]{4,}", "English"),
}

SARVAM_LANGUAGE_CODES = {
    "hi": "hi-IN", "mr": "mr-IN", "ta": "ta-IN", "te": "te-IN",
    "gu": "gu-IN", "bn": "bn-IN", "kn": "kn-IN", "ml": "ml-IN",
    "pa": "pa-IN", "or": "or-IN", "ur": "ur-IN", "en": "en-IN",
}


def detect_script_language(text: str) -> str:
    """Detect primary language from script. Returns ISO 639-1 code."""
    if not text:
        return "hi"  # Default to Hindi
        
    # Check Devanagari script first
    if re.search(r"[\u0900-\u097F]", text):
        marathi_indicators = ["आहे", "झाले", "केले", "भाऊ", "नाही", "करून", "मराठी", "खर्च", "जमा", "रुपये"]
        if any(word in text for word in marathi_indicators) or any(word in text.lower() for word in ["ahe", "zal", "kel", "bhau"]):
            return "mr"
        return "hi"

    # Other script blocks
    for lang_code, (pattern, name) in SCRIPT_DETECTORS.items():
        if lang_code in ("hi", "mr"):
            continue
        if re.search(pattern, text):
            return lang_code
            
    return "hi"


def get_sarvam_language_code(lang: str) -> str:
    return SARVAM_LANGUAGE_CODES.get(lang, "hi-IN")


async def route_transcription(audio_bytes: bytes, detected_language: str) -> dict:
    """Route audio to appropriate ASR based on language."""
    lang_code = get_sarvam_language_code(detected_language)
    from ai.speech import _sarvam_transcribe, _whisper_transcribe

    # Use Sarvam for Indian languages, Whisper for English/others
    if detected_language != "en" and settings.SARVAM_API_KEY:
        return await _sarvam_transcribe(audio_bytes, lang_code)
    else:
        return await _whisper_transcribe(audio_bytes, detected_language)
