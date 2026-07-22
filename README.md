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

```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# Docs: http://localhost:8000/docs
```

The Android emulator reaches the host backend at `http://10.0.2.2:8000/v1` (already set in `frontend/src/api/config.ts`).

## Implemented in this milestone

- Design system (light/dark), shared component library, navigation, Redux + persistence.
- Screens from the approved Stitch designs: **Splash, Onboarding (Target Band), Home Dashboard, Speaking Interview, Writing Feedback**, plus **Login / Register / Forgot Password** and tab placeholders (Practice, Progress, Coach, Profile).
- Backend scaffold: health, auth (stub), dashboard overview, correlation-id + error middleware, camelCase responses matching the frontend types.
