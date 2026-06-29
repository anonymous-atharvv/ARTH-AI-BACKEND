# backend/ai/response_generator.py
"""Multilingual WhatsApp response templates."""

RESPONSES = {
    "transaction_recorded": {
        "hi": "✅ Transaction record hua!\n💰 {type}: ₹{amount:,.0f}\n📂 {category}\n📝 {description}\n\nKya yeh sahi hai? (Haan/Nahi)",
        "en": "✅ Transaction recorded!\n💰 {type}: ₹{amount:,.0f}\n📂 {category}\n📝 {description}\n\nIs this correct? (Yes/No)",
    },
    "greeting": {
        "hi": "🙏 Namaste! Main ArthAI hoon.\n\nAap mujhe bhej sakte hain:\n📸 Receipt ki photo\n🎤 Voice note\n✍️ Text message\n\nAur main aapki kamai aur kharche track karunga!",
        "en": "🙏 Hello! I'm ArthAI.\n\nSend me:\n📸 Receipt photos\n🎤 Voice notes\n✍️ Text messages\n\nI'll track your income & expenses!",
    },
    "score_summary": {
        "hi": "📊 Aapka ArthScore: {score}/900\n🏆 Grade: {grade}\n💰 Loan Eligibility: ₹{loan:,}\n\n{insight}",
        "en": "📊 Your ArthScore: {score}/900\n🏆 Grade: {grade}\n💰 Loan Eligibility: ₹{loan:,}\n\n{insight}",
    },
    "confirmed": {
        "hi": "✅ Theek hai! Transaction save ho gaya.",
        "en": "✅ Great! Transaction saved.",
    },
    "cancelled": {
        "hi": "❌ Transaction cancel kar diya. Dobara bhejein.",
        "en": "❌ Transaction cancelled. Please resend.",
    },
}

def get_response(key: str, lang: str = "hi", **kwargs) -> str:
    template = RESPONSES.get(key, {}).get(lang, RESPONSES.get(key, {}).get("en", ""))
    return template.format(**kwargs) if template else f"[{key}]"
