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

To ensure maximum scalability, low latency, and zero-cost cold starts, the deployment leverages **Cloudflare Pages**, **Neon Tech**, and **Supabase**.

```
┌─────────────────┐       ┌────────────────────────┐       ┌─────────────────┐
│     Frontend    │ ────> │        Backend         │ ────> │    Database     │
│ Cloudflare Pages│       │ Supabase/Render/Tunnel │       │ Neon Tech (Post)│
└─────────────────┘       └────────────────────────┘       └─────────────────┘
         │                            │                             │
         ▼                            ▼                             ▼
   Hosted React v18             FastAPI App Engine            Serverless Postgres
                                      │
                                      ▼
                             ┌─────────────────┐
                             │  File Storage   │
                             │ Supabase Bucket │
                             └─────────────────┘
```

---

### Step 1: Database Setup on Neon Tech (PostgreSQL)

Neon provides a serverless PostgreSQL database with autoscaling and branching capabilities.

1. **Sign Up & Create Project**:
   - Go to [neon.tech](https://neon.tech/) and create a free account.
   - Click **Create Project**, name it `arthai`, and select your preferred region (e.g., `ap-south-1` for lowest latency in India).
2. **Obtain Connection String**:
   - Copy the Connection String from your Neon dashboard dashboard (ensure transaction pooling is enabled if running serverless).
   - The format will look like:
     ```env
     DATABASE_URL="postgresql://[user]:[password]@[ep-host].ap-south-1.aws.neon.tech/neondb?sslmode=require"
     ```
3. **Execute Migrations**:
   - Set this URL in your backend environment variables and run your Alembic/SQLAlchemy initialization script:
     ```bash
     cd backend
     python -c "from database import engine, Base; Base.metadata.create_all(bind=engine)"
     ```

---

### Step 2: Storage & Authentication Setup on Supabase

We use Supabase as the backend engine for file uploads (receipts, audio recordings, statement PDFs) and secure authentication.

1. **Create Supabase Project**:
   - Log in to the [Supabase Console](https://supabase.com/).
   - Click **New Project**, select your organization, name the project `arthai`, and set your database password.
2. **Configure Storage Buckets**:
   - Navigate to the **Storage** tab on the left sidebar.
   - Click **New Bucket**, name it `arthai-media`.
   - Set the bucket to **Public** (so Twilio and the React frontend can fetch uploaded receipts and statement PDFs directly).
   - Set up bucket policies to allow authenticated uploads or anonymous uploads for webhook storage.
3. **Configure AWS S3-Compatibility (Optional)**:
   - Supabase storage supports S3-compatible endpoints. Retrieve your **S3 Connection parameters** from:
     `Project Settings -> Storage -> S3 Connection`.
   - Update your backend `.env` variables:
     ```env
     AWS_ACCESS_KEY_ID="your-supabase-s3-access-key"
     AWS_SECRET_ACCESS_KEY="your-supabase-s3-secret-key"
     AWS_STORAGE_BUCKET_NAME="arthai-media"
     AWS_S3_ENDPOINT_URL="https://[project-ref].supabase.co/storage/v1/s3"
     ```

---

### Step 3: Frontend Deployment on Cloudflare Pages

Cloudflare Pages provides global CDN distribution, automatic SSL, and instant git-based deployments.

1. **Push Code to Git**:
   - Initialize git and push your repository to GitHub or GitLab:
     ```bash
     git init
     git add .
     git commit -m "feat: complete arthai deployment"
     ```
2. **Configure Cloudflare Pages Project**:
   - Go to the **Cloudflare Dashboard** -> **Workers & Pages** -> **Create application** -> **Pages** -> **Connect to Git**.
   - Select your repository.
3. **Configure Build Settings**:
   - **Framework Preset**: `Vite` (or custom).
   - **Build Command**: `npm run build`
   - **Build Directory**: `frontend/dist`
   - **Root Directory**: `frontend`
4. **Set Environment Variables**:
   - Under Pages configuration settings, set:
     ```env
     VITE_API_URL="https://your-backend-domain.com"
     ```
5. **Deploy**:
   - Click **Save and Deploy**. Cloudflare will build the SPA and provide a custom subdomain (e.g., `arthai.pages.dev`).

---

### Step 4: Webhook & Backend Tunnel Deployment via Cloudflare

To receive live webhooks from Twilio WhatsApp API on your local developer machine or private cloud instances, you can expose the backend port securely using a **Cloudflare Tunnel**.

1. **Install Cloudflare Tunnel (`cloudflared`)**:
   - Follow instructions on [developers.cloudflare.com](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/install-tunnel/) to download the binary.
2. **Authenticate & Create Tunnel**:
   ```bash
   cloudflared tunnel login
   cloudflared tunnel create arthai-tunnel
   ```
3. **Configure the Tunnel**:
   - Create a configuration file `config.yml`:
     ```yaml
     tunnel: arthai-tunnel
     credentials-file: /root/.cloudflared/[tunnel-id].json

     ingress:
       - hostname: api.yourdomain.com
         service: http://localhost:8000
       - service: http_status:404
     ```
4. **Route Traffic**:
   ```bash
   cloudflared tunnel route dns arthai-tunnel api.yourdomain.com
   ```
5. **Run the Tunnel**:
   ```bash
   cloudflared tunnel run arthai-tunnel
   ```
6. **Twilio Webhook Association**:
   - Open your **Twilio Console** -> **Messaging** -> **Senders** -> **WhatsApp Senders**.
   - Configure your WhatsApp Sandbox or Business Number webhook URL to point to:
     `https://api.yourdomain.com/api/webhook/whatsapp`

---

## 🎯 Validation Checklists

Before declaring the deployment live, verify the following checks:
*   [ ] Run `npm run build` inside `frontend/` to confirm zero bundler/typescript errors.
*   [ ] Perform `python3 -m compileall backend` to confirm zero syntax errors.
*   [ ] Ensure `DATABASE_URL` resolves to Neon Tech Postgres without connection failures.
*   [ ] Verify file uploads in `storage.py` route seamlessly to the Supabase Public bucket.
*   [ ] Validate that Twilio sends webhooks to your server and receives immediate `<Response></Response>` within 200ms.
