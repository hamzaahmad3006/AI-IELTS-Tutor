/** Writing API module. */

import { apiClient, toApiProblem } from './client';
import { API_CONFIG } from './config';
import { ENDPOINTS } from './endpoints';
import { MOCK_WRITING_FEEDBACK, MOCK_WRITING_RESULT } from './mock/fixtures';
import type {
  WritingFeedback,
  WritingHistoryPage,
  WritingResult,
  WritingSubmit,
} from '../types';

const delay = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

export const writingApi = {
  /** Submit an essay for AI scoring. */
  async submit(payload: WritingSubmit): Promise<WritingResult> {
    if (API_CONFIG.useMock) {
      await delay(800);
      return { ...MOCK_WRITING_RESULT, taskType: payload.taskType };
    }
    try {
      const { data } = await apiClient.post<WritingResult>(
        ENDPOINTS.writing.attempts,
        payload,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  /** Fetch a scored writing attempt. */
  async getResult(attemptId: string): Promise<WritingResult> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return { ...MOCK_WRITING_RESULT, attemptId };
    }
    try {
      const { data } = await apiClient.get<WritingResult>(
        ENDPOINTS.writing.attempt(attemptId),
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async getHistory(cursor?: string): Promise<WritingHistoryPage> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return { items: [], nextCursor: null };
    }
    try {
      const { data } = await apiClient.get<WritingHistoryPage>(
        ENDPOINTS.writing.history,
        { params: cursor ? { cursor } : undefined },
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  /**
   * Rich, design-oriented feedback for the Writing Feedback screen (mock-only
   * shape; the real backend returns the leaner WritingResult above).
   */
  async getFeedback(attemptId: string): Promise<WritingFeedback> {
    await delay(600);
    return { ...MOCK_WRITING_FEEDBACK, attemptId };
  },
};
