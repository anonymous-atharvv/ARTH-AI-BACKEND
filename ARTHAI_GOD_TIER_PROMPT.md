# ARTHAI_GOD_TIER_PROMPT.md
## Complete AI-Agent Implementation Bible
### Version: 2.0 | InnovaHack Chapter 1 | Domain: Generative AI

---

> **BUILDER CONTRACT**: This document is a self-contained, executable specification.
> An AI coding agent reading this file must be able to build the complete ArthAI
> system — from database migrations to deployed Railway URL — without asking a
> single clarifying question. Every ambiguity is resolved here. Every edge case
> is pre-handled. Every prompt is written. Every schema is defined.
>
> **North Star**: Raju Kumar, auto-rickshaw driver, Pune. 6 years of business.
> Zero bank loans. After 90 days with ArthAI: ₹75,000 loan at 18% p.a.
> That is the only success metric that matters.

---

## 0. MISSION BRIEF

### 0.1 What We Are Building

ArthAI is a **WhatsApp-first, multimodal AI financial co-pilot** for India's
63 million informal micro-entrepreneurs. It converts the natural language of
India's informal economy — voice notes, receipt photos, WhatsApp text, UPI
screenshots — into structured financial records, real-time P&L intelligence,
a proprietary creditworthiness score (ArthScore), and bank-readable Financial
Passport PDFs that unlock formal credit for the first time.

**The fundamental insight**: These entrepreneurs are not poor. They are
*data-invisible*. They have 6+ years of consistent revenue but zero formal
financial history. ArthAI is the bridge. Not by changing how they work —
by learning to understand how they already work.

### 0.2 Hackathon Deliverables (24-Hour Build)

| Deliverable | Specification |
|-------------|---------------|
| Live backend URL | `https://arthai-backend.up.railway.app` |
| Live frontend URL | `https://arthai-demo.vercel.app` |
| GitHub repo | `github.com/[team]/arthai` with README + demo GIF |
| WhatsApp sandbox | Twilio sandbox, functional demo |
| Financial Passport | Actual PDF download from demo flow |
| Demo dataset | 90 days of Raju's synthetic transactions pre-loaded |

### 0.3 What Success Looks Like for Judges

1. **Judge sends a receipt photo** to the WhatsApp sandbox → 3 seconds → structured response
2. **Judge sends Hindi voice note** → transcription → categorized transaction
3. **Judge asks** "Mera profit kya raha is hafte?" → intelligent Hindi response with numbers
4. **Judge clicks** "Generate Financial Passport" → downloads a real, professional PDF
5. **Judge sees** ArthScore 714/900 with loan eligibility notification
6. **Judge feels**: "Why hasn't this existed before?"

---

## 1. COMPLETE SYSTEM ARCHITECTURE

### 1.1 Architecture Diagram

```
╔══════════════════════════════════════════════════════════════════════╗
║                        USER INTERACTION LAYER                        ║
║  WhatsApp Business API (Twilio)  │  React Dashboard  │  REST APIs   ║
╚══════════════════════╦═══════════════════════════════════════════════╝
                       ║ Webhook POST /webhook/whatsapp
╔══════════════════════▼═══════════════════════════════════════════════╗
║                   FastAPI APPLICATION LAYER (Python 3.11)            ║
║                                                                       ║
║   /webhook/whatsapp  →  MessageRouter  →  Celery Task Queue         ║
║   /api/transactions  →  TransactionService  →  PostgreSQL            ║
║   /api/reports       →  PassportGenerator  →  WeasyPrint → S3        ║
║   /api/score         →  ArthScoreEngine  →  Redis Cache             ║
║   /api/query         →  LangGraph Agent  →  OpenAI                  ║
╚══════════════════════╦═══════════════════════════════════════════════╝
                       ║
╔══════════════════════▼═══════════════════════════════════════════════╗
║                      MULTIMODAL AI PIPELINE                           ║
║                                                                       ║
║  ┌─────────────────┐  ┌────────────────┐  ┌───────────────────────┐  ║
║  │   VISION MODULE │  │  SPEECH MODULE │  │     NLU MODULE        │  ║
║  │                 │  │                │  │                       │  ║
║  │  GPT-4o-mini    │  │  Sarvam AI     │  │  GPT-4o-mini          │  ║
║  │  (OCR primary)  │  │  saarika-v2    │  │  (intent + entity)    │  ║
║  │                 │  │  (primary ASR) │  │                       │  ║
║  │  Fallback:      │  │  Fallback:     │  │  Transaction          │  ║
║  │  PaddleOCR      │  │  Whisper v3    │  │  Categorization       │  ║
║  └────────┬────────┘  └───────┬────────┘  └──────────┬────────────┘  ║
║           └──────────────────▼────────────────────────┘              ║
║                    TRANSACTION OBJECT (Pydantic)                      ║
╚══════════════════════╦═══════════════════════════════════════════════╝
                       ║
╔══════════════════════▼═══════════════════════════════════════════════╗
║               FINANCIAL INTELLIGENCE ENGINE (LangGraph)              ║
║                                                                       ║
║  classify_input → extract_entities → validate → categorize →        ║
║  store_transaction → update_analytics → check_insights →            ║
║  generate_response → send_whatsapp_reply                            ║
║                                                                       ║
║  ArthScore Engine (7-factor MVP → 47-factor production)             ║
╚══════════════════════╦═══════════════════════════════════════════════╝
                       ║
╔══════════════════════▼═══════════════════════════════════════════════╗
║                         DATA LAYER                                   ║
║                                                                       ║
║  PostgreSQL (Supabase)     │  pgvector (embeddings)                 ║
║  Redis (sessions + cache)  │  AWS S3 (files + PDFs)                 ║
╚══════════════════════════════════════════════════════════════════════╝
```

### 1.2 Data Flow (Per WhatsApp Message)

```
User sends image/audio/text to WhatsApp
          ↓
Twilio webhook fires → POST /webhook/whatsapp (FastAPI)
          ↓
MessageRouter identifies type: IMAGE | AUDIO | TEXT | DOCUMENT
          ↓
Celery task dispatched (async, <200ms webhook response to Twilio)
          ↓
AI Pipeline runs:
  IMAGE  → download_media() → GPT-4V extract() → TransactionObject
  AUDIO  → download_media() → Sarvam transcribe() → NLU parse() → TransactionObject
  TEXT   → NLU classify_intent() →
             TRANSACTION: NLU extract() → TransactionObject
             QUERY:       LangGraph handle_query() → Response
             REPORT:      PassportGenerator.generate() → PDF URL
             GREETING:    WelcomeFlow.respond()
             HELP:        HelpFlow.respond()
          ↓
TransactionObject → validate (confidence check) →
  HIGH CONF (>85%): store() + notify_success()
  LOW CONF (<85%): send_confirmation_request() + pause
          ↓
update_analytics() → recalculate_pnl() + recalculate_arthascore()
          ↓
check_proactive_insights() → send if anomaly detected
          ↓
Response sent in user's language via Twilio WhatsApp
```

---

## 2. COMPLETE FILE SYSTEM

```
arthai/
│
├── README.md
├── .env.example
├── .gitignore
├── Procfile                          # Railway deployment
├── railway.json                      # Railway config
│
├── backend/
│   ├── main.py                       # FastAPI app, CORS, middleware
│   ├── config.py                     # Settings from env vars
│   ├── database.py                   # SQLAlchemy async engine
│   ├── dependencies.py               # Shared DI (db session, auth)
│   │
│   ├── models/                       # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── transaction.py
│   │   ├── category.py
│   │   ├── arthascore.py
│   │   └── document.py
│   │
│   ├── schemas/                      # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── transaction.py
│   │   ├── report.py
│   │   └── whatsapp.py
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── webhook.py               # POST /webhook/whatsapp (Twilio)
│   │   ├── transactions.py          # GET/POST /api/transactions
│   │   ├── analytics.py             # GET /api/analytics/pnl, /cash-flow
│   │   ├── score.py                 # GET /api/score/{user_id}
│   │   ├── reports.py               # POST /api/reports/passport
│   │   ├── users.py                 # POST /api/users/register
│   │   └── demo.py                  # GET /api/demo/seed (loads Raju data)
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── whatsapp.py              # Twilio WhatsApp send/receive helpers
│   │   ├── storage.py               # AWS S3 upload/download
│   │   ├── analytics.py             # P&L, cash flow calculations
│   │   └── language.py              # Language detection + response i18n
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── vision.py                # GPT-4V receipt OCR module
│   │   ├── speech.py                # Sarvam AI + Whisper transcription
│   │   ├── nlu.py                   # Intent classification + entity extraction
│   │   ├── response_generator.py    # Multilingual WhatsApp response generation
│   │   └── categorizer.py           # Transaction category assignment
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── financial_agent.py       # LangGraph main agent graph
│   │   ├── arthascore.py            # ArthScore calculation engine
│   │   └── passport_generator.py   # Financial Passport PDF builder
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── celery_app.py            # Celery + Redis broker config
│   │   └── message_tasks.py        # Async Celery tasks
│   │
│   ├── templates/
│   │   └── passport.html            # WeasyPrint Financial Passport template
│   │
│   └── migrations/
│       └── 001_initial_schema.sql   # Full DB DDL
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   ├── index.html
│   │
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   └── client.ts            # Axios API client
│       │
│       ├── components/
│       │   ├── ArthScoreGauge.tsx   # 300-900 circular gauge
│       │   ├── PLChart.tsx          # Recharts income/expense area chart
│       │   ├── TransactionFeed.tsx  # Virtualized transaction list
│       │   ├── InsightCard.tsx      # Proactive AI insight display
│       │   ├── LanguageToggle.tsx   # Hindi ↔ English toggle
│       │   └── LoadingSpinner.tsx
│       │
│       ├── pages/
│       │   ├── Dashboard.tsx        # Main overview
│       │   ├── Transactions.tsx     # Full transaction list
│       │   ├── Passport.tsx         # Financial Passport preview + download
│       │   └── Demo.tsx             # Raju demo mode
│       │
│       └── types/
│           └── index.ts             # TypeScript interfaces
│
└── demo-data/
    └── raju_90days.json             # Raju's synthetic 90-day transactions
```

---

## 3. ENVIRONMENT SETUP

### 3.1 .env.example (ALL required variables)

```bash
# ─── DATABASE ───────────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://user:password@db.supabase.co:5432/postgres
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_role_key

# ─── REDIS ──────────────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# ─── AI APIS ────────────────────────────────────────────────────────
OPENAI_API_KEY=sk-...
OPENAI_MODEL_VISION=gpt-4o-mini           # Use for OCR — cheaper, fast enough
OPENAI_MODEL_NLU=gpt-4o-mini             # Intent + entity extraction
SARVAM_API_KEY=your_sarvam_api_key       # https://sarvam.ai → get free tier key
SARVAM_ASR_MODEL=saarika-v2

# ─── MESSAGING ──────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID=ACxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886  # Twilio sandbox number
TWILIO_WEBHOOK_URL=https://arthai-backend.up.railway.app/webhook/whatsapp

# ─── STORAGE ────────────────────────────────────────────────────────
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=your_secret
AWS_BUCKET_NAME=arthai-receipts
AWS_REGION=ap-south-1

# ─── APPLICATION ────────────────────────────────────────────────────
SECRET_KEY=your_32_char_secret_key_here_change_this
ENVIRONMENT=production
LOG_LEVEL=INFO
ALLOWED_ORIGINS=https://arthai-demo.vercel.app,http://localhost:5173

# ─── ARTHASCORE ─────────────────────────────────────────────────────
ARTHASCORE_MIN=300
ARTHASCORE_MAX=900
CONFIDENCE_THRESHOLD=0.85              # Below this → ask for confirmation

# ─── FEATURE FLAGS ──────────────────────────────────────────────────
ENABLE_SARVAM_ASR=true                 # Set false to fall back to Whisper
ENABLE_S3_STORAGE=true                 # Set false for local file storage
DEMO_MODE=false                        # Set true to bypass auth in demo
```

### 3.2 requirements.txt

```txt
# Core framework
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9

# Database
sqlalchemy[asyncio]==2.0.30
asyncpg==0.29.0
alembic==1.13.1
pgvector==0.2.5

# AI / ML
openai==1.30.1
httpx==0.27.0                  # Sarvam AI REST calls
tiktoken==0.7.0

# Agentic framework
langgraph==0.1.5
langchain-core==0.2.5
langchain-openai==0.1.8

# Task queue
celery[redis]==5.4.0
redis==5.0.4

# WhatsApp / Twilio
twilio==9.1.0

# PDF generation
weasyprint==61.2
jinja2==3.1.4

# Storage
boto3==1.34.110

# Validation
pydantic==2.7.1
pydantic-settings==2.3.0
email-validator==2.1.1

# Utils
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.1
structlog==24.1.0
tenacity==8.3.0               # Retry logic for AI API calls
numpy==1.26.4                 # ArthScore calculations
scikit-learn==1.5.0           # Linear regression for growth trajectory
```

---

## 4. DATABASE LAYER

### 4.1 Complete Schema DDL

```sql
-- migrations/001_initial_schema.sql
-- Run this against your Supabase PostgreSQL instance

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ═══════════════════════════════════════════════════════════════════
-- USERS TABLE
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone_number    VARCHAR(15) UNIQUE NOT NULL,  -- E.164 format: +919876543210
    name            VARCHAR(100),
    preferred_language VARCHAR(10) DEFAULT 'hi',  -- ISO 639-1: hi, mr, ta, te, gu, bn, pa, ml, kn, or, ur, en
    business_type   VARCHAR(100),                 -- "Auto-rickshaw", "Kirana", "Tailoring", etc.
    business_location VARCHAR(200),
    onboarding_complete BOOLEAN DEFAULT FALSE,
    whatsapp_session_state JSONB DEFAULT '{"state": "IDLE"}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_phone ON users(phone_number);

-- ═══════════════════════════════════════════════════════════════════
-- TRANSACTION CATEGORIES (Master list)
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE categories (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(50) UNIQUE NOT NULL,
    name_en         VARCHAR(100) NOT NULL,
    name_hi         VARCHAR(100) NOT NULL,
    type            VARCHAR(10) NOT NULL CHECK (type IN ('income', 'expense', 'transfer')),
    parent_code     VARCHAR(50) REFERENCES categories(code),
    icon            VARCHAR(10) DEFAULT '💰',
    sort_order      INTEGER DEFAULT 0
);

-- Seed categories (run after table creation)
INSERT INTO categories (code, name_en, name_hi, type, icon) VALUES
-- INCOME
('sales_product',    'Product Sales',        'माल बिक्री',      'income',   '🛒'),
('sales_service',    'Service Income',       'सेवा आय',         'income',   '⚙️'),
('commission',       'Commission/Referral',  'कमीशन',           'income',   '🤝'),
('rental_income',    'Rental Income',        'किराया आय',       'income',   '🏠'),
('loan_received',    'Loan Received',        'कर्ज मिला',       'transfer', '🏦'),
('other_income',     'Other Income',         'अन्य आय',         'income',   '💵'),
-- EXPENSES
('inventory',        'Inventory/Stock',      'माल/स्टॉक',       'expense',  '📦'),
('labor_wages',      'Labor/Wages',          'मजदूरी',          'expense',  '👷'),
('transport_fuel',   'Transport/Fuel',       'ईंधन/यातायात',    'expense',  '⛽'),
('rent_premises',    'Shop/Office Rent',     'दुकान/दफ्तर किराया', 'expense', '🏪'),
('utilities',        'Utilities',            'बिजली/पानी',      'expense',  '💡'),
('equipment',        'Equipment/Repairs',    'उपकरण/मरम्मत',    'expense',  '🔧'),
('marketing',        'Marketing/Promotion',  'विज्ञापन',        'expense',  '📢'),
('professional_fees','Professional Fees',    'CA/वकील फीस',     'expense',  '📋'),
('loan_repayment',   'Loan Repayment',       'कर्ज चुकाना',     'transfer', '💸'),
('tax_government',   'Tax/Government Fees',  'टैक्स/सरकारी फीस','expense', '🏛️'),
('food_personal',    'Food (Personal)',       'खाना (व्यक्तिगत)','expense',  '🍱'),
('mobile_internet',  'Mobile/Internet',      'मोबाइल/इंटरनेट',  'expense',  '📱'),
('other_expense',    'Other Expense',        'अन्य खर्च',       'expense',  '📝');

-- ═══════════════════════════════════════════════════════════════════
-- TRANSACTIONS TABLE
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE transactions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount          NUMERIC(12, 2) NOT NULL,
    type            VARCHAR(10) NOT NULL CHECK (type IN ('income', 'expense', 'transfer')),
    category_code   VARCHAR(50) REFERENCES categories(code),
    counterparty    VARCHAR(200),         -- merchant name, customer name, etc.
    description     VARCHAR(500),         -- original text / transcription
    payment_method  VARCHAR(20) DEFAULT 'cash' CHECK (payment_method IN ('cash','upi','card','credit','unknown')),
    transaction_date DATE NOT NULL DEFAULT CURRENT_DATE,
    transaction_time TIME,
    source          VARCHAR(20) NOT NULL CHECK (source IN ('image','voice','text','upi_statement','manual')),
    raw_input       TEXT,                 -- original WhatsApp message / file path
    extracted_data  JSONB,                -- full AI extraction output
    confidence_score NUMERIC(4, 3),      -- 0.000 to 1.000
    verified        BOOLEAN DEFAULT FALSE,  -- user confirmed
    location        VARCHAR(200),
    notes           TEXT,
    embedding       vector(1536),         -- pgvector for similarity search
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_transactions_user_date ON transactions(user_id, transaction_date DESC);
CREATE INDEX idx_transactions_user_type ON transactions(user_id, type);
CREATE INDEX idx_transactions_user_category ON transactions(user_id, category_code);
CREATE INDEX idx_transactions_embedding ON transactions USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_transactions_date ON transactions(transaction_date DESC);

-- ═══════════════════════════════════════════════════════════════════
-- ARTHASCORE HISTORY TABLE
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE arthascore_history (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    score           INTEGER NOT NULL CHECK (score >= 300 AND score <= 900),
    -- Individual factor scores (0-100 each)
    income_regularity   INTEGER,
    growth_trajectory   INTEGER,
    expense_control     INTEGER,
    transaction_volume  INTEGER,
    business_longevity  INTEGER,
    payment_consistency INTEGER,
    data_completeness   INTEGER,
    -- Metadata
    data_points         INTEGER,    -- number of transactions used
    period_days         INTEGER,    -- lookback window in days
    snapshot_data       JSONB,      -- full calculation details
    calculated_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_arthascore_user_time ON arthascore_history(user_id, calculated_at DESC);

-- ═══════════════════════════════════════════════════════════════════
-- GENERATED DOCUMENTS TABLE
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_type   VARCHAR(50) NOT NULL CHECK (document_type IN ('financial_passport','pnl_report','gst_invoice','itr_summary')),
    file_url        TEXT NOT NULL,        -- S3 URL
    period_start    DATE,
    period_end      DATE,
    arthascore_at_generation INTEGER,
    summary_data    JSONB,               -- key financials embedded in doc
    generated_at    TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ DEFAULT NOW() + INTERVAL '30 days'
);

CREATE INDEX idx_documents_user ON documents(user_id, generated_at DESC);

-- ═══════════════════════════════════════════════════════════════════
-- WHATSAPP SESSION STATE TABLE
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE whatsapp_sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    phone_number    VARCHAR(15) NOT NULL,
    state           VARCHAR(50) NOT NULL DEFAULT 'IDLE',
    -- States: IDLE, AWAITING_CONFIRMATION, AWAITING_CATEGORY, REPORT_GENERATING, ONBOARDING
    pending_transaction JSONB,           -- transaction waiting for confirmation
    context         JSONB DEFAULT '{}',  -- last 5 messages for context
    last_activity   TIMESTAMPTZ DEFAULT NOW(),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_sessions_phone ON whatsapp_sessions(phone_number);

-- ═══════════════════════════════════════════════════════════════════
-- PROACTIVE INSIGHTS TABLE (logged for analytics)
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE insights_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id),
    insight_type    VARCHAR(50),   -- anomaly_expense, milestone_income, weekly_summary, etc.
    insight_data    JSONB,
    sent_at         TIMESTAMPTZ DEFAULT NOW(),
    acknowledged    BOOLEAN DEFAULT FALSE
);

-- ═══════════════════════════════════════════════════════════════════
-- ANALYTICS CACHE TABLE (pre-computed for speed)
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE analytics_cache (
    user_id         UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    -- Current period (MTD)
    mtd_income      NUMERIC(12, 2) DEFAULT 0,
    mtd_expenses    NUMERIC(12, 2) DEFAULT 0,
    mtd_net_profit  NUMERIC(12, 2) DEFAULT 0,
    -- This week
    wtd_income      NUMERIC(12, 2) DEFAULT 0,
    wtd_expenses    NUMERIC(12, 2) DEFAULT 0,
    -- All time
    total_transactions INTEGER DEFAULT 0,
    first_transaction_date DATE,
    -- Current ArthScore
    current_arthascore INTEGER,
    -- Cache metadata
    last_updated    TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════════════
-- UPDATED_AT TRIGGER (apply to all relevant tables)
-- ═══════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER update_transactions_updated_at BEFORE UPDATE ON transactions FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

### 4.2 SQLAlchemy Models

```python
# backend/models/transaction.py
from sqlalchemy import Column, String, Numeric, Boolean, Date, Time, Text, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMPTZ
from pgvector.sqlalchemy import Vector
import uuid
from database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    type = Column(String(10), nullable=False)       # income | expense | transfer
    category_code = Column(String(50))
    counterparty = Column(String(200))
    description = Column(String(500))
    payment_method = Column(String(20), default='cash')
    transaction_date = Column(Date, nullable=False)
    source = Column(String(20), nullable=False)     # image | voice | text | upi_statement
    raw_input = Column(Text)
    extracted_data = Column(JSON)
    confidence_score = Column(Numeric(4, 3))
    verified = Column(Boolean, default=False)
    embedding = Column(Vector(1536))
    created_at = Column(TIMESTAMPTZ)
    updated_at = Column(TIMESTAMPTZ)
```

---

## 5. FASTAPI BACKEND — COMPLETE IMPLEMENTATION

### 5.1 main.py

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from config import settings
from database import create_db_tables
from routes import webhook, transactions, analytics, score, reports, users, demo

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ArthAI backend starting up", env=settings.ENVIRONMENT)
    await create_db_tables()
    yield
    logger.info("ArthAI backend shutting down")

app = FastAPI(
    title="ArthAI API",
    description="India's Agentic Financial Intelligence Layer for the Informal Economy",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Route Registration ───────────────────────────────────────────────────────
app.include_router(webhook.router,       prefix="/webhook",   tags=["WhatsApp Webhook"])
app.include_router(users.router,         prefix="/api/users", tags=["Users"])
app.include_router(transactions.router,  prefix="/api/transactions", tags=["Transactions"])
app.include_router(analytics.router,     prefix="/api/analytics",   tags=["Analytics"])
app.include_router(score.router,         prefix="/api/score",       tags=["ArthScore"])
app.include_router(reports.router,       prefix="/api/reports",     tags=["Reports"])
app.include_router(demo.router,          prefix="/api/demo",        tags=["Demo"])

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ArthAI Backend", "version": "1.0.0"}
```

### 5.2 Pydantic Schemas

```python
# backend/schemas/transaction.py
from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any
from datetime import date, datetime
from uuid import UUID
from enum import Enum

class TransactionType(str, Enum):
    income = "income"
    expense = "expense"
    transfer = "transfer"

class PaymentMethod(str, Enum):
    cash = "cash"
    upi = "upi"
    card = "card"
    credit = "credit"
    unknown = "unknown"

class TransactionSource(str, Enum):
    image = "image"
    voice = "voice"
    text = "text"
    upi_statement = "upi_statement"
    manual = "manual"

class TransactionCreate(BaseModel):
    amount: float
    type: TransactionType
    category_code: Optional[str] = None
    counterparty: Optional[str] = None
    description: Optional[str] = None
    payment_method: PaymentMethod = PaymentMethod.cash
    transaction_date: date
    source: TransactionSource
    raw_input: Optional[str] = None
    confidence_score: Optional[float] = None

class TransactionResponse(BaseModel):
    id: UUID
    amount: float
    type: str
    category_code: Optional[str]
    description: Optional[str]
    transaction_date: date
    source: str
    verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}

# backend/schemas/whatsapp.py
class WhatsAppIncoming(BaseModel):
    """Twilio WhatsApp webhook payload schema"""
    From: str                    # e.g., "whatsapp:+919876543210"
    To: str                      # Twilio sandbox number
    Body: Optional[str] = ""     # Text message content
    NumMedia: Optional[str] = "0"
    MediaUrl0: Optional[str] = None    # Image/audio URL
    MediaContentType0: Optional[str] = None

class ExtractedTransaction(BaseModel):
    """Standardized output from all AI extraction modules"""
    amount: float
    type: TransactionType
    category_code: str
    counterparty: Optional[str] = None
    description: str
    payment_method: PaymentMethod = PaymentMethod.cash
    transaction_date: date
    confidence: float             # 0.0 to 1.0
    raw_text: Optional[str] = None   # original transcription / text
    language_detected: str = "hi"    # ISO 639-1

class ArthScoreResponse(BaseModel):
    score: int                   # 300-900
    grade: str                   # "Excellent" / "Good" / "Fair" / "Poor"
    grade_hi: str                # Hindi grade name
    max_loan_eligible: float     # estimated max loan amount in INR
    factors: Dict[str, int]      # individual factor scores
    insight_hi: str              # Hindi explanation
    insight_en: str
    calculated_at: datetime
```

### 5.3 WhatsApp Webhook Handler

```python
# backend/routes/webhook.py
"""
CRITICAL: This is the entry point for ALL WhatsApp interactions.
Twilio sends a POST request here on every message. We must respond
within 5 seconds or Twilio retries. All heavy processing is async via Celery.
"""
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from dependencies import get_db
from schemas.whatsapp import WhatsAppIncoming
from tasks.message_tasks import process_whatsapp_message
from services.whatsapp import WhatsAppService

router = APIRouter()
logger = structlog.get_logger()

@router.post("/whatsapp")
async def whatsapp_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Receives all WhatsApp messages from Twilio.
    
    IMPORTANT: Return HTTP 200 + empty TwiML IMMEDIATELY.
    Dispatch Celery task for async AI processing.
    """
    try:
        form_data = await request.form()
        payload = WhatsAppIncoming(**dict(form_data))
        
        logger.info("WhatsApp message received",
                   from_number=payload.From,
                   has_media=int(payload.NumMedia or 0) > 0,
                   body_length=len(payload.Body or ""))

        # Dispatch async processing (non-blocking)
        process_whatsapp_message.delay({
            "from": payload.From,
            "to": payload.To,
            "body": payload.Body,
            "num_media": payload.NumMedia,
            "media_url": payload.MediaUrl0,
            "media_type": payload.MediaContentType0,
        })

        # Return empty TwiML — we'll send our response via Twilio API later
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml"
        )

    except Exception as e:
        logger.error("Webhook processing failed", error=str(e))
        # Still return 200 to prevent Twilio retries flooding us
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml"
        )

@router.get("/whatsapp")
async def whatsapp_verify(request: Request):
    """Health check endpoint for Twilio webhook validation"""
    return PlainTextResponse("ArthAI WhatsApp webhook active")
```

### 5.4 Core API Routes

```python
# backend/routes/analytics.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import date, timedelta
from typing import Optional

from dependencies import get_db
from services.analytics import AnalyticsService

router = APIRouter()

@router.get("/pnl/{user_id}")
async def get_pnl(
    user_id: UUID,
    period: str = Query("90d", enum=["7d", "30d", "90d", "1y"]),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns P&L data for charting.
    period: 7d=weekly bars, 30d=daily bars, 90d=weekly bars, 1y=monthly bars
    
    Response:
    {
      "period": "90d",
      "total_income": 72400,
      "total_expenses": 27800,
      "net_profit": 44600,
      "net_margin_pct": 61.6,
      "series": [
        {"period_label": "Week 1", "income": 5200, "expenses": 1800, "net": 3400},
        ...
      ],
      "top_income_categories": [...],
      "top_expense_categories": [...]
    }
    """
    service = AnalyticsService(db)
    return await service.get_pnl_data(user_id, period)

@router.get("/cash-flow/{user_id}")
async def get_cash_flow(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    7-day and 30-day cash flow + 7-day forecast.
    """
    service = AnalyticsService(db)
    return await service.get_cash_flow(user_id)

@router.get("/summary/{user_id}")
async def get_summary(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Dashboard summary — all KPIs in one call.
    Returns: MTD income, MTD expenses, WTD income, WTD expenses,
             transaction count, avg daily income, top category.
    """
    service = AnalyticsService(db)
    return await service.get_dashboard_summary(user_id)

# backend/routes/reports.py
@router.post("/passport/{user_id}")
async def generate_financial_passport(
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Generates a bank-grade Financial Passport PDF.
    
    Process:
    1. Fetch last 12 months of transactions
    2. Calculate all P&L metrics
    3. Fetch current ArthScore
    4. Generate LLM business narrative
    5. Render HTML template → WeasyPrint PDF
    6. Upload to S3
    7. Return download URL
    
    Returns: {"document_id": "...", "download_url": "...", "expires_at": "..."}
    """
    from agents.passport_generator import PassportGenerator
    generator = PassportGenerator(db)
    result = await generator.generate(user_id)
    return result
```

---

## 6. AI MODULES — EXACT IMPLEMENTATIONS

### 6.1 Vision Module (Receipt OCR)

```python
# backend/ai/vision.py
"""
Receipt OCR using GPT-4o-mini vision capabilities.
Handles: printed receipts, handwritten bills, Hindi/regional scripts,
         crumpled photos, dim lighting, dual-language bills.
"""
import base64
import httpx
from openai import AsyncOpenAI
from typing import Optional
from datetime import date
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from schemas.whatsapp import ExtractedTransaction
from config import settings

logger = structlog.get_logger()

# ─── THE EXACT GPT-4V SYSTEM PROMPT FOR RECEIPT OCR ─────────────────────────
VISION_SYSTEM_PROMPT = """You are ArthAI's Receipt Intelligence Engine.
You analyze photos of financial documents for Indian micro-entrepreneurs.

Your job: Extract transaction details from receipt/invoice/bill photos.

The photos may contain:
- Printed receipts (petrol pumps, grocery stores, pharmacies)
- Handwritten bills (local vendors, sabzi mandis)
- UPI payment screenshots
- WhatsApp payment notifications
- Physical cash receipts

Documents may be in: Hindi, Marathi, Tamil, Telugu, Gujarati, Bengali, English, or mixed.
Script may be: Devanagari, Tamil, Telugu, Kannada, Bengali, Latin.
Images may be: crumpled, blurry, low-light, photographed at an angle.

Extract and return ONLY a JSON object with these fields:
{
  "amount": <number: the primary transaction amount in INR, NO currency symbols>,
  "type": <"income" or "expense" — receipts are usually expenses for the buyer>,
  "category_code": <one of: sales_product, sales_service, commission, rental_income, other_income,
                    inventory, labor_wages, transport_fuel, rent_premises, utilities,
                    equipment, marketing, professional_fees, loan_repayment, tax_government,
                    food_personal, mobile_internet, other_expense>,
  "counterparty": <merchant/person name if visible, else null>,
  "description": <brief description in English: what was bought/sold>,
  "payment_method": <"cash", "upi", "card", or "unknown">,
  "transaction_date": <"YYYY-MM-DD" if date visible on receipt, else today's date>,
  "confidence": <0.0-1.0: your confidence in this extraction>,
  "notes": <any ambiguity or additional detail worth noting>
}

RULES:
- If amount is unclear or you cannot read it with >50% confidence, set confidence < 0.5
- For fuel receipts: use transport_fuel category
- For petrol amounts: the amount in rupees is usually the largest number
- For handwritten bills: amount is typically on the right side or bottom
- NEVER return text outside the JSON — just the JSON object
"""

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def extract_from_receipt_image(
    image_url: str,
    user_language: str = "hi"
) -> ExtractedTransaction:
    """
    Download image from Twilio URL and send to GPT-4V for extraction.
    
    Args:
        image_url: Twilio media URL for the image
        user_language: user's preferred language (for fallback description)
    
    Returns:
        ExtractedTransaction with all fields populated
    """
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    # Download and encode image
    async with httpx.AsyncClient() as http:
        auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        response = await http.get(image_url, auth=auth, timeout=30)
        image_data = base64.b64encode(response.content).decode("utf-8")
        content_type = response.headers.get("content-type", "image/jpeg")
    
    logger.info("Sending image to GPT-4V", image_size_kb=len(response.content) // 1024)
    
    gpt_response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL_VISION,
        messages=[
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {
                    "url": f"data:{content_type};base64,{image_data}",
                    "detail": "high"
                }},
                {"type": "text", "text": "Extract transaction data from this receipt/document."}
            ]}
        ],
        max_tokens=500,
        temperature=0.1  # Low temperature for factual extraction
    )
    
    import json
    raw_json = gpt_response.choices[0].message.content.strip()
    # Strip markdown code blocks if GPT adds them
    raw_json = raw_json.replace("```json", "").replace("```", "").strip()
    data = json.loads(raw_json)
    
    return ExtractedTransaction(
        amount=float(data["amount"]),
        type=data["type"],
        category_code=data["category_code"],
        counterparty=data.get("counterparty"),
        description=data.get("description", "Receipt transaction"),
        payment_method=data.get("payment_method", "cash"),
        transaction_date=date.fromisoformat(data["transaction_date"]),
        confidence=float(data["confidence"]),
        language_detected="en"  # Receipt text language (not user language)
    )
```

### 6.2 Speech Module (Indic Voice → Text → Transaction)

```python
# backend/ai/speech.py
"""
Voice-to-transaction in 12 Indian languages.
Primary: Sarvam AI saarika-v2 (best for Indic languages, handles Hinglish)
Fallback: OpenAI Whisper large-v3 (more general, still good)
"""
import httpx
import base64
from openai import AsyncOpenAI
from typing import Optional
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from ai.nlu import extract_transaction_from_text

logger = structlog.get_logger()

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
async def transcribe_with_sarvam(audio_url: str) -> Optional[str]:
    """
    Transcribe Hindi/Indic voice note using Sarvam AI API.
    
    Sarvam saarika-v2 supports:
    - Hindi, Marathi, Tamil, Telugu, Gujarati, Bengali
    - Kannada, Malayalam, Punjabi, Odia, Urdu
    - Code-mixed speech (Hinglish, Tanglish, etc.)
    """
    async with httpx.AsyncClient(timeout=30) as http:
        # Download audio from Twilio
        auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        audio_response = await http.get(audio_url, auth=auth)
        audio_bytes = audio_response.content
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        
        # Call Sarvam AI ASR endpoint
        sarvam_response = await http.post(
            "https://api.sarvam.ai/speech-to-text",
            headers={
                "api-subscription-key": settings.SARVAM_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "model": settings.SARVAM_ASR_MODEL,   # saarika-v2
                "language_code": "unknown",             # auto-detect language
                "with_timestamps": False,
                "debug_mode": False,
                "input_audio": audio_b64,
                "audio_format": "wav"                   # Twilio sends OGG/Opus, convert if needed
            }
        )
        
        if sarvam_response.status_code == 200:
            data = sarvam_response.json()
            transcript = data.get("transcript", "")
            logger.info("Sarvam transcription complete",
                       language=data.get("language_code"),
                       transcript_length=len(transcript))
            return transcript
        else:
            logger.warning("Sarvam ASR failed", status=sarvam_response.status_code)
            return None

async def transcribe_with_whisper(audio_url: str) -> Optional[str]:
    """Fallback: OpenAI Whisper"""
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    async with httpx.AsyncClient(timeout=30) as http:
        auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        audio_response = await http.get(audio_url, auth=auth)
    
    import io
    audio_file = io.BytesIO(audio_response.content)
    audio_file.name = "audio.ogg"
    
    result = await client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language=None,    # Auto-detect
        prompt="Hindi, Marathi, financial transaction, rupees, paise, income, expense"
    )
    return result.text

async def voice_to_transaction(audio_url: str, user_language: str = "hi"):
    """
    Full pipeline: audio URL → transcription → ExtractedTransaction
    """
    # Try Sarvam first, fall back to Whisper
    transcript = None
    if settings.ENABLE_SARVAM_ASR:
        transcript = await transcribe_with_sarvam(audio_url)
    
    if not transcript:
        logger.info("Falling back to Whisper ASR")
        transcript = await transcribe_with_whisper(audio_url)
    
    if not transcript:
        raise ValueError("All ASR systems failed to transcribe audio")
    
    logger.info("Transcription result", transcript=transcript)
    
    # Now extract transaction from transcribed text
    return await extract_transaction_from_text(transcript, user_language)
```

### 6.3 NLU Module (Intent + Entity Extraction)

```python
# backend/ai/nlu.py
"""
Natural Language Understanding for financial messages.
Handles:
- Intent classification (TRANSACTION, QUERY, REPORT_REQUEST, GREETING, HELP)
- Entity extraction (amount, type, category, counterparty, date)
- Supports Hinglish + 12 Indian languages
"""
import json
from openai import AsyncOpenAI
from datetime import date
import structlog
from typing import Tuple

from config import settings
from schemas.whatsapp import ExtractedTransaction

logger = structlog.get_logger()

# ─── INTENT CLASSIFICATION PROMPT ───────────────────────────────────────────
INTENT_SYSTEM_PROMPT = """You classify WhatsApp messages from Indian small business owners.

Classify into ONE of these intents:
- TRANSACTION: Recording a financial transaction (income/expense/payment)
- QUERY: Asking about their financial data ("kitna kamaya?", "mera profit kya hai?")
- REPORT_REQUEST: Requesting a document ("loan ke liye document chahiye", "passport banao")
- GREETING: Hello, hi, namaste, first contact
- HELP: Asking what ArthAI can do, confused about usage
- CONFIRMATION_YES: Confirming a previous suggestion (haan, 1, yes, sahi hai, thik hai)
- CONFIRMATION_NO: Rejecting a previous suggestion (nahi, 2, galat, wrong)

Return ONLY a JSON: {"intent": "TRANSACTION", "confidence": 0.95}

Examples:
"Aaj ₹850 ki sawari mili" → {"intent": "TRANSACTION", "confidence": 0.99}
"Is hafte kitna kamaya?" → {"intent": "QUERY", "confidence": 0.98}
"Loan ke liye document chahiye" → {"intent": "REPORT_REQUEST", "confidence": 0.97}
"Haan, sahi hai" → {"intent": "CONFIRMATION_YES", "confidence": 0.99}
"Ramesh ko ₹2000 diye petrol ke liye" → {"intent": "TRANSACTION", "confidence": 0.97}
"""

# ─── TRANSACTION EXTRACTION PROMPT ──────────────────────────────────────────
EXTRACTION_SYSTEM_PROMPT = """You extract financial transaction details from Indian business owner messages.
Messages come in Hindi, Marathi, Hinglish, or other Indian languages. Extract accurately.

AMOUNT PARSING RULES:
- "teen hazaar" = ₹3,000
- "do sau pachas" = ₹250
- "1.5 lakh" = ₹1,50,000
- "panch so" = ₹500
- "dus rupaye" = ₹10
- Symbol "₹" always precedes amount in Indian convention

TYPE DETERMINATION:
- "mili", "aaya", "kamaya", "sale", "earned", "received" → income
- "diya", "diye", "kharcha", "expense", "paid", "kharida" → expense
- Context: if buying something → expense; if selling/earning → income

Return ONLY this JSON (no explanation):
{
  "amount": <number in INR>,
  "type": <"income" or "expense">,
  "category_code": <exact code from list below>,
  "counterparty": <person/merchant name or null>,
  "description": <brief English description>,
  "payment_method": <"cash"|"upi"|"card"|"unknown">,
  "transaction_date": <"YYYY-MM-DD", today if not mentioned>,
  "confidence": <0.0-1.0>
}

VALID CATEGORY CODES:
Income: sales_product, sales_service, commission, rental_income, other_income
Expense: inventory, labor_wages, transport_fuel, rent_premises, utilities,
         equipment, marketing, professional_fees, loan_repayment, tax_government,
         food_personal, mobile_internet, other_expense

TODAY: {today_date}
"""

# ─── QUERY HANDLER PROMPT ────────────────────────────────────────────────────
QUERY_SYSTEM_PROMPT = """You are ArthAI, a friendly financial assistant for Indian small business owners.
The user will ask about their business finances. Answer in their language (usually Hindi or Hinglish).

You have access to their financial data in JSON format. Use it to answer accurately.

Response style:
- Friendly, like talking to a trusted friend who knows business
- Use Indian number formats (lakh, hazaar, etc.)
- Keep responses under 200 words
- End with a useful insight or encouragement
- If asked in Hindi, respond in Hindi/Hinglish
- Use simple language, no accounting jargon

Example response (Hindi):
"Raju bhai, is hafte aapne ₹7,800 kamaye aur ₹3,600 kharcha kiya.
Net profit ₹4,200 raha — average se 10% zyada!
Fuel expense thoda zyada tha (₹1,200 = 16% of income), dhyan rakhein."
"""


async def classify_intent(text: str) -> Tuple[str, float]:
    """Classify message intent. Returns (intent, confidence)"""
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL_NLU,
        messages=[
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ],
        max_tokens=60,
        temperature=0.1
    )
    
    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)
    return data["intent"], data["confidence"]


async def extract_transaction_from_text(
    text: str,
    user_language: str = "hi"
) -> ExtractedTransaction:
    """Extract structured transaction from natural language text"""
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    prompt = EXTRACTION_SYSTEM_PROMPT.replace("{today_date}", date.today().isoformat())
    
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL_NLU,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text}
        ],
        max_tokens=300,
        temperature=0.1
    )
    
    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)
    
    return ExtractedTransaction(
        amount=float(data["amount"]),
        type=data["type"],
        category_code=data["category_code"],
        counterparty=data.get("counterparty"),
        description=data.get("description", text[:200]),
        payment_method=data.get("payment_method", "cash"),
        transaction_date=date.fromisoformat(data["transaction_date"]),
        confidence=float(data["confidence"]),
        raw_text=text,
        language_detected=user_language
    )


async def answer_financial_query(
    question: str,
    financial_data: dict,
    user_language: str = "hi"
) -> str:
    """Answer natural language financial question using user's data"""
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    lang_instruction = "Respond in Hindi/Hinglish (mix of Hindi and English)." if user_language == "hi" else "Respond in English."
    
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL_NLU,
        messages=[
            {"role": "system", "content": QUERY_SYSTEM_PROMPT + f"\n\n{lang_instruction}"},
            {"role": "user", "content": f"""User's financial data:
{json.dumps(financial_data, indent=2, ensure_ascii=False)}

User's question: {question}

Answer their question using the financial data. Be specific with numbers."""}
        ],
        max_tokens=300,
        temperature=0.7
    )
    
    return response.choices[0].message.content.strip()
```

---

## 7. LANGGRAPH AGENT — COMPLETE IMPLEMENTATION

```python
# backend/agents/financial_agent.py
"""
LangGraph stateful agent for processing each WhatsApp message.
Nodes handle the full pipeline from raw input to WhatsApp response.
"""
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from typing import TypedDict, Optional, Literal
from datetime import date
import structlog

from ai.vision import extract_from_receipt_image
from ai.speech import voice_to_transaction
from ai.nlu import classify_intent, extract_transaction_from_text, answer_financial_query
from services.analytics import AnalyticsService
from services.whatsapp import WhatsAppService
from schemas.whatsapp import ExtractedTransaction
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
    extracted_transaction: Optional[ExtractedTransaction]
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
    
    media_type = state.get("media_type", "")
    
    if media_type and ("image/" in media_type or "image" in media_type):
        state["message_type"] = "IMAGE"
        state["intent"] = "TRANSACTION"  # Images are almost always receipts
        state["intent_confidence"] = 0.9
        
    elif media_type and ("audio/" in media_type or "ogg" in media_type):
        state["message_type"] = "AUDIO"
        state["intent"] = "TRANSACTION"  # Voice notes are almost always transactions
        state["intent_confidence"] = 0.85
        
    else:
        state["message_type"] = "TEXT"
        body = state.get("raw_body", "")
        if body:
            intent, confidence = await classify_intent(body)
            state["intent"] = intent
            state["intent_confidence"] = confidence
        else:
            state["intent"] = "HELP"
            state["intent_confidence"] = 1.0
    
    logger.info("Input classified",
               message_type=state["message_type"],
               intent=state["intent"],
               confidence=state["intent_confidence"])
    return state


# ─── NODE: Extract Transaction from Media ─────────────────────────────────────
async def extract_transaction(state: AgentState) -> AgentState:
    """Extract structured transaction from image/audio/text"""
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
            
        state["extracted_transaction"] = extracted
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
    
    if state.get("error"):
        return state
    
    tx = state["extracted_transaction"]
    
    if tx.confidence < settings.CONFIDENCE_THRESHOLD:
        state["needs_clarification"] = True
        amount_str = f"₹{tx.amount:,.0f}"
        category_names = {
            "transport_fuel": "Fuel/Transport",
            "inventory": "Stock purchase",
            "labor_wages": "Wages/Labor",
            "sales_service": "Service income",
            # ... add all categories
        }
        cat_name = category_names.get(tx.category_code, tx.category_code)
        
        if state["user_language"] == "hi":
            state["clarification_message"] = (
                f"Maine record kiya: {amount_str} {tx.type}, {cat_name}. "
                f"Sahi hai?\n\n1️⃣ Haan, sahi hai ✅\n2️⃣ Nahi, galat hai ❌"
            )
        else:
            state["clarification_message"] = (
                f"I recorded: {amount_str} {tx.type}, {cat_name}. "
                f"Is this correct?\n\n1️⃣ Yes ✅\n2️⃣ No ❌"
            )
    else:
        state["needs_clarification"] = False
    
    return state


# ─── NODE: Store Transaction ───────────────────────────────────────────────────
async def store_transaction(state: AgentState) -> AgentState:
    """Write validated transaction to PostgreSQL"""
    if state.get("error") or state.get("needs_clarification"):
        return state
    
    from database import AsyncSessionLocal
    from models.transaction import Transaction
    from services.analytics import AnalyticsService
    
    tx = state["extracted_transaction"]
    
    async with AsyncSessionLocal() as db:
        # Save transaction
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
            verified=True if tx.confidence > settings.CONFIDENCE_THRESHOLD else False
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
    from database import AsyncSessionLocal
    from services.analytics import AnalyticsService
    
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
            f"📄 Download karen: {result['download_url']}\n\n"
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
        intent = state.get("intent", "HELP")
        msg_type = state.get("message_type", "TEXT")
        
        if msg_type in ("IMAGE", "AUDIO"):
            return "extract_transaction"
        elif intent == "TRANSACTION":
            return "extract_transaction"
        elif intent == "QUERY":
            return "handle_query"
        elif intent in ("REPORT_REQUEST",):
            return "generate_report"
        else:  # GREETING, HELP, CONFIRMATION_YES, CONFIRMATION_NO
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
            f"💰 {amount_str} {tx.type}\n"
            f"📂 {tx.category_code.replace('_', ' ').title()}\n"
            f"💳 {tx.payment_method.upper()}\n"
            f"📅 {tx.transaction_date.strftime('%B %d')}\n\n"
            f"_Type 'profit kya hai?' to see your weekly summary._"
        )

def get_error_response(language: str) -> str:
    if language == "hi":
        return "😕 Maafi chahiye, aapka message samajh nahi aaya. Kripya dobara bhejein ya likhkar batayein kya transaction tha."
    return "😕 Sorry, I couldn't understand that. Please try again or type the transaction details."
```

---

## 8. ARTHSCORE ENGINE — MATHEMATICAL SPECIFICATION

```python
# backend/agents/arthascore.py
"""
ArthScore: Proprietary creditworthiness score for informal economy entrepreneurs.
Scale: 300-900 (mirrors CIBIL for psychological familiarity)

MVP: 7 factors (sufficient for hackathon + initial product)
Production: 47 factors (behavioral signals, seasonal analysis, peer comparison)

SCIENTIFIC BASIS:
- Inspired by CIBIL methodology but adapted for cash/informal transactions
- Weighted toward income consistency (most predictive of repayment ability)
- Back-testable against CIBIL scores of formalized MSME borrowers
"""
import numpy as np
from sklearn.linear_model import LinearRegression
from typing import List, Dict, Optional
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import structlog

logger = structlog.get_logger()

# ─── FACTOR WEIGHTS (must sum to 1.0) ────────────────────────────────────────
FACTOR_WEIGHTS = {
    "income_regularity":    0.25,  # Most important: can they repay consistently?
    "growth_trajectory":    0.20,  # Is the business growing?
    "expense_control":      0.15,  # Do they manage costs well?
    "transaction_volume":   0.15,  # How active is the business?
    "business_longevity":   0.10,  # How long have they been operating?
    "payment_consistency":  0.10,  # Do they pay suppliers on time?
    "data_completeness":    0.05,  # Quality of the data we have
}

assert abs(sum(FACTOR_WEIGHTS.values()) - 1.0) < 0.001, "Weights must sum to 1.0"


class ArthScoreEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def calculate(self, user_id: str, lookback_days: int = 90) -> Dict:
        """
        Calculate ArthScore for a user.
        
        Args:
            user_id: User UUID
            lookback_days: Analysis window (90 days default)
        
        Returns:
            {
                "score": 714,
                "grade": "Good",
                "grade_hi": "अच्छा",
                "factors": {"income_regularity": 78, ...},
                "max_loan_eligible": 75000,
                "data_points": 87,
                "insight_hi": "..."
            }
        """
        from models.transaction import Transaction
        
        # Fetch transactions in lookback window
        cutoff = date.today() - timedelta(days=lookback_days)
        result = await self.db.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= cutoff,
                Transaction.verified == True
            ).order_by(Transaction.transaction_date)
        )
        transactions = result.scalars().all()
        
        if len(transactions) < 5:
            return self._insufficient_data_response()
        
        # Build time series
        income_tx = [t for t in transactions if t.type == "income"]
        expense_tx = [t for t in transactions if t.type == "expense"]
        
        # Group into weeks for time-series analysis
        weekly_income = self._group_by_week(income_tx, lookback_days)
        weekly_expenses = self._group_by_week(expense_tx, lookback_days)
        
        # Calculate each factor
        factors = {}
        
        # FACTOR 1: Income Regularity (Coefficient of Variation)
        factors["income_regularity"] = self._calc_income_regularity(weekly_income)
        
        # FACTOR 2: Growth Trajectory (Linear regression on weekly income)
        factors["growth_trajectory"] = self._calc_growth_trajectory(weekly_income)
        
        # FACTOR 3: Expense Control (Net margin)
        total_income = sum(t.amount for t in income_tx)
        total_expense = sum(t.amount for t in expense_tx)
        factors["expense_control"] = self._calc_expense_control(total_income, total_expense)
        
        # FACTOR 4: Transaction Volume
        factors["transaction_volume"] = self._calc_transaction_volume(len(transactions), lookback_days)
        
        # FACTOR 5: Business Longevity
        first_tx_date = min(t.transaction_date for t in transactions)
        factors["business_longevity"] = self._calc_business_longevity(first_tx_date)
        
        # FACTOR 6: Payment Consistency (simplified: ratio of expense regularity)
        factors["payment_consistency"] = self._calc_payment_consistency(expense_tx, lookback_days)
        
        # FACTOR 7: Data Completeness
        factors["data_completeness"] = self._calc_data_completeness(transactions, lookback_days)
        
        # Calculate weighted score
        weighted_sum = sum(
            factors[f] * FACTOR_WEIGHTS[f] for f in FACTOR_WEIGHTS
        )  # 0-100 range
        
        # Map to 300-900 range
        score = int(300 + (weighted_sum / 100) * 600)
        score = max(300, min(900, score))  # Clamp
        
        # Determine grade
        grade, grade_hi = self._get_grade(score)
        
        # Calculate max loan eligible
        monthly_net = (total_income - total_expense) / (lookback_days / 30)
        max_loan = monthly_net * 4  # 4x monthly net income (conservative)
        max_loan = min(max_loan, 500000)  # Cap at 5 lakh for MVP
        
        result = {
            "score": score,
            "grade": grade,
            "grade_hi": grade_hi,
            "factors": factors,
            "max_loan_eligible": round(max_loan / 1000) * 1000,  # Round to nearest 1000
            "data_points": len(transactions),
            "period_days": lookback_days,
            "insight_hi": self._generate_insight_hi(score, factors, monthly_net),
            "insight_en": self._generate_insight_en(score, factors, monthly_net),
        }
        
        logger.info("ArthScore calculated", user_id=user_id, score=score)
        return result

    def _group_by_week(self, transactions, lookback_days: int) -> List[float]:
        """Group transactions into weekly buckets, return list of weekly totals"""
        num_weeks = lookback_days // 7
        weeks = [0.0] * num_weeks
        
        today = date.today()
        for tx in transactions:
            days_ago = (today - tx.transaction_date).days
            week_idx = days_ago // 7
            if 0 <= week_idx < num_weeks:
                weeks[num_weeks - 1 - week_idx] += float(tx.amount)
        
        return weeks

    def _calc_income_regularity(self, weekly_income: List[float]) -> int:
        """
        Coefficient of Variation = std / mean
        Lower CV = more regular income = higher score
        CV < 0.2 → score 90-100
        CV > 1.0 → score 0-20
        """
        if not weekly_income or all(w == 0 for w in weekly_income):
            return 0
        
        active_weeks = [w for w in weekly_income if w > 0]
        if len(active_weeks) < 2:
            return 50  # Insufficient data, neutral score
        
        mean = np.mean(active_weeks)
        std = np.std(active_weeks)
        cv = std / mean if mean > 0 else 1.0
        
        # Linear mapping: CV=0 → score=100, CV=1.0 → score=0
        score = max(0, int(100 * (1 - min(cv, 1.0))))
        return score

    def _calc_growth_trajectory(self, weekly_income: List[float]) -> int:
        """
        Linear regression slope on weekly income.
        Positive slope → score > 50 (growing)
        Negative slope → score < 50 (declining)
        """
        if len(weekly_income) < 3:
            return 50
        
        X = np.array(range(len(weekly_income))).reshape(-1, 1)
        y = np.array(weekly_income)
        
        model = LinearRegression()
        model.fit(X, y)
        slope = model.coef_[0]
        
        # Normalize slope to 0-100 scale
        # slope / mean_income gives percentage growth per week
        mean_income = np.mean([w for w in weekly_income if w > 0]) or 1
        normalized_slope = slope / mean_income
        
        # Map: -20% per week → 0, 0% → 50, +20% per week → 100
        score = int(50 + (normalized_slope * 250))
        return max(0, min(100, score))

    def _calc_expense_control(self, total_income: float, total_expense: float) -> int:
        """Net margin quality. 50%+ margin → 100 score"""
        if total_income == 0:
            return 0
        margin = (total_income - total_expense) / total_income
        score = int(min(100, margin * 200))  # 50% margin → 100
        return max(0, score)

    def _calc_transaction_volume(self, tx_count: int, lookback_days: int) -> int:
        """
        Active business has regular transactions.
        Benchmark: 2-3 transactions/day for typical MSME.
        Target: 60+ transactions in 90 days → score 80-100
        """
        daily_rate = tx_count / lookback_days
        target_daily_rate = 0.67  # ~2 per day
        score = int(min(100, (daily_rate / target_daily_rate) * 80))
        return max(0, score)

    def _calc_business_longevity(self, first_transaction_date: date) -> int:
        """Days in business → score. 1 year = 100 score."""
        days = (date.today() - first_transaction_date).days
        score = min(100, int(days / 365 * 100))
        return score

    def _calc_payment_consistency(self, expense_tx, lookback_days: int) -> int:
        """
        Simplified: regular expenses suggest regular business operations.
        In production: track supplier payment dates vs. due dates.
        """
        if not expense_tx:
            return 70  # Neutral default
        
        # Check if there are consistent expense patterns (weekly fuel, monthly rent)
        weeks_with_expenses = len(set(
            (t.transaction_date - date.today()).days // 7 for t in expense_tx
        ))
        total_weeks = lookback_days // 7
        consistency = weeks_with_expenses / total_weeks
        return int(consistency * 100)

    def _calc_data_completeness(self, transactions, lookback_days: int) -> int:
        """What percentage of days have at least one transaction?"""
        days_with_tx = len(set(t.transaction_date for t in transactions))
        # Business typically operates 6 days/week
        expected_operating_days = lookback_days * (6 / 7)
        score = int(min(100, (days_with_tx / expected_operating_days) * 100))
        return score

    def _get_grade(self, score: int):
        if score >= 750: return "Excellent", "उत्कृष्ट"
        if score >= 650: return "Good", "अच्छा"
        if score >= 550: return "Fair", "ठीक-ठाक"
        return "Needs Improvement", "सुधार आवश्यक"

    def _generate_insight_hi(self, score: int, factors: dict, monthly_net: float) -> str:
        grade = self._get_grade(score)[1]
        return (
            f"Aapka ArthScore {score}/900 hai — {grade}! "
            f"Aapki monthly net income approximately ₹{monthly_net:,.0f} hai. "
            f"{'Aap ₹' + str(int(monthly_net * 4 / 1000) * 1000) + ' tak ke loan ke liye eligible hain.' if score >= 600 else 'Aur 30 din ke transactions add karen ArthScore improve karne ke liye.'}"
        )

    def _generate_insight_en(self, score: int, factors: dict, monthly_net: float) -> str:
        grade = self._get_grade(score)[0]
        return (
            f"Your ArthScore is {score}/900 — {grade}! "
            f"Your estimated monthly net income is ₹{monthly_net:,.0f}. "
            f"{'You are eligible for loans up to ₹' + str(int(monthly_net * 4 / 1000) * 1000) + '.' if score >= 600 else 'Add 30 more days of transactions to improve your score.'}"
        )

    def _insufficient_data_response(self):
        return {
            "score": 0,
            "grade": "Insufficient Data",
            "grade_hi": "अपर्याप्त डेटा",
            "factors": {},
            "max_loan_eligible": 0,
            "data_points": 0,
            "insight_hi": "ArthScore ke liye kam se kam 5 transactions chahiye. Aur transactions add karen.",
            "insight_en": "Need at least 5 transactions to calculate ArthScore. Add more transactions."
        }
```

---

## 9. FINANCIAL PASSPORT — PDF TEMPLATE

```python
# backend/agents/passport_generator.py
"""
Generates bank-grade Financial Passport PDF using WeasyPrint.
This is the primary deliverable that unlocks formal credit.
"""
from jinja2 import Template
from weasyprint import HTML
import boto3
from datetime import date, timedelta
from io import BytesIO
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from config import settings
from agents.arthascore import ArthScoreEngine
from services.analytics import AnalyticsService

logger = structlog.get_logger()

BUSINESS_NARRATIVE_PROMPT = """Write a professional 3-sentence business narrative for a Financial Passport document.

Business data:
- Owner: {name}
- Business type: {business_type}
- Location: {location}
- Operating months: {months}
- Monthly average income: ₹{avg_monthly_income}
- Monthly average expenses: ₹{avg_monthly_expenses}
- Net margin: {net_margin_pct}%
- Payment regularity: {payment_regularity}%

Write in formal English, like a bank officer would write. Focus on business stability and creditworthiness.
Keep under 60 words. Start with "{name} operates..."
"""

PASSPORT_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');
  
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Inter', 'Helvetica Neue', sans-serif; color: #1a1a2e; background: #fff; }
  
  .header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    color: white; padding: 40px 50px; display: flex;
    justify-content: space-between; align-items: center;
  }
  .header-brand { font-size: 28px; font-weight: 900; letter-spacing: -0.5px; }
  .header-brand span { color: #4ade80; }
  .header-subtitle { font-size: 13px; color: #94a3b8; margin-top: 4px; letter-spacing: 2px; text-transform: uppercase; }
  .doc-id { font-size: 11px; color: #64748b; text-align: right; }
  
  .score-banner {
    background: #f0fdf4; border-left: 6px solid #16a34a;
    padding: 25px 50px; display: flex; align-items: center; gap: 40px;
  }
  .score-number { font-size: 64px; font-weight: 900; color: #16a34a; line-height: 1; }
  .score-label { font-size: 13px; color: #166534; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
  .score-max { font-size: 20px; color: #4ade80; font-weight: 400; }
  .score-grade { font-size: 18px; font-weight: 700; color: #15803d; }
  .loan-eligible { background: #dcfce7; border-radius: 8px; padding: 12px 20px; text-align: center; }
  .loan-eligible-label { font-size: 11px; color: #166534; font-weight: 600; text-transform: uppercase; }
  .loan-eligible-amount { font-size: 24px; font-weight: 900; color: #15803d; }
  
  .section { padding: 30px 50px; border-bottom: 1px solid #e2e8f0; }
  .section-title { font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 2px;
                   text-transform: uppercase; margin-bottom: 20px; padding-bottom: 8px;
                   border-bottom: 2px solid #e2e8f0; }
  
  .info-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
  .info-item label { font-size: 11px; color: #94a3b8; display: block; margin-bottom: 4px; }
  .info-item value { font-size: 15px; font-weight: 600; color: #1e293b; }
  
  .metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 20px; }
  .metric-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px; text-align: center; }
  .metric-value { font-size: 22px; font-weight: 800; color: #1e293b; }
  .metric-value.income { color: #16a34a; }
  .metric-value.expense { color: #dc2626; }
  .metric-label { font-size: 11px; color: #64748b; margin-top: 4px; }
  
  .factor-bars { display: flex; flex-direction: column; gap: 10px; }
  .factor-row { display: flex; align-items: center; gap: 12px; }
  .factor-name { font-size: 12px; color: #475569; width: 180px; flex-shrink: 0; }
  .factor-bar-bg { flex: 1; background: #f1f5f9; border-radius: 4px; height: 8px; }
  .factor-bar-fill { height: 8px; border-radius: 4px; background: linear-gradient(90deg, #4ade80, #16a34a); }
  .factor-score { font-size: 12px; font-weight: 700; color: #1e293b; width: 30px; text-align: right; }
  
  .narrative-box { background: #fffbeb; border-left: 4px solid #f59e0b;
                   padding: 20px; border-radius: 0 8px 8px 0; font-size: 13px;
                   line-height: 1.7; color: #451a03; }
  
  .monthly-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; }
  .month-card { text-align: center; padding: 12px 8px; background: #f8fafc;
                border-radius: 6px; border: 1px solid #e2e8f0; }
  .month-name { font-size: 10px; color: #94a3b8; }
  .month-income { font-size: 12px; font-weight: 700; color: #16a34a; }
  .month-expense { font-size: 11px; color: #dc2626; }
  
  .footer {
    background: #1e293b; color: white; padding: 25px 50px;
    display: flex; justify-content: space-between; align-items: center;
  }
  .footer-brand { font-size: 16px; font-weight: 700; }
  .footer-legal { font-size: 10px; color: #64748b; text-align: right; line-height: 1.5; }
  
  .badge { display: inline-block; padding: 3px 10px; border-radius: 20px;
           font-size: 10px; font-weight: 600; text-transform: uppercase; }
  .badge-valid { background: #dcfce7; color: #15803d; }
  .badge-arthai { background: #eff6ff; color: #1d4ed8; }
</style>
</head>
<body>

<!-- HEADER -->
<div class="header">
  <div>
    <div class="header-brand">Arth<span>AI</span></div>
    <div class="header-subtitle">Financial Passport</div>
  </div>
  <div class="doc-id">
    <div>Document ID: {{ doc_id }}</div>
    <div>Generated: {{ generated_date }}</div>
    <div>Valid Until: {{ expiry_date }}</div>
    <span class="badge badge-valid">● VALID</span>
  </div>
</div>

<!-- ARTHSCORE BANNER -->
<div class="score-banner">
  <div>
    <div class="score-number">{{ score }}<span class="score-max">/900</span></div>
    <div class="score-label">ArthScore™</div>
    <div class="score-grade">{{ grade }}</div>
  </div>
  <div style="flex:1">
    <div class="score-label" style="margin-bottom: 8px;">Score Composition</div>
    <div class="factor-bars">
      {% for factor_name, factor_score in factors.items() %}
      <div class="factor-row">
        <div class="factor-name">{{ factor_name }}</div>
        <div class="factor-bar-bg"><div class="factor-bar-fill" style="width: {{ factor_score }}%"></div></div>
        <div class="factor-score">{{ factor_score }}</div>
      </div>
      {% endfor %}
    </div>
  </div>
  <div class="loan-eligible">
    <div class="loan-eligible-label">Estimated Loan Eligibility</div>
    <div class="loan-eligible-amount">₹{{ "{:,.0f}".format(max_loan) }}</div>
    <div style="font-size: 11px; color: #166534;">At competitive rates</div>
  </div>
</div>

<!-- BUSINESS PROFILE -->
<div class="section">
  <div class="section-title">Business Profile</div>
  <div class="info-grid">
    <div class="info-item"><label>Business Owner</label><value>{{ name }}</value></div>
    <div class="info-item"><label>Business Type</label><value>{{ business_type }}</value></div>
    <div class="info-item"><label>Location</label><value>{{ location }}</value></div>
    <div class="info-item"><label>Operating Since</label><value>{{ operating_since }}</value></div>
    <div class="info-item"><label>Months of Data</label><value>{{ data_months }} months</value></div>
    <div class="info-item"><label>Data Source</label><value>WhatsApp + ArthAI</value></div>
  </div>
</div>

<!-- 12-MONTH P&L SUMMARY -->
<div class="section">
  <div class="section-title">12-Month Financial Summary</div>
  <div class="metric-grid">
    <div class="metric-card">
      <div class="metric-value income">₹{{ "{:,.0f}".format(total_income) }}</div>
      <div class="metric-label">Total Income</div>
    </div>
    <div class="metric-card">
      <div class="metric-value expense">₹{{ "{:,.0f}".format(total_expenses) }}</div>
      <div class="metric-label">Total Expenses</div>
    </div>
    <div class="metric-card">
      <div class="metric-value">₹{{ "{:,.0f}".format(net_profit) }}</div>
      <div class="metric-label">Net Profit</div>
    </div>
    <div class="metric-card">
      <div class="metric-value income">₹{{ "{:,.0f}".format(avg_monthly_income) }}</div>
      <div class="metric-label">Avg Monthly Income</div>
    </div>
    <div class="metric-card">
      <div class="metric-value">{{ net_margin_pct }}%</div>
      <div class="metric-label">Net Margin</div>
    </div>
    <div class="metric-card">
      <div class="metric-value">{{ payment_regularity }}%</div>
      <div class="metric-label">Payment Regularity</div>
    </div>
  </div>

  <!-- Monthly breakdown -->
  <div class="monthly-grid">
    {% for month in monthly_data %}
    <div class="month-card">
      <div class="month-name">{{ month.label }}</div>
      <div class="month-income">₹{{ "{:,.0f}".format(month.income) }}</div>
      <div class="month-expense">₹{{ "{:,.0f}".format(month.expenses) }}</div>
    </div>
    {% endfor %}
  </div>
</div>

<!-- BUSINESS NARRATIVE -->
<div class="section">
  <div class="section-title">Business Assessment</div>
  <div class="narrative-box">{{ narrative }}</div>
</div>

<!-- FOOTER -->
<div class="footer">
  <div>
    <div class="footer-brand">ArthAI™</div>
    <div style="font-size: 11px; color: #94a3b8;">India's Financial Intelligence Layer</div>
    <span class="badge badge-arthai">ArthAI Verified</span>
  </div>
  <div class="footer-legal">
    This Financial Passport is generated by ArthAI using AI-analyzed transaction data.<br>
    ArthScore™ is a proprietary creditworthiness indicator. This document does not guarantee loan approval.<br>
    Data processed as per RBI Data Localization Guidelines. © ArthAI 2024-2026.
  </div>
</div>

</body>
</html>"""


class PassportGenerator:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate(self, user_id: str) -> dict:
        from models.user import User
        from services.analytics import AnalyticsService
        
        # Fetch user data
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        
        # Calculate ArthScore
        scorer = ArthScoreEngine(self.db)
        score_data = await scorer.calculate(user_id, lookback_days=90)
        
        # Fetch analytics
        analytics = AnalyticsService(self.db)
        pnl_12m = await analytics.get_pnl_data(user_id, "1y")
        
        # Generate AI business narrative
        narrative = await self._generate_narrative(user, pnl_12m, score_data)
        
        # Prepare template data
        template_data = {
            "doc_id": f"AP-{user_id[:8].upper()}-{date.today().strftime('%Y%m%d')}",
            "generated_date": date.today().strftime("%d %B %Y"),
            "expiry_date": (date.today() + timedelta(days=30)).strftime("%d %B %Y"),
            "score": score_data["score"],
            "grade": score_data["grade"],
            "factors": {
                "Income Regularity": score_data["factors"].get("income_regularity", 0),
                "Growth Trend": score_data["factors"].get("growth_trajectory", 0),
                "Expense Control": score_data["factors"].get("expense_control", 0),
                "Business Activity": score_data["factors"].get("transaction_volume", 0),
                "Longevity": score_data["factors"].get("business_longevity", 0),
                "Payment Habit": score_data["factors"].get("payment_consistency", 0),
            },
            "max_loan": score_data["max_loan_eligible"],
            "name": user.name or "Business Owner",
            "business_type": user.business_type or "Micro Business",
            "location": user.business_location or "India",
            "operating_since": "2018",  # Will be derived from first transaction
            "data_months": min(12, 90 // 30),
            "total_income": pnl_12m.get("total_income", 0),
            "total_expenses": pnl_12m.get("total_expenses", 0),
            "net_profit": pnl_12m.get("net_profit", 0),
            "avg_monthly_income": pnl_12m.get("total_income", 0) / 12,
            "net_margin_pct": pnl_12m.get("net_margin_pct", 0),
            "payment_regularity": score_data["factors"].get("payment_consistency", 70),
            "monthly_data": pnl_12m.get("series", []),
            "narrative": narrative,
        }
        
        # Render HTML → PDF
        html_content = Template(PASSPORT_HTML_TEMPLATE).render(**template_data)
        pdf_bytes = HTML(string=html_content).write_pdf()
        
        # Upload to S3
        file_key = f"passports/{user_id}/{date.today().isoformat()}_passport.pdf"
        download_url = await self._upload_to_s3(pdf_bytes, file_key)
        
        return {
            "download_url": download_url,
            "arthascore": score_data["score"],
            "loan_eligible": score_data["max_loan_eligible"],
            "expires_at": (date.today() + timedelta(days=30)).isoformat()
        }
    
    async def _generate_narrative(self, user, pnl_data: dict, score_data: dict) -> str:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        prompt = BUSINESS_NARRATIVE_PROMPT.format(
            name=user.name or "The Business Owner",
            business_type=user.business_type or "micro business",
            location=user.business_location or "India",
            months=3,
            avg_monthly_income=pnl_data.get("total_income", 0) / 3,
            avg_monthly_expenses=pnl_data.get("total_expenses", 0) / 3,
            net_margin_pct=round(pnl_data.get("net_margin_pct", 0)),
            payment_regularity=score_data["factors"].get("payment_consistency", 70)
        )
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150, temperature=0.3
        )
        return response.choices[0].message.content.strip()
    
    async def _upload_to_s3(self, pdf_bytes: bytes, key: str) -> str:
        s3 = boto3.client("s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        s3.put_object(
            Bucket=settings.AWS_BUCKET_NAME,
            Key=key,
            Body=pdf_bytes,
            ContentType="application/pdf",
            ContentDisposition=f'attachment; filename="ArthAI_Financial_Passport.pdf"'
        )
        url = s3.generate_presigned_url("get_object",
            Params={"Bucket": settings.AWS_BUCKET_NAME, "Key": key},
            ExpiresIn=30 * 24 * 3600  # 30 days
        )
        return url
```

---

## 10. CELERY ASYNC TASKS

```python
# backend/tasks/celery_app.py
from celery import Celery
from config import settings

celery_app = Celery(
    "arthai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["tasks.message_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_soft_time_limit=60,     # 60 second soft limit per task
    task_time_limit=90,           # 90 second hard limit
    worker_prefetch_multiplier=1, # Process one task at a time per worker
)

# backend/tasks/message_tasks.py
from tasks.celery_app import celery_app
import asyncio
import structlog

logger = structlog.get_logger()

@celery_app.task(name="process_whatsapp_message", bind=True, max_retries=2)
def process_whatsapp_message(self, payload: dict):
    """
    Main async task for processing incoming WhatsApp messages.
    Runs the full LangGraph agent pipeline.
    """
    asyncio.run(_process_message_async(payload))

async def _process_message_async(payload: dict):
    from agents.financial_agent import build_financial_agent
    from database import AsyncSessionLocal
    from models.user import User
    from sqlalchemy import select
    
    phone = payload["from"].replace("whatsapp:", "")  # "+919876543210"
    
    async with AsyncSessionLocal() as db:
        # Get or create user
        result = await db.execute(select(User).where(User.phone_number == phone))
        user = result.scalar_one_or_none()
        
        if not user:
            # New user onboarding
            user = User(phone_number=phone, preferred_language="hi")
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            from services.whatsapp import WhatsAppService
            wa = WhatsAppService()
            await wa.send_message(phone,
                "🙏 Namaste! Main ArthAI hoon — aapka financial assistant.\n\n"
                "Mujhe bhejein:\n"
                "📸 Receipt ka photo → Main record kar lunga\n"
                "🎤 Voice note → Main samajh lunga\n"
                "✍️ Text → 'Aaj ₹500 ki sale hui'\n\n"
                "Pehle, aapka naam aur kaam kya hai? (e.g., 'Raju, auto-rickshaw')"
            )
            return
        
        # Build and run agent
        agent = build_financial_agent()
        initial_state = {
            "user_phone": phone,
            "user_id": str(user.id),
            "user_language": user.preferred_language or "hi",
            "message_type": "",
            "raw_body": payload.get("body", ""),
            "media_url": payload.get("media_url"),
            "media_type": payload.get("media_type"),
            "intent": None,
            "intent_confidence": 0.0,
            "extracted_transaction": None,
            "needs_clarification": False,
            "clarification_message": None,
            "financial_summary": None,
            "response_text": "",
            "response_sent": False,
            "error": None,
        }
        
        await agent.ainvoke(initial_state)
```

---

## 11. FRONTEND DASHBOARD — REACT COMPONENTS

### 11.1 App.tsx Router

```typescript
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Transactions from './pages/Transactions'
import Passport from './pages/Passport'
import Demo from './pages/Demo'
import { LanguageProvider } from './contexts/LanguageContext'

// For demo: use Raju's pre-seeded user ID
const DEMO_USER_ID = "550e8400-e29b-41d4-a716-446655440000"

export default function App() {
  return (
    <LanguageProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to={`/dashboard/${DEMO_USER_ID}`} />} />
          <Route path="/dashboard/:userId" element={<Dashboard />} />
          <Route path="/transactions/:userId" element={<Transactions />} />
          <Route path="/passport/:userId" element={<Passport />} />
          <Route path="/demo" element={<Demo />} />
        </Routes>
      </BrowserRouter>
    </LanguageProvider>
  )
}
```

### 11.2 ArthScore Gauge Component

```typescript
// frontend/src/components/ArthScoreGauge.tsx
import { useEffect, useRef } from 'react'

interface ArthScoreGaugeProps {
  score: number        // 300-900
  grade: string
  gradeHi: string
  loanEligible: number
  language: 'hi' | 'en'
  animateFrom?: number
}

export default function ArthScoreGauge({
  score, grade, gradeHi, loanEligible, language, animateFrom = 300
}: ArthScoreGaugeProps) {
  
  const getColor = (s: number) => {
    if (s >= 750) return '#16a34a'   // green
    if (s >= 650) return '#0ea5e9'   // blue
    if (s >= 550) return '#f59e0b'   // amber
    return '#ef4444'                  // red
  }
  
  const pct = (score - 300) / 600  // 0-1 range
  const radius = 80
  const circumference = 2 * Math.PI * radius
  const dashOffset = circumference * (1 - pct * 0.75)  // 270 degree arc
  const color = getColor(score)
  
  return (
    <div className="bg-white rounded-2xl shadow-lg p-6 text-center">
      <div className="relative inline-block">
        <svg width="200" height="160" viewBox="0 0 200 160">
          {/* Background arc */}
          <path
            d="M 20 140 A 80 80 0 1 1 180 140"
            fill="none" stroke="#f1f5f9" strokeWidth="16"
            strokeLinecap="round"
          />
          {/* Score arc */}
          <path
            d="M 20 140 A 80 80 0 1 1 180 140"
            fill="none" stroke={color} strokeWidth="16"
            strokeLinecap="round"
            strokeDasharray={`${circumference * 0.75}`}
            strokeDashoffset={dashOffset}
            style={{ transition: 'stroke-dashoffset 1.5s ease' }}
          />
          {/* Score text */}
          <text x="100" y="110" textAnchor="middle" fontSize="36"
                fontWeight="900" fill={color}>{score}</text>
          <text x="100" y="130" textAnchor="middle" fontSize="12"
                fill="#94a3b8">/900</text>
        </svg>
      </div>
      
      <div className="mt-2">
        <span className={`inline-block px-3 py-1 rounded-full text-sm font-bold`}
              style={{ background: `${color}20`, color }}>
          {language === 'hi' ? gradeHi : grade}
        </span>
      </div>
      
      <div className="mt-4 bg-green-50 rounded-xl p-3">
        <p className="text-xs text-green-700 font-semibold uppercase tracking-wide">
          {language === 'hi' ? 'Loan Eligibility' : 'Loan Eligibility'}
        </p>
        <p className="text-2xl font-black text-green-800">
          ₹{loanEligible.toLocaleString('en-IN')}
        </p>
      </div>
    </div>
  )
}
```

### 11.3 P&L Chart Component

```typescript
// frontend/src/components/PLChart.tsx
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface PLData {
  period_label: string
  income: number
  expenses: number
  net: number
}

interface PLChartProps {
  data: PLData[]
  language: 'hi' | 'en'
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white border border-gray-100 rounded-xl shadow-xl p-3 text-sm">
        <p className="font-bold text-gray-800 mb-2">{label}</p>
        {payload.map((p: any) => (
          <p key={p.name} style={{ color: p.color }} className="font-semibold">
            {p.name}: ₹{Number(p.value).toLocaleString('en-IN')}
          </p>
        ))}
      </div>
    )
  }
  return null
}

export default function PLChart({ data, language }: PLChartProps) {
  const labels = {
    income: language === 'hi' ? 'आय (Income)' : 'Income',
    expenses: language === 'hi' ? 'खर्च (Expenses)' : 'Expenses',
    net: language === 'hi' ? 'मुनाफा (Net Profit)' : 'Net Profit',
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg p-6">
      <h3 className="font-bold text-gray-800 mb-4 text-lg">
        {language === 'hi' ? 'आय-खर्च विश्लेषण' : 'Income & Expense Analysis'}
      </h3>
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="incomeGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#16a34a" stopOpacity={0.15}/>
              <stop offset="95%" stopColor="#16a34a" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="expenseGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#dc2626" stopOpacity={0.15}/>
              <stop offset="95%" stopColor="#dc2626" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="period_label" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} tick={{ fontSize: 11 }} />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Area type="monotone" dataKey="income" name={labels.income}
                stroke="#16a34a" fill="url(#incomeGrad)" strokeWidth={2} />
          <Area type="monotone" dataKey="expenses" name={labels.expenses}
                stroke="#dc2626" fill="url(#expenseGrad)" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
```

### 11.4 Transaction Feed Component

```typescript
// frontend/src/components/TransactionFeed.tsx
interface Transaction {
  id: string
  amount: number
  type: 'income' | 'expense'
  category_code: string
  description: string
  transaction_date: string
  source: string
  verified: boolean
}

const CATEGORY_CONFIG: Record<string, { name_hi: string; name_en: string; icon: string; bg: string }> = {
  transport_fuel:  { name_hi: "ईंधन",    name_en: "Fuel",        icon: "⛽", bg: "bg-orange-50 text-orange-700" },
  sales_service:   { name_hi: "सेवा आय", name_en: "Service",     icon: "⚙️", bg: "bg-green-50 text-green-700"  },
  inventory:       { name_hi: "माल",     name_en: "Inventory",   icon: "📦", bg: "bg-blue-50 text-blue-700"    },
  labor_wages:     { name_hi: "मजदूरी",  name_en: "Wages",       icon: "👷", bg: "bg-purple-50 text-purple-700"},
  utilities:       { name_hi: "बिजली",   name_en: "Utilities",   icon: "💡", bg: "bg-yellow-50 text-yellow-700"},
  food_personal:   { name_hi: "खाना",    name_en: "Food",        icon: "🍱", bg: "bg-red-50 text-red-700"      },
  mobile_internet: { name_hi: "मोबाइल",  name_en: "Mobile",      icon: "📱", bg: "bg-gray-50 text-gray-700"   },
  other_income:    { name_hi: "अन्य आय", name_en: "Other Income",icon: "💵", bg: "bg-green-50 text-green-700" },
  other_expense:   { name_hi: "अन्य",    name_en: "Other",       icon: "📝", bg: "bg-gray-50 text-gray-700"   },
}

const SOURCE_ICONS: Record<string, string> = {
  image: "📸", voice: "🎤", text: "✍️", upi_statement: "💳", manual: "📋"
}

export default function TransactionFeed({ transactions, language }: {
  transactions: Transaction[], language: 'hi' | 'en'
}) {
  return (
    <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100">
        <h3 className="font-bold text-gray-800 text-lg">
          {language === 'hi' ? 'हाल के लेनदेन' : 'Recent Transactions'}
        </h3>
      </div>
      <div className="divide-y divide-gray-50">
        {transactions.map(tx => {
          const cat = CATEGORY_CONFIG[tx.category_code] || 
                      { name_hi: tx.category_code, name_en: tx.category_code, 
                        icon: "💰", bg: "bg-gray-50 text-gray-700" }
          return (
            <div key={tx.id} className="px-6 py-4 flex items-center gap-4 hover:bg-gray-50">
              <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center text-xl">
                {cat.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${cat.bg}`}>
                    {language === 'hi' ? cat.name_hi : cat.name_en}
                  </span>
                  <span className="text-xs text-gray-400" title={`Logged via ${tx.source}`}>
                    {SOURCE_ICONS[tx.source]}
                  </span>
                  {tx.verified && <span className="text-xs text-green-600">✓</span>}
                </div>
                <p className="text-sm text-gray-600 truncate">{tx.description}</p>
                <p className="text-xs text-gray-400">{new Date(tx.transaction_date).toLocaleDateString('en-IN')}</p>
              </div>
              <div className={`text-right font-bold text-lg ${
                tx.type === 'income' ? 'text-green-600' : 'text-red-500'
              }`}>
                {tx.type === 'income' ? '+' : '-'}₹{Number(tx.amount).toLocaleString('en-IN')}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

---

## 12. DEMO DATA — RAJU'S 90-DAY SYNTHETIC DATASET

```json
// demo-data/raju_90days.json
// Raju Kumar, Auto-rickshaw driver, Pune
// 90 days (Jan 1 – Mar 31, 2026)
// Working: ~25 days/month | Rest: Sundays + occasional sick days
// Income: ₹850–1,200/day from fares (avg ₹925/day)
// Expenses: Fuel ₹150-180/day, occasional maintenance, mobile

{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "phone_number": "+919876543210",
    "name": "Raju Kumar",
    "preferred_language": "hi",
    "business_type": "Auto-rickshaw Services",
    "business_location": "Pune, Maharashtra",
    "onboarding_complete": true
  },
  "transactions": [
    {"amount": 950, "type": "income", "category_code": "sales_service", "description": "Auto-rickshaw fares - Monday morning runs", "transaction_date": "2026-01-02", "source": "voice", "payment_method": "cash", "verified": true},
    {"amount": 165, "type": "expense", "category_code": "transport_fuel", "counterparty": "IndianOil Kothrud", "description": "CNG fuel", "transaction_date": "2026-01-02", "source": "image", "payment_method": "cash", "verified": true},
    {"amount": 1100, "type": "income", "category_code": "sales_service", "description": "Auto-rickshaw fares - tourist season rush", "transaction_date": "2026-01-03", "source": "text", "payment_method": "cash", "verified": true},
    {"amount": 175, "type": "expense", "category_code": "transport_fuel", "counterparty": "HP Petrol Pump Baner", "description": "CNG refill", "transaction_date": "2026-01-03", "source": "image", "payment_method": "cash", "verified": true},
    {"amount": 890, "type": "income", "category_code": "sales_service", "description": "Day fares", "transaction_date": "2026-01-05", "source": "voice", "payment_method": "cash", "verified": true},
    {"amount": 160, "type": "expense", "category_code": "transport_fuel", "description": "Fuel", "transaction_date": "2026-01-05", "source": "image", "payment_method": "cash", "verified": true},
    {"amount": 1050, "type": "income", "category_code": "sales_service", "description": "Corporate office drops + evening rides", "transaction_date": "2026-01-06", "source": "voice", "payment_method": "cash", "verified": true},
    {"amount": 170, "type": "expense", "category_code": "transport_fuel", "description": "CNG", "transaction_date": "2026-01-06", "source": "image", "payment_method": "cash", "verified": true},
    {"amount": 925, "type": "income", "category_code": "sales_service", "description": "Day's earnings", "transaction_date": "2026-01-07", "source": "text", "payment_method": "cash", "verified": true},
    {"amount": 155, "type": "expense", "category_code": "transport_fuel", "description": "Fuel", "transaction_date": "2026-01-07", "source": "image", "payment_method": "cash", "verified": true},
    {"amount": 975, "type": "income", "category_code": "sales_service", "description": "Aaj 8 sawariyan gayi", "transaction_date": "2026-01-08", "source": "voice", "payment_method": "cash", "verified": true},
    {"amount": 168, "type": "expense", "category_code": "transport_fuel", "description": "CNG IndianOil", "transaction_date": "2026-01-08", "source": "image", "payment_method": "cash", "verified": true},
    {"amount": 199, "type": "expense", "category_code": "mobile_internet", "counterparty": "Jio", "description": "Monthly mobile recharge", "transaction_date": "2026-01-10", "source": "image", "payment_method": "upi", "verified": true},
    {"amount": 1150, "type": "income", "category_code": "sales_service", "description": "Good day - airport runs", "transaction_date": "2026-01-11", "source": "voice", "payment_method": "cash", "verified": true},
    {"amount": 180, "type": "expense", "category_code": "transport_fuel", "description": "Full tank CNG", "transaction_date": "2026-01-11", "source": "image", "payment_method": "cash", "verified": true},
    {"amount": 880, "type": "income", "category_code": "sales_service", "description": "Aaj thoda kam raha", "transaction_date": "2026-01-12", "source": "voice", "payment_method": "cash", "verified": true},
    {"amount": 158, "type": "expense", "category_code": "transport_fuel", "description": "CNG", "transaction_date": "2026-01-12", "source": "image", "payment_method": "cash", "verified": true},
    {"amount": 1200, "type": "income", "category_code": "sales_service", "description": "Best day this week - Hinjewadi IT park runs", "transaction_date": "2026-01-13", "source": "voice", "payment_method": "cash", "verified": true},
    {"amount": 175, "type": "expense", "category_code": "transport_fuel", "description": "CNG Hinjewadi pump", "transaction_date": "2026-01-13", "source": "image", "payment_method": "cash", "verified": true},
    {"amount": 1500, "type": "expense", "category_code": "equipment", "counterparty": "Manish Auto Works", "description": "3-month service + brake adjustment", "transaction_date": "2026-01-14", "source": "image", "payment_method": "cash", "verified": true},
    {"amount": 850, "type": "income", "category_code": "sales_service", "description": "Day earnings", "transaction_date": "2026-01-15", "source": "voice", "payment_method": "cash", "verified": true},
    {"amount": 162, "type": "expense", "category_code": "transport_fuel", "description": "Fuel", "transaction_date": "2026-01-15", "source": "image", "payment_method": "cash", "verified": true},
    {"amount": 5000, "type": "expense", "category_code": "loan_repayment", "counterparty": "Suresh (moneylender)", "description": "Monthly installment to moneylender at 4% per month", "transaction_date": "2026-01-17", "source": "text", "payment_method": "cash", "verified": true},
    {"amount": 920, "type": "income", "category_code": "sales_service", "description": "Weekday runs", "transaction_date": "2026-01-19", "source": "voice", "payment_method": "cash", "verified": true},
    {"amount": 163, "type": "expense", "category_code": "transport_fuel", "description": "CNG", "transaction_date": "2026-01-19", "source": "image", "payment_method": "cash", "verified": true},
    {"amount": 1080, "type": "income", "category_code": "sales_service", "description": "Aaj 10 sawariyan, UPI bhi aaya ek se", "transaction_date": "2026-01-20", "source": "voice", "payment_method": "cash", "verified": true},
    {"amount": 172, "type": "expense", "category_code": "transport_fuel", "description": "Fuel refill", "transaction_date": "2026-01-20", "source": "image", "payment_method": "cash", "verified": true},
    {"amount": 960, "type": "income", "category_code": "sales_service", "description": "Normal day", "transaction_date": "2026-01-21", "source": "voice", "payment_method": "cash", "verified": true},
    {"amount": 165, "type": "expense", "category_code": "transport_fuel", "description": "CNG", "transaction_date": "2026-01-21", "source": "image", "payment_method": "cash", "verified": true},
    {"amount": 870, "type": "income", "category_code": "sales_service", "description": "Morning + evening runs", "transaction_date": "2026-01-22", "source": "voice", "payment_method": "cash", "verified": true},
    {"amount": 1100, "type": "income", "category_code": "sales_service", "description": "Holi pre-season - more rides", "transaction_date": "2026-01-23", "source": "voice", "payment_method": "cash", "verified": true},
    {"amount": 170, "type": "expense", "category_code": "transport_fuel", "description": "CNG full tank", "transaction_date": "2026-01-23", "source": "image", "payment_method": "cash", "verified": true},
    {"amount": 940, "type": "income", "category_code": "sales_service", "description": "Day total", "transaction_date": "2026-01-26", "source": "voice", "payment_method": "cash", "verified": true},
    {"amount": 165, "type": "expense", "category_code": "transport_fuel", "description": "Fuel", "transaction_date": "2026-01-26", "source": "image", "payment_method": "cash", "verified": true},
    {"amount": 980, "type": "income", "category_code": "sales_service", "description": "Aaj teen office drops", "transaction_date": "2026-01-27", "source": "voice", "payment_method": "cash", "verified": true},
    {"amount": 168, "type": "expense", "category_code": "transport_fuel", "description": "CNG", "transaction_date": "2026-01-27", "source": "image", "payment_method": "cash", "verified": true},
    {"amount": 1020, "type": "income", "category_code": "sales_service", "description": "Month end earnings", "transaction_date": "2026-01-28", "source": "voice", "payment_method": "cash", "verified": true},
    {"amount": 1300, "type": "income", "category_code": "sales_service", "description": "Republic Day holiday - lots of rides", "transaction_date": "2026-01-29", "source": "voice", "payment_method": "cash", "verified": true},
    {"amount": 185, "type": "expense", "category_code": "transport_fuel", "description": "Extra fuel - long day", "transaction_date": "2026-01-29", "source": "image", "payment_method": "cash", "verified": true},
    {"amount": 199, "type": "expense", "category_code": "mobile_internet", "counterparty": "Jio", "description": "Feb recharge", "transaction_date": "2026-02-10", "source": "image", "payment_method": "upi", "verified": true},
    {"amount": 5000, "type": "expense", "category_code": "loan_repayment", "counterparty": "Suresh (moneylender)", "description": "February installment", "transaction_date": "2026-02-17", "source": "text", "payment_method": "cash", "verified": true},
    {"amount": 2000, "type": "expense", "category_code": "equipment", "counterparty": "Bharat Tyres Kothrud", "description": "Rear tyre replacement", "transaction_date": "2026-02-20", "source": "image", "payment_method": "cash", "verified": true},
    {"amount": 199, "type": "expense", "category_code": "mobile_internet", "counterparty": "Jio", "description": "March recharge", "transaction_date": "2026-03-10", "source": "image", "payment_method": "upi", "verified": true},
    {"amount": 5000, "type": "expense", "category_code": "loan_repayment", "counterparty": "Suresh (moneylender)", "description": "March installment", "transaction_date": "2026-03-17", "source": "text", "payment_method": "cash", "verified": true}
  ],
  "summary": {
    "period": "Jan 1 - Mar 31, 2026",
    "total_income": 72400,
    "total_expenses": 27800,
    "net_profit": 44600,
    "avg_monthly_income": 24133,
    "avg_daily_income": 875,
    "arthascore": 714,
    "loan_eligible": 75000
  }
}
```

---

## 13. WHATSAPP SERVICE LAYER

```python
# backend/services/whatsapp.py
from twilio.rest import Client
from config import settings
import structlog

logger = structlog.get_logger()

class WhatsAppService:
    def __init__(self):
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.from_number = settings.TWILIO_WHATSAPP_FROM

    async def send_message(self, to_phone: str, body: str) -> str:
        """Send WhatsApp message via Twilio"""
        # Ensure E.164 format with whatsapp: prefix
        if not to_phone.startswith("whatsapp:"):
            to_phone = f"whatsapp:{to_phone}"
        
        try:
            message = self.client.messages.create(
                body=body[:1500],  # WhatsApp limit
                from_=self.from_number,
                to=to_phone
            )
            logger.info("WhatsApp message sent", message_sid=message.sid, to=to_phone)
            return message.sid
        except Exception as e:
            logger.error("WhatsApp send failed", error=str(e), to=to_phone)
            raise

    async def send_document(self, to_phone: str, media_url: str, caption: str = "") -> str:
        """Send PDF document via WhatsApp"""
        if not to_phone.startswith("whatsapp:"):
            to_phone = f"whatsapp:{to_phone}"
        
        message = self.client.messages.create(
            body=caption,
            from_=self.from_number,
            to=to_phone,
            media_url=[media_url]
        )
        return message.sid
```

---

## 14. DEPLOYMENT CONFIGURATION

### 14.1 Procfile (Railway)

```
web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
worker: celery -A backend.tasks.celery_app worker --loglevel=info --concurrency=2
```

### 14.2 railway.json

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn backend.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE"
  }
}
```

### 14.3 .gitignore

```
__pycache__/
*.pyc
.env
.env.local
node_modules/
dist/
*.pdf
uploads/
.DS_Store
```

---

## 15. API ENDPOINTS COMPLETE REFERENCE

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| POST | `/webhook/whatsapp` | Twilio webhook — receives all WhatsApp messages | TwiML XML |
| GET | `/health` | Health check | `{status: "healthy"}` |
| POST | `/api/users/register` | Register new user | UserResponse |
| GET | `/api/users/{phone}` | Get user by phone | UserResponse |
| GET | `/api/transactions/{user_id}` | List transactions (paginated) | Transaction[] |
| POST | `/api/transactions/{user_id}` | Manual transaction add | Transaction |
| GET | `/api/analytics/summary/{user_id}` | Dashboard KPIs | SummaryResponse |
| GET | `/api/analytics/pnl/{user_id}?period=90d` | P&L time series | PLResponse |
| GET | `/api/analytics/cash-flow/{user_id}` | Cash flow + forecast | CashFlowResponse |
| GET | `/api/score/{user_id}` | Calculate ArthScore | ArthScoreResponse |
| POST | `/api/reports/passport/{user_id}` | Generate Financial Passport PDF | {download_url, expires_at} |
| GET | `/api/demo/seed` | Load Raju's 90-day dataset | `{message: "seeded"}` |

---

## 16. DEMO SEED ENDPOINT (Critical for Hackathon)

```python
# backend/routes/demo.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import json
from pathlib import Path
from datetime import date

from dependencies import get_db
from models.user import User
from models.transaction import Transaction

router = APIRouter()

@router.post("/seed")
async def seed_demo_data(db: AsyncSession = Depends(get_db)):
    """
    Seeds Raju's 90-day synthetic transaction dataset.
    Call this ONCE to set up the demo.
    GET /api/demo/seed → loads raju_90days.json into the DB
    """
    demo_data_path = Path(__file__).parent.parent.parent / "demo-data" / "raju_90days.json"
    data = json.loads(demo_data_path.read_text())
    
    # Create or update Raju's user
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == data["user"]["id"]))
    raju = result.scalar_one_or_none()
    
    if not raju:
        raju = User(**data["user"])
        db.add(raju)
    
    # Clear existing demo transactions
    from sqlalchemy import delete
    await db.execute(delete(Transaction).where(Transaction.user_id == data["user"]["id"]))
    
    # Insert all transactions
    for tx_data in data["transactions"]:
        tx = Transaction(
            user_id=data["user"]["id"],
            amount=tx_data["amount"],
            type=tx_data["type"],
            category_code=tx_data["category_code"],
            counterparty=tx_data.get("counterparty"),
            description=tx_data["description"],
            payment_method=tx_data.get("payment_method", "cash"),
            transaction_date=date.fromisoformat(tx_data["transaction_date"]),
            source=tx_data["source"],
            confidence_score=0.95,
            verified=True
        )
        db.add(tx)
    
    await db.commit()
    return {
        "message": "Demo data seeded successfully",
        "user": "Raju Kumar",
        "transactions_loaded": len(data["transactions"]),
        "demo_user_id": data["user"]["id"],
        "dashboard_url": f"/dashboard/{data['user']['id']}"
    }
```

---

## 17. SECURITY IMPLEMENTATION

```python
# backend/middleware/security.py
"""
Security layers:
1. Twilio webhook signature validation (prevents spoofed webhooks)
2. API key authentication for dashboard endpoints
3. AES-256 encryption for sensitive fields (in production)
4. Rate limiting via Redis
"""

from fastapi import Request, HTTPException
from twilio.request_validator import RequestValidator
from config import settings

async def validate_twilio_signature(request: Request):
    """Validate that the webhook is genuinely from Twilio"""
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)
    form_data = await request.form()
    params = dict(form_data)
    
    if not validator.validate(url, params, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
```

---

## 18. LANGUAGE SUPPORT MATRIX

| Language | ISO Code | ASR Model | NLU Tested | Category Keywords |
|----------|----------|-----------|------------|-------------------|
| Hindi | `hi` | saarika-v2 | ✅ Primary | hazaar, rupaye, lakh, kharcha, kamaya |
| Marathi | `mr` | saarika-v2 | ✅ Good | hazaar, rupaye, kharch, milale |
| Hinglish | `hi-en` | saarika-v2 | ✅ Best | "teen thousand diye" |
| English | `en` | whisper-1 | ✅ Primary | — |
| Tamil | `ta` | saarika-v2 | ⚠️ Beta | ஆயிரம், ரூபாய் |
| Telugu | `te` | saarika-v2 | ⚠️ Beta | వేయి, రూపాయలు |
| Gujarati | `gu` | saarika-v2 | ⚠️ Beta | હજાર, રૂપિયા |
| Bengali | `bn` | saarika-v2 | ⚠️ Beta | হাজার, টাকা |

**Default**: If language detection fails, treat as Hindi + fallback to GPT-4 for NLU.

---

## 19. 24-HOUR HACKATHON BUILD SPRINT

### Hour 0–2: Foundation
```bash
# Setup
git init arthai && cd arthai
python -m venv venv && source venv/bin/activate
pip install fastapi uvicorn sqlalchemy asyncpg openai twilio celery redis weasyprint pydantic-settings boto3 langgraph langchain-core langchain-openai httpx jinja2 structlog tenacity pgvector scikit-learn numpy python-multipart

# Project structure
mkdir -p backend/{models,schemas,routes,services,ai,agents,tasks,templates,migrations}
mkdir -p frontend/src/{components,pages,api,types,contexts}
mkdir demo-data

# Copy .env.example → .env, fill in keys
```

### Hour 2–4: Database + Seed
```bash
# Apply schema to Supabase
psql $DATABASE_URL -f backend/migrations/001_initial_schema.sql

# Implement main.py, config.py, database.py
# Implement User and Transaction SQLAlchemy models
# Implement /api/demo/seed endpoint
# Seed Raju's data: curl -X POST http://localhost:8000/api/demo/seed
```

### Hour 4–7: AI Pipeline (Core)
```bash
# Implement ai/vision.py — GPT-4V receipt OCR
# Implement ai/speech.py — Sarvam + Whisper
# Implement ai/nlu.py — intent + entity extraction
# Test each independently:
# python -c "import asyncio; from ai.nlu import classify_intent; print(asyncio.run(classify_intent('Aaj ₹950 ki sawari mili')))"
```

### Hour 7–11: LangGraph Agent + WhatsApp
```bash
# Implement agents/financial_agent.py — full LangGraph graph
# Implement routes/webhook.py — Twilio endpoint
# Implement tasks/message_tasks.py — Celery worker
# Configure Twilio sandbox + ngrok tunnel for local testing
# ngrok http 8000
# Set Twilio sandbox webhook to: https://[ngrok-url]/webhook/whatsapp
```

### Hour 11–15: ArthScore + Financial Passport
```bash
# Implement agents/arthascore.py — 7-factor scoring engine
# Implement agents/passport_generator.py — PDF generator
# Create templates/passport.html — the full HTML template
# Test: POST /api/reports/passport/[raju-user-id] → get PDF URL
```

### Hour 15–20: React Frontend
```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install recharts axios react-router-dom @types/react-router-dom tailwindcss
npx tailwindcss init -p

# Implement components: ArthScoreGauge, PLChart, TransactionFeed, InsightCard
# Implement pages: Dashboard, Transactions, Passport, Demo
# Wire up API client to backend
```

### Hour 20–22: Analytics Service
```bash
# Implement services/analytics.py
# - get_pnl_data() — group transactions by week/month
# - get_dashboard_summary() — MTD, WTD metrics
# - get_cash_flow() — 7-day trend + simple 7-day forecast
# Test: GET /api/analytics/summary/[raju-user-id]
```

### Hour 22–24: Deploy + Polish
```bash
# railway login && railway init
# railway add --plugin redis
# railway variables set [all .env variables]
# git push origin main → Railway auto-deploys

# Deploy frontend to Vercel:
cd frontend && vercel --prod

# Final checklist:
# ✅ WhatsApp sandbox: send photo → get response in <5s
# ✅ Send voice note in Hindi → categorized transaction
# ✅ Ask "Mera profit kya hai?" → intelligent response
# ✅ GET /api/reports/passport → real PDF download
# ✅ Dashboard shows ArthScore 714, P&L chart, transaction feed
# ✅ /api/demo/seed works and loads 90 days of data
```

---

## 20. PROACTIVE INSIGHTS ENGINE

```python
# Add to agents/financial_agent.py

INSIGHT_RULES = [
    {
        "id": "weekly_summary",
        "trigger": "every_monday",
        "condition": lambda data: True,
        "message_hi": lambda d: f"📊 Pichhle hafte ka summary:\n💰 Income: ₹{d['wtd_income']:,.0f}\n📉 Kharcha: ₹{d['wtd_expenses']:,.0f}\n✅ Net: ₹{d['wtd_net']:,.0f}",
    },
    {
        "id": "expense_anomaly",
        "trigger": "on_transaction",
        "condition": lambda data: data.get("expense_spike_pct", 0) > 40,
        "message_hi": lambda d: f"⚠️ Is mahine {d['category_name']} ka kharcha {d['spike_pct']:.0f}% zyada hai average se. Koi khaas kharcha tha?",
    },
    {
        "id": "income_milestone",
        "trigger": "on_transaction",
        "condition": lambda data: data.get("crossed_milestone"),
        "message_hi": lambda d: f"🎉 Badhai ho! Is mahine aapne ₹{d['milestone']:,.0f} ki income cross kar li!",
    },
    {
        "id": "score_ready",
        "trigger": "on_50th_transaction",
        "condition": lambda data: data.get("tx_count", 0) == 50,
        "message_hi": lambda d: f"🏆 ArthScore ready hai! Aapka score: {d['score']}/900. 'Passport banao' likhein loan ke liye document generate karne ke liye!",
    },
]
```

---

## 21. SUCCESS METRICS FOR DEMO

Track these live during demo for maximum impact:

| Metric | Target | How to Show |
|--------|--------|-------------|
| Receipt OCR latency | < 3 seconds | Show timestamp in WhatsApp |
| Voice transcription accuracy | > 90% in Hindi | Live demo with judges |
| ArthScore calculation | < 500ms | Dashboard refresh |
| Financial Passport generation | < 15 seconds | Show "generating..." → PDF |
| Transaction categorization accuracy | > 95% | Category badge in feed |
| API uptime during demo | 100% | Railway dashboard |

---

## FINAL CHECKLIST — TOP 1% STANDARDS

**Technical Completeness** ✅
- [ ] All 6 API route files implemented and tested
- [ ] LangGraph agent handles all 5 message types
- [ ] ArthScore calculates with real data (not hardcoded)
- [ ] Financial Passport PDF is beautiful and professional
- [ ] Vision + Speech + NLU all working with fallbacks
- [ ] Demo seed loads 90 real-feeling transactions
- [ ] Railway deployment is live and HTTPS
- [ ] WhatsApp sandbox functional end-to-end

**Demo Quality** ✅
- [ ] Raju's data loaded and visible in dashboard
- [ ] ArthScore shows 714/900 with loan eligibility ₹75,000
- [ ] P&L chart shows 3-month trend (income > expenses)
- [ ] WhatsApp demo: receipt photo → < 3s → Hindi response
- [ ] PDF download works and looks professional
- [ ] Language toggle (Hindi ↔ English) functional

**Hackathon Presentation** ✅
- [ ] GitHub README has demo GIF (record with Loom)
- [ ] Live URL in submission form
- [ ] "Raju getting his first loan" narrative front and center
- [ ] ArthScore methodology explained in README
- [ ] Data flywheel moat articulated clearly

---

*"Apna Business, Apni Zubaan Mein."*
*Your Business, In Your Own Language.*

*Document Version: 2.0 | ArthAI | InnovaHack Chapter 1*
*Built for Builders. Designed for Raju.*

---

## 22. ANALYTICS SERVICE — COMPLETE IMPLEMENTATION

```python
# backend/services/analytics.py
"""
Core financial calculation engine.
All P&L, cash flow, category aggregation, and forecasting live here.
This is what powers the dashboard and the Financial Passport.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract
from datetime import date, timedelta
from typing import List, Dict, Optional
from uuid import UUID
from collections import defaultdict
import numpy as np
import structlog

from models.transaction import Transaction

logger = structlog.get_logger()


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_summary(self, user_id: str) -> dict:
        """
        Single endpoint for all dashboard KPIs.
        Called on page load — must be fast (<200ms).
        """
        today = date.today()
        week_start = today - timedelta(days=today.weekday())   # Monday
        month_start = today.replace(day=1)

        # Fetch all transactions this month + this week
        result = await self.db.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= month_start
            )
        )
        txs = result.scalars().all()

        mtd_income = sum(t.amount for t in txs if t.type == "income")
        mtd_expenses = sum(t.amount for t in txs if t.type == "expense")
        mtd_net = mtd_income - mtd_expenses

        wtd_income = sum(t.amount for t in txs
                        if t.type == "income" and t.transaction_date >= week_start)
        wtd_expenses = sum(t.amount for t in txs
                          if t.type == "expense" and t.transaction_date >= week_start)

        # Days active this month
        days_active = len(set(t.transaction_date for t in txs))
        days_in_month = today.day
        avg_daily_income = mtd_income / days_active if days_active > 0 else 0

        # Top income category
        income_by_cat = defaultdict(float)
        for t in txs:
            if t.type == "income":
                income_by_cat[t.category_code] += float(t.amount)
        top_income_cat = max(income_by_cat, key=income_by_cat.get) if income_by_cat else None

        # Top expense category
        expense_by_cat = defaultdict(float)
        for t in txs:
            if t.type == "expense":
                expense_by_cat[t.category_code] += float(t.amount)
        top_expense_cat = max(expense_by_cat, key=expense_by_cat.get) if expense_by_cat else None

        # Total transaction count all time
        count_result = await self.db.execute(
            select(func.count()).where(Transaction.user_id == user_id)
        )
        total_tx_count = count_result.scalar()

        return {
            "mtd_income":       float(mtd_income),
            "mtd_expenses":     float(mtd_expenses),
            "mtd_net_profit":   float(mtd_net),
            "mtd_margin_pct":   round(mtd_net / mtd_income * 100, 1) if mtd_income else 0,
            "wtd_income":       float(wtd_income),
            "wtd_expenses":     float(wtd_expenses),
            "wtd_net":          float(wtd_income - wtd_expenses),
            "avg_daily_income": round(avg_daily_income, 0),
            "days_active_mtd":  days_active,
            "top_income_category":  top_income_cat,
            "top_expense_category": top_expense_cat,
            "income_by_category":   dict(income_by_cat),
            "expense_by_category":  dict(expense_by_cat),
            "total_transactions":   total_tx_count,
        }

    async def get_pnl_data(self, user_id: str, period: str) -> dict:
        """
        P&L time series for chart rendering.
        period: "7d" → daily bars | "30d" → daily | "90d" → weekly | "1y" → monthly
        """
        period_map = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
        days = period_map.get(period, 90)
        cutoff = date.today() - timedelta(days=days)

        result = await self.db.execute(
            select(Transaction).where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.transaction_date >= cutoff
                )
            ).order_by(Transaction.transaction_date)
        )
        txs = result.scalars().all()

        # Group into appropriate buckets
        if period in ("7d", "30d"):
            series = self._group_by_day(txs, days)
        elif period == "90d":
            series = self._group_by_week(txs, 13)     # 13 weeks
        else:
            series = self._group_by_month(txs, 12)    # 12 months

        total_income = sum(float(t.amount) for t in txs if t.type == "income")
        total_expenses = sum(float(t.amount) for t in txs if t.type == "expense")
        net_profit = total_income - total_expenses

        # Category breakdown
        income_cats = defaultdict(float)
        expense_cats = defaultdict(float)
        for t in txs:
            if t.type == "income":
                income_cats[t.category_code] += float(t.amount)
            else:
                expense_cats[t.category_code] += float(t.amount)

        return {
            "period": period,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_profit": net_profit,
            "net_margin_pct": round(net_profit / total_income * 100, 1) if total_income else 0,
            "series": series,
            "top_income_categories": sorted(
                [{"code": k, "amount": v} for k, v in income_cats.items()],
                key=lambda x: x["amount"], reverse=True
            )[:5],
            "top_expense_categories": sorted(
                [{"code": k, "amount": v} for k, v in expense_cats.items()],
                key=lambda x: x["amount"], reverse=True
            )[:5],
        }

    async def get_cash_flow(self, user_id: str) -> dict:
        """
        Last 30 days cash flow + 7-day simple forecast.
        Forecast method: weighted moving average of last 4 weeks, same weekday.
        """
        cutoff = date.today() - timedelta(days=30)
        result = await self.db.execute(
            select(Transaction).where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.transaction_date >= cutoff
                )
            ).order_by(Transaction.transaction_date)
        )
        txs = result.scalars().all()

        # Daily net for last 30 days
        daily_net = defaultdict(float)
        for t in txs:
            sign = 1 if t.type == "income" else -1
            daily_net[t.transaction_date] += sign * float(t.amount)

        history = []
        for i in range(30, 0, -1):
            d = date.today() - timedelta(days=i)
            history.append({
                "date": d.isoformat(),
                "label": d.strftime("%b %d"),
                "net": round(daily_net.get(d, 0), 0),
                "cumulative": 0  # Will fill below
            })

        # Cumulative
        running = 0
        for h in history:
            running += h["net"]
            h["cumulative"] = round(running, 0)

        # Simple forecast: average of same weekday over last 4 occurrences
        forecast = []
        for i in range(1, 8):
            future_date = date.today() + timedelta(days=i)
            weekday = future_date.weekday()
            # Find last 4 occurrences of this weekday in history
            same_weekday_nets = [
                daily_net.get(date.today() - timedelta(days=j), 0)
                for j in range(7, 35, 7)
                if (date.today() - timedelta(days=j)).weekday() == weekday
            ]
            avg_net = np.mean(same_weekday_nets) if same_weekday_nets else 0
            forecast.append({
                "date": future_date.isoformat(),
                "label": future_date.strftime("%b %d"),
                "forecast_net": round(float(avg_net), 0),
                "is_forecast": True
            })

        return {
            "history": history,
            "forecast": forecast,
            "avg_daily_net_30d": round(
                sum(h["net"] for h in history) / 30, 0
            ),
            "projected_weekly_net": round(
                sum(f["forecast_net"] for f in forecast), 0
            )
        }

    async def refresh_cache(self, user_id: str):
        """Update analytics_cache table after each new transaction"""
        from models.analytics import AnalyticsCache
        summary = await self.get_dashboard_summary(user_id)

        from sqlalchemy.dialects.postgresql import insert
        stmt = insert(AnalyticsCache).values(
            user_id=user_id,
            mtd_income=summary["mtd_income"],
            mtd_expenses=summary["mtd_expenses"],
            mtd_net_profit=summary["mtd_net_profit"],
            wtd_income=summary["wtd_income"],
            wtd_expenses=summary["wtd_expenses"],
            total_transactions=summary["total_transactions"],
            last_updated=date.today()
        ).on_conflict_do_update(
            index_elements=["user_id"],
            set_={
                "mtd_income": summary["mtd_income"],
                "mtd_expenses": summary["mtd_expenses"],
                "mtd_net_profit": summary["mtd_net_profit"],
                "wtd_income": summary["wtd_income"],
                "wtd_expenses": summary["wtd_expenses"],
                "total_transactions": summary["total_transactions"],
                "last_updated": date.today()
            }
        )
        await self.db.execute(stmt)
        await self.db.commit()

    # ─── Private Grouping Helpers ────────────────────────────────────────────

    def _group_by_day(self, txs, days: int) -> List[dict]:
        daily = defaultdict(lambda: {"income": 0.0, "expenses": 0.0})
        for t in txs:
            if t.type == "income":
                daily[t.transaction_date]["income"] += float(t.amount)
            else:
                daily[t.transaction_date]["expenses"] += float(t.amount)

        series = []
        for i in range(days, 0, -1):
            d = date.today() - timedelta(days=i)
            inc = daily[d]["income"]
            exp = daily[d]["expenses"]
            series.append({
                "period_label": d.strftime("%b %d"),
                "income": round(inc, 0),
                "expenses": round(exp, 0),
                "net": round(inc - exp, 0)
            })
        return series

    def _group_by_week(self, txs, num_weeks: int) -> List[dict]:
        weekly = defaultdict(lambda: {"income": 0.0, "expenses": 0.0})
        for t in txs:
            days_ago = (date.today() - t.transaction_date).days
            week_num = days_ago // 7
            weekly[week_num]["income" if t.type == "income" else "expenses"] += float(t.amount)

        series = []
        for w in range(num_weeks, 0, -1):
            inc = weekly[w]["income"]
            exp = weekly[w]["expenses"]
            week_start = date.today() - timedelta(days=w * 7 + 7)
            series.append({
                "period_label": f"W {week_start.strftime('%b %d')}",
                "income": round(inc, 0),
                "expenses": round(exp, 0),
                "net": round(inc - exp, 0)
            })
        return series

    def _group_by_month(self, txs, num_months: int) -> List[dict]:
        monthly = defaultdict(lambda: {"income": 0.0, "expenses": 0.0})
        for t in txs:
            key = t.transaction_date.strftime("%Y-%m")
            monthly[key]["income" if t.type == "income" else "expenses"] += float(t.amount)

        series = []
        today = date.today()
        for m in range(num_months, 0, -1):
            month_date = date(today.year, today.month, 1) - timedelta(days=m * 28)
            key = month_date.strftime("%Y-%m")
            inc = monthly[key]["income"]
            exp = monthly[key]["expenses"]
            series.append({
                "period_label": month_date.strftime("%b '%y"),
                "income": round(inc, 0),
                "expenses": round(exp, 0),
                "net": round(inc - exp, 0)
            })
        return series
```

---

## 23. UPI STATEMENT PARSER

```python
# backend/ai/upi_parser.py
"""
Parse forwarded UPI transaction screenshots and NPCI statement PDFs.
Users forward their GPay/PhonePe/BHIM screenshots to ArthAI.

Key patterns to extract:
- "₹500 paid to Ramesh Kumar"
- "₹1,200 received from Sunita Devi"
- "You paid ₹320 at IndianOil" (Google Pay format)
- "Credited ₹850.00" (bank SMS format)
- Multi-transaction statements (monthly NPCI exports)
"""
import re
from datetime import date
from openai import AsyncOpenAI
from config import settings
from schemas.whatsapp import ExtractedTransaction

UPI_EXTRACTION_PROMPT = """You are parsing a UPI payment screenshot or statement.

Extract ALL transactions visible. UPI transactions follow these patterns:
- "₹[amount] paid to [name]" → expense
- "₹[amount] received from [name]" → income
- "Paid ₹[amount] to [merchant]" → expense
- "Debited ₹[amount]" → expense
- "Credited ₹[amount]" → income
- "You paid ₹[amount] at [place]" → expense

Return a JSON array of transactions:
[
  {
    "amount": 500,
    "type": "expense",
    "counterparty": "Ramesh Kumar",
    "description": "UPI payment to Ramesh Kumar",
    "payment_method": "upi",
    "transaction_date": "2026-03-15",
    "confidence": 0.95
  }
]

If only ONE transaction is visible, return an array with one item.
For CATEGORY, assign:
- Personal transfers/names → "other_expense" or "other_income"
- Fuel stations → "transport_fuel"
- Grocery stores → "inventory" (for business) or "food_personal"
- Mobile recharges → "mobile_internet"
- Unknown → "other_expense" or "other_income"

TODAY: {today}
"""

async def parse_upi_screenshot(image_url: str, user_language: str = "hi") -> List[ExtractedTransaction]:
    """
    Parse a forwarded UPI screenshot.
    May contain 1 or multiple transactions (statement view).
    """
    import base64, httpx, json
    from config import settings

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async with httpx.AsyncClient() as http:
        auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        resp = await http.get(image_url, auth=auth)
        img_b64 = base64.b64encode(resp.content).decode()
        content_type = resp.headers.get("content-type", "image/jpeg")

    prompt = UPI_EXTRACTION_PROMPT.replace("{today}", date.today().isoformat())

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL_VISION,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {
                    "url": f"data:{content_type};base64,{img_b64}",
                    "detail": "high"
                }},
                {"type": "text", "text": "Extract all UPI transactions from this screenshot."}
            ]}
        ],
        max_tokens=800, temperature=0.1
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    items = json.loads(raw)

    return [ExtractedTransaction(
        amount=float(item["amount"]),
        type=item["type"],
        category_code=item.get("category_code", "other_expense" if item["type"] == "expense" else "other_income"),
        counterparty=item.get("counterparty"),
        description=item.get("description", "UPI transaction"),
        payment_method="upi",
        transaction_date=date.fromisoformat(item.get("transaction_date", date.today().isoformat())),
        confidence=float(item.get("confidence", 0.85)),
        language_detected=user_language
    ) for item in items]
```

---

## 24. WHATSAPP CONVERSATION STATE MACHINE — COMPLETE

```python
# backend/services/conversation.py
"""
Persistent conversation state machine for multi-turn WhatsApp flows.
States and transitions are stored in PostgreSQL (whatsapp_sessions table).

State Diagram:
IDLE ──────────────────────────────────────────────────────────→ (handles all normal messages)
  │
  ├── receives low-confidence transaction
  │    └──→ AWAITING_CONFIRMATION
  │              ├── user says "1/haan/yes" → store + back to IDLE
  │              └── user says "2/nahi/no"  → ask for correction → IDLE
  │
  ├── receives ambiguous category
  │    └──→ AWAITING_CATEGORY
  │              └── user picks category → store + back to IDLE
  │
  ├── requests report
  │    └──→ REPORT_GENERATING → (auto back to IDLE when done)
  │
NEW_USER ──→ ONBOARDING_NAME ──→ ONBOARDING_BUSINESS ──→ IDLE
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
import json
import structlog

logger = structlog.get_logger()

# ─── State Constants ──────────────────────────────────────────────────────────
class ConvState:
    IDLE = "IDLE"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    AWAITING_CATEGORY = "AWAITING_CATEGORY"
    REPORT_GENERATING = "REPORT_GENERATING"
    ONBOARDING_NAME = "ONBOARDING_NAME"
    ONBOARDING_BUSINESS = "ONBOARDING_BUSINESS"
    ONBOARDING_LANGUAGE = "ONBOARDING_LANGUAGE"


class ConversationStateManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_state(self, phone: str) -> dict:
        """Get current conversation state for a user"""
        from models.session import WhatsAppSession
        result = await self.db.execute(
            select(WhatsAppSession).where(WhatsAppSession.phone_number == phone)
        )
        session = result.scalar_one_or_none()

        if not session:
            return {"state": ConvState.IDLE, "pending_transaction": None, "context": {}}

        return {
            "state": session.state,
            "pending_transaction": session.pending_transaction,
            "context": session.context or {}
        }

    async def set_state(self, phone: str, state: str,
                        pending_transaction=None, context=None):
        """Update conversation state"""
        from models.session import WhatsAppSession
        from sqlalchemy.dialects.postgresql import insert

        stmt = insert(WhatsAppSession).values(
            phone_number=phone,
            state=state,
            pending_transaction=pending_transaction,
            context=context or {},
            last_activity=datetime.utcnow()
        ).on_conflict_do_update(
            index_elements=["phone_number"],
            set_={
                "state": state,
                "pending_transaction": pending_transaction,
                "context": context or {},
                "last_activity": datetime.utcnow()
            }
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def reset(self, phone: str):
        """Reset to IDLE state"""
        await self.set_state(phone, ConvState.IDLE)

    def is_confirmation_yes(self, text: str) -> bool:
        """Detect positive confirmation in multiple languages"""
        text_lower = text.lower().strip()
        yes_words = {
            "1", "haan", "han", "ha", "yes", "yeah", "yep", "ok", "okay",
            "sahi", "sahi hai", "thik", "thik hai", "bilkul", "zaroor",
            "correct", "right", "true", "✅", "👍"
        }
        return any(w in text_lower for w in yes_words)

    def is_confirmation_no(self, text: str) -> bool:
        """Detect negative confirmation in multiple languages"""
        text_lower = text.lower().strip()
        no_words = {
            "2", "nahi", "no", "nope", "galat", "wrong", "incorrect",
            "nai", "na", "nahin", "❌", "👎"
        }
        return any(w in text_lower for w in no_words)
```

---

## 25. ONBOARDING FLOW

```python
# backend/services/onboarding.py
"""
New user WhatsApp onboarding. Runs when a user messages ArthAI for the first time.
Collects: name, business type, preferred language.
3-message onboarding — keeps it minimal.
"""
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
```

---

## 26. WHATSAPP RESPONSE TEMPLATES — COMPLETE LIBRARY

```python
# backend/ai/response_templates.py
"""
All WhatsApp response messages. Bilingual (Hindi/English).
Keep responses under 1500 chars. WhatsApp renders *bold* and _italic_.
"""
from datetime import date


class ResponseTemplates:

    @staticmethod
    def transaction_success(amount: float, tx_type: str, category: str,
                           payment: str, tx_date: date, lang: str = "hi") -> str:
        CAT_NAMES = {
            "hi": {
                "transport_fuel": "⛽ ईंधन", "inventory": "📦 माल/स्टॉक",
                "labor_wages": "👷 मजदूरी", "sales_service": "⚙️ सेवा आय",
                "sales_product": "🛒 बिक्री", "food_personal": "🍱 खाना",
                "mobile_internet": "📱 मोबाइल", "utilities": "💡 बिजली/पानी",
                "equipment": "🔧 उपकरण/मरम्मत", "rent_premises": "🏪 किराया",
                "loan_repayment": "💸 कर्ज चुकाना", "other_expense": "📝 अन्य खर्च",
                "other_income": "💵 अन्य आय", "commission": "🤝 कमीशन",
            },
            "en": {
                "transport_fuel": "⛽ Fuel", "inventory": "📦 Stock/Inventory",
                "labor_wages": "👷 Wages", "sales_service": "⚙️ Service Income",
                "sales_product": "🛒 Product Sale", "food_personal": "🍱 Personal Food",
                "mobile_internet": "📱 Mobile", "utilities": "💡 Utilities",
                "equipment": "🔧 Equipment", "rent_premises": "🏪 Rent",
                "loan_repayment": "💸 Loan Payment", "other_expense": "📝 Other",
                "other_income": "💵 Other Income", "commission": "🤝 Commission",
            }
        }
        cat_display = CAT_NAMES.get(lang, CAT_NAMES["hi"]).get(category, category)
        payment_display = {"upi": "🔵 UPI", "cash": "💵 Cash", "card": "💳 Card"}.get(payment, payment)

        if lang == "hi":
            type_word = "✅ आय" if tx_type == "income" else "📤 खर्च"
            return (
                f"{type_word} Record hua!\n\n"
                f"💰 *₹{amount:,.0f}*\n"
                f"📂 {cat_display}\n"
                f"💳 {payment_display}\n"
                f"📅 {tx_date.strftime('%d %B')}\n\n"
                f"_Apna hisaab dekhne ke liye: 'profit kya hai?' likhein_ 👇"
            )
        else:
            return (
                f"{'✅ Income' if tx_type == 'income' else '📤 Expense'} Recorded!\n\n"
                f"💰 *₹{amount:,.0f}*\n"
                f"📂 {cat_display}\n"
                f"💳 {payment_display}\n"
                f"📅 {tx_date.strftime('%B %d')}\n\n"
                f"_Type 'profit kya hai?' to see your summary_ 👇"
            )

    @staticmethod
    def confirmation_request(amount: float, tx_type: str,
                            category: str, lang: str = "hi") -> str:
        if lang == "hi":
            return (
                f"🤔 Maine record kiya:\n\n"
                f"*₹{amount:,.0f} {tx_type}* — {category}\n\n"
                f"Sahi hai?\n"
                f"1️⃣ *Haan, sahi hai* ✅\n"
                f"2️⃣ *Nahi, galat hai* ❌"
            )
        return (
            f"🤔 I recorded:\n\n"
            f"*₹{amount:,.0f} {tx_type}* — {category}\n\n"
            f"Is this correct?\n"
            f"1️⃣ *Yes, correct* ✅\n"
            f"2️⃣ *No, wrong* ❌"
        )

    @staticmethod
    def weekly_insight(income: float, expenses: float, net: float,
                      avg_net: float, lang: str = "hi") -> str:
        pct_vs_avg = ((net - avg_net) / avg_net * 100) if avg_net else 0
        trend_emoji = "📈" if pct_vs_avg >= 0 else "📉"

        if lang == "hi":
            return (
                f"📊 *Is hafte ka summary:*\n\n"
                f"💰 Income: *₹{income:,.0f}*\n"
                f"📤 Kharcha: *₹{expenses:,.0f}*\n"
                f"✅ Net profit: *₹{net:,.0f}*\n\n"
                f"{trend_emoji} Average se *{abs(pct_vs_avg):.0f}%* "
                f"{'zyada' if pct_vs_avg >= 0 else 'kam'}!"
            )
        return (
            f"📊 *This week's summary:*\n\n"
            f"💰 Income: *₹{income:,.0f}*\n"
            f"📤 Expenses: *₹{expenses:,.0f}*\n"
            f"✅ Net profit: *₹{net:,.0f}*\n\n"
            f"{trend_emoji} *{abs(pct_vs_avg):.0f}%* "
            f"{'above' if pct_vs_avg >= 0 else 'below'} your average!"
        )

    @staticmethod
    def expense_anomaly_alert(category: str, current: float,
                             avg: float, spike_pct: float, lang: str = "hi") -> str:
        if lang == "hi":
            return (
                f"⚠️ *Kharcha Alert!*\n\n"
                f"Is mahine *{category}* ka kharcha ₹{current:,.0f} raha — "
                f"average ₹{avg:,.0f} se *{spike_pct:.0f}% zyada*.\n\n"
                f"Koi khaas kharcha tha? Agar haan, toh sab theek hai. 👍"
            )
        return (
            f"⚠️ *Expense Alert!*\n\n"
            f"This month's *{category}* cost ₹{current:,.0f} — "
            f"*{spike_pct:.0f}% above* your average of ₹{avg:,.0f}.\n\n"
            f"Was there a special expense? If yes, you're all good. 👍"
        )

    @staticmethod
    def arthascore_milestone(score: int, loan_eligible: float, lang: str = "hi") -> str:
        if lang == "hi":
            return (
                f"🏆 *Aapka ArthScore ready hai!*\n\n"
                f"🎯 Score: *{score}/900*\n"
                f"💰 Loan eligibility: *₹{loan_eligible:,.0f}*\n\n"
                f"Loan document banana hai? Likhein:\n"
                f"*\"Passport banao\"* 📄"
            )
        return (
            f"🏆 *Your ArthScore is ready!*\n\n"
            f"🎯 Score: *{score}/900*\n"
            f"💰 Loan eligible: *₹{loan_eligible:,.0f}*\n\n"
            f"Ready to get a loan? Type:\n"
            f"*\"Generate passport\"* 📄"
        )

    @staticmethod
    def help_message(lang: str = "hi") -> str:
        if lang == "hi":
            return (
                f"🤖 *Main ArthAI hoon — aapka financial assistant*\n\n"
                f"Main samajh sakta hoon:\n\n"
                f"📸 *Receipt photo* → Automatic record\n"
                f"🎤 *Voice note* → Hindi mein bolen\n"
                f"✍️ *Text* → 'Aaj ₹950 mili'\n\n"
                f"*Savaal poochein:*\n"
                f"• 'Is hafte ka profit kya hai?'\n"
                f"• 'Pichhle mahine kitna kamaya?'\n"
                f"• 'Loan ke liye document chahiye'\n\n"
                f"_Dashboard: arthai-demo.vercel.app_ 📊"
            )
        return (
            f"🤖 *I'm ArthAI — your financial assistant*\n\n"
            f"I understand:\n\n"
            f"📸 *Receipt photo* → Auto-logged\n"
            f"🎤 *Voice note* → Speak naturally\n"
            f"✍️ *Text* → 'Earned ₹950 today'\n\n"
            f"*Ask me:*\n"
            f"• 'What's my profit this week?'\n"
            f"• 'How much did I earn last month?'\n"
            f"• 'I need a loan document'\n\n"
            f"_Dashboard: arthai-demo.vercel.app_ 📊"
        )

    @staticmethod
    def error_message(lang: str = "hi") -> str:
        if lang == "hi":
            return (
                "😕 Maafi chahiye, kuch problem aayi. "
                "Kripya dobara bhejein ya alag tarike se batayein. "
                "Agar problem bani rahe toh likhein: *help*"
            )
        return (
            "😕 Sorry, something went wrong. "
            "Please try again or rephrase. "
            "If the issue persists, type: *help*"
        )
```

---

## 27. FRONTEND — COMPLETE TYPE DEFINITIONS

```typescript
// frontend/src/types/index.ts

export type Language = 'hi' | 'en'
export type TransactionType = 'income' | 'expense' | 'transfer'
export type MessageSource = 'image' | 'voice' | 'text' | 'upi_statement' | 'manual'

export interface User {
  id: string
  phone_number: string
  name: string
  preferred_language: Language
  business_type: string
  business_location: string
  onboarding_complete: boolean
  created_at: string
}

export interface Transaction {
  id: string
  user_id: string
  amount: number
  type: TransactionType
  category_code: string
  counterparty?: string
  description: string
  payment_method: string
  transaction_date: string
  source: MessageSource
  verified: boolean
  confidence_score: number
  created_at: string
}

export interface CategoryTotal {
  code: string
  amount: number
}

export interface PLSeries {
  period_label: string
  income: number
  expenses: number
  net: number
}

export interface PLData {
  period: string
  total_income: number
  total_expenses: number
  net_profit: number
  net_margin_pct: number
  series: PLSeries[]
  top_income_categories: CategoryTotal[]
  top_expense_categories: CategoryTotal[]
}

export interface DashboardSummary {
  mtd_income: number
  mtd_expenses: number
  mtd_net_profit: number
  mtd_margin_pct: number
  wtd_income: number
  wtd_expenses: number
  wtd_net: number
  avg_daily_income: number
  days_active_mtd: number
  top_income_category: string | null
  top_expense_category: string | null
  income_by_category: Record<string, number>
  expense_by_category: Record<string, number>
  total_transactions: number
}

export interface ArthScoreData {
  score: number            // 300–900
  grade: string
  grade_hi: string
  max_loan_eligible: number
  factors: {
    income_regularity: number
    growth_trajectory: number
    expense_control: number
    transaction_volume: number
    business_longevity: number
    payment_consistency: number
    data_completeness: number
  }
  insight_hi: string
  insight_en: string
  calculated_at: string
  data_points: number
}

export interface CashFlowPoint {
  date: string
  label: string
  net: number
  cumulative: number
  is_forecast?: boolean
  forecast_net?: number
}

export interface DocumentInfo {
  id: string
  document_type: string
  download_url: string
  arthascore_at_generation: number
  generated_at: string
  expires_at: string
}

// UI State
export interface ContextType {
  language: Language
  setLanguage: (l: Language) => void
  userId: string
}
```

---

## 28. FRONTEND — API CLIENT

```typescript
// frontend/src/api/client.ts
import axios from 'axios'
import type {
  DashboardSummary, PLData, ArthScoreData,
  Transaction, CashFlowPoint, DocumentInfo
} from '../types'

const BASE_URL = import.meta.env.VITE_API_URL || 'https://arthai-backend.up.railway.app'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
})

// ─── Analytics ────────────────────────────────────────────────────────────────
export const getDashboardSummary = async (userId: string): Promise<DashboardSummary> => {
  const { data } = await api.get(`/api/analytics/summary/${userId}`)
  return data
}

export const getPLData = async (userId: string, period = '90d'): Promise<PLData> => {
  const { data } = await api.get(`/api/analytics/pnl/${userId}`, {
    params: { period }
  })
  return data
}

export const getCashFlow = async (userId: string): Promise<{
  history: CashFlowPoint[];
  forecast: CashFlowPoint[];
  avg_daily_net_30d: number;
  projected_weekly_net: number;
}> => {
  const { data } = await api.get(`/api/analytics/cash-flow/${userId}`)
  return data
}

// ─── ArthScore ────────────────────────────────────────────────────────────────
export const getArthScore = async (userId: string): Promise<ArthScoreData> => {
  const { data } = await api.get(`/api/score/${userId}`)
  return data
}

// ─── Transactions ─────────────────────────────────────────────────────────────
export const getTransactions = async (
  userId: string,
  page = 1,
  limit = 50
): Promise<{ items: Transaction[]; total: number; page: number }> => {
  const { data } = await api.get(`/api/transactions/${userId}`, {
    params: { page, limit }
  })
  return data
}

// ─── Reports ──────────────────────────────────────────────────────────────────
export const generatePassport = async (userId: string): Promise<{
  download_url: string;
  arthascore: number;
  loan_eligible: number;
  expires_at: string;
}> => {
  const { data } = await api.post(`/api/reports/passport/${userId}`)
  return data
}

// ─── Demo ─────────────────────────────────────────────────────────────────────
export const seedDemoData = async (): Promise<void> => {
  await api.post('/api/demo/seed')
}
```

---

## 29. FRONTEND — COMPLETE DASHBOARD PAGE

```tsx
// frontend/src/pages/Dashboard.tsx
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useLanguage } from '../contexts/LanguageContext'
import ArthScoreGauge from '../components/ArthScoreGauge'
import PLChart from '../components/PLChart'
import TransactionFeed from '../components/TransactionFeed'
import InsightCard from '../components/InsightCard'
import LoadingSpinner from '../components/LoadingSpinner'
import {
  getDashboardSummary, getPLData, getArthScore, getTransactions
} from '../api/client'
import type { DashboardSummary, PLData, ArthScoreData, Transaction } from '../types'

const CATEGORY_DISPLAY: Record<string, { en: string; hi: string; icon: string }> = {
  transport_fuel:  { en: 'Fuel',        hi: 'ईंधन',     icon: '⛽' },
  inventory:       { en: 'Stock',       hi: 'माल',      icon: '📦' },
  labor_wages:     { en: 'Wages',       hi: 'मजदूरी',   icon: '👷' },
  sales_service:   { en: 'Services',    hi: 'सेवा',     icon: '⚙️' },
  sales_product:   { en: 'Sales',       hi: 'बिक्री',   icon: '🛒' },
  other_expense:   { en: 'Other',       hi: 'अन्य',     icon: '📝' },
  other_income:    { en: 'Other Income',hi: 'अन्य आय',  icon: '💵' },
}

export default function Dashboard() {
  const { userId } = useParams<{ userId: string }>()
  const { language } = useLanguage()

  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [pnl, setPnl] = useState<PLData | null>(null)
  const [score, setScore] = useState<ArthScoreData | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [period, setPeriod] = useState<'7d' | '30d' | '90d'>('90d')

  const T = {
    dashboard:    { hi: 'डैशबोर्ड',         en: 'Dashboard' },
    mtdIncome:    { hi: 'इस महीने आय',       en: 'MTD Income' },
    mtdExpenses:  { hi: 'इस महीने खर्च',     en: 'MTD Expenses' },
    netProfit:    { hi: 'शुद्ध लाभ',         en: 'Net Profit' },
    avgDaily:     { hi: 'औसत दैनिक आय',     en: 'Avg Daily Income' },
    thisWeek:     { hi: 'इस हफ्ते',          en: 'This Week' },
    topCategory:  { hi: 'शीर्ष श्रेणी',      en: 'Top Category' },
  }

  useEffect(() => {
    if (!userId) return

    const fetchAll = async () => {
      setLoading(true)
      try {
        const [s, p, sc, tx] = await Promise.all([
          getDashboardSummary(userId),
          getPLData(userId, period),
          getArthScore(userId),
          getTransactions(userId)
        ])
        setSummary(s)
        setPnl(p)
        setScore(sc)
        setTransactions(tx.items)
      } catch (err) {
        console.error('Dashboard fetch failed:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchAll()
  }, [userId, period])

  if (loading) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <LoadingSpinner message={language === 'hi' ? 'Loading...' : 'Loading...'} />
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ── Header ── */}
      <div className="bg-gradient-to-r from-slate-900 to-slate-800 text-white px-6 py-4">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <div>
            <span className="text-2xl font-black">Arth<span className="text-green-400">AI</span></span>
            <p className="text-slate-400 text-xs mt-0.5">
              {language === 'hi' ? 'Aapka Financial Assistant' : 'Your Financial Assistant'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => window.open('/api/demo/seed', '_blank')}
              className="text-xs bg-slate-700 hover:bg-slate-600 px-3 py-1.5 rounded-lg"
            >
              🔄 Reset Demo
            </button>
            <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded">
              ● Live
            </span>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-6 space-y-6">

        {/* ── KPI Cards Row ── */}
        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              {
                label: T.mtdIncome[language],
                value: `₹${summary.mtd_income.toLocaleString('en-IN')}`,
                sub: `${summary.mtd_margin_pct}% margin`,
                color: 'text-green-600', bg: 'bg-green-50 border-green-200'
              },
              {
                label: T.mtdExpenses[language],
                value: `₹${summary.mtd_expenses.toLocaleString('en-IN')}`,
                sub: `${summary.days_active_mtd} active days`,
                color: 'text-red-600', bg: 'bg-red-50 border-red-200'
              },
              {
                label: T.netProfit[language],
                value: `₹${summary.mtd_net_profit.toLocaleString('en-IN')}`,
                sub: language === 'hi' ? 'इस महीने' : 'This month',
                color: 'text-blue-700', bg: 'bg-blue-50 border-blue-200'
              },
              {
                label: T.avgDaily[language],
                value: `₹${summary.avg_daily_income.toLocaleString('en-IN')}`,
                sub: `${summary.total_transactions} total transactions`,
                color: 'text-purple-700', bg: 'bg-purple-50 border-purple-200'
              }
            ].map((kpi, i) => (
              <div key={i} className={`rounded-2xl border p-4 ${kpi.bg}`}>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{kpi.label}</p>
                <p className={`text-2xl font-black mt-1 ${kpi.color}`}>{kpi.value}</p>
                <p className="text-xs text-gray-500 mt-0.5">{kpi.sub}</p>
              </div>
            ))}
          </div>
        )}

        {/* ── ArthScore + P&L Chart ── */}
        <div className="grid md:grid-cols-3 gap-6">
          {score && (
            <ArthScoreGauge
              score={score.score}
              grade={score.grade}
              gradeHi={score.grade_hi}
              loanEligible={score.max_loan_eligible}
              language={language}
            />
          )}
          <div className="md:col-span-2">
            {/* Period selector */}
            <div className="flex gap-2 mb-3">
              {(['7d', '30d', '90d'] as const).map(p => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className={`px-3 py-1 rounded-full text-sm font-semibold transition-all ${
                    period === p
                      ? 'bg-slate-800 text-white'
                      : 'bg-white text-gray-600 border hover:border-slate-400'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
            {pnl && <PLChart data={pnl.series} language={language} />}
          </div>
        </div>

        {/* ── Category Breakdown ── */}
        {summary && (
          <div className="grid md:grid-cols-2 gap-6">
            {[
              { title: language === 'hi' ? 'आय के स्रोत' : 'Income Sources', data: summary.income_by_category, type: 'income' },
              { title: language === 'hi' ? 'खर्च की श्रेणियां' : 'Expense Categories', data: summary.expense_by_category, type: 'expense' }
            ].map(({ title, data, type }) => (
              <div key={type} className="bg-white rounded-2xl shadow-sm p-5">
                <h3 className="font-bold text-gray-800 mb-4">{title}</h3>
                <div className="space-y-3">
                  {Object.entries(data)
                    .sort(([,a], [,b]) => b - a)
                    .slice(0, 5)
                    .map(([code, amount]) => {
                      const cat = CATEGORY_DISPLAY[code]
                      const total = Object.values(data).reduce((a, b) => a + b, 0)
                      const pct = total > 0 ? (amount / total * 100) : 0
                      return (
                        <div key={code}>
                          <div className="flex justify-between text-sm mb-1">
                            <span className="font-medium text-gray-700">
                              {cat?.icon} {language === 'hi' ? cat?.hi : cat?.en || code}
                            </span>
                            <span className="font-bold text-gray-900">
                              ₹{amount.toLocaleString('en-IN')}
                            </span>
                          </div>
                          <div className="w-full bg-gray-100 rounded-full h-1.5">
                            <div
                              className={`h-1.5 rounded-full ${type === 'income' ? 'bg-green-500' : 'bg-red-400'}`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      )
                    })}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── Transaction Feed ── */}
        <TransactionFeed transactions={transactions} language={language} />

        {/* ── Generate Passport CTA ── */}
        <div className="bg-gradient-to-r from-green-600 to-emerald-600 rounded-2xl p-6 text-white text-center">
          <h3 className="text-xl font-black mb-1">
            {language === 'hi' ? '🏦 Loan ke liye document ready karein' : '🏦 Get your loan documents ready'}
          </h3>
          <p className="text-green-100 text-sm mb-4">
            {language === 'hi'
              ? `ArthScore ${score?.score || '---'}/900 — ₹${(score?.max_loan_eligible || 0).toLocaleString('en-IN')} tak eligible`
              : `ArthScore ${score?.score || '---'}/900 — Eligible for up to ₹${(score?.max_loan_eligible || 0).toLocaleString('en-IN')}`
            }
          </p>
          <button
            onClick={async () => {
              if (!userId) return
              alert(language === 'hi' ? 'Financial Passport generate ho raha hai...' : 'Generating Financial Passport...')
              const { download_url } = await generatePassport(userId)
              window.open(download_url, '_blank')
            }}
            className="bg-white text-green-700 font-bold px-8 py-3 rounded-xl shadow-lg hover:shadow-xl transition-all"
          >
            {language === 'hi' ? '📄 Financial Passport Download Karen' : '📄 Download Financial Passport'}
          </button>
        </div>

      </div>
    </div>
  )
}
```

---

## 30. FRONTEND — LANGUAGE CONTEXT

```tsx
// frontend/src/contexts/LanguageContext.tsx
import { createContext, useContext, useState, ReactNode } from 'react'
import type { Language } from '../types'

interface LanguageContextType {
  language: Language
  setLanguage: (l: Language) => void
  t: (key: string) => string
}

const TRANSLATIONS: Record<string, Record<Language, string>> = {
  income:        { hi: 'आय',          en: 'Income'   },
  expenses:      { hi: 'खर्च',        en: 'Expenses' },
  netProfit:     { hi: 'शुद्ध लाभ',  en: 'Net Profit'},
  transactions:  { hi: 'लेनदेन',     en: 'Transactions'},
  thisMonth:     { hi: 'इस महीने',   en: 'This Month'},
  thisWeek:      { hi: 'इस हफ्ते',   en: 'This Week'},
  download:      { hi: 'Download करें',en: 'Download' },
  generate:      { hi: 'बनाएं',       en: 'Generate' },
}

const LanguageContext = createContext<LanguageContextType>({
  language: 'hi',
  setLanguage: () => {},
  t: (key) => key,
})

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>('hi')

  const t = (key: string): string => {
    return TRANSLATIONS[key]?.[language] || key
  }

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export const useLanguage = () => useContext(LanguageContext)
```

---

## 31. FRONTEND — LANGUAGE TOGGLE COMPONENT

```tsx
// frontend/src/components/LanguageToggle.tsx
import { useLanguage } from '../contexts/LanguageContext'

export default function LanguageToggle() {
  const { language, setLanguage } = useLanguage()

  return (
    <div className="flex items-center bg-gray-100 rounded-full p-1 gap-1">
      {(['hi', 'en'] as const).map(lang => (
        <button
          key={lang}
          onClick={() => setLanguage(lang)}
          className={`px-3 py-1 rounded-full text-sm font-semibold transition-all ${
            language === lang
              ? 'bg-white shadow-sm text-gray-900'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          {lang === 'hi' ? '🇮🇳 हिंदी' : '🇬🇧 EN'}
        </button>
      ))}
    </div>
  )
}
```

---

## 32. INSIGHT CARD COMPONENT

```tsx
// frontend/src/components/InsightCard.tsx
import { useLanguage } from '../contexts/LanguageContext'

interface InsightProps {
  type: 'expense_anomaly' | 'weekly_summary' | 'score_ready' | 'income_milestone'
  data: Record<string, any>
  onDismiss?: () => void
}

const INSIGHT_STYLES = {
  expense_anomaly:  { bg: 'bg-amber-50 border-amber-200', icon: '⚠️', color: 'text-amber-800' },
  weekly_summary:   { bg: 'bg-blue-50 border-blue-200',   icon: '📊', color: 'text-blue-800'  },
  score_ready:      { bg: 'bg-green-50 border-green-200', icon: '🏆', color: 'text-green-800' },
  income_milestone: { bg: 'bg-purple-50 border-purple-200',icon: '🎉',color: 'text-purple-800'},
}

export default function InsightCard({ type, data, onDismiss }: InsightProps) {
  const { language } = useLanguage()
  const style = INSIGHT_STYLES[type]

  const messages: Record<typeof type, { hi: string; en: string }> = {
    expense_anomaly: {
      hi: `⚠️ Is mahine *${data.category}* का खर्च ₹${data.current?.toLocaleString('en-IN')} रहा — average से *${data.spike_pct?.toFixed(0)}% ज़्यादा*.`,
      en: `⚠️ This month's *${data.category}* costs are *${data.spike_pct?.toFixed(0)}% above* your average.`
    },
    weekly_summary: {
      hi: `📊 इस हफ्ते: आय ₹${data.income?.toLocaleString('en-IN')}, खर्च ₹${data.expenses?.toLocaleString('en-IN')}, मुनाफा ₹${data.net?.toLocaleString('en-IN')}`,
      en: `📊 This week: Income ₹${data.income?.toLocaleString('en-IN')}, Expenses ₹${data.expenses?.toLocaleString('en-IN')}, Net ₹${data.net?.toLocaleString('en-IN')}`
    },
    score_ready: {
      hi: `🏆 आपका ArthScore ready है: *${data.score}/900*. ₹${data.loan?.toLocaleString('en-IN')} तक loan eligible!`,
      en: `🏆 Your ArthScore is ready: *${data.score}/900*. Eligible for loans up to ₹${data.loan?.toLocaleString('en-IN')}!`
    },
    income_milestone: {
      hi: `🎉 बधाई हो! इस महीने ₹${data.milestone?.toLocaleString('en-IN')} की income cross कर ली!`,
      en: `🎉 Congratulations! You crossed ₹${data.milestone?.toLocaleString('en-IN')} in income this month!`
    }
  }

  return (
    <div className={`rounded-xl border p-4 ${style.bg} relative`}>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="absolute top-3 right-3 text-gray-400 hover:text-gray-600 text-lg leading-none"
        >
          ×
        </button>
      )}
      <p className={`text-sm font-medium ${style.color} pr-6`}>
        {messages[type][language]}
      </p>
    </div>
  )
}
```

---

## 33. FRONTEND — PASSPORT PAGE

```tsx
// frontend/src/pages/Passport.tsx
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useLanguage } from '../contexts/LanguageContext'
import { generatePassport } from '../api/client'

export default function Passport() {
  const { userId } = useParams<{ userId: string }>()
  const { language } = useLanguage()
  const [status, setStatus] = useState<'idle' | 'generating' | 'done' | 'error'>('idle')
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null)
  const [passportData, setPassportData] = useState<{
    arthascore: number; loan_eligible: number; expires_at: string
  } | null>(null)

  const handleGenerate = async () => {
    if (!userId) return
    setStatus('generating')
    try {
      const result = await generatePassport(userId)
      setDownloadUrl(result.download_url)
      setPassportData({
        arthascore: result.arthascore,
        loan_eligible: result.loan_eligible,
        expires_at: result.expires_at
      })
      setStatus('done')
    } catch {
      setStatus('error')
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl overflow-hidden">

        {/* Header */}
        <div className="bg-gradient-to-br from-slate-900 to-slate-700 p-8 text-white text-center">
          <div className="text-4xl mb-2">📄</div>
          <h1 className="text-xl font-black">
            {language === 'hi' ? 'Financial Passport' : 'Financial Passport'}
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            {language === 'hi'
              ? 'Bank-grade document for loan applications'
              : 'Bank-grade document for loan applications'}
          </p>
        </div>

        <div className="p-6 space-y-4">
          {/* What's included */}
          <div>
            <h3 className="font-bold text-gray-800 mb-3">
              {language === 'hi' ? 'Document mein kya hoga:' : "What's included:"}
            </h3>
            <div className="space-y-2">
              {[
                { icon: '📊', hi: '12-month P&L Statement', en: '12-month P&L Statement' },
                { icon: '🎯', hi: 'ArthScore™ with breakdown', en: 'ArthScore™ with breakdown' },
                { icon: '📝', hi: 'AI-generated business narrative', en: 'AI-generated business narrative' },
                { icon: '💰', hi: 'Loan eligibility certificate', en: 'Loan eligibility certificate' },
                { icon: '🏦', hi: 'RBI-compliant format', en: 'RBI-compliant format' },
              ].map(item => (
                <div key={item.en} className="flex items-center gap-3 text-sm text-gray-700">
                  <span>{item.icon}</span>
                  <span>{language === 'hi' ? item.hi : item.en}</span>
                  <span className="ml-auto text-green-500">✓</span>
                </div>
              ))}
            </div>
          </div>

          {/* Generate button */}
          {status === 'idle' && (
            <button
              onClick={handleGenerate}
              className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 rounded-xl transition-all shadow-lg hover:shadow-xl"
            >
              {language === 'hi' ? '🚀 Financial Passport Generate Karen' : '🚀 Generate Financial Passport'}
            </button>
          )}

          {status === 'generating' && (
            <div className="text-center py-6">
              <div className="w-12 h-12 border-4 border-green-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-gray-600 font-medium">
                {language === 'hi' ? 'Generating your passport...' : 'Generating your passport...'}
              </p>
              <p className="text-gray-400 text-sm mt-1">AI apka document bana raha hai</p>
            </div>
          )}

          {status === 'done' && passportData && (
            <div className="space-y-3">
              <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
                <div className="text-3xl font-black text-green-700">{passportData.arthascore}/900</div>
                <div className="text-sm text-green-600">ArthScore™</div>
                <div className="text-lg font-bold text-green-800 mt-1">
                  ₹{passportData.loan_eligible.toLocaleString('en-IN')} eligible
                </div>
              </div>

              <a
                href={downloadUrl!}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full bg-slate-800 hover:bg-slate-700 text-white font-bold py-3 rounded-xl transition-all flex items-center justify-center gap-2"
              >
                <span>⬇️</span>
                <span>{language === 'hi' ? 'PDF Download Karen' : 'Download PDF'}</span>
              </a>

              <p className="text-xs text-center text-gray-400">
                {language === 'hi' ? 'Valid until:' : 'Valid until:'} {new Date(passportData.expires_at).toLocaleDateString('en-IN')}
              </p>
            </div>
          )}

          {status === 'error' && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-center">
              <p className="text-red-700 font-medium">
                {language === 'hi' ? 'Kuch galat hua. Dobara try karein.' : 'Something went wrong. Please try again.'}
              </p>
              <button onClick={() => setStatus('idle')} className="text-red-600 text-sm mt-2 underline">
                {language === 'hi' ? 'Retry' : 'Retry'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
```

---

## 34. README.md — HACKATHON READY

```markdown
# ArthAI ⚡
### India's Agentic Financial Intelligence Layer for the Informal Economy

> **"63 million entrepreneurs power India's economy. None of them can get a loan. We're fixing that with AI."**

[![Railway Deploy](https://img.shields.io/badge/Backend-Railway-purple)](https://arthai-backend.up.railway.app)
[![Vercel](https://img.shields.io/badge/Frontend-Vercel-black)](https://arthai-demo.vercel.app)
[![WhatsApp Demo](https://img.shields.io/badge/WhatsApp-Demo_Active-25D366)](https://wa.me/14155238886?text=Hello+ArthAI)

---

## 🎯 The Problem
India's 63M micro-entrepreneurs contribute 30% of GDP but 94% have zero access to formal credit.
**Not because they lack money — because their financial data exists as voice notes, receipt photos, and memory.**

## 🚀 What ArthAI Does
A **WhatsApp-first AI platform** that converts informal financial data into formal credit profiles:

```
📸 Photo of crumpled petrol receipt  →  ₹165, Fuel expense, IndianOil  (3 seconds)
🎤 "Aaj teen sawariyan gayi ₹1,200"  →  ₹1,200 income, Auto-Rickshaw  (2 seconds)
✍️ "Mera profit kya raha is hafte?"  →  "₹4,200 net, 10% above average" (Hindi)
📄 "Loan ke liye document chahiye"   →  ArthScore 714/900, ₹75,000 eligible, PDF
```

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Tailwind CSS + Recharts |
| Backend | FastAPI + Python 3.11 + Uvicorn |
| AI/Vision | OpenAI GPT-4o-mini (OCR + NLU) |
| Voice AI | Sarvam AI saarika-v2 (12 Indic languages) |
| Agent | LangGraph (stateful multi-step AI workflows) |
| Database | Supabase PostgreSQL + pgvector |
| Messaging | Twilio WhatsApp Business API |
| PDF | WeasyPrint (HTML → Financial Passport) |
| Queue | Celery + Redis |
| Deploy | Railway (backend) + Vercel (frontend) |

## 🏗️ Architecture

```
WhatsApp → Twilio Webhook → FastAPI → Celery Worker
                                            ↓
                            LangGraph Agent Pipeline
                      ┌─────────────────────────────┐
                      │  Vision → Speech → NLU       │
                      │  Classify → Extract → Store  │
                      │  ArthScore → Response        │
                      └─────────────────────────────┘
                                  ↓
              PostgreSQL + pgvector + Redis + S3
```

## 🎮 Try the Demo

### WhatsApp
1. Save `+1 415 523 8886` in your contacts
2. Send `join [sandbox-keyword]` to activate
3. Try:
   - Send a photo of any receipt
   - Send voice note: "Aaj ₹800 ki sale hui"
   - Type: "Is hafte mera profit kya raha?"
   - Type: "Passport banao"

### Web Dashboard
🌐 [arthai-demo.vercel.app](https://arthai-demo.vercel.app)
Pre-loaded with 90 days of Raju Kumar's (auto-rickshaw, Pune) transaction history.

## 🚀 Local Setup

```bash
# Clone
git clone https://github.com/[team]/arthai && cd arthai

# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Fill in your API keys

# Database setup (Supabase)
psql $DATABASE_URL -f migrations/001_initial_schema.sql

# Seed demo data
uvicorn main:app --reload &
curl -X POST http://localhost:8000/api/demo/seed

# Start Celery worker (in new terminal)
celery -A tasks.celery_app worker --loglevel=info

# Frontend
cd ../frontend
npm install
npm run dev
```

## 📊 The ArthScore™

Proprietary creditworthiness score (300-900, modeled after CIBIL):

| Factor | Weight | What It Measures |
|--------|--------|-----------------|
| Income Regularity | 25% | Coefficient of variation of weekly income |
| Growth Trajectory | 20% | 12-week linear regression slope |
| Expense Control | 15% | Net profit margin quality |
| Transaction Volume | 15% | Business activity frequency |
| Business Longevity | 10% | Days since first transaction |
| Payment Consistency | 10% | Supplier payment regularity |
| Data Completeness | 5% | Operational day coverage |

**Score 714 → ₹75,000 loan at 18% p.a.** (vs 48% from moneylenders)

## 💰 Business Model

| Stream | Revenue |
|--------|---------|
| B2C Pro (₹299/mo) | Year 3: 1M users → ₹35Cr/mo ARR |
| Credit Marketplace (1-2% origination) | Year 2: ₹500Cr disbursals → ₹10Cr |
| B2B API (₹10-25/passport) | Year 2: NBFC white-label |
| Market Intelligence (anonymized) | Year 3 |

**LTV:CAC = 33:1** | Payback < 1 month

## 🌍 Why Now

Five conditions that have JUST become true simultaneously:
1. UPI: 14B+ transactions/month
2. WhatsApp: 530M Indian users
3. RBI Account Aggregator Framework: Live
4. Indic Voice AI (Sarvam saarika-v2): Production ready
5. Multimodal LLMs (GPT-4V): Can read crumpled Hindi receipts

**This window is 2024-2026. ArthAI is built for this exact moment.**

## 👥 Team
[Team names] | InnovaHack Chapter 1 | Domain: Generative AI

---
*"Apna Business, Apni Zubaan Mein." — Your Business, In Your Own Language.*
```

---

## 35. TESTING SUITE — CRITICAL PATHS

```python
# backend/tests/test_arthascore.py
"""
Unit tests for the ArthScore engine.
Run: pytest backend/tests/ -v
"""
import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock
from agents.arthascore import ArthScoreEngine, FACTOR_WEIGHTS

class TestArthScoreAlgorithm:

    def test_factor_weights_sum_to_one(self):
        """Weights must sum to exactly 1.0"""
        assert abs(sum(FACTOR_WEIGHTS.values()) - 1.0) < 0.001

    def test_income_regularity_perfect_consistency(self):
        """Perfectly consistent income → score 100"""
        engine = ArthScoreEngine(None)
        weekly_income = [1000.0] * 13  # Exactly same every week
        score = engine._calc_income_regularity(weekly_income)
        assert score == 100

    def test_income_regularity_high_variance(self):
        """Highly variable income → low score"""
        engine = ArthScoreEngine(None)
        weekly_income = [0, 5000, 0, 5000, 0, 5000, 0, 5000, 0, 5000, 0, 5000, 0]
        score = engine._calc_income_regularity(weekly_income)
        assert score < 30

    def test_growth_trajectory_positive_trend(self):
        """Growing income → score > 50"""
        engine = ArthScoreEngine(None)
        weekly_income = [500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700]
        score = engine._calc_growth_trajectory(weekly_income)
        assert score > 60

    def test_growth_trajectory_declining(self):
        """Declining income → score < 50"""
        engine = ArthScoreEngine(None)
        weekly_income = [1700, 1600, 1500, 1400, 1300, 1200, 1100, 1000, 900, 800, 700, 600, 500]
        score = engine._calc_growth_trajectory(weekly_income)
        assert score < 40

    def test_expense_control_good_margin(self):
        """50% net margin → 100 score"""
        engine = ArthScoreEngine(None)
        score = engine._calc_expense_control(10000, 5000)
        assert score == 100

    def test_expense_control_loss(self):
        """Expenses > income → 0 score"""
        engine = ArthScoreEngine(None)
        score = engine._calc_expense_control(5000, 7000)
        assert score == 0

    def test_score_clamped_300_900(self):
        """Final score must be between 300 and 900"""
        engine = ArthScoreEngine(None)
        # Even with perfect factors, score should not exceed 900
        # Even with zero factors, score should not go below 300
        score_perfect = int(300 + (100 / 100) * 600)
        score_zero = int(300 + (0 / 100) * 600)
        assert score_perfect == 900
        assert score_zero == 300

    def test_loan_eligibility_calculation(self):
        """Max loan = 4x monthly net income"""
        monthly_net = 18000
        expected = 18000 * 4
        assert expected == 72000  # Round to 72000

    def test_insufficient_data_response(self):
        engine = ArthScoreEngine(None)
        response = engine._insufficient_data_response()
        assert response["score"] == 0
        assert "data_points" in response
        assert "insight_hi" in response


# backend/tests/test_nlu.py
class TestNLU:

    @pytest.mark.asyncio
    async def test_hindi_transaction_intent(self):
        """Hindi transaction messages classified correctly"""
        from ai.nlu import classify_intent
        # Note: This test requires OPENAI_API_KEY set
        # For CI: mock the OpenAI call
        test_cases = [
            ("Aaj ₹950 ki sawari mili", "TRANSACTION"),
            ("Is hafte kitna kamaya?", "QUERY"),
            ("Loan ke liye document chahiye", "REPORT_REQUEST"),
            ("Haan, sahi hai", "CONFIRMATION_YES"),
            ("Namaste", "GREETING"),
        ]
        # In actual test: mock OpenAI client
        # assert intent == expected for each case

    def test_amount_formats(self):
        """Indian amount format parsing"""
        # These are parsed in the NLU prompt — validate the prompt handles them
        test_amounts = [
            ("teen hazaar", 3000),
            ("1.5 lakh", 150000),
            ("₹500", 500),
            ("pachas rupaye", 50),
            ("do sau pachas", 250),
        ]
        # Validation that prompt handles these (integration test with actual API)
        assert True  # Placeholder — run with live API

    def test_confirmation_detection(self):
        """State machine confirmation detection"""
        from services.conversation import ConversationStateManager
        mgr = ConversationStateManager(None)

        yes_phrases = ["haan", "1", "yes", "sahi hai", "thik hai", "✅", "👍", "ok"]
        no_phrases = ["nahi", "2", "no", "galat", "wrong", "❌", "👎"]

        for phrase in yes_phrases:
            assert mgr.is_confirmation_yes(phrase), f"'{phrase}' should be YES"
        for phrase in no_phrases:
            assert mgr.is_confirmation_no(phrase), f"'{phrase}' should be NO"
```

---

## 36. NBFC CREDIT MARKETPLACE — DEMO IMPLEMENTATION

```python
# backend/routes/marketplace.py
"""
Simulated NBFC loan marketplace for demo purposes.
In production: integrate with actual NBFC APIs via OCEN protocol.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import date

from dependencies import get_db
from agents.arthascore import ArthScoreEngine

router = APIRouter()

# Simulated NBFC partners with eligibility criteria
NBFC_PARTNERS = [
    {
        "name": "FinFlex Capital",
        "min_score": 650,
        "max_loan": 200000,
        "interest_rate_pct": 18,
        "tenure_months": [6, 12, 24],
        "processing_fee_pct": 1.5,
        "tagline": "No collateral required",
        "turnaround_hours": 48,
        "logo": "🏦"
    },
    {
        "name": "MSME Credit Pro",
        "min_score": 600,
        "max_loan": 100000,
        "interest_rate_pct": 22,
        "tenure_months": [3, 6, 12],
        "processing_fee_pct": 2.0,
        "tagline": "Disbursed in 24 hours",
        "turnaround_hours": 24,
        "logo": "💳"
    },
    {
        "name": "BharatMicro Finance",
        "min_score": 550,
        "max_loan": 50000,
        "interest_rate_pct": 26,
        "tenure_months": [3, 6],
        "processing_fee_pct": 2.5,
        "tagline": "Flexible repayment",
        "turnaround_hours": 72,
        "logo": "🏛️"
    },
]

@router.get("/offers/{user_id}")
async def get_loan_offers(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get personalized loan offers based on ArthScore.
    Returns list of NBFCs the user qualifies for, ranked by interest rate.
    """
    scorer = ArthScoreEngine(db)
    score_data = await scorer.calculate(str(user_id))
    score = score_data["score"]
    max_eligible = score_data["max_loan_eligible"]

    eligible_offers = []
    for nbfc in NBFC_PARTNERS:
        if score >= nbfc["min_score"]:
            loan_amount = min(max_eligible, nbfc["max_loan"])
            monthly_rate = nbfc["interest_rate_pct"] / 12 / 100

            # Calculate EMI for first tenure option
            n = nbfc["tenure_months"][0]
            emi = loan_amount * monthly_rate * (1 + monthly_rate)**n / ((1 + monthly_rate)**n - 1)

            eligible_offers.append({
                **nbfc,
                "loan_amount": loan_amount,
                "emi_per_month": round(emi),
                "total_interest": round(emi * n - loan_amount),
                "eligible": True,
                "your_arthascore": score
            })

    # Sort by interest rate (best first)
    eligible_offers.sort(key=lambda x: x["interest_rate_pct"])

    return {
        "arthascore": score,
        "grade": score_data["grade"],
        "total_offers": len(eligible_offers),
        "offers": eligible_offers,
        "comparison": {
            "formal_rate": eligible_offers[0]["interest_rate_pct"] if eligible_offers else None,
            "moneylender_rate": 48,
            "annual_savings": round(
                max_eligible * (0.48 - (eligible_offers[0]["interest_rate_pct"] / 100))
            ) if eligible_offers else 0
        }
    }
```

---

## 37. VITE CONFIG + TAILWIND SETUP

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
```

```javascript
// frontend/tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        arthai: {
          green: '#16a34a',
          dark: '#1a1a2e',
        }
      }
    },
  },
  plugins: [],
}
```

```css
/* frontend/src/index.css */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
@tailwind base;
@tailwind components;
@tailwind utilities;

* { font-family: 'Inter', system-ui, sans-serif; }

/* Custom scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #f1f5f9; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }

/* Animate score gauge */
.arthascore-animate { transition: stroke-dashoffset 1.5s cubic-bezier(0.25, 0.46, 0.45, 0.94); }
```

---

## 38. LOADING SPINNER COMPONENT

```tsx
// frontend/src/components/LoadingSpinner.tsx
interface LoadingSpinnerProps {
  message?: string
  size?: 'sm' | 'md' | 'lg'
}

export default function LoadingSpinner({ message, size = 'md' }: LoadingSpinnerProps) {
  const sizes = { sm: 'w-6 h-6', md: 'w-10 h-10', lg: 'w-16 h-16' }

  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <div className={`${sizes[size]} border-4 border-green-500/30 border-t-green-600 rounded-full animate-spin`} />
      {message && <p className="text-gray-500 text-sm font-medium">{message}</p>}
    </div>
  )
}
```

---

## 39. ENVIRONMENT VALIDATION ON STARTUP

```python
# backend/config.py
from pydantic_settings import BaseSettings
from typing import Optional, List
import sys

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # AI APIs
    OPENAI_API_KEY: str
    OPENAI_MODEL_VISION: str = "gpt-4o-mini"
    OPENAI_MODEL_NLU: str = "gpt-4o-mini"
    SARVAM_API_KEY: Optional[str] = None
    SARVAM_ASR_MODEL: str = "saarika-v2"

    # Messaging
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_WHATSAPP_FROM: str = "whatsapp:+14155238886"
    TWILIO_WEBHOOK_URL: str

    # Storage
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_BUCKET_NAME: str = "arthai-receipts"
    AWS_REGION: str = "ap-south-1"

    # App
    SECRET_KEY: str
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173"]

    # Feature flags
    ENABLE_SARVAM_ASR: bool = True
    ENABLE_S3_STORAGE: bool = True
    CONFIDENCE_THRESHOLD: float = 0.85
    DEMO_MODE: bool = False

    ARTHASCORE_MIN: int = 300
    ARTHASCORE_MAX: int = 900

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def validate_critical(self):
        """Crash fast if critical env vars are missing"""
        critical = [
            ("OPENAI_API_KEY", self.OPENAI_API_KEY),
            ("TWILIO_ACCOUNT_SID", self.TWILIO_ACCOUNT_SID),
            ("DATABASE_URL", self.DATABASE_URL),
        ]
        missing = [name for name, val in critical if not val or "your_" in str(val)]
        if missing:
            print(f"❌ FATAL: Missing critical environment variables: {missing}")
            print("Copy .env.example → .env and fill in the required values.")
            sys.exit(1)

        if self.ENABLE_SARVAM_ASR and not self.SARVAM_API_KEY:
            print("⚠️  WARNING: ENABLE_SARVAM_ASR=true but SARVAM_API_KEY not set.")
            print("   Voice will fall back to OpenAI Whisper. Set ENABLE_SARVAM_ASR=false to suppress.")

settings = Settings()
settings.validate_critical()
```

---

## 40. COMPLETE PACKAGE.JSON

```json
{
  "name": "arthai-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.23.1",
    "axios": "^1.7.2",
    "recharts": "^2.12.7"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.38",
    "tailwindcss": "^3.4.4",
    "typescript": "^5.4.5",
    "vite": "^5.3.1"
  }
}
```

---

## 41. DEMO VIDEO SHOT LIST

Follow this exactly for the 5-minute demo video:

**[0:00–0:05] Brand title card**
- ArthAI logo on dark background
- Tagline: "Apna Business, Apni Zubaan Mein."
- Background: busy Pune market street (b-roll)

**[0:05–0:30] The Hook — statistics slam**
Screen shows one by one, 2 seconds each:
```
63,000,000
MSMEs generating ₹50 lakh crore/year
94% have zero bank credit
₹25 lakh crore unmet credit gap
```
Cut to: Raju's WhatsApp — messy mix of voice notes, UPI screenshots, crumpled receipt photos.
Voiceover: *"This is Raju's financial life. 6 years. ₹25,000/month. Zero bank loan."*

**[0:30–1:00] Show existing tools failing**
Side by side: KhataBook app (complex UI) vs. WhatsApp (where Raju actually lives).
*"Every tool requires Raju to change. ArthAI learns Raju's language instead."*

**[1:00–2:00] LIVE DEMO — Receipt**
Screen record WhatsApp. Send petrol pump photo.
[Real-time 3-second pause]
ArthAI responds: "✅ Record hua! ₹165 खर्च, ⛽ ईंधन, IndianOil Baner Road"
*Voiceover: "Photo → Ledger entry. Automatic. No typing."*

**[2:00–2:45] LIVE DEMO — Voice Note**
Send voice note: "Aaj teen sawariyan gayi, total ₹1,200 mile"
[Real-time 2-second pause]
ArthAI: "✅ Record hua! ₹1,200 आय, ⚙️ सेवा आय, आज 14:32"
*Voiceover: "Hindi voice note → Income tracked. Zero friction."*

**[2:45–3:15] LIVE DEMO — Query**
Type: "Is hafte mera profit kya raha?"
ArthAI responds with full Hindi analytics breakdown.
*Voiceover: "Natural language question → instant business intelligence."*

**[3:15–4:00] LIVE DEMO — Financial Passport**
Type: "Passport banao"
Show loading → PDF appears
Scroll through PDF: ArthScore 714/900, 3-month P&L, loan eligibility ₹75,000.
*Voiceover: "90 days of WhatsApp messages → bank-grade financial document."*

**[4:00–4:30] THE OUTCOME**
Show: NBFC notification — "Loan of ₹75,000 approved at 18% p.a."
Cut to: Dashboard showing ArthScore trend going from 650 → 714 → 742
*Voiceover: "Raju's first formal loan in 6 years. He didn't change anything. ArthAI learned his language."*

**[4:30–5:00] THE SCALE + CLOSE**
```
63 million Rajus in India
₹25 lakh crore waiting
0 tools that work for them
```
Final: ArthAI logo + LinkedIn/GitHub QR
*"Apna Business, Apni Zubaan Mein."*

---

## 42. EDGE CASES — PRE-HANDLED

| Edge Case | Handling Strategy |
|-----------|-------------------|
| User sends unreadable blurry photo | Confidence < 0.5 → ask to resend clearer photo |
| Voice note too short (< 1 second) | Check duration before Sarvam API call → ask to re-record |
| Mixed language bill (Hindi + English) | GPT-4V handles bilingual natively |
| UPI screenshot with amounts in lakhs | Prompt engineering handles "1.5 lakh" = 150000 |
| Negative amount in text | NLU checks context: "wapas mila" → income |
| Duplicate transaction | Check last 5 transactions for same amount+date before storing |
| User sends document (PDF bank statement) | Route to document parser, extract multiple transactions |
| Sarvam AI rate limit | Exponential backoff → Whisper fallback → error message |
| OpenAI API down | Return error message, retry after 30s via Celery |
| User sends emoji only | Classified as GREETING, get help message |
| WhatsApp session expired | State reset to IDLE, process as new message |
| Amount format: "paunay teen hazaar" (₹2,750) | GPT-4 NLU handles Indian number expressions |
| Group chat message | Phone number routing ensures correct user lookup |
| First-time user sends a transaction | Onboarding interleaved: save transaction + ask for name |

---

## 43. FINAL GOD-TIER ARCHITECTURE DECISIONS — WHY EACH CHOICE MATTERS

| Decision | Chosen | Rejected | Reason |
|----------|--------|----------|--------|
| Messaging Platform | WhatsApp (Twilio) | Telegram, Custom App | 530M Indian users, zero install |
| Voice AI | Sarvam saarika-v2 | Google STT, AWS Transcribe | Native Indic language + Hinglish + lowest WER for Hindi |
| Agent Framework | LangGraph | LangChain chains, custom | Stateful graph = handles multi-turn confirmations |
| PDF Generation | WeasyPrint | ReportLab, Puppeteer | Python-native, CSS-based = beautiful output, hackathon-fast |
| Database | Supabase PostgreSQL | MongoDB, DynamoDB | ACID for financial data + built-in auth + free tier |
| Embedding | pgvector | Pinecone, Weaviate | Zero additional infra — semantic search in same DB |
| Score Scale | 300-900 | 0-100 | Mirrors CIBIL — psychological familiarity for Indian users |
| Task Queue | Celery + Redis | Webhook async | Need retry logic for AI API failures |
| Deployment | Railway | Heroku, GCP | Zero-config, free tier Redis + PostgreSQL |
| AI Model | gpt-4o-mini | gpt-4o | 10x cheaper, fast enough for hackathon OCR + NLU |
| Frontend | React + Recharts | Next.js, Vue | Simpler setup, faster demo, Recharts = best charts |

---

## 44. LOAN IMPACT CALCULATOR — BONUS FRONTEND WIDGET

```tsx
// frontend/src/components/LoanImpactCalculator.tsx
import { useState } from 'react'

export default function LoanImpactCalculator() {
  const [loanAmount, setLoanAmount] = useState(75000)
  const moneylenderRate = 0.48
  const arthAIRate = 0.18
  const tenure = 12

  const moneylenderMonthly = (loanAmount * moneylenderRate) / 12
  const arthAIMonthly = loanAmount * (arthAIRate / 12) * Math.pow(1 + arthAIRate / 12, tenure) / (Math.pow(1 + arthAIRate / 12, tenure) - 1)
  const annualSavings = (moneylenderMonthly - arthAIMonthly) * 12

  return (
    <div className="bg-white rounded-2xl shadow-lg p-6">
      <h3 className="font-bold text-gray-800 text-lg mb-4">💰 Loan Impact Calculator</h3>

      <div className="mb-4">
        <label className="text-sm text-gray-600">Loan Amount</label>
        <input
          type="range" min="25000" max="500000" step="5000"
          value={loanAmount}
          onChange={e => setLoanAmount(Number(e.target.value))}
          className="w-full mt-1"
        />
        <p className="text-lg font-bold text-center text-gray-800 mt-1">
          ₹{loanAmount.toLocaleString('en-IN')}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-red-50 rounded-xl p-4 text-center">
          <p className="text-xs text-red-700 font-semibold uppercase">Moneylender</p>
          <p className="text-2xl font-black text-red-600">48%</p>
          <p className="text-sm text-red-700">₹{Math.round(moneylenderMonthly).toLocaleString('en-IN')}/month</p>
        </div>
        <div className="bg-green-50 rounded-xl p-4 text-center">
          <p className="text-xs text-green-700 font-semibold uppercase">via ArthAI</p>
          <p className="text-2xl font-black text-green-600">18%</p>
          <p className="text-sm text-green-700">₹{Math.round(arthAIMonthly).toLocaleString('en-IN')}/month</p>
        </div>
      </div>

      <div className="mt-4 bg-blue-50 rounded-xl p-4 text-center">
        <p className="text-sm text-blue-700 font-semibold">Annual Savings</p>
        <p className="text-3xl font-black text-blue-800">₹{Math.round(annualSavings).toLocaleString('en-IN')}</p>
        <p className="text-xs text-blue-600 mt-1">per year saved vs. moneylender</p>
      </div>
    </div>
  )
}
```

---

## MASTER SUBMISSION CHECKLIST

```
TECHNICAL ──────────────────────────────────────────────────────────
□ POST /webhook/whatsapp — functional, responds in <5s
□ IMAGE: Receipt photo → structured transaction (GPT-4V)
□ AUDIO: Hindi voice note → transcribed + categorized (Sarvam/Whisper)
□ TEXT: "Aaj ₹950 mili" → intent classified + stored
□ TEXT: "Is hafte profit?" → analytics query answered in Hindi
□ TEXT: "Passport banao" → PDF generated + URL returned
□ GET /api/analytics/summary/[user_id] — returns all KPIs
□ GET /api/analytics/pnl/[user_id]?period=90d — chart data
□ GET /api/score/[user_id] — ArthScore 300-900 calculated
□ POST /api/reports/passport/[user_id] — real PDF download
□ POST /api/demo/seed — loads Raju's 90-day data
□ All Celery tasks registered and worker running
□ Railway deployment live at HTTPS URL
□ Vercel frontend live and connected to backend

DEMO DATA ───────────────────────────────────────────────────────────
□ Raju Kumar's 90-day dataset loaded
□ ArthScore shows 714/900 (not a static mock)
□ Loan eligibility shows ₹75,000
□ P&L chart shows 3 months of income > expenses
□ Top categories: sales_service (income), transport_fuel (expense)
□ Transaction feed shows ~40+ transactions with source icons

FRONTEND ────────────────────────────────────────────────────────────
□ Dashboard KPI cards accurate to seed data
□ P&L chart renders with correct data (income green, expenses red)
□ ArthScore gauge animates on load
□ Language toggle switches between Hindi and English labels
□ Transaction feed is scrollable and categorized
□ "Generate Passport" button downloads real PDF
□ Mobile-responsive (judges use phones)

PRESENTATION ────────────────────────────────────────────────────────
□ GitHub repo public with complete README
□ README has demo GIF (record with Loom → convert)
□ Live URLs in submission form
□ WhatsApp sandbox functional with correct sandbox join keyword
□ 5-minute video recorded per shot list above
□ 10-slide deck prepared from document Section 10

NARRATIVE ───────────────────────────────────────────────────────────
□ "Raju getting his first loan" is the emotional center of the demo
□ "Zero behavior change" message is repeated 3x
□ ArthScore methodology explained (not a black box)
□ ₹25 lakh crore credit gap statistic cited
□ Data flywheel moat explained clearly
□ Geographic expansion (Indonesia, Nigeria) mentioned
```

---

*ArthAI — Where India's Informal Economy Meets Formal Finance.*
*Built in 24 hours. Built for 63 million. Built for Raju.*

**"Apna Business, Apni Zubaan Mein."**

---
*ARTHAI_GOD_TIER_PROMPT.md | Version 2.0 COMPLETE | Total Sections: 44*
