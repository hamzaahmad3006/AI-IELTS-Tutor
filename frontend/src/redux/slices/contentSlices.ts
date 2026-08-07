/**
 * The read-only slices, built from one factory.
 *
 * Each caches the response of a single endpoint and tracks its loading and
 * error state. Grouped in one file because separate files would be six imports
 * and six exports for six three-line declarations — the file boundary would
 * carry no information.
 *
 * Anything with real behaviour of its own gets its own module. `authSlice`
 * owns a session, `offlineSlice` owns a write queue; neither belongs here.
 */

import { analyticsApi, meApi, plannerApi, vocabularyApi } from '@api';
import { createAsyncSlice } from '../createAsyncSlice';

export const progressSlice = createAsyncSlice({
  name: 'progress',
  fetcher: () => analyticsApi.getProgress(),
  fallbackError: 'Could not load your progress.',
});

export const trendSlice = createAsyncSlice({
  name: 'trend',
  fetcher: () => analyticsApi.getTrend(),
  fallbackError: 'Could not load your band history.',
});

export const insightsSlice = createAsyncSlice({
  name: 'insights',
  fetcher: () => analyticsApi.getInsights(),
  fallbackError: 'Could not load your insights.',
});

export const plannerSlice = createAsyncSlice({
  name: 'planner',
  fetcher: () => plannerApi.getPlan(),
  fallbackError: 'Could not load your study plan.',
});

export const vocabularySlice = createAsyncSlice({
  name: 'vocabulary',
  fetcher: () => vocabularyApi.getStats(),
  fallbackError: 'Could not load your vocabulary progress.',
});

export const weaknessSlice = createAsyncSlice({
  name: 'weakness',
  fetcher: () => meApi.getWeaknesses(),
  fallbackError: 'Could not load your weak areas.',
});

export const coachSlice = createAsyncSlice({
  name: 'coach',
  fetcher: () => meApi.getRecommendations(),
  fallbackError: 'Could not load your recommendations.',
});

export const progressReducer = progressSlice.reducer;
export const trendReducer = trendSlice.reducer;
export const insightsReducer = insightsSlice.reducer;
export const plannerReducer = plannerSlice.reducer;
export const vocabularyReducer = vocabularySlice.reducer;
export const weaknessReducer = weaknessSlice.reducer;
export const coachReducer = coachSlice.reducer;

export const fetchProgress = progressSlice.fetch;
export const fetchTrend = trendSlice.fetch;
export const fetchInsights = insightsSlice.fetch;
export const fetchPlan = plannerSlice.fetch;
export const fetchVocabularyStats = vocabularySlice.fetch;
export const fetchWeaknesses = weaknessSlice.fetch;
export const fetchRecommendations = coachSlice.fetch;

/**
 * Every cached slice, so logout can clear all of them.
 *
 * Listed once here rather than at each call site: a slice missing from a
 * hand-written logout would leave one person's progress on screen for the
 * next person to sign in on the same device.
 */
export const CACHED_SLICES = [
  progressSlice,
  trendSlice,
  insightsSlice,
  plannerSlice,
  vocabularySlice,
  weaknessSlice,
  coachSlice,
] as const;
