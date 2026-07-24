# AI IELTS Tutor — Remaining Tasks

Everything **not yet completed** to finish the project, organized by area. Checked = done, unchecked = remaining. Use this as the living backlog.

> Current overall completion ≈ **10–12%**. Built so far: frontend design system, navigation, Redux, mock API, and 5 UI screens (Splash, Onboarding Target-Band, Home, Speaking UI, Writing Feedback) + Auth + tab placeholders, plus a backend scaffold.

---

## 0. Project Setup & Tooling (blocking)

- [ ] Run `npm install` in `frontend/` (deps are declared but not installed)
- [ ] iOS: `cd ios && pod install`
- [ ] Add Plus Jakarta Sans + Inter `.ttf` files to `src/assets/fonts` and run `npx react-native-asset`
- [ ] Run `tsc --noEmit` and fix any type errors surfaced after install
- [ ] Configure ESLint + Prettier scripts and run a clean lint pass
- [ ] Verify the app boots on Android emulator and iOS simulator
- [ ] Add `react-native-config` (or equivalent) so `.env` is actually read by the app
- [ ] Set up absolute imports / path aliases (`@components`, `@constants`, …) in `tsconfig` + Babel

---

## 1. Frontend — Screens (UI + `use*` hook per screen)

### Onboarding (only Target-Band step exists)
- [ ] Welcome / value-proposition carousel
- [ ] Sign-up entry step
- [ ] Exam type selection (Academic / General)
- [ ] Current level selection (Beginner / Intermediate / Advanced)
- [ ] Exam date picker
- [ ] Daily study-time selection
- [ ] Consent screen (voice recording + AI processing)
- [ ] Adaptive placement diagnostic runner (all 4 modules)
- [ ] Baseline results + CEFR + "generating plan" screen
- [ ] Wire full onboarding flow into navigation (multi-step stack)

### Speaking (only mock UI exists)
- [ ] Session start screen (full interview vs single part, mic permission)
- [ ] Part 1 real flow
- [ ] Part 2 cue-card screen (60s prep + ≤120s speak timers)
- [ ] Part 3 discussion flow
- [ ] Feedback screen (band + 4 criteria + highlighted transcript + replay)
- [ ] Speaking history list
- [ ] Recording replay with jump-to-issue markers

### Writing (only Feedback screen exists)
- [ ] Task selection (Task 1 / Task 2, Academic vs General)
- [ ] Prompt display (with chart/image asset for Task 1 Academic)
- [ ] Essay editor (rich text, live word count, timer, submit)
- [ ] Submission → scoring pending/loading state
- [ ] Writing history with band trend + diffs

### Reading (not started)
- [ ] Difficulty selection
- [ ] Passage + question runner (MCQ, True/False/Not Given, Matching Headings)
- [ ] Question navigator + timer
- [ ] Result screen: raw score → band, per-question AI explanations

### Listening (not started)
- [ ] Difficulty selection
- [ ] Audio player (single-play / replay policy) + question runner
- [ ] Instant feedback with answer timestamps
- [ ] Result screen: raw score → band

### AI Tutor / Learning (not started)
- [ ] Daily Coach feed (message + recommendations)
- [ ] Vocabulary builder (spaced-repetition flashcards)
- [ ] Grammar tutor (lesson list + lesson detail)
- [ ] Full Mock Test flow (4 modules, timed, assembled, scored) + readiness report

### Progress / Analytics (placeholder only)
- [ ] Band trend charts (per module, line)
- [ ] Radar chart of 4 modules
- [ ] Improvement velocity + predicted exam-day band with confidence
- [ ] Consistency / streak / time-on-task
- [ ] Learning insights (strengths/weaknesses) cards

### Profile / Settings (basic version only)
- [ ] Editable goals / target band / exam date / daily minutes (triggers replan)
- [ ] Notification & reminder scheduling
- [ ] Consent management
- [ ] Data export + delete account (privacy)
- [ ] Offline mode banner + sync status UI

---

## 2. Frontend — Components (remaining)

- [ ] Line chart / trend chart component
- [ ] Radar chart (4-module) component
- [ ] Waveform recorder / live audio visualizer
- [ ] Audio player with scrubber + speed control
- [ ] Question components (MCQ, True/False/Not-Given segmented, Matching Headings drag-connect)
- [ ] Flashcard (flip) component
- [ ] Cue-card component
- [ ] Countdown / timer component
- [ ] Toast / Snackbar
- [ ] Bottom sheet / modal
- [ ] Consent modal
- [ ] Empty / error / offline state components
- [ ] Skeleton loaders
- [ ] Streak flame (animated) + progress ring (SVG)

---

## 3. Frontend — State, API & Infra

- [ ] Redux slices for: speaking, writing, reading, listening, planner, analytics, vocabulary, coach, offline
- [ ] RTK Query (or thunks) for all real endpoints
- [ ] Replace mock API (`useMock`) wiring with real backend calls
- [ ] Token refresh flow (interceptor: 401 → refresh → retry / logout)
- [ ] Secure token storage (Keychain/Keystore) instead of plain AsyncStorage
- [ ] Offline queue + deferred sync + conflict resolution
- [ ] Push notifications / reminders integration
- [ ] Error boundary + global error/toast handling
- [ ] Accessibility pass (labels, dynamic type, contrast) + localization (i18n) setup

---

## 4. Backend — Foundation

- [x] Pydantic `Settings` (env-driven config) + `.env` loading
- [x] Async SQLAlchemy engine + session (Supabase PostgreSQL / SQLite dev)
- [x] Alembic migrations setup (async env) + initial schema migration (users, refresh_tokens, learner_profiles) — extend as new models land
- [ ] Repository layer (base + per-aggregate repos)
- [x] Service/use-case logic + dependency injection (auth) — extend to other domains
- [x] Unit-of-Work / transaction handling (request-scoped commit/rollback)
- [ ] Structured logging + correlation propagation (extend middleware)
- [x] Rate limiting (in-memory fixed-window on auth + AI endpoints, 429 problem+json + Retry-After) — [ ] Redis backing for multi-instance
- [ ] Redis integration (cache + queue)
- [ ] Background job runner (Celery/arq) + task definitions
- [ ] Full exception taxonomy + handlers (extend current RFC 7807)

---

## 5. Backend — Auth & Security

- [x] Real user registration (Argon2id hashing)
- [x] JWT access token issuance + verification
- [x] Refresh token storage + rotation — [ ] full reuse-detection family revocation
- [x] RBAC dependencies (`require_roles`) — [ ] own-resource checks
- [x] Password policy (strength) + email/name field validation — [ ] login rate limiting / lockout
- [x] `/auth/me`, `/auth/refresh`, `/auth/logout` endpoints
- [x] Audit logging for admin actions (`audit_logs` table, written on user changes)
- [x] Input validation hardening (field validators + RFC 7807 problem+json contract with correlation IDs) — [ ] TLS/secrets management

---

## 6. Backend — Domain Endpoints

- [x] Onboarding submit + profile GET/PATCH — [ ] adaptive diagnostic + baseline computation
- [ ] Planner: generate/adapt study plans + tasks
- [x] Speaking: transcript AI scoring (4 criteria, rubric-as-code) + history — [ ] session creation (LiveKit token), finish
- [x] Writing: submission, AI scoring, improved essay (POST/GET attempts) + history — [ ] prompt delivery
- [x] Reading (backend): passage/question delivery (no answer leak), auto-grading, raw→band mapping, per-question explanations — [ ] AI question generation
- [x] Listening (backend): clip/question delivery (no answer leak), auto-grading, band mapping, per-question feedback with audio timestamps — [ ] AI question generation, signed audio URLs
- [x] Analytics: progress + band prediction + **real dashboard overview** (greeting, streak, prediction, module levels, recommendations) — [ ] insights
- [ ] Vocabulary (SRS) + grammar lesson endpoints
- [ ] Mock test assembly + scoring
- [ ] Notifications / reminders

---

## 7. AI Layer

- [x] `LLMProvider` port (provider-agnostic abstraction) + offline mock provider
- [x] Groq provider adapter (OpenAI-compatible via httpx)
- [x] AI orchestrator (Writing scoring) — [ ] full multi-task routing policy
- [ ] Prompt registry (versioned templates) per module — partial (Writing rubric prompt exists)
- [x] Rubric-as-code scoring schemas (Writing + Speaking)
- [x] Structured-output validation (Pydantic) — [ ] bounded self-repair
- [ ] AI memory / weakness model (store + retriever + updater)
- [ ] Adaptive difficulty controller (EMA + severity decay)
- [x] Band predictor (transparent heuristic: weekly velocity + projection + confidence)
- [ ] Question/passage/audio generation
- [x] AI usage logging: `ai_interactions` table (provider/model/tokens/latency/cost) written on every scoring call
- [ ] Offline eval harness (gold-set MAE gate)
- [ ] Future adapters scaffolding (LangGraph / CrewAI / AutoGen / OpenAI / Gemini / Claude)

---

## 8. Voice Pipeline (not started)

- [ ] LiveKit server integration + room/token minting
- [ ] Server-side voice agent (examiner loop)
- [ ] STT provider port + adapter (streaming)
- [ ] TTS provider port + adapter (streaming)
- [ ] Barge-in / VAD handling
- [ ] Part state machine (Greeting → Part1 → Part2 → Part3 → Scoring)
- [ ] Recording storage (object store, signed URLs) + transcript alignment
- [ ] React Native LiveKit client integration + mic/audio session handling

---

## 9. Admin Panel (not started)

- [ ] Admin auth + dashboard overview (KPIs)
- [x] User management: list (paginated + search), suspend/reactivate, role assignment (privileged roles super-admin-gated), audit-logged
- [ ] Content management: passages, audio, questions, cue cards, writing prompts, vocabulary, grammar lessons (CRUD + versioning)
- [ ] Platform analytics & reports
- [x] AI usage monitoring endpoint `GET /admin/ai-usage` (tokens, cost, latency, error rate, by-model) — [ ] budget alerts
- [ ] Subscription/plan management (future, feature-flagged)

---

## 10. Data & Storage

- [ ] Implement full PostgreSQL schema (SRS §15) via migrations
- [ ] Object storage (S3-compatible) for recordings/audio + signed URLs
- [ ] Seed content scripts (passages, audio, questions, vocab, grammar)
- [ ] Indexes, partitioning (attempts, ai_interactions), retention jobs
- [ ] Backups / PITR configuration

---

## 11. Testing

- [ ] Frontend unit tests (reducers, selectors, hooks, utils) — Jest
- [ ] Frontend component tests — React Native Testing Library
- [ ] Frontend E2E — Detox
- [ ] Backend unit tests (services, repos, validators) — pytest
- [x] Backend integration smoke suites (TestClient + SQLite) for all verticals, run in isolated processes via `tests/run_smoke.py` — [ ] broaden to pytest unit tests + Postgres/testcontainers
- [ ] AI evaluation suite (rubric MAE vs gold set)
- [ ] Voice pipeline tests (latency budget, FSM, barge-in)
- [ ] Load tests (k6/Locust) against SLOs
- [ ] Security tests (authz, injection, rate limits)

---

## 12. DevOps / Infra

- [ ] Dockerfiles (api, worker, voice) + docker-compose (local)
- [ ] Environment configs (dev/staging/prod)
- [x] CI: backend compile + Alembic up/down + smoke suites on every push/PR (GitHub Actions) — [ ] frontend typecheck/build, lint, deploy stages
- [ ] Observability: metrics (Prometheus), tracing (OpenTelemetry), dashboards + alerts
- [ ] Health/readiness probes wired to real dependencies
- [ ] Kubernetes manifests / Helm (future)
- [ ] Secrets management integration
- [ ] Crash reporting (Sentry) + analytics events

---

## 13. Compliance & Polish

- [ ] Consent capture + enforcement (voice + AI)
- [ ] Data export + account deletion (GDPR-style)
- [ ] "Scores are estimates" disclaimers in UI
- [ ] App store assets (icons, splash, screenshots, privacy policy)
- [ ] Performance tuning (cold start, list virtualization, memoization)
- [ ] Dark-mode QA across all screens
- [ ] Final accessibility (WCAG 2.1 AA) audit

---

### Suggested next milestone (highest impact)
1. Backend foundation: Settings + Supabase Postgres + SQLAlchemy + Alembic + real JWT auth.
2. One full vertical end-to-end — **Writing**: editor → submit → Groq scoring (rubric-as-code) → feedback — to prove the AI + provider-abstraction architecture.
3. Then replicate the pattern for Reading/Listening, and build out Speaking voice.
