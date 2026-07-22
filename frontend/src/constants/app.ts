/**
 * App-wide static configuration constants.
 */

export const APP_CONFIG = {
  displayName: 'IELTS Master',
  tagline: 'Your AI Mentor for IELTS Success',
  poweredBy: 'POWERED BY ADVANCED AI',
  brandMark: 'AURAGRAPH',
  splashDurationMs: 2200,
} as const;

/** IELTS domain constants. */
export const IELTS = {
  minBand: 0,
  maxBand: 9,
  bandStep: 0.5,
  modules: ['speaking', 'writing', 'reading', 'listening'] as const,
  examTypes: ['academic', 'general'] as const,
  levels: ['beginner', 'intermediate', 'advanced'] as const,
  difficulties: ['easy', 'medium', 'hard', 'adaptive'] as const,
} as const;
