# ────────────────────────────────────────────────────────────────
# Ide/AI Frontend — Production Dockerfile (Railway-ready)
# Multi-stage build: npm build → Caddy static server
# ────────────────────────────────────────────────────────────────

# ── Stage 1: Build static assets ──
# Node 24 LTS (supported to April 2028). Node 20 reached end of life in April 2026.
# CI's frontend job uses the same major (.github/workflows/ci.yml).
FROM node:24-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# VITE_API_BASE_URL is baked in at build time.
# Set to your backend's public URL, e.g. https://your-backend.up.railway.app/api/v1
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

ARG VITE_CLERK_PUBLISHABLE_KEY
ENV VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PUBLISHABLE_KEY

RUN npm run build

# ── Stage 2: Serve with Caddy ──
FROM caddy:2-alpine

COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=builder /app/dist /srv

# Railway injects $PORT at runtime
ENV PORT=3000
