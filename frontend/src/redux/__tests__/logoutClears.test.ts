/**
 * Logging out clears everything the previous learner loaded.
 *
 * The failure this prevents is specific: one person's progress, weaknesses and
 * study plan still in the store when the next person signs in on the same
 * device. Nothing crashes — they simply see someone else's data attributed to
 * them, and on a shared phone that is a real disclosure.
 */

import { store } from '../store';
import { logout } from '../slices/authSlice';
import {
  fetchProgress,
  fetchRecommendations,
  fetchWeaknesses,
} from '../slices/contentSlices';
import { initialAsyncState } from '../createAsyncSlice';

jest.mock('@api', () => ({
  analyticsApi: {
    getProgress: jest.fn(() => Promise.resolve({ overallBand: 6.5 })),
    getTrend: jest.fn(() => Promise.resolve({})),
    getInsights: jest.fn(() => Promise.resolve({})),
  },
  plannerApi: { getPlan: jest.fn(() => Promise.resolve(null)) },
  vocabularyApi: { getStats: jest.fn(() => Promise.resolve({})) },
  meApi: {
    getWeaknesses: jest.fn(() =>
      Promise.resolve({ items: [{ tag: 'grammar' }] }),
    ),
    getRecommendations: jest.fn(() => Promise.resolve({ items: [] })),
  },
  authApi: { logout: jest.fn(() => Promise.resolve()) },
}));

describe('logout', () => {
  it('clears every cached read', async () => {
    await store.dispatch(fetchProgress());
    await store.dispatch(fetchWeaknesses());
    await store.dispatch(fetchRecommendations());

    expect(store.getState().progress.data).not.toBeNull();
    expect(store.getState().weakness.data).not.toBeNull();

    store.dispatch(logout());

    // Not "most of it" — a hand-written list of slices to clear is one someone
    // forgets to update, and the thing it forgets is somebody's data.
    expect(store.getState().progress).toEqual(initialAsyncState());
    expect(store.getState().weakness).toEqual(initialAsyncState());
    expect(store.getState().coach).toEqual(initialAsyncState());
    expect(store.getState().trend).toEqual(initialAsyncState());
    expect(store.getState().insights).toEqual(initialAsyncState());
    expect(store.getState().planner).toEqual(initialAsyncState());
    expect(store.getState().vocabulary).toEqual(initialAsyncState());
  });

  it('clears the session itself', () => {
    store.dispatch(logout());
    expect(store.getState().auth.isAuthenticated).toBe(false);
    expect(store.getState().auth.tokens).toBeNull();
    expect(store.getState().auth.user).toBeNull();
  });

  it('keeps the theme', () => {
    // A device preference, not anyone's data. Resetting it to light mode at
    // 11pm because someone signed out is a small hostility.
    const before = store.getState().theme.mode;
    store.dispatch(logout());
    expect(store.getState().theme.mode).toBe(before);
  });

  it('leaves the store usable afterwards', async () => {
    store.dispatch(logout());

    // The next learner must be able to load their own data immediately; a
    // cleared store that cannot be refilled is just a different bug.
    await store.dispatch(fetchProgress());
    expect(store.getState().progress.data).not.toBeNull();
    expect(store.getState().progress.status).toBe('succeeded');
  });
});
