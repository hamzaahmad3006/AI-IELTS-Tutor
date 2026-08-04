/**
 * Connectivity state and the queue of writes that could not be sent.
 *
 * Connectivity is *inferred from request outcomes*, not read from the OS. A
 * true connectivity API needs `@react-native-community/netinfo`, which is a
 * native module and cannot be verified here. Inference is honest about what it
 * knows: a request that never reached the server means offline, a response of
 * any kind means online. The cost is that going offline is only noticed on the
 * next attempt, which is stated in the UI rather than hidden.
 *
 * Persisted, because a queue that empties on app restart would silently discard
 * the very work it exists to protect.
 */

import { createSlice, nanoid, type PayloadAction } from '@reduxjs/toolkit';

/** Only writes are queued. A failed read is retried by reopening the screen. */
export type QueuedKind = 'planTask';

export interface QueuedMutation {
  id: string;
  kind: QueuedKind;
  /** Identifies the row the write targets, for de-duplication. */
  targetId: string;
  payload: Record<string, boolean>;
  queuedAt: string;
  attempts: number;
  lastError: string | null;
}

export interface OfflineState {
  isOffline: boolean;
  queue: QueuedMutation[];
  isSyncing: boolean;
  lastSyncedAt: string | null;
}

const initialState: OfflineState = {
  isOffline: false,
  queue: [],
  isSyncing: false,
  lastSyncedAt: null,
};

interface EnqueuePayload {
  kind: QueuedKind;
  targetId: string;
  payload: Record<string, boolean>;
}

const offlineSlice = createSlice({
  name: 'offline',
  initialState,
  reducers: {
    connectivityChanged(state, action: PayloadAction<boolean>): void {
      state.isOffline = action.payload;
    },

    enqueue: {
      reducer(state, action: PayloadAction<QueuedMutation>): void {
        // Last write wins per target. Toggling a task on, off, then on again
        // offline should send one final state, not three conflicting writes
        // that race on the server and land in an arbitrary order.
        const existing = state.queue.findIndex(
          item =>
            item.kind === action.payload.kind &&
            item.targetId === action.payload.targetId,
        );
        if (existing >= 0) {
          state.queue[existing] = {
            ...action.payload,
            // Keep the original queue time: what matters is when the learner
            // first went offline, not when they last changed their mind.
            queuedAt: state.queue[existing].queuedAt,
          };
          return;
        }
        state.queue.push(action.payload);
      },
      prepare({ kind, targetId, payload }: EnqueuePayload) {
        return {
          payload: {
            id: nanoid(),
            kind,
            targetId,
            payload,
            queuedAt: new Date().toISOString(),
            attempts: 0,
            lastError: null,
          },
        };
      },
    },

    syncStarted(state): void {
      state.isSyncing = true;
    },

    mutationSucceeded(state, action: PayloadAction<string>): void {
      state.queue = state.queue.filter(item => item.id !== action.payload);
    },

    mutationFailed(
      state,
      action: PayloadAction<{ id: string; error: string }>,
    ): void {
      const item = state.queue.find(entry => entry.id === action.payload.id);
      if (item) {
        item.attempts += 1;
        item.lastError = action.payload.error;
      }
    },

    syncFinished(state, action: PayloadAction<{ allSent: boolean }>): void {
      state.isSyncing = false;
      if (action.payload.allSent) {
        state.lastSyncedAt = new Date().toISOString();
      }
    },

    clearQueue(state): void {
      state.queue = [];
    },
  },
});

export const {
  connectivityChanged,
  enqueue,
  syncStarted,
  mutationSucceeded,
  mutationFailed,
  syncFinished,
  clearQueue,
} = offlineSlice.actions;
export const offlineReducer = offlineSlice.reducer;
