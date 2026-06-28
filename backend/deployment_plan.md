# ArthAI Cloud Deployment Guide 🚀
### Deploying Frontend to Cloudflare, Database to Neon Tech, and Storage/Auth to Supabase

This document outlines the step-by-step deployable architecture for the ArthAI production stack.

---

## 🏗️ Deployment Topology

```
┌────────────────────────┐
│     React Frontend     │  (Cloudflare Pages CDN)
└────────────────────────┘
            │
            ▼  (Encrypted HTTPS)
┌────────────────────────┐
│    FastAPI Backend     │  (Supabase Edge Functions / VPS / PaaS)
└────────────────────────┘
      │            │
      │            ▼
      │      ┌────────────────────────┐
      │      │    Object Storage      │  (Supabase Buckets - Receipts & PDFs)
      │      └────────────────────────┘
      ▼
┌────────────────────────┐
│  Serverless Database   │  (Neon Tech PostgreSQL)
└────────────────────────┘
```

---

## 💾 1. Database Setup: Neon Tech (Postgres)

Neon provides serverless PostgreSQL with scale-to-zero capabilities and transaction pooling.

### Setup Instructions
1. **Create Account**: Sign up at [neon.tech](https://neon.tech/).
2. **Provision Database**: Create a new project `arthai`. Choose region `ap-south-1` (Mumbai) for the lowest latency in India.
3. **Retrieve Connection String**:
   - Copy the connection string from the dashboard. Ensure to enable transaction pooling (port `5432` or pooled host prefix `ep-...-pooler...`) if connecting via serverless workers.
   - Example connection string format:
     ```env
     DATABASE_URL="postgresql://[user]:[password]@[host]-pooler.ap-south-1.aws.neon.tech/neondb?sslmode=require"
     ```
4. **Run Database Migrations**:
   - Run the initialization script in the backend to set up the schemas:
     ```bash
     cd backend
     python -c "from database import engine, Base; Base.metadata.create_all(bind=engine)"
     ```

---

## ⚡ 2. Media Storage & Auth: Supabase

Supabase is used for object storage (receipt images, audio recordings, statement PDFs) and optional app authentication.

### Storage Setup Instructions
1. **Create Project**: Sign up at [supabase.com](https://supabase.com/) and spin up a new project named `arthai`.
2. **Create Public Bucket**:
   - Go to **Storage** -> **Create New Bucket**.
   - Name it `arthai-media`.
   - Toggle **Public** to `ON` so that Twilio's WhatsApp API and the React client can download images and PDFs using static public URLs.
3. **Configure S3-Compatible Keys** (Used by `backend/services/storage.py`):
   - Navigate to **Project Settings** -> **Storage**.
   - Copy the **S3 Connection URL**: `https://[project-ref].supabase.co/storage/v1/s3`.
   - Go to your Supabase Access Tokens and generate S3 access keys (`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`).
   - Configure these in your backend `.env` variables:
     ```env
     AWS_ACCESS_KEY_ID="your-supabase-s3-access-key"
     AWS_SECRET_ACCESS_KEY="your-supabase-s3-secret-key"
     AWS_BUCKET_NAME="arthai-media"
     AWS_S3_ENDPOINT_URL="https://[project-ref].supabase.co/storage/v1/s3"
     ENABLE_S3_STORAGE=true
     ```

---

## 🌐 3. Frontend Deployment: Cloudflare Pages

The React single-page application is hosted globally on Cloudflare's edge network.

### Setup Instructions
1. **Push Frontend Repository**: Push your code to GitHub or GitLab.
2. **Configure Cloudflare Pages**:
   - Go to **Cloudflare Dashboard** -> **Workers & Pages** -> **Create Application** -> **Pages** -> **Connect to Git**.
3. **Build Parameters**:
   - **Root Directory**: `frontend`
   - **Framework Preset**: `Vite`
   - **Build Command**: `npm run build`
   - **Build Output Directory**: `dist`
4. **Environment Configuration**:
   - Under project settings -> **Environment variables**, define:
     ```env
     VITE_API_URL="https://your-backend-api-domain.com"
     ```
5. **Deploy**: Click **Save and Deploy**. Cloudflare compiles the assets and assigns a production URL (e.g. `arthai.pages.dev`).

---

## 📡 4. Webhook Security & Exposing Backend: Cloudflare Tunnel

Since Twilio communicates via standard webhooks, the backend must be publicly accessible on HTTPS. We secure the ingress without exposing ports directly using **Cloudflare Tunnel** (`cloudflared`).

### Setup Instructions
1. **Install Cloudflared**:
   - Download the agent binary to your hosting environment:
     ```bash
     curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
     chmod +x cloudflared
     ```
2. **Create Tunnel**:
   ```bash
   cloudflared tunnel login
   cloudflared tunnel create arthai-tunnel
   ```
3. **Write Configuration (`config.yml`)**:
   ```yaml
   tunnel: arthai-tunnel
   credentials-file: /root/.cloudflared/[tunnel-id].json

   ingress:
     - hostname: api.yourdomain.com
       service: http://localhost:8000
     - service: http_status:404
   ```
4. **Map Hostname DNS**:
   ```bash
   cloudflared tunnel route dns arthai-tunnel api.yourdomain.com
   ```
5. **Execute Tunnel**:
   ```bash
   cloudflared tunnel run arthai-tunnel
   ```
6. **Twilio Webhook Configuration**:
   - Point the Twilio WhatsApp Incoming Webhook url to:
     `https://api.yourdomain.com/api/webhook/whatsapp`
