/**
 * Factory for the "fetch one thing, track loading and error" slice.
 *
 * Six of these were about to be written by hand, and they would have been the
 * same forty lines six times with the nouns changed. Copies drift: the fifth
 * one forgets to clear the error on retry, the third reports a different
 * default message, and nobody notices because each looks fine on its own.
 *
 * The pieces that genuinely differ are the name and the fetch call, so those
 * are the arguments. Everything else — the three lifecycle cases, the error
 * handling, the reset — is written once.
 *
 * A slice that needs more than this should be written by hand rather than
 * forced through here. `offlineSlice` is the example: it owns a queue with real
 * behaviour, not a cached response.
 */

import {
  createAsyncThunk,
  createSlice,
  type PayloadAction,
} from '@reduxjs/toolkit';
import type { ApiProblem, AsyncState } from '@models';

interface AsyncSliceOptions<T, Arg> {
  /** Slice name; also the thunk's action-type prefix. */
  name: string;
  /** The API call. */
  fetcher: (arg: Arg) => Promise<T>;
  /** Shown when the API gives no message of its own. */
  fallbackError: string;
}

export const initialAsyncState = <T>(): AsyncState<T> => ({
  data: null,
  status: 'idle',
  error: null,
});

/**
 * Pull a human-readable message off whatever was thrown.
 *
 * The API layer normalises errors to ApiProblem, but a network failure or a
 * bug in a reducer arrives as something else entirely, and "undefined" on
 * screen is worse than a generic sentence.
 */
const describe = (error: unknown, fallback: string): string => {
  const problem = error as ApiProblem | undefined;
  if (problem && typeof problem.title === 'string' && problem.title) {
    return problem.title;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
};

export const createAsyncSlice = <T, Arg = void>({
  name,
  fetcher,
  fallbackError,
}: AsyncSliceOptions<T, Arg>) => {
  const thunk = createAsyncThunk<T, Arg, { rejectValue: string }>(
    `${name}/fetch`,
    async (arg, { rejectWithValue }) => {
      try {
        return await fetcher(arg);
      } catch (error) {
        return rejectWithValue(describe(error, fallbackError));
      }
    },
  );

  const slice = createSlice({
    name,
    initialState: initialAsyncState<T>(),
    reducers: {
      /** Drop cached data, e.g. on logout so the next user sees nothing of it. */
      reset: () => initialAsyncState<T>(),
    },
    extraReducers: builder => {
      builder
        .addCase(thunk.pending, state => {
          state.status = 'loading';
          // Cleared on every attempt: a stale error rendered next to fresh
          // data is the app telling the user two contradictory things.
          state.error = null;
        })
        .addCase(thunk.fulfilled, (state, action: PayloadAction<T>) => {
          state.status = 'succeeded';
          // Cast to the state's own field type rather than Draft<T>:
          // immer's Draft is conditional on whether T is an object, which an
          // unconstrained generic cannot satisfy.
          state.data = action.payload as typeof state.data;
          state.error = null;
        })
        .addCase(thunk.rejected, (state, action) => {
          state.status = 'failed';
          state.error = action.payload ?? fallbackError;
          // `data` is deliberately kept. A failed refresh should leave the
          // last good content on screen rather than blanking it — the user
          // would rather see slightly old progress than nothing at all.
        });
    },
  });

  return {
    reducer: slice.reducer,
    actions: slice.actions,
    fetch: thunk,
  };
};
