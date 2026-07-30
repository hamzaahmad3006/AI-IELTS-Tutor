/**
 * Response-interceptor behaviour: token refresh on 401, and the terminal
 * auth-failure path that clears an unrecoverable session.
 */

import { AxiosError, type AxiosAdapter, type AxiosResponse } from 'axios';
import {
  apiClient,
  setAuthFailureHandler,
  setAuthTokenProvider,
  setRefreshHandler,
} from '../client';

/**
 * Adapter that replies with each status in turn and records how many calls it
 * saw. A custom adapter bypasses axios's own `validateStatus` handling, so it
 * has to reject non-2xx itself the way the built-in adapters do.
 */
const adapterReplying = (
  statuses: number[],
): { adapter: AxiosAdapter; calls: () => number } => {
  let call = 0;
  const adapter: AxiosAdapter = (config) => {
    const status = statuses[Math.min(call, statuses.length - 1)];
    call += 1;
    const response: AxiosResponse = {
      data: {},
      status,
      statusText: String(status),
      headers: {},
      config,
    };
    if (status >= 200 && status < 300) {
      return Promise.resolve(response);
    }
    return Promise.reject(
      new AxiosError(
        `Request failed with status code ${status}`,
        AxiosError.ERR_BAD_REQUEST,
        config,
        undefined,
        response,
      ),
    );
  };
  return { adapter, calls: () => call };
};

describe('apiClient response interceptor', () => {
  const originalAdapter = apiClient.defaults.adapter;

  afterEach(() => {
    apiClient.defaults.adapter = originalAdapter;
    setAuthTokenProvider(() => null);
    setRefreshHandler(async () => null);
    setAuthFailureHandler(() => undefined);
  });

  it('retries the request once with the refreshed token', async () => {
    const { adapter, calls } = adapterReplying([401, 200]);
    apiClient.defaults.adapter = adapter;

    setAuthTokenProvider(() => 'stale-token');
    setRefreshHandler(async () => 'fresh-token');
    const onAuthFailure = jest.fn();
    setAuthFailureHandler(onAuthFailure);

    const response = await apiClient.get('/analytics/overview');

    expect(response.status).toBe(200);
    expect(calls()).toBe(2);
    expect(onAuthFailure).not.toHaveBeenCalled();
  });

  it('clears the session when the refresh also fails', async () => {
    const { adapter } = adapterReplying([401]);
    apiClient.defaults.adapter = adapter;

    setAuthTokenProvider(() => 'stale-token');
    setRefreshHandler(async () => null); // refresh token rejected too
    const onAuthFailure = jest.fn();
    setAuthFailureHandler(onAuthFailure);

    await expect(apiClient.get('/analytics/overview')).rejects.toBeDefined();

    // Without this the user is stranded on an authenticated screen that 401s.
    expect(onAuthFailure).toHaveBeenCalledTimes(1);
  });

  it('does not attempt a refresh for the login endpoint', async () => {
    const { adapter, calls } = adapterReplying([401]);
    apiClient.defaults.adapter = adapter;

    const refresh = jest.fn(async () => 'fresh-token');
    setRefreshHandler(refresh);
    const onAuthFailure = jest.fn();
    setAuthFailureHandler(onAuthFailure);

    await expect(apiClient.post('/auth/login')).rejects.toBeDefined();

    // Bad credentials must surface as a 401 to the form, not a refresh attempt
    // or a session wipe.
    expect(calls()).toBe(1);
    expect(refresh).not.toHaveBeenCalled();
    expect(onAuthFailure).not.toHaveBeenCalled();
  });
});
