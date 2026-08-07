/**
 * The async-slice factory.
 *
 * These are the behaviours that drift when forty lines are copied six times:
 * one copy forgets to clear the error on retry, another blanks the data on a
 * failed refresh, a third reports "undefined" because the thrown thing was not
 * the shape it expected. Written once and tested once instead.
 */

import { configureStore } from '@reduxjs/toolkit';
import { createAsyncSlice, initialAsyncState } from '../createAsyncSlice';

interface Payload {
  value: string;
}

const build = (fetcher: () => Promise<Payload>) => {
  const slice = createAsyncSlice<Payload>({
    name: 'test',
    fetcher,
    fallbackError: 'fallback message',
  });
  const store = configureStore({ reducer: { test: slice.reducer } });
  return { slice, store, state: () => store.getState().test };
};

describe('createAsyncSlice', () => {
  it('starts idle and empty', () => {
    const { state } = build(() => Promise.resolve({ value: 'x' }));
    expect(state()).toEqual(initialAsyncState());
  });

  it('moves through loading to succeeded', async () => {
    const { slice, store, state } = build(() =>
      Promise.resolve({ value: 'loaded' }),
    );

    const pending = store.dispatch(slice.fetch());
    expect(state().status).toBe('loading');

    await pending;
    expect(state().status).toBe('succeeded');
    expect(state().data).toEqual({ value: 'loaded' });
    expect(state().error).toBeNull();
  });

  it('reports the API message on failure', async () => {
    const { slice, store, state } = build(() =>
      Promise.reject({ title: 'Your session expired.' }),
    );

    await store.dispatch(slice.fetch());
    expect(state().status).toBe('failed');
    expect(state().error).toBe('Your session expired.');
  });

  it('falls back when the thrown thing has no message', async () => {
    // A network failure or a bug arrives as something that is not an
    // ApiProblem, and "undefined" on screen is worse than a generic sentence.
    for (const thrown of [
      {},
      null,
      undefined,
      'a bare string',
      { title: '' },
    ]) {
      const { slice, store, state } = build(() => Promise.reject(thrown));
      await store.dispatch(slice.fetch());
      expect(state().error).toBe('fallback message');
    }
  });

  it('uses an Error message when there is one', async () => {
    const { slice, store, state } = build(() =>
      Promise.reject(new Error('Network Error')),
    );
    await store.dispatch(slice.fetch());
    expect(state().error).toBe('Network Error');
  });

  it('clears a stale error when a retry starts', async () => {
    let fail = true;
    const { slice, store, state } = build(() =>
      fail
        ? Promise.reject({ title: 'boom' })
        : Promise.resolve({ value: 'ok' }),
    );

    await store.dispatch(slice.fetch());
    expect(state().error).toBe('boom');

    fail = false;
    const pending = store.dispatch(slice.fetch());
    // Showing an old error beside a fresh spinner tells the user two
    // contradictory things at once.
    expect(state().error).toBeNull();

    await pending;
    expect(state().data).toEqual({ value: 'ok' });
    expect(state().error).toBeNull();
  });

  it('keeps the last good data when a refresh fails', async () => {
    let fail = false;
    const { slice, store, state } = build(() =>
      fail
        ? Promise.reject({ title: 'offline' })
        : Promise.resolve({ value: 'good' }),
    );

    await store.dispatch(slice.fetch());
    expect(state().data).toEqual({ value: 'good' });

    fail = true;
    await store.dispatch(slice.fetch());

    // Slightly old progress beats a blank screen. Blanking it would punish the
    // user for a network blip by deleting what they were reading.
    expect(state().data).toEqual({ value: 'good' });
    expect(state().status).toBe('failed');
    expect(state().error).toBe('offline');
  });

  it('resets to empty on request', async () => {
    const { slice, store, state } = build(() =>
      Promise.resolve({ value: 'private' }),
    );
    await store.dispatch(slice.fetch());
    expect(state().data).not.toBeNull();

    store.dispatch(slice.actions.reset());

    // Used on logout: one person's data left on screen for the next person to
    // sign in on the same device is the failure this prevents.
    expect(state()).toEqual(initialAsyncState());
  });

  it('passes its argument through to the fetcher', async () => {
    const fetcher = jest.fn((arg: number) =>
      Promise.resolve({ value: `${arg}` }),
    );
    const slice = createAsyncSlice<Payload, number>({
      name: 'arg',
      fetcher,
      fallbackError: 'nope',
    });
    const store = configureStore({ reducer: { arg: slice.reducer } });

    await store.dispatch(slice.fetch(42));
    expect(fetcher).toHaveBeenCalledWith(42);
    expect(store.getState().arg.data).toEqual({ value: '42' });
  });
});
