/** Writing API module. */

import { apiClient, toApiProblem } from './client';
import { API_CONFIG } from './config';
import { ENDPOINTS } from './endpoints';
import { MOCK_WRITING_FEEDBACK, MOCK_WRITING_RESULT } from './mock/fixtures';
import type {
  ExamType,
  WritingFeedback,
  WritingHistoryPage,
  WritingPrompt,
  WritingResult,
  WritingSubmit,
} from '../types';

const delay = (ms: number): Promise<void> =>
  new Promise(resolve => setTimeout(resolve, ms));

const MOCK_PROMPT: WritingPrompt = {
  id: 'wp_mock_1',
  examType: 'academic',
  taskNumber: 2,
  prompt:
    'Some people believe technology has made our lives more complex, while ' +
    'others think it has simplified them. Discuss both views and give your own opinion.',
  topic: 'technology',
  assetRef: null,
  difficulty: 'medium',
  minWords: 250,
};

export const writingApi = {
  /** Fetch a Task 1/2 prompt from the backend prompt bank. */
  async getPrompt(
    taskNumber = 2,
    examType: ExamType = 'academic',
  ): Promise<WritingPrompt> {
    if (API_CONFIG.useMock) {
      await delay(300);
      // Reflect the requested paper so the selector is demonstrable offline.
      return {
        ...MOCK_PROMPT,
        taskNumber,
        examType,
        minWords: taskNumber === 1 ? 150 : 250,
      };
    }
    try {
      const { data } = await apiClient.get<WritingPrompt>(
        ENDPOINTS.writing.prompts,
        { params: { taskNumber, examType } },
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

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
