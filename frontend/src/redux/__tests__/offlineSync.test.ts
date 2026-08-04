/** Queue draining: ordering, retry limits and connectivity inference. */

import { plannerApi } from '@api';
import { store } from '../store';
import { drainQueue, MAX_ATTEMPTS } from '../offlineSync';
import {
  clearQueue,
  connectivityChanged,
  enqueue,
  mutationFailed,
  syncFinished,
} from '../slices/offlineSlice';

const reset = (): void => {
  store.dispatch(clearQueue());
  store.dispatch(connectivityChanged(false));
  store.dispatch(syncFinished({ allSent: false }));
};

describe('drainQueue', () => {
  beforeEach(() => {
    reset();
    jest.restoreAllMocks();
  });

  it('does nothing when the queue is empty', async () => {
    const spy = jest.spyOn(plannerApi, 'setTaskDone');
    await drainQueue(store.dispatch, store.getState);
    expect(spy).not.toHaveBeenCalled();
  });

  it('sends queued writes and clears them', async () => {
    const spy = jest
      .spyOn(plannerApi, 'setTaskDone')
      .mockResolvedValue({} as never);

    store.dispatch(
      enqueue({ kind: 'planTask', targetId: 'pt1', payload: { isDone: true } }),
    );
    store.dispatch(
      enqueue({
        kind: 'planTask',
        targetId: 'pt2',
        payload: { isDone: false },
      }),
    );

    await drainQueue(store.dispatch, store.getState);

    expect(spy).toHaveBeenCalledTimes(2);
    // Replayed oldest first, so the server ends up in the state the learner
    // actually left the app in.
    expect(spy.mock.calls[0]).toEqual(['pt1', true]);
    expect(spy.mock.calls[1]).toEqual(['pt2', false]);
    expect(store.getState().offline.queue).toHaveLength(0);
    expect(store.getState().offline.lastSyncedAt).not.toBeNull();
  });

  it('stops on the first failure instead of burning the retry budget', async () => {
    const spy = jest
      .spyOn(plannerApi, 'setTaskDone')
      .mockRejectedValue(new Error('Network Error'));

    store.dispatch(
      enqueue({ kind: 'planTask', targetId: 'pt1', payload: { isDone: true } }),
    );
    store.dispatch(
      enqueue({ kind: 'planTask', targetId: 'pt2', payload: { isDone: true } }),
    );
    // `lastSyncedAt` records the last *complete* sync and is meant to survive
    // later failures, so the check is that it did not move.
    const before = store.getState().offline.lastSyncedAt;

    await drainQueue(store.dispatch, store.getState);

    // One attempt, not two: a failure here almost certainly means still
    // offline, so the rest of the queue is left alone.
    expect(spy).toHaveBeenCalledTimes(1);
    expect(store.getState().offline.queue).toHaveLength(2);
    expect(store.getState().offline.isOffline).toBe(true);
    expect(store.getState().offline.lastSyncedAt).toBe(before);
  });

  it('leaves an exhausted item queued rather than deleting it', async () => {
    const spy = jest
      .spyOn(plannerApi, 'setTaskDone')
      .mockResolvedValue({} as never);

    store.dispatch(
      enqueue({ kind: 'planTask', targetId: 'pt1', payload: { isDone: true } }),
    );
    const { id } = store.getState().offline.queue[0];
    for (let i = 0; i < MAX_ATTEMPTS; i += 1) {
      store.dispatch(mutationFailed({ id, error: 'Network Error' }));
    }

    const before = store.getState().offline.lastSyncedAt;
    await drainQueue(store.dispatch, store.getState);

    // Not retried, but not discarded either: silently dropping the learner's
    // work is worse than showing it as stuck.
    expect(spy).not.toHaveBeenCalled();
    expect(store.getState().offline.queue).toHaveLength(1);
    // Nothing was sent, so this is not a completed sync.
    expect(store.getState().offline.lastSyncedAt).toBe(before);
  });

  it('marks connectivity restored once everything is sent', async () => {
    jest.spyOn(plannerApi, 'setTaskDone').mockResolvedValue({} as never);
    store.dispatch(connectivityChanged(true));
    store.dispatch(
      enqueue({ kind: 'planTask', targetId: 'pt1', payload: { isDone: true } }),
    );

    await drainQueue(store.dispatch, store.getState);

    expect(store.getState().offline.isOffline).toBe(false);
  });
});
