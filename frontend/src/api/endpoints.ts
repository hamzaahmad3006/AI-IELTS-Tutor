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
    attempt: (id: string): string => `/speaking/attempts/${id}`,
    history: '/speaking/history',
  },
  writing: {
    attempts: '/writing/attempts',
    attempt: (id: string): string => `/writing/attempts/${id}`,
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
  analytics: {
    overview: '/analytics/overview',
    progress: '/analytics/progress',
    prediction: '/analytics/prediction',
  },
} as const;
