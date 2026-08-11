/** Central registry of backend endpoint paths (relative to API base). */

export const ENDPOINTS = {
  auth: {
    register: '/auth/register',
    login: '/auth/login',
    refresh: '/auth/refresh',
    logout: '/auth/logout',
    me: '/auth/me',
  },
  onboarding: {
    submit: '/onboarding',
    diagnostic: '/onboarding/diagnostic',
  },
  profile: {
    root: '/profile',
  },
  me: {
    weaknesses: '/me/weaknesses',
    adaptiveDifficulty: '/me/adaptive-difficulty',
    recommendations: '/me/recommendations',
    export: '/me/export',
    deleteAccount: '/me',
  },
  mockTests: {
    root: '/mock-tests',
  },
  planner: {
    // These replace the earlier '/plans/*' placeholders, which were never
    // implemented on the backend.
    plan: '/planner/plan',
    tasks: '/planner/tasks',
  },
  dashboard: {
    overview: '/analytics/overview',
  },
  // The spoken interview: a session-driven exam, distinct from the one-shot
  // speaking attempts below.
  interview: {
    sessions: '/interview/sessions',
    session: (id: string): string => `/interview/sessions/${id}`,
    answer: (id: string): string => `/interview/sessions/${id}/answer`,
    answerAudio: (id: string): string =>
      `/interview/sessions/${id}/answer-audio`,
    skipPrep: (id: string): string => `/interview/sessions/${id}/skip-prep`,
    score: (id: string): string => `/interview/sessions/${id}/score`,
    questionAudio: (id: string): string =>
      `/interview/sessions/${id}/question-audio`,
    rtcToken: (id: string): string => `/interview/sessions/${id}/rtc-token`,
  },
  speaking: {
    sessions: '/speaking/sessions',
    cueCards: '/speaking/cue-cards',
    questions: '/speaking/questions',
    attempts: '/speaking/attempts',
    transcribe: '/speaking/transcribe',
    attempt: (id: string): string => `/speaking/attempts/${id}`,
    history: '/speaking/history',
  },
  writing: {
    prompts: '/writing/prompts',
    attempts: '/writing/attempts',
    attempt: (id: string): string => `/writing/attempts/${id}`,
    history: '/writing/history',
  },
  reading: {
    passages: '/reading/passages',
    attempts: '/reading/attempts',
    attempt: (id: string): string => `/reading/attempts/${id}`,
    history: '/reading/history',
  },
  listening: {
    clips: '/listening/clips',
    attempts: '/listening/attempts',
    attempt: (id: string): string => `/listening/attempts/${id}`,
    history: '/listening/history',
  },
  vocabulary: {
    review: '/vocabulary/review',
    grade: '/vocabulary/grade',
    stats: '/vocabulary/stats',
  },
  grammar: {
    lessons: '/grammar/lessons',
    lesson: (id: string): string => `/grammar/lessons/${id}`,
  },
  diagnostic: {
    root: '/diagnostic',
  },
  analytics: {
    overview: '/analytics/overview',
    progress: '/analytics/progress',
    prediction: '/analytics/prediction',
    trend: '/analytics/trend',
    insights: '/analytics/insights',
  },
} as const;
