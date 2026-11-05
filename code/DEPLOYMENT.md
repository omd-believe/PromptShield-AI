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

## Section 6 — AI Service on Fedora + Cloudflare Tunnel (Persistent systemd Services)

### 6.1 Architecture & Persistence Overview

The AI service and Cloudflare Tunnel run as persistent systemd user services on Fedora.
- Path Symlink: `~/promptshield-ai` points to the AI service directory to keep systemd paths clean.
- Systemd User Services:
  - `promptshield-ai.service`: Manages the FastAPI Uvicorn process, loads environment variables via `EnvironmentFile`, and utilizes local GPU CUDA inference.
  - `promptshield-tunnel.service`: Manages the Cloudflare Tunnel forwarding to `http://127.0.0.1:8000`, started automatically after `promptshield-ai.service`.
- Session Lingering: Enabled via `loginctl enable-linger omd24` so services continue running headless across lock screens, logouts, and system reboots.

### 6.2 Service Control Commands

**FastAPI AI Service:**
```bash
# Check status
systemctl --user status promptshield-ai.service

# View recent logs
journalctl --user -u promptshield-ai.service -n 50 --no-pager

# Follow logs in real time
journalctl --user -u promptshield-ai.service -f

# Restart / Stop / Start
systemctl --user restart promptshield-ai.service
systemctl --user stop promptshield-ai.service
systemctl --user start promptshield-ai.service
```

**Cloudflare Tunnel:**
```bash
# Check status
systemctl --user status promptshield-tunnel.service

# Extract current Quick Tunnel public URL
journalctl --user -u promptshield-tunnel.service -n 50 --no-pager | grep "trycloudflare.com"

# Restart tunnel (note: creates a new Quick Tunnel URL)
systemctl --user restart promptshield-tunnel.service
```

### 6.3 Local Verification (Without Exposing Secrets)

```bash
# 1. Verify health check (unauthenticated)
curl -s http://127.0.0.1:8000/health

# 2. Verify unauthorized requests are rejected (HTTP 401)
curl -s -o /dev/null -w "Missing key: HTTP %{http_code}\n" -X POST http://127.0.0.1:8000/optimize -H "Content-Type: application/json" -d '{"prompt": "test"}'
curl -s -o /dev/null -w "Invalid key: HTTP %{http_code}\n" -X POST http://127.0.0.1:8000/optimize -H "Content-Type: application/json" -H "X-API-Key: invalid-key" -d '{"prompt": "test"}'

# 3. Verify authorized GPU inference (safe in-memory key test)
python3 - << 'EOF'
import requests

env_vars = {}
with open("/home/omd24/promptshield-ai/.env") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env_vars[k.strip()] = v.strip().strip("'\"")

res = requests.post(
    "http://127.0.0.1:8000/optimize",
    json={"prompt": "Hello test prompt with email test@example.com", "compression_engine": "llmlingua"},
    headers={"Content-Type": "application/json", "X-API-Key": env_vars.get("AI_SERVICE_API_KEY", "")},
    timeout=60
)
print(f"Status: {res.status_code}, Anonymized: {res.json().get('optimized_prompt')}")
EOF
```

### 6.4 Update Render Backend with Tunnel URL

1. Obtain the active tunnel URL:
   ```bash
   journalctl --user -u promptshield-tunnel.service -n 50 --no-pager | grep "trycloudflare.com"
   ```
2. In the Render Dashboard:
   - Navigate to **Dashboard** → **promptshield-backend** → **Environment**.
   - Set or update:
     - `AI_SERVICE_URL` = `https://<active-subdomain>.trycloudflare.com` (do not add a trailing slash).
     - `AI_SERVICE_API_KEY` = `<your-ai-service-api-key>` (must match the key in `.env`).
3. Save changes. Render will redeploy the backend in 1–2 minutes.

---

## Section 7 — Tunnel Maintenance & Upgrading to a Named Tunnel

### When the Quick Tunnel Restarts
Quick Tunnels are ephemeral: whenever `promptshield-tunnel.service` restarts or your laptop reconnects, a new `*.trycloudflare.com` URL is generated.
When this happens:
1. Run `journalctl --user -u promptshield-tunnel.service -n 30 | grep trycloudflare.com` to get the new URL.
2. Update `AI_SERVICE_URL` in the Render dashboard.

### Upgrading to a Stable Named Tunnel (Zero URL Changes)
When you are ready for a permanent URL:
```bash
# 1. Authenticate with your Cloudflare account
cloudflared tunnel login

# 2. Create a named tunnel
cloudflared tunnel create promptshield-ai

# 3. Route DNS to your custom domain
cloudflared tunnel route dns promptshield-ai ai.yourdomain.com

# 4. Update ~/.config/systemd/user/promptshield-tunnel.service ExecStart to:
# ExecStart=/usr/local/bin/cloudflared tunnel run --url http://127.0.0.1:8000 promptshield-ai
systemctl --user daemon-reload
systemctl --user restart promptshield-tunnel.service
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

