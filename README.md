# ArthAI 🚀
### India's Agentic Financial Intelligence Layer for Micro-Businesses

ArthAI is a state-of-the-art agentic financial assistant designed for India's 63+ million MSMEs and micro-merchants (kirana stores, auto-drivers, street vendors). It allows users to track their business completely via **WhatsApp voice notes, text messages, and receipt images**, and automatically compiles this raw data into a structured financial ledger, calculates a non-traditional **ArthScore™**, and generates an RBI-compliant **Financial Passport** PDF to unlock formal bank credit.

---

## 🏗️ Architecture Overview

The system is structured as two cleanly separated codebases:

```
├── backend/                  # FastAPI Webhook, Celery Workers, LangGraph Agent, Database
│   ├── agents/               # LangGraph Agent nodes & conditional routing graph
│   ├── ai/                   # AI engines: OCR (Vision), ASR (Speech), NLU (Query/Intent parsing)
│   ├── models/               # SQLAlchemy models (PostgreSQL compatibility)
│   ├── routes/               # API endpoints & Twilio WhatsApp webhook router
│   ├── services/             # Analytics, Storage, Twilio WhatsApp, LangGraph onboarding State Machine
│   └── tasks/                # Celery and Redis asynchronous worker configuration
│
└── frontend/                 # React 18 SPA + Vite + TypeScript + Vanilla CSS (Rich Aesthetics)
    ├── src/components/       # Premium Interactive UI: ArthScore Gauge, Loan Simulator, P&L Chart
    ├── src/pages/            # Dashboard, Ledger List, Passport PDF Generator, and Demo Sandbox
    └── src/api/              # Client services for API interaction
```

---

## ⚡ Quick Start: Running Locally

### 1. Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and configure your environment variables:
   ```bash
   cp .env.example .env
   ```
3. Run the FastAPI development server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
4. Run the Celery background worker (requires Redis):
   ```bash
   celery -A tasks.celery_app.celery_app worker --loglevel=info
   ```

### 2. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the Vite development server:
   ```bash
   npm run dev
   ```
4. Build the production app:
   ```bash
   npm run build
   ```

---

## ☁️ Cloud Deployment Plan

To ensure maximum scalability, low latency, and zero-cost hosting, the deployment leverages **Cloudflare Pages** (frontend), **Hugging Face Spaces** (backend), and **Neon Tech** (database).

```
┌──────────────────────┐       ┌────────────────────────┐       ┌─────────────────┐
│       Frontend       │ ────> │        Backend         │ ────> │    Database     │
│ Cloudflare Pages CDN │       │  Hugging Face Spaces   │       │ Neon Tech (Post)│
└──────────────────────┘       └────────────────────────┘       └─────────────────┘
                                           │
                                           ▼
                                 ┌───────────────────┐
                                 │   Object Storage  │
                                 │  Supabase Bucket  │
                                 └───────────────────┘
```

Detailed setup, credentials, secrets configuration, and deployment commands are fully documented in the backend folder:
🔗 **[backend/deployment_plan.md](file:///home/elliot/Project/backend/deployment_plan.md)**

---

## 🎯 Validation Checklists

Before declaring the deployment live, verify the following checks:
*   [x] Run `npm run build` inside `frontend/` to confirm zero bundler/typescript errors.
*   [x] Perform `python3 -m compileall backend` to confirm zero syntax errors.
*   [x] Ensure `DATABASE_URL` resolves to Neon Tech Postgres without connection failures.
*   [x] Verify file uploads in `storage.py` route seamlessly to the Supabase Public bucket.
*   [x] Validate that Twilio sends webhooks to your server and receives immediate `<Response></Response>` within 200ms.
