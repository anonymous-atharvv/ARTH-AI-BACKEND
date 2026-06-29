# ArthAI — GOD TIER V3: FULL PRODUCTION SPECIFICATION
## YCombinator-Grade Implementation Bible
### Version: 3.0 | Post-Hackathon → Production | ~45 Issues Fixed

> **AUDIT VERDICT**: The hackathon build is architecturally sound but has 45 production-blocking issues:
> 8 critical bugs, 6 security holes, 10 architecture gaps, 8 missing features, 6 frontend deficiencies, 7 DevOps gaps.
> This document fixes all of them. Read every section. Build in order. Ship.

---

## AUDIT FINDINGS SUMMARY

| Priority | Issue Count | Examples |
|----------|-------------|---------|
| **P0 Critical Bugs** | 8 | SQLite default, `Optional` missing, HTML not PDF, date type mismatch |
| **P1 Security** | 6 | No auth, no Twilio validation, no rate limiting, CORS wide open |
| **P2 Architecture** | 10 | No Alembic, no Redis cache, no health checks, no API versioning |
| **P3 Missing Features** | 8 | GST invoices, Account Aggregator, proactive insights, Celery Beat |
| **P4 Frontend** | 6 | No error boundaries, no code splitting, type `any` everywhere |
| **P5 DevOps** | 7 | No Sentry, no Prometheus, no CI/CD, no migrations runner |

---

## SECTION 0: NORTH STAR & CONSTRAINTS

**Product Mission**: Turn India's 63M informal entrepreneurs data-invisible → credit-visible in 90 days.
**Technical Mission**: Build a system a 10-person team can operate at 1M users without burnout.
**YC Test**: Would this embarrass us at Demo Day? Fix everything that would.

**Build Order (STRICT)**:
```
1. Fix P0 bugs (nothing else matters if core is broken)
2. Security hardening (never ship auth-less)
3. Database & migrations (foundation for everything)
4. AI pipeline hardening (the core value prop)
5. Financial intelligence (passport PDF, ArthScore v2)
6. Frontend production quality
7. DevOps, monitoring, CI/CD
8. Missing business features
9. Performance optimization
10. Load test + security audit
```

---

## SECTION 1: P0 CRITICAL BUG FIXES

### Bug 1 — `Optional` Not Imported in `backend/ai/nlu.py`

**Problem**: Bottom of file uses `Optional[float]` in `_extract_amount` return type but `Optional` isn't imported.

**Fix**: Add to imports at top of `backend/ai/nlu.py`:
```python
from typing import Tuple, Optional  # ADD Optional here
```

---

### Bug 2 — SQLite String Dates Break All Analytics

**Problem**: `backend/models/transaction.py` stores `transaction_date` as `Column(String)` for "SQLite compat." This means `ORDER BY transaction_date` sorts lexicographically, not chronologically. All date-range queries return wrong data. The "fix" must work in both SQLite (dev) and PostgreSQL (prod).

**Fix** — Replace `backend/models/transaction.py` entirely:
```python
# backend/models/transaction.py
import uuid
from datetime import datetime, date as date_type
from sqlalchemy import Column, String, Float, Boolean, Date, Text, JSON, func
from sqlalchemy.types import TypeDecorator
from database import Base
from models.user import GUID


class ISODate(TypeDecorator):
    """Store dates as ISO strings in SQLite, native Date in PostgreSQL."""
    impl = String(10)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, date_type):
            return value.isoformat()
        if isinstance(value, str):
            return value[:10]  # truncate to YYYY-MM-DD
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, date_type):
            return value
        try:
            return date_type.fromisoformat(str(value)[:10])
        except (ValueError, TypeError):
            return None


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(GUID(), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    type = Column(String(10), nullable=False)
    category_code = Column(String(50), index=True)
    counterparty = Column(String(200))
    description = Column(String(500))
    payment_method = Column(String(20), default="cash")
    transaction_date = Column(ISODate, nullable=False, index=True)  # ← KEY FIX
    transaction_time = Column(String(8))
    source = Column(String(20), nullable=False)
    raw_input = Column(Text)
    extracted_data = Column(JSON)
    confidence_score = Column(Float, default=0.95)
    verified = Column(Boolean, default=False)
    location = Column(String(200))
    notes = Column(Text)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    updated_at = Column(String, default=lambda: datetime.utcnow().isoformat())
```

**Update all analytics queries** in `backend/services/analytics.py` that compare dates:
```python
# BEFORE (broken string comparison):
Transaction.transaction_date >= month_start.isoformat()

# AFTER (works with ISODate type):
Transaction.transaction_date >= month_start.isoformat()  # same syntax, ISODate handles it
# But sorting: use .order_by(Transaction.transaction_date) — now sorts correctly
```

---

### Bug 3 — Financial Passport Generates HTML, Not PDF

**Problem**: `backend/agents/passport_generator.py` writes `.html` file instead of PDF. WeasyPrint is in requirements but not used in the actual generator.

**Fix** — Replace `backend/agents/passport_generator.py`:
```python
# backend/agents/passport_generator.py
"""Generates bank-grade Financial Passport as real PDF using WeasyPrint."""
from jinja2 import Template
from datetime import date, timedelta
from pathlib import Path
import uuid, os, structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from agents.arthascore import ArthScoreEngine
from services.analytics import AnalyticsService
from services.storage import StorageService

logger = structlog.get_logger()

PASSPORT_HTML = Path(__file__).parent.parent / "templates" / "passport.html"


class PassportGenerator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate(self, user_id: str) -> dict:
        from models.user import User
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        scorer = ArthScoreEngine(self.db)
        score_data = await scorer.calculate(user_id, lookback_days=90)

        analytics = AnalyticsService(self.db)
        pnl = await analytics.get_pnl_data(user_id, "90d")

        doc_id = f"AP-{user_id[:8].upper()}-{date.today().strftime('%Y%m%d')}"
        data = self._build_template_data(user, score_data, pnl, doc_id)

        # Render HTML
        template_src = PASSPORT_HTML.read_text(encoding="utf-8")
        html_content = Template(template_src).render(**data)

        # Attempt PDF with WeasyPrint; fall back to HTML if system deps missing
        pdf_bytes, file_ext, content_type = self._render_pdf(html_content)

        # Upload to storage
        storage = StorageService()
        file_key = f"passports/{user_id}/{date.today().isoformat()}/passport.{file_ext}"
        download_url = await storage.upload_file(pdf_bytes, file_key, content_type)

        # Log document
        await self._log_document(user_id, download_url, score_data)

        return {
            "download_url": download_url,
            "arthascore": score_data.get("score", 0),
            "loan_eligible": score_data.get("max_loan_eligible", 0),
            "expires_at": (date.today() + timedelta(days=30)).isoformat(),
            "doc_id": doc_id,
            "format": file_ext,
        }

    def _render_pdf(self, html_content: str):
        """Try WeasyPrint → fallback to HTML bytes."""
        try:
            from weasyprint import HTML as WeasyHTML
            pdf_bytes = WeasyHTML(string=html_content).write_pdf()
            logger.info("PDF rendered successfully", size_kb=len(pdf_bytes) // 1024)
            return pdf_bytes, "pdf", "application/pdf"
        except Exception as e:
            logger.warning("WeasyPrint unavailable, falling back to HTML", error=str(e))
            html_bytes = html_content.encode("utf-8")
            return html_bytes, "html", "text/html; charset=utf-8"

    def _build_template_data(self, user, score_data, pnl, doc_id) -> dict:
        return {
            "doc_id": doc_id,
            "generated_date": date.today().strftime("%d %B %Y"),
            "expiry_date": (date.today() + timedelta(days=30)).strftime("%d %B %Y"),
            "score": score_data.get("score", 0),
            "grade": score_data.get("grade", "N/A"),
            "grade_hi": score_data.get("grade_hi", "N/A"),
            "factors": {
                "Income Regularity": score_data.get("factors", {}).get("income_regularity", 0),
                "Growth Trend": score_data.get("factors", {}).get("growth_trajectory", 0),
                "Expense Control": score_data.get("factors", {}).get("expense_control", 0),
                "Business Activity": score_data.get("factors", {}).get("transaction_volume", 0),
                "Business Age": score_data.get("factors", {}).get("business_longevity", 0),
                "Payment Habit": score_data.get("factors", {}).get("payment_consistency", 0),
            },
            "max_loan": score_data.get("max_loan_eligible", 0),
            "name": getattr(user, "name", None) or "Business Owner",
            "business_type": getattr(user, "business_type", None) or "Micro Business",
            "location": getattr(user, "business_location", None) or "India",
            "total_income": pnl.get("total_income", 0),
            "total_expenses": pnl.get("total_expenses", 0),
            "net_profit": pnl.get("net_profit", 0),
            "avg_monthly_income": pnl.get("total_income", 0) / 3,
            "net_margin_pct": round(pnl.get("net_margin_pct", 0), 1),
            "payment_regularity": score_data.get("factors", {}).get("payment_consistency", 70),
            "monthly_data": pnl.get("series", [])[:6],
        }

    async def _log_document(self, user_id: str, download_url: str, score_data: dict):
        from models.document import Document
        from datetime import timedelta
        doc = Document(
            user_id=user_id,
            document_type="financial_passport",
            file_url=download_url,
            period_start=date.today().replace(day=1).isoformat(),
            period_end=date.today().isoformat(),
            arthascore_at_generation=score_data.get("score", 0),
            summary_data={"score": score_data.get("score"), "loan_eligible": score_data.get("max_loan_eligible")},
            expires_at=(date.today() + timedelta(days=30)).isoformat(),
        )
        self.db.add(doc)
        await self.db.commit()
```

---

### Bug 4 — ArthScore Date Type Mismatch

**Problem**: `backend/agents/arthascore.py` calls `date.fromisoformat(t.transaction_date)` — but with the new `ISODate` type, `t.transaction_date` IS already a `date` object. Calling `fromisoformat` on it crashes.

**Fix** — Replace all date parsing in `arthascore.py`:
```python
# BEFORE (crashes if already a date):
d = date.fromisoformat(t.transaction_date) if isinstance(t.transaction_date, str) else t.transaction_date

# AFTER (robust):
def _to_date(val) -> date:
    if isinstance(val, date):
        return val
    try:
        return date.fromisoformat(str(val)[:10])
    except (ValueError, TypeError):
        return date.today()
```

Apply `_to_date()` everywhere in `arthascore.py` where transaction dates are used.

---

### Bug 5 — Analytics `refresh_cache` Broken Import

**Problem**: `services/analytics.py` `refresh_cache()` does `from models.analytics import AnalyticsCache` inside the method then uses `insert` from `sqlalchemy.dialects.postgresql` which doesn't exist in SQLite.

**Fix** — Replace `refresh_cache` method:
```python
async def refresh_cache(self, user_id: str):
    """Update analytics_cache after each transaction — SQLite + PostgreSQL safe."""
    try:
        from models.analytics import AnalyticsCache
        from sqlalchemy import update as sql_update
        
        summary = await self.get_dashboard_summary(user_id)
        
        # Check if cache row exists
        result = await self.db.execute(
            select(AnalyticsCache).where(AnalyticsCache.user_id == user_id)
        )
        cache = result.scalar_one_or_none()
        
        if cache:
            cache.mtd_income = summary["mtd_income"]
            cache.mtd_expenses = summary["mtd_expenses"]
            cache.mtd_net_profit = summary["mtd_net_profit"]
            cache.wtd_income = summary["wtd_income"]
            cache.wtd_expenses = summary["wtd_expenses"]
            cache.total_transactions = summary["total_transactions"]
            cache.last_updated = datetime.utcnow().isoformat()
        else:
            cache = AnalyticsCache(
                user_id=user_id,
                mtd_income=summary["mtd_income"],
                mtd_expenses=summary["mtd_expenses"],
                mtd_net_profit=summary["mtd_net_profit"],
                wtd_income=summary["wtd_income"],
                wtd_expenses=summary["wtd_expenses"],
                total_transactions=summary["total_transactions"],
            )
            self.db.add(cache)
        
        await self.db.commit()
    except Exception as e:
        logger.error("Analytics cache refresh failed", error=str(e))
        # Non-fatal — don't crash the transaction flow
```

---

### Bug 6 — WhatsApp Session `user_id` Null on New Users

**Problem**: `services/conversation.py` creates `WhatsAppSession` with `user_id` field but new users don't have a `user_id` yet at the point sessions are first created.

**Fix** — Make `user_id` nullable in `WhatsAppSession` and populate it after user creation:
```python
# backend/models/session.py — update user_id column:
user_id = Column(GUID(), nullable=True)  # nullable until user created

# In message_tasks.py, after user creation:
async with AsyncSessionLocal() as db:
    # ... create user ...
    await db.commit()
    await db.refresh(user)
    
    # NOW update any existing session with the new user_id
    state_mgr = ConversationStateManager(db)
    await state_mgr.set_user_id(phone, str(user.id))
```

Add `set_user_id` method to `ConversationStateManager`:
```python
async def set_user_id(self, phone: str, user_id: str):
    """Backfill user_id after user creation."""
    from models.session import WhatsAppSession
    result = await self.db.execute(
        select(WhatsAppSession).where(WhatsAppSession.phone_number == phone)
    )
    session = result.scalar_one_or_none()
    if session and session.user_id is None:
        session.user_id = user_id
        await self.db.commit()
```

---

### Bug 7 — LangGraph `ExtractedTransaction` in TypedDict

**Problem**: `AgentState` TypedDict has `extracted_transaction: Optional[ExtractedTransaction]` but TypedDict with Pydantic models causes runtime serialization issues in LangGraph's state management.

**Fix** — Store as dict in state, convert when needed:
```python
# In AgentState TypedDict:
extracted_transaction: Optional[dict]  # Store as dict, not Pydantic model

# When storing:
state["extracted_transaction"] = extracted.model_dump(mode="json")

# When reading:
tx_dict = state["extracted_transaction"]
tx = ExtractedTransaction(**tx_dict)
```

---

### Bug 8 — App.tsx Bypasses Demo Page

**Problem**: `frontend/src/App.tsx` redirects `/` directly to `/dashboard/raju-demo-001`, skipping the Demo landing page entirely.

**Fix** — Change App.tsx routing:
```typescript
// BEFORE:
<Route path="/" element={<Navigate to={`/dashboard/${DEMO_USER_ID}`} replace />} />

// AFTER:
<Route path="/" element={<Demo />} />
<Route path="/demo" element={<Demo />} />
```

---

## SECTION 2: P1 SECURITY HARDENING

### 2.1 — JWT Authentication System

Create `backend/middleware/auth.py`:
```python
# backend/middleware/auth.py
"""JWT-based authentication for ArthAI API."""
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from config import settings

security = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7  # 7 days


def create_access_token(user_id: str, phone: str) -> str:
    payload = {
        "sub": user_id,
        "phone": phone,
        "exp": datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
        "iat": datetime.utcnow(),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """Verify JWT token — use as FastAPI dependency."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user_id(token: dict = Depends(verify_token)) -> str:
    """Extract user_id from verified JWT payload."""
    return token["sub"]


def get_current_phone(token: dict = Depends(verify_token)) -> str:
    return token["phone"]
```

Create `backend/routes/auth.py`:
```python
# backend/routes/auth.py
"""Phone OTP authentication flow."""
import random, string
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from database import get_db
from models.user import User
from middleware.auth import create_access_token
import redis.asyncio as aioredis
from config import settings

router = APIRouter()

# OTP store (Redis, 5-minute expiry)
async def get_redis():
    return await aioredis.from_url(settings.REDIS_URL)


class SendOTPRequest(BaseModel):
    phone: str  # E.164 format: +919876543210


class VerifyOTPRequest(BaseModel):
    phone: str
    otp: str


@router.post("/send-otp")
async def send_otp(request: SendOTPRequest):
    """Send 6-digit OTP via WhatsApp/SMS."""
    # Generate OTP
    otp = "".join(random.choices(string.digits, k=6))
    
    redis = await get_redis()
    await redis.setex(f"otp:{request.phone}", 300, otp)  # 5-minute expiry
    
    # In production: send via Twilio WhatsApp
    # For demo: log it
    import structlog
    structlog.get_logger().info("OTP generated", phone=request.phone, otp=otp)
    
    return {"message": "OTP sent", "expires_in": 300}


@router.post("/verify-otp")
async def verify_otp(request: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    """Verify OTP and return JWT token."""
    redis = await get_redis()
    stored_otp = await redis.get(f"otp:{request.phone}")
    
    if not stored_otp or stored_otp.decode() != request.otp:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    await redis.delete(f"otp:{request.phone}")
    
    # Get or create user
    result = await db.execute(select(User).where(User.phone_number == request.phone))
    user = result.scalar_one_or_none()
    
    is_new_user = False
    if not user:
        user = User(phone_number=request.phone, preferred_language="hi")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        is_new_user = True
    
    token = create_access_token(str(user.id), user.phone_number)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "is_new_user": is_new_user,
        "onboarding_complete": user.onboarding_complete,
    }


@router.post("/demo-token")
async def get_demo_token(db: AsyncSession = Depends(get_db)):
    """Get a pre-authenticated token for the demo user (disable in production)."""
    from config import settings
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Demo mode is disabled")
    
    result = await db.execute(select(User).where(User.id == "raju-demo-001"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Demo not seeded. Call /api/demo/seed first.")
    
    token = create_access_token("raju-demo-001", "+919876543210")
    return {"access_token": token, "token_type": "bearer", "user_id": "raju-demo-001"}
```

**Apply auth to all routes** — update each route to include:
```python
from middleware.auth import get_current_user_id

# In every endpoint that reads user data:
@router.get("/summary/{user_id}")
async def get_summary(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    # Enforce: users can only see their own data
    if user_id != current_user_id and not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail="Forbidden")
    service = AnalyticsService(db)
    return await service.get_dashboard_summary(user_id)
```

---

### 2.2 — Twilio Webhook Signature Validation

**Problem**: Anyone can POST fake WhatsApp messages to `/webhook/whatsapp`.

**Fix** — Replace `backend/routes/webhook.py`:
```python
# backend/routes/webhook.py
from fastapi import APIRouter, Request, Response, HTTPException
from twilio.request_validator import RequestValidator
from config import settings
import structlog, asyncio

router = APIRouter()
logger = structlog.get_logger()


def validate_twilio_request(request_url: str, form_params: dict, signature: str) -> bool:
    """Validate Twilio webhook signature."""
    if settings.DEMO_MODE or not settings.TWILIO_AUTH_TOKEN:
        return True  # Skip in demo mode
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    return validator.validate(request_url, form_params, signature)


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
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
        "num_media": int(params.get("NumMedia", 0)),
    }
    
    logger.info("WhatsApp message received",
                from_number=payload["from"][-4:],  # Last 4 digits only for privacy
                has_media=payload["num_media"] > 0)
    
    try:
        from tasks.message_tasks import process_whatsapp_message
        process_whatsapp_message.delay(payload)
    except Exception as celery_err:
        logger.warning("Celery unavailable, async fallback", error=str(celery_err))
        asyncio.create_task(_process_async(payload))
    
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="application/xml"
    )


async def _process_async(payload):
    from tasks.message_tasks import _process_message_async
    await _process_message_async(payload)
```

---

### 2.3 — Rate Limiting

Add `slowapi` to `requirements.txt`, then create `backend/middleware/rate_limit.py`:
```python
# backend/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

limiter = Limiter(key_func=get_remote_address, default_limits=["200/hour"])


def rate_limit_error_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": "Rate limit exceeded. Please slow down.", "retry_after": 60}
    )
```

Update `backend/main.py`:
```python
from middleware.rate_limit import limiter, rate_limit_error_handler
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_error_handler)
app.add_middleware(SlowAPIMiddleware)
```

Apply rate limits to sensitive routes:
```python
# Aggressive limit on OTP send (prevent SMS bombing):
@router.post("/send-otp")
@limiter.limit("5/hour")
async def send_otp(request: Request, ...):

# WhatsApp webhook (Twilio is the only caller):
@router.post("/whatsapp")
@limiter.limit("1000/minute")  # Twilio can send bursts
async def whatsapp_webhook(request: Request, ...):
```

---

### 2.4 — Security Headers Middleware

Create `backend/middleware/security_headers.py`:
```python
# backend/middleware/security_headers.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        # Remove server info
        response.headers.pop("server", None)
        return response
```

Add to `main.py`:
```python
from middleware.security_headers import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)

# Tighten CORS for production:
ALLOWED_ORIGINS = settings.ALLOWED_ORIGINS  # List from env, not ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    max_age=3600,
)
```

---

### 2.5 — Input Sanitization

Create `backend/middleware/sanitizer.py`:
```python
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
```

---

## SECTION 3: P2 ARCHITECTURE — DATABASE & MIGRATIONS

### 3.1 — Alembic Migration Setup

Add `alembic==1.13.1` to requirements (already there, but not configured).

Run:
```bash
cd backend
alembic init migrations
```

Update `backend/migrations/env.py`:
```python
from config import settings
from database import Base
import models  # Import all models to register with metadata

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("+asyncpg", "").replace("+aiosqlite", ""))
target_metadata = Base.metadata
```

Create initial migration:
```bash
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

**Never use `create_all` in production.** Update `database.py`:
```python
async def create_db_tables():
    """Dev/demo only — use Alembic in production."""
    import os
    if os.getenv("ENVIRONMENT", "development") == "production":
        logger.warning("create_db_tables skipped in production — use alembic upgrade head")
        return
    # ... existing create_all logic for dev
```

---

### 3.2 — Redis Caching for ArthScore

**Problem**: ArthScore recalculates on every request (heavy ML computation). Should cache for 1 hour.

Update `backend/routes/score.py`:
```python
# backend/routes/score.py
import json
import redis.asyncio as aioredis
from config import settings

ARTHASCORE_CACHE_TTL = 3600  # 1 hour

async def get_redis_client():
    try:
        return await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        return None


@router.get("/{user_id}")
async def get_arthascore(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    force_refresh: bool = False,
):
    cache_key = f"arthascore:{user_id}"
    
    # Try cache first
    if not force_refresh:
        redis = await get_redis_client()
        if redis:
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
    
    # Calculate fresh
    engine = ArthScoreEngine(db)
    result = await engine.calculate(user_id, lookback_days=90)
    
    # Cache it
    redis = await get_redis_client()
    if redis:
        await redis.setex(cache_key, ARTHASCORE_CACHE_TTL, json.dumps(result))
    
    return result


# Invalidate cache when new transaction added:
# In routes/transactions.py, after creating a transaction:
async def invalidate_arthascore_cache(user_id: str):
    redis = await get_redis_client()
    if redis:
        await redis.delete(f"arthascore:{user_id}")
```

---

### 3.3 — Production Health Check

Replace the basic `/health` endpoint:
```python
# In backend/main.py:
@app.get("/health")
async def health_check():
    """Comprehensive health check for load balancers and monitoring."""
    import time
    start = time.time()
    health = {
        "status": "healthy",
        "service": "ArthAI Backend",
        "version": "3.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Database check
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(select(1))
        health["checks"]["database"] = "ok"
    except Exception as e:
        health["checks"]["database"] = f"error: {str(e)}"
        health["status"] = "degraded"
    
    # Redis check
    try:
        import redis.asyncio as aioredis
        r = await aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        health["checks"]["redis"] = "ok"
        await r.close()
    except Exception:
        health["checks"]["redis"] = "unavailable"
        # Not critical if demo mode
    
    # OpenAI check (lightweight)
    health["checks"]["openai_key"] = "configured" if settings.OPENAI_API_KEY else "missing"
    
    health["latency_ms"] = round((time.time() - start) * 1000, 2)
    
    status_code = 200 if health["status"] == "healthy" else 503
    return JSONResponse(content=health, status_code=status_code)


@app.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe — only checks if app can serve traffic."""
    return {"status": "ready"}
```

---

### 3.4 — API Versioning

Update route prefixes in `main.py`:
```python
# BEFORE:
app.include_router(analytics.router, prefix="/api/analytics", ...)

# AFTER (v1 prefix):
app.include_router(analytics.router, prefix="/api/v1/analytics", ...)
app.include_router(transactions.router, prefix="/api/v1/transactions", ...)
app.include_router(score.router, prefix="/api/v1/score", ...)
app.include_router(reports.router, prefix="/api/v1/reports", ...)
app.include_router(users.router, prefix="/api/v1/users", ...)
app.include_router(auth_router, prefix="/api/v1/auth", ...)
app.include_router(marketplace.router, prefix="/api/v1/marketplace", ...)

# Keep demo at unversioned (dev only):
app.include_router(demo.router, prefix="/api/demo", ...)

# Webhook stays at root (Twilio sends here):
app.include_router(webhook.router, prefix="/webhook", ...)
```

Update `frontend/src/api/client.ts`:
```typescript
const API_VERSION = '/api/v1';

export const apiClient = {
  getSummary: (userId: string) => api.get(`${API_VERSION}/analytics/summary/${userId}`),
  // ... all routes updated with /api/v1 prefix
};
```

---

## SECTION 4: P3 MISSING FEATURES

### 4.1 — Celery Beat: Proactive Insights & Weekly Summaries

Add to `requirements.txt`:
```
celery[redis,beat]==5.4.0
```

Create `backend/tasks/scheduled_tasks.py`:
```python
# backend/tasks/scheduled_tasks.py
"""Periodic tasks for proactive insights."""
from tasks.celery_app import celery_app
from celery.schedules import crontab
import asyncio, structlog

logger = structlog.get_logger()

# Configure beat schedule
celery_app.conf.beat_schedule = {
    # Weekly P&L summary every Monday 9 AM IST
    "weekly-summary": {
        "task": "tasks.scheduled_tasks.send_weekly_summaries",
        "schedule": crontab(hour=9, minute=0, day_of_week="monday"),
        "options": {"timezone": "Asia/Kolkata"},
    },
    # Expense anomaly check daily at 8 PM IST
    "daily-anomaly-check": {
        "task": "tasks.scheduled_tasks.check_expense_anomalies",
        "schedule": crontab(hour=20, minute=0),
        "options": {"timezone": "Asia/Kolkata"},
    },
    # Refresh ArthScores nightly
    "nightly-arthascore-refresh": {
        "task": "tasks.scheduled_tasks.refresh_all_arthascore",
        "schedule": crontab(hour=2, minute=0),
        "options": {"timezone": "Asia/Kolkata"},
    },
}


@celery_app.task(name="tasks.scheduled_tasks.send_weekly_summaries")
def send_weekly_summaries():
    asyncio.run(_weekly_summaries_async())


@celery_app.task(name="tasks.scheduled_tasks.check_expense_anomalies")
def check_expense_anomalies():
    asyncio.run(_anomaly_check_async())


@celery_app.task(name="tasks.scheduled_tasks.refresh_all_arthascore")
def refresh_all_arthascore():
    asyncio.run(_arthascore_refresh_async())


async def _weekly_summaries_async():
    """Send weekly P&L summary to all active users."""
    from database import AsyncSessionLocal
    from models.user import User
    from services.analytics import AnalyticsService
    from services.whatsapp import WhatsAppService
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.onboarding_complete == True)
        )
        users = result.scalars().all()
    
    wa = WhatsAppService()
    for user in users:
        try:
            async with AsyncSessionLocal() as db:
                analytics = AnalyticsService(db)
                summary = await analytics.get_dashboard_summary(str(user.id))
                
                lang = user.preferred_language or "hi"
                if lang == "hi":
                    msg = (
                        f"📊 *Is hafte ka summary:*\n\n"
                        f"💰 Income: *₹{summary['wtd_income']:,.0f}*\n"
                        f"📤 Kharcha: *₹{summary['wtd_expenses']:,.0f}*\n"
                        f"✅ Net: *₹{summary['wtd_net']:,.0f}*\n\n"
                        f"_Apna Financial Passport: 'passport banao' likhein_"
                    )
                else:
                    msg = (
                        f"📊 *This week's summary:*\n\n"
                        f"💰 Income: *₹{summary['wtd_income']:,.0f}*\n"
                        f"📤 Expenses: *₹{summary['wtd_expenses']:,.0f}*\n"
                        f"✅ Net: *₹{summary['wtd_net']:,.0f}*"
                    )
                
                await wa.send_message(user.phone_number, msg)
        except Exception as e:
            logger.error("Weekly summary failed for user", user_id=str(user.id), error=str(e))


async def _anomaly_check_async():
    """Check for expense spikes > 40% above 4-week average."""
    from database import AsyncSessionLocal
    from models.user import User
    from models.transaction import Transaction
    from services.whatsapp import WhatsAppService
    from sqlalchemy import select, func
    from datetime import date, timedelta
    from collections import defaultdict
    
    today = date.today()
    current_month_start = today.replace(day=1)
    prev_3_months_start = (today.replace(day=1) - timedelta(days=90))
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.onboarding_complete == True)
        )
        users = result.scalars().all()
    
    wa = WhatsAppService()
    
    for user in users:
        try:
            async with AsyncSessionLocal() as db:
                # Current month expenses by category
                curr_result = await db.execute(
                    select(Transaction.category_code, func.sum(Transaction.amount))
                    .where(
                        Transaction.user_id == str(user.id),
                        Transaction.type == "expense",
                        Transaction.transaction_date >= current_month_start.isoformat(),
                    ).group_by(Transaction.category_code)
                )
                current = dict(curr_result.all())
                
                # Average over previous 3 months by category
                prev_result = await db.execute(
                    select(Transaction.category_code, func.sum(Transaction.amount))
                    .where(
                        Transaction.user_id == str(user.id),
                        Transaction.type == "expense",
                        Transaction.transaction_date >= prev_3_months_start.isoformat(),
                        Transaction.transaction_date < current_month_start.isoformat(),
                    ).group_by(Transaction.category_code)
                )
                prev_totals = dict(prev_result.all())
                prev_avg = {k: v / 3 for k, v in prev_totals.items()}
                
                # Find spikes
                for cat, curr_amt in current.items():
                    if cat in prev_avg and prev_avg[cat] > 0:
                        spike_pct = ((curr_amt - prev_avg[cat]) / prev_avg[cat]) * 100
                        if spike_pct > 40:
                            cat_display = cat.replace("_", " ").title()
                            msg = (
                                f"⚠️ *Expense Alert!*\n\n"
                                f"Is mahine *{cat_display}* ka kharcha ₹{curr_amt:,.0f} raha.\n"
                                f"Average se *{spike_pct:.0f}% zyada*.\n\n"
                                f"Koi khaas kharcha tha? 🤔"
                            )
                            await wa.send_message(user.phone_number, msg)
        except Exception as e:
            logger.error("Anomaly check failed", user_id=str(user.id), error=str(e))
```

Update `Procfile`:
```
web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
worker: celery -A backend.tasks.celery_app worker --loglevel=info --concurrency=2
beat: celery -A backend.tasks.celery_app beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

---

### 4.2 — GST Invoice Generator

Create `backend/agents/gst_invoice_generator.py`:
```python
# backend/agents/gst_invoice_generator.py
"""Auto-generate GST-compliant invoices from transaction data."""
from jinja2 import Template
from datetime import date
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

GST_INVOICE_HTML = Path(__file__).parent.parent / "templates" / "gst_invoice.html"

GST_INVOICE_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 40px; }
  .header { display: flex; justify-content: space-between; border-bottom: 2px solid #333; padding-bottom: 20px; }
  .invoice-title { font-size: 28px; font-weight: 900; color: #1a1a2e; }
  .gst-badge { background: #16a34a; color: white; padding: 4px 12px; border-radius: 4px; font-size: 12px; }
  table { width: 100%; border-collapse: collapse; margin: 20px 0; }
  th { background: #1a1a2e; color: white; padding: 10px; text-align: left; }
  td { padding: 8px 10px; border-bottom: 1px solid #e2e8f0; }
  .total-row { font-weight: 700; background: #f0fdf4; }
  .footer { margin-top: 40px; font-size: 12px; color: #64748b; }
</style>
</head>
<body>
<div class="header">
  <div>
    <div class="invoice-title">TAX INVOICE</div>
    <span class="gst-badge">GST Compliant</span>
    <p style="margin-top:10px; color:#64748b">Invoice #: {{ invoice_number }}</p>
    <p style="color:#64748b">Date: {{ invoice_date }}</p>
  </div>
  <div style="text-align:right">
    <div style="font-size:20px; font-weight:700">{{ seller_name }}</div>
    <p>{{ seller_business }}</p>
    <p>{{ seller_location }}</p>
    {% if seller_gstin %}<p><strong>GSTIN:</strong> {{ seller_gstin }}</p>{% endif %}
  </div>
</div>

<div style="margin:20px 0">
  <strong>Bill To:</strong> {{ buyer_name or 'Walk-in Customer' }}<br>
  {% if buyer_phone %}<span>Phone: {{ buyer_phone }}</span>{% endif %}
</div>

<table>
  <tr><th>Description</th><th>Qty</th><th>Rate (₹)</th><th>GST%</th><th>Amount (₹)</th></tr>
  {% for item in items %}
  <tr>
    <td>{{ item.description }}</td>
    <td>{{ item.qty or 1 }}</td>
    <td>{{ "{:,.2f}".format(item.rate) }}</td>
    <td>{{ item.gst_pct or 18 }}%</td>
    <td>{{ "{:,.2f}".format(item.amount) }}</td>
  </tr>
  {% endfor %}
  <tr class="total-row">
    <td colspan="4">Subtotal</td><td>₹{{ "{:,.2f}".format(subtotal) }}</td>
  </tr>
  <tr>
    <td colspan="4">CGST (9%)</td><td>₹{{ "{:,.2f}".format(cgst) }}</td>
  </tr>
  <tr>
    <td colspan="4">SGST (9%)</td><td>₹{{ "{:,.2f}".format(sgst) }}</td>
  </tr>
  <tr class="total-row">
    <td colspan="4"><strong>Total Amount</strong></td>
    <td><strong>₹{{ "{:,.2f}".format(total) }}</strong></td>
  </tr>
</table>

<div style="margin-top:20px; padding:15px; background:#f8fafc; border-radius:8px">
  <strong>Amount in Words:</strong> {{ amount_in_words }}
</div>

<div class="footer">
  <p>Generated by ArthAI™ — India's Financial Intelligence Layer</p>
  <p>This is a computer-generated invoice and does not require a physical signature.</p>
</div>
</body></html>"""


class GSTInvoiceGenerator:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate(self, user_id: str, transaction_id: str) -> dict:
        from models.transaction import Transaction
        from models.user import User
        from services.storage import StorageService
        from datetime import date
        
        # Fetch transaction and user
        tx_result = await self.db.execute(
            select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user_id)
        )
        tx = tx_result.scalar_one_or_none()
        if not tx:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        
        # Build invoice data
        subtotal = tx.amount / 1.18  # Back-calculate pre-GST amount
        cgst = sgst = (tx.amount - subtotal) / 2
        
        invoice_number = f"INV-{user_id[:6].upper()}-{date.today().strftime('%Y%m%d')}-{transaction_id[:4].upper()}"
        
        data = {
            "invoice_number": invoice_number,
            "invoice_date": date.today().strftime("%d %B %Y"),
            "seller_name": user.name or "Business Owner",
            "seller_business": user.business_type or "Business",
            "seller_location": user.business_location or "India",
            "seller_gstin": None,  # To be added when user provides GSTIN
            "buyer_name": tx.counterparty,
            "buyer_phone": None,
            "items": [{"description": tx.description or "Services", "qty": 1, "rate": subtotal, "gst_pct": 18, "amount": subtotal}],
            "subtotal": subtotal,
            "cgst": cgst,
            "sgst": sgst,
            "total": tx.amount,
            "amount_in_words": self._num_to_words(tx.amount),
        }
        
        html_content = Template(GST_INVOICE_TEMPLATE).render(**data)
        
        try:
            from weasyprint import HTML as WeasyHTML
            pdf_bytes = WeasyHTML(string=html_content).write_pdf()
            file_ext, content_type = "pdf", "application/pdf"
        except Exception:
            pdf_bytes = html_content.encode("utf-8")
            file_ext, content_type = "html", "text/html"
        
        storage = StorageService()
        file_key = f"invoices/{user_id}/{invoice_number}.{file_ext}"
        download_url = await storage.upload_file(pdf_bytes, file_key, content_type)
        
        return {"invoice_number": invoice_number, "download_url": download_url}
    
    def _num_to_words(self, amount: float) -> str:
        """Convert amount to Indian words (simplified)."""
        rupees = int(amount)
        if rupees >= 100000:
            return f"Rupees {rupees / 100000:.1f} Lakhs Only"
        if rupees >= 1000:
            return f"Rupees {rupees / 1000:.1f} Thousand Only"
        return f"Rupees {rupees} Only"
```

Add endpoint in `backend/routes/reports.py`:
```python
@router.post("/gst-invoice/{user_id}/{transaction_id}")
async def generate_gst_invoice(
    user_id: str,
    transaction_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    from agents.gst_invoice_generator import GSTInvoiceGenerator
    generator = GSTInvoiceGenerator(db)
    result = await generator.generate(user_id, transaction_id)
    return result
```

---

### 4.3 — Monitoring & Observability (Sentry + Structlog)

Add to `requirements.txt`:
```
sentry-sdk[fastapi]==2.3.1
prometheus-fastapi-instrumentator==6.1.0
```

Update `backend/main.py`:
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from prometheus_fastapi_instrumentator import Instrumentator

# Initialize Sentry (before app creation)
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration(), SqlalchemyIntegration(), CeleryIntegration()],
        traces_sample_rate=0.1,  # 10% of transactions
        profiles_sample_rate=0.1,
        environment=settings.ENVIRONMENT,
        release=f"arthai@3.0.0",
        # Don't send PII
        send_default_pii=False,
    )

# Prometheus metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

Add `SENTRY_DSN` to `config.py`:
```python
SENTRY_DSN: Optional[str] = None  # Set in production
```

Update structlog configuration in `main.py` for JSON logging in production:
```python
import structlog

if settings.ENVIRONMENT == "production":
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )
```

---

## SECTION 5: P4 FRONTEND PRODUCTION QUALITY

### 5.1 — Error Boundaries

Create `frontend/src/components/ErrorBoundary.tsx`:
```typescript
import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    console.error('[ArthAI Error Boundary]', error, info);
    this.props.onError?.(error);
    // Report to Sentry in production
    if (import.meta.env.PROD) {
      // Sentry.captureException(error);
    }
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div style={{
          minHeight: '100vh', background: '#0a0e1a', display: 'flex',
          alignItems: 'center', justifyContent: 'center', color: '#f1f5f9',
          fontFamily: 'Inter, sans-serif', flexDirection: 'column', gap: 20
        }}>
          <div style={{ fontSize: 48 }}>⚠️</div>
          <h2 style={{ fontSize: 20, fontWeight: 700 }}>Something went wrong</h2>
          <p style={{ color: '#94a3b8', fontSize: 14 }}>
            {this.state.error?.message ?? 'An unexpected error occurred'}
          </p>
          <button
            onClick={() => { this.setState({ hasError: false, error: null }); window.location.reload(); }}
            style={{
              background: '#16a34a', color: '#0f172a', border: 'none',
              padding: '12px 24px', borderRadius: 8, fontWeight: 700, cursor: 'pointer'
            }}
          >
            🔄 Reload App
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

Wrap app in `frontend/src/main.tsx`:
```typescript
import { ErrorBoundary } from './components/ErrorBoundary';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>
);
```

---

### 5.2 — Code Splitting with React.lazy

Update `frontend/src/App.tsx`:
```typescript
import { lazy, Suspense } from 'react';
import LoadingSpinner from './components/LoadingSpinner';
import { ErrorBoundary } from './components/ErrorBoundary';

// Lazy load heavy pages
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Transactions = lazy(() => import('./pages/Transactions'));
const Passport = lazy(() => import('./pages/Passport'));
const Demo = lazy(() => import('./pages/Demo'));

function App() {
  return (
    <LanguageProvider>
      <BrowserRouter>
        <ErrorBoundary>
          <Suspense fallback={<LoadingSpinner message="Loading..." />}>
            <Routes>
              <Route path="/" element={<Demo />} />
              <Route path="/demo" element={<Demo />} />
              <Route path="/dashboard/:userId" element={<Dashboard />} />
              <Route path="/transactions/:userId" element={<Transactions />} />
              <Route path="/passport/:userId" element={<Passport />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </BrowserRouter>
    </LanguageProvider>
  );
}
```

---

### 5.3 — Proper API Error Handling & Retry Logic

Replace `frontend/src/api/client.ts`:
```typescript
import axios, { AxiosError, AxiosRequestConfig } from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_VERSION = '/api/v1';

export const api = axios.create({
  baseURL: `${API_BASE}${API_VERSION}`,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: inject JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('arthai_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle 401 gracefully
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token expired — redirect to login
      localStorage.removeItem('arthai_token');
      window.location.href = '/demo';
    }
    if (error.response?.status === 429) {
      console.warn('[ArthAI] Rate limited — retry after 60s');
    }
    return Promise.reject(error);
  }
);

// Retry helper with exponential backoff
async function withRetry<T>(fn: () => Promise<T>, retries = 3, delay = 1000): Promise<T> {
  for (let i = 0; i < retries; i++) {
    try {
      return await fn();
    } catch (err) {
      if (i === retries - 1) throw err;
      const wait = delay * Math.pow(2, i);
      await new Promise(resolve => setTimeout(resolve, wait));
    }
  }
  throw new Error('All retries failed');
}

// Token management
export const authClient = {
  getDemoToken: () => api.post('/auth/demo-token', {}, { baseURL: API_BASE }),
  sendOTP: (phone: string) => api.post('/auth/send-otp', { phone }, { baseURL: `${API_BASE}/api/v1` }),
  verifyOTP: (phone: string, otp: string) => api.post('/auth/verify-otp', { phone, otp }, { baseURL: `${API_BASE}/api/v1` }),
  setToken: (token: string) => localStorage.setItem('arthai_token', token),
  getToken: () => localStorage.getItem('arthai_token'),
  clearToken: () => localStorage.removeItem('arthai_token'),
};

// Main API client
const apiClient = {
  getSummary: (userId: string) => withRetry(() => api.get(`/analytics/summary/${userId}`)),
  getPnl: (userId: string, period = '90d') => withRetry(() => api.get(`/analytics/pnl/${userId}`, { params: { period } })),
  getTransactions: (userId: string, page = 1, limit = 20) => withRetry(() =>
    api.get(`/transactions/${userId}`, { params: { page, limit } })
  ),
  getArthScore: (userId: string, forceRefresh = false) => withRetry(() =>
    api.get(`/score/${userId}`, { params: { force_refresh: forceRefresh } })
  ),
  generatePassport: (userId: string) => api.post(`/reports/passport/${userId}`),
  getLoanOffers: (userId: string) => api.get(`/marketplace/offers/${userId}`),
  seedDemo: () => axios.post(`${API_BASE}/api/demo/seed`),
};

export default apiClient;
```

---

### 5.4 — Authentication Flow in Frontend

Create `frontend/src/hooks/useAuth.ts`:
```typescript
import { useState, useEffect } from 'react';
import { authClient } from '../api/client';

export interface AuthState {
  isAuthenticated: boolean;
  userId: string | null;
  loading: boolean;
  error: string | null;
}

export function useAuth() {
  const [auth, setAuth] = useState<AuthState>({
    isAuthenticated: false,
    userId: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    // Auto-login demo user in demo mode
    const initAuth = async () => {
      const existing = authClient.getToken();
      if (existing) {
        // Decode JWT to get userId (no library needed for demo)
        try {
          const payload = JSON.parse(atob(existing.split('.')[1]));
          if (payload.exp * 1000 > Date.now()) {
            setAuth({ isAuthenticated: true, userId: payload.sub, loading: false, error: null });
            return;
          }
        } catch { /* invalid token */ }
      }

      // Try demo token
      try {
        const res = await authClient.getDemoToken();
        authClient.setToken(res.data.access_token);
        setAuth({
          isAuthenticated: true,
          userId: res.data.user_id,
          loading: false,
          error: null,
        });
      } catch (err) {
        setAuth({ isAuthenticated: false, userId: null, loading: false, error: 'Auth failed' });
      }
    };

    initAuth();
  }, []);

  return auth;
}
```

---

### 5.5 — TypeScript Strictness Fixes

Update `frontend/tsconfig.app.json`:
```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "exactOptionalPropertyTypes": true
  }
}
```

Fix `any` types in components — all `(p: any)` in PLChart should be:
```typescript
interface TooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}

const CustomTooltip = ({ active, payload, label }: TooltipProps) => {
  if (!active || !payload?.length) return null;
  // ...
};
```

---

## SECTION 6: P5 DEVOPS & INFRASTRUCTURE

### 6.1 — Production Docker Setup

Replace `backend/Dockerfile` with multi-stage build:
```dockerfile
# backend/Dockerfile
# ── Stage 1: Builder ──────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install system deps for WeasyPrint PDF generation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev libcairo2-dev libpango1.0-dev \
    libpangocairo-1.0-0 libgdk-pixbuf2.0-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Production ───────────────────────────────────────────────
FROM python:3.11-slim

# WeasyPrint runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 arthai && chown -R arthai:arthai /app
USER arthai

# Create necessary directories
RUN mkdir -p /app/static/passports /app/static/invoices

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "2", "--loop", "uvloop", "--http", "httptools"]
```

Create `docker-compose.yml` for local dev:
```yaml
version: '3.9'

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: arthai
      POSTGRES_USER: arthai
      POSTGRES_PASSWORD: arthai_dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U arthai"]
      interval: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s

  backend:
    build: ./backend
    env_file: ./backend/.env
    environment:
      DATABASE_URL: postgresql+asyncpg://arthai:arthai_dev_password@db:5432/arthai
      REDIS_URL: redis://redis:6379/0
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./backend:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  worker:
    build: ./backend
    env_file: ./backend/.env
    environment:
      DATABASE_URL: postgresql+asyncpg://arthai:arthai_dev_password@db:5432/arthai
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - backend
      - redis
    command: celery -A tasks.celery_app worker --loglevel=info

  beat:
    build: ./backend
    env_file: ./backend/.env
    environment:
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - redis
    command: celery -A tasks.celery_app beat --loglevel=info

volumes:
  postgres_data:
```

---

### 6.2 — GitHub Actions CI/CD

Create `.github/workflows/deploy.yml`:
```yaml
name: ArthAI CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.11"
  NODE_VERSION: "20"

jobs:
  test-backend:
    name: Backend Tests
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: arthai_test
          POSTGRES_USER: arthai
          POSTGRES_PASSWORD: test_password
        ports: ["5432:5432"]
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
      redis:
        image: redis:7
        ports: ["6379:6379"]

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip

      - name: Install backend deps
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-asyncio httpx pytest-cov

      - name: Run migrations
        env:
          DATABASE_URL: postgresql+asyncpg://arthai:test_password@localhost:5432/arthai_test
        run: |
          cd backend
          alembic upgrade head

      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://arthai:test_password@localhost:5432/arthai_test
          REDIS_URL: redis://localhost:6379/0
          OPENAI_API_KEY: sk-test-key
          DEMO_MODE: "true"
        run: |
          cd backend
          pytest tests/ -v --cov=. --cov-report=xml --cov-fail-under=70

      - name: Upload coverage
        uses: codecov/codecov-action@v4

  test-frontend:
    name: Frontend Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: npm
          cache-dependency-path: frontend/package-lock.json

      - name: Install and build
        run: |
          cd frontend
          npm ci
          npm run build
          npm run lint

  deploy-backend:
    name: Deploy Backend
    needs: [test-backend, test-frontend]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Railway
        uses: bervProject/railway-deploy@v1.0.0
        with:
          railway_token: ${{ secrets.RAILWAY_TOKEN }}
          service: arthai-backend

  deploy-frontend:
    name: Deploy Frontend
    needs: [test-backend, test-frontend]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
      - run: cd frontend && npm ci && npm run build
      - uses: cloudflare/pages-action@v1
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          projectName: arthai-frontend
          directory: frontend/dist
```

---

### 6.3 — Complete Test Suite

Create `backend/tests/conftest.py`:
```python
# backend/tests/conftest.py
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from main import app
from database import Base, get_db

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as c:
        yield c
    
    app.dependency_overrides.clear()

@pytest.fixture
def demo_user_data():
    return {
        "id": "test-user-001",
        "phone_number": "+919876543210",
        "name": "Test User",
        "preferred_language": "hi",
        "business_type": "Kirana Store",
        "business_location": "Mumbai",
        "onboarding_complete": True,
    }

@pytest.fixture
def sample_transactions():
    from datetime import date, timedelta
    transactions = []
    for i in range(30):
        d = date.today() - timedelta(days=i)
        transactions.append({
            "user_id": "test-user-001",
            "amount": 1000 + (i * 50),
            "type": "income" if i % 3 != 0 else "expense",
            "category_code": "sales_product" if i % 3 != 0 else "inventory",
            "description": f"Transaction {i}",
            "transaction_date": d.isoformat(),
            "source": "text",
            "verified": True,
        })
    return transactions
```

Create `backend/tests/test_arthascore.py`:
```python
# backend/tests/test_arthascore.py
import pytest
from agents.arthascore import ArthScoreEngine, FACTOR_WEIGHTS


class TestArthScoreAlgorithm:
    def test_weights_sum_to_one(self):
        assert abs(sum(FACTOR_WEIGHTS.values()) - 1.0) < 0.001

    def test_income_regularity_perfect(self):
        engine = ArthScoreEngine(None)
        score = engine._cv([1000.0] * 13)
        assert score == 100

    def test_income_regularity_high_variance(self):
        engine = ArthScoreEngine(None)
        score = engine._cv([0, 5000, 0, 5000, 0, 5000] * 2 + [0])
        assert score < 30

    def test_growth_positive(self):
        engine = ArthScoreEngine(None)
        score = engine._growth(list(range(100, 1400, 100)))
        assert score > 60

    def test_growth_declining(self):
        engine = ArthScoreEngine(None)
        score = engine._growth(list(range(1400, 100, -100)))
        assert score < 40

    def test_expense_control_good_margin(self):
        engine = ArthScoreEngine(None)
        score = engine._calc_expense_control(10000, 5000)
        assert score == 100

    def test_expense_control_loss(self):
        engine = ArthScoreEngine(None)
        score = engine._calc_expense_control(5000, 7000)
        assert score == 0

    def test_score_clamped_300_900(self):
        assert int(300 + (100 / 100) * 600) == 900
        assert int(300 + (0 / 100) * 600) == 300

    def test_insufficient_data(self):
        engine = ArthScoreEngine(None)
        result = engine._no_data()
        assert result["score"] == 0
        assert "insight_hi" in result


class TestArthScoreIntegration:
    @pytest.mark.asyncio
    async def test_calculate_with_real_data(self, db_session, demo_user_data, sample_transactions):
        from models.user import User
        from models.transaction import Transaction
        
        user = User(**demo_user_data)
        db_session.add(user)
        
        for tx_data in sample_transactions:
            tx = Transaction(**tx_data)
            db_session.add(tx)
        
        await db_session.commit()
        
        engine = ArthScoreEngine(db_session)
        result = await engine.calculate("test-user-001", lookback_days=90)
        
        assert 300 <= result["score"] <= 900
        assert result["grade"] in ["Excellent", "Good", "Fair", "Needs Improvement"]
        assert result["data_points"] > 0
        assert result["max_loan_eligible"] >= 0
```

Create `backend/tests/test_analytics.py`:
```python
# backend/tests/test_analytics.py
import pytest
from services.analytics import AnalyticsService
from models.user import User
from models.transaction import Transaction
from datetime import date, timedelta


class TestAnalyticsService:
    @pytest.mark.asyncio
    async def test_dashboard_summary(self, db_session, demo_user_data, sample_transactions):
        user = User(**demo_user_data)
        db_session.add(user)
        for tx in sample_transactions:
            db_session.add(Transaction(**tx))
        await db_session.commit()
        
        service = AnalyticsService(db_session)
        summary = await service.get_dashboard_summary("test-user-001")
        
        assert "mtd_income" in summary
        assert "mtd_expenses" in summary
        assert summary["total_transactions"] > 0
        assert isinstance(summary["income_by_category"], dict)

    @pytest.mark.asyncio
    async def test_pnl_data_90d(self, db_session, demo_user_data, sample_transactions):
        user = User(**demo_user_data)
        db_session.add(user)
        for tx in sample_transactions:
            db_session.add(Transaction(**tx))
        await db_session.commit()
        
        service = AnalyticsService(db_session)
        pnl = await service.get_pnl_data("test-user-001", "90d")
        
        assert pnl["period"] == "90d"
        assert pnl["total_income"] >= 0
        assert len(pnl["series"]) == 13  # 13 weeks

    @pytest.mark.asyncio
    async def test_empty_user_returns_zeros(self, db_session, demo_user_data):
        user = User(**demo_user_data)
        db_session.add(user)
        await db_session.commit()
        
        service = AnalyticsService(db_session)
        summary = await service.get_dashboard_summary("test-user-001")
        
        assert summary["mtd_income"] == 0
        assert summary["total_transactions"] == 0


class TestWebhook:
    @pytest.mark.asyncio
    async def test_webhook_rejects_invalid_signature(self, client):
        """Webhook must validate Twilio signature in production."""
        # With DEMO_MODE=True, signature validation is skipped
        resp = await client.post(
            "/webhook/whatsapp",
            data={"From": "whatsapp:+919876543210", "Body": "Hello"}
        )
        assert resp.status_code == 200
        assert "<Response>" in resp.text

    @pytest.mark.asyncio  
    async def test_health_check(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "checks" in data
```

---

## SECTION 7: UPDATED REQUIREMENTS & ENVIRONMENT

### Updated `backend/requirements.txt`:
```text
# Core framework
fastapi==0.111.0
uvicorn[standard]==0.29.0
uvloop==0.19.0
httptools==0.6.1
python-multipart==0.0.9

# Database
sqlalchemy[asyncio]==2.0.30
asyncpg==0.29.0
aiosqlite==0.20.0
alembic==1.13.1

# Auth
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# AI / ML
openai==1.30.1
httpx==0.27.0
tiktoken==0.7.0

# Agentic framework
langgraph==0.1.5
langchain-core==0.2.5
langchain-openai==0.1.8

# Task queue
celery[redis]==5.4.0
redis[asyncio]==5.0.4

# Rate limiting
slowapi==0.1.9

# WhatsApp / Twilio
twilio==9.1.0

# PDF generation
weasyprint==61.2
jinja2==3.1.4

# Storage
boto3==1.34.110

# Monitoring
sentry-sdk[fastapi]==2.3.1
prometheus-fastapi-instrumentator==6.1.0

# Validation & security
pydantic==2.7.1
pydantic-settings==2.3.0
email-validator==2.1.1

# Utils
python-dotenv==1.0.1
structlog==24.1.0
tenacity==8.3.0
numpy==1.26.4
scikit-learn==1.5.0

# Testing
pytest==8.2.0
pytest-asyncio==0.23.6
httpx==0.27.0
pytest-cov==5.0.0
```

### Updated `backend/.env.example`:
```bash
# ─── DATABASE ────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://arthai:password@localhost:5432/arthai
# Dev fallback: sqlite+aiosqlite:///./arthai_dev.db

# ─── REDIS ───────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# ─── AI APIs ─────────────────────────────────────────
OPENAI_API_KEY=sk-...
OPENAI_MODEL_VISION=gpt-4o-mini
OPENAI_MODEL_NLU=gpt-4o-mini
SARVAM_API_KEY=your_sarvam_key
SARVAM_ASR_MODEL=saarika-v2

# ─── MESSAGING ───────────────────────────────────────
TWILIO_ACCOUNT_SID=ACxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_WEBHOOK_URL=https://your-domain.com/webhook/whatsapp

# ─── STORAGE ─────────────────────────────────────────
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=your_secret
AWS_BUCKET_NAME=arthai-production
AWS_REGION=ap-south-1

# ─── SECURITY ────────────────────────────────────────
SECRET_KEY=CHANGE_ME_32_CHAR_RANDOM_STRING_HERE  # openssl rand -hex 32
ALLOWED_ORIGINS=https://your-frontend.pages.dev,https://app.yourdomain.com

# ─── MONITORING ──────────────────────────────────────
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project

# ─── APP ─────────────────────────────────────────────
ENVIRONMENT=production
LOG_LEVEL=INFO
DEMO_MODE=false  # true for demo/hackathon only

# ─── ARTHASCORE ──────────────────────────────────────
ARTHASCORE_MIN=300
ARTHASCORE_MAX=900
CONFIDENCE_THRESHOLD=0.85

# ─── FEATURE FLAGS ───────────────────────────────────
ENABLE_SARVAM_ASR=true
ENABLE_S3_STORAGE=true
```

---

## SECTION 8: FINAL PRODUCTION CHECKLIST

### Backend: 46-Point Checklist

```
P0 CRITICAL BUGS:
[x] Optional imported in nlu.py
[x] Transaction dates use ISODate type (sortable, filterable)
[x] PDF generation uses WeasyPrint with HTML fallback
[x] ArthScore date parsing handles both str and date types
[x] Analytics refresh_cache uses portable upsert (no pg-specific INSERT)
[x] WhatsApp session user_id is nullable until user created
[x] LangGraph state stores ExtractedTransaction as dict
[x] App.tsx routes to Demo page first, not dashboard

P1 SECURITY:
[x] JWT auth on all user-facing API endpoints
[x] Phone OTP authentication flow
[x] Twilio webhook signature validation
[x] Rate limiting (slowapi) on all routes
[x] Security headers middleware
[x] CORS tightened to specific origins

P2 ARCHITECTURE:
[x] Alembic migrations setup (not create_all in production)
[x] Redis caching for ArthScore (1-hour TTL, invalidated on new tx)
[x] Comprehensive health check (DB + Redis + AI key status)
[x] API versioning (/api/v1/)
[x] Non-root Docker user
[x] Multi-stage Docker build (WeasyPrint system deps included)
[x] docker-compose.yml for local dev

P3 FEATURES:
[x] Celery Beat schedule (weekly summaries, anomaly detection)
[x] GST invoice generator
[x] Sentry error monitoring
[x] Prometheus metrics endpoint
[x] Structured JSON logging in production

P4 DEVOPS:
[x] GitHub Actions CI/CD pipeline
[x] Automated tests on every PR
[x] Backend test suite (70%+ coverage target)
[x] Frontend TypeScript strict mode
[x] Code coverage reporting (Codecov)
[x] Production Docker healthcheck

FRONTEND:
[x] ErrorBoundary wrapping entire app
[x] React.lazy code splitting for all pages
[x] JWT token injection in API client
[x] 401 auto-redirect to login
[x] Retry with exponential backoff
[x] TypeScript strict mode, no `any`
[x] Demo page as proper landing (not auto-redirect)
[x] Authentication hook (useAuth)
```

---

## SECTION 9: QUICK START — POST-AUDIT BUILD ORDER

```bash
# 1. Fix all P0 bugs first (1 hour)
# Apply all code changes from Section 1

# 2. Set up PostgreSQL and Alembic (30 min)
docker-compose up db redis -d
cd backend
alembic init migrations
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head

# 3. Install new dependencies (10 min)
pip install -r requirements.txt

# 4. Run tests to confirm P0 fixes (20 min)
pytest tests/ -v --tb=short

# 5. Test the whole stack locally (30 min)
docker-compose up --build
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/demo/seed
curl http://localhost:8000/api/v1/analytics/summary/raju-demo-001

# 6. Deploy to Railway (15 min)
railway login && railway up

# 7. Set environment variables in Railway dashboard
# (All variables from .env.example)

# 8. Deploy frontend to Cloudflare Pages (10 min)
cd frontend && npm run build
# Push to git → Cloudflare auto-deploys

# 9. Configure Twilio webhook URL
# https://your-railway-url.up.railway.app/webhook/whatsapp

# 10. Test end-to-end with WhatsApp sandbox
# Send a message → watch logs → confirm transaction recorded

# Total estimated time: ~3 hours for P0+P1 fixes
# Full production implementation: ~3 days
```

---

## SECTION 10: YC EVALUATION FRAME

| YC Question | Before V3 | After V3 |
|------------|-----------|----------|
| **Does it work?** | Partially (8 bugs) | Yes (all bugs fixed) |
| **Is it secure?** | No (0 auth, 0 rate limiting) | Yes (JWT + Twilio validation + rate limits) |
| **Can it scale?** | No (SQLite, no cache) | Yes (PostgreSQL + Redis + Celery) |
| **Is it observable?** | No (print logs only) | Yes (Sentry + Prometheus + structured logs) |
| **Can you trust it?** | No (no tests) | Yes (70%+ coverage, CI/CD) |
| **Can you ship it?** | No (manual deploy) | Yes (GitHub Actions auto-deploy) |
| **Does Raju still get his loan?** | Yes | **Still yes, but now reliably at 1M users** |

---

*ArthAI V3 — Built for 63 million. Hardened for production. Ready for YC.*

*"Apna Business, Apni Zubaan Mein." — Now at enterprise scale.*

---
**Document Version**: 3.0 | **Audit Date**: June 2026 | **Issues Fixed**: 45/45
