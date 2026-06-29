# ArthAI Cloud Deployment Guide 🚀
### Deploying Frontend to Cloudflare, Database to Neon Tech, and Backend to Hugging Face Spaces

This document outlines the step-by-step deployable architecture for the ArthAI production stack.

---

## 🏗️ Deployment Topology

```
┌────────────────────────┐
│     React Frontend     │  (Cloudflare Pages CDN / Cloudflared)
└────────────────────────┘
            │
            ▼  (Encrypted HTTPS)
┌────────────────────────┐
│    FastAPI Backend     │  (Hugging Face Spaces - Docker Template)
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

## 🤗 2. Backend Deployment: Hugging Face Spaces (Docker Space)

Hugging Face Spaces runs full FastAPI applications inside custom Docker containers.

### Important Port & Dependency Details
- **Port 7860**: Hugging Face Spaces routes traffic to port `7860` by default. The `backend/Dockerfile` is configured to `EXPOSE 7860` and start the Uvicorn server on port `7860`.
- **System Dependencies**: The builder stage installs `libgdk-pixbuf-2.0-dev` instead of the legacy `libgdk-pixbuf2.0-dev` to ensure compatibility with modern Debian-slim images.

### Setup Instructions
1. **Create Space**:
   - Go to [huggingface.co/spaces](https://huggingface.co/spaces) and click **Create new Space**.
   - Set **Owner** and **Space Name** (e.g., `arthai-backend`).
   - Select **Docker** as the SDK/Template.
   - Select **Blank** as the Docker template.
   - Set **Space License** to Apache-2.0 (or keep private if needed).
2. **Configure Space Secrets**:
   - In your Hugging Face Space, go to **Settings** -> **Variables and secrets** -> **New secret**.
   - Add all environment variables from `backend/.env.example` as Space secrets:
     - `DATABASE_URL` (your Neon connection string)
      - `GEMINI_API_KEY`
      - `SARVAM_API_KEY`
     - `TWILIO_ACCOUNT_SID`
     - `TWILIO_AUTH_TOKEN`
     - `TWILIO_WHATSAPP_FROM`
     - `SECRET_KEY` (a 32-character secret string)
3. **Push Code to Hugging Face**:
   - Clone your Hugging Face space repository locally or push your `backend/` directory to it:
     ```bash
     git remote add hf https://huggingface.co/spaces/[your-username]/[space-name]
     git push hf main
     ```
   - Hugging Face will automatically detect the `backend/Dockerfile`, compile the image (including all dependencies for PDF compilation), expose port `7860`, and run the app.
4. **Twilio Webhook Routing**:
   - Go to your Twilio WhatsApp sender dashboard.
   - Set your inbound webhook URL to the Hugging Face Space direct API URL:
     `https://[username]-[space-name].hf.space/whatsapp`

---

## 🌐 3. Frontend Deployment: Cloudflare Pages / Workers

The React single-page application is hosted globally on Cloudflare's edge network. You can deploy it either via Git Integration (Cloudflare Pages Dashboard) or via Wrangler CLI.

### Option A: Deployment via Wrangler CLI (Recommended)
1. **Configure Environment Variables**:
   Create a `.env` file in the `frontend` folder with your production API URL:
   ```env
   VITE_API_URL="https://[username]-[space-name].hf.space"
   ```
2. **Build and Deploy**:
   From the project directory:
   ```bash
   cd frontend
   npm run deploy
   ```
   *Note: Under the hood, this runs `npm run build && wrangler deploy`, compiling the React bundle into `./dist` and publishing it to Cloudflare Pages/Workers as defined in `wrangler.jsonc`.*

### Option B: Deployment via Cloudflare Pages (Git Integration)
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
     VITE_API_URL="https://[username]-[space-name].hf.space"
     ```
5. **Deploy**: Click **Save and Deploy**. Cloudflare compiles the assets and assigns a production URL (e.g. `arthai.pages.dev`).

---

## 📡 4. Exposing Local Dev to Webhooks: Cloudflare Tunnel

To test webhooks locally during development, use **Cloudflare Tunnel** (`cloudflared`) to expose port `8000`.

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
