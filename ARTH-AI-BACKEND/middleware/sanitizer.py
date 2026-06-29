# backend/middleware/sanitizer.py
import re


def sanitize_text(text: str, max_length: int = 1000) -> str:
    """Remove potential injection vectors and limit length."""
    if not text:
        return ""
    # Remove null bytes
    text = text.replace("\x00", "")
    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Limit length
    return text[:max_length]


def sanitize_phone(phone: str) -> str:
    """Ensure phone is E.164 format."""
    # Keep only + and digits
    cleaned = re.sub(r"[^\d+]", "", phone)
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    if not re.match(r"^\+\d{10,15}$", cleaned):
        raise ValueError(f"Invalid phone number format: {phone}")
    return cleaned
