/** Writing API module. */

import { apiClient, toApiProblem } from './client';
import { API_CONFIG } from './config';
import { ENDPOINTS } from './endpoints';
import { MOCK_WRITING_FEEDBACK } from './mock/fixtures';
import type { WritingFeedback } from '../types';

const delay = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

export const writingApi = {
  async getFeedback(attemptId: string): Promise<WritingFeedback> {
    if (API_CONFIG.useMock) {
      await delay(600);
      return { ...MOCK_WRITING_FEEDBACK, attemptId };
    }
    try {
      const { data } = await apiClient.get<WritingFeedback>(
        ENDPOINTS.writing.attempt(attemptId),
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },
};
