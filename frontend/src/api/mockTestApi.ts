/** Full mock test API module. */

import { apiClient, toApiProblem } from './client';
import { API_CONFIG } from './config';
import { ENDPOINTS } from './endpoints';
import { MOCK_MOCK_RESULT, MOCK_MOCK_TEST } from './mock/fixtures';
import type { MockResult, MockSubmission, MockTest } from '../types';

const delay = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

export const mockTestApi = {
  async start(): Promise<MockTest> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return MOCK_MOCK_TEST;
    }
    try {
      const { data } = await apiClient.post<MockTest>(ENDPOINTS.mockTests.root);
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async submit(testId: string, payload: MockSubmission): Promise<MockResult> {
    if (API_CONFIG.useMock) {
      await delay(500);
      return MOCK_MOCK_RESULT;
    }
    try {
      const { data } = await apiClient.post<MockResult>(
        `${ENDPOINTS.mockTests.root}/${testId}/submit`,
        payload,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },

  async history(): Promise<MockResult[]> {
    if (API_CONFIG.useMock) {
      await delay(300);
      return [MOCK_MOCK_RESULT];
    }
    try {
      const { data } = await apiClient.get<MockResult[]>(
        ENDPOINTS.mockTests.root,
      );
      return data;
    } catch (error) {
      throw toApiProblem(error);
    }
  },
};
