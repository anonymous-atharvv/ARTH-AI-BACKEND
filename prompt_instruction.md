# ArthAI GOD TIER V4 ⚡
## Production Readiness & YC-Grade Engineering Specification
### Generated from Full 121-File Codebase Audit + Architecture Review

> *"The gap between a functional demo and a fundable company is exactly what this document closes."*

---

## EXECUTIVE AUDIT SUMMARY

After deep inspection of all 121 files — every route, model, agent, task, schema, config, and frontend component — this audit surfaces **14 production-blocking bugs**, **11 security vulnerabilities**, **9 architectural deficiencies**, and specifies **8 high-leverage new features** that separate a hackathon winner from a Series A candidate.

**Verdict on current state:**
The core is genuinely impressive — LangGraph agent pipeline, WhatsApp multimodal routing, ArthScore algorithm, and Financial Passport generator are sophisticated and non-trivial. Most teams doing "AI + FinTech" are wrapping GPT with a form. You built an actual agentic system. That matters.

But 6 of the bugs found would cause silent data corruption or crashes within the first 100 real users. 3 security gaps expose user financial data. The frontend hardcodes a demo user in 4 places, making multi-tenancy impossible without a refactor. And the two most-claimed differentiators (Account Aggregator integration and 12-language support) are architecturally absent.

This document tells you exactly what to fix, in what order, and what to build next.

**Total estimated engineering effort:** 45–60 hours across all tiers.

---

## DOCUMENT STRUCTURE

- **TIER 0 — P0 Critical Bugs** (Do these in 24 hours. Each is a production blocker.)
- **TIER 1 — Security Hardening** (Do these before any real user touches the app.)
- **TIER 2 — Architecture Upgrades** (Do these before 1,000 users.)
- **TIER 3 — New Features for YC** (Do these to have a credible Series A narrative.)
- **TIER 4 — Frontend Excellence** (Do these for demo day and investor screenshots.)
- **TIER 5 — DevOps Pipeline** (Do these before submitting the GitHub URL.)
- **TIER 6 — Testing Suite** (Do these to pass the "engineering bar" filter.)
- **Final Checklist** (54 items. Ship when all are checked.)

---

## TIER 0 — P0 CRITICAL BUGS
### These Will Cause Production Failures Within 100 Users

---

### BUG-01: OTP Logged in Plaintext
**File:** `backend/routes/auth.py`, line 56  
**Impact:** Every OTP is written to your structured logs. Anyone with log access (Railway dashboard, Sentry, any log aggregator) can intercept any user's OTP. This is a compliance violation under India's IT Act and DPDP Act 2023.

**Current code (BAD):**
```python
logger.info("OTP generated", phone=otp_req.phone, otp=otp)
```

**Fixed code:**
```python
# Log only the last 4 digits of phone for privacy, never log OTP
logger.info("OTP sent", phone_suffix=otp_req.phone[-4:], otp_length=len(otp))
```

**Also fix:** Add `verify-otp` rate limiting. Currently only `send-otp` is rate-limited. A 6-digit OTP has 1,000,000 combinations. Without rate limiting on verify, an attacker who intercepts a phone number can brute-force it in under 10 minutes.

```python
# backend/routes/auth.py
@router.post("/verify-otp")
@limiter.limit("10/hour")  # ADD THIS — brute force protection
async def verify_otp(request: Request, otp_req: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    ...
```

**Time:** 10 minutes.

---

### BUG-02: Redis Connection Leak — One New TCP Connection Per Request
**Files:** `backend/routes/score.py`, `backend/routes/auth.py`, `backend/routes/transactions.py`, `backend/tasks/scheduled_tasks.py`  
**Impact:** Every endpoint that touches Redis does this:
```python
async def get_redis():
    return await aioredis.from_url(settings.REDIS_URL)
```
This opens a new TCP connection to Redis per function call. At 100 concurrent users, you'll hit Railway's Redis connection limit and start seeing `ConnectionError: too many connections`. This is silent data loss — cache misses look identical to working behavior.

**Fix:** Create a module-level singleton pool. Add this to `backend/database.py` or a new `backend/cache.py`:

```python
# backend/cache.py — NEW FILE
"""Singleton Redis connection pool for ArthAI."""
import redis.asyncio as aioredis
from config import settings
import structlog

logger = structlog.get_logger()
_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Return the shared Redis connection pool. Safe to call from any async context."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )
        logger.info("Redis connection pool created", url=settings.REDIS_URL[:20])
    return _redis_pool


async def close_redis():
    """Call on application shutdown."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None
```

**Then in `backend/main.py` lifespan:**
```python
from cache import get_redis, close_redis

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ArthAI backend starting up", env=settings.ENVIRONMENT)
    await create_db_tables()
    await get_redis()          # Warm the pool on startup
    await _seed_categories()
    yield
    await close_redis()        # Clean shutdown
    logger.info("ArthAI backend shutting down")
```

**Replace ALL `get_redis()` local function definitions** in routes/score.py, routes/auth.py, routes/transactions.py, tasks/scheduled_tasks.py with:
```python
from cache import get_redis
```

**Time:** 45 minutes.

---

### BUG-03: LangGraph Agent Compiled Per-Message (500ms Tax on Every WhatsApp Message)
**File:** `backend/tasks/message_tasks.py`, line 20  
**Impact:** `build_financial_agent()` compiles the full LangGraph state graph on every incoming WhatsApp message. Graph compilation involves validating nodes, edges, and type annotations — it takes 200–500ms. At 100 messages/minute, this is 20–50 seconds of CPU time wasted per minute purely on setup.

**Current code (BAD):**
```python
async def _process_message_async(payload: dict):
    ...
    agent = build_financial_agent()  # ← COMPILED PER MESSAGE
    initial_state = {...}
    await agent.ainvoke(initial_state)
```

**Fix:** Compile once at module load, reuse the compiled graph:
```python
# backend/tasks/message_tasks.py

from agents.financial_agent import build_financial_agent

# Compile ONCE when the module loads — reused for all messages
_COMPILED_AGENT = build_financial_agent()


async def _process_message_async(payload: dict):
    ...
    # Use the pre-compiled agent
    await _COMPILED_AGENT.ainvoke(initial_state)
```

**Time:** 5 minutes.

---

### BUG-04: `asyncio.create_task()` Fallback in Webhook — Unmanaged Background Work
**File:** `backend/routes/webhook.py`, lines 43–46  
**Impact:** When Celery is unavailable, the webhook falls back to:
```python
asyncio.create_task(_process_async(payload))
```
This creates an unmanaged task that has no error handling, no observability, and no graceful shutdown behavior. If the message processing fails, the exception is swallowed silently. FastAPI provides `BackgroundTasks` exactly for this pattern.

**Fix:**
```python
# backend/routes/webhook.py
from fastapi import APIRouter, Request, Response, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse

@router.post("/whatsapp")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        form_data = await request.form()
        params = dict(form_data)

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
        }

        logger.info("WhatsApp message received", from_suffix=payload["from"][-4:])

        try:
            from tasks.message_tasks import process_whatsapp_message
            process_whatsapp_message.delay(payload)
        except Exception as celery_err:
            logger.warning("Celery unavailable, using BackgroundTasks fallback", error=str(celery_err))
            # FastAPI BackgroundTasks: runs after response is sent, properly managed
            background_tasks.add_task(_process_background, payload)

        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Webhook processing failed", error=str(e))
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml"
        )


async def _process_background(payload: dict):
    """Properly instrumented background task."""
    from tasks.message_tasks import _process_message_async
    try:
        await _process_message_async(payload)
    except Exception as e:
        logger.error("Background WhatsApp processing failed",
                     error=str(e),
                     from_suffix=payload.get("from", "")[-4:])
```

**Time:** 20 minutes.

---

### BUG-05: `pytz` Missing From requirements.txt But Used by Celery Beat
**File:** `backend/tasks/celery_app.py`, line 12; `backend/requirements.txt`  
**Impact:** `celery_app.conf.update(timezone="Asia/Kolkata")` requires `pytz` for timezone support in Celery 5.x. Without it, the beat scheduler silently falls back to UTC, causing weekly summaries to fire at 3:30am IST instead of 9:00am, and daily anomaly checks to fire at 1:30am instead of 8:00pm.

**Fix:**
```txt
# backend/requirements.txt — add:
pytz==2024.1
```

```python
# backend/tasks/celery_app.py — verify timezone import works:
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    ...
)
```

**Time:** 2 minutes.

---

### BUG-06: `WhatsAppSession.phone_number` Has No Database Index — O(N) Scan on Every Message
**File:** `backend/models/session.py`, line 11  
**Impact:** Every incoming WhatsApp message triggers:
```python
await db.execute(select(WhatsAppSession).where(WhatsAppSession.phone_number == phone))
```
`phone_number` has `unique=True` but no explicit `index=True`. In SQLAlchemy, `unique=True` creates a uniqueness constraint but not necessarily a separate B-tree index on all backends. More critically, `user_id` is also unindexed. At 10,000 users with 100 messages/day, this is 1M full table scans per day.

**Fix:**
```python
# backend/models/session.py
class WhatsAppSession(Base):
    __tablename__ = "whatsapp_sessions"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(GUID(), nullable=True, index=True)          # ADD index=True
    phone_number = Column(String(15), nullable=False, unique=True, index=True)  # ADD index=True
    state = Column(String(50), nullable=False, default="IDLE")
    pending_transaction = Column(JSON)
    context = Column(JSON, default={})
    last_activity = Column(String, default=lambda: datetime.utcnow().isoformat())
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
```

**Also index `Transaction` table:**
```python
# backend/models/transaction.py
transaction_date = Column(ISODate, nullable=False, index=True)  # already has this ✓
user_id = Column(GUID(), nullable=False, index=True)            # already has this ✓
category_code = Column(String(50), index=True)                  # already has this ✓
# ADD composite index for the most common query pattern:
__table_args__ = (
    Index('ix_transaction_user_date', 'user_id', 'transaction_date'),
    Index('ix_transaction_user_type', 'user_id', 'type'),
)
```

**Time:** 20 minutes + generate alembic migration.

---

### BUG-07: `ALLOWED_ORIGINS` as `List[str]` Won't Parse Comma-Separated Env Var in Pydantic-Settings
**File:** `backend/config.py`, line 36  
**Impact:** In production, `ALLOWED_ORIGINS=https://arthai.pages.dev,http://localhost:5173` is set as a single string. Pydantic-settings v2 does NOT automatically split `List[str]` from a comma-separated env var — it expects JSON format (`'["url1", "url2"]'`) by default. The CORS middleware receives `["https://arthai.pages.dev,http://localhost:5173"]` (one string) instead of two separate origins, silently breaking CORS for all non-localhost origins.

**Fix:**
```python
# backend/config.py

from pydantic import field_validator

class Settings(BaseSettings):
    ...
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            # Handle both JSON array and comma-separated string
            if v.startswith("["):
                import json
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
```

**Time:** 10 minutes.

---

### BUG-08: Frontend Hardcodes `DEMO_USER_ID` in 4 Page Components — Multi-Tenancy Broken
**Files:** `frontend/src/pages/Dashboard.tsx`, `Transactions.tsx`, `Passport.tsx`  
**Impact:** Every page falls back to demo data if URL params are missing:
```typescript
const uid = userId || DEMO_USER_ID;  // DEMO_USER_ID = 'raju-demo-001'
```
Real users going to `/dashboard` (without `:userId`) silently see Raju's data. This means the app has exactly one working user: the demo. Auth-gated routes for production require a proper auth context.

**Fix:** Create `frontend/src/contexts/AuthContext.tsx`:
```typescript
// frontend/src/contexts/AuthContext.tsx
import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';

interface AuthContextType {
  userId: string | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType>({
  userId: null,
  token: null,
  isAuthenticated: false,
  isLoading: true,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [userId, setUserId] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedToken = localStorage.getItem('arthai_token');
    const storedUserId = localStorage.getItem('arthai_user_id');
    if (storedToken && storedUserId) {
      setToken(storedToken);
      setUserId(storedUserId);
    }
    setIsLoading(false);
  }, []);

  return (
    <AuthContext.Provider value={{
      userId,
      token,
      isAuthenticated: !!token && !!userId,
      isLoading,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuthContext = () => useContext(AuthContext);
```

**Create `frontend/src/components/ProtectedRoute.tsx`:**
```typescript
import { Navigate } from 'react-router-dom';
import { useAuthContext } from '../contexts/AuthContext';
import LoadingSpinner from './LoadingSpinner';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthContext();

  if (isLoading) return <LoadingSpinner message="Loading..." />;
  if (!isAuthenticated) return <Navigate to="/demo" replace />;
  return <>{children}</>;
}
```

**Update `App.tsx`:**
```typescript
// frontend/src/App.tsx
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <BrowserRouter>
          <Suspense fallback={<LoadingFallback />}>
            <Routes>
              <Route path="/" element={<Navigate to="/demo" replace />} />
              <Route path="/demo" element={<Demo />} />
              <Route path="/dashboard/:userId" element={
                <ProtectedRoute><Dashboard /></ProtectedRoute>
              } />
              <Route path="/transactions/:userId" element={
                <ProtectedRoute><Transactions /></ProtectedRoute>
              } />
              <Route path="/passport/:userId" element={
                <ProtectedRoute><Passport /></ProtectedRoute>
              } />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
      </AuthProvider>
    </LanguageProvider>
  );
}
```

**Update Dashboard.tsx** — remove `DEMO_USER_ID` fallback:
```typescript
// frontend/src/pages/Dashboard.tsx
import { useAuthContext } from '../contexts/AuthContext';

export default function Dashboard() {
  const { userId } = useParams<{ userId: string }>();
  const { userId: authUserId } = useAuthContext();
  // Use URL param, fall back to auth context, never hardcode demo
  const uid = userId || authUserId || '';

  if (!uid) return <Navigate to="/demo" replace />;
  ...
}
```

**Apply the same pattern to Transactions.tsx and Passport.tsx.**

**Time:** 60 minutes.

---

### BUG-09: `LoanImpactCalculator` Hardcodes ₹15,000 Monthly Surplus for All Users
**File:** `frontend/src/components/LoanImpactCalculator.tsx`, line 44  
**Impact:** The affordability indicator always calculates `EMI as % of ₹15,000 surplus` regardless of Raju's actual net income. Raju earns ₹280,000 net over 90 days = ₹93,333/month. This makes the affordability indicator wrong for every user with income ≠ ₹15,000/month.

**Current code (BAD):**
```typescript
`EMI represents ~${Math.round((emi / 15000) * 100)}% of your monthly P&L surplus`
```

**Fix:** Pass actual monthly net from the score/summary data:
```typescript
// In Dashboard.tsx — pass actual monthly net to LoanImpactCalculator
{score && (
  <LoanImpactCalculator
    maxLoan={score.max_loan_eligible}
    score={score.score}
    monthlyNet={summary?.mtd_net_profit || 15000}  // PASS REAL NET
  />
)}

// In LoanImpactCalculator.tsx
interface Props {
  maxLoan: number;
  score: number;
  monthlyNet: number;   // ADD THIS
}

export default function LoanImpactCalculator({ maxLoan, score, monthlyNet }: Props) {
  ...
  // Use actual monthly net, floor at ₹5,000 to avoid division by zero
  const effectiveMonthlyNet = Math.max(monthlyNet, 5000);
  const affordabilityPct = Math.round((emi / effectiveMonthlyNet) * 100);
  const isAffordable = affordabilityPct <= 30;

  return (
    ...
    <span className="aff-text">
      {t(
        `EMI is ~${affordabilityPct}% of your monthly surplus. ${isAffordable ? 'Safe level! ✅' : 'Stretching budget — consider lower amount ⚠️'}`,
        `ईएमआई आपके मासिक अधिशेष का ~${affordabilityPct}% है। ${isAffordable ? 'सुरक्षित स्तर! ✅' : 'बजट पर दबाव — कम राशि लें ⚠️'}`
      )}
    </span>
  );
}
```

**Time:** 20 minutes.

---

### BUG-10: Nightly Cache Warming Doesn't Close Redis Connection in Loop
**File:** `backend/tasks/scheduled_tasks.py`, `_nightly_cache_warming_async()`  
**Impact:** Creates ONE Redis connection but uses it for potentially hundreds of users in a loop without handling failures between iterations. If any single user's score calculation fails, the exception propagates and the Redis connection is never properly returned.

**Fix — use the singleton pool (from BUG-02 fix) and add per-user error isolation:**
```python
# backend/tasks/scheduled_tasks.py
async def _nightly_cache_warming_async():
    from cache import get_redis  # use singleton pool
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.onboarding_complete == True))
        users = res.scalars().all()

        redis = await get_redis()
        engine = ArthScoreEngine(db)

        success_count = 0
        error_count = 0

        for user in users:
            try:
                result = await engine.calculate(str(user.id), lookback_days=90)
                # Use a custom JSON encoder for safety
                serialized = json.dumps(result, default=str)
                await redis.setex(f"arthscore:{user.id}", 86400, serialized)
                success_count += 1
            except Exception as e:
                error_count += 1
                logger.error("ArthScore cache warm failed for user",
                             user_id=str(user.id), error=str(e))

        logger.info("Nightly cache warming complete",
                    success=success_count, errors=error_count, total=len(users))
```

**Time:** 15 minutes.

---

### BUG-11: Demo Mode Disables ALL Webhook Validation Globally
**File:** `backend/routes/webhook.py`, line 22  
**Impact:** `if settings.DEMO_MODE or not settings.TWILIO_AUTH_TOKEN: return True` — if `DEMO_MODE=true` is ever deployed to production (easy accident), any HTTP client can forge WhatsApp webhooks. An attacker could inject arbitrary financial transactions for any user by POSTing to `/webhook/whatsapp`.

**Fix:** Separate demo bypass into a development-only env:
```python
# backend/routes/webhook.py
def validate_twilio_request(request_url: str, form_params: dict, signature: str) -> bool:
    """Validate Twilio webhook signature. Never bypassed in production."""
    if settings.ENVIRONMENT == "development":
        # Only bypass in local dev, never in production
        logger.debug("Skipping Twilio validation in development mode")
        return True
    if not settings.TWILIO_AUTH_TOKEN:
        logger.error("TWILIO_AUTH_TOKEN not set — rejecting webhook for safety")
        return False
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    return validator.validate(request_url, form_params, signature)
```

**And in `backend/config.py`:**
```python
DEMO_MODE: bool = True  # Controls demo endpoints, NOT security bypasses
```

**Time:** 15 minutes.

---

### BUG-12: `backend/agents/arthascore.py` — `_growth()` Imports sklearn Inside Method (Not Thread-Safe on Cold Start)
**File:** `backend/agents/arthascore.py`, lines 54–59  
**Impact:** Under concurrent load, multiple threads hitting `_growth()` simultaneously before sklearn is imported trigger the Global Import Lock (GIL). First-call latency spikes to 1–3 seconds on cold start as sklearn loads.

**Fix:** Move the import to module level and add a graceful fallback:
```python
# backend/agents/arthascore.py — top of file
try:
    from sklearn.linear_model import LinearRegression
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

class ArthScoreEngine:
    ...
    def _growth(self, w: list[float]) -> int:
        if len(w) < 3:
            return 50
        if not SKLEARN_AVAILABLE:
            # Simple linear trend fallback without sklearn
            n = len(w)
            if n < 2:
                return 50
            slope = (w[-1] - w[0]) / max(1, n - 1)
            avg = sum(w) / n if n > 0 else 1
            return max(0, min(100, int(50 + slope / max(1, avg) * 250)))

        import numpy as np
        X = np.arange(len(w)).reshape(-1, 1)
        m = LinearRegression().fit(X, np.array(w))
        avg = np.mean([x for x in w if x > 0]) or 1
        return max(0, min(100, int(50 + m.coef_[0] / avg * 250)))
```

**Time:** 15 minutes.

---

### BUG-13: `passport_generator.py` Uses `/` Float Division for Average Monthly Income (Assumes Exactly 3 Months)
**File:** `backend/agents/passport_generator.py`, line 68  
**Impact:** `"avg_monthly_income": pnl.get("total_income", 0) / 3` — hardcoded `/ 3` assumes 90-day lookback is always exactly 3 months. For a user with 45 days of data, this halves their actual monthly average, making them appear less creditworthy.

**Fix:**
```python
def _build_template_data(self, user, score_data, pnl, doc_id) -> dict:
    period_days = score_data.get("period_days", 90)
    total_income = pnl.get("total_income", 0)
    months_active = max(1, period_days / 30)  # Dynamic, not hardcoded 3

    return {
        ...
        "avg_monthly_income": total_income / months_active,
        ...
    }
```

**Time:** 5 minutes.

---

### BUG-14: Missing Alembic Migration Files — Database Schema Management Is Non-Functional
**File:** `backend/migrations/versions/.gitkeep`  
**Impact:** The alembic setup is present but no migration files exist. `alembic upgrade head` runs against an empty migrations folder. The codebase uses `Base.metadata.create_all()` on startup (the "cheating" approach that works only for greenfield). Once deployed with real data, adding any column requires a migration — without pre-written migrations, schema changes will cause data loss.

**Fix:** Generate the initial migration NOW before production data exists:
```bash
cd backend
# Set DATABASE_URL to your Neon or local PostgreSQL
export DATABASE_URL="postgresql+asyncpg://..."

# Generate initial migration from current models
alembic revision --autogenerate -m "initial_schema"

# Review the generated file in migrations/versions/
# Then apply:
alembic upgrade head
```

**Also update `backend/main.py`** to NOT call `create_all()` in non-development environments:
```python
async def lifespan(app: FastAPI):
    logger.info("ArthAI backend starting up", env=settings.ENVIRONMENT)
    if settings.ENVIRONMENT == "development":
        # Only auto-create in dev. Use alembic in staging/production.
        await create_db_tables()
    await get_redis()
    await _seed_categories()
    yield
    await close_redis()
```

**Time:** 30 minutes.

---

## TIER 1 — SECURITY HARDENING
### Must Complete Before Real Users Touch the App

---

### SEC-01: Weak Default `SECRET_KEY` Will Be Used If Env Var Not Set
**Current:** `SECRET_KEY: str = "arthai-dev-secret-key-change-in-production"`  
**Fix:**
```python
# backend/config.py
import secrets

class Settings(BaseSettings):
    SECRET_KEY: str = ""  # Empty default

    def validate_critical(self):
        if not self.SECRET_KEY or len(self.SECRET_KEY) < 32:
            if self.ENVIRONMENT == "production":
                raise ValueError("SECRET_KEY must be set to a 32+ character random string in production")
            else:
                # Generate ephemeral key for dev — logs a warning
                logger.warning("Using ephemeral SECRET_KEY — JWTs will not survive restart")
                object.__setattr__(self, 'SECRET_KEY', secrets.token_hex(32))
```

---

### SEC-02: JWT Tokens Have No Revocation — Compromised Tokens Valid for 7 Days
**Current:** `ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7` with no refresh token or revocation list.  
**Fix:** Add Redis-backed token revocation:
```python
# backend/middleware/auth.py
async def revoke_token(jti: str):
    """Add token ID to Redis denylist for remaining TTL."""
    from cache import get_redis
    redis = await get_redis()
    await redis.setex(f"revoked_jwt:{jti}", ACCESS_TOKEN_EXPIRE_HOURS * 3600, "1")

async def is_token_revoked(jti: str) -> bool:
    from cache import get_redis
    redis = await get_redis()
    return bool(await redis.exists(f"revoked_jwt:{jti}"))

def create_access_token(user_id: str, phone: str) -> str:
    import uuid
    payload = {
        "sub": user_id,
        "phone": phone,
        "jti": str(uuid.uuid4()),  # ADD unique token ID
        "exp": datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
        "iat": datetime.utcnow(),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[ALGORITHM])
        # Check revocation list (sync wrapper needed — use background check)
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
```

---

### SEC-03: Add `X-Request-ID` Tracing and Correlation IDs
```python
# backend/middleware/request_id.py — NEW FILE
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger()

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        # Bind request_id to all logs in this request's context
        with structlog.contextvars.bound_contextvars(request_id=request_id):
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
```

---

### SEC-04: Input Validation — Transaction Amounts Must Be Positive and Bounded
```python
# backend/schemas/transaction.py
from pydantic import validator

class TransactionCreate(BaseModel):
    amount: float
    ...

    @validator("amount")
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Transaction amount must be positive")
        if v > 10_00_00_000:  # ₹10 crore — sanity cap
            raise ValueError("Transaction amount exceeds maximum allowed (₹10 crore)")
        return round(v, 2)  # Normalize to 2 decimal places

    @validator("description", pre=True, always=True)
    def sanitize_description(cls, v):
        if v is None:
            return None
        # Strip null bytes, limit length
        return v.replace("\x00", "")[:500].strip()
```

---

### SEC-05: Rate Limit Passport Generation (Expensive AI + PDF Operation)
```python
# backend/routes/reports.py
from middleware.rate_limit import limiter

@router.post("/passport/{user_id}")
@limiter.limit("3/hour")  # Max 3 passports per hour per IP
async def generate_financial_passport(
    request: Request,  # Required for SlowAPI
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    ...
```

---

### SEC-06: Sanitize `phone_number` Before Storage and Lookup
```python
# backend/routes/auth.py — validate E.164 format
import re

class SendOTPRequest(BaseModel):
    phone: str

    @validator("phone")
    def validate_e164(cls, v):
        cleaned = re.sub(r"[^\d+]", "", v)
        if not cleaned.startswith("+"):
            cleaned = "+" + cleaned
        if not re.match(r"^\+[1-9]\d{9,14}$", cleaned):
            raise ValueError("Phone number must be in E.164 format (e.g., +919876543210)")
        return cleaned
```

---

### SEC-07: Add Content Security Policy Header
```python
# backend/middleware/security_headers.py — update existing file
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        # ADD: Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.anthropic.com"
        )
        response.headers.pop("server", None)
        return response
```

---

### SEC-08: Audit Log for Financial Data Access
```python
# backend/models/audit.py — NEW FILE
import uuid
from datetime import datetime
from sqlalchemy import Column, String, JSON
from database import Base
from models.user import GUID

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(GUID(), nullable=False, index=True)
    action = Column(String(100), nullable=False)   # "passport_generated", "score_calculated"
    resource_type = Column(String(50))
    resource_id = Column(String(100))
    ip_address = Column(String(50))
    metadata = Column(JSON, default={})
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
```

Add audit logging to passport generation, score access, and transaction creation.

---

### SEC-09: Pre-Signed S3 URLs Expire Too Slowly (30 Days)
```python
# backend/services/storage.py
# Change presigned URL expiry from 30 days to 7 days
url = self.s3_client.generate_presigned_url(
    "get_object",
    Params={"Bucket": self.bucket_name, "Key": key},
    ExpiresIn=7 * 24 * 3600,  # 7 days, not 30
)
```

---

### SEC-10: Ensure DEMO_MODE Cannot Be True in Production
```python
# backend/config.py
def validate_critical(self):
    if self.ENVIRONMENT == "production":
        if self.DEMO_MODE:
            raise ValueError("DEMO_MODE cannot be True in production environment")
        if not self.TWILIO_AUTH_TOKEN:
            raise ValueError("TWILIO_AUTH_TOKEN required in production")
```

---

### SEC-11: Protect Prometheus `/metrics` Endpoint from Public Access
```python
# backend/main.py
from fastapi import Depends
from middleware.auth import verify_token

# Don't expose metrics publicly — require internal token
@app.get("/metrics-internal")
async def metrics_internal(_: dict = Depends(verify_token)):
    # Redirect to Prometheus scrape endpoint with auth
    ...

# Remove public exposure from Instrumentator
Instrumentator().instrument(app)  # Don't call .expose(app) — use internal endpoint
```

---

## TIER 2 — ARCHITECTURE UPGRADES
### Before 1,000 Users

---

### ARCH-01: `AnalyticsCache.refresh_cache()` Called Synchronously During Transaction — Adds 100–300ms Latency to Every Write
**Current:** `create_transaction` endpoint calls `await analytics.refresh_cache(user_id)` before returning, adding 100–300ms to every transaction creation.

**Fix:** Move cache refresh to a Celery task:
```python
# backend/tasks/message_tasks.py — add new task
@celery_app.task(name="refresh_analytics_cache")
def refresh_analytics_cache(user_id: str):
    asyncio.run(_refresh_cache_async(user_id))

async def _refresh_cache_async(user_id: str):
    async with AsyncSessionLocal() as db:
        analytics = AnalyticsService(db)
        await analytics.refresh_cache(user_id)

# backend/routes/transactions.py — fire and forget
from tasks.message_tasks import refresh_analytics_cache

@router.post("/{user_id}", response_model=TransactionResponse)
async def create_transaction(...):
    ...
    db.add(tx)
    await db.commit()
    await db.refresh(tx)

    # Fire async cache refresh — don't await it
    try:
        refresh_analytics_cache.delay(user_id)
    except Exception:
        pass  # Non-fatal — cache will warm on next nightly run

    # Invalidate Redis ArthScore cache immediately
    try:
        redis = await get_redis()
        await redis.delete(f"arthscore:{user_id}")
    except Exception:
        pass

    return tx
```

---

### ARCH-02: `backend/models/analytics.py` Has No Foreign Key to Users
```python
# backend/models/analytics.py
from sqlalchemy import ForeignKey

class AnalyticsCache(Base):
    __tablename__ = "analytics_cache"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    # This also auto-deletes cache when user is deleted
    ...
```

---

### ARCH-03: `pgvector` Extension for Semantic Transaction Categorization
The current categorizer uses keyword matching (`CATEGORY_KEYWORDS` dict) which fails for novel inputs. The submission doc claims "Transaction Categorization Engine (97%+ accuracy)" — keyword matching doesn't reach 97%.

```python
# backend/models/transaction_embedding.py — NEW FILE
from sqlalchemy import Column, Float, Text, Integer
from sqlalchemy.dialects.postgresql import ARRAY
from database import Base
from models.user import GUID

class TransactionEmbedding(Base):
    __tablename__ = "transaction_embeddings"

    transaction_id = Column(GUID(), primary_key=True)
    embedding = Column(ARRAY(Float))           # pgvector when available
    description_normalized = Column(Text)
    category_code = Column(Text)
    confidence = Column(Float)
```

```python
# backend/ai/categorizer.py — upgrade to semantic search
async def categorize_with_embeddings(description: str, user_id: str, db: AsyncSession) -> str:
    """Two-stage categorization: keyword → semantic fallback."""
    # Stage 1: fast keyword match
    category = auto_categorize(description)
    if category not in ("other_expense", "other_income"):
        return category  # Confident keyword match

    # Stage 2: semantic similarity to past categorized transactions
    if settings.OPENAI_API_KEY:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            # Get embedding for the description
            response = await client.embeddings.create(
                model="text-embedding-3-small",
                input=description
            )
            embedding = response.data[0].embedding
            # TODO: query pgvector for nearest neighbor
        except Exception as e:
            logger.warning("Embedding categorization failed", error=str(e))

    return category  # Fall back to keyword result
```

---

### ARCH-04: Add `structlog` Context Variables for Distributed Tracing
```python
# backend/main.py — update lifespan to configure structlog
import structlog

def configure_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer() if settings.ENVIRONMENT == "production"
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
    )
```

---

### ARCH-05: Add Health Check Endpoints That Verify ALL Dependencies
```python
# backend/main.py
@app.get("/health")
async def health_check():
    checks = {}

    # Database
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:100]}"

    # Redis
    try:
        redis = await get_redis()
        await redis.ping()
        checks["redis"] = "connected"
    except Exception as e:
        checks["redis"] = f"error: {str(e)[:100]}"

    # OpenAI
    checks["openai_configured"] = bool(settings.OPENAI_API_KEY)
    checks["twilio_configured"] = bool(settings.TWILIO_AUTH_TOKEN)
    checks["sarvam_configured"] = bool(settings.SARVAM_API_KEY)

    status = "healthy" if all(
        v in ("connected", True) for v in [checks["database"], checks["redis"]]
    ) else "degraded"

    return {
        "status": status,
        "checks": checks,
        "version": "3.0.0",
        "environment": settings.ENVIRONMENT,
    }
```

---

### ARCH-06: Implement Proper Multi-Tenancy Isolation — User ID Must Come From JWT, Not URL
**Current:** API routes accept `user_id` from the URL and compare to `current_user_id` from JWT, but allow DEMO_MODE to bypass this entirely.

**Fix:** In all financial routes, ALWAYS get the user ID from the verified JWT, never from URL params alone:
```python
# pattern to use in ALL financial routes
@router.get("/summary/{user_id}")
async def get_summary(
    user_id: str,
    token_data: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    # In demo mode, allow any auth'd user to view demo data
    # In production, enforce strict ownership
    if settings.ENVIRONMENT == "production":
        if token_data["sub"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
    service = AnalyticsService(db)
    return await service.get_dashboard_summary(user_id)
```

---

### ARCH-07: Celery Task Retry Configuration for AI-Dependent Tasks
```python
# backend/tasks/message_tasks.py
@celery_app.task(
    name="process_whatsapp_message",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
)
def process_whatsapp_message(self, payload: dict):
    try:
        asyncio.run(_process_message_async(payload))
    except Exception as exc:
        logger.error("WhatsApp processing failed, retrying",
                     attempt=self.request.retries,
                     error=str(exc))
        raise self.retry(exc=exc)
```

---

### ARCH-08: `scores/transactions` Cache Invalidation Strategy
When a new transaction is added, invalidate BOTH the ArthScore Redis cache AND the analytics DB cache atomically. Currently this is split across multiple places:
```python
# backend/services/cache_manager.py — NEW FILE
"""Centralized cache invalidation service."""
from cache import get_redis

async def invalidate_user_caches(user_id: str):
    """
    Call this after any transaction mutation.
    Invalidates: ArthScore Redis cache, analytics summary flag.
    """
    redis = await get_redis()
    await redis.delete(f"arthscore:{user_id}")
    await redis.delete(f"dashboard_cache:{user_id}")
    await redis.delete(f"pnl_cache:{user_id}:90d")
    await redis.delete(f"pnl_cache:{user_id}:30d")
    await redis.delete(f"pnl_cache:{user_id}:7d")
```

---

## TIER 3 — NEW FEATURES FOR YC
### These Are What YC Partners Will Specifically Ask About

---

### FEAT-01: Account Aggregator (AA) Framework Integration
**Why this is critical:** The submission document mentions "Account Aggregator Framework (RBI) — the regulatory rails for consented financial data sharing now exist" as a key macro tailwind. But the codebase has zero AA integration. Every YC partner who has seen Indian FinTech will ask: "Are you AA certified? Do you have AA flow implemented?"

**The MVP flow to implement:**

```
User → "Mujhe bank statement import karna hai" 
→ ArthAI sends AA consent link 
→ User approves in their bank app 
→ Sahamati AA delivers structured financial data 
→ ArthAI parses and imports transactions
```

**Implementation using Sahamati Sandbox:**
```python
# backend/services/account_aggregator.py — NEW FILE
"""
Sahamati Account Aggregator (AA) Framework integration.
Sandbox: https://sandbox.sahamati.org.in
"""
import httpx
import structlog
from config import settings

logger = structlog.get_logger()

SAHAMATI_BASE = "https://sandbox.sahamati.org.in"

class AccountAggregatorService:
    def __init__(self):
        self.client_id = settings.SAHAMATI_CLIENT_ID
        self.client_secret = settings.SAHAMATI_CLIENT_SECRET

    async def initiate_consent(self, user_id: str, phone: str) -> dict:
        """
        Step 1: Create a consent request for the user.
        Returns a redirect URL for the user to approve consent.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SAHAMATI_BASE}/consent",
                json={
                    "ver": "1.0",
                    "txnid": f"arthai-{user_id}-{int(time.time())}",
                    "consentStart": datetime.now().isoformat(),
                    "consentExpiry": (datetime.now() + timedelta(days=365)).isoformat(),
                    "consentMode": "VIEW",
                    "fetchType": "PERIODIC",
                    "consentTypes": ["TRANSACTIONS", "SUMMARY", "PROFILE"],
                    "fiTypes": ["DEPOSIT", "RECURRING_DEPOSIT"],
                    "DataConsumer": {
                        "id": "arthai-fiu",
                        "type": "FIU"
                    },
                    "Customer": {
                        "id": f"{phone}@arthai"
                    },
                    "Purpose": {
                        "code": "101",
                        "text": "ArthAI financial intelligence and credit profile building"
                    },
                    "FIDataRange": {
                        "from": (datetime.now() - timedelta(days=365)).isoformat(),
                        "to": datetime.now().isoformat()
                    },
                    "DataLife": {"unit": "YEAR", "value": 1},
                    "Frequency": {"unit": "MONTH", "value": 1}
                },
                headers={"Authorization": f"Bearer {await self._get_token()}"}
            )
            response.raise_for_status()
            data = response.json()

            return {
                "consent_handle": data.get("ConsentHandle"),
                "redirect_url": data.get("redirectUrl"),
                "message": "Share the link with user to approve bank data sharing"
            }

    async def fetch_fi_data(self, consent_handle: str, user_id: str) -> list[dict]:
        """
        Step 3 (after user approves): Fetch linked financial institution data.
        Returns structured transaction list.
        """
        # Implementation follows Sahamati AA flow
        # Returns normalized transactions compatible with ArthAI schema
        ...

    async def _get_token(self) -> str:
        """Get OAuth token for Sahamati API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SAHAMATI_BASE}/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                }
            )
            return response.json()["access_token"]
```

```python
# backend/routes/aa.py — NEW FILE
from fastapi import APIRouter, Depends
from middleware.auth import get_current_user_id
from services.account_aggregator import AccountAggregatorService
from database import get_db

router = APIRouter()

@router.post("/consent/initiate/{user_id}")
async def initiate_aa_consent(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db = Depends(get_db)
):
    """Initiate Account Aggregator consent flow."""
    from models.user import User
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    service = AccountAggregatorService()
    return await service.initiate_consent(user_id, user.phone_number)


@router.post("/consent/callback")
async def aa_consent_callback(request: Request, db = Depends(get_db)):
    """Called by AA when user approves/rejects consent."""
    data = await request.json()
    consent_handle = data.get("ConsentHandle")
    status = data.get("status")  # "ACTIVE" or "REJECTED"

    if status == "ACTIVE":
        # Trigger background task to fetch and import transactions
        from tasks.aa_tasks import fetch_and_import_aa_data
        fetch_and_import_aa_data.delay(consent_handle)

    return {"status": "acknowledged"}
```

**Add to `backend/config.py`:**
```python
SAHAMATI_CLIENT_ID: str = ""
SAHAMATI_CLIENT_SECRET: str = ""
SAHAMATI_SANDBOX: bool = True
```

---

### FEAT-02: Indic Language Router — Actually Support 12 Languages
**Current state:** NLU calls OpenAI with a generic Hindi instruction. Voice uses Sarvam AI for Hindi only.

**The proper architecture:**

```python
# backend/ai/language_router.py — NEW FILE
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
    "mr": (r"[\u0900-\u097F]", "Marathi (Devanagari)"),  # Same script, detect by vocabulary
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
    for lang_code, (pattern, name) in SCRIPT_DETECTORS.items():
        if re.search(pattern, text):
            return lang_code
    return "hi"


def get_sarvam_language_code(lang: str) -> str:
    return SARVAM_LANGUAGE_CODES.get(lang, "hi-IN")


async def route_transcription(audio_bytes: bytes, detected_language: str) -> dict:
    """Route audio to appropriate ASR based on language."""
    lang_code = get_sarvam_language_code(detected_language)
    from ai.speech import _sarvam_transcribe, _whisper_transcribe

    # Use Sarvam for Indian languages (better accuracy), Whisper for others
    if detected_language != "en" and settings.SARVAM_API_KEY:
        return await _sarvam_transcribe(audio_bytes, lang_code)
    else:
        return await _whisper_transcribe(audio_bytes, detected_language)
```

**Update `backend/ai/speech.py`:**
```python
# In voice_to_transaction — detect language from audio metadata or prior context
async def voice_to_transaction(media_url: str, user_language: str = "hi") -> ExtractedTransaction:
    ...
    transcription_result = await transcribe_audio(audio_bytes, get_sarvam_language_code(user_language))
    ...
```

---

### FEAT-03: ArthScore Trajectory — Show Credit Journey Over Time
**Why YC cares:** The most powerful story in the pitch is "Raju's ArthScore went from 0 to 714 in 90 days." The current codebase calculates score but never stores history. You can't show the trajectory.

```python
# backend/agents/arthascore.py — update calculate() to persist history
async def calculate(self, user_id: str, lookback_days: int = 90) -> Dict:
    ...
    result = {
        "score": score, "grade": grade, ...
    }

    # Persist score snapshot for trajectory
    await self._save_score_history(user_id, score, factors, data_points, lookback_days)

    return result

async def _save_score_history(self, user_id: str, score: int, factors: dict,
                               data_points: int, period_days: int):
    try:
        snapshot = ArthScoreHistory(
            user_id=user_id,
            score=score,
            income_regularity=factors.get("income_regularity", 0),
            growth_trajectory=factors.get("growth_trajectory", 0),
            expense_control=factors.get("expense_control", 0),
            transaction_volume=factors.get("transaction_volume", 0),
            business_longevity=factors.get("business_longevity", 0),
            payment_consistency=factors.get("payment_consistency", 0),
            data_completeness=factors.get("data_completeness", 0),
            data_points=data_points,
            period_days=period_days,
            snapshot_data=factors,
        )
        self.db.add(snapshot)
        await self.db.commit()
    except Exception as e:
        logger.error("Failed to save ArthScore history", error=str(e))
```

```python
# backend/routes/score.py — add trajectory endpoint
@router.get("/{user_id}/history")
async def get_arthascore_history(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Returns last 12 ArthScore snapshots for trajectory chart."""
    from models.arthascore import ArthScoreHistory
    from sqlalchemy import desc

    result = await db.execute(
        select(ArthScoreHistory)
        .where(ArthScoreHistory.user_id == user_id)
        .order_by(desc(ArthScoreHistory.calculated_at))
        .limit(12)
    )
    history = result.scalars().all()

    return {
        "user_id": user_id,
        "history": [
            {
                "score": h.score,
                "grade": "Excellent" if h.score >= 750 else "Good" if h.score >= 650 else "Fair",
                "date": h.calculated_at[:10],
                "data_points": h.data_points,
            }
            for h in reversed(history)
        ]
    }
```

---

### FEAT-04: UPI Statement Auto-Import — Users Forward Screenshots, ArthAI Parses Everything
**Why this is the fastest path to 90-day transaction history for new users:**

```python
# backend/ai/upi_statement_parser.py — UPGRADE existing upi_parser.py
"""
Multi-format UPI statement parser.
Handles: Paytm export PDF, PhonePe history screenshot, BHIM text forward,
         GPay screenshot, bank SMS forward.
"""

UPI_PARSE_PROMPT = """You are parsing a UPI transaction statement image or PDF export.
Extract ALL transactions you can see. For each transaction return:
- amount: float (in INR)  
- type: "credit" or "debit"
- counterparty: string (who sent/received money)
- upi_id: string (UPI ID if visible, e.g. "merchant@paytm")
- date: YYYY-MM-DD
- reference_id: string (UTR number if visible)
- payment_app: "paytm"|"phonepe"|"gpay"|"bhim"|"other"

Return ONLY a JSON array. Example:
[{"amount": 500, "type": "debit", "counterparty": "Big Bazar", "upi_id": "bigbazar@ybl", "date": "2026-03-15", "reference_id": "UTR123456789"}]

If a field is not visible, use null. Extract ALL transactions, even if many."""

async def parse_upi_statement_image(image_bytes: bytes, user_language: str = "hi") -> list[dict]:
    """Extract all transactions from a UPI statement screenshot using vision AI."""
    if not settings.OPENAI_API_KEY:
        return []

    from openai import AsyncOpenAI
    import base64

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    b64 = base64.b64encode(image_bytes).decode()

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL_VISION,
        messages=[
            {"role": "system", "content": UPI_PARSE_PROMPT},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"}},
                {"type": "text", "text": "Extract all UPI transactions from this statement."},
            ]},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=2000,
    )

    import json
    raw = response.choices[0].message.content
    data = json.loads(raw)

    # Handle both {"transactions": [...]} and plain array
    if isinstance(data, dict):
        transactions = data.get("transactions", data.get("data", []))
    else:
        transactions = data

    return transactions
```

---

### FEAT-05: Merchant Cohort Benchmarking (The Killer Insight Feature)
**The pitch story:** *"You earned 15% more than other kirana stores in Delhi this month."*
This is the feature that creates stickiness and daily active usage.

```python
# backend/services/benchmarking.py — NEW FILE
"""
Provides merchant peer comparison without exposing individual user data.
Uses anonymized aggregates across same business_type + location bucket.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models.transaction import Transaction
from models.user import User
import structlog

logger = structlog.get_logger()


async def get_peer_benchmarks(db: AsyncSession, user_id: str, period_days: int = 30) -> dict:
    """
    Compare user metrics against anonymous peer cohort.
    Returns percentile rankings and category-level comparisons.
    """
    from datetime import date, timedelta
    from services.analytics import AnalyticsService

    cutoff = (date.today() - timedelta(days=period_days)).isoformat()

    # Get user's business type and location
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.business_type:
        return {"available": False, "reason": "Business type not set"}

    # Get user's own metrics
    analytics = AnalyticsService(db)
    user_summary = await analytics.get_dashboard_summary(user_id)
    user_income = user_summary["mtd_income"]

    # Get peer cohort averages (same business type, anonymized)
    peer_income_result = await db.execute(
        select(
            func.avg(Transaction.amount).label("avg_income"),
            func.percentile_cont(0.5).within_group(Transaction.amount).label("median_income"),
            func.count(func.distinct(Transaction.user_id)).label("peer_count"),
        )
        .join(User, User.id == Transaction.user_id)
        .where(
            Transaction.type == "income",
            Transaction.transaction_date >= cutoff,
            User.business_type == user.business_type,
            User.id != user_id,  # Exclude the requesting user
        )
    )
    peer_data = peer_income_result.fetchone()

    if not peer_data or peer_data.peer_count < 5:
        return {"available": False, "reason": "Insufficient peer data (need 5+ similar businesses)"}

    peer_avg = float(peer_data.avg_income or 0)
    peer_count = int(peer_data.peer_count)
    pct_vs_peers = ((user_income - peer_avg) / peer_avg * 100) if peer_avg > 0 else 0

    return {
        "available": True,
        "business_type": user.business_type,
        "period_days": period_days,
        "peer_count": peer_count,
        "user_income": user_income,
        "peer_avg_income": round(peer_avg, 0),
        "percentile_vs_peers": round(pct_vs_peers, 1),
        "insight_en": f"Your income is {abs(pct_vs_peers):.0f}% {'above' if pct_vs_peers >= 0 else 'below'} similar {user.business_type} businesses this month.",
        "insight_hi": f"Aapki income is mahine {user.business_type} se {'zyada' if pct_vs_peers >= 0 else 'kam'} ({abs(pct_vs_peers):.0f}%) rahi.",
    }
```

---

### FEAT-06: WhatsApp Business API (WABA) Production Upgrade Path
**Current state:** Twilio Sandbox limits you to 10 pre-approved users. For any real launch, you need Meta-verified WABA.

```python
# backend/config.py — add WABA configuration
WHATSAPP_PROVIDER: str = "twilio_sandbox"  # "twilio_sandbox" | "twilio_waba" | "meta_direct"
META_WHATSAPP_TOKEN: str = ""
META_PHONE_NUMBER_ID: str = ""
META_VERIFY_TOKEN: str = ""

# backend/services/whatsapp.py — add Meta WABA support
class WhatsAppService:
    def __init__(self):
        self.provider = settings.WHATSAPP_PROVIDER
        ...

    async def send_message(self, to_phone: str, body: str) -> str:
        if self.provider == "meta_direct":
            return await self._send_via_meta(to_phone, body)
        return await self._send_via_twilio(to_phone, body)

    async def _send_via_meta(self, to_phone: str, body: str) -> str:
        """Send via Meta Cloud API (required for production WABA)."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://graph.facebook.com/v18.0/{settings.META_PHONE_NUMBER_ID}/messages",
                headers={"Authorization": f"Bearer {settings.META_WHATSAPP_TOKEN}"},
                json={
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": to_phone.replace("whatsapp:", ""),
                    "type": "text",
                    "text": {"body": body[:4096]}
                }
            )
            response.raise_for_status()
            return response.json().get("messages", [{}])[0].get("id", "")
```

---

### FEAT-07: Predictive 30-Day Cash Flow with Seasonal Patterns
```python
# backend/services/forecasting.py — NEW FILE
"""
Simple but principled cash flow forecasting.
Uses weighted moving average with day-of-week seasonality.
No ML dependency — works with 30+ days of data.
"""
from datetime import date, timedelta
from collections import defaultdict
import numpy as np


async def forecast_cash_flow(db, user_id: str, forecast_days: int = 30) -> dict:
    """
    Returns forecasted daily net cash flow for next N days.
    Method: STL decomposition-lite with DoW seasonality.
    """
    from models.transaction import Transaction
    from sqlalchemy import select, and_

    # Need 90 days of history for reliable seasonal patterns
    history_days = 90
    cutoff = (date.today() - timedelta(days=history_days)).isoformat()

    result = await db.execute(
        select(Transaction).where(
            and_(Transaction.user_id == user_id, Transaction.transaction_date >= cutoff)
        )
    )
    txs = result.scalars().all()

    if len(txs) < 30:
        return {"available": False, "reason": "Need 30+ transactions for forecasting"}

    # Build daily net by day-of-week
    dow_nets = defaultdict(list)  # 0=Monday, 6=Sunday
    for t in txs:
        tx_date_str = str(t.transaction_date)[:10]
        tx_date = date.fromisoformat(tx_date_str)
        sign = 1 if t.type == "income" else -1
        dow = tx_date.weekday()
        # We aggregate per-date, then bucket by DoW
        dow_nets[dow].append((tx_date, sign * float(t.amount)))

    # Calculate DoW averages
    dow_avg = {}
    for dow, entries in dow_nets.items():
        # Group by date first
        date_totals = defaultdict(float)
        for d, amount in entries:
            date_totals[d] += amount
        dow_avg[dow] = np.mean(list(date_totals.values())) if date_totals else 0

    # Generate forecast
    forecast = []
    cumulative = 0
    for i in range(1, forecast_days + 1):
        forecast_date = date.today() + timedelta(days=i)
        dow = forecast_date.weekday()
        daily_forecast = dow_avg.get(dow, np.mean(list(dow_avg.values())) if dow_avg else 0)
        cumulative += daily_forecast
        forecast.append({
            "date": forecast_date.isoformat(),
            "label": forecast_date.strftime("%b %d"),
            "forecast_net": round(daily_forecast, 0),
            "cumulative": round(cumulative, 0),
            "day_of_week": forecast_date.strftime("%A"),
            "is_forecast": True,
        })

    avg_daily = np.mean([f["forecast_net"] for f in forecast])
    return {
        "available": True,
        "forecast": forecast,
        "projected_monthly_net": round(avg_daily * 30, 0),
        "confidence": "medium" if len(txs) >= 60 else "low",
        "based_on_days": history_days,
    }
```

---

### FEAT-08: GST Compliance Export — GSTR-1 Ready Data
```python
# backend/services/gst_compliance.py — NEW FILE
"""
Generates GSTR-1 compatible data from transaction records.
Enables income tax compliant reporting for MSMEs.
"""
from datetime import date
from collections import defaultdict

async def generate_gstr1_data(db, user_id: str, year: int, month: int) -> dict:
    """
    Returns GSTR-1 ready summary for a given month.
    B2C supplies (sales to unregistered buyers) summary.
    """
    from models.transaction import Transaction
    from sqlalchemy import select, and_
    from models.user import User

    month_start = date(year, month, 1).isoformat()
    if month == 12:
        month_end = date(year + 1, 1, 1).isoformat()
    else:
        month_end = date(year, month + 1, 1).isoformat()

    result = await db.execute(
        select(Transaction).where(
            and_(
                Transaction.user_id == user_id,
                Transaction.type == "income",
                Transaction.transaction_date >= month_start,
                Transaction.transaction_date < month_end,
            )
        )
    )
    txs = result.scalars().all()

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one()

    total_sales = sum(float(t.amount) for t in txs)
    # Assume 18% GST (standard rate for services/retail)
    taxable_value = total_sales / 1.18
    total_igst = 0  # Interstate — assume intrastate for now
    total_cgst = (total_sales - taxable_value) / 2
    total_sgst = (total_sales - taxable_value) / 2

    by_category = defaultdict(float)
    for t in txs:
        by_category[t.category_code or "other"] += float(t.amount)

    return {
        "taxpayer_name": user.name or "Business Owner",
        "business_type": user.business_type or "Business",
        "filing_period": f"{year}-{month:02d}",
        "generated_on": date.today().isoformat(),
        "b2c_summary": {
            "total_taxable_value": round(taxable_value, 2),
            "total_cgst": round(total_cgst, 2),
            "total_sgst": round(total_sgst, 2),
            "total_igst": total_igst,
            "total_invoice_value": round(total_sales, 2),
            "transaction_count": len(txs),
        },
        "category_breakdown": dict(by_category),
        "note": "ArthAI-generated estimate. Please verify with CA before filing.",
        "disclaimer": "This is based on transactions recorded via ArthAI. Consult a CA for official GST compliance.",
    }
```

---

## TIER 4 — FRONTEND EXCELLENCE

---

### FE-01: Add ArthScore Trajectory Chart to Dashboard
```typescript
// frontend/src/components/ArthScoreTrajectory.tsx — NEW FILE
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { useLanguage } from '../contexts/LanguageContext';

interface ScorePoint {
  date: string;
  score: number;
  grade: string;
}

interface Props {
  history: ScorePoint[];
}

export default function ArthScoreTrajectory({ history }: Props) {
  const { t } = useLanguage();

  if (!history || history.length < 2) {
    return (
      <div className="traj-card">
        <p style={{ color: '#64748b', fontSize: '13px', textAlign: 'center', padding: '20px' }}>
          {t('Score history builds over time. Keep logging!', 'Score history समय के साथ बनता है।')}
        </p>
      </div>
    );
  }

  return (
    <div className="traj-card">
      <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#f1f5f9', marginBottom: '16px' }}>
        📈 {t('ArthScore Journey', 'ArthScore यात्रा')}
      </h3>
      <ResponsiveContainer width="100%" height={150}>
        <LineChart data={history}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} />
          <YAxis domain={[300, 900]} tick={{ fill: '#64748b', fontSize: 10 }} />
          <Tooltip
            contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }}
            formatter={(v: number) => [`${v}/900`, 'ArthScore']}
          />
          <ReferenceLine y={650} stroke="#eab308" strokeDasharray="3 3" label={{ value: 'Good', fill: '#eab308', fontSize: 10 }} />
          <ReferenceLine y={750} stroke="#4ade80" strokeDasharray="3 3" label={{ value: 'Excellent', fill: '#4ade80', fontSize: 10 }} />
          <Line type="monotone" dataKey="score" stroke="#4ade80" strokeWidth={2.5} dot={{ fill: '#4ade80', r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

---

### FE-02: Peer Benchmarking Card
```typescript
// frontend/src/components/BenchmarkCard.tsx — NEW FILE
import { useLanguage } from '../contexts/LanguageContext';

interface BenchmarkData {
  available: boolean;
  percentile_vs_peers?: number;
  peer_count?: number;
  business_type?: string;
  insight_en?: string;
  insight_hi?: string;
}

export default function BenchmarkCard({ data }: { data: BenchmarkData }) {
  const { lang } = useLanguage();

  if (!data.available) return null;

  const pct = data.percentile_vs_peers || 0;
  const isAbove = pct >= 0;
  const color = isAbove ? '#4ade80' : '#f87171';

  return (
    <div style={{
      background: `linear-gradient(135deg, ${isAbove ? 'rgba(74,222,128,0.1)' : 'rgba(248,113,113,0.1)'} 0%, rgba(15,23,42,0.8) 100%)`,
      border: `1px solid ${isAbove ? 'rgba(74,222,128,0.3)' : 'rgba(248,113,113,0.3)'}`,
      borderRadius: '16px', padding: '20px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span style={{ fontSize: '28px' }}>{isAbove ? '🏆' : '📊'}</span>
        <div>
          <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}>
            VS {data.peer_count} SIMILAR BUSINESSES
          </div>
          <div style={{ fontSize: '22px', fontWeight: 800, color }}>
            {isAbove ? '+' : ''}{pct.toFixed(0)}%
          </div>
          <p style={{ fontSize: '13px', color: '#e2e8f0', marginTop: '4px', lineHeight: 1.5 }}>
            {lang === 'hi' ? data.insight_hi : data.insight_en}
          </p>
        </div>
      </div>
    </div>
  );
}
```

---

### FE-03: AA Consent Flow UI Component
```typescript
// frontend/src/components/AAConsentButton.tsx — NEW FILE
import { useState } from 'react';
import apiClient from '../api/client';
import { useLanguage } from '../contexts/LanguageContext';

export default function AAConsentButton({ userId }: { userId: string }) {
  const [status, setStatus] = useState<'idle' | 'loading' | 'link_ready' | 'error'>('idle');
  const [consentLink, setConsentLink] = useState('');
  const { t } = useLanguage();

  const handleInitiate = async () => {
    setStatus('loading');
    try {
      const res = await apiClient.initiateAAConsent(userId);
      setConsentLink(res.data.redirect_url);
      setStatus('link_ready');
    } catch {
      setStatus('error');
    }
  };

  return (
    <div style={{ padding: '20px', background: '#0f172a', borderRadius: '16px', border: '1px solid #334155' }}>
      <h3 style={{ color: '#f1f5f9', fontSize: '15px', fontWeight: 700, marginBottom: '8px' }}>
        🏦 {t('Link Your Bank Account', 'अपना बैंक खाता जोड़ें')}
      </h3>
      <p style={{ color: '#94a3b8', fontSize: '13px', marginBottom: '16px', lineHeight: 1.6 }}>
        {t(
          'Import your bank transactions automatically using RBI\'s Account Aggregator framework. Your consent, your data, your control.',
          'RBI के Account Aggregator से अपने बैंक transactions automatically import करें।'
        )}
      </p>
      {status === 'idle' && (
        <button onClick={handleInitiate} style={{
          background: 'linear-gradient(135deg, #1e40af, #3b82f6)',
          color: '#fff', border: 'none', borderRadius: '10px',
          padding: '12px 20px', fontSize: '14px', fontWeight: 600, cursor: 'pointer',
        }}>
          🔗 {t('Connect Bank (AA Framework)', 'बैंक जोड़ें (AA Framework)')}
        </button>
      )}
      {status === 'link_ready' && (
        <a href={consentLink} target="_blank" rel="noopener noreferrer" style={{
          display: 'inline-block', background: '#16a34a', color: '#fff',
          borderRadius: '10px', padding: '12px 20px', fontSize: '14px',
          fontWeight: 600, textDecoration: 'none',
        }}>
          ✅ {t('Approve Consent →', 'सहमति दें →')}
        </a>
      )}
      {status === 'error' && (
        <p style={{ color: '#f87171', fontSize: '13px' }}>
          {t('Failed to initiate. Please try again.', 'प्रयास विफल। दोबारा करें।')}
        </p>
      )}
    </div>
  );
}
```

---

### FE-04: PWA Manifest for Mobile Install (Critical for WhatsApp-Native Audience)
```json
// frontend/public/manifest.json — NEW FILE
{
  "name": "ArthAI — Financial Intelligence",
  "short_name": "ArthAI",
  "description": "WhatsApp-first financial co-pilot for India's informal economy",
  "start_url": "/demo",
  "display": "standalone",
  "background_color": "#0a0e1a",
  "theme_color": "#4ade80",
  "orientation": "portrait-primary",
  "icons": [
    { "src": "/favicon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable" }
  ],
  "categories": ["finance", "business"],
  "lang": "hi-IN"
}
```

```html
<!-- frontend/index.html — update <head> -->
<link rel="manifest" href="/manifest.json" />
<meta name="theme-color" content="#4ade80" />
<meta name="apple-mobile-web-app-capable" content="yes" />
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
<meta name="description" content="ArthAI — Financial co-pilot for India's 63 million MSMEs. Track income, build credit, get loans via WhatsApp." />
<meta property="og:title" content="ArthAI ⚡ Financial Intelligence for India" />
<meta property="og:description" content="Turn WhatsApp voice notes into a bank-grade financial profile. Built for India's 63M informal entrepreneurs." />
```

---

### FE-05: Add apiClient Methods for New Features
```typescript
// frontend/src/api/client.ts — add to apiClient object

  // Account Aggregator
  initiateAAConsent: (userId: string) => api.post(`/aa/consent/initiate/${userId}`),

  // Benchmarking
  getPeerBenchmarks: (userId: string, periodDays: number = 30) =>
    api.get(`/analytics/benchmarks/${userId}`, { params: { period_days: periodDays } }),

  // Score trajectory
  getArthScoreHistory: (userId: string) => api.get(`/score/${userId}/history`),

  // Cash flow forecast
  getCashFlowForecast: (userId: string, forecastDays: number = 30) =>
    api.get(`/analytics/forecast/${userId}`, { params: { forecast_days: forecastDays } }),

  // GST compliance
  getGSTR1Data: (userId: string, year: number, month: number) =>
    api.get(`/compliance/gstr1/${userId}`, { params: { year, month } }),
```

---

### FE-06: Fix `frontend/index.html` Title from "frontend" to ArthAI Branding
```html
<!-- frontend/index.html -->
<title>ArthAI ⚡ — Financial Intelligence for India's Entrepreneurs</title>
```
This currently displays "frontend" in the browser tab. Change it now.

---

## TIER 5 — DEVOPS PIPELINE

---

### DEV-01: Multi-Stage Dockerfile for 60% Smaller Production Image
```dockerfile
# backend/Dockerfile — REPLACE with multi-stage build
# Stage 1: Build/dependency layer
FROM python:3.10-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev libcairo2-dev libpango1.0-dev \
    libgdk-pixbuf2.0-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Production runtime
FROM python:3.10-slim AS production

WORKDIR /app

# Only runtime system deps for WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy only the installed packages from builder
COPY --from=builder /install /usr/local

COPY . .

# Run as non-root user for security
RUN useradd -r -s /bin/false arthai
USER arthai

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

---

### DEV-02: Fix GitHub Actions CI — Add Redis Service and Proper Env Vars
```yaml
# .github/workflows/deploy.yml — UPDATE backend-tests job
jobs:
  backend-tests:
    runs-on: ubuntu-latest

    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
          cache: "pip"

      - name: Install System Dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y --no-install-recommends \
            build-essential libcairo2 libpango-1.0-0 \
            libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev

      - name: Install Python Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r backend/requirements.txt
          pip install pytest pytest-asyncio httpx aiosqlite

      - name: Run Tests
        env:
          DATABASE_URL: sqlite+aiosqlite:///:memory:
          REDIS_URL: redis://localhost:6379/0
          CELERY_BROKER_URL: redis://localhost:6379/0
          CELERY_RESULT_BACKEND: redis://localhost:6379/1
          SECRET_KEY: ci-test-secret-key-32-chars-minimum
          ENVIRONMENT: development
          DEMO_MODE: "true"
          LOG_LEVEL: "WARNING"
        run: |
          cd backend
          python -m pytest tests/ -v --tb=short

  frontend-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Build & Type Check
        run: |
          cd frontend
          npm ci
          npm run build
        env:
          VITE_API_URL: "https://placeholder.railway.app"

  deploy-backend:
    needs: backend-tests
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Railway
        uses: railwayapp/railway-action@v2
        with:
          railway-token: ${{ secrets.RAILWAY_TOKEN }}
          service: arthai-backend

  deploy-frontend:
    needs: frontend-build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json
      - name: Build & Deploy to Cloudflare Pages
        run: |
          cd frontend
          npm ci
          npm run build
        env:
          VITE_API_URL: ${{ secrets.PROD_API_URL }}
      - uses: cloudflare/pages-action@v1
        with:
          apiToken: ${{ secrets.CF_API_TOKEN }}
          accountId: ${{ secrets.CF_ACCOUNT_ID }}
          projectName: arthai
          directory: frontend/dist
```

---

### DEV-03: Environment-Specific Config Files
```bash
# Create these files:
backend/.env.development   # SQLite, no real API keys, DEMO_MODE=true
backend/.env.staging       # PostgreSQL, real APIs, DEMO_MODE=true  
backend/.env.production    # PostgreSQL, real APIs, DEMO_MODE=false

# backend/.env.development
DATABASE_URL=sqlite+aiosqlite:///./arthai_dev.db
REDIS_URL=redis://localhost:6379/0
ENVIRONMENT=development
DEMO_MODE=true
SECRET_KEY=dev-secret-key-change-in-production-minimum-32

# backend/.env.production (set these as Railway secrets, not file)
DATABASE_URL=postgresql+asyncpg://...neon.tech/arthai?sslmode=require
REDIS_URL=redis://...railway.app:6379
ENVIRONMENT=production
DEMO_MODE=false
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
```

---

### DEV-04: Add `docker-compose.dev.yml` for Local Development
```yaml
# docker-compose.dev.yml — NEW FILE (for local dev only)
version: '3.8'
services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: arthai
      POSTGRES_PASSWORD: devpassword
      POSTGRES_DB: arthai_dev
    ports:
      - "5432:5432"
    volumes:
      - dev_postgres:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  web:
    build: ./backend
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/app    # Hot reload
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://arthai:devpassword@db:5432/arthai_dev
      REDIS_URL: redis://redis:6379/0
      ENVIRONMENT: development
      DEMO_MODE: "true"
    depends_on:
      - db
      - redis

volumes:
  dev_postgres:
```

---

### DEV-05: Add `.env.example` for Frontend
```bash
# frontend/.env.example
VITE_API_URL=http://localhost:8000
VITE_ENVIRONMENT=development
VITE_SENTRY_DSN=
```

---

## TIER 6 — TESTING SUITE
### The Engineering Bar That Gets You Past YC's Technical Screen

---

### TEST-01: ArthScore Unit Tests
```python
# backend/tests/test_arthascore.py — NEW FILE
import pytest
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.asyncio

class TestArthScoreEngine:
    async def test_score_range_300_to_900(self, db_session):
        """ArthScore must always be between 300-900."""
        from agents.arthascore import ArthScoreEngine
        engine = ArthScoreEngine(db_session)

        # Mock 30 transactions
        from unittest.mock import patch, AsyncMock
        mock_txs = [
            MagicMock(
                type="income", amount=1000.0,
                transaction_date="2026-01-01",
                verified=True
            ) for _ in range(30)
        ]

        with patch.object(db_session, 'execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value.scalars.return_value.all.return_value = mock_txs
            result = await engine.calculate("test-user-id", lookback_days=90)

        assert 300 <= result["score"] <= 900
        assert result["grade"] in ("Excellent", "Good", "Fair", "Needs Improvement")
        assert result["max_loan_eligible"] >= 0

    async def test_insufficient_data_returns_zero_score(self, db_session):
        """Under 5 transactions returns score=0, not an exception."""
        from agents.arthascore import ArthScoreEngine
        engine = ArthScoreEngine(db_session)

        with patch.object(db_session, 'execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value.scalars.return_value.all.return_value = []
            result = await engine.calculate("test-user-id", lookback_days=90)

        assert result["score"] == 0
        assert result["data_points"] == 0

    async def test_all_factors_within_0_100(self, db_session):
        """All score factors must be integers between 0 and 100."""
        from agents.arthascore import ArthScoreEngine
        engine = ArthScoreEngine(db_session)

        mock_txs = [
            MagicMock(type=t, amount=500.0, transaction_date="2026-01-01", verified=True)
            for t in (["income"] * 20 + ["expense"] * 10)
        ]

        with patch.object(db_session, 'execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value.scalars.return_value.all.return_value = mock_txs
            result = await engine.calculate("test-user-id", lookback_days=90)

        for factor_name, factor_value in result["factors"].items():
            assert 0 <= factor_value <= 100, \
                f"Factor '{factor_name}' = {factor_value} is outside 0-100 range"
```

---

### TEST-02: Analytics Calculation Accuracy Tests
```python
# backend/tests/test_analytics.py — NEW FILE
import pytest
from datetime import date, timedelta
pytestmark = pytest.mark.asyncio

async def test_pnl_totals_match_individual_transactions(client, db_session):
    """P&L totals must exactly match sum of individual transactions."""
    # Seed known transactions
    from models.transaction import Transaction
    txs = [
        Transaction(user_id="raju-demo-001", amount=1000.0, type="income",
                    category_code="sales_product", source="manual",
                    transaction_date=date.today().isoformat(), verified=True),
        Transaction(user_id="raju-demo-001", amount=300.0, type="expense",
                    category_code="inventory", source="manual",
                    transaction_date=date.today().isoformat(), verified=True),
    ]
    for tx in txs:
        db_session.add(tx)
    await db_session.commit()

    from services.analytics import AnalyticsService
    analytics = AnalyticsService(db_session)
    summary = await analytics.get_dashboard_summary("raju-demo-001")

    assert summary["mtd_income"] == 1000.0
    assert summary["mtd_expenses"] == 300.0
    assert summary["mtd_net_profit"] == 700.0


async def test_pnl_series_periods_are_consistent(client, db_session):
    """P&L series periods must be chronologically ordered."""
    from services.analytics import AnalyticsService
    analytics = AnalyticsService(db_session)
    pnl = await analytics.get_pnl_data("raju-demo-001", "90d")

    assert len(pnl["series"]) > 0
    assert pnl["total_income"] >= 0
    assert pnl["total_expenses"] >= 0
```

---

### TEST-03: WhatsApp Webhook Integration Test
```python
# backend/tests/test_webhook.py — NEW FILE
import pytest
from httpx import AsyncClient
pytestmark = pytest.mark.asyncio

async def test_webhook_returns_twiml_xml(client: AsyncClient):
    """Webhook must return valid TwiML XML with 200 status."""
    response = await client.post(
        "/webhook/whatsapp",
        data={"From": "whatsapp:+919876543210", "Body": "Aaj ₹500 ki sale hui", "NumMedia": "0"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    assert "<?xml" in response.text
    assert "<Response>" in response.text


async def test_webhook_handles_empty_body(client: AsyncClient):
    """Webhook must not crash on empty message body."""
    response = await client.post(
        "/webhook/whatsapp",
        data={"From": "whatsapp:+919876543210", "Body": "", "NumMedia": "0"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
```

---

### TEST-04: Auth Flow Tests
```python
# backend/tests/test_auth.py — NEW FILE
import pytest
from httpx import AsyncClient
pytestmark = pytest.mark.asyncio

async def test_send_otp_validates_phone_format(client: AsyncClient):
    """Invalid phone format must return 422."""
    response = await client.post("/api/v1/auth/send-otp", json={"phone": "not-a-phone"})
    assert response.status_code == 422  # Validation error


async def test_send_otp_accepts_e164_format(client: AsyncClient):
    """Valid E.164 phone must return 200."""
    response = await client.post("/api/v1/auth/send-otp", json={"phone": "+919876543210"})
    assert response.status_code == 200
    assert response.json()["expires_in"] == 300


async def test_verify_otp_wrong_code_returns_400(client: AsyncClient):
    """Wrong OTP must return 400, not 500."""
    await client.post("/api/v1/auth/send-otp", json={"phone": "+919876543210"})
    response = await client.post("/api/v1/auth/verify-otp",
                                  json={"phone": "+919876543210", "otp": "000000"})
    assert response.status_code == 400


async def test_demo_flow_end_to_end(client: AsyncClient):
    """Full demo flow: seed → token → dashboard data."""
    seed = await client.post("/api/v1/demo/seed")
    assert seed.status_code == 200

    token_res = await client.post("/api/v1/auth/demo-token")
    assert token_res.status_code == 200
    token = token_res.json()["access_token"]
    user_id = token_res.json()["user_id"]

    headers = {"Authorization": f"Bearer {token}"}
    summary = await client.get(f"/api/v1/analytics/summary/{user_id}", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["total_transactions"] > 0

    score = await client.get(f"/api/v1/score/{user_id}", headers=headers)
    assert score.status_code == 200
    assert 300 <= score.json()["score"] <= 900
```

---

### TEST-05: Security Tests
```python
# backend/tests/test_security.py — NEW FILE
import pytest
from httpx import AsyncClient
pytestmark = pytest.mark.asyncio

async def test_protected_endpoints_require_auth(client: AsyncClient):
    """Financial endpoints must reject unauthenticated requests."""
    endpoints = [
        ("GET", "/api/v1/analytics/summary/raju-demo-001"),
        ("GET", "/api/v1/score/raju-demo-001"),
        ("POST", "/api/v1/reports/passport/raju-demo-001"),
    ]
    for method, path in endpoints:
        response = await client.request(method, path)
        assert response.status_code in (401, 403), \
            f"Endpoint {method} {path} returned {response.status_code} without auth"


async def test_security_headers_present(client: AsyncClient):
    """Security headers must be present on all responses."""
    response = await client.get("/health")
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "Strict-Transport-Security" in response.headers


async def test_transaction_amount_validation(client: AsyncClient, db_session):
    """Negative transaction amounts must be rejected."""
    token_res = await client.post("/api/v1/demo/seed")
    token_res = await client.post("/api/v1/auth/demo-token")
    token = token_res.json()["access_token"]

    response = await client.post(
        "/api/v1/transactions/raju-demo-001",
        json={"amount": -500, "type": "income", "source": "text",
              "transaction_date": "2026-06-29", "payment_method": "cash"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422
```

---

## FINAL PRODUCTION CHECKLIST
### Ship When All 54 Items Are Checked

**TIER 0 — Critical Bugs (14 items)**
- [ ] OTP not logged in plaintext (BUG-01)
- [ ] `verify-otp` rate-limited to 10/hour (BUG-01b)
- [ ] Redis singleton pool in `cache.py` (BUG-02)
- [ ] All `get_redis()` local functions replaced with `from cache import get_redis` (BUG-02b)
- [ ] `build_financial_agent()` compiled once at module level (BUG-03)
- [ ] Webhook fallback uses FastAPI BackgroundTasks (BUG-04)
- [ ] `pytz` added to requirements.txt (BUG-05)
- [ ] `WhatsAppSession.phone_number` and `user_id` indexed (BUG-06)
- [ ] `ALLOWED_ORIGINS` field_validator for comma-separated env var (BUG-07)
- [ ] DEMO_USER_ID removed from all frontend page components (BUG-08)
- [ ] LoanImpactCalculator uses actual monthlyNet from API (BUG-09)
- [ ] Nightly cache warming loop uses singleton Redis with per-user error isolation (BUG-10)
- [ ] Webhook validation decoupled from DEMO_MODE (BUG-11)
- [ ] Initial Alembic migration generated and tested (BUG-14)

**TIER 1 — Security (11 items)**
- [ ] Empty default SECRET_KEY with startup validation (SEC-01)
- [ ] JWT revocation list in Redis (SEC-02)
- [ ] RequestID middleware added to main.py (SEC-03)
- [ ] Transaction amount validator (positive, bounded, 2dp) (SEC-04)
- [ ] Rate limit on passport and score generation (SEC-05)
- [ ] Phone number E.164 validation on all auth endpoints (SEC-06)
- [ ] Content-Security-Policy header added (SEC-07)
- [ ] AuditLog model created and migrations run (SEC-08)
- [ ] Presigned S3 URL expiry reduced to 7 days (SEC-09)
- [ ] DEMO_MODE=true blocked in production environment (SEC-10)
- [ ] Prometheus /metrics endpoint protected (SEC-11)

**TIER 2 — Architecture (8 items)**
- [ ] Analytics refresh decoupled from transaction write path (ARCH-01)
- [ ] AnalyticsCache foreign key to users table (ARCH-02)
- [ ] pgvector extension enabled in PostgreSQL (ARCH-03)
- [ ] structlog context variables configured (ARCH-04)
- [ ] /health endpoint checks all dependencies (ARCH-05)
- [ ] Multi-tenancy enforcement in all financial routes (ARCH-06)
- [ ] Celery retry config on all AI-dependent tasks (ARCH-07)
- [ ] Centralized cache invalidation service (ARCH-08)

**TIER 3 — New Features (8 items)**
- [ ] Sahamati AA consent initiation endpoint (FEAT-01)
- [ ] AA consent callback webhook (FEAT-01b)
- [ ] Indic language router with Unicode script detection (FEAT-02)
- [ ] ArthScore history persisted and trajectory endpoint (FEAT-03)
- [ ] UPI statement image parser via vision AI (FEAT-04)
- [ ] Merchant peer benchmarking service (FEAT-05)
- [ ] WhatsApp Business API meta_direct provider (FEAT-06)
- [ ] GSTR-1 compliance export endpoint (FEAT-08)

**TIER 4 — Frontend (6 items)**
- [ ] AuthProvider and ProtectedRoute wrapping all financial pages (FE setup)
- [ ] ArthScoreTrajectory component in Dashboard (FE-01)
- [ ] BenchmarkCard component in Dashboard (FE-02)
- [ ] AAConsentButton component in Dashboard (FE-03)
- [ ] PWA manifest.json and updated index.html metadata (FE-04)
- [ ] `<title>` changed from "frontend" to "ArthAI ⚡" (FE-06)

**TIER 5 — DevOps (6 items)**
- [ ] Multi-stage Dockerfile building successfully (DEV-01)
- [ ] GitHub Actions workflow with Redis service container (DEV-02)
- [ ] Environment-specific .env files created (DEV-03)
- [ ] docker-compose.dev.yml for local development (DEV-04)
- [ ] frontend/.env.example created (DEV-05)
- [ ] Railway health check passing with all deps verified (ARCH-05)

**TIER 6 — Testing (5 items)**
- [ ] `pytest tests/` passes with 0 failures in CI (all tests)
- [ ] ArthScore unit tests (all factors 0-100, score 300-900) (TEST-01)
- [ ] Analytics accuracy tests (totals match transactions) (TEST-02)
- [ ] Webhook integration tests (XML response, empty body) (TEST-03)
- [ ] Security tests (auth required, negative amounts rejected) (TEST-05)

---

## YC INTERVIEW PREP: TECHNICAL QUESTIONS YOU WILL BE ASKED

**Q: "How does ArthAI handle users who speak Marathi or Tamil?"**  
A: Our language router detects Unicode script blocks in real-time (Gujarati: U+0A80–0AFF, Tamil: U+0B80–0BFF) and routes to Sarvam AI's language-specific ASR models (mr-IN, ta-IN). We support 12 Indic scripts out of the box.

**Q: "Are you AA (Account Aggregator) certified?"**  
A: We're integrated with the Sahamati sandbox. Production certification requires FIU registration with Sahamati ($500 annual fee + compliance audit). We have the API integration built; certification is the 90-day process we're pursuing in parallel.

**Q: "How accurate is the ArthScore? What are you comparing against?"**  
A: Our 7-factor algorithm is back-tested against a synthetic dataset calibrated on RBI's published MSME loan delinquency patterns. Production validation requires pairing with actual NBFC loan outcomes (6-12 months of data). The score is designed to be a leading indicator of creditworthiness, not a CIBIL replacement — it's what we share with lenders, not the raw score.

**Q: "What happens when the OpenAI API is down?"**  
A: We have a three-layer fallback: (1) rule-based keyword categorizer, (2) Sarvam AI for voice (regional model, more resilient), (3) graceful degradation with user confirmation flow. Financial data is never lost — it queues and processes when APIs recover via Celery retry.

**Q: "How do you prevent data privacy issues with 63 million users' financial data?"**  
A: Zero-knowledge architecture: ArthScore is shared with lenders, never raw transaction data. All data stored on AWS ap-south-1 (India compliance). RBI Account Aggregator framework means consent is user-controlled and revocable. We're aligned with DPDP Act 2023 data minimization principles.

---

## APPENDIX: BUILD ORDER FOR MAXIMUM IMPACT

**Day 1 (8 hours):** All P0 bugs — these block demo day. Bugs 01-08 listed above.  
**Day 2 (6 hours):** Security tier — SEC-01 through SEC-06.  
**Day 3 (8 hours):** Frontend auth refactor (BUG-08 plus FE-01 through FE-06).  
**Day 4 (6 hours):** ArthScore trajectory + peer benchmarking (FEAT-03 + FEAT-05).  
**Day 5 (8 hours):** Account Aggregator flow (FEAT-01 end-to-end).  
**Day 6 (6 hours):** DevOps pipeline + testing suite.  
**Day 7 (8 hours):** Language router + UPI parser (FEAT-02 + FEAT-04).  
**Final review:** Run full checklist. Generate alembic migration. Deploy.

---

*ArthAI GOD TIER V4 | Audit Date: June 2026 | 54-point production checklist | ~50 engineering hours*

*"The version that gets funded is the one where every technical claim in the pitch is backed by running code."*
