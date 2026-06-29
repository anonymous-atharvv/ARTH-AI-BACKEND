# backend/agents/financial_agent.py
"""
LangGraph stateful agent for processing each WhatsApp message.
Nodes handle the full pipeline from raw input to WhatsApp response.
"""
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from typing import TypedDict, Optional, Literal
from datetime import date, datetime
import structlog

from ai.vision import extract_from_receipt_image
from ai.speech import voice_to_transaction
from ai.nlu import classify_intent, extract_transaction_from_text, answer_financial_query
from services.analytics import AnalyticsService
from services.whatsapp import WhatsAppService
from services.conversation import ConversationStateManager, ConvState
from services.onboarding import handle_onboarding_step
from schemas.whatsapp import ExtractedTransaction
from schemas.transaction import TransactionType, PaymentMethod
from config import settings

logger = structlog.get_logger()

# ─── AGENT STATE DEFINITION ──────────────────────────────────────────────────
class AgentState(TypedDict):
    # Input
    user_phone: str
    user_id: Optional[str]
    user_language: str
    message_type: str           # IMAGE | AUDIO | TEXT | DOCUMENT
    raw_body: Optional[str]
    media_url: Optional[str]
    media_type: Optional[str]
    
    # Processing
    intent: Optional[str]
    intent_confidence: float
    extracted_transaction: Optional[dict]
    needs_clarification: bool
    clarification_message: Optional[str]
    
    # Financial data (loaded on demand)
    financial_summary: Optional[dict]
    
    # Output
    response_text: str
    response_sent: bool
    error: Optional[str]


# ─── NODE: Classify Message Type & Intent ────────────────────────────────────
async def classify_input(state: AgentState) -> AgentState:
    """Route based on message type (IMAGE/AUDIO/TEXT) and intent"""
    from database import AsyncSessionLocal
    
    media_type = state.get("media_type", "")
    phone = state["user_phone"]
    body = state.get("raw_body", "") or ""
    
    # Check conversation session state
    async with AsyncSessionLocal() as db:
        state_mgr = ConversationStateManager(db)
        session_data = await state_mgr.get_state(phone)
        conv_state = session_data.get("state", ConvState.IDLE)
        
        # 1. Onboarding turns
        if conv_state in (ConvState.ONBOARDING_NAME, ConvState.ONBOARDING_BUSINESS):
            await handle_onboarding_step(phone, body, session_data, db)
            state["intent"] = "ONBOARDING"
            state["intent_confidence"] = 1.0
            state["message_type"] = "TEXT"
            state["response_sent"] = True
            return state

        # 2. Awaiting transaction confirmation turn
        if conv_state == ConvState.AWAITING_CONFIRMATION:
            pending_tx = session_data.get("pending_transaction")
            if state_mgr.is_confirmation_yes(body):
                if pending_tx:
                    # Save transaction
                    from models.transaction import Transaction
                    new_tx = Transaction(
                        user_id=state["user_id"],
                        amount=pending_tx["amount"],
                        type=pending_tx["type"],
                        category_code=pending_tx["category_code"],
                        counterparty=pending_tx.get("counterparty"),
                        description=pending_tx.get("description", "Confirmed via WA"),
                        payment_method=pending_tx.get("payment_method", "cash"),
                        transaction_date=date.fromisoformat(pending_tx["transaction_date"]),
                        source="text",
                        raw_input=pending_tx.get("raw_text"),
                        confidence_score=pending_tx.get("confidence", 1.0),
                        verified=True
                    )
                    db.add(new_tx)
                    await db.commit()
                    
                    # Refresh Cache
                    analytics = AnalyticsService(db)
                    await analytics.refresh_cache(state["user_id"])
                    
                    # Construct ExtractedTransaction to format response
                    tx_obj = ExtractedTransaction(
                        amount=pending_tx["amount"],
                        type=TransactionType(pending_tx["type"]),
                        category_code=pending_tx["category_code"],
                        counterparty=pending_tx.get("counterparty"),
                        description=pending_tx.get("description", "Confirmed"),
                        payment_method=PaymentMethod(pending_tx.get("payment_method", "cash")),
                        transaction_date=date.fromisoformat(pending_tx["transaction_date"]),
                        confidence=1.0,
                        raw_text=pending_tx.get("raw_text")
                    )
                    state["response_text"] = build_success_response(tx_obj, state["user_language"])
                else:
                    state["response_text"] = "No pending transaction found."
                
                await state_mgr.reset(phone)
            elif state_mgr.is_confirmation_no(body):
                if state["user_language"] == "hi":
                    state["response_text"] = "Thik hai, cancel kar diya gaya. Naya transaction batayein."
                else:
                    state["response_text"] = "Okay, cancelled. Please send the correct transaction details."
                await state_mgr.reset(phone)
            else:
                if state["user_language"] == "hi":
                    state["response_text"] = "Kripya '1' (Haan) ya '2' (Nahi) likh kar batayein."
                else:
                    state["response_text"] = "Please reply with '1' (Yes) or '2' (No)."
            
            state["intent"] = "CONFIRMATION_RESPONSE"
            state["intent_confidence"] = 1.0
            state["message_type"] = "TEXT"
            return state

    # Normal routing
    if media_type and ("image/" in media_type or "image" in media_type):
        state["message_type"] = "IMAGE"
        state["intent"] = "TRANSACTION"
        state["intent_confidence"] = 0.9
        
    elif media_type and ("audio/" in media_type or "ogg" in media_type):
        state["message_type"] = "AUDIO"
        state["intent"] = "TRANSACTION"
        state["intent_confidence"] = 0.85
        
    else:
        state["message_type"] = "TEXT"
        if body:
            intent, confidence = await classify_intent(body)
            state["intent"] = intent
            state["intent_confidence"] = confidence
        else:
            state["intent"] = "HELP"
            state["intent_confidence"] = 1.0
            
    # Quick responses for GREETING and HELP
    if state["intent"] == "GREETING":
        if state["user_language"] == "hi":
            state["response_text"] = "Namaste! Main ArthAI hoon. Main aapke business ka hisaab rakh sakta hoon. Naya transaction bhejkar shuru karein!"
        else:
            state["response_text"] = "Hello! I am ArthAI. I can help manage your business accounts. Send me a transaction to get started!"
    elif state["intent"] == "HELP":
        if state["user_language"] == "hi":
            state["response_text"] = "Aap receipt ki photo bhej sakte hain, voice note bhej sakte hain (jaise: 'aaj ₹500 ki sale hui'), ya text likh sakte hain."
        else:
            state["response_text"] = "You can send receipt photos, voice notes (e.g., 'sold items for ₹500'), or text messages."
            
    logger.info("Input classified",
               message_type=state["message_type"],
               intent=state["intent"],
               confidence=state["intent_confidence"])
    return state


# ─── NODE: Extract Transaction from Media ─────────────────────────────────────
async def extract_transaction(state: AgentState) -> AgentState:
    """Extract structured transaction from image/audio/text"""
    if state.get("response_text") or state.get("response_sent"):
        return state
        
    try:
        if state["message_type"] == "IMAGE":
            extracted = await extract_from_receipt_image(
                state["media_url"], state["user_language"])
            
        elif state["message_type"] == "AUDIO":
            extracted = await voice_to_transaction(
                state["media_url"], state["user_language"])
            
        elif state["message_type"] == "TEXT":
            extracted = await extract_transaction_from_text(
                state["raw_body"], state["user_language"])
            
        state["extracted_transaction"] = extracted.model_dump(mode="json") if hasattr(extracted, "model_dump") else extracted.dict()
        logger.info("Transaction extracted",
                   amount=extracted.amount,
                   type=extracted.type,
                   confidence=extracted.confidence)
                   
    except Exception as e:
        logger.error("Transaction extraction failed", error=str(e))
        state["error"] = f"extraction_failed: {str(e)}"
        state["response_text"] = get_error_response(state["user_language"])
    
    return state


# ─── NODE: Validate & Check Confidence ────────────────────────────────────────
async def validate_extraction(state: AgentState) -> AgentState:
    """Check confidence. Low confidence → ask for user confirmation."""
    if state.get("error") or state.get("response_text") or state.get("response_sent"):
        return state
    
    tx_val = state["extracted_transaction"]
    tx = ExtractedTransaction(**tx_val) if isinstance(tx_val, dict) else tx_val
    
    if tx.confidence < settings.CONFIDENCE_THRESHOLD:
        state["needs_clarification"] = True
        amount_str = f"₹{tx.amount:,.0f}"
        
        CATEGORY_NAMES_HI = {
            "transport_fuel": "ईंधन/यातायात", "inventory": "माल/स्टॉक",
            "labor_wages": "मजदूरी", "sales_service": "सेवा आय",
            "sales_product": "बिक्री", "food_personal": "खाना",
            "mobile_internet": "मोबाइल", "utilities": "बिजली/पानी",
            "equipment": "उपकरण/मरम्मत", "rent_premises": "किराया",
            "other_expense": "अन्य खर्च", "other_income": "अन्य आय",
        }
        
        cat_name = CATEGORY_NAMES_HI.get(tx.category_code, tx.category_code.replace('_', ' ').title())
        type_word = "income" if tx.type == "income" else "expense"
        
        # Save state in WhatsApp session
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            state_mgr = ConversationStateManager(db)
            pending = {
                "amount": tx.amount,
                "type": tx.type.value,
                "category_code": tx.category_code,
                "counterparty": tx.counterparty,
                "description": tx.description,
                "payment_method": tx.payment_method.value,
                "transaction_date": tx.transaction_date.isoformat(),
                "confidence": tx.confidence,
                "raw_text": tx.raw_text
            }
            await state_mgr.set_state(
                state["user_phone"],
                ConvState.AWAITING_CONFIRMATION,
                pending_transaction=pending
            )

        if state["user_language"] == "hi":
            state["clarification_message"] = (
                f"Maine record kiya: {amount_str} {type_word}, category: {cat_name}.\n"
                f"Sahi hai?\n\n1️⃣ Haan, sahi hai ✅\n2️⃣ Nahi, galat hai ❌"
            )
        else:
            state["clarification_message"] = (
                f"I recorded: {amount_str} {type_word}, category: {cat_name}.\n"
                f"Is this correct?\n\n1️⃣ Yes ✅\n2️⃣ No ❌"
            )
    else:
        state["needs_clarification"] = False
    
    return state


# ─── NODE: Store Transaction ───────────────────────────────────────────────────
async def store_transaction(state: AgentState) -> AgentState:
    """Write validated transaction to PostgreSQL"""
    if state.get("error") or state.get("needs_clarification") or state.get("response_text") or state.get("response_sent"):
        return state
    
    from database import AsyncSessionLocal
    from models.transaction import Transaction
    
    tx_val = state["extracted_transaction"]
    tx = ExtractedTransaction(**tx_val) if isinstance(tx_val, dict) else tx_val
    
    async with AsyncSessionLocal() as db:
        new_tx = Transaction(
            user_id=state["user_id"],
            amount=tx.amount,
            type=tx.type,
            category_code=tx.category_code,
            counterparty=tx.counterparty,
            description=tx.description,
            payment_method=tx.payment_method,
            transaction_date=tx.transaction_date,
            source=state["message_type"].lower(),
            raw_input=tx.raw_text or state.get("raw_body"),
            confidence_score=tx.confidence,
            verified=True
        )
        db.add(new_tx)
        await db.commit()
        
        # Update analytics cache
        analytics = AnalyticsService(db)
        await analytics.refresh_cache(state["user_id"])
    
    # Build success response
    state["response_text"] = build_success_response(tx, state["user_language"])
    return state


# ─── NODE: Handle Financial Query ─────────────────────────────────────────────
async def handle_query(state: AgentState) -> AgentState:
    """Answer natural language financial question"""
    if state.get("response_text") or state.get("response_sent"):
        return state

    from database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        analytics = AnalyticsService(db)
        financial_data = await analytics.get_dashboard_summary(state["user_id"])
        weekly_data = await analytics.get_pnl_data(state["user_id"], "7d")
        
        full_data = {**financial_data, "weekly_breakdown": weekly_data}
    
    response = await answer_financial_query(
        state["raw_body"], full_data, state["user_language"])
    state["response_text"] = response
    return state


# ─── NODE: Generate Report ────────────────────────────────────────────────────
async def generate_report(state: AgentState) -> AgentState:
    """Generate Financial Passport PDF and send download link"""
    if state.get("response_text") or state.get("response_sent"):
        return state

    from agents.passport_generator import PassportGenerator
    from database import AsyncSessionLocal
    
    # Send "generating" message first
    wa = WhatsAppService()
    if state["user_language"] == "hi":
        generating_msg = "📊 Aapka Financial Passport generate ho raha hai... (kuch seconds)"
    else:
        generating_msg = "📊 Generating your Financial Passport... (a few seconds)"
    
    await wa.send_message(state["user_phone"], generating_msg)
    
    async with AsyncSessionLocal() as db:
        generator = PassportGenerator(db)
        result = await generator.generate(state["user_id"])
    
    if state["user_language"] == "hi":
        state["response_text"] = (
            f"✅ Aapka Financial Passport ready hai!\n\n"
            f"📄 Download: {result['download_url']}\n\n"
            f"🎯 ArthScore: {result['arthascore']}/900\n"
            f"💰 Estimated loan eligibility: ₹{result['loan_eligible']:,.0f}\n\n"
            f"Yeh document 30 din tak valid hai. Bank ya NBFC ko directly share kar sakte hain."
        )
    else:
        state["response_text"] = (
            f"✅ Your Financial Passport is ready!\n\n"
            f"📄 Download: {result['download_url']}\n\n"
            f"🎯 ArthScore: {result['arthascore']}/900\n"
            f"💰 Estimated loan eligibility: ₹{result['loan_eligible']:,.0f}\n\n"
            f"Valid for 30 days. Share directly with banks or NBFCs."
        )
    
    return state


# ─── NODE: Send WhatsApp Response ─────────────────────────────────────────────
async def send_response(state: AgentState) -> AgentState:
    """Send final response via Twilio WhatsApp API"""
    if state.get("response_sent"):
        return state

    wa = WhatsAppService()
    
    # Handle clarification vs regular response
    msg = state.get("clarification_message") or state.get("response_text", "")
    
    if msg:
        await wa.send_message(state["user_phone"], msg)
        state["response_sent"] = True
    
    return state


# ─── BUILD THE GRAPH ──────────────────────────────────────────────────────────
def build_financial_agent():
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("classify_input", classify_input)
    graph.add_node("extract_transaction", extract_transaction)
    graph.add_node("validate_extraction", validate_extraction)
    graph.add_node("store_transaction", store_transaction)
    graph.add_node("handle_query", handle_query)
    graph.add_node("generate_report", generate_report)
    graph.add_node("send_response", send_response)
    
    # Entry point
    graph.set_entry_point("classify_input")
    
    # Routing from classify_input
    def route_from_classify(state: AgentState) -> str:
        if state.get("response_sent"):
            return "handle_special_intent"
            
        intent = state.get("intent", "HELP")
        msg_type = state.get("message_type", "TEXT")
        
        if msg_type in ("IMAGE", "AUDIO"):
            return "extract_transaction"
        elif intent == "TRANSACTION":
            return "extract_transaction"
        elif intent == "QUERY":
            return "handle_query"
        elif intent in ("REPORT_REQUEST", "REPORT"):
            return "generate_report"
        else:  # GREETING, HELP, CONFIRMATION_YES, CONFIRMATION_NO, ONBOARDING, CONFIRMATION_RESPONSE
            return "handle_special_intent"
    
    graph.add_conditional_edges("classify_input", route_from_classify, {
        "extract_transaction": "extract_transaction",
        "handle_query": "handle_query",
        "generate_report": "generate_report",
        "handle_special_intent": "send_response",  # Quick responses bypass extraction
    })
    
    graph.add_edge("extract_transaction", "validate_extraction")
    graph.add_edge("validate_extraction", "store_transaction")
    graph.add_edge("store_transaction", "send_response")
    graph.add_edge("handle_query", "send_response")
    graph.add_edge("generate_report", "send_response")
    graph.add_edge("send_response", END)
    
    return graph.compile()


# ─── HELPER FUNCTIONS ─────────────────────────────────────────────────────────
def build_success_response(tx: ExtractedTransaction, language: str) -> str:
    amount_str = f"₹{tx.amount:,.0f}"
    
    CATEGORY_NAMES_HI = {
        "transport_fuel": "ईंधन/यातायात", "inventory": "माल/स्टॉक",
        "labor_wages": "मजदूरी", "sales_service": "सेवा आय",
        "sales_product": "बिक्री", "food_personal": "खाना",
        "mobile_internet": "मोबाइल", "utilities": "बिजली/पानी",
        "equipment": "उपकरण/मरम्मत", "rent_premises": "किराया",
        "other_expense": "अन्य खर्च", "other_income": "अन्य आय",
    }
    
    cat_name = CATEGORY_NAMES_HI.get(tx.category_code, tx.category_code)
    type_word = "आय" if tx.type == "income" else "खर्च"
    method = "UPI" if tx.payment_method == "upi" else "नकद"
    
    if language == "hi":
        return (
            f"✅ Record ho gaya!\n\n"
            f"💰 {amount_str} {type_word}\n"
            f"📂 {cat_name}\n"
            f"💳 {method}\n"
            f"📅 {tx.transaction_date.strftime('%d %B')}\n\n"
            f"_'Profit kya hai?' likhein apna weekly summary dekhne ke liye._"
        )
    else:
        return (
            f"✅ Recorded!\n\n"
            f"💰 {amount_str} {tx.type.value.title() if hasattr(tx.type, 'value') else str(tx.type).title()}\n"
            f"📂 {tx.category_code.replace('_', ' ').title()}\n"
            f"💳 {tx.payment_method.value.upper() if hasattr(tx.payment_method, 'value') else str(tx.payment_method).upper()}\n"
            f"📅 {tx.transaction_date.strftime('%B %d')}\n\n"
            f"_Type 'profit kya hai?' to see your weekly summary._"
        )

def get_error_response(language: str) -> str:
    if language == "hi":
        return "😕 Maafi chahiye, aapka message samajh nahi aaya. Kripya dobara bhejein ya likhkar batayein kya transaction tha."
    return "😕 Sorry, I couldn't understand that. Please try again or type the transaction details."
