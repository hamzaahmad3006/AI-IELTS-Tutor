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
  planner: {
    generate: '/plans/generate',
    active: '/plans/active',
  },
  dashboard: {
    overview: '/analytics/overview',
  },
  speaking: {
    sessions: '/speaking/sessions',
    cueCards: '/speaking/cue-cards',
    attempts: '/speaking/attempts',
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
  analytics: {
    overview: '/analytics/overview',
    progress: '/analytics/progress',
    prediction: '/analytics/prediction',
    trend: '/analytics/trend',
  },
} as const;
