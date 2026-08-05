/** Reading API module. */

import { apiClient, toApiProblem } from './client';
import { API_CONFIG } from './config';
import { ENDPOINTS } from './endpoints';
import { MOCK_READING_PASSAGE, MOCK_READING_RESULT } from '@fixtures';
import type {
  Difficulty,
  ReadingHistoryPage,
  ReadingPassage,
  ReadingResult,
  ReadingSubmit,
} from '../types';

const delay = (ms: number): Promise<void> =>
  new Promise(resolve => setTimeout(resolve, ms));

export const readingApi = {
  async getPassage(difficulty?: Difficulty): Promise<ReadingPassage> {
    if (API_CONFIG.useMock) {
      await delay(400);
      return MOCK_READING_PASSAGE;
    }
    try {
      const { data } = await apiClient.get<ReadingPassage>(
        ENDPOINTS.reading.passages,
        { params: difficulty ? { difficulty } : undefined },
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async submit(payload: ReadingSubmit): Promise<ReadingResult> {
    if (API_CONFIG.useMock) {
      await delay(500);
      return MOCK_READING_RESULT;
    }
    try {
      const { data } = await apiClient.post<ReadingResult>(
        ENDPOINTS.reading.attempts,
        payload,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async getAttempt(attemptId: string): Promise<ReadingResult> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return { ...MOCK_READING_RESULT, attemptId };
    }
    try {
      const { data } = await apiClient.get<ReadingResult>(
        ENDPOINTS.reading.attempt(attemptId),
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async getHistory(cursor?: string): Promise<ReadingHistoryPage> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return { items: [], nextCursor: null };
    }
    try {
      const { data } = await apiClient.get<ReadingHistoryPage>(
        ENDPOINTS.reading.history,
        { params: cursor ? { cursor } : undefined },
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },
};
