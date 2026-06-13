# Job Hunter — VPS Deployment Guide

**Stack:** FastAPI (Python 3.11) + Next.js 16 + PostgreSQL 15 + Docker Compose  
**LLM:** Google Gemini 1.5 Flash/Pro  
**2FA:** Email OTP (SMTP) + WhatsApp OTP (Meta Cloud API / Twilio)

---

## 1. Prerequisites

```bash
# Server: Ubuntu 22.04 LTS / Debian Bookworm
# Required on the VPS:
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin git curl

# Verify
docker --version        # >= 24.0
docker compose version  # >= 2.20
```

---

## 2. Clone the Repository

```bash
git clone <repo-url> /opt/jobhunter
cd /opt/jobhunter
```

---

## 3. Environment File — COMPLETE VARIABLE REFERENCE

Create `/opt/jobhunter/job_hunter/.env` with **all** of the following:

```dotenv
# ── Google Gemini (LLM) ──────────────────────────────────────────────────────
# Required — no fallback. Get key at https://aistudio.google.com/apikey
GEMINI_API_KEY=AIza...

# ── PostgreSQL ───────────────────────────────────────────────────────────────
# Internal Docker network address — keep postgres hostname
DATABASE_URL=postgresql://jobhunter:STRONG_PASSWORD@postgres:5432/jobhunter_db

# ── Auth / JWT ───────────────────────────────────────────────────────────────
# MUST be changed. Generate: python3 -c "import secrets; print(secrets.token_hex(32))"
AUTH_SECRET=<64-char-random-hex>

# ── OTP signing ──────────────────────────────────────────────────────────────
# If omitted, falls back to AUTH_SECRET (acceptable)
OTP_SECRET=

# ── SMTP / Email OTP ─────────────────────────────────────────────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
# Use a Gmail App Password (16 chars), NOT your account password
# Generate at: https://myaccount.google.com/apppasswords
SMTP_PASS=xxxx xxxx xxxx xxxx
EMAIL_FROM=your-email@gmail.com
EMAIL_FROM_NAME=Job Hunter

# ── WhatsApp OTP (choose ONE of the three options below) ─────────────────────

# OPTION A — Meta Cloud API (recommended for production)
# Setup: https://developers.facebook.com/apps → WhatsApp → API Setup
WHATSAPP_CLOUD_API_TOKEN=EAAx...
WHATSAPP_PHONE_NUMBER_ID=1234567890

# OPTION B — Twilio (alternative)
# TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# OPTION C — Local WhatsApp Web bot (development/fallback only)
# WHATSAPP_API_URL=http://localhost:3001/send
# WHATSAPP_BOT_NUMBER=+521234567890

# ── Telegram Bot (optional — bot won't start if empty) ────────────────────────
TELEGRAM_BOT_TOKEN=
TELEGRAM_ADMIN_ID=

# ── Playwright ───────────────────────────────────────────────────────────────
PLAYWRIGHT_HEADLESS=true
```

**IMPORTANT:** The `DATABASE_URL` password must match the PostgreSQL credentials in `docker-compose.yml`. If you change the password, update **both** files:

In `docker-compose.yml`:
```yaml
postgres:
  environment:
    POSTGRES_PASSWORD: STRONG_PASSWORD   # ← match .env
```

---

## 4. Frontend Environment

The frontend reads environment variables at **build time** via the Dockerfile.  
`NEXT_PUBLIC_API_URL=/backend` is already set in `frontend/Dockerfile`.

If your domain is `https://app.example.com`, set these in `docker-compose.yml` under the `frontend` service:

```yaml
environment:
  - AUTH_URL=https://app.example.com
  - AUTH_SECRET=<same-secret-as-backend>
  - AUTH_TRUST_HOST=true
  - NEXT_TELEMETRY_DISABLED=1
  - NODE_ENV=production
  - BACKEND_URL=http://api:8000
```

---

## 5. Build and Launch

```bash
cd /opt/jobhunter

# First-time build (takes 5-15 min — downloads texlive + playwright + node modules)
docker compose up -d --build

# Follow logs
docker compose logs -f api
docker compose logs -f frontend
```

### Verify all services are healthy:

```bash
docker compose ps
# Expected: postgres (healthy), api (healthy), frontend (Up)

# API smoke test
curl -s http://localhost:8000/ | python3 -m json.tool

# Frontend smoke test
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
# Expected: 200
```

---

## 6. Database

**No manual migrations required.** The API auto-creates and auto-migrates all tables on startup via `_init_db()` in `api.py`. This includes:
- `usuarios` table with all 2FA columns (`email_otp`, `whatsapp_otp`, `phone_verified`, etc.)
- `vacantes` table
- `default_user` seed entry

To verify the DB is initialized after first boot:

```bash
docker compose exec postgres psql -U jobhunter -d jobhunter_db -c "\dt"
# Expected: usuarios, vacantes (and any others)

# Check default_user seed:
docker compose exec postgres psql -U jobhunter -d jobhunter_db \
  -c "SELECT user_id, email, role, tier FROM usuarios LIMIT 5;"
```

If you later need to run Prisma migrations (for schema tooling only):

```bash
docker compose exec api bash -c "cd /app && pip install prisma && prisma migrate deploy"
```

---

## 7. Reverse Proxy (Nginx — recommended)

```nginx
server {
    listen 80;
    server_name app.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name app.example.com;

    ssl_certificate     /etc/letsencrypt/live/app.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.example.com/privkey.pem;

    # Frontend (Next.js)
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API (direct access if needed)
    location /api-direct/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
    }
}
```

The Next.js rewrite rule in `next.config.ts` already proxies `/backend/*` → `http://api:8000/*` via Docker internal networking, so the frontend handles all API calls transparently.

---

## 8. Useful Maintenance Commands

```bash
# Restart a specific service without rebuild
docker compose restart api

# Rebuild only the backend after Python changes
docker compose up -d --build api

# Rebuild only the frontend after Next.js changes
docker compose up -d --build frontend

# View real-time API logs
docker compose logs -f --tail=100 api

# Shell into the API container
docker compose exec api bash

# Shell into the DB
docker compose exec postgres psql -U jobhunter -d jobhunter_db

# Full teardown (keeps postgres_data volume)
docker compose down

# Full teardown INCLUDING database (DESTRUCTIVE — loses all data)
docker compose down -v
```

---

## 9. Persistent Volumes

| Volume / Bind Mount | Purpose | Notes |
|---|---|---|
| `postgres_data` (named volume) | PostgreSQL data | Survives `docker compose down` |
| `./job_hunter/db` → `/app/db` | SQLite fallback / user data JSON | Back this up |
| `./job_hunter/outputs` → `/app/outputs` | Generated PDF and .tex files | Back this up |
| `./job_hunter/logs` → `/app/logs` | Application logs | Rotate with logrotate |

Backup command:
```bash
# Backup PostgreSQL
docker compose exec postgres pg_dump -U jobhunter jobhunter_db | gzip > backup_$(date +%Y%m%d).sql.gz

# Backup user files
tar czf user_data_$(date +%Y%m%d).tar.gz /opt/jobhunter/job_hunter/{db,outputs}
```

---

## 10. API Key Rotation

To rotate `GEMINI_API_KEY` without downtime:

```bash
# 1. Update the .env file
nano /opt/jobhunter/job_hunter/.env

# 2. Restart the API container (no rebuild needed — reads .env at runtime)
docker compose restart api

# 3. Verify
docker compose logs --tail=20 api | grep -i gemini
```

---

## 11. WhatsApp OTP — Provider Priority

The system attempts delivery in this order:
1. **Meta Cloud API** — if `WHATSAPP_CLOUD_API_TOKEN` and `WHATSAPP_PHONE_NUMBER_ID` are set
2. **Twilio** — if `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM` are set
3. **Local bot** — fallback to `WHATSAPP_API_URL` (dev only)

For production, configure **Option A (Meta Cloud API)**. The WhatsApp Business Account must have the number approved and the message template "text" type enabled.

---

## 12. Checklist Before Going Live

- [ ] `AUTH_SECRET` changed from default (check both `.env` and `docker-compose.yml` frontend section)
- [ ] PostgreSQL password changed from `devpass`
- [ ] `GEMINI_API_KEY` set and tested (GET `/` should return `{"status":"ok"}`)
- [ ] SMTP credentials set and email OTP delivered in test registration
- [ ] WhatsApp OTP provider configured (Meta Cloud API or Twilio)
- [ ] `AUTH_URL` in `docker-compose.yml` frontend points to the real HTTPS domain
- [ ] Nginx reverse proxy with SSL configured
- [ ] PostgreSQL port `5433` NOT exposed publicly (remove the `ports:` line from `postgres` service in prod)
- [ ] `docker compose ps` shows all services healthy
- [ ] Backup cron job configured
