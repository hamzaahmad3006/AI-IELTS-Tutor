# Google Stitch — Master Prompt (copy-paste)

Design a complete, production-grade **mobile app UI** (iOS + Android, React Native style) for **"AI IELTS Tutor"**, an AI-first IELTS preparation platform where an AI examiner scores all four IELTS modules (Speaking, Writing, Reading, Listening), builds adaptive study plans, remembers learner weaknesses, and predicts the IELTS band. Generate every screen, flow, and component below in a single cohesive design system. Also include a separate desktop/web **Admin Panel** section. Use a modern, trustworthy, calm-but-energetic EdTech aesthetic. Support light and dark themes. Follow WCAG 2.1 AA contrast.

## BRAND IDENTITY
- Name/wordmark: "AI IELTS Tutor". Logo = a rounded speech bubble whose inside forms an ascending soundwave/bar-graph (symbolizing speaking + measurable progress), paired with a clean geometric wordmark. Provide app icon, horizontal lockup, and monochrome variant.
- Personality: intelligent, supportive mentor; premium, minimal, confidence-building; not childish, not corporate-cold.
- Logo usage on splash, headers, empty states, and auth screens.

## DESIGN SYSTEM
- Primary: Indigo #4F46E5. Primary-dark #4338CA. Accent/CTA: Teal #14B8A6. Warm highlight: Coral #FB7185.
- Neutrals: Ink #0F172A, Slate #334155/#64748B, Cloud #F1F5F9, White #FFFFFF. Dark theme surfaces: #0B1220 / #111827 / #1E293B.
- Band score color scale: 0–4.5 red #EF4444, 5–6 amber #F59E0B, 6.5–7 lime #84CC16, 7.5–9 green #10B981. Use these consistently for BandBadge, charts, and criteria bars.
- Semantic: success #10B981, warning #F59E0B, error #EF4444, info #3B82F6.
- Typography: Headings "Sora" or "Plus Jakarta Sans" (bold, tight); Body/UI "Inter". Type scale: Display 32/40, H1 24, H2 20, H3 17, Body 15, Caption 13. Generous line-height.
- Shape & spacing: 12–16px card radius, 999px pills/badges, 8pt spacing grid, soft shadows, subtle gradients only on hero/CTA. Rounded, friendly, spacious.
- Iconography: consistent line icons (rounded), 24px grid.
- Motion cues (describe in UI): progress rings, skeleton loaders, streak flame, waveform animation.

## GLOBAL NAVIGATION
Bottom tab bar (5 tabs): Home, Practice, Progress, Coach, Profile. Persistent AI-status/"scoring…" indicators. Floating quick-start button for "Start a Session".

## REUSABLE COMPONENTS (design as a library)
Primary/Secondary/Ghost Buttons, Pill Chips, Input fields, OTP/password field, Card, StatTile, BandBadge (0–9, color-coded), Criteria bar (Fluency/Lexical/Grammar/Pronunciation or Task/Coherence/Lexical/Grammar), Progress ring, Streak flame, Difficulty selector (Easy/Medium/Hard/Adaptive), Module tile (Speaking/Writing/Reading/Listening), Timer/Countdown, CueCard, Audio player with scrubber + speed, Waveform recorder + mic button (idle/listening/processing states), Transcript viewer with highlighted errors/strong phrases/filler markers, Inline correction tooltip (original→suggestion), Essay diff view, Flashcard (flip), Question types (MCQ radio, True/False/Not Given segmented, Matching Headings drag-connect), Result/Feedback panel (band + strengths + improvements), Recommendation card, Coach message bubble, Chart (line trend, radar for 4 modules), Insight card, Empty/Loading/Error/Offline states, Toast/Snackbar, Bottom sheet, Consent modal (voice recording + AI processing).

## SCREENS — AUTH & ONBOARDING
1. Splash (logo + tagline).
2. Value-proposition intro carousel.
3. Sign Up (email, password, strength meter).
4. Login (+ forgot password).
5. Onboarding wizard (multi-step): exam type (Academic/General), current self-level (Beginner/Intermediate/Advanced), target band (0–9 slider), exam date (calendar), daily study minutes, consent screen (voice + AI toggles).
6. Adaptive placement diagnostic intro + question runner across all 4 modules + progress.
7. Baseline results (per-module band cards + CEFR level + "generating your plan" animation).

## SCREENS — HOME / DASHBOARD
8. Home: greeting, predicted IELTS band card with confidence, streak flame, today's goals checklist (adaptive tasks), quick-start module tiles, daily coach message banner, weekly focus.

## SCREENS — SPEAKING (voice examiner)
9. Speaking start (choose full interview or single part; mic permission prompt).
10. Live interview — Part 1 (examiner speaking state via TTS, learner waveform recorder, live transcript, examiner avatar/orb, barge-in).
11. Part 2 — CueCard screen (topic + bullet points, 60s prep timer, then ≤120s speak timer).
12. Part 3 — abstract discussion with dynamic follow-ups.
13. Speaking feedback: overall BandBadge + 4 criteria bars (Fluency & Coherence, Lexical, Grammar, Pronunciation), highlighted transcript, replay audio with jump-to-issue markers, targeted drills.
14. Speaking history list (per-attempt bands + trend).

## SCREENS — WRITING
15. Writing task selection (Task 1 Academic graph/chart/process/map or General letter; Task 2 essay).
16. Prompt display (with asset/chart image for Task 1 Academic) + start.
17. Essay editor (rich text, live word count, optional timer, submit).
18. Writing result: overall band + 4 criteria (Task Response, Coherence & Cohesion, Lexical Resource, Grammatical Range & Accuracy), inline grammar corrections, vocabulary upgrade suggestions, "Improved Model Essay" + diff toggle.
19. Writing history with band trend + diffs.

## SCREENS — READING
20. Reading setup (difficulty selector Easy/Medium/Hard/Adaptive).
21. Reading practice: passage pane + question set (MCQ, True/False/Not Given, Matching Headings), question navigator, timer.
22. Reading result: raw score → band, per-question correctness, AI explanations with passage evidence highlighting, weakness tags.

## SCREENS — LISTENING
23. Listening setup (difficulty).
24. Listening practice: audio player (single-play/replay per policy) + questions (form/note completion, MCQ, matching).
25. Listening result: raw score → band, instant per-question feedback with the answer's audio timestamp segment.

## SCREENS — AI TUTOR / COACH / LEARNING
26. Coach tab: daily motivational message, personalized recommendations feed (weakness-driven lessons/vocab/drills).
27. Vocabulary builder: spaced-repetition flashcards (flip, grade recall) tied to weak lexical fields; deck overview.
28. Grammar tutor: lesson list by concept tag + lesson detail (explanation + examples).
29. Mock Test: full 4-module timed simulation flow + assembly + overall band readiness report.

## SCREENS — PROGRESS / ANALYTICS
30. Progress dashboard: per-module band trend charts (line), improvement velocity, radar chart of 4 modules, predicted exam-day band with confidence interval, consistency/streak/time-on-task, learning insights (strengths/weaknesses) cards.

## SCREENS — PROFILE / SETTINGS
31. Profile: goals & target band (editable → triggers replan), exam date, daily minutes, level.
32. Settings: notifications/reminders scheduling, theme (light/dark), consents management, data export & delete account (privacy), logout.
33. Notifications/reminders center.
34. Offline mode banner + sync status (queued attempts).

## GLOBAL STATES (design variants)
Loading/skeleton, empty, error (with correlation id friendly message), offline, "AI scoring in progress", rate-limit/quota reached, session failed/retry.

## ADMIN PANEL (separate desktop/web dashboard, same brand & design system)
A1. Admin login. A2. Admin dashboard overview (KPIs). A3. User management (list, filter, view, suspend, role assignment). A4. Question bank management (CRUD, difficulty/topic tags, versioning). A5. Reading passages management. A6. Listening audio management (upload, transcript). A7. Vocabulary library management. A8. Grammar lessons management. A9. Platform analytics & reports (growth, learning outcomes, retention charts). A10. AI usage monitoring (tokens, cost, latency, error rate, per-feature filters, budget alerts). A11. Subscription/plan management (future, feature-flagged).

Deliver a unified, elegant design system with all above screens, both light and dark, consistent components, and the branded logo throughout. Prioritize clarity, trust, and a premium mentor-like feel.
