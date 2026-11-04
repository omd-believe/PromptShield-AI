# PromptShield-AI

> Privacy-preserving AI prompt optimization and analysis — microservices architecture with LLMLingua-2 compression running on your own GPU.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER'S BROWSER                                     │
│                    React 19 + Vite (Vercel / Render Static)                 │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ HTTPS (JWT in Authorization header)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SPRING BOOT BACKEND (Render Docker)                  │
│            Java 21 • Spring Security • JWT • JPA • PostgreSQL               │
│                                                                             │
│  POST /api/v1/register   POST /api/v1/login                                 │
│  POST /api/v1/prompts    POST /api/v1/prompts/analyze                       │
│  GET  /api/v1/prompts/user   GET /api/v1/prompts/stats                     │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ HTTPS + X-AI-Service-Key (Cloudflare Tunnel)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     AI SERVICE (Your Fedora Laptop)                          │
│            Python • FastAPI • spaCy NER • LLMLingua-2 • FLAN-T5             │
│            AMD Ryzen 7 7840HS • NVIDIA RTX 3050 (6 GB VRAM)                │
│                                                                             │
│  POST /optimize   POST /analyze   GET /health                               │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ Neon PostgreSQL (SSL)
                                    ▼
                    ┌───────────────────────────────────┐
                    │      Neon PostgreSQL (Cloud)       │
                    │  users • prompts • privacy_audit   │
                    └───────────────────────────────────┘
```

> **Security boundary:** The browser never contacts the AI service directly. The Spring Boot backend is the only caller of the FastAPI endpoints, and all calls include a shared API key.

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Frontend | React 19, Vite 8, Axios, React Router 7 |
| Backend | Java 21, Spring Boot 4.1, Spring Security, JWT (HS256), Spring Data JPA |
| AI Service | Python 3.12+, FastAPI, spaCy 3.8, LLMLingua-2, FLAN-T5 (optional) |
| Database | PostgreSQL 17 (Neon serverless in production) |
| Infrastructure | Render (backend), Vercel/Render Static (frontend), Cloudflare Quick Tunnel (AI) |

---

## Prerequisites

### Local Development

| Tool | Version | Purpose |
|------|---------|---------|
| Node.js | 20+ | Frontend |
| Java | 21 | Backend |
| Python | 3.12+ | AI Service |
| PostgreSQL | 17 | Local DB (or use Docker) |
| Docker | 24+ (optional) | Full-stack local dev |

### Production

| Service | Purpose |
|---------|---------|
| Render | Backend Docker + Static frontend |
| Neon | Managed PostgreSQL |
| Vercel (optional) | Frontend alternative |
| Cloudflare Quick Tunnel | Expose local AI service |

---

## Local Setup (Without Docker)

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_USERNAME/promptshield-ai.git
cd promptshield-ai

# Copy and fill in environment files
cp docker/.env.example docker/.env
# Edit docker/.env with your secrets
```

### 2. Database (PostgreSQL)

```bash
# Start a local PostgreSQL instance (or use Docker):
docker run -d --name promptshield-postgres \
  -e POSTGRES_DB=promptshield_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=your_password \
  -p 127.0.0.1:5432:5432 \
  postgres:17-alpine
```

### 3. AI Service

```bash
cd ai-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Configure
cp .env.example .env
# Edit .env — set AI_SERVICE_API_KEY and optionally LLMLINGUA_USE_ONLINE_DOWNLOAD=true

# Run
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. Backend

```bash
cd backend/promptshield
export SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/promptshield_db
export SPRING_DATASOURCE_USERNAME=postgres
export SPRING_DATASOURCE_PASSWORD=your_password
export JWT_SECRET=$(openssl rand -base64 48)
export AI_SERVICE_URL=http://localhost:8000
export AI_SERVICE_API_KEY=your_api_key  # must match AI service

./mvnw spring-boot:run
```

### 5. Frontend

```bash
cd frontend
npm install
# Create .env with backend URL:
echo "VITE_API_BASE_URL=http://localhost:8080/api/v1" > .env
npm run dev
```

---

## Docker Compose Setup (Local)

```bash
# 1. Configure environment
cd docker
cp .env.example .env
# Fill in POSTGRES_PASSWORD, JWT_SECRET, AI_SERVICE_API_KEY

# 2. Build and start all services
docker compose up --build

# Services:
#   Frontend:  http://localhost:5173
#   Backend:   http://localhost:8080
#   AI:        http://localhost:8000
#   DB:        localhost:5433
```

---

## Environment Variable Reference

### Backend (Spring Boot on Render)

| Variable | Required | Description |
|----------|----------|-------------|
| `SPRING_DATASOURCE_URL` | ✅ | Neon JDBC URL with `?sslmode=require` |
| `SPRING_DATASOURCE_USERNAME` | ✅ | Neon database user |
| `SPRING_DATASOURCE_PASSWORD` | ✅ | Neon database password |
| `JWT_SECRET` | ✅ | HS256 signing key ≥ 32 bytes (`openssl rand -base64 48`) |
| `JWT_EXPIRATION` | No | Token TTL in ms (default: 86400000 = 24h) |
| `AI_SERVICE_URL` | ✅ | Cloudflare Tunnel URL, e.g. `https://abc.trycloudflare.com` |
| `AI_SERVICE_API_KEY` | ✅ | Shared secret with AI service (`openssl rand -hex 32`) |
| `CORS_ALLOWED_ORIGINS` | ✅ | Comma-separated frontend URLs |
| `PORT` | No | Render injects this automatically |

### AI Service (Fedora Laptop)

| Variable | Required | Description |
|----------|----------|-------------|
| `AI_SERVICE_API_KEY` | ✅ in prod | Must match backend setting |
| `LLMLINGUA_ENABLED` | No | Enable LLMLingua-2 (default: `true`) |
| `LLMLINGUA_DEVICE` | No | `auto`, `cpu`, or `cuda` |
| `LLMLINGUA_USE_ONLINE_DOWNLOAD` | No | Download model on first run |
| `FLAN_T5_ENABLED` | No | Enable FLAN-T5 (default: `false`) |
| `COMPRESSION_ENGINE` | No | `auto`, `llmlingua`, `flan-t5`, `deterministic` |

### Frontend (Build-time only)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_BASE_URL` | ✅ | Backend URL including `/api/v1`, e.g. `https://backend.onrender.com/api/v1` |

---

## Neon PostgreSQL Configuration

1. Create a free project at [neon.tech](https://neon.tech)
2. Copy the **Connection string** from the Neon dashboard
3. Set the env var:
   ```
   SPRING_DATASOURCE_URL=jdbc:postgresql://ep-xxx.us-east-2.aws.neon.tech/promptshield_db?sslmode=require
   ```
4. Schema is created automatically by Hibernate (`ddl-auto=update`) on first startup.

> **For production migrations:** After initial setup, change `HIBERNATE_DDL_AUTO=validate` and use Flyway for schema changes.

---

## Frontend Deployment

### Vercel

```bash
# Install Vercel CLI
npm i -g vercel

cd frontend
vercel --prod
# Set environment variable in Vercel dashboard:
# VITE_API_BASE_URL = https://your-backend.onrender.com/api/v1
```

Add `vercel.json` for SPA routing:
```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/" }]
}
```

### Render Static Site

| Setting | Value |
|---------|-------|
| Build Command | `npm ci && npm run build` |
| Publish Directory | `dist` |
| Root Directory | `frontend` |
| Environment Variable | `VITE_API_BASE_URL=https://your-backend.onrender.com/api/v1` |

Add a rewrite rule: `/* → /index.html` (200 status).

---

## Spring Boot Render Docker Deployment

| Setting | Value |
|---------|-------|
| Runtime | Docker |
| Root Directory | `backend/promptshield` |
| Dockerfile Path | `Dockerfile` |
| Health Check Path | `/api/v1/health` |
| Port | `10000` (Render auto-sets `PORT`) |

Required Environment Variables in Render dashboard:
```
SPRING_DATASOURCE_URL=jdbc:postgresql://...neon.tech/promptshield_db?sslmode=require
SPRING_DATASOURCE_USERNAME=your_neon_user
SPRING_DATASOURCE_PASSWORD=your_neon_password
JWT_SECRET=<openssl rand -base64 48>
AI_SERVICE_URL=https://your-tunnel.trycloudflare.com
AI_SERVICE_API_KEY=<openssl rand -hex 32>
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
```

---

## AI Service — Fedora Setup

### Install and run

```bash
cd ai-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Set environment variables
export AI_SERVICE_API_KEY=<same key as backend>
export LLMLINGUA_ENABLED=true
export LLMLINGUA_DEVICE=auto    # uses CUDA automatically
export LLMLINGUA_USE_ONLINE_DOWNLOAD=true  # first run only

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### GPU setup (RTX 3050)

```bash
# Install PyTorch with CUDA support (adjust cuda version for your driver)
pip install torch --index-url https://download.pytorch.org/whl/cu121

# Verify CUDA is detected
python3 -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

After first model download, set `LLMLINGUA_USE_ONLINE_DOWNLOAD=false` to prevent network calls on restart.

---

## Cloudflare Quick Tunnel Setup

```bash
# Install cloudflared (Fedora)
sudo dnf install cloudflared    # or use the binary from cloudflare.com/downloads

# Start tunnel (AI service must be running on port 8000)
cloudflared tunnel --url http://localhost:8000
```

The tunnel URL looks like: `https://abc-def-123.trycloudflare.com`

**Update the backend when the tunnel URL changes:**
1. Go to Render backend service → Environment
2. Update `AI_SERVICE_URL` to the new tunnel URL
3. Render redeploys automatically (< 2 min)

> **Never commit the tunnel URL.** It is a temporary address that changes every time you restart the tunnel.

---

## Service Endpoints

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 (dev) |
| Backend API | http://localhost:8080/api/v1 |
| Backend Swagger | http://localhost:8080/swagger-ui.html |
| AI Service | http://localhost:8000 |
| AI Docs | http://localhost:8000/docs |

---

## Security Considerations

1. **Never commit secrets** — all credentials must be environment variables
2. **Rotate credentials** if they were ever in git history
3. **AI service is protected** — `X-AI-Service-Key` header required when `AI_SERVICE_API_KEY` is set
4. **Browser isolation** — the React frontend never calls the AI service directly
5. **JWT minimum 32 bytes** — the backend enforces this at startup
6. **Neon SSL** — `sslmode=require` is enforced in JDBC URL and Hibernate config
7. **CORS is explicit** — `CORS_ALLOWED_ORIGINS` must list exact frontend URLs; wildcards are not used

---

## Known Free-Hosting Limitations

| Issue | Detail |
|-------|--------|
| Render free tier sleeps after 15 min | First request after sleep takes ~30s |
| Neon serverless cold start | First query after idle period takes ~1s |
| Cloudflare Quick Tunnel URL changes | Update `AI_SERVICE_URL` in Render after each laptop restart |
| RTX 3050 6 GB VRAM | LLMLingua-2 runs fine; multiple simultaneous requests are queued |

---

## Available Commands

```bash
# Local launcher (all services)
./run.sh              # start all
./run.sh start -d     # background
./run.sh stop         # stop all
./run.sh status       # health check
./run.sh logs ai      # view AI service logs

# Frontend
cd frontend && npm run dev    # dev server
cd frontend && npm run build  # production build
cd frontend && npm run lint   # lint check

# Backend
cd backend/promptshield && ./mvnw spring-boot:run
cd backend/promptshield && ./mvnw clean test
cd backend/promptshield && ./mvnw clean package -DskipTests

# AI Service
cd ai-service && .venv/bin/pytest tests/ -v
cd ai-service && uvicorn app.main:app --host 0.0.0.0 --port 8000
```
