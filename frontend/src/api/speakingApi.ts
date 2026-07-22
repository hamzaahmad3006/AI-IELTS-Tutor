/** Speaking API module. */

import { apiClient, toApiProblem } from './client';
import { API_CONFIG } from './config';
import { ENDPOINTS } from './endpoints';
import { MOCK_SPEAKING_SESSION } from './mock/fixtures';
import type { SpeakingSession } from '../types';

const delay = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

export const speakingApi = {
  async createSession(): Promise<SpeakingSession> {
    if (API_CONFIG.useMock) {
      await delay(800);
      return MOCK_SPEAKING_SESSION;
    }
    try {
      const { data } = await apiClient.post<SpeakingSession>(
        ENDPOINTS.speaking.sessions,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },
};
