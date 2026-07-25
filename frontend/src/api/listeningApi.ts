/** Listening API module. */

import { apiClient, toApiProblem } from './client';
import { API_CONFIG } from './config';
import { ENDPOINTS } from './endpoints';
import { MOCK_LISTENING_CLIP, MOCK_LISTENING_RESULT } from './mock/fixtures';
import type {
  Difficulty,
  ListeningClip,
  ListeningHistoryPage,
  ListeningResult,
  ListeningSubmit,
} from '../types';

const delay = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

export const listeningApi = {
  async getClip(difficulty?: Difficulty): Promise<ListeningClip> {
    if (API_CONFIG.useMock) {
      await delay(400);
      return MOCK_LISTENING_CLIP;
    }
    try {
      const { data } = await apiClient.get<ListeningClip>(
        ENDPOINTS.listening.clips,
        { params: difficulty ? { difficulty } : undefined },
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async submit(payload: ListeningSubmit): Promise<ListeningResult> {
    if (API_CONFIG.useMock) {
      await delay(500);
      return MOCK_LISTENING_RESULT;
    }
    try {
      const { data } = await apiClient.post<ListeningResult>(
        ENDPOINTS.listening.attempts,
        payload,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async getAttempt(attemptId: string): Promise<ListeningResult> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return { ...MOCK_LISTENING_RESULT, attemptId };
    }
    try {
      const { data } = await apiClient.get<ListeningResult>(
        ENDPOINTS.listening.attempt(attemptId),
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async getHistory(cursor?: string): Promise<ListeningHistoryPage> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return { items: [], nextCursor: null };
    }
    try {
      const { data } = await apiClient.get<ListeningHistoryPage>(
        ENDPOINTS.listening.history,
        { params: cursor ? { cursor } : undefined },
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },
};
