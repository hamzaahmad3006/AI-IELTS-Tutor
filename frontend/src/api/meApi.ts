/** Learner self-service API module (`/me`). */

import { apiClient, toApiProblem } from './client';
import { API_CONFIG } from './config';
import { ENDPOINTS } from './endpoints';
import {
  MOCK_ADAPTIVE_DIFFICULTY,
  MOCK_RECOMMENDATIONS,
  MOCK_WEAKNESSES,
} from './mock/fixtures';
import type {
  AdaptiveDifficultyResponse,
  RecommendationsResponse,
  WeaknessList,
} from '../types';

const delay = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

export const meApi = {
  async getWeaknesses(includeResolved = false): Promise<WeaknessList> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return MOCK_WEAKNESSES;
    }
    try {
      const { data } = await apiClient.get<WeaknessList>(
        ENDPOINTS.me.weaknesses,
        { params: { includeResolved } },
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async getAdaptiveDifficulty(): Promise<AdaptiveDifficultyResponse> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return MOCK_ADAPTIVE_DIFFICULTY;
    }
    try {
      const { data } = await apiClient.get<AdaptiveDifficultyResponse>(
        ENDPOINTS.me.adaptiveDifficulty,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async getRecommendations(): Promise<RecommendationsResponse> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return MOCK_RECOMMENDATIONS;
    }
    try {
      const { data } = await apiClient.get<RecommendationsResponse>(
        ENDPOINTS.me.recommendations,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },
};
