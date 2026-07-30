/**
 * Axios HTTP client with auth-token injection and error normalization.
 *
 * The access token is provided lazily via `setAuthTokenProvider` so this module
 * has no dependency on Redux (avoids circular imports).
 */

import axios, {
  AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from 'axios';
import { API_CONFIG } from './config';
import type { ApiProblem } from '../types';

type TokenProvider = () => string | null;
/** Performs a token refresh and resolves the new access token (or null). */
type RefreshHandler = () => Promise<string | null>;
/** Called when the session is definitively unrecoverable. */
type AuthFailureHandler = () => void;
/** Reports a request failure to the user (wired to the toast queue). */
type ErrorReporter = (message: string) => void;

let getAccessToken: TokenProvider = () => null;
let refreshHandler: RefreshHandler | null = null;
let authFailureHandler: AuthFailureHandler | null = null;
let errorReporter: ErrorReporter | null = null;
let refreshInFlight: Promise<string | null> | null = null;

export const setAuthTokenProvider = (provider: TokenProvider): void => {
  getAccessToken = provider;
};

/** Wire the refresh flow (set from the app root, backed by Redux). */
export const setRefreshHandler = (handler: RefreshHandler): void => {
  refreshHandler = handler;
};

/**
 * Wire the terminal auth-failure path (set from the app root).
 *
 * Without this, a persisted session whose refresh token is *also* rejected
 * leaves the user inside the authenticated navigator with every request 401ing:
 * a blank screen, no error, and no route back to sign-in. That is not an edge
 * case - it happens on refresh-token expiry, a password change, an admin
 * revoking sessions, or the API being repointed at a different database.
 */
export const setAuthFailureHandler = (handler: AuthFailureHandler): void => {
  authFailureHandler = handler;
};

/**
 * Wire connectivity reporting (set from the app root).
 *
 * Only fires when the request never reached the server — no response at all.
 * HTTP errors are deliberately left to the calling screen, which knows whether
 * a 404 or a 422 is worth interrupting the user over; a blanket toast on every
 * non-2xx would double up on inline validation messages.
 */
export const setErrorReporter = (reporter: ErrorReporter): void => {
  errorReporter = reporter;
};

interface RetryableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_CONFIG.baseUrl,
  timeout: API_CONFIG.timeoutMs,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
    const token = getAccessToken();
    if (token) {
      config.headers.set('Authorization', `Bearer ${token}`);
    }
    return config;
  },
);

// On 401, refresh the access token once (single-flight) and retry the request.
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError): Promise<unknown> => {
    const original = error.config as RetryableConfig | undefined;
    const status = error.response?.status;
    const url = original?.url ?? '';
    const isAuthPath =
      url.includes('/auth/login') ||
      url.includes('/auth/register') ||
      url.includes('/auth/refresh');

    if (status === 401 && original && !original._retry && !isAuthPath && refreshHandler) {
      original._retry = true;
      if (!refreshInFlight) {
        refreshInFlight = refreshHandler().finally(() => {
          refreshInFlight = null;
        });
      }
      const newToken = await refreshInFlight;
      if (newToken) {
        original.headers.set('Authorization', `Bearer ${newToken}`);
        return apiClient(original);
      }
      // Refresh failed: the session cannot be recovered. Clear it so the app
      // returns to the sign-in screen instead of stranding the user.
      authFailureHandler?.();
    }

    // No response object means the request never landed: airplane mode, wrong
    // API host, backend down, DNS failure. The user cannot fix that from the
    // screen they are on, so it is surfaced globally.
    if (!error.response) {
      errorReporter?.(
        'No connection to the server. Check your network and try again.',
      );
    }
    return Promise.reject(error);
  },
);

/** Normalize any axios failure into a typed ApiProblem. */
export const toApiProblem = (error: unknown): ApiProblem => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiProblem>;
    const data = axiosError.response?.data;
    if (data && typeof data.code === 'string') {
      return data;
    }
    return {
      type: 'about:blank',
      title: axiosError.message,
      status: axiosError.response?.status ?? 0,
      code: 'network_error',
      correlationId: '',
    };
  }
  return {
    type: 'about:blank',
    title: 'Unexpected error',
    status: 0,
    code: 'unknown_error',
    correlationId: '',
  };
};
