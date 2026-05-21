# Ide/AI Frontend

React + TypeScript SPA for the Ide/AI pre-builder planning platform.

## Stack

- React 19.2, TypeScript, Vite 7.3
- Tailwind CSS v4 (CSS-based config, no `tailwind.config.js`)
- Framer Motion (animations, page transitions)
- Zustand (client state) + Axios (API client)
- Clerk (`@clerk/clerk-react`) for authentication
- Stripe (checkout redirect, billing portal link)

## Getting Started

```bash
npm install
npm run dev
```

Requires a running backend at the URL specified by `VITE_API_BASE_URL`.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_CLERK_PUBLISHABLE_KEY` | Clerk frontend publishable key | *(required)* |
| `VITE_API_BASE_URL` | Backend API base URL | `/api/v1` |
| `VITE_STRIPE_PUBLISHABLE_KEY` | Stripe frontend publishable key | *(required for billing)* |

## Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start Vite dev server (port 5173) |
| `npm run build` | Production build (`tsc -b && vite build`) |
| `npm run preview` | Preview production build locally |
| `npm run lint` | Run ESLint |

## Project Structure

```
src/
  pages/           # Route-level page components
  components/      # Reusable UI components (layout, ui, sharing, tutorial, etc.)
  stores/          # Zustand stores (authStore, pathwayStore, modulePathwayStore, tutorialStore)
  hooks/           # Custom React hooks (useSSE, useVoiceInput)
  lib/             # Utilities (apiClient, extractError, categories, exportUtils)
  types/           # TypeScript interfaces
  styles/          # Tailwind v4 CSS globals
```

## Design System

- Dark glassmorphism theme (`#0d0d12` background, `bg-white/5` cards, `backdrop-blur`)
- Accent: electric cyan `#00E5FF`
- Typography: Arial (body), JetBrains Mono (code/prompts)
- Cards: 12px radius, glass border, hover `scale-[1.02]`
- Responsive: sidebar collapses to bottom nav on <768px

## Deployment

Deployed to Railway as a static site served by Caddy. Auto-deploys on push to `main`.
