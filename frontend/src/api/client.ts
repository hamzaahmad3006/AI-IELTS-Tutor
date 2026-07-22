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

let getAccessToken: TokenProvider = () => null;

export const setAuthTokenProvider = (provider: TokenProvider): void => {
  getAccessToken = provider;
};

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
