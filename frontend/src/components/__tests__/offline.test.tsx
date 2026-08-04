/** Offline queue semantics, sync draining, and the status banner. */

import React from 'react';
import { screen } from '@testing-library/react-native';
import { renderWithProviders as render } from '../../testUtils/renderWithProviders';
import { OfflineBanner } from '../OfflineBanner/OfflineBanner';
import { store } from '../../redux/store';
import {
  clearQueue,
  connectivityChanged,
  enqueue,
  mutationFailed,
  mutationSucceeded,
  syncFinished,
  syncStarted,
} from '../../redux/slices/offlineSlice';

const reset = (): void => {
  store.dispatch(clearQueue());
  store.dispatch(connectivityChanged(false));
  store.dispatch(syncFinished({ allSent: false }));
};

describe('offlineSlice', () => {
  beforeEach(reset);

  it('queues a write with its target and payload', () => {
    store.dispatch(
      enqueue({ kind: 'planTask', targetId: 'pt1', payload: { isDone: true } }),
    );
    const [item] = store.getState().offline.queue;
    expect(item.kind).toBe('planTask');
    expect(item.targetId).toBe('pt1');
    expect(item.payload).toEqual({ isDone: true });
    expect(item.attempts).toBe(0);
  });

  it('collapses repeated writes to the same target, last one wins', () => {
    // Toggling on, off, then on again offline must send one final state, not
    // three writes that race on the server and land in an arbitrary order.
    store.dispatch(
      enqueue({ kind: 'planTask', targetId: 'pt1', payload: { isDone: true } }),
    );
    store.dispatch(
      enqueue({
        kind: 'planTask',
        targetId: 'pt1',
        payload: { isDone: false },
      }),
    );
    store.dispatch(
      enqueue({ kind: 'planTask', targetId: 'pt1', payload: { isDone: true } }),
    );

    const { queue } = store.getState().offline;
    expect(queue).toHaveLength(1);
    expect(queue[0].payload).toEqual({ isDone: true });
  });

  it('keeps the original queue time when a write is superseded', () => {
    // What matters is when the learner went offline, not when they last
    // changed their mind.
    store.dispatch(
      enqueue({ kind: 'planTask', targetId: 'pt1', payload: { isDone: true } }),
    );
    const first = store.getState().offline.queue[0].queuedAt;
    store.dispatch(
      enqueue({
        kind: 'planTask',
        targetId: 'pt1',
        payload: { isDone: false },
      }),
    );
    expect(store.getState().offline.queue[0].queuedAt).toBe(first);
  });

  it('keeps separate targets separate', () => {
    store.dispatch(
      enqueue({ kind: 'planTask', targetId: 'pt1', payload: { isDone: true } }),
    );
    store.dispatch(
      enqueue({ kind: 'planTask', targetId: 'pt2', payload: { isDone: true } }),
    );
    expect(store.getState().offline.queue).toHaveLength(2);
  });

  it('removes an item once it is sent', () => {
    store.dispatch(
      enqueue({ kind: 'planTask', targetId: 'pt1', payload: { isDone: true } }),
    );
    const { id } = store.getState().offline.queue[0];
    store.dispatch(mutationSucceeded(id));
    expect(store.getState().offline.queue).toHaveLength(0);
  });

  it('records failures without discarding the write', () => {
    // Silently dropping a write the learner made is worse than showing it as
    // stuck and unsent.
    store.dispatch(
      enqueue({ kind: 'planTask', targetId: 'pt1', payload: { isDone: true } }),
    );
    const { id } = store.getState().offline.queue[0];
    store.dispatch(mutationFailed({ id, error: 'Network Error' }));

    const [item] = store.getState().offline.queue;
    expect(item.attempts).toBe(1);
    expect(item.lastError).toBe('Network Error');
  });

  it('only records a sync time when everything actually went', () => {
    store.dispatch(syncStarted());
    store.dispatch(syncFinished({ allSent: false }));
    expect(store.getState().offline.lastSyncedAt).toBeNull();

    store.dispatch(syncFinished({ allSent: true }));
    expect(store.getState().offline.lastSyncedAt).not.toBeNull();
  });
});

describe('OfflineBanner', () => {
  beforeEach(reset);

  it('stays out of the way when online with nothing pending', () => {
    render(<OfflineBanner />);
    expect(screen.queryByTestId('offline-banner')).toBeNull();
  });

  it('says how many changes are held on the device when offline', () => {
    store.dispatch(connectivityChanged(true));
    store.dispatch(
      enqueue({ kind: 'planTask', targetId: 'pt1', payload: { isDone: true } }),
    );
    render(<OfflineBanner />);
    expect(screen.getByTestId('offline-banner')).toBeTruthy();
    expect(screen.getByText(/1 change saved on this device/)).toBeTruthy();
  });

  it('shows pending work even once connectivity is back', () => {
    store.dispatch(
      enqueue({ kind: 'planTask', targetId: 'pt1', payload: { isDone: true } }),
    );
    store.dispatch(
      enqueue({ kind: 'planTask', targetId: 'pt2', payload: { isDone: true } }),
    );
    render(<OfflineBanner />);
    expect(screen.getByText(/2 changes waiting to sync/)).toBeTruthy();
  });

  it('announces itself to assistive tech', () => {
    store.dispatch(connectivityChanged(true));
    render(<OfflineBanner />);
    expect(screen.getByTestId('offline-banner').props.accessibilityRole).toBe(
      'alert',
    );
  });
});
