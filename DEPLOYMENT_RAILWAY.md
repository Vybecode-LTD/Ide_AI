# Ide/AI — Railway Deployment Guide

> **Last updated:** 2026-05-27

Step-by-step guide to deploy Ide/AI (React frontend + FastAPI backend + PostgreSQL) on [Railway](https://railway.com).

---

## Architecture Overview

```
                      Railway Project
 ┌──────────────────────────────────────────────────┐
 │                                                  │
 │  ┌──────────────┐   ┌──────────────┐             │
 │  │   Backend    │   │   Frontend   │             │
 │  │  FastAPI +   │   │  Vite build  │             │
 │  │  Uvicorn     │   │  served by   │             │
 │  │              │   │  Caddy       │             │
 │  │ (public URL) │   │ (public URL) │             │
 │  └──────┬───────┘   └──────────────┘             │
 │         │                                        │
 │  ┌──────▼───────┐                                │
 │  │  PostgreSQL  │  managed DB (private network)  │
 │  └──────────────┘                                │
 └──────────────────────────────────────────────────┘
```

**3 services total (no reverse proxy):**
1. **PostgreSQL** — Managed database (one-click provision)
2. **Backend** — FastAPI + Uvicorn, publicly exposed (from `/backend`)
3. **Frontend** — Static Vite build served by Caddy, publicly exposed (from `/frontend`)

Both backend and frontend have their own public Railway domains. The frontend makes API calls directly to the backend's public URL via `VITE_API_BASE_URL`.

---

## Prerequisites

- A [Railway account](https://railway.com) (Hobby plan recommended, $5/month base)
- Your code pushed to a **GitHub repository**
- Your **Anthropic API key** (`sk-ant-...`)
- A **Clerk** application (for authentication)
- A **Stripe** account (for billing)

---

## Step 1 — Create the Railway Project

1. Go to [railway.com/dashboard](https://railway.com/dashboard)
2. Click **"+ New Project"** > **"Empty Project"**
3. Name it `ide-ai`

---

## Step 2 — Provision PostgreSQL

1. Inside your project, click **"+ New"** > **"Database"** > **"PostgreSQL"**
2. Railway instantly provisions a Postgres 15 instance
3. Note that `DATABASE_URL` is automatically generated

---

## Step 3 — Deploy the Backend

1. Click **"+ New"** > **"GitHub Repo"** > select your Ide/AI repository
2. Go to **Settings**:

| Setting | Value |
|---------|-------|
| **Root Directory** | `/backend` |
| **Config File Path** | `/backend/railway.toml` |
| **Watch Paths** | `/backend/**` |

3. Go to **Settings** > **Networking** > **"Generate Domain"** to get a public URL
4. Go to **Variables** and add the required variables (see table below)
5. Click **"Deploy"**

Railway will build the Docker image, run `alembic upgrade head` (pre-deploy), and start Uvicorn.

---

## Step 4 — Deploy the Frontend

1. Click **"+ New"** > **"GitHub Repo"** > select the **same repo**
2. Go to **Settings**:

| Setting | Value |
|---------|-------|
| **Root Directory** | `/frontend` |
| **Config File Path** | `/frontend/railway.toml` |
| **Watch Paths** | `/frontend/**` |

3. Go to **Settings** > **Networking** > **"Generate Domain"** to get a public URL
4. Go to **Variables** and add `VITE_API_BASE_URL` and `VITE_CLERK_PUBLISHABLE_KEY` (see table below)
5. Click **"Deploy"**

---

## Step 5 — Verify

1. Open the frontend public URL — you should see the landing page
2. Test the backend health endpoint: `https://<backend-domain>/api/v1/health`
3. Try signing in and creating a project

---

## Environment Variables Reference

### Backend Service (required)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` — Railway reference syntax |
| `ANTHROPIC_KEY` | Claude API key for AI features |
| `CLERK_SECRET_KEY` | Clerk backend secret key |
| `CLERK_WEBHOOK_SECRET` | Webhook signing secret from Clerk dashboard |
| `STRIPE_SECRET_KEY` | Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | Webhook signing secret from Stripe dashboard |
| `STRIPE_PRICE_BASIC_MONTHLY` | Stripe price ID for Basic monthly plan |
| `STRIPE_PRICE_BASIC_YEARLY` | Stripe price ID for Basic yearly plan |
| `STRIPE_PRICE_PRO_MONTHLY` | Stripe price ID for Pro monthly plan |
| `STRIPE_PRICE_PRO_YEARLY` | Stripe price ID for Pro yearly plan |
| `FRONTEND_URL` | Public URL of the frontend service (e.g. `https://frontend-production-xxxx.up.railway.app`) |
| `CORS_ORIGINS` | JSON array with the frontend URL (e.g. `["https://frontend-production-xxxx.up.railway.app"]`) |

### Backend Service (recommended)

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Set to `production` |
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | Anthropic model to use |
| `INBOX_DOMAIN` | — | Domain for inbound email addresses |
| `RESEND_API_KEY` | — | Resend API key for outbound email |
| `RESEND_WEBHOOK_SECRET` | — | Inbound email webhook HMAC secret |
| `REDIS_URL` | — | Redis connection string for realtime inbox SSE |
| `CLERK_ISSUER` | — | Expected JWT issuer for production hardening |
| `CLERK_AUTHORIZED_PARTIES` | — | Expected JWT audience for production hardening |
| `SHARE_ACCESS_SECRET` | — | Secret for generating share access tokens |
| `INTEGRATION_TOKEN_KEY` | — | Fernet key for encrypting OAuth tokens |

### Frontend Service

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Full public backend URL + `/api/v1` (e.g. `https://backend-production-xxxx.up.railway.app/api/v1`) |
| `VITE_CLERK_PUBLISHABLE_KEY` | Clerk publishable key for frontend auth |

> **Important:** `VITE_*` variables are baked into the JS bundle at build time. Changing them requires a redeploy.

---

## Database Migrations

Migrations run **automatically** on every deploy via `railway.toml`:

```toml
[deploy]
preDeployCommand = "alembic upgrade head"
```

This runs after the Docker image builds but before the new container replaces the old one. If the migration fails, the deploy is rolled back.

---

## Troubleshooting

### Backend can't connect to Postgres
- Ensure `DATABASE_URL` uses `${{Postgres.DATABASE_URL}}` (reference syntax)
- Railway's private network is IPv6-only; the backend config handles the `postgresql://` to `postgresql+asyncpg://` scheme swap

### Frontend shows blank page or API errors
- Verify `VITE_API_BASE_URL` points to the backend's **public** domain (not private), including the `/api/v1` suffix
- Verify `CORS_ORIGINS` on the backend includes the frontend's public URL

### CORS errors
- Since backend and frontend have separate public domains, CORS is required
- Set `CORS_ORIGINS` on the backend to `["https://<frontend-domain>"]`

### Deploy fails at migration step
- Check the deploy logs for the `preDeployCommand` output
- Common: `DATABASE_URL` scheme mismatch — handled in `config.py`

---

## Files Used by Railway

```
Ide_AI/
├── backend/
│   ├── Dockerfile         ← Multi-stage production build
│   └── railway.toml       ← Build + deploy config (pre-deploy: alembic)
└── frontend/
    ├── Dockerfile         ← Multi-stage build → Caddy static server
    ├── Caddyfile          ← SPA routing + caching headers
    └── railway.toml       ← Build + deploy config
```
