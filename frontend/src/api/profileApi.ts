/** Onboarding + profile API module. */

import { apiClient, toApiProblem } from './client';
import { API_CONFIG } from './config';
import { ENDPOINTS } from './endpoints';
import { MOCK_PROFILE } from './mock/fixtures';
import type {
  OnboardingRequest,
  ProfileResponse,
  ProfileUpdate,
} from '../types';

const delay = (ms: number): Promise<void> =>
  new Promise(resolve => setTimeout(resolve, ms));

export const profileApi = {
  async submitOnboarding(payload: OnboardingRequest): Promise<ProfileResponse> {
    if (API_CONFIG.useMock) {
      await delay(500);
      return { ...MOCK_PROFILE, ...payload };
    }
    try {
      const { data } = await apiClient.post<ProfileResponse>(
        ENDPOINTS.onboarding.submit,
        payload,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async getProfile(): Promise<ProfileResponse> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return MOCK_PROFILE;
    }
    try {
      const { data } = await apiClient.get<ProfileResponse>(
        ENDPOINTS.profile.root,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async updateProfile(patch: ProfileUpdate): Promise<ProfileResponse> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return { ...MOCK_PROFILE, ...patch };
    }
    try {
      const { data } = await apiClient.patch<ProfileResponse>(
        ENDPOINTS.profile.root,
        patch,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },
};
