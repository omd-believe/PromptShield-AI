# DEPLOYMENT.md — PromptShield-AI Step-by-Step Deployment Guide

This guide walks through the complete deployment of all four components.
Follow sections in order. Total estimated time: 60–90 minutes on first deploy.

---

## Prerequisites Checklist

- [ ] Neon account created at [neon.tech](https://neon.tech)
- [ ] Render account created at [render.com](https://render.com)
- [ ] Vercel account (optional — alternatively use Render Static Site)
- [ ] Cloudflare account (free, for Quick Tunnel)
- [ ] GitHub repository created and code pushed (see Section 1)
- [ ] `cloudflared` installed on your Fedora laptop
- [ ] AI service dependencies installed (`pip install -r requirements.txt`)

---

## Section 1 — GitHub Push (First Time)

```bash
cd /path/to/your/code  # the repo root

# 1. Initialize git
git init

# 2. Add all files, respecting .gitignore
git add .

# 3. Verify no secrets are staged
git status
# IMPORTANT: check that docker/.env, ai-service/.env, backend/.env are NOT listed

# If any .env file appears (should not after the gitignore fix):
git rm --cached docker/.env
git rm --cached ai-service/.env
git rm --cached backend/promptshield/.env

# 4. Commit
git commit -m "feat: initial production-ready PromptShield-AI"

# 5. Push to GitHub
git remote add origin https://github.com/YOUR_USERNAME/promptshield-ai.git
git branch -M main
git push -u origin main
```

> **Before pushing:** Verify `docker/.env` contains only `!!CHANGE!!` placeholder values, not real credentials. The git commit above includes our sanitized version.

---

## Section 2 — Neon PostgreSQL

1. Go to [neon.tech](https://neon.tech) → New Project
2. Region: Choose closest to your Render region (e.g. US East)
3. Database name: `promptshield_db`
4. After creation, click **Connection string** → copy the JDBC URL:
   ```
   jdbc:postgresql://ep-xxx.us-east-2.aws.neon.tech/promptshield_db?sslmode=require
   ```
5. Note down:
   - Connection string (JDBC format)
   - Username
   - Password

No manual table creation needed — Hibernate creates the schema on first backend startup.

---

## Section 3 — Generate Secrets

Run these commands locally to generate strong secrets:

```bash
# PostgreSQL password (if using local dev)
openssl rand -base64 24

# JWT signing key (minimum 32 bytes = 43+ base64 chars)
openssl rand -base64 48

# AI service shared API key
openssl rand -hex 32
```

**Store these values securely** — you will enter them in Render and locally.

---

## Section 4 — Deploy Spring Boot Backend to Render

### 4.1 Create a new Web Service

1. Go to [render.com](https://render.com) → **New** → **Web Service**
2. Connect your GitHub repository
3. Configure:

| Field | Value |
|-------|-------|
| **Name** | `promptshield-backend` |
| **Region** | US East (or closest to Neon) |
| **Root Directory** | `backend/promptshield` |
| **Runtime** | `Docker` |
| **Dockerfile Path** | `Dockerfile` |
| **Docker Build Context** | `.` (the root directory = `backend/promptshield`) |
| **Instance Type** | Free (512 MB RAM) |
| **Health Check Path** | `/api/v1/health` |

### 4.2 Set Environment Variables

In Render → Environment tab, add:

```
SPRING_DATASOURCE_URL       = jdbc:postgresql://ep-xxx.aws.neon.tech/promptshield_db?sslmode=require
SPRING_DATASOURCE_USERNAME  = your_neon_username
SPRING_DATASOURCE_PASSWORD  = your_neon_password
JWT_SECRET                  = <your generated JWT secret>
JWT_EXPIRATION              = 86400000
AI_SERVICE_URL              = https://your-tunnel.trycloudflare.com
AI_SERVICE_API_KEY          = <your generated AI API key>
CORS_ALLOWED_ORIGINS        = https://your-frontend.vercel.app
```

> Leave `AI_SERVICE_URL` as a placeholder initially — set it after starting the Cloudflare Tunnel in Section 6.

### 4.3 Deploy

Click **Create Web Service**. First build takes 5–10 minutes.

After deployment, verify:
```bash
curl https://promptshield-backend.onrender.com/api/v1/health
# Expected: {"status":"UP","service":"PromptShield Backend","timestamp":"..."}
```

---

## Section 5 — Deploy Frontend

### Option A: Vercel (Recommended)

1. Go to [vercel.com](https://vercel.com) → **Add New Project**
2. Import GitHub repository
3. Configure:

| Field | Value |
|-------|-------|
| **Framework** | Vite |
| **Root Directory** | `frontend` |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |
| **Install Command** | `npm ci` |

4. Add environment variable:
   ```
   VITE_API_BASE_URL = https://promptshield-backend.onrender.com/api/v1
   ```
5. Create a `frontend/vercel.json` file (already created in repo):
   ```json
   {"rewrites": [{"source": "/(.*)", "destination": "/"}]}
   ```
6. Click **Deploy**

### Option B: Render Static Site

1. Render → **New** → **Static Site**
2. Configure:

| Field | Value |
|-------|-------|
| **Root Directory** | `frontend` |
| **Build Command** | `npm ci && npm run build` |
| **Publish Directory** | `dist` |

3. Add environment variable:
   ```
   VITE_API_BASE_URL = https://promptshield-backend.onrender.com/api/v1
   ```
4. Add a Rewrite Rule: `/*` → `/index.html` (HTTP 200)

### 5.1 Update Backend CORS

After getting the frontend URL (e.g. `https://promptshield.vercel.app`):

1. Go to Render backend → Environment
2. Update `CORS_ALLOWED_ORIGINS`:
   ```
   CORS_ALLOWED_ORIGINS = https://promptshield.vercel.app
   ```
3. Render will auto-redeploy

---

## Section 6 — AI Service on Fedora + Cloudflare Tunnel

### 6.1 Set up the AI service

```bash
cd ai-service
source .venv/bin/activate   # activate existing venv (or create: python -m venv .venv)

# Set required environment variables
export AI_SERVICE_API_KEY=<same key as Render backend>
export LLMLINGUA_ENABLED=true
export LLMLINGUA_DEVICE=auto
export LLMLINGUA_USE_ONLINE_DOWNLOAD=true  # first run only; set false after cache

# Start the AI service
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Verify locally:
```bash
curl http://localhost:8000/health
# {"status":"healthy"}
```

### 6.2 Test API key authentication

```bash
# Should return 401 (no key)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/optimize \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test"}'

# Should work (correct key)
curl -s http://localhost:8000/health
# (health endpoint has no auth requirement)
```

### 6.3 Start Cloudflare Quick Tunnel

```bash
# Install cloudflared (if not installed)
sudo dnf install cloudflared
# Or: wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.rpm
# sudo rpm -ivh cloudflared-linux-amd64.rpm

# Start the tunnel (keep this terminal open)
cloudflared tunnel --url http://localhost:8000
```

The output will show a URL like:
```
2026-11-04T10:00:00Z INF +----------------------------+
2026-11-04T10:00:00Z INF |  Your quick Tunnel has been created! Visit it at    |
2026-11-04T10:00:00Z INF |  https://abc-def-ghi-123.trycloudflare.com          |
```

### 6.4 Update Render backend with tunnel URL

1. Render → promptshield-backend → Environment
2. Set `AI_SERVICE_URL = https://abc-def-ghi-123.trycloudflare.com`
3. Render auto-redeploys (< 2 minutes)

### 6.5 Verify end-to-end

```bash
# Test backend can reach AI service
curl https://promptshield-backend.onrender.com/api/v1/health
```

---

## Section 7 — When the Tunnel URL Changes

The Quick Tunnel URL changes **every time you restart cloudflared**. To update:

```bash
# 1. Start cloudflared again (get new URL from output)
cloudflared tunnel --url http://localhost:8000

# 2. Update Render immediately
# Go to: Render → promptshield-backend → Environment
# Set: AI_SERVICE_URL = https://new-url.trycloudflare.com
# Render will redeploy in < 2 min
```

**Optional: persistent tunnel (named tunnel)**
```bash
# One-time setup for a stable URL
cloudflared tunnel login
cloudflared tunnel create promptshield-ai
cloudflared tunnel route dns promptshield-ai ai.yourdomain.com
cloudflared tunnel run --url http://localhost:8000 promptshield-ai
# This URL never changes — no need to update Render
```

---

## Section 8 — Integration Tests

After all services are deployed and running:

```bash
# 1. Health checks
curl https://promptshield-backend.onrender.com/api/v1/health

# 2. Register a user
curl -X POST https://promptshield-backend.onrender.com/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com","password":"SecurePass123!"}'

# 3. Login
curl -X POST https://promptshield-backend.onrender.com/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"SecurePass123!"}'
# Note the token from the response

# 4. Optimize a prompt (replace TOKEN with the JWT from step 3)
curl -X POST https://promptshield-backend.onrender.com/api/v1/prompts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"prompt":"Please can you help me to kindly summarize the following text that I need to present in a document format for a business meeting tomorrow morning?"}'
```

---

## Section 9 — Deployment Checklist

### Pre-deployment
- [ ] `docker/.env` contains only `!!CHANGE!!` placeholders
- [ ] No real credentials in any committed file
- [ ] `.gitignore` excludes all `.env` files
- [ ] Frontend build passes (`npm run build`)
- [ ] Python syntax check passes
- [ ] AI service unit tests pass (140 unit tests)

### Neon
- [ ] Project created, database `promptshield_db` exists
- [ ] JDBC connection string copied (with `?sslmode=require`)
- [ ] Credentials noted securely

### Render Backend
- [ ] Web Service created with Docker runtime
- [ ] Root Directory set to `backend/promptshield`
- [ ] All 7 environment variables set
- [ ] Health check `/api/v1/health` returns 200
- [ ] Hibernate has created the database schema

### Frontend
- [ ] Deployed to Vercel or Render Static Site
- [ ] `VITE_API_BASE_URL` set to backend URL
- [ ] SPA rewrite configured (`/*` → `/index.html`)
- [ ] CORS on backend updated with frontend URL
- [ ] Login and registration work from browser

### AI Service
- [ ] `uvicorn` running on `0.0.0.0:8000`
- [ ] `AI_SERVICE_API_KEY` set (matches backend)
- [ ] LLMLingua-2 model downloaded and cached
- [ ] `cloudflared tunnel` running (note the URL)
- [ ] `AI_SERVICE_URL` updated in Render backend

### End-to-End
- [ ] User can register and log in via browser
- [ ] Prompt optimization returns results
- [ ] Privacy analysis works
- [ ] History page shows past prompts
- [ ] Dashboard shows statistics
- [ ] No secrets visible in browser DevTools Network tab

