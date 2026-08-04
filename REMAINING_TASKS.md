# AI IELTS Tutor — Remaining Tasks

Everything **not yet completed** to finish the project, organized by area. Checked = done, unchecked = remaining. Use this as the living backlog.

> **Status as of PR #71** — **134 of 192 checklist items done (~70%)**. Weighted by
> effort it is further along than that, since the backend and data layer are largely
> complete while most remaining items are large features (live voice, deployment) or
> are blocked on native modules.
> **Running on real infrastructure:** live Supabase PostgreSQL 17.6 and the real Groq
> API, verified on a physical Android phone — register → onboarding → dashboard → all
> four practice modules → progress → coach → profile → logout.
> **Verified by:** 27 backend smoke suites, a 13-step E2E user-journey check, 170
> frontend tests, ESLint at zero warnings, Prettier, `tsc --noEmit`, and a Docker image
> build — all gated in CI on every push.
> **Biggest remaining:** the live voice (LiveKit) pipeline, native audio playback,
> secure token storage, production deployment, and iOS — all of which need hardware,
> a native rebuild, or hosting to verify.

---

## 0. Project Setup & Tooling

- [x] `npm install` in `frontend/` (lockfile committed; `npm ci` reproducible in CI)
- [x] `tsc --noEmit` clean (0 errors) and enforced by the CI frontend job
- [x] **App bundles for release on both platforms** (`npm run bundle:android` / `bundle:ios`, ~1.79 MB each) — proves every import resolves; enforced in CI
- [x] Platform-aware API base URL (Android `10.0.2.2`, iOS `localhost`) with a single documented override point
- [ ] iOS: `cd ios && pod install`
- [ ] Add Plus Jakarta Sans + Inter `.ttf` files to `src/assets/fonts` and run `npx react-native-asset`
- [x] ESLint + Prettier — `npm run lint` (**`--max-warnings 0`**), `format`,
      `format:check`, all three gated in CI. Fixed 6 real errors and formatted
      103 files; rules that fight the architecture (theme-driven inline styles,
      deliberate `void` on fire-and-forget promises) are disabled **with reasons**
      rather than worked around case by case
- [ ] **Verify the app boots on an Android emulator / iOS simulator** ← main outstanding validation
- [ ] Add `react-native-config` (or equivalent) so `.env` is actually read by the app
- [x] Path aliases in tsconfig + Babel + Jest — 86 files migrated, zero three-level
      climbs left. `src/types` is aliased as `@models`, not `@types`, because
      module-resolver matches by prefix and would capture `@types/react`

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
- [x] Welcome / value-proposition carousel — three swipeable slides, dots, and a
      Skip route out. Copy is limited to what the app actually does (a test
      guards against "guaranteed band" style claims creeping in)
- [x] Exam date picker in onboarding — optional by design, since many learners have
      not booked yet and blocking on a date they do not have would stall them at
      the door. Verified end to end: it persists and becomes the prediction horizon
- [x] Placement diagnostic runner — one short sitting across all four modules,
      skippable at any point. Reading and Listening grade instantly from the key;
      Writing and Speaking are optional and a skipped or too-short response
      records **no** baseline rather than a fabricated one
- [x] Baseline results + CEFR — per-module bands with the reason for each, overall
      band, and an indicative CEFR level; written back to the learner profile
- [x] "Generating plan" state — shown while the plan is built, stating what is
      happening rather than a bare spinner

### Speaking (AI-scored practice built; live voice pipeline pending)
- [x] Part 2 cue-card practice: real cue card from the backend bank, prep → speak timers driven by the card, response capture
- [x] AI scoring result (band + 4 criteria bars + examiner feedback)
- [x] Session start screen — full interview or any single part. It states plainly
      that answers are typed and does **not** request microphone access, since
      voice capture is not wired yet and asking for a permission the app cannot
      use would be worse than saying so
- [x] Part 1 and Part 3 flows — themed question sets from a new `speaking_questions`
      bank (`GET /speaking/questions?part=`), answered in order and scored as one
      run, with part-specific guidance so Part 3 is not answered like Part 1
- [x] Highlighted transcript + jump-to-issue markers — the AI returns verbatim
      quotes, the API locates each in the transcript and **drops any it cannot
      find**, so a paraphrase never highlights the wrong words
- [ ] Recording replay alongside the transcript — blocked on the voice pipeline
- [x] Speaking history (shown in the unified History screen)

### Writing (practice + feedback built)
- [x] Prompt delivered from the backend prompt bank (random within difficulty)
- [x] Essay editor (multiline, live word count, submit) + AI-scored result (band, 4 criteria, feedback, improved essay)
- [x] Submission → scoring pending/loading state
- [x] Task selection UI — Academic/General x Task 1/Task 2, with the Task 1 label
      following the paper (Report vs Letter) and the word target switching with it
- [ ] Task 1 chart/image assets — Task 1 prompts currently state their data as text
      (a table and a process list), so they are fully answerable; real chart images
      would be an upgrade rather than a fix
- [x] Writing timer — real IELTS allowances (20 min Task 1, 40 min Task 2), amber
      under 5 minutes, start/pause/restart. Expiry never discards or force-submits
      the essay; it only stops claiming there is time left
- [x] Writing history (unified History screen), with a per-module band-trend chart
- [x] Essay diffs — a Changes tab word-diffs the draft against the model essay,
      ignoring punctuation-only edits so real changes are not lost in noise

### Reading (built)
- [x] Passage + question runner (MCQ / True-False-Not-Given / short answer)
- [x] Result screen: raw score → band + per-question correctness & explanations
- [x] Adaptive difficulty (server-resolved) + randomized passage selection
- [x] Explicit difficulty selection UI — Adaptive/Easy/Medium/Hard, with the level
      actually served shown alongside the request
- [x] Question navigator + timer — numbered strip showing answered state (labelled
      for screen readers, not colour-only), and a 20-minute passage clock
- [x] Matching-headings task — **tap-to-assign, not drag**. Dragging a small target
      on a phone is error-prone and has no accessible equivalent for screen
      readers; tapping a heading then a paragraph expresses the same intent and
      is fully operable by assistive tech. Modelled as grouped multiple choice,
      so the existing grading path is unchanged

### Listening (built)
- [x] Clip delivery + question runner with answer capture
- [x] Result screen: raw score → band + per-question feedback with **audio timestamps**
- [x] Adaptive difficulty + randomized clip selection
- [x] **Audio is now actually served** — `/media/...` route (the advertised `audioUrl` used to 404), path-traversal guarded, covered by a smoke test
- [ ] **Native audio playback in the app** — needs a player library (`react-native-video`/`sound`) that requires native linking; cannot be verified without a device build
- [ ] **Replace silent placeholder audio with real recordings** — clips are valid WAVs of the right duration but contain silence (`scripts/generate_placeholder_audio.py`)
- [x] Explicit difficulty selection UI (shared `DifficultySelector`)
- [x] Single-play / replay policy — exam rules by default (one play, no repeat),
      with an explicit practice mode because drilling a failed clip is a
      legitimate way to learn. Note: playback is still simulated until a native
      player lands, so this enforces the policy, not the audio

### AI Tutor / Learning
- [x] Daily Coach feed (message + weakness-driven recommendations that tap through to practice)
- [x] **Vocabulary builder** — SM-2 spaced-repetition flashcards (reveal → grade → reschedule), session summary + stats, reachable from Coach
- [x] **Grammar tutor** — 8-lesson library with worked examples; lessons that match the learner's recorded weaknesses are badged "FOR YOU" and sorted first; reachable from Coach
- [x] Full mock test — four sections with their real allowances, assembled at start
      so a resumed sitting serves the same items. Each section is submitted through
      its own module controller, so a mock test produces real attempts and feeds
      history, trends and weakness tracking like ordinary practice
- [x] Readiness report — verdict, per-section gap to target, and what to do next.
      The verdict is driven by the **weakest** section, not just the average:
      9.0/5.0 averages to target but is not ready, and saying otherwise would be
      actively misleading

### Progress / Analytics (built — real data)
- [x] Progress screen: overall band, predicted band + confidence, per-module bands, focus areas
- [x] Coach screen: recommendations (tap-through) + adaptive level per module
- [x] Practice hub: module launcher with adaptive difficulty badges
> All five tabs are now real screens (no placeholders remain).
- [x] Band trend chart — `GET /analytics/trend` serves per-module *and* running-overall
      series; the Progress screen plots the overall line (four lines on a phone-width
      chart is unreadable, and per-module current bands are in the radar below it)
- [x] Radar chart of 4 modules (current band per module, unmeasured axes collapse
      to the centre rather than reading as 0)
- [x] Improvement velocity — per-module weekly rate of change, signed and
      unit-bearing. Modules with too little history are omitted rather than shown
      as 0.00/wk, which would read as stagnation instead of absence of data
- [x] Consistency — current and longest streak, active days in the last 30, and an
      8-week activity histogram (`GET /analytics/insights`). Time-on-task reports
      **only** measured speaking minutes and says so; the other modules record no
      elapsed time, and a fabricated "hours studied" would be worse than none
- [x] Learning insights cards — strengths ranked against the learner's own overall
      band, recorded weakness tags worst-first, and a plain-language summary

### Profile / Settings (real profile data)
- [x] Loads the real profile; editable **target band** and **daily study time** (PATCHed to the backend)
- [x] Shows exam type / exam date / CEFR + per-module starting levels (baselines)
- [x] Theme toggle + server-side logout (refresh token revoked)
- [x] Exam-date editing (`DatePickerSheet`, month grid, past days disabled; feeds
      the prediction horizon). Built without
      `@react-native-community/datetimepicker` to avoid a native module and a
      rebuild that cannot be verified on iOS here
- [x] Replan on exam-date change — rebuilds only if a plan already exists, so it
      never creates one for someone who never asked
- [ ] Notification & reminder scheduling
- [ ] Real time-on-task across all four modules — needs the client to submit
      elapsed time per attempt (schema + API change); only Speaking records it today
- [x] Consent management — reachable any time from Profile, both consents
      withdrawable, and withdrawing AI states what stops working
- [x] Data export — `GET /me/export` returns every table the learner owns as JSON,
      shared from the app via RN's built-in `Share` (no filesystem permission or
      native module). Credential hashes are never included
- [x] Delete account — `DELETE /me` erases all owned rows and revokes sessions,
      behind a type-DELETE confirmation. AI usage rows are anonymised rather than
      deleted so historical cost reporting stays honest, and the audit row outlives
      the account
- [x] Offline banner + sync status — app-wide strip showing offline state and how
      many changes are held locally. Connectivity is **inferred from whether
      requests reach the server**, not read from the OS: a real connectivity API
      needs `@react-native-community/netinfo`, a native module. The banner states
      that limitation rather than implying live monitoring

---

## 2. Frontend — Components (remaining)

- [x] Line chart / trend chart component (`LineChart`, SVG, fixed 0-9 band axis)
- [x] Radar chart component (`RadarChart`, SVG, n-axis)
- [ ] Waveform recorder / live audio visualizer
- [ ] Audio player with scrubber + speed control
- [x] Question rendering (MCQ / True-False-Not-Given radio options + short-answer input) — [ ] Matching Headings drag-connect
- [x] Cue-card rendering (topic, prompt, bullet points)
- [x] Countdown / timer (Speaking prep + speak phases)
- [x] Flashcard (reveal/grade) component — [ ] flip animation
- [x] Toast / Snackbar (`ToastHost` + `toastSlice`; queue in Redux so the axios
      interceptor can raise one without a provider in scope, duplicates collapsed)
- [x] Bottom sheet / modal (`BottomSheet` on RN `Modal`, so it sits above the
      navigator and the hardware back button dismisses it)
- [x] Consent modal (`ConsentSheet`)
- [x] Empty / error / offline state components (`EmptyState`, three variants — a new
      account must not be told "something went wrong")
- [x] Skeleton loaders (`Skeleton` + `SkeletonCard`, shared pulse; adopted on Progress)
- [ ] Streak flame (animated) + progress ring (SVG)

---

## 3. Frontend — State, API & Infra

- [ ] Redux slices for: speaking, writing, reading, listening, planner, analytics, vocabulary, coach, offline
- [ ] RTK Query (or thunks) for all real endpoints
- [x] **Full API layer live-verified** against the backend — auth, onboarding/profile, `/me`, dashboard, analytics, and all four modules
- [x] **Mock data can never reach a release build** (`useMock` is gated on `__DEV__`, guarded by a test). Dev still defaults to fixtures via `USE_MOCK_IN_DEV` — [ ] set it to false once a backend is routinely running
- [ ] Tree-shake fixture data out of release bundles (currently ~11.5 KB / 0.66% of the bundle ships unused but is never served)
- [x] Token refresh flow (single-flight 401 → refresh → retry; server logout via `logoutThunk`) — verified against a live backend — [ ] wire remaining screens off mock
- [ ] Secure token storage (Keychain/Keystore) — needs `react-native-keychain`, a
      native module. **Not attempted**: with no device attached it could not be
      verified, and unverified native auth code is worse than none
- [x] Offline queue + deferred sync — writes that never reach the server are
      queued and persisted, then replayed oldest-first when connectivity returns.
      Conflict policy is last-write-wins **per target**, collapsed at enqueue time:
      toggling a task on/off/on offline sends one final state, not three writes
      that race. An exhausted item stays queued rather than being deleted
- [ ] Push notifications / reminders integration
- [x] Error boundary + global error handling (`ErrorBoundary` at the root; requests
      that never reach the server raise a toast, HTTP errors stay with the screen)
- [ ] Accessibility pass (labels, dynamic type, contrast) + localization (i18n) setup

---

## 4. Backend — Foundation

- [x] Pydantic `Settings` (env-driven config) + `.env` loading
- [x] Async SQLAlchemy engine + session (Supabase PostgreSQL / SQLite dev)
- [x] Alembic migrations setup (async env) + initial schema migration (users, refresh_tokens, learner_profiles) — extend as new models land
- [x] Repository layer — `OwnedRepository.get_owned` replaces the fetch-then-check
      ownership dance that was written out six times. Each copy had to remember to
      return 404 rather than 403, because 403 confirms a row exists to someone who
      should not know. Deliberately thin: controllers still write their own
      queries where the query is the interesting part
- [x] Service/use-case logic + dependency injection (auth) — extend to other domains
- [x] Unit-of-Work / transaction handling (request-scoped commit/rollback)
- [x] Structured logging + correlation propagation — single-line JSON logs, the
      correlation id carried in a ContextVar so any code reached during a request
      gets it without threading it through call signatures; it is the same id the
      client saw in `X-Correlation-Id`
- [x] Rate limiting (in-memory fixed-window on auth + AI endpoints, 429 problem+json + Retry-After) — [ ] Redis backing for multi-instance
- [ ] Redis integration (cache + queue)
- [ ] Background job runner (Celery/arq) + task definitions
- [x] Exception taxonomy — `core/errors.py` with stable machine-readable codes and
      real `type` URIs. Every error used to collapse to `code: "http_error"`, so a
      client could only tell them apart by string-matching the title. Bare
      HTTPExceptions now derive a code from their status, so nothing is opaque

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
- [x] Planner — `GET/POST /planner/plan`, `PATCH /planner/tasks/{id}`. Deterministic,
      not AI-generated: a plan has to be explainable and must not change every
      time it is rebuilt. Sessions are allocated by distance-to-target per module
      using largest-remainder, so each week totals exactly the intended count
- [x] Speaking: transcript AI scoring (4 criteria, rubric-as-code) + history + **cue-card bank** (`GET /speaking/cue-cards`) — [ ] session creation (LiveKit token), finish
- [x] Writing: submission, AI scoring, improved essay (POST/GET attempts) + history + **prompt bank** (`GET /writing/prompts`)
- [x] Reading (backend): passage/question delivery (no answer leak), auto-grading, raw→band mapping, per-question explanations — [ ] AI question generation
- [x] Listening (backend): clip/question delivery (no answer leak), auto-grading, band mapping, per-question feedback with audio timestamps — [ ] AI question generation, signed audio URLs
- [x] Analytics: progress + band prediction + **real dashboard overview** (greeting, streak, prediction, module levels, recommendations) — [ ] insights
- [x] Vocabulary SRS endpoints (`/vocabulary/review`, `/grade`, `/stats`) with an SM-2 scheduler
- [x] Grammar lesson endpoints (`/grammar/lessons`, `/grammar/lessons/{id}`) with weakness-based recommendation
- [ ] Notifications / reminders

---

## 7. AI Layer

- [x] `LLMProvider` port (provider-agnostic abstraction) + offline mock provider
- [x] Groq provider adapter (OpenAI-compatible via httpx)
- [x] Adaptive difficulty resolver (recent-band → easy/medium/hard, wired into Reading/Listening delivery) + weakness-driven recommendations (`/me/adaptive-difficulty`, `/me/recommendations`)
- [x] AI orchestrator (Writing scoring) — [ ] full multi-task routing policy
- [x] Prompt registry — every prompt has an id and a version, and the version is
      written onto each `ai_interactions` row. Change a rubric's wording and the
      bands it produces shift; without a recorded version, last month's 6.5 and
      today's 6.5 are quietly different measurements. Rows written before the
      registry stay null rather than being backfilled with a version they never used
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

- [x] Admin dashboard overview — `GET /admin/overview`, RBAC-guarded (a learner
      gets 403). Users, onboarded, active learners last week, attempts per module,
      mock tests, active plans, AI calls/tokens/cost/failures, and the live prompt
      versions. Every figure is a straight count over real rows; nothing estimated
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

### Verified on real infrastructure (2026-07-30)

Running against **live Supabase PostgreSQL 17.6** and the **real Groq API**, on a
physically connected Android phone:

- [x] All 12 Alembic migrations applied to Supabase — 20 tables in `public`
- [x] Real AI scoring, and it discriminates: a weak 45-word essay scored **band 1.5**,
      a strong 260-word essay scored **band 9.0**, with per-criterion breakdowns
- [x] `ai_interactions` rows confirm `provider=groq`, `model=llama-3.3-70b-versatile`
      with genuine token counts and latencies — not the mock
- [x] Full 13-step E2E journey passes end-to-end against Supabase + Groq
- [x] On-device: register → onboarding → Home → logout → login, all against the live
      backend. Profile persisted (target 7.0, academic, intermediate, 30 min,
      `consent_ai=true`), refresh token correctly rotated and the old one revoked

### Known gaps worth stating plainly
- Listening has **no real audio playback** yet — questions are answerable, the clip does not play.
- Speaking is **transcript-based**, not live voice.
- AI scoring falls back to the **offline mock provider** when `GROQ_API_KEY` is unset.
- **iOS still carries the `frontend` Xcode target and bundle id.** Renaming a
  `.pbxproj` target is invasive and there is no Mac here to verify the result, so it
  was deliberately left alone rather than shipped unverified. Android is done
  (`com.ieltsmaster.app`).
- Only the **Android debug** build has been run on hardware; release signing and iOS
  remain unverified (no Mac available).

### Known test-hygiene issue
- Any Jest suite that **renders a component** leaves a handle open, so the run ends
  with "Jest did not exit one second after the test run has completed". Pure unit
  suites (e.g. `src/constants/__tests__/colors.test.ts`) exit cleanly, and the leak
  reproduces on suites that predate the current work, so it is in the shared render
  setup rather than any one test. Harmless today — CI passes — but it should be
  tracked down before it turns into flaky runs.

### Infrastructure notes learned the hard way
- **Renaming the Android package requires clearing `android/build/generated/autolinking`.**
  React Native's `GenerateEntryPointTask` reads `project.android.packageName` from that
  cached `autolinking.json`, and it lives in the *root* `android/build` directory, which
  `:app:clean` does not touch. Until it is deleted the build keeps emitting
  `ReactNativeApplicationEntryPoint.java` against the old package and fails with
  `error: package com.frontend does not exist`, even after a full clean and
  `--rerun-tasks`.
- **Use the Supabase connection pooler, not the direct endpoint.**
  `db.<ref>.supabase.co` resolves to **IPv6 only**; on an IPv4-only network every
  connection fails with the opaque `[WinError 121] The semaphore timeout period has
  expired`. Use `aws-<n>-<region>.pooler.supabase.com` with user
  `postgres.<project-ref>`. See `backend/.env.example`.
- The engine sets `pool_recycle=300`: managed Postgres behind NAT silently drops idle
  TCP, and a dead pooled connection surfaces as a bare `OSError` that asyncpg does not
  classify as a disconnect, so `pool_pre_ping` alone cannot recover it.
