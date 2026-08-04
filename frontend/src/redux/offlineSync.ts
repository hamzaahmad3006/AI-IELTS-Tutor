/**
 * Drains the offline queue.
 *
 * Lives outside the slice because sending is a side effect, and outside the
 * screens because a queued write must survive the screen that created it.
 */

import { plannerApi } from '@api';
import type { AppDispatch, RootState } from './store';
import {
  connectivityChanged,
  mutationFailed,
  mutationSucceeded,
  syncFinished,
  syncStarted,
  type QueuedMutation,
} from './slices/offlineSlice';

/** Give up on an item after this many failed sends. */
export const MAX_ATTEMPTS = 5;

const send = async (item: QueuedMutation): Promise<void> => {
  switch (item.kind) {
    case 'planTask':
      await plannerApi.setTaskDone(item.targetId, item.payload.isDone === true);
      return;
    default: {
      // Exhaustiveness: adding a kind without a sender is a type error here
      // rather than a silent no-op that quietly drops the learner's work.
      const unreachable: never = item.kind;
      throw new Error(`No sender for queued mutation: ${String(unreachable)}`);
    }
  }
};

/**
 * Attempt to send everything queued, oldest first.
 *
 * Order matters: writes are replayed in the order they were made, so the
 * server ends up in the state the learner actually left the app in.
 */
export const drainQueue = async (
  dispatch: AppDispatch,
  getState: () => RootState,
): Promise<void> => {
  const { queue, isSyncing } = getState().offline;
  if (isSyncing || queue.length === 0) {
    return;
  }

  dispatch(syncStarted());
  let allSent = true;

  for (const item of [...queue]) {
    if (item.attempts >= MAX_ATTEMPTS) {
      // Left in the queue rather than deleted: silently discarding a write the
      // learner made is worse than showing it as stuck and unsent.
      allSent = false;
      continue;
    }
    try {
      // Sequential on purpose: replaying in order is what makes the final
      // server state match what the learner left behind.
      await send(item);
      dispatch(mutationSucceeded(item.id));
    } catch (error) {
      allSent = false;
      dispatch(
        mutationFailed({
          id: item.id,
          error: error instanceof Error ? error.message : 'Send failed',
        }),
      );
      // A failure here almost certainly means still offline, so stop rather
      // than burning through the rest of the queue's retry budget at once.
      dispatch(connectivityChanged(true));
      break;
    }
  }

  if (allSent) {
    dispatch(connectivityChanged(false));
  }
  dispatch(syncFinished({ allSent }));
};
