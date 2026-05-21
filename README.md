# Ide/AI

Pre-builder planning platform. Describe a rough idea, go through AI-guided discovery, and walk away with a structured design kit: prioritized feature breakdown, tech stack recommendation, platform-specific prompts, and exportable documentation.

## Why

People waste credits, time, and money figuring out *what* to build inside metered platforms (Bubble, Cursor, Claude Code, Bolt, etc.) when that planning should happen beforehand.

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, PostgreSQL |
| Frontend | React 19.2, TypeScript, Vite 7.3, Tailwind CSS v4, Framer Motion, Zustand |
| Auth | Clerk (Google/Microsoft/GitHub OAuth + email/password) |
| Billing | Stripe (checkout sessions, billing portal, webhook sync) |
| AI | Anthropic Claude (claude-sonnet-4-6), SSE streaming |
| Export | fpdf2 (PDF), python-docx (DOCX), Jinja2, ZIP |
| Deploy | Railway (2 services: backend + frontend) |

## Local Development

### Backend
```bash
cd backend
pip install -e ".[dev]"
cp .env.example .env  # Fill in required env vars
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

See `CONTEXT_HANDOFF.md` for the full list. At minimum:
- `DATABASE_URL` — PostgreSQL connection string
- `ANTHROPIC_KEY` — Claude API key
- `CLERK_SECRET_KEY` — Clerk backend secret
- `CLERK_WEBHOOK_SECRET` — Clerk webhook signing secret
- `STRIPE_SECRET_KEY` — Stripe backend secret
- `VITE_CLERK_PUBLISHABLE_KEY` — Clerk frontend key
- `VITE_API_BASE_URL` — Backend API base (defaults to `/api/v1`)

## Project Documentation

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Claude Code session instructions (read first) |
| `CONTEXT_HANDOFF.md` | Session handoff context with current state |
| `ARCHITECTURE.md` | Directory structure, schema, design decisions |
| `AI_PARTNER_SELECTOR_SPEC.md` | AI partner style specification |

## Deployment

Both services deploy to Railway on push to `main`. See `DEPLOYMENT_RAILWAY.md` for configuration details.
