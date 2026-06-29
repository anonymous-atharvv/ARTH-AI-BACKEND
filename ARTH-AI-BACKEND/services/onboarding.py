from services.whatsapp import WhatsAppService
from services.conversation import ConversationStateManager, ConvState

WELCOME_MESSAGE = """🙏 *Namaste! Main ArthAI hoon.*

Main aapka *financial assistant* hoon. Aapke business ka hisaab-kitaab rakhna, loan ke liye document banana — sab kuch WhatsApp pe.

Pehle mujhe batayein:
👤 *Aapka naam kya hai?*

_(Example: "Raju Kumar")_"""

LANGUAGE_PROMPT = """Great! Aap kaun si language prefer karte hain?

1️⃣ *Hindi* — मुझसे हिंदी में बात करें
2️⃣ *English* — Talk to me in English
3️⃣ *Marathi* — मराठीत बोला"""

BUSINESS_PROMPT_HI = """{name} ji, shukriya! 🙏

Ab batayein aapka business kya hai?
_(Example: "Auto-rickshaw", "Kirana dukaan", "Darzi", "Sabzi wala")_"""

READY_MESSAGE_HI = """✅ *Setup complete!*

Ab aap yeh kar sakte hain:
📸 Receipt ka *photo* bhejein → Main record kar lunga
🎤 *Voice note* mein batayein → "Aaj ₹950 ki sawari mili"
✍️ *Text* likhein → "Ramesh ko ₹500 diye"

Pehle transaction try karen! 👆"""

async def handle_onboarding_step(phone: str, text: str, current_state: dict, db):
    wa = WhatsAppService()
    state_mgr = ConversationStateManager(db)
    context = current_state.get("context", {})

    if current_state["state"] == ConvState.ONBOARDING_NAME:
        # User sent their name
        name = text.strip().title()
        context["name"] = name

        await state_mgr.set_state(phone, ConvState.ONBOARDING_BUSINESS,
                                  context=context)

        await wa.send_message(phone, BUSINESS_PROMPT_HI.format(name=name))

    elif current_state["state"] == ConvState.ONBOARDING_BUSINESS:
        # User sent their business type
        business_type = text.strip()
        context["business_type"] = business_type

        # Save to user profile
        from models.user import User
        from sqlalchemy import update as sql_update
        await db.execute(
            sql_update(User)
            .where(User.phone_number == phone)
            .values(
                name=context.get("name"),
                business_type=business_type,
                preferred_language="hi",
                onboarding_complete=True
            )
        )
        await db.commit()

        await state_mgr.reset(phone)
        await wa.send_message(phone, READY_MESSAGE_HI)
