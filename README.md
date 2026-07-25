# AI IELTS Tutor

AI-powered IELTS preparation platform. Monorepo with a **React Native (CLI, TypeScript)** mobile app and a **FastAPI (Python)** backend, persisting to **Supabase PostgreSQL** (used only as Postgres). See `AI_IELTS_Tutor_SRS.md` for the full specification.

## Repository layout

```
AI IELTS Tutor/
├── frontend/            # React Native mobile app
│   └── src/
│       ├── api/         # axios client, endpoints, typed mock fixtures
│       ├── assets/      # images (logo) + fonts
│       ├── AppNavigation/ # Root / Auth / Onboarding / MainTab navigators
│       ├── components/  # shared UI (AppText, Button, Card, BandBadge, Icon, ...)
│       ├── constants/   # design system: colors, typography, spacing, theme, icons
│       ├── redux/       # store + slices (auth, onboarding, dashboard, theme)
│       ├── screens/     # feature folders, each: Screen.tsx + useScreen.ts
│       └── types/       # all TypeScript interfaces
├── backend/             # FastAPI backend
│   ├── main.py
│   ├── routes/          # HTTP layer
│   ├── controllers/     # business logic + schemas
│   └── middleware/      # correlation-id + RFC 7807 errors
└── AI_IELTS_Tutor_SRS.md
```

## Architecture rules

- **UI / logic separation:** every screen has `Screen.tsx` (UI only) + `useScreen.ts` (state, API calls, validation, business logic).
- **Design tokens only:** screens import colors/fonts/spacing from `src/constants` — never hardcoded.
- **Strict TypeScript:** no `any`/`unknown` except unavoidable cases (e.g. `catch` error normalization).
- **Provider-agnostic backend:** AI access will flow through an `LLMProvider` port (see SRS §19).

## Frontend — run

```bash
cd frontend
npm install                 # installs navigation, redux, svg, gradient, etc.
# iOS only:
cd ios && pod install && cd ..
# Fonts (Plus Jakarta Sans + Inter): drop .ttf files in src/assets/fonts, then:
npx react-native-asset

npm start                   # Metro
npm run android             # or: npm run ios
```

> The app runs against **typed mock data** out of the box (`API_CONFIG.useMock = true` in `src/api/config.ts`). Flip it to `false` to hit the FastAPI backend.

## Backend — run

Runs on SQLite with zero config (see [backend/README.md](backend/README.md) for full details):

```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# Docs: http://localhost:8000/docs   Health: http://localhost:8000/health
```

Or with Docker (API + PostgreSQL):

```bash
docker compose up --build
```

Common tasks are wrapped in the root `Makefile` (`make help`, `make test`, `make run`, `make migrate`, `make docker-up`). The Android emulator reaches the host backend at `http://10.0.2.2:8000/v1` (set in `frontend/src/api/config.ts`).

## Status

**Backend** — substantially built and covered by CI (compile → migrations → smoke suites → Docker build/health):

- Auth (JWT access + rotating refresh, RBAC), onboarding & profile
- All four modules: **Writing & Speaking** AI-scored (rubric-as-code, provider-agnostic `LLMProvider` → Groq or offline mock); **Reading & Listening** auto-graded with band mapping; per-module history (cursor pagination)
- **Weakness memory** (rising severity + decay), **adaptive difficulty**, and weakness-driven **recommendations**
- **Analytics**: per-module progress + band prediction; real **dashboard overview**
- **Admin**: user management + AI-usage monitoring + reading-content CRUD (audit-logged)
- Validation + RFC 7807 error contract, rate limiting, correlation IDs, Dockerized, GitHub Actions CI

**Frontend** — design system + navigation + Redux, and 5 approved Stitch screens (Splash, Onboarding Target-Band, Home, Speaking, Writing Feedback) + Auth + tab stubs, currently on **mock data** (`API_CONFIG.useMock = true`). Wiring to the live backend and the remaining screens are the main outstanding work.

The full, continuously-updated backlog is in [REMAINING_TASKS.md](REMAINING_TASKS.md).
