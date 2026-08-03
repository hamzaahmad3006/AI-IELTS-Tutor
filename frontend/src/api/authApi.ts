/** Authentication API module. */

import { apiClient, toApiProblem } from './client';
import { API_CONFIG } from './config';
import { ENDPOINTS } from './endpoints';
import { MOCK_AUTH } from './mock/fixtures';
import type {
  AuthenticatedUser,
  AuthResponse,
  LoginRequest,
  RegisterRequest,
} from '../types';

const delay = (ms: number): Promise<void> =>
  new Promise(resolve => setTimeout(resolve, ms));

export const authApi = {
  async login(payload: LoginRequest): Promise<AuthResponse> {
    if (API_CONFIG.useMock) {
      await delay(600);
      return MOCK_AUTH;
    }
    try {
      const { data } = await apiClient.post<AuthResponse>(
        ENDPOINTS.auth.login,
        payload,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async register(payload: RegisterRequest): Promise<AuthResponse> {
    if (API_CONFIG.useMock) {
      await delay(700);
      return {
        ...MOCK_AUTH,
        user: {
          ...MOCK_AUTH.user,
          fullName: payload.fullName,
          email: payload.email,
        },
      };
    }
    try {
      const { data } = await apiClient.post<AuthResponse>(
        ENDPOINTS.auth.register,
        payload,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async refresh(refreshToken: string): Promise<AuthResponse> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return MOCK_AUTH;
    }
    try {
      const { data } = await apiClient.post<AuthResponse>(
        ENDPOINTS.auth.refresh,
        { refreshToken },
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async me(): Promise<AuthenticatedUser> {
    if (API_CONFIG.useMock) {
      await delay(200);
      return MOCK_AUTH.user;
    }
    try {
      const { data } = await apiClient.get<AuthenticatedUser>(
        ENDPOINTS.auth.me,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async logout(refreshToken: string): Promise<void> {
    if (API_CONFIG.useMock) {
      return;
    }
    try {
      await apiClient.post(ENDPOINTS.auth.logout, { refreshToken });
    } catch {
      // Best-effort: local sign-out proceeds even if the call fails.
    }
  },
};
