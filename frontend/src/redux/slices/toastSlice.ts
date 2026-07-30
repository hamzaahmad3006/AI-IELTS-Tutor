/**
 * Transient user feedback (toasts / snackbars).
 *
 * Lives in Redux rather than a React context so non-component code — the axios
 * interceptor in particular — can raise a message without a provider in scope.
 * Never persisted: a stale "Saved!" on next launch would be a lie.
 */

import { createSlice, nanoid, type PayloadAction } from '@reduxjs/toolkit';

export type ToastTone = 'success' | 'error' | 'info';

export interface Toast {
  id: string;
  message: string;
  tone: ToastTone;
  /** Milliseconds before auto-dismiss. */
  durationMs: number;
}

export interface ToastState {
  queue: Toast[];
}

const initialState: ToastState = { queue: [] };

/** Errors stay longer: they usually carry an instruction to act on. */
const DEFAULT_DURATION: Record<ToastTone, number> = {
  success: 2500,
  info: 3000,
  error: 4500,
};

interface ShowToastPayload {
  message: string;
  tone?: ToastTone;
  durationMs?: number;
}

const toastSlice = createSlice({
  name: 'toast',
  initialState,
  reducers: {
    showToast: {
      reducer(state, action: PayloadAction<Toast>): void {
        // Collapse repeats: a failing screen that retries three times should
        // not stack three identical bars.
        if (state.queue.some((t) => t.message === action.payload.message)) {
          return;
        }
        state.queue.push(action.payload);
      },
      prepare({ message, tone = 'info', durationMs }: ShowToastPayload) {
        return {
          payload: {
            id: nanoid(),
            message,
            tone,
            durationMs: durationMs ?? DEFAULT_DURATION[tone],
          },
        };
      },
    },
    dismissToast(state, action: PayloadAction<string>): void {
      state.queue = state.queue.filter((t) => t.id !== action.payload);
    },
    clearToasts(state): void {
      state.queue = [];
    },
  },
});

export const { showToast, dismissToast, clearToasts } = toastSlice.actions;
export const toastReducer = toastSlice.reducer;
