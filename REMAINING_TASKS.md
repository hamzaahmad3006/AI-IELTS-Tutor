# AI IELTS Tutor — Remaining Tasks

Everything **not yet completed** to finish the project, organized by area. Checked = done, unchecked = remaining. Use this as the living backlog.

> **Status as of PR #40** — **69 of 174 checklist items done (~40%)**; weighted by effort the product is roughly **45%**, since the backend and data layer are largely complete while the remaining items skew toward large features (voice, deployment).
> **Working end-to-end:** register → onboarding → dashboard → all four practice modules (Reading, Listening, Writing, Speaking) → progress → coach → profile → logout, against the real backend.
> **Verified by:** 15 backend smoke suites, a 13-step E2E user-journey check, frontend `tsc`, and a Docker image build — all four gates run in CI on every push.
> **Biggest remaining:** the live voice (LiveKit) pipeline, on-device validation, AI content generation, and production deployment.

---

## 0. Project Setup & Tooling

- [x] `npm install` in `frontend/` (lockfile committed; `npm ci` reproducible in CI)
- [x] `tsc --noEmit` clean (0 errors) and enforced by the CI frontend job
- [x] **App bundles for release on both platforms** (`npm run bundle:android` / `bundle:ios`, ~1.79 MB each) — proves every import resolves; enforced in CI
- [x] Platform-aware API base URL (Android `10.0.2.2`, iOS `localhost`) with a single documented override point
- [ ] iOS: `cd ios && pod install`
- [ ] Add Plus Jakarta Sans + Inter `.ttf` files to `src/assets/fonts` and run `npx react-native-asset`
- [ ] Configure ESLint + Prettier scripts and run a clean lint pass
- [ ] **Verify the app boots on an Android emulator / iOS simulator** ← main outstanding validation
- [ ] Add `react-native-config` (or equivalent) so `.env` is actually read by the app
- [ ] Set up absolute imports / path aliases (`@components`, `@constants`, …) in `tsconfig` + Babel

---

## 1. Frontend — Screens (UI + `use*` hook per screen)

### Onboarding (flow complete, submits to the real backend)
- [x] Target-band step (slider, band labels, AI recommendation)
- [x] Exam type selection (Academic / General)
- [x] Current level selection (Beginner / Intermediate / Advanced)
- [x] Daily study-time selection
- [x] Consent (AI processing required, voice optional)
- [x] Submits the full draft to `POST /onboarding`, then enters the app shell
- [x] Wired into navigation (Splash → Auth → Register → Onboarding → Main)
- [ ] Welcome / value-proposition carousel
- [ ] Exam date picker (currently carried in the draft, not user-set in the UI)
- [ ] Adaptive placement diagnostic runner (all 4 modules)
- [ ] Baseline results + CEFR + "generating plan" screen

### Speaking (AI-scored practice built; live voice pipeline pending)
- [x] Part 2 cue-card practice: real cue card from the backend bank, prep → speak timers driven by the card, response capture
- [x] AI scoring result (band + 4 criteria bars + examiner feedback)
- [ ] Session start screen (full interview vs single part, mic permission)
- [ ] Part 1 and Part 3 flows
- [ ] Highlighted transcript + recording replay with jump-to-issue markers
- [x] Speaking history (shown in the unified History screen)

### Writing (practice + feedback built)
- [x] Prompt delivered from the backend prompt bank (random within difficulty)
- [x] Essay editor (multiline, live word count, submit) + AI-scored result (band, 4 criteria, feedback, improved essay)
- [x] Submission → scoring pending/loading state
- [ ] Task selection UI (Task 1 vs Task 2, Academic vs General)
- [ ] Task 1 chart/image assets
- [ ] Writing timer
- [x] Writing history (unified History screen) — [ ] band-trend chart + essay diffs

### Reading (built)
- [x] Passage + question runner (MCQ / True-False-Not-Given / short answer)
- [x] Result screen: raw score → band + per-question correctness & explanations
- [x] Adaptive difficulty (server-resolved) + randomized passage selection
- [ ] Explicit difficulty selection UI
- [ ] Question navigator + timer
- [ ] Matching-headings drag UI

### Listening (built)
- [x] Clip delivery + question runner with answer capture
- [x] Result screen: raw score → band + per-question feedback with **audio timestamps**
- [x] Adaptive difficulty + randomized clip selection
- [ ] **Real audio playback** (player UI + state exist; native media playback pending)
- [ ] Explicit difficulty selection UI + single-play/replay policy enforcement

### AI Tutor / Learning
- [x] Daily Coach feed (message + weakness-driven recommendations that tap through to practice)
- [ ] Vocabulary builder (spaced-repetition flashcards)
- [ ] Grammar tutor (lesson list + lesson detail)
- [ ] Full Mock Test flow (4 modules, timed, assembled, scored) + readiness report

### Progress / Analytics (built — real data)
- [x] Progress screen: overall band, predicted band + confidence, per-module bands, focus areas
- [x] Coach screen: recommendations (tap-through) + adaptive level per module
- [x] Practice hub: module launcher with adaptive difficulty badges
> All five tabs are now real screens (no placeholders remain).
- [ ] Band trend charts (per module, line)
- [ ] Radar chart of 4 modules
- [ ] Improvement velocity + predicted exam-day band with confidence
- [ ] Consistency / streak / time-on-task
- [ ] Learning insights (strengths/weaknesses) cards

### Profile / Settings (real profile data)
- [x] Loads the real profile; editable **target band** and **daily study time** (PATCHed to the backend)
- [x] Shows exam type / exam date / CEFR + per-module starting levels (baselines)
- [x] Theme toggle + server-side logout (refresh token revoked)
- [ ] Exam-date editing + replan trigger
- [ ] Notification & reminder scheduling
- [ ] Consent management screen
- [ ] Data export + delete account (privacy)
- [ ] Offline mode banner + sync status UI

---

## 2. Frontend — Components (remaining)

- [ ] Line chart / trend chart component
- [ ] Radar chart (4-module) component
- [ ] Waveform recorder / live audio visualizer
- [ ] Audio player with scrubber + speed control
- [x] Question rendering (MCQ / True-False-Not-Given radio options + short-answer input) — [ ] Matching Headings drag-connect
- [x] Cue-card rendering (topic, prompt, bullet points)
- [x] Countdown / timer (Speaking prep + speak phases)
- [ ] Flashcard (flip) component
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
- [x] **Full API layer live-verified** against the backend — auth, onboarding/profile, `/me`, dashboard, analytics, and all four modules
- [x] **Mock data can never reach a release build** (`useMock` is gated on `__DEV__`, guarded by a test). Dev still defaults to fixtures via `USE_MOCK_IN_DEV` — [ ] set it to false once a backend is routinely running
- [ ] Tree-shake fixture data out of release bundles (currently ~11.5 KB / 0.66% of the bundle ships unused but is never served)
- [x] Token refresh flow (single-flight 401 → refresh → retry; server logout via `logoutThunk`) — verified against a live backend — [ ] wire remaining screens off mock
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
- [x] Speaking: transcript AI scoring (4 criteria, rubric-as-code) + history + **cue-card bank** (`GET /speaking/cue-cards`) — [ ] session creation (LiveKit token), finish
- [x] Writing: submission, AI scoring, improved essay (POST/GET attempts) + history + **prompt bank** (`GET /writing/prompts`)
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
- [x] Adaptive difficulty resolver (recent-band → easy/medium/hard, wired into Reading/Listening delivery) + weakness-driven recommendations (`/me/adaptive-difficulty`, `/me/recommendations`)
- [x] AI orchestrator (Writing scoring) — [ ] full multi-task routing policy
- [ ] Prompt registry (versioned templates) per module — partial (Writing rubric prompt exists)
- [x] Rubric-as-code scoring schemas (Writing + Speaking)
- [x] Structured-output validation (Pydantic) — [ ] bounded self-repair
- [x] AI weakness memory: record from scored attempts (rising severity + decay), `GET /me/weaknesses` by priority — [ ] semantic (pgvector) retriever
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
- [x] Content management: reading passages + questions CRUD (audit-logged, RBAC content_editor/admin) — [ ] audio, cue cards, writing prompts, vocabulary, grammar lessons; versioning
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

- [x] Frontend unit tests — Jest in CI (band-scale logic, auth slice, onboarding slice). `npm test` was broken (missing `@react-native/jest-preset`) and is now fixed — [ ] broaden to hooks/selectors/utils
- [x] **Every screen has a render test** (React Native Testing Library): auth (3, incl. validation interactions), all 4 practice screens, all 5 dashboard tabs + History, plus the full app tree — 38 tests / 7 suites in CI
- [ ] Frontend E2E — Detox
- [ ] Backend unit tests (services, repos, validators) — pytest
- [x] Backend integration smoke suites (TestClient + SQLite) for all verticals, run in isolated processes via `tests/run_smoke.py` — [ ] broaden to pytest unit tests + Postgres/testcontainers
- [x] **E2E user-journey check** (`tests/journey/journey_check.js`) — 13 steps in the app's screen order, content-agnostic, run in CI
- [x] Frontend typecheck gate (`tsc --noEmit`) in CI
- [ ] AI evaluation suite (rubric MAE vs gold set)
- [ ] Voice pipeline tests (latency budget, FSM, barge-in)
- [ ] Load tests (k6/Locust) against SLOs
- [ ] Security tests (authz, injection, rate limits)

---

## 12. DevOps / Infra

- [x] Dockerfile (api, multi-stage, non-root) + docker-compose (API + Postgres) + CI image build & health check — [ ] worker/voice images
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

1. **Run the app on a device/emulator** (`cd frontend && npm install && npm run android`) and fix whatever surfaces. Everything is typecheck- and contract-verified, but **nothing has been rendered on a device yet** — this is the single biggest unknown.
2. **Flip `API_CONFIG.useMock` to `false`** (point `baseUrl` at the running backend) so the app uses live data by default.
3. **Real audio playback** for Listening (the player UI/state exist; native media playback is missing).
4. **Remaining screens**: Writing/Speaking history, Vocabulary, Grammar, Mock Test.
5. **Voice pipeline** (LiveKit + STT/TTS) — the largest single remaining feature.
6. **Production**: deploy (Docker image is CI-built), Postgres/Supabase config, observability, secrets.

### Known gaps worth stating plainly
- The app has **never been run on a device or emulator** in this environment. Verification is: `tsc`, a **release bundle build for Android + iOS** (all imports resolve), live API contract checks, and an E2E journey against the real backend. Rendering and native behaviour remain unverified.
- Listening has **no real audio playback** yet — questions are answerable, the clip does not play.
- Speaking is **transcript-based**, not live voice.
- AI scoring runs through the **offline mock provider** unless `GROQ_API_KEY` is set.
